from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class GeoRiskEvent(Base):
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True, nullable=False) # E.g., GDELT, RapidAPI
    title = Column(String, nullable=False)
    url = Column(String, unique=True, index=True, nullable=True)
    domain = Column(String, nullable=True) # E.g., bbc.com
    event_type = Column(String, index=True, nullable=True) # Derived from keywords
    affected_region = Column(String, index=True, nullable=True) # Extracted location
    severity_score = Column(Float, nullable=False) # 0.0 to 1.0 DistilBERT Negative Probability
    seendate = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __tablename__ = "geo_risk_events"
