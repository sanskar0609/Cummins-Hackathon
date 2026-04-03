import asyncio
import websockets
import json
import logging
import os
from datetime import datetime
from app.core.config import settings
from app.services.kafka_producer import publish_message
from app.db.redis import redis_client

# We will use standard logging or structlog for clarity in the background task
from app.core.logging import log

# The specific bounding boxes requested
# AISStream format: [[SouthWestLat, SouthWestLon], [NorthEastLat, NorthEastLon]]
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

REDIS_AIS_KEY = "ais:live:positions"
MAX_CACHED_VESSELS = 100

def _get_boxes():
    return [box for chokepoint, box in CHOKEPOINTS.items()]

async def consume_ais_stream():
    """
    Connects to AISStream.io, processes vessel updates for key chokepoints,
    pushes raw payload to Kafka, logs to JSONL file locally, and updates Redis.
    """
    if not settings.AISSTREAM_API_KEY:
        log.error("ais_stream_failed", reason="AISSTREAM_API_KEY is not defined in config")
        return

    url = "wss://stream.aisstream.io/v0/stream"
    subscription_message = {
        "APIKey": settings.AISSTREAM_API_KEY,
        "BoundingBoxes": _get_boxes()
    }
    
    # Ensure the target storage path exists
    os.makedirs(settings.DATA_RAW_PATH, exist_ok=True)
    ais_raw_path = os.path.join(settings.DATA_RAW_PATH, "ais")
    os.makedirs(ais_raw_path, exist_ok=True)
    raw_log_file = os.path.join(ais_raw_path, f"ais_raw_{datetime.utcnow().strftime('%Y%m%d')}.jsonl")
    
    log.info("ais_stream_connecting", url=url, chokepoints_count=len(CHOKEPOINTS))

    # Keep alive loop wrapping websocket connection to retry on failure
    while True:
        try:
            async with websockets.connect(url) as websocket:
                await websocket.send(json.dumps(subscription_message))
                log.info("ais_stream_subscribed", message="Successfully subscribed to BoundingBoxes")
                
                async for message in websocket:
                    # Message is a string of JSON
                    try:
                        data = json.loads(message)
                        
                        # We only care about PositionReport for tracking live vessels
                        if data.get("MessageType") == "PositionReport":
                            msg_id = data.get("Message", {}).get("PositionReport", {}).get("UserID", "UNKNOWN")
                            
                            # 1. Publish raw data to Kafka ais-feed
                            publish_message(settings.KAFKA_TOPIC_AIS, key=str(msg_id), message=data)
                            
                            # 2. Store to local ./data/raw/ais/ as JSON lines
                            with open(raw_log_file, "a", encoding="utf-8") as f:
                                f.write(json.dumps(data) + "\n")
                                
                            # 3. Store the latest 100 positions in Redis cache
                            # Using LPUSH and LTRIM to keep max 100 elements
                            redis_client.lpush(REDIS_AIS_KEY, message)
                            redis_client.ltrim(REDIS_AIS_KEY, 0, MAX_CACHED_VESSELS - 1)

                    except json.JSONDecodeError:
                        log.warning("ais_stream_parse_error", raw_message=message[:100])
                    except Exception as e:
                        log.error("ais_stream_processing_error", error=str(e))
        
        except websockets.ConnectionClosed as cc:
            log.warning("ais_stream_closed", reason=str(cc))
        except Exception as e:
            log.error("ais_stream_exception", error=str(e))
            
        # Reconnect backoff
        await asyncio.sleep(5)

# If run directly -> startup loop manually
if __name__ == "__main__":
    asyncio.run(consume_ais_stream())
