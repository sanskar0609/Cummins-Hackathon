import json
from typing import Any, Dict
from app.core.logging import log

# Kafka producer is optional — if confluent_kafka fails to connect
# (e.g. Zookeeper/Kafka not running on Windows Docker), all publish
# calls degrade silently so every FastAPI endpoint still returns 200.

_producer = None

def _get_producer():
    """Lazily initialise the Kafka producer exactly once.
    Returns None if Kafka is unavailable so callers can skip safely."""
    global _producer
    if _producer is not None:
        return _producer
    try:
        from confluent_kafka import Producer
        from app.core.config import settings

        conf = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'client.id': 'supply-chain-os-producer',
            'socket.timeout.ms': 3000,
            'message.timeout.ms': 3000,
        }
        _producer = Producer(conf)
        log.info("kafka_producer_initialised")
    except Exception as e:
        log.warning("kafka_unavailable_producer_disabled", error=str(e))
        _producer = None
    return _producer


def delivery_report(err, msg):
    if err is not None:
        log.warning("kafka_delivery_failed", error=str(err))
    else:
        log.debug("kafka_delivery_ok", topic=msg.topic())


def publish_message(topic: str, key: str, message: Dict[str, Any]) -> bool:
    """
    Publish a JSON message to Kafka. Returns True on success, False when
    Kafka is unavailable — never raises so endpoints stay healthy.
    """
    producer = _get_producer()
    if producer is None:
        log.debug("kafka_skipped_producer_unavailable", topic=topic)
        return False
    try:
        producer.produce(
            topic,
            key=str(key),
            value=json.dumps(message),
            callback=delivery_report
        )
        producer.poll(0)
        return True
    except Exception as e:
        log.warning("kafka_produce_failed", error=str(e), topic=topic)
        return False


def flush_producer(timeout: float = 5.0):
    producer = _get_producer()
    if producer:
        try:
            producer.flush(timeout)
        except Exception:
            pass
