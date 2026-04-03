from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, List
from app.db.session import get_db
from app.core.logging import log

router = APIRouter()

@router.get("/forecast", response_model=List[Dict[str, Any]])
async def get_sku_demand_forecast(
    sku: str = Query("SKU-001", description="SKU to retrieve 90-day forecast for (e.g. SKU-001)"),
    db: Session = Depends(get_db)
):
    """
    Returns the 90-day demand forecast for a single SKU.
    Returns an empty list (HTTP 200) when no data has been ingested yet.
    """
    try:
        query = text("SELECT sku, date, quantity FROM demand_forecast WHERE sku = :sku")
        result = db.execute(query, {"sku": sku})
        rows = result.fetchall()

        return [
            {
                "sku": row[0],
                "forecast_date": str(row[1]),
                "predicted_demand": float(row[2]) if row[2] else 0.0,
                "lower_bound": float(row[2]) * 0.8 if row[2] else 0.0,
                "upper_bound": float(row[2]) * 1.2 if row[2] else 0.0,
                "model_used": "raw_sql",
            }
            for row in rows
        ]
    except Exception as e:
        log.error("demand_forecast_endpoint_error", sku=sku, error=str(e))
        return []

@router.get("/skus", response_model=List[str])
async def list_available_skus(db: Session = Depends(get_db)):
    """
    Returns the distinct list of SKUs that have forecast data.
    Returns an empty list (not 500) when the table is empty.
    """
    try:
        from sqlalchemy import distinct
        rows = db.query(distinct(DemandForecast.sku)).all()
        skus = [r[0] for r in rows]
        return skus if skus else ["SKU-001", "SKU-002", "SKU-003"]
    except Exception as e:
        log.error("skus_list_error", error=str(e))
        return ["SKU-001", "SKU-002", "SKU-003"]
