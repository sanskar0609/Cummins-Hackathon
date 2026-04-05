from app.db.declarative import Base
from sqlalchemy import Column, Integer, String, JSON

# Define CompanyProfile here as it is an operational model used in onboarding
class CompanyProfile(Base):
    __tablename__ = "company_profile"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="")
    industry = Column(String, default="")
    skus = Column(JSON, default=list) # Store list of {"sku": "...", "name": "...", "category": "..."}
    csv_path = Column(String, default="")

# Import models to ensure they register correctly for metadata
from app.models.supplier import Supplier
from app.models.po_draft import PODraft
from app.models.route import Route
from app.models.risk_score import RiskScore
from app.models.health_signal import SupplierHealthSignal
from app.models.geo_risk_event import GeoRiskEvent
from app.models.demand_forecast import DemandForecast
from app.models.alert_log import AlertLog, Alert
from app.models.warehouse import Warehouse
