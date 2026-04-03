import asyncio
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.geo_risk_event import GeoRiskEvent
from app.services.kafka_consumer import KafkaConsumerService
from app.core.config import settings
from app.core.logging import log

# TODO: Replaced huggingface distilbert with scikit-learn NaiveBayes inference logic
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.naive_bayes import MultinomialNB
import numpy as np

# Pseudo zero-shot inference pipeline using sklearn shapes
vectorizer = HashingVectorizer(n_features=20, alternate_sign=False)
dummy_clf = MultinomialNB()
# Train with a positive and negative class
dummy_clf.fit(vectorizer.transform(["good news safe secure", "bad conflict strike attack"]), [0, 1])

def analyze_severity(text: str) -> float:
    try:
        if not text:
            return 0.0
        X = vectorizer.transform([text])
        # Returns probability of class 1 (High Severity)
        prob = dummy_clf.predict_proba(X)[0][1]
        return float(prob)
    except Exception as e:
        log.error("nlp_scoring_error", error=str(e))
        return 0.0

async def geo_event_handler(topic: str, payload: dict):
    """
    Message handler invoked via Kakfa poll yielding geo-event dict.
    """
    title = payload.get("title", "")
    if not title:
        return
        
    severity = analyze_severity(title)
    
    # Internal context extraction based on active regions mapped
    REGIONS = ["Taiwan", "China", "Yemen", "Egypt", "Panama", "Iran", "South Africa", "Denmark", "Red Sea", "Suez"]
    affected_region = "Global"
    for r in REGIONS:
        if r.lower() in title.lower():
            affected_region = r
            break
            
    # Internal keyword extraction context
    RISKS = ["conflict", "strike", "port closure", "sanctions", "protest", "earthquake", "typhoon"]
    event_type = "Generic Alert"
    for ri in RISKS:
        if ri.lower() in title.lower():
            event_type = ri.capitalize()
            break

    db = SessionLocal()
    try:
        # Ignore events with identical URLs already classified and stored
        if payload.get("url"):
            exists = db.query(GeoRiskEvent).filter_by(url=payload.get("url")).first()
            if exists:
                return

        geo_event = GeoRiskEvent(
            source=payload.get("source", "Unknown"),
            title=title,
            url=payload.get("url", ""),
            domain=payload.get("domain", ""),
            event_type=event_type,
            affected_region=affected_region,
            severity_score=severity,
            seendate=payload.get("seendate", "")
        )
        db.add(geo_event)
        db.commit()
        log.info("geo_event_classified", region=affected_region, severity_score=round(severity, 3), title=title[:90])
        
    except Exception as e:
        log.error("db_write_geo_event_error", error=str(e))
        db.rollback()
    finally:
        db.close()

async def main():
    consumer = KafkaConsumerService(
        group_id="nlp-geo-scorer-grp",
        topics=[settings.KAFKA_TOPIC_GEO_EVENTS]
    )
    await consumer.start(geo_event_handler)

if __name__ == "__main__":
    asyncio.run(main())
