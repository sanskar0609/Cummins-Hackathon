from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class POStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    APPROVED_PENDING_ERP = "APPROVED_PENDING_ERP"
    SENT = "SENT"
    REJECTED = "REJECTED"


# Alias for backward compatibility
PODraftStatus = POStatus
APPROVED_PENDING_ERP = POStatus.APPROVED

class PODraft(Base):
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    sku = Column(String, index=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    estimated_cost = Column(Float, nullable=True)
    status = Column(Enum(POStatus), default=POStatus.DRAFT, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_by = Column(String, nullable=True) # E.g., Slack User ID
    
    __tablename__ = "po_drafts"
