from sqlalchemy import Column, Integer, String, Float, Enum
from app.db.declarative import Base
import enum

class SupplierTier(str, enum.Enum):
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"

class Supplier(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    domain = Column(String, unique=True, index=True, nullable=True)
    tier = Column(Enum(SupplierTier), default=SupplierTier.TIER_1, nullable=False)
    location = Column(String, nullable=True)
    health_score = Column(Float, nullable=True)
    health_status = Column(String, nullable=True) # E.g., HEALTHY, WARNING, CRITICAL
    
    __tablename__ = "suppliers"
