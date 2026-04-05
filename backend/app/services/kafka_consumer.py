import json
import os
import asyncio
from typing import Callable, Coroutine, Any, Dict, List
from confluent_kafka import Consumer, KafkaException
from app.core.config import settings
from app.core.logging import log

def _setup_aiven_ssl_certs():
    """Reads Aiven Kafka certs from Render environment variables and writes them to files."""
    kafa_ca = os.getenv("KAFKA_CA")
    if not kafa_ca:
        return False
        
    with open("ca.pem", "w") as f:
        f.write(kafa_ca.replace("\\n", "\n"))
    with open("service.cert", "w") as f:
        f.write(os.getenv("KAFKA_CERT", "").replace("\\n", "\n"))
    with open("service.key", "w") as f:
        f.write(os.getenv("KAFKA_KEY", "").replace("\\n", "\n"))
        
    return True

class KafkaConsumerService:
    def __init__(self, group_id: str, topics: List[str]):
        """
        Initializes the Kafka Consumer Base instance meant for background tasks.
        """
        self.group_id = group_id
        self.topics = topics
        self.running = False

        self.consumer_conf = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'group.id': group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False
        }
        
        if _setup_aiven_ssl_certs():
            self.consumer_conf.update({
                'security.protocol': 'SSL',
                'ssl.ca.location': 'ca.pem',
                'ssl.certificate.location': 'service.cert',
                'ssl.key.location': 'service.key'
            })
            log.info("kafka_consumer_aiven_ssl_configured")
            
        self.consumer = Consumer(self.consumer_conf)

    async def start(self, message_handler: Callable[[str, Dict[str, Any]], Coroutine[Any, Any, None]]):
        """
        Starts the event loop consuming from the initialized topic list.
        `message_handler` is an async callback taking arguments: (topic_name, JSON payload dict)
        """
        try:
            self.consumer.subscribe(self.topics)
            self.running = True
            log.info("kafka_consumer_started", topics=self.topics, group_id=self.group_id)

            while self.running:
                # Use a small timeout so we do not block the thread completely
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    # Give control back to the event loop
                    await asyncio.sleep(0.01)
                    continue
                if msg.error():
                    if msg.error().code() == KafkaException._PARTITION_EOF:
                        continue
                    else:
                        log.error("kafka_consumer_error", error=str(msg.error()))
                        break

                # Valid message retrieved
                raw_value = msg.value().decode('utf-8')
                topic = msg.topic()

                try:
                    payload = json.loads(raw_value)
                    
                    # Fire async message handler logic
                    await message_handler(topic, payload)

                    # Commit offset ONLY if successful parsing and handling 
                    self.consumer.commit(asynchronous=True)
                
                except json.JSONDecodeError as de:
                    log.error("kafka_json_decode_error", error=str(de), payload=raw_value)
                except Exception as e:
                    log.error("kafka_handler_error", error=str(e), topic=topic)

        finally:
            self.consumer.close()
            log.info("kafka_consumer_stopped", topics=self.topics)

    def stop(self):
        """
        Gracefully stop the background consumption loop.
        """
        self.running = False
