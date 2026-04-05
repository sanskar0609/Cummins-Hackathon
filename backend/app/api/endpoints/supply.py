import asyncio
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.db.session import get_db
from app.services.supply_ratio import calculate_ds_ratio
from app.core.logging import log

router = APIRouter()

# ─── Agentic Loop: fire-and-forget alert when D/S crosses threshold ──────────
def _maybe_trigger_agentic_loop(report: Dict[str, Any]):
    """
    If D/S ratio > 1.5×, run the full smart-alert agentic loop:
    Detect → Draft PO summary → Dispatch Slack (or mock).
    Non-blocking: runs in background so the D/S response is instant.
    """
    ratio = report.get("ds_ratio", 0)
    if ratio <= 1.5:
        return

    try:
        from app.services.agents.smart_alert import trigger_smart_alert
        from app.db.redis import redis_client

        company_id = report.get("company_id", "0")
        sku        = report.get("sku", "UNKNOWN")
        route      = report.get("route_id", "UNKNOWN")
        demand_30d = report.get("30_day_demand", 0)
        supply     = report.get("in_transit_supply", 0)
        gap_units  = round(demand_30d - supply)
        severity   = "CRITICAL" if ratio > 2.0 else "WARNING"

        # Rate-limit: only one alert per SKU per 30 minutes
        rate_key = f"alert_sent:{company_id}:{sku}:{route}"
        if redis_client.get(rate_key):
            log.info("agentic_loop_skipped_rate_limit", sku=sku, ratio=ratio)
            return
        redis_client.setex(rate_key, 1800, "1")   # 30-min cooldown

        log.info("agentic_loop_triggered", sku=sku, ratio=ratio, severity=severity)

        alert_result = trigger_smart_alert(
            alert_source=f"DS_RATIO_{severity}",
            raw_context={
                "sku":               sku,
                "route_id":          route,
                "ds_ratio":          ratio,
                "30_day_demand":     demand_30d,
                "in_transit_supply": supply,
                "gap_units":         gap_units,
                "severity":          severity,
                "action_proposed":   (
                    f"Emergency PO to backup supplier — {gap_units:,} units needed. "
                    f"Est. cost ~${gap_units * 8.20:,.0f}. "
                    f"Cost of inaction (stockout): ~${gap_units * 28:,.0f} lost revenue."
                ),
                "details": (
                    f"SKU {sku} on route {route} has D/S ratio of {ratio:.2f}×. "
                    f"30-day demand: {demand_30d:,.0f} units. "
                    f"In-transit supply: {supply:,.0f} units. "
                    f"Gap: {gap_units:,} units."
                )
            }
        )

        # Cache the alert result for Alerts page to pick up
        redis_client.setex(
            f"agentic_po_draft:{company_id}:{sku}",
            3600,
            __import__("json").dumps({
                "sku":         sku,
                "route":       route,
                "ratio":       ratio,
                "severity":    severity,
                "gap_units":   gap_units,
                "summary":     alert_result.get("situation_summary", ""),
                "action":      alert_result.get("recommended_action", ""),
                "slack_status": alert_result.get("status", "MOCKED_EXECUTION"),
                "triggered_at": __import__("datetime").datetime.utcnow().isoformat(),
            })
        )
        log.info("agentic_loop_complete", sku=sku, status=alert_result.get("status"))

    except Exception as e:
        log.error("agentic_loop_error", error=str(e))


@router.get("/ds-ratio", response_model=Dict[str, Any])
async def get_ds_ratio(
    sku: str = Query("SKU-001", description="Product SKU (e.g., SKU-001)"),
    route_id: str = Query("SUEZ-ROTTERDAM", description="Transit route ID (e.g., SUEZ-ROTTERDAM)"),
    company_id: int = Query(None, description="Company DB ID"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Returns the Demand/Supply ratio for a given SKU and route.
    When ratio > 1.5×, automatically triggers the autonomous agentic loop
    (Detect → Draft PO → Slack dispatch) in the background.
    """
    report = calculate_ds_ratio(db, sku, route_id.upper(), company_id)

    # Fire agentic loop in background — non-blocking, doesn't slow response
    if background_tasks:
        background_tasks.add_task(_maybe_trigger_agentic_loop, report)
    else:
        asyncio.get_event_loop().run_in_executor(None, _maybe_trigger_agentic_loop, report)

    return report
