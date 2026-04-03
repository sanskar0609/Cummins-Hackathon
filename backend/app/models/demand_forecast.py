from sqlalchemy import Column, Integer, String, Float, DateTime, Date
from sqlalchemy.sql import func
from app.db.base import Base

class DemandForecast(Base):
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, index=True, nullable=False)
    forecast_date = Column(Date, index=True, nullable=False) # The future date being predicted
    predicted_demand = Column(Float, nullable=False) # yhat
    lower_bound = Column(Float, nullable=False) # yhat_lower
    upper_bound = Column(Float, nullable=False) # yhat_upper
    model_used = Column(String, nullable=False) # E.g., 'prophet' or 'arima'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __tablename__ = "demand_forecasts"
