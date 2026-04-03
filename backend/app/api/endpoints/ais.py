from fastapi import APIRouter
from typing import Dict, Any, List
import json
from app.db.redis import redis_client
from app.services.ais_stream import REDIS_AIS_KEY

router = APIRouter()

@router.get("/live", response_model=Dict[str, Any])
async def get_live_ais():
    """
    Returns the last up to 100 vessel positions cached in Redis,
    formatted strictly as a GeoJSON FeatureCollection.
    """
    raw_vessels: List[str] = redis_client.lrange(REDIS_AIS_KEY, 0, 99)
    
    features = []
    
    for vessel_str in raw_vessels:
        data = json.loads(vessel_str)
        
        # Ensure we are parsing a valid PositionReport
        msg = data.get("Message", {}).get("PositionReport", {})
        if not msg:
            continue
            
        mmsi = msg.get("UserID", 0)
        lat = msg.get("Latitude", 0)
        lon = msg.get("Longitude", 0)
        speed = msg.get("Sog", 0)
        heading = msg.get("TrueHeading", 0)
        nav_status = msg.get("NavigationalStatus", 0)

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]  # GeoJSON format is [longitude, latitude]
            },
            "properties": {
                "mmsi": mmsi,
                "speed_knots": speed,
                "heading": heading,
                "nav_status": nav_status,
                "timestamp": data.get("TimeUtc", "")
            }
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return geojson
