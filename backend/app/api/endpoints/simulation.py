from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from app.services.monte_carlo import run_whatif_simulation
from app.core.logging import log

router = APIRouter()

class WhatIfSimRequest(BaseModel):
    chokepoint_id: Optional[str] = Field(None, description="E.g., SUEZ-ROTTERDAM")
    lock_days: int = Field(0, description="Number of days the exact chokepoint is physically locked out")
    supplier_failure_id: Optional[str] = Field(None, description="Direct supplier ID triggering massive disruption (e.g., SUP-T3-B)")
    demand_spike_percent: float = Field(0.0, description="Spike percentage in global physical demand")

@router.post("/whatif", response_model=Dict[str, Any])
async def generate_whatif_simulation(
    payload: WhatIfSimRequest
):
    """
    Executes a heavy mathematical 1000-pass Monte Carlo evaluation directly iterating the active Neo4j matrix.
    Safely triggers simulated shocks natively to produce cascading node failure probability outputs dynamically.
    """
    log.info("triggering_monte_carlo", args=payload.model_dump())
    
    try:
        results = run_whatif_simulation(
            chokepoint_id=payload.chokepoint_id or "",
            lock_days=payload.lock_days,
            supplier_failure_id=payload.supplier_failure_id or "",
            demand_spike_percent=payload.demand_spike_percent
        )
        return results
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        log.error("monte_carlo_fatal_error", error=str(e))
        raise HTTPException(status_code=500, detail="Monte Carlo Engine encountered an unexpected exception.")
