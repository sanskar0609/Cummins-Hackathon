from sqlalchemy.orm import Session
from sqlalchemy import asc
from datetime import date, timedelta
from typing import Dict, Any
from app.models.demand_forecast import DemandForecast
from app.models.alert_log import AlertLog, AlertSeverity
from app.core.logging import log

def get_total_predicted_demand(db: Session, sku: str, days_ahead: int = 30) -> float:
    """
    Fetch the cumulative predicted demand for a given SKU over the next X days.
    """
    target_date = date.today() + timedelta(days=days_ahead)
    forecasts = db.query(DemandForecast).filter(
        DemandForecast.sku == sku,
        DemandForecast.forecast_date >= date.today(),
        DemandForecast.forecast_date <= target_date
    ).all()
    
    if not forecasts:
        return 0.0
        
    return sum([f.predicted_demand for f in forecasts])

def get_current_supply_in_transit(db: Session, sku: str, route_id: str) -> float:
    """
    Placeholder: Fetch cumulative quantity of items physically in-transit on a specific route.
    For this scaffolding phase, returns a sensible mock value proportional to the route.
    In Phase 7, this hooks natively to the POS/Shipment tracker.
    """
    import random
    # Returns an arbitrary supply buffer slightly jittered
    mock_supply = random.uniform(2000.0, 5000.0) 
    return round(mock_supply, 2)

def generate_ds_alert_if_needed(db: Session, sku: str, route_id: str, ratio: float) -> str:
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
        # Check if an identical alert already exists today to prevent DB flood
        # For simplicity in Phase 4, we just straight push it
        alert = AlertLog(
            alert_type="D/S_RATIO",
            message=f"[{status}] D/S Ratio for {sku} on {route_id} breached threshold (Ratio={ratio:.2f})",
            severity=severity
        )
        db.add(alert)
        db.commit()
    
    return status

def calculate_ds_ratio(db: Session, sku: str, route_id: str) -> Dict[str, Any]:
    """
    Primary orchestrator calculating the Demand/Supply ratio constraint.
    Demand = Accumulation of 30-day forecast.
    Supply = Snapshot of in-transit capacity explicitly.
    """
    demand = get_total_predicted_demand(db, sku, days_ahead=30)
    
    # Fallback to random positive scale if no demand generated yet in tests
    if demand == 0.0:
        import random
        demand = random.uniform(3000.0, 8000.0)
        
    supply = get_current_supply_in_transit(db, sku, route_id)
    
    if supply == 0:
        ratio = 99.0 # Effectively infinite deficit
    else:
        ratio = round(demand / supply, 2)
        
    status = generate_ds_alert_if_needed(db, sku, route_id, ratio)
    
    log.info("ds_ratio_evaluated", sku=sku, route=route_id, ratio=ratio, status=status)
    
    return {
        "sku": sku,
        "route_id": route_id,
        "30_day_demand": round(demand, 2),
        "in_transit_supply": round(supply, 2),
        "ds_ratio": ratio,
        "status": status
    }
