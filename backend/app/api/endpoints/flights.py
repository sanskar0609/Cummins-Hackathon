from fastapi import APIRouter
from typing import Dict, Any, List
import json
from app.db.redis import redis_client
from app.services.opensky_ingest import REDIS_FLIGHTS_KEY

router = APIRouter()

@router.get("/live", response_model=Dict[str, Any])
async def get_live_flights():
    """
    Returns the latest sampled flight state vectors bound by
    our major supply chain hubs, cached in Redis and formatted as GeoJSON.
    """
    raw_flights_list = redis_client.lrange(REDIS_FLIGHTS_KEY, 0, -1)
    
    features = []
    
    for fl_str in raw_flights_list:
        data = json.loads(fl_str)
        lon = data.get("longitude", 0.0)
        lat = data.get("latitude", 0.0)

        # Basic GeoJSON schema feature wrap
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": {
                "icao24": data.get("icao24"),
                "callsign": data.get("callsign"),
                "origin_country": data.get("origin_country"),
                "altitude_m": data.get("altitude_m"),
                "velocity_ms": data.get("velocity_ms"),
                "heading": data.get("heading"),
                "hub": data.get("hub"),
                "timestamp": data.get("timestamp_utc")
            }
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return geojson
