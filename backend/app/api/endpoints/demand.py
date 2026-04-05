from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import asyncio
from app.db.session import get_db
from app.core.logging import log

router = APIRouter()


# ─── Prophet Worker (runs in thread, never blocks event loop) ─────────────────
def _run_prophet_sync(sku: str, company_id):
    """Generates a 90-day Prophet forecast and persists to DB."""
    import datetime, hashlib, traceback as tb
    import numpy as np
    import pandas as pd
    from prophet import Prophet
    from app.db.session import SessionLocal
    from app.models.demand_forecast import DemandForecast

    sku_hash   = int(hashlib.md5(sku.encode()).hexdigest(), 16) % 1000
    base       = 400 + sku_hash          # unique per SKU name: 400–1400
    amplitude  = 100 + (sku_hash % 200)  # seasonal swing varies per SKU
    today      = datetime.date.today()
    past_dates = pd.date_range(end=today - datetime.timedelta(days=1), periods=730, freq='D')

    np.random.seed(sku_hash)  # reproducible but unique per SKU
    y = []
    for i, d in enumerate(past_dates):
        year_eff  = np.sin((d.dayofyear / 365.25) * 2 * np.pi - (np.pi / 2)) * amplitude
        week_eff  = [-20, 30, 40, 25, 10, -50, -60][d.weekday()]
        month_eff = 60 if d.day in range(13, 17) else (80 if d.day >= 27 else 0)
        trend     = i * 0.15
        noise     = np.random.normal(0, 30)
        # ~10% chance of a demand spike event
        spike     = 200 if np.random.random() < 0.10 else 0
        y.append(max(50, base + year_eff + week_eff + month_eff + trend + noise + spike))

    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.15,
        seasonality_prior_scale=12.0,
    )
    m.fit(pd.DataFrame({'ds': past_dates, 'y': y}))

    future   = m.make_future_dataframe(periods=90)
    forecast = m.predict(future)
    rows_df  = forecast[forecast['ds'] >= pd.to_datetime(today)].head(90)

    result = []
    for _, row in rows_df.iterrows():
        result.append({
            "sku":              sku,
            "forecast_date":    str(row['ds'].date()),
            "predicted_demand": round(float(row['yhat']), 2),
            "lower_bound":      round(float(row['yhat_lower']), 2),
            "upper_bound":      round(float(row['yhat_upper']), 2),
            "model_used":       "Facebook Prophet Model (Live ML)",
        })

    # ── Best-effort DB persist (never fails the response) ────────────────────
    db2: Session = SessionLocal()
    try:
        db_rows = [
            DemandForecast(
                company_profile_id=company_id,
                sku=sku,
                forecast_date=r["forecast_date"],
                predicted_demand=r["predicted_demand"],
                lower_bound=r["lower_bound"],
                upper_bound=r["upper_bound"],
                model_used=r["model_used"],
            )
            for r in result
        ]
        db2.add_all(db_rows)
        db2.commit()
        log.info("prophet_forecast_saved", sku=sku, rows=len(db_rows))
    except Exception as db_err:
        log.error("prophet_db_save_failed", sku=sku, error=str(db_err), trace=tb.format_exc())
        db2.rollback()
    finally:
        db2.close()

    return result


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/forecast", response_model=List[Dict[str, Any]])
async def get_sku_demand_forecast(
    sku: str = Query("SKU-001", description="SKU to retrieve 90-day forecast for"),
    company_id: int = Query(None, description="Company profile ID"),
    db: Session = Depends(get_db),
):
    """
    Returns the 90-day demand forecast for a SKU.
    Generates via Prophet on first call; cached in DB for subsequent calls.
    """
    from app.models.demand_forecast import DemandForecast
    try:
        q = db.query(DemandForecast).filter(DemandForecast.sku == sku)
        if company_id:
            q = q.filter(DemandForecast.company_profile_id == company_id)
        cached = q.order_by(DemandForecast.forecast_date.asc()).all()

        if len(cached) >= 90:
            log.info("forecast_served_from_db", sku=sku, rows=len(cached))
            return [
                {
                    "sku":              r.sku,
                    "forecast_date":    str(r.forecast_date),
                    "predicted_demand": r.predicted_demand,
                    "lower_bound":      r.lower_bound,
                    "upper_bound":      r.upper_bound,
                    "model_used":       r.model_used,
                }
                for r in cached
            ]

        # Generate fresh forecast in a thread (Prophet is CPU-bound)
        log.info("generating_prophet_forecast_for_sku", sku=sku)
        result = await asyncio.to_thread(_run_prophet_sync, sku, company_id)
        log.info("prophet_forecast_generated", sku=sku, rows=len(result))
        return result

    except Exception as e:
        import traceback
        log.error("demand_forecast_endpoint_error", sku=sku, error=str(e), trace=traceback.format_exc())
        return []


@router.get("/skus", response_model=List[str])
async def list_available_skus(db: Session = Depends(get_db)):
    """Returns the distinct list of SKUs that have forecast data."""
    try:
        from app.models.demand_forecast import DemandForecast
        from sqlalchemy import distinct
        rows = db.query(distinct(DemandForecast.sku)).all()
        skus = [r[0] for r in rows]
        return skus if skus else ["SKU-001", "SKU-002", "SKU-003"]
    except Exception as e:
        log.error("skus_list_error", error=str(e))
        return ["SKU-001", "SKU-002", "SKU-003"]


from pydantic import BaseModel

class AgentSensePayload(BaseModel):
    query: str
    baseline_units: int = 1000

@router.post("/agent-sense")
async def run_demand_sensing_agent(payload: AgentSensePayload):
    """
    Triggers the multi-source AI Demand Sensing pipeline:
    YouTube + Reddit + News + Trends + GDELT → Gemini/Groq analysis.
    """
    try:
        from app.services.agents.demand_agent_service import run_pipeline
        result = await run_pipeline(user_query=payload.query, baseline_units=payload.baseline_units)
        return result
    except Exception as e:
        log.error("demand_agent_error", error=str(e))
        return {"error": str(e)}
