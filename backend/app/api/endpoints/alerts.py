import json
from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.db.redis import redis_client

router = APIRouter()

@router.get("", response_model=List[Dict[str, Any]])
async def get_active_alerts(
    company_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Returns active alerts sourced from 4 places:
    1. `alerts` table        — seeded system alerts
    2. `alert_logs` table    — real agentic loop audit trail (Gap 3 ✅)
    3. `po_drafts` table     — pending PO approvals (Gap 2 ✅)
    4. Redis                 — live agentic PO drafts cached in last 30 min
    """
    alerts: List[Dict[str, Any]] = []
    seen_ids = set()

    # ── 1. Seeded system alerts ────────────────────────────────────────────────
    try:
        rows = db.execute(
            text("SELECT id, title, severity, message, created_at FROM alerts ORDER BY created_at DESC LIMIT 10")
        ).fetchall()
        for row in rows:
            aid = f"seed-{row[0]}"
            seen_ids.add(aid)
            alerts.append({
                "id":                aid,
                "type":              str(row[1]),
                "severity":          str(row[2]).lower(),
                "summary":           str(row[3]),
                "timestamp":         str(row[4]) if row[4] else "Recent",
                "affected":          "System",
                "recommendedAction": "Inspect parameters.",
                "rawSource":         "seed",
                "agenticDraft":      None,
            })
    except Exception as e:
        print(f"Seed alerts error: {e}")

    # ── 2. alert_logs table (agentic audit trail) ──────────────────────────────
    try:
        where_clause = f"WHERE company_profile_id = {company_id}" if company_id else ""
        rows = db.execute(
            text(f"""
                SELECT id, alert_type, message, severity, status, created_at
                FROM alert_logs
                {where_clause}
                ORDER BY created_at DESC LIMIT 20
            """)
        ).fetchall()
        for row in rows:
            aid = f"log-{row[0]}"
            if aid in seen_ids:
                continue
            seen_ids.add(aid)
            sev_raw = str(row[3]).upper()
            alerts.append({
                "id":                aid,
                "type":              str(row[1]),
                "severity":          "critical" if sev_raw == "CRITICAL" else ("warning" if sev_raw == "WARNING" else "info"),
                "summary":           str(row[2])[:300],
                "timestamp":         str(row[5]) if row[5] else "Recent",
                "affected":          str(row[1]),
                "recommendedAction": "Review agentic loop action and approve/dismiss.",
                "rawSource":         "alert_logs",
                "agenticDraft":      None,
            })
    except Exception as e:
        print(f"alert_logs error: {e}")

    # ── 3. po_drafts table (pending PO approvals) ──────────────────────────────
    try:
        where_clause = f"WHERE pd.status IN ('DRAFT', 'PENDING_APPROVAL')"
        if company_id:
            where_clause += f" AND pd.company_profile_id = {company_id}"
            
        rows = db.execute(
            text(f"""
                SELECT pd.id, pd.sku, pd.quantity, pd.estimated_cost, pd.status, pd.created_at,
                       s.name AS supplier_name, s.location AS supplier_location
                FROM po_drafts pd
                LEFT JOIN suppliers s ON s.id = pd.supplier_id
                {where_clause}
                ORDER BY pd.created_at DESC LIMIT 10
            """)
        ).fetchall()
        for row in rows:
            aid = f"po-{row[0]}"
            if aid in seen_ids:
                continue
            seen_ids.add(aid)
            qty       = int(row[2]) if row[2] else 0
            cost      = float(row[3]) if row[3] else qty * 8.20
            lost_rev  = round(qty * 28)
            alerts.append({
                "id":       aid,
                "type":     f"PENDING PO — {row[1]}",
                "severity": "critical" if str(row[4]) == "PENDING_APPROVAL" else "warning",
                "summary":  (
                    f"Emergency PO for SKU {row[1]}: {qty:,} units to "
                    f"{row[6] or 'backup supplier'} ({row[7] or 'unknown location'}). "
                    f"Estimated cost: ${cost:,.0f}."
                ),
                "timestamp":         str(row[5]) if row[5] else "Recent",
                "affected":          f"SKU {row[1]}",
                "recommendedAction": (
                    f"Approve PO of {qty:,} units (${cost:,.0f}). "
                    f"Cost of inaction: ~${lost_rev:,} in lost revenue."
                ),
                "rawSource":  "po_drafts",
                "agenticDraft": {
                    "gapUnits":   qty,
                    "costEst":    round(cost),
                    "lostRevEst": lost_rev,
                    "supplier":   row[6],
                    "status":     str(row[4]),
                },
            })
    except Exception as e:
        print(f"po_drafts error: {e}")

    # ── 4. Redis live agentic cache (recent 30 min) ────────────────────────────
    try:
        redis_pattern = f"agentic_po_draft:{company_id}:*" if company_id else "agentic_po_draft:*"
        po_keys = redis_client.keys(redis_pattern)
        for key in po_keys:
            raw = redis_client.get(key)
            if not raw:
                continue
            po  = json.loads(raw)
            sku = po.get("sku", "?")
            aid = f"redis-{sku}"
            if aid in seen_ids:
                continue
            seen_ids.add(aid)
            ratio    = po.get("ratio", 0)
            severity = po.get("severity", "WARNING")
            gap      = po.get("gap_units", 0)
            alerts.append({
                "id":       aid,
                "type":     f"D/S RATIO BREACH — {sku}",
                "severity": "critical" if severity == "CRITICAL" else "warning",
                "summary":  (
                    po.get("summary") or
                    f"SKU {sku} on {po.get('route','?')}: D/S ratio {ratio:.2f}× "
                    f"({severity}). Gap of {gap:,} units detected."
                ),
                "timestamp":       po.get("triggered_at", "Recent"),
                "affected":        f"SKU {sku} · {po.get('route','?')}",
                "recommendedAction": (
                    po.get("action") or
                    f"Approve emergency PO — {gap:,} units at ~${gap * 8.20:,.0f}."
                ),
                "rawSource":  "agentic_loop_redis",
                "agenticDraft": {
                    "dsRatio":    ratio,
                    "gapUnits":   gap,
                    "costEst":    round(gap * 8.20),
                    "lostRevEst": round(gap * 28),
                    "slackStatus": po.get("slack_status", "MOCKED"),
                },
            })
    except Exception as e:
        print(f"Redis agentic alerts error: {e}")

    # Sort: critical first, then by most recent
    alerts.sort(key=lambda a: (0 if a["severity"] == "critical" else 1))
    return alerts
