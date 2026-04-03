from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from app.db.neo4j import neo4j_db
from app.core.logging import log

router = APIRouter()

@router.get("/graph", response_model=Dict[str, List[Dict[str, Any]]])
async def get_supplier_graph():
    """
    Returns the complete supply chain n-tier dependency graph extracted directly from Neo4j.
    Structured perfectly compatible with cytoscape.js for frontend tree rendering.
    """
    session = neo4j_db.get_session()
    if not session:
        raise HTTPException(status_code=503, detail="Neo4j Graph Database is currently unreachable.")
        
    try:
        nodes = []
        edges = []
        
        # 1. Fetch distinct nodes
        nodes_result = session.run("MATCH (n) RETURN n, labels(n) AS labels")
        for record in nodes_result:
            node = record["n"]
            labels = record["labels"]
            
            # Map native neo4j properties into the flat cytoscape standard `data` dictionary
            data_props = dict(node.items())
            data_props['type'] = labels[0] if labels else 'Unknown'
            # Cytoscape requires a strictly unique 'id' key natively mapped. We'll use the domain ID or internal element_id.
            data_props['id'] = node.get("id", str(node.element_id))
            
            nodes.append({"data": data_props})

        # 2. Fetch distinct relationships
        rels_result = session.run("""
            MATCH (source)-[r]->(target) 
            RETURN r, type(r) as r_type, source, target
        """)
        for record in rels_result:
            r = record["r"]
            r_type = record["r_type"]
            source = record["source"]
            target = record["target"]
            
            source_id = source.get("id", str(source.element_id))
            target_id = target.get("id", str(target.element_id))
            
            edge_data = dict(r.items())
            edge_data['id'] = f"{source_id}-{r_type}-{target_id}"
            edge_data['source'] = source_id
            edge_data['target'] = target_id
            edge_data['label'] = r_type
            
            edges.append({"data": edge_data})
            
        log.info("supplier_graph_extracted", total_nodes=len(nodes), total_edges=len(edges))
        return {
            "nodes": nodes,
            "edges": edges
        }
        
    except Exception as e:
        log.error("neo4j_extraction_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to construct Cytoscape payload from Graph DB.")
    finally:
        session.close()

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.session import get_db
from app.models.health_signal import SupplierHealthSignal
from app.services.health_monitor import gather_and_save_health_signals

@router.get("/{supplier_id}/health", response_model=Dict[str, Any])
async def get_supplier_health(
    supplier_id: str,
    company_name: str,
    domain: str = "",
    force_refresh: bool = False,
    db: Session = Depends(get_db)
):
    """
    Exposes explicit corporate OSINT evaluations harvested from 
    Hunter (Email Activity), NewsAPI (Sentiment Flagging), and RapidAPI (Finance).
    """
    if not force_refresh:
        # Check DB for existing signals
        signal = db.query(SupplierHealthSignal).filter(
            SupplierHealthSignal.supplier_id == supplier_id
        ).order_by(desc(SupplierHealthSignal.created_at)).first()
        
        if signal:
            return {
                "supplier_id": signal.supplier_id,
                "hunter_data": signal.hunter_data,
                "news_data": signal.news_data,
                "rapidapi_data": signal.rapidapi_data,
                "last_updated": signal.created_at.isoformat()
            }
            
    # Harvest dynamically if none existed globally or manually refreshed
    try:
        new_signal = await gather_and_save_health_signals(db, supplier_id, company_name, domain)
        return {
            "supplier_id": new_signal.supplier_id,
            "hunter_data": new_signal.hunter_data,
            "news_data": new_signal.news_data,
            "rapidapi_data": new_signal.rapidapi_data,
            "last_updated": new_signal.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from app.services.agents.narrative_generator import generate_health_narrative

@router.post("/{supplier_id}/narrative", response_model=Dict[str, Any])
async def create_supplier_narrative(
    supplier_id: str,
    company_name: str,
    db: Session = Depends(get_db)
):
    """
    Executes a LangGraph Native node dynamically compiling operational backend intelligence 
    (Hunter, NewsAPI, RapidAPI) into a direct 3-4 sentence plain-English risk narrative 
    via Gemini 2.5 Flash constraints.
    """
    # Grab latest signals natively from DB
    signal = db.query(SupplierHealthSignal).filter(
        SupplierHealthSignal.supplier_id == supplier_id
    ).order_by(desc(SupplierHealthSignal.created_at)).first()
    
    if not signal:
        raise HTTPException(status_code=404, detail="No health signals found. Please hit the GET /health endpoint first to retrieve OSINT matrices prior to narrative generation.")
        
    full_health_data = {
        "hunter_emails_and_activity": signal.hunter_data,
        "news_sentiment_flags": signal.news_data,
        "rapidapi_financials": signal.rapidapi_data
    }
    
    try:
        # LangGraph invoke
        result = generate_health_narrative(supplier_id, company_name, full_health_data)
        return {
            "supplier_id": supplier_id,
            "company_name": company_name,
            "narrative": result["narrative"],
            "confidence_rating": result["confidence_rating"],
            "llm_model_used": "gemini-2.5-flash"
        }
    except Exception as e:
        log.error("narrative_agent_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"LLM AI generation failed: {str(e)}")
