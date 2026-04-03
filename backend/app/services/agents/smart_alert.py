import json
from google import genai
from google.genai import types
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Dict, Any
from app.core.config import settings
from app.core.logging import log

_client = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None

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

    if not _client:
        state["situation_summary"] = "Gemini API key not configured."
        state["recommended_action"] = "Configure GEMINI_API_KEY in .env."
        state["status"] = "ERROR"
        return state

    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        payload = json.loads(response.text)
        state["situation_summary"] = payload.get("situation_summary", "Critical threshold breached.")
        state["recommended_action"] = payload.get("recommended_action", "Review dashboard.")
        state["status"] = "FORMATTED"
    except Exception as e:
        log.error("gemini_alert_format_error", error=str(e))
        state["situation_summary"] = "Error parsing context via AI core."
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

def trigger_smart_alert(alert_source: str, raw_context: dict) -> Dict[str, Any]:
    initial_state = AlertState(
        alert_source=alert_source, raw_context=raw_context,
        situation_summary=None, recommended_action=None, slack_ts=None, status="NEW"
    )
    return smart_alert_agent.invoke(initial_state)
