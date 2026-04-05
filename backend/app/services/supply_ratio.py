from sqlalchemy.orm import Session
from sqlalchemy import asc
from datetime import date, timedelta
from typing import Dict, Any
from app.models.demand_forecast import DemandForecast
from app.models.alert_log import AlertLog, AlertSeverity
from app.core.logging import log

def get_total_predicted_demand(db: Session, sku: str, days_ahead: int = 30, company_id: int = None) -> float:
    """
    Fetch the cumulative predicted demand for a given SKU over the next X days.
    """
    target_date = date.today() + timedelta(days=days_ahead)
    query = db.query(DemandForecast).filter(
        DemandForecast.sku == sku,
        DemandForecast.forecast_date >= date.today(),
        DemandForecast.forecast_date <= target_date
    )
    if company_id:
        query = query.filter(DemandForecast.company_profile_id == company_id)
        
    forecasts = query.all()
    
    if not forecasts:
        return 0.0
        
    return sum([f.predicted_demand for f in forecasts])

def get_current_supply_in_transit(db: Session, sku: str, route_id: str, company_id: int = None) -> float:
    """Fetches real-time supply from Redis (network state) or returns 0.0 for live data integrity."""
    from app.db.redis import redis_client
    try:
        cid = company_id or 1
        cached = redis_client.get(f"network_supply:{cid}")
        if cached:
            return float(cached)
    except Exception:
        log.error("redis_supply_fetch_failed", sku=sku)
    return 0.0

def generate_ds_alert_if_needed(db: Session, sku: str, route_id: str, ratio: float, company_id: int = None) -> str:
    """
    Evaluates the ratio thresholds. If anomalous, saves an AlertLog natively.
    Returns the string text status.
    """
    status = "OK"
    severity = AlertSeverity.INFO
    
    if ratio > 2.0:
        status = "CRITICAL"
        severity = AlertSeverity.CRITICAL
    elif ratio > 1.5:
        status = "WARNING"
        severity = AlertSeverity.WARNING
        
    if severity != AlertSeverity.INFO:
        alert = AlertLog(
            company_profile_id=company_id,
            alert_type="D/S_RATIO",
            message=f"[{status}] D/S Ratio for {sku} on {route_id} breached threshold (Ratio={ratio:.2f})",
            severity=severity
        )
        db.add(alert)
        db.commit()
    
    return status

def calculate_ds_ratio(db: Session, sku: str, route_id: str, company_id: int = None) -> Dict[str, Any]:
    """
    Primary orchestrator calculating the Demand/Supply ratio from LIVE data sources.
    No mock fallbacks.
    """
    demand = get_total_predicted_demand(db, sku, days_ahead=30, company_id=company_id)
    supply = get_current_supply_in_transit(db, sku, route_id, company_id)
    
    if demand == 0:
        return {
            "company_id": company_id,
            "sku": sku,
            "route_id": route_id,
            "30_day_demand": 0.0,
            "in_transit_supply": round(supply, 2),
            "ds_ratio": 0.0,
            "status": "NO_DEMAND"
        }

    if supply == 0:
        ratio = 99.0 # Infinity gap
    else:
        ratio = round(demand / supply, 2)
        
    status = generate_ds_alert_if_needed(db, sku, route_id, ratio, company_id)
    
    log.info("ds_ratio_evaluated", sku=sku, route=route_id, ratio=ratio, status=status)
    
    return {
        "company_id": company_id,
        "sku": sku,
        "route_id": route_id,
        "30_day_demand": round(demand, 2),
        "in_transit_supply": round(supply, 2),
        "ds_ratio": ratio,
        "status": status
    }
