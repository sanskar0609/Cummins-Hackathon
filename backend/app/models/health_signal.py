from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from app.db.base import Base

class SupplierHealthSignal(Base):
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(String, index=True, nullable=False) # E.g., SUP-T1-A
    
    # Storing raw JSON intelligence blocks from external proxy APIs
    hunter_data = Column(JSON, nullable=True)     # Email patterns / activity
    news_data = Column(JSON, nullable=True)       # Negative sentiment NLP filtered events
    rapidapi_data = Column(JSON, nullable=True)   # Business financial & operative datasets
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __tablename__ = "supplier_health_signals"
