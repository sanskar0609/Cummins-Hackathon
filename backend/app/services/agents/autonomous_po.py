import json
from google import genai
from google.genai import types
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.po_draft import PODraft, POStatus as PODraftStatus
from app.core.config import settings
from app.core.logging import log

_client = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None

class POAgentState(TypedDict):
    telemetry: dict
    is_breach: bool
    po_draft: Optional[dict]
    slack_ts: Optional[str]
    bapi_status: str

def detect_breach_node(state: POAgentState) -> POAgentState:
    ratio = state["telemetry"].get("ds_ratio", 0.0)
    log.info("po_agent_evaluating_breach", ratio=ratio)
    if ratio > 1.5:
        state["is_breach"] = True
    else:
        state["is_breach"] = False
        state["bapi_status"] = "SKIPPED_NO_BREACH"
    return state

def draft_po_node(state: POAgentState) -> POAgentState:
    if not state["is_breach"]:
        return state

    log.info("po_agent_drafting_po")
    prompt = f"""
    You are an autonomous SAP ERP Purchasing Agent.
    A Demand/Supply ratio breach has been detected.

    Telemetry Context:
    {json.dumps(state['telemetry'], indent=2)}

    Calculate how much emergency supply to order to bring ratio back to ~1.0.
    Output STRICTLY as JSON:
    {{
       "sku": "...",
       "supplier_id": "...",
       "quantity_to_order": 0,
       "estimated_unit_cost": 0.0,
       "justification": "..."
    }}
    """
    if not _client:
        state["po_draft"] = None
        state["bapi_status"] = "GEMINI_NOT_CONFIGURED"
        return state

    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        state["po_draft"] = json.loads(response.text)
    except Exception as e:
        log.error("gemini_po_drafting_error", error=str(e))
        state["po_draft"] = None
        state["bapi_status"] = "AI_FORMATTING_ERROR"

    return state

def dispatch_slack_approval_node(state: POAgentState) -> POAgentState:
    if state.get("bapi_status") or not state.get("po_draft"):
        return state

    if not settings.SLACK_BOT_TOKEN or not settings.SLACK_CHANNEL_ID:
        log.warning("mocking_slack_approval", reason="No slack credentials")
        state["slack_ts"] = "mocked_ts_12345"
        return state

    client = WebClient(token=settings.SLACK_BOT_TOKEN)
    po = state["po_draft"]
    total_cost = po.get("quantity_to_order", 0) * po.get("estimated_unit_cost", 0.0)
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "🤖 Autonomous PO Draft Prepared"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*SKU:*\n{po.get('sku')}"},
            {"type": "mrkdwn", "text": f"*Supplier:*\n{po.get('supplier_id')}"},
            {"type": "mrkdwn", "text": f"*Quantity:*\n{po.get('quantity_to_order')}"},
            {"type": "mrkdwn", "text": f"*Est Total:*\n${total_cost:,.2f}"},
        ]},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*AI Justification:*\n_{po.get('justification')}_"}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "Approve & Execute (BAPI)"}, "style": "primary", "value": "approve_po"},
            {"type": "button", "text": {"type": "plain_text", "text": "Reject"}, "style": "danger", "value": "reject_po"},
        ]}
    ]
    try:
        res = client.chat_postMessage(channel=settings.SLACK_CHANNEL_ID, blocks=blocks, text="PO Approval Required")
        state["slack_ts"] = res["ts"]
        log.info("slack_po_approval_dispatched")
    except SlackApiError as e:
        log.error("slack_dispatch_error", error=e.response["error"])
        state["bapi_status"] = "SLACK_API_ERROR"

    return state

def execute_mock_bapi_node(state: POAgentState) -> POAgentState:
    if state.get("bapi_status") or not state.get("po_draft"):
        return state

    po = state["po_draft"]
    db: Session = SessionLocal()
    try:
        draft = PODraft(
            sku=po.get("sku", "UNKNOWN"),
            supplier_id=po.get("supplier_id", "UNKNOWN"),
            quantity=po.get("quantity_to_order", 0),
            unit_cost=po.get("estimated_unit_cost", 0.0),
            ai_justification=po.get("justification", ""),
            total_value=po.get("quantity_to_order", 0) * po.get("estimated_unit_cost", 0.0),
            status=PODraftStatus.APPROVED_PENDING_ERP
        )
        db.add(draft)
        db.commit()
        log.info("po_agent_bapi_stubbed_and_audited")
        state["bapi_status"] = "SUCCESS_LOGGED_TO_DB"
    except Exception as e:
        log.error("bapi_commit_error", error=str(e))
        state["bapi_status"] = "DB_PERSISTENCE_ERROR"
    finally:
        db.close()

    return state

# ─── LANGGRAPH TOPOLOGY ────────────────────────────────────────────────────────
po_workflow = StateGraph(POAgentState)
po_workflow.add_node("detect_breach", detect_breach_node)
po_workflow.add_node("draft_po", draft_po_node)
po_workflow.add_node("dispatch_slack", dispatch_slack_approval_node)
po_workflow.add_node("execute_bapi", execute_mock_bapi_node)
po_workflow.set_entry_point("detect_breach")
po_workflow.add_edge("detect_breach", "draft_po")
po_workflow.add_edge("draft_po", "dispatch_slack")
po_workflow.add_edge("dispatch_slack", "execute_bapi")
po_workflow.add_edge("execute_bapi", END)
autonomous_po_agent = po_workflow.compile()

def trigger_po_agent(telemetry: dict) -> dict:
    initial_state = POAgentState(
        telemetry=telemetry, is_breach=False, po_draft=None, slack_ts=None, bapi_status=""
    )
    return autonomous_po_agent.invoke(initial_state)
