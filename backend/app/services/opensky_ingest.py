import asyncio
import httpx
import json
import os
from datetime import datetime
from aiohttp import BasicAuth
from app.core.config import settings
from app.services.kafka_producer import publish_message
from app.db.redis import redis_client
from app.core.logging import log

# Key Air Cargo Hubs Bounding Boxes (approximate)
# Format: lomin, lamin, lomax, lamax
# E.g., Memphis (FedEx Hub), Hong Kong (HKIA), Frankfurt (FRA), Anchorage (ANC)
HUBS = {
    "Memphis":      {"lomin": -90.5, "lamin": 34.5, "lomax": -89.5, "lamax": 35.5},
    "Hong Kong":    {"lomin": 113.5, "lamin": 22.0, "lomax": 114.5, "lamax": 23.0},
    "Frankfurt":    {"lomin": 8.0,   "lamin": 49.5, "lomax": 9.0,   "lamax": 50.5},
    "Anchorage":    {"lomin": -150.5,"lamin": 60.5, "lomax": -149.5,"lamax": 61.5}
}

REDIS_FLIGHTS_KEY = "flights:live:positions"
POLL_INTERVAL_SECONDS = 300  # 5 minutes

async def fetch_flights_for_hub(client: httpx.AsyncClient, hub_name: str, coords: dict):
    """
    Fetch flights for a specific bounding box from OpenSky Network.
    """
    url = "https://opensky-network.org/api/states/all"
    params = coords
    
    # OpenSky free tier requires basic auth to get decent rate limits
    auth = (settings.OPENSKY_USERNAME, settings.OPENSKY_PASSWORD) if settings.OPENSKY_USERNAME else None

    log.debug("opensky_polling", hub=hub_name, coords=coords)

    try:
        response = await client.get(url, params=params, auth=auth, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        # 'states' is a list of lists representing flight data vectors
        states = data.get("states") or []
        log.info("opensky_success", hub=hub_name, count=len(states))
        
        parsed_flights = []
        for state in states:
            # OpenSky JSON array format reference:
            # 0=icao24, 1=callsign, 2=origin_country, 5=longitude, 6=latitude,
            # 7=baro_altitude, 8=on_ground, 9=velocity, 10=true_track
            if state[5] is not None and state[6] is not None:
                parsed_flights.append({
                    "icao24": str(state[0]),
                    "callsign": str(state[1]).strip() if state[1] else "",
                    "origin_country": str(state[2]),
                    "longitude": float(state[5]),
                    "latitude": float(state[6]),
                    "altitude_m": float(state[7]) if state[7] else 0.0,
                    "velocity_ms": float(state[9]) if state[9] else 0.0,
                    "heading": float(state[10]) if state[10] else 0.0,
                    "hub": hub_name,
                    "timestamp_utc": datetime.utcnow().isoformat()
                })
        return parsed_flights

    except httpx.HTTPStatusError as he:
        # 429 indicates rate limiting by OpenSky
        log.warning("opensky_http_error", hub=hub_name, status=he.response.status_code, text=he.response.text[:100])
        return []
    except Exception as e:
        log.error("opensky_error", hub=hub_name, error=str(e))
        return []

async def poll_flights():
    """
    Background loop to systematically poll OpenSky every 5 minutes.
    """
    os.makedirs(settings.DATA_RAW_PATH, exist_ok=True)
    flights_raw_path = os.path.join(settings.DATA_RAW_PATH, "flights")
    os.makedirs(flights_raw_path, exist_ok=True)

    # Use HTTPX client session to keep connections alive
    async with httpx.AsyncClient() as client:
        while True:
            log.info("opensky_polling_batch_started")
            batch_flights = []
            
            for hub_name, coords in HUBS.items():
                flights = await fetch_flights_for_hub(client, hub_name, coords)
                batch_flights.extend(flights)
                
                # Sleep briefly between hub requests to avoid aggressively hitting the API
                await asyncio.sleep(2)
                
            if batch_flights:
                # 1. Store to local ./data/raw/flights/ as JSON lines
                raw_log_file = os.path.join(flights_raw_path, f"flights_raw_{datetime.utcnow().strftime('%Y%m%d')}.jsonl")
                with open(raw_log_file, "a", encoding="utf-8") as f:
                    for fl in batch_flights:
                        f.write(json.dumps(fl) + "\n")
                        
                        # 2. Publish to Kafka
                        publish_message(settings.KAFKA_TOPIC_FLIGHT, key=fl["icao24"], message=fl)

                # 3. Cache latest snapshot in Redis (wipe old one, insert full list)
                json_str_payload = [json.dumps(fl) for fl in batch_flights]
                # Pipeline it to be atomic
                pipe = redis_client.pipeline()
                pipe.delete(REDIS_FLIGHTS_KEY)
                if json_str_payload:
                    pipe.lpush(REDIS_FLIGHTS_KEY, *json_str_payload)
                pipe.execute()

            log.info("opensky_polling_batch_complete", total_flights_cached=len(batch_flights))
            
            # Wait 5 minutes
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

# To run independently:
if __name__ == "__main__":
    asyncio.run(poll_flights())
