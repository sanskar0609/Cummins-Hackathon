from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.db.session import get_db
from app.services.supply_ratio import calculate_ds_ratio
from app.core.logging import log

router = APIRouter()

@router.get("/ds-ratio", response_model=Dict[str, Any])
async def get_ds_ratio(
    sku: str = Query("SKU-001", description="Product SKU (e.g., SKU-001)"),
    route_id: str = Query("SUEZ-ROTTERDAM", description="Transit route ID (e.g., SUEZ-ROTTERDAM)"),
    db: Session = Depends(get_db)
):
    """
    Returns the Demand/Supply ratio for a given SKU and route.
    Always returns HTTP 200 — when no forecast data exists the ratio is
    computed from generated mock supply values so the gauge still renders.
    """
    try:
        report = calculate_ds_ratio(db, sku, route_id.upper())
        return report
    except Exception as e:
        log.error("ds_ratio_endpoint_error", sku=sku, route=route_id, error=str(e))
        # Return a safe fallback payload so the frontend gauge does not crash
        return {
            "sku":              sku,
            "route_id":         route_id.upper(),
            "30_day_demand":    0.0,
            "in_transit_supply": 0.0,
            "ds_ratio":         0.0,
            "status":           "DATA_UNAVAILABLE",
        }
