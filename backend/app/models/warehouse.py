from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.declarative import Base

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    company_profile_id = Column(Integer, ForeignKey("company_profile.id"), nullable=True, index=True)
    name = Column(String, index=True, nullable=False)
    stock = Column(Float, nullable=False, default=0.0)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    demand = Column(Float, nullable=True, default=0.0) # Snapshot of regional demand at compute time
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
