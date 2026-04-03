from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class AlertStatus(str, enum.Enum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"

class AlertLog(Base):
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String, index=True, nullable=False) # E.g., CONGESTION, D/S_RATIO
    message = Column(String, nullable=False)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.INFO, nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.NEW, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __tablename__ = "alert_logs"
