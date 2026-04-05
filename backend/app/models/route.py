from sqlalchemy import Column, Integer, String, Float, Enum, JSON
from app.db.declarative import Base
import enum

class TransportMode(str, enum.Enum):
    SEA = "SEA"
    AIR = "AIR"
    ROAD = "ROAD"
    RAIL = "RAIL"

class Route(Base):
    id = Column(Integer, primary_key=True, index=True)
    origin_node = Column(String, index=True, nullable=False)
    destination_node = Column(String, index=True, nullable=False)
    transport_mode = Column(Enum(TransportMode), default=TransportMode.SEA, nullable=False)
    average_time_hours = Column(Float, nullable=True)
    chokepoint_associated = Column(String, nullable=True) # E.g., Suez Canal, Hormuz
    
    __tablename__ = "routes"
