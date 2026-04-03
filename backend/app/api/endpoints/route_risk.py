from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any
from app.services.ml_lstm_route import predict_route_risk
from app.core.logging import log

router = APIRouter()

@router.get("/route", response_model=Dict[str, Any])
async def get_route_risk(
    route_id: str = Query(..., description="The shipping lane or flight route to inspect (e.g., SUEZ-ROTTERDAM)")
):
    """
    Exposes the PyTorch LSTM neural network predicting cumulative risk transit probabilities.
    Features internally ingested include live AIS congestion, NLP Geo Risk, weather anomalies, and backtested disruptions.
    """
    try:
        score = predict_route_risk(route_id.upper())
        
        # Add discrete textual classification maps simply for UI consumption
        status = "LOW"
        if score > 30: status = "MEDIUM"
        if score > 60: status = "HIGH"
        if score > 80: status = "CRITICAL"
        
        log.info("route_risk_calculated", route=route_id, lstm_score=score, status=status)
        
        return {
            "route_id": route_id.upper(),
            "route_risk_score_0_100": score,
            "overall_status": status,
            "backend_model": "PyTorch_LSTM_v1"
        }
    except Exception as e:
        log.error("route_lstm_failed", route=route_id, error=str(e))
        raise HTTPException(status_code=500, detail="PyTorch LSTM inference encountered an error.")
