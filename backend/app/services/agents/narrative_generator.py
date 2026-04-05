import json
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Dict
from app.core.config import settings
from app.core.logging import log
from app.core.gemini_rotator import generate_content_with_retry as _gemini_gen

class NarrativeState(TypedDict):
    supplier_id: str
    company_name: str
    health_data: dict
    narrative: Optional[str]
    confidence_rating: Optional[str]

def generate_narrative_node(state: NarrativeState) -> NarrativeState:
    """
    Core LLM Node targeting gemini-2.5-flash.
    Ingests OSINT JSON records and outputs a plain-English risk summary.
    """
    log.info("generating_narrative", supplier=state["company_name"])

    prompt = f"""
    You are an expert Supply Chain Risk Analyst working in a mission-critical operations center.
    Analyze the following operational health signals for supplier '{state['company_name']}' (ID: {state['supplier_id']}).

    Data Context (Hunter.io + NewsAPI Sentiment + RapidAPI Finance):
    {json.dumps(state['health_data'], indent=2)}

    REQUIREMENTS:
    1. Write exactly 3-4 sentences summarizing operational status, focusing on negative sentiment,
       financial instability, or operational risks (layoffs, strikes, etc.).
       If data is empty, state that explicitly.
    2. Provide a Confidence Rating: HIGH, MEDIUM, or LOW — scaled to the amount of context provided
       (empty/not_found maps => LOW).

    Output STRICTLY as valid JSON with exactly these two keys:
    {{
       "narrative": "...",
       "confidence_rating": "..."
    }}
    """

    try:
        # Gemini rotator (5 keys round-robin) → auto falls back to Groq on full exhaustion
        raw = _gemini_gen(prompt, model_name="gemini-2.0-flash")
        clean = raw.replace("```json", "").replace("```", "").strip()
        payload = json.loads(clean)
        state["narrative"] = payload.get("narrative", "Unable to generate narrative.")
        state["confidence_rating"] = payload.get("confidence_rating", "LOW")
    except json.JSONDecodeError:
        state["narrative"] = raw.strip() if 'raw' in dir() else "Unable to parse AI response."
        state["confidence_rating"] = "LOW"
    except Exception as e:
        log.error("gemini_narrative_error", error=str(e))
        state["narrative"] = "Error executing AI inference."
        state["confidence_rating"] = "ERROR"

    return state

# ─── LANGGRAPH TOPOLOGY ────────────────────────────────────────────────────────
workflow = StateGraph(NarrativeState)
workflow.add_node("generate_narrative", generate_narrative_node)
workflow.set_entry_point("generate_narrative")
workflow.add_edge("generate_narrative", END)
narrative_app = workflow.compile()

def generate_health_narrative(supplier_id: str, company_name: str, health_data: dict) -> Dict[str, str]:
    initial_state = NarrativeState(
        supplier_id=supplier_id,
        company_name=company_name,
        health_data=health_data,
        narrative=None,
        confidence_rating=None
    )
    result = narrative_app.invoke(initial_state)
    return {
        "narrative": result["narrative"],
        "confidence_rating": result["confidence_rating"]
    }
