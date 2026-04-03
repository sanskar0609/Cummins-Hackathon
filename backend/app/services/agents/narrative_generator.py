import json
from google import genai
from google.genai import types
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Dict
from app.core.config import settings
from app.core.logging import log

# Initialise the new google.genai client once
_client = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None

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

    if not _client:
        state["narrative"] = "Gemini API key not configured."
        state["confidence_rating"] = "LOW"
        return state

    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        payload = json.loads(response.text)
        state["narrative"] = payload.get("narrative", "Unable to generate narrative.")
        state["confidence_rating"] = payload.get("confidence_rating", "LOW")
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
