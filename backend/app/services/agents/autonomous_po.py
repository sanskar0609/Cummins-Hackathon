import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.po_draft import PODraft, POStatus as PODraftStatus
from app.core.config import settings
from app.core.logging import log
from app.core.gemini_rotator import generate_content_with_retry as _gemini_gen

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
       "supplier_id": 1,
       "company_id": 0,
       "quantity_to_order": 0,
       "estimated_unit_cost": 0.0,
       "justification": "..."
    }}
    """
    try:
        # Gemini rotator (5 keys round-robin) → auto falls back to Groq on full exhaustion
        raw = _gemini_gen(prompt, model_name="gemini-2.0-flash")
        clean = raw.replace("```json", "").replace("```", "").strip()
        state["po_draft"] = json.loads(clean)
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
        supplier_id_val = po.get("supplier_id", 1)
        if isinstance(supplier_id_val, str) and not supplier_id_val.isdigit():
            supplier_id_val = 1
            
        # Enforce company_id from telemetry to prevent any AI-driven data cross-contamination
        cid = state["telemetry"].get("company_id")
            
        draft = PODraft(
            company_profile_id=cid,
            sku=po.get("sku", "UNKNOWN")[:20],
            supplier_id=int(supplier_id_val),
            quantity=po.get("quantity_to_order", 0),
            unit_cost=po.get("estimated_unit_cost", 0.0),
            ai_justification=po.get("justification", ""),
            total_value=po.get("quantity_to_order", 0) * po.get("estimated_unit_cost", 0.0),
            status=PODraftStatus.PENDING_APPROVAL
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
        log.info("po_agent_draft_created", id=draft.id, company_id=cid)
        state["po_draft"]["id"] = draft.id
        state["bapi_status"] = "DRAFT_SAVED"
    except Exception as e:
        log.error("po_agent_db_save_error", error=str(e))
        state["bapi_status"] = "DB_PERSISTENCE_ERROR"
    finally:
        db.close()

    return state

def finalize_po_execution(po_id: int, approved_by: str = "MANUAL_UI") -> dict:
    db: Session = SessionLocal()
    try:
        draft = db.query(PODraft).filter(PODraft.id == po_id).first()
        if not draft:
            return {"status": "error", "message": "PO Draft not found"}
        
        draft.status = PODraftStatus.APPROVED
        draft.approved_by = approved_by
        db.commit()
        log.info("po_finalized", id=po_id, approved_by=approved_by)
        return {"status": "success", "po_id": po_id}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

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
