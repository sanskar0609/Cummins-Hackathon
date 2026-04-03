import redis
import json
from typing import Any, Optional
from app.core.config import settings
from app.core.logging import log

import os

# Identify if REDIS_URL is injected via Docker network layer, otherwise default to pool host logic or localhost url
redis_url = os.environ.get("REDIS_URL")
if redis_url:
    redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
else:
    pool = redis.ConnectionPool(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD or None,
        decode_responses=True
    )
    redis_client = redis.Redis(connection_pool=pool)

def get_cache(key: str) -> Optional[Any]:
    """
    Retrieve a value from Redis cache by key and deserialize from JSON.
    Returns None if the key does not exist.
    """
    try:
        val = redis_client.get(key)
        if val:
            return json.loads(val)
        return None
    except Exception as e:
        log.error("redis_get_error", key=key, error=str(e))
        return None

def set_cache(key: str, value: Any, ex: int = 3600) -> bool:
    """
    Serialize a value to JSON and store it in Redis cache with an expiration time.
    Default expiration is 3600 seconds (1 hour).
    """
    try:
        serialized_value = json.dumps(value)
        return bool(redis_client.set(key, serialized_value, ex=ex))
    except Exception as e:
        log.error("redis_set_error", key=key, error=str(e))
        return False

def delete_cache(key: str) -> bool:
    """
    Delete a key from Redis cache.
    """
    try:
        return bool(redis_client.delete(key))
    except Exception as e:
        log.error("redis_delete_error", key=key, error=str(e))
        return False
