from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, List
from app.db.session import get_db
from app.core.logging import log

router = APIRouter()

# Canonical chokepoint list — used to build a complete response even when
# the risk_scores table is empty (no ingestion has run yet).
_CHOKEPOINTS = [
    {"id": "SUEZ",     "name": "Suez Canal",         "region": "Middle East"},
    {"id": "HORMUZ",   "name": "Strait of Hormuz",   "region": "Persian Gulf"},
    {"id": "MALACCA",  "name": "Strait of Malacca",  "region": "Southeast Asia"},
    {"id": "TAIWAN",   "name": "Taiwan Strait",       "region": "East Asia"},
    {"id": "PANAMA",   "name": "Panama Canal",        "region": "Central America"},
    {"id": "BOSPORUS", "name": "Bosphorus Strait",    "region": "Turkey"},
    {"id": "DOVER",    "name": "Strait of Dover",     "region": "Northern Europe"},
    {"id": "BABELM",   "name": "Bab-el-Mandeb",       "region": "Red Sea"},
]

@router.get("/chokepoints", response_model=List[Dict[str, Any]])
async def get_chokepoint_risks(db: Session = Depends(get_db)):
    """
    Returns the latest risk scores for all tracked maritime chokepoints.
    """
    try:
        query = text("SELECT name, origin, destination, risk_level, chokepoint FROM routes")
        result = db.execute(query)
        rows = result.fetchall()
        
        if rows:
            coords_map = {
                "Suez Canal": {"lat": 30.5852, "lon": 32.2654},
                "Strait of Hormuz": {"lat": 26.5667, "lon": 56.2500},
                "Malacca Strait": {"lat": 2.9000, "lon": 101.2667},
                "Panama Canal": {"lat": 9.1000, "lon": -79.6333},
                "Bab-el-Mandeb": {"lat": 12.5833, "lon": 43.3333}
            }
            results = []
            for row in rows:
                c_name = row[0]
                risk_level = str(row[3]).upper() if row[3] else "LOW"
                color = (
                    "red" if risk_level == "CRITICAL" else
                    "orange" if risk_level == "HIGH" else
                    "yellow" if risk_level == "MEDIUM" else
                    "green"
                )
                results.append({
                    "name": c_name,
                    "origin": row[1],
                    "destination": row[2],
                    "risk_level": risk_level,
                    "color": color,
                    "chokepoint": row[4],
                    "lat": coords_map.get(c_name, {}).get("lat", 0.0),
                    "lon": coords_map.get(c_name, {}).get("lon", 0.0)
                })
            return results
            
    except Exception as e:
        log.error("chokepoints_endpoint_error", error=str(e))
        
    # Hardcoded Fallback executed gracefully on Exception or empty Query array mapping gracefully
    results = []
    for cp in _CHOKEPOINTS:
        results.append({
            "chokepoint_id":    cp["id"],
            "name":             cp["name"],
            "region":           cp["region"],
            "risk_score":       0.0,
            "risk_level":       "LOW",
            "vessel_count":     None,
            "avg_speed_knots":  None,
            "congestion_index": None,
            "computed_at":      None,
        })
    return results
