import asyncio
import json
import time
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.core.logging import log
from app.db.session import SessionLocal
from app.models.risk_score import RiskScore, EntityType
from app.services.kafka_consumer import KafkaConsumerService
from app.core.config import settings

# Same bounding boxes to map a vessel to a chokepoint locally
CHOKEPOINTS = {
    "Strait of Hormuz": [[25.0, 54.0], [27.0, 57.0]],
    "Suez Canal": [[29.0, 32.0], [31.5, 33.0]],
    "Strait of Malacca": [[1.0, 101.0], [6.0, 105.0]],
    "Panama Canal": [[8.0, -80.5], [10.0, -79.0]],
    "Bab-el-Mandeb": [[12.0, 42.0], [13.5, 44.0]],
    "Cape of Good Hope": [[-36.0, 17.0], [-33.0, 21.0]],
    "Taiwan Strait": [[22.0, 118.0], [26.0, 122.0]],
    "Danish Straits": [[54.0, 9.0], [58.0, 13.0]]
}

# State: { "Suez Canal": { "mmsi123": {"speed": 14.5, "ts": 1600000000} } }
active_vessels: Dict[str, Dict[str, Dict[str, float]]] = {cp: {} for cp in CHOKEPOINTS.keys()}

def get_chokepoint_from_coords(lat: float, lon: float) -> str:
    for cp_name, bounds in CHOKEPOINTS.items():
        sw_lat, sw_lon = bounds[0]
        ne_lat, ne_lon = bounds[1]
        
        # Handle wraparound mapping roughly if needed, otherwise standard box logic
        if sw_lat <= lat <= ne_lat and sw_lon <= lon <= ne_lon:
            return cp_name
    return "UNKNOWN"

def calculate_risk_level(congestion_index: float) -> str:
    if congestion_index < 30:
        return "LOW"
    elif congestion_index < 60:
        return "MEDIUM"
    elif congestion_index < 80:
        return "HIGH"
    return "CRITICAL"

async def ais_message_handler(topic: str, payload: dict):
    """
    Callback fired for every new PositionReport from Kafka.
    Updates the local memory dict.
    """
    msg = payload.get("Message", {}).get("PositionReport", {})
    if not msg:
        return

    mmsi = str(msg.get("UserID", ""))
    lat = float(msg.get("Latitude", 0))
    lon = float(msg.get("Longitude", 0))
    speed = float(msg.get("Sog", 0)) # Speed over ground in knots

    cp_name = get_chokepoint_from_coords(lat, lon)
    if cp_name != "UNKNOWN":
        active_vessels[cp_name][mmsi] = {"speed": speed, "ts": time.time()}

async def evaluate_and_store_risk(db: Session):
    """
    Periodically calculates aggregate scores and writes to PostgreSQL. 
    """
    now = time.time()
    STALE_THRESHOLD_SEC = 600 # 10 mins

    for cp_name, vessels in active_vessels.items():
        # Remove stale
        to_remove = [mmsi for mmsi, data in vessels.items() if now - data["ts"] > STALE_THRESHOLD_SEC]
        for mmsi in to_remove:
            del vessels[mmsi]
            
        vessel_count = len(vessels)
        if vessel_count == 0:
            continue
            
        avg_speed = sum(d["speed"] for d in vessels.values()) / vessel_count
        
        # Heuristic Congestion Index: Highly scaled by volume vs speed
        # If there are many vessels and they are moving slowly, index goes up.
        # Cap at 100 max.
        speed_factor = max(avg_speed, 1.0)
        raw_index = (vessel_count * 15.0) / speed_factor
        congestion_index = min(raw_index, 100.0)
        
        risk_level = calculate_risk_level(congestion_index)
        
        # Store risk score to PostgreSQL
        risk_entry = RiskScore(
            entity_type=EntityType.CHOKEPOINT,
            entity_id=cp_name,
            score=congestion_index,
            reason=f"Risk Level: {risk_level} | Vessels: {vessel_count} | Avg Speed: {avg_speed:.1f} kts"
        )
        db.add(risk_entry)
        
        log.info("chokepoint_scored", chokepoint=cp_name, risk_level=risk_level, congestion_index=round(congestion_index,2), count=vessel_count)

    db.commit()

async def risk_scoring_loop():
    """
    Dedicated loop that triggers the SQL evaluation every 60 seconds.
    """
    while True:
        await asyncio.sleep(60)
        db = SessionLocal()
        try:
            await evaluate_and_store_risk(db)
        except Exception as e:
            log.error("risk_evaluation_error", error=str(e))
            db.rollback()
        finally:
            db.close()

async def main():
    consumer = KafkaConsumerService(
        group_id="chokepoint-scorer-grp",
        topics=[settings.KAFKA_TOPIC_AIS]
    )
    
    # Run the Kafka consumer loop and the 60s Scoring loop concurrently
    scorer_task = asyncio.create_task(risk_scoring_loop())
    await consumer.start(ais_message_handler)

if __name__ == "__main__":
    asyncio.run(main())
