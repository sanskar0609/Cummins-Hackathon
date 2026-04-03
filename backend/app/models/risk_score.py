from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class EntityType(str, enum.Enum):
    ROUTE = "ROUTE"
    SUPPLIER = "SUPPLIER"
    CHOKEPOINT = "CHOKEPOINT"
    REGION = "REGION"

class RiskScore(Base):
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(Enum(EntityType), nullable=False, index=True)
    entity_id = Column(String, index=True, nullable=False) # ID or Name of the evaluated entity
    score = Column(Float, nullable=False) # 0 to 100
    reason = Column(String, nullable=True) # NLP generated or ruled based reason
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __tablename__ = "risk_scores"
