from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.declarative import Base
import enum

class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class AlertStatus(str, enum.Enum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"

# Existing AlertLog for agentic audit trails
class AlertLog(Base):
    __tablename__ = "alert_logs"
    id = Column(Integer, primary_key=True, index=True)
    company_profile_id = Column(Integer, ForeignKey("company_profile.id"), nullable=True, index=True)
    alert_type = Column(String, index=True, nullable=False) # E.g., CONGESTION, D/S_RATIO
    message = Column(String, nullable=False)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.INFO, nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.NEW, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# New Alert model for global system notifications (matches endpoints/alerts.py)
class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    severity = Column(String, default="WARNING")
    message = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
