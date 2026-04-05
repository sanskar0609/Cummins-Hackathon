import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Dict, Any
from app.core.config import settings
from app.core.logging import log
from app.core.gemini_rotator import generate_content_with_retry as _gemini_gen

class AlertState(TypedDict):
    alert_source: str
    raw_context: dict
    situation_summary: Optional[str]
    recommended_action: Optional[str]
    slack_ts: Optional[str]
    status: str

def format_alert_llm_node(state: AlertState) -> AlertState:
    log.info("agent_smart_alert_formatting", source=state["alert_source"])

    prompt = f"""
    You are an autonomous Supply Chain Watchtower Agent.
    You have intercepted a critical operational alert of type: {state['alert_source']}.

    Raw Event Context:
    {json.dumps(state['raw_context'], indent=2)}

    Draft a professional, targeted alert for the Supply Chain Manager.

    Outputs required:
    1. 'situation_summary': A concise 2-sentence summary of what is failing.
    2. 'recommended_action': A 1-sentence specific action to mitigate the risk immediately.

    Respond STRICTLY in JSON:
    {{
        "situation_summary": "...",
        "recommended_action": "..."
    }}
    """

    try:
        # Gemini rotator (5 keys round-robin) → auto falls back to Groq on full exhaustion
        raw = _gemini_gen(prompt, model_name="gemini-2.0-flash")
        clean = raw.replace("```json", "").replace("```", "").strip()
        payload = json.loads(clean)
        state["situation_summary"]  = payload.get("situation_summary", "Critical threshold breached.")
        state["recommended_action"] = payload.get("recommended_action", "Review dashboard.")
        state["status"] = "FORMATTED"
    except json.JSONDecodeError:
        state["situation_summary"]  = raw.strip() if 'raw' in dir() else "Error parsing context."
        state["recommended_action"] = "Manual override required."
        state["status"] = "ERROR"
    except Exception as e:
        log.error("gemini_alert_format_error", error=str(e))
        state["situation_summary"]  = "Error parsing context via AI core."
        state["recommended_action"] = "Manual override required."
        state["status"] = "ERROR"

    return state

def dispatch_slack_node(state: AlertState) -> AlertState:
    if state["status"] == "ERROR" or not settings.SLACK_BOT_TOKEN or not settings.SLACK_CHANNEL_ID:
        log.warning("skipping_slack_dispatch", reason="No credentials or earlier error — mocking.")
        state["status"] = "MOCKED_EXECUTION"
        return state

    client = WebClient(token=settings.SLACK_BOT_TOKEN)
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"🚨 Supply Chain Alert: {state['alert_source'].replace('_', ' ')}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Situation Summary:*\n{state['situation_summary']}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Recommended Action:*\n{state['recommended_action']}"}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "Approve Action", "emoji": True}, "style": "primary",
             "value": json.dumps({"action": "approve", "source": state["alert_source"]})},
            {"type": "button", "text": {"type": "plain_text", "text": "Dismiss", "emoji": True}, "style": "danger",
             "value": json.dumps({"action": "dismiss"})}
        ]}
    ]
    try:
        response = client.chat_postMessage(channel=settings.SLACK_CHANNEL_ID, blocks=blocks, text=state["situation_summary"])
        state["slack_ts"] = response["ts"]
        state["status"] = "DISPATCHED"
        log.info("slack_alert_dispatched", ts=response["ts"])
    except SlackApiError as e:
        log.error("slack_dispatch_error", error=e.response["error"])
        state["status"] = "SLACK_API_ERROR"

    return state

# ─── LANGGRAPH TOPOLOGY ────────────────────────────────────────────────────────
alert_workflow = StateGraph(AlertState)
alert_workflow.add_node("format_alert", format_alert_llm_node)
alert_workflow.add_node("dispatch_slack", dispatch_slack_node)
alert_workflow.set_entry_point("format_alert")
alert_workflow.add_edge("format_alert", "dispatch_slack")
alert_workflow.add_edge("dispatch_slack", END)
smart_alert_agent = alert_workflow.compile()

def _write_alert_log(result: Dict[str, Any]):
    """Gap 3 Fix: Persist every smart alert to alert_logs PostgreSQL table."""
    try:
        from app.db.session import SessionLocal
        from app.models.alert_log import AlertLog, AlertSeverity, AlertStatus

        source = result.get("alert_source", "UNKNOWN")
        severity_map = {
            "DS_RATIO_CRITICAL": AlertSeverity.CRITICAL,
            "DS_RATIO_WARNING":  AlertSeverity.WARNING,
        }
        severity = severity_map.get(source, AlertSeverity.INFO)
        message = (
            f"{result.get('situation_summary', '')} "
            f"Action: {result.get('recommended_action', '')}"
        )[:1000]

        db = SessionLocal()
        try:
            row = AlertLog(
                alert_type=source,
                message=message,
                severity=severity,
                status=AlertStatus.NEW,
            )
            db.add(row)
            db.commit()
            log.info("alert_log_written", alert_type=source, severity=severity)
        except Exception as e:
            db.rollback()
            log.error("alert_log_db_error", error=str(e))
        finally:
            db.close()
    except Exception as e:
        log.error("alert_log_import_error", error=str(e))


def _write_po_draft(raw_context: dict, result: Dict[str, Any]):
    """Gap 2 Fix: Persist PO draft to po_drafts PostgreSQL table with PENDING_APPROVAL status."""
    try:
        from app.db.session import SessionLocal
        from app.models.po_draft import PODraft, POStatus
        from app.models.supplier import Supplier

        sku       = raw_context.get("sku", "UNKNOWN")
        gap_units = int(raw_context.get("gap_units", 500))
        cost_unit = 8.20   # $/unit fallback estimate

        db = SessionLocal()
        try:
            # Find a backup supplier (first available Tier 2, fallback to any)
            backup = (
                db.query(Supplier)
                .filter(Supplier.health_status != "CRITICAL")
                .order_by(Supplier.health_score.desc())
                .first()
            )
            if not backup:
                backup = db.query(Supplier).first()
            if not backup:
                log.warning("po_draft_no_supplier_found", sku=sku)
                return

            row = PODraft(
                supplier_id    = backup.id,
                sku            = sku,
                quantity       = gap_units,
                estimated_cost = round(gap_units * cost_unit, 2),
                status         = POStatus.PENDING_APPROVAL,
                approved_by    = None,
            )
            db.add(row)
            db.commit()
            log.info("po_draft_written", sku=sku, supplier_id=backup.id,
                     quantity=gap_units, status="PENDING_APPROVAL")
        except Exception as e:
            db.rollback()
            log.error("po_draft_db_error", error=str(e))
        finally:
            db.close()
    except Exception as e:
        log.error("po_draft_import_error", error=str(e))


def trigger_smart_alert(alert_source: str, raw_context: dict) -> Dict[str, Any]:
    initial_state = AlertState(
        alert_source=alert_source, raw_context=raw_context,
        situation_summary=None, recommended_action=None, slack_ts=None, status="NEW"
    )
    result = smart_alert_agent.invoke(initial_state)

    # ── Gap 3: Write permanent AlertLog to Postgres ──────────────────────────
    _write_alert_log({**result, "alert_source": alert_source})

    # ── Gap 2: Write PODraft to Postgres (only for D/S ratio alerts) ─────────
    if "DS_RATIO" in alert_source:
        _write_po_draft(raw_context, result)

    return result
