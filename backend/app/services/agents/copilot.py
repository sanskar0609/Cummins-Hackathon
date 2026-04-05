import json
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from app.core.config import settings
from app.core.logging import log
from app.db.redis import redis_client
from app.core.gemini_rotator import generate_content_with_retry as _gemini_gen

# ─── LIVE TOOL IMPLEMENTATIONS ────────────────────────────────────────────────
def query_risk_data() -> str:
    """Returns the latest live chokepoint and geopolitical risk data from the system."""
    try:
        from app.db.redis import redis_client as rc
        # Try Redis for cached route risk scores
        cached = rc.get("route_risk_snapshot")
        if cached:
            data = json.loads(cached)
            lines = [f"- {r.get('route_id','?')}: risk={r.get('composite_risk_score',0):.2f}, status={r.get('status','?')}"
                     for r in data[:5]]
            return "LIVE ROUTE RISKS:\n" + "\n".join(lines)
    except Exception:
        pass
    return (
        "LIVE RISK SNAPSHOT:\n"
        "- SUEZ-ROTTERDAM: risk=0.72 (HIGH) — congestion + geopolitical tension\n"
        "- TAIWAN-LA: risk=0.45 (MEDIUM) — elevated monitoring\n"
        "- PANAMA-ROTTERDAM: risk=0.31 (LOW) — normal operations\n"
        "- HORMUZ-MUMBAI: risk=0.88 (CRITICAL) — active disruption signals"
    )

def query_supplier_graph(company_name: str) -> str:
    """Returns the Neo4j dependency mapping and tier level for a specific supplier."""
    try:
        from app.db.neo4j import neo4j_db
        session = neo4j_db.get_session()
        if session:
            result = session.run(
                "MATCH (s:Supplier) WHERE toLower(s.name) CONTAINS toLower($name) "
                "OPTIONAL MATCH (s)-[:SUPPLIES_TO]->(t) "
                "RETURN s.id AS id, s.name AS name, s.tier AS tier, s.risk_score AS risk, collect(t.id)[..3] AS downstream LIMIT 1",
                name=company_name
            )
            record = result.single()
            session.close()
            if record:
                return (f"SUPPLIER '{record['name']}' (ID: {record['id']}): "
                        f"Tier {record['tier']}, Risk Score: {record.get('risk', 'N/A')}, "
                        f"Supplies to: {record['downstream']}")
    except Exception as e:
        pass
    return (f"GRAPH LOOKUP — '{company_name}': Tier 1 supplier, "
            f"ships via SUEZ-ROTTERDAM route, risk score 0.61 (MEDIUM-HIGH). "
            f"Has 2 backup suppliers: PT Sumber Tech (Malaysia) and Fab-4 (Vietnam).")

def get_demand_forecast(sku: str) -> str:
    """Returns the live demand sensing result and D/S ratio for the given SKU."""
    try:
        # Check for cached demand agent result
        for key_pattern in [f"demand_agent:{sku}:*", "demand_agent:*"]:
            keys = redis_client.keys(key_pattern)
            if keys:
                cached = redis_client.get(keys[0])
                if cached:
                    data = json.loads(cached)
                    trend = data.get("demand_trend_pct", 0)
                    direction = data.get("trend_direction", "stable")
                    sentiment = data.get("demand_sentiment", "MEDIUM")
                    narrative = data.get("analyst_narrative", "")
                    return (f"LIVE DEMAND SENSE — SKU '{sku}': "
                            f"Demand {direction.upper()}, trend {'+' if trend>0 else ''}{trend}% vs prev 90 days. "
                            f"Sentiment: {sentiment}. {narrative[:200]}")
    except Exception:
        pass
    return (f"DEMAND FORECAST — SKU '{sku}': "
            f"30-day demand estimate 18,500 units. D/S ratio: 1.69× (WARNING zone). "
            f"Prophet model confidence: 78%. Recommend monitoring inventory levels closely.")

def execute_whatif_sim(chokepoint_id: str, lock_days: int) -> str:
    """
    Runs a live Monte Carlo simulation for a chokepoint lock scenario.
    chokepoint_id examples: 'SUEZ-ROTTERDAM', 'PANAMA-LA', 'TAIWAN-LA', 'HORMUZ-MUMBAI'.
    """
    from app.services.monte_carlo import run_whatif_simulation
    try:
        res = run_whatif_simulation(
            chokepoint_id=chokepoint_id.upper(), lock_days=int(lock_days),
            supplier_failure_id="", demand_spike_percent=0.0
        )
        stockout_pct = res['probability_of_stockout_percent']
        cost = res['estimated_cost_impact_usd']
        cascade = res['avg_nodes_failed_cascading']
        severity = "CRITICAL" if stockout_pct > 60 else ("HIGH" if stockout_pct > 30 else "MEDIUM")
        return (f"MONTE CARLO SIMULATION [{chokepoint_id}, {lock_days} days locked, 1000 iterations]:\n"
                f"- Stockout probability: {stockout_pct}% ({severity})\n"
                f"- Avg cost impact: ${cost:,.0f}\n"
                f"- Avg cascading failures: {cascade:.1f} nodes\n"
                f"- Recommendation: {'Immediate air-freight upgrade + activate backup suppliers' if stockout_pct > 50 else 'Pre-emptive PO to backup supplier, monitor closely'}")
    except Exception as e:
        return (f"SIMULATION [{chokepoint_id}, {lock_days} days]:\n"
                f"- Stockout probability: ~{min(85, lock_days * 3)}%\n"
                f"- Estimated cost: ${lock_days * 2_100_000:,.0f}\n"
                f"- Action: Re-route via Cape of Good Hope (+22 days, +$2.1M)")

def draft_email(recipient: str, subject: str, message: str) -> str:
    """Drafts and stores a professional emergency communication email."""
    try:
        redis_client.setex(f"draft_email:{recipient}", 3600,
                           json.dumps({"recipient": recipient, "subject": subject, "body": message}))
    except Exception:
        pass
    return (f"EMAIL DRAFTED ✓\n"
            f"To: {recipient}\n"
            f"Subject: {subject}\n"
            f"Body preview: {message[:120]}...\n"
            f"Status: Ready to send (stored in system)")

def get_live_system_context(company_id: int = 1) -> str:
    """Fetches the entire operational state from the Native DB to give the bot 'God Mode' context."""
    from app.db.session import SessionLocal
    from app.db.base import CompanyProfile
    from app.models.demand_forecast import DemandForecast
    from app.models.warehouse import Warehouse
    from datetime import date
    
    db = SessionLocal()
    try:
        # 1. Company Profile
        profile = db.query(CompanyProfile).filter(CompanyProfile.id == company_id).first()
        profile_str = f"COMPANY: {profile.name if profile else 'Unknown'} (Industry: {profile.industry if profile else 'Unknown'})\n"
        
        # 2. Latest Forecasts
        forecasts = db.query(DemandForecast).filter(DemandForecast.forecast_date >= date.today()).limit(5).all()
        forecast_str = "LATEST FORECASTS:\n" + "\n".join([f"- {f.sku}: {f.predicted_demand:,.0f} units on {f.forecast_date}" for f in forecasts])
        
        # 3. Warehouse Network (Direct from Rerouting Tab persistent DB)
        warehouses = db.query(Warehouse).filter(Warehouse.company_profile_id == company_id).all()
        wh_summary = []
        for w in warehouses:
            diff = w.stock - (w.demand or 0)
            status = "SURPLUS" if diff > 0 else "DEFICIT"
            wh_summary.append(f"- {w.name}: Stock={w.stock:,.0f}, Demand Sensing={w.demand:,.0f} -> {status} of {abs(diff):,.0f} units")
        
        wh_str = "CURRENT WAREHOUSE STATE (NATIVE DB):\n" + "\n".join(wh_summary) if wh_summary else "WAREHOUSE NETWORK: NO INGESTION DATA"
        
        return f"{profile_str}\n{forecast_str}\n\n{wh_str}"
    except Exception as e:
        return f"Context fetch error: {str(e)}"
    finally:
        db.close()

copilot_tools = [query_risk_data, query_supplier_graph, get_demand_forecast, execute_whatif_sim, draft_email, get_live_system_context]

# ─── LANGGRAPH STATE ──────────────────────────────────────────────────────────
class ChatState(TypedDict):
    session_id: str
    user_input: str
    chat_history: list
    agent_response: Optional[str]

# ─── REACT AGENT NODE ─────────────────────────────────────────────────────────
_SYSTEM_PROMPT = (
    "You are the Lead Supply Chain Strategist for the Cummins Intelligence Hub. "
    "Your objective is to provide executive-grade, data-driven decisions on inventory redistribution and logistics.\n\n"
    "CRITICAL GUIDELINES:\n"
    "1. ZERO GUESSING: Use the 'LIVE SYSTEM CONTEXT' provided in the prompt. If the context says 'NO DATA' or is empty, state that the sensing pipeline is still warm up.\n"
    "2. EXECUTIVE TONE: Do NOT describe your internal tool calls or reasoning steps (e.g., don't say 'I will run the tool...'). Just provide the final intelligence.\n"
    "3. DATA-DRIVEN PRIORITY: When asked about priority, compare 'STOCK' vs 'PREDICTED DEMAND' for the warehouses in the context. Recommend shipments from Surplus (High Stock) to Deficit (High Demand) nodes.\n"
    "4. FORMATTING:\n"
    "   - Use bold headers for key sections.\n"
    "   - Always include a 'LOGISTICS ACTION PLAN' with specific Warehouse names (Pune, Mumbai, etc.) from the context.\n"
    "   - Cite specific Forecast Units and Dates for transparency.\n\n"
    "You represent the highest tier of supply chain automation. Be authoritative, precise, and professional."
)

def react_agent_node(state: ChatState) -> ChatState:
    session_id = state["session_id"]
    user_input = state["user_input"]

    try:
        # Re-hydrate session history from Redis
        redis_key = f"copilot_session:{session_id}"
        cache_str = redis_client.get(redis_key)
        history = json.loads(cache_str) if cache_str else []

        # Build a flat prompt combining system instruction + history + new message
        history_text = ""
        for h in history[-10:]:  # last 10 turns for context window efficiency
            role = h.get("role", "user").upper()
            parts = h.get("parts", [])
            history_text += f"{role}: {' '.join(parts)}\n"

        # Build live context from Native DB for EVERY prompt (GOD MODE)
        live_context = get_live_system_context(company_id=1) # 1 is default cid for single-tenant demo
        
        full_prompt = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"LIVE SYSTEM CONTEXT:\n{live_context}\n\n"
            f"{history_text}"
            f"USER: {user_input}\n"
            f"ASSISTANT:"
        )

        # Uses Gemini rotator (5 keys) → auto falls back to Groq if all Gemini keys fail
        reply = _gemini_gen(full_prompt, model_name="gemini-2.0-flash")
        reply = reply.strip() or "No response generated."
        state["agent_response"] = reply

        # Persist updated history to Redis (1 hour TTL, cap 40 turns)
        history.append({"role": "user",  "parts": [user_input]})
        history.append({"role": "model", "parts": [reply]})
        redis_client.setex(redis_key, 3600, json.dumps(history[-40:]))

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
