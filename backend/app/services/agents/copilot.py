import json
from google import genai
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from app.core.config import settings
from app.core.logging import log
from app.db.redis import redis_client

# ─── NATIVE TOOLS ─────────────────────────────────────────────────────────────
def query_risk_data() -> str:
    """Returns the latest chokepoint and geo-political risk data."""
    return "Suez Canal: HIGH risk (60% congestion). Taiwan Strait: LOW risk. Panama Canal: MEDIUM."

def query_supplier_graph(company_name: str) -> str:
    """Returns the dependency mapping and tier level for a specific supplier by name."""
    return f"Graph Lookup: '{company_name}' is a Tier 1 supplier supplying the OEM via the 'Taiwan Strait Express' AirFreight route."

def get_demand_forecast(sku: str) -> str:
    """Returns the 30-day projected demand for the given SKU."""
    return f"Demand Forecast: '{sku}' requires 15,000 units over the next 30 days."

def execute_whatif_sim(chokepoint_id: str, lock_days: int) -> str:
    """
    Runs a Monte Carlo simulation for a chokepoint lock scenario.
    chokepoint_id examples: 'SUEZ-ROTTERDAM', 'PANAMA-LA', 'TAIWAN-LA'.
    """
    from app.services.monte_carlo import run_whatif_simulation
    try:
        res = run_whatif_simulation(
            chokepoint_id=chokepoint_id, lock_days=lock_days,
            supplier_failure_id="", demand_spike_percent=0.0
        )
        return (f"SIMULATION: {res['probability_of_stockout_percent']}% stockout risk. "
                f"Avg cost impact: ${res['estimated_cost_impact_usd']:,.2f}")
    except Exception as e:
        return f"Simulation failed: {str(e)}"

def draft_email(recipient: str, subject: str, message: str) -> str:
    """Drafts an emergency communication email to the given recipient."""
    return f"Email drafted to {recipient} — Subject: '{subject}'."

copilot_tools = [query_risk_data, query_supplier_graph, get_demand_forecast, execute_whatif_sim, draft_email]

# ─── LANGGRAPH STATE ──────────────────────────────────────────────────────────
class ChatState(TypedDict):
    session_id: str
    user_input: str
    chat_history: list
    agent_response: Optional[str]

# ─── REACT AGENT NODE ─────────────────────────────────────────────────────────
def react_agent_node(state: ChatState) -> ChatState:
    session_id = state["session_id"]
    user_input = state["user_input"]

    if not settings.GEMINI_API_KEY:
        state["agent_response"] = "Gemini API key not configured. Add GEMINI_API_KEY to .env."
        return state

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Re-hydrate session history from Redis
        redis_key = f"copilot_session:{session_id}"
        cache_str = redis_client.get(redis_key)
        history = json.loads(cache_str) if cache_str else []

        # Build content list: history messages + current user message
        contents = []
        for h in history:
            contents.append({"role": h["role"], "parts": [{"text": p} for p in h.get("parts", [])]})
        contents.append({"role": "user", "parts": [{"text": user_input}]})

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=genai.types.GenerateContentConfig(
                tools=copilot_tools,
                system_instruction=(
                    "You are the AI Co-Pilot for Supply Chain Intelligence OS. "
                    "Help the manager by calling tools to check risk data, run simulations, "
                    "forecast demand, and draft emails. Be concise and professional."
                )
            )
        )

        reply = response.text or "No response generated."
        state["agent_response"] = reply

        # Persist updated history to Redis (1 hour TTL)
        history.append({"role": "user",  "parts": [user_input]})
        history.append({"role": "model", "parts": [reply]})
        redis_client.setex(redis_key, 3600, json.dumps(history[-40:]))  # cap at 40 turns; setex(name, seconds, value)

    except Exception as e:
        log.error("copilot_agent_error", error=str(e))
        state["agent_response"] = f"Agent error: {str(e)}"

    return state

# ─── TOPOLOGY ─────────────────────────────────────────────────────────────────
workflow = StateGraph(ChatState)
workflow.add_node("agent", react_agent_node)
workflow.set_entry_point("agent")
workflow.add_edge("agent", END)
copilot_agent = workflow.compile()

def invoke_copilot(session_id: str, user_message: str) -> str:
    initial_state = ChatState(
        session_id=session_id, user_input=user_message,
        chat_history=[], agent_response=None
    )
    result = copilot_agent.invoke(initial_state)
    return result.get("agent_response", "No response generated.")
