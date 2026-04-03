import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime
from prophet import Prophet
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.demand_forecast import DemandForecast
from app.core.config import settings
from app.core.logging import log

# Mute Prophet's cmdstanpy noisy logging
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
logging.getLogger('prophet').setLevel(logging.WARNING)

def _ensure_mock_data(csv_path: str):
    """ Generates 2 years of synthetic historical order data for multiple SKUs natively. """
    if os.path.exists(csv_path):
        return
        
    log.info("generating_mock_sku_data", path=csv_path)
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    dates = pd.date_range(end=datetime.now(), periods=730)
    skus = ['SKU-001', 'SKU-002', 'SKU-003']
    data = []
    
    for sku in skus:
        # Base daily demand scaling
        base = np.random.randint(50, 200)
        for d in dates:
            day_of_year = d.timetuple().tm_yday
            # Simulate real-world retail seasonality
            seasonality = 35 * np.sin(day_of_year * (2 * np.pi / 365.25))
            noise = np.random.normal(0, 10)
            trend = (d - dates[0]).days * 0.05
            
            y = max(0, int(base + seasonality + trend + noise))
            data.append({"ds": d.strftime("%Y-%m-%d"), "y": y, "sku": sku})
            
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)
    log.info("mock_sku_data_generated", total_rows=len(df), skus=skus)

def run_prophet_forecast(df: pd.DataFrame, periods: int = 90) -> pd.DataFrame:
    """ Computes Prophet predictive 90-day time-series extension. """
    model = Prophet(interval_width=0.95, daily_seasonality=False, yearly_seasonality=True)
    
    # Needs columns exactly named 'ds' and 'y'
    model.fit(df)
    
    # Extend timeline natively inside Prophet dataframe
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)
    
    # Filter bounds purely tracking future (unseen) horizons
    future_forecast = forecast[forecast['ds'] > df['ds'].max()].copy()
    return future_forecast

def generate_and_store_forecasts():
    """ Load historical data, train local Prophet per SKU, push artifacts directly into OS postgres. """
    os.makedirs(settings.DATA_RAW_PATH, exist_ok=True)
    csv_path = os.path.join(settings.DATA_RAW_PATH, "mock_sku_orders.csv")
    
    _ensure_mock_data(csv_path)
    
    try:
        df_all = pd.read_csv(csv_path)
    except Exception as e:
        log.error("demand_data_load_error", error=str(e))
        return
        
    # Isolate targets
    skus = df_all['sku'].unique()
    db = SessionLocal()
    
    try:
        log.info("starting_demand_forecasting", skus=list(skus))
        
        for sku in skus:
            df_sku = df_all[df_all['sku'] == sku][['ds', 'y']]
            df_sku['ds'] = pd.to_datetime(df_sku['ds'])
            
            # Predict
            forecast_df = run_prophet_forecast(df_sku, periods=90)
            
            # Wipe old projections for a clean state rewrite
            db.query(DemandForecast).filter(DemandForecast.sku == sku).delete()
            
            # Insert forward vectors
            for _, row in forecast_df.iterrows():
                pred = DemandForecast(
                    sku=sku,
                    forecast_date=row['ds'].date(),
                    predicted_demand=max(0, float(row['yhat'])),
                    lower_bound=max(0, float(row['yhat_lower'])),
                    upper_bound=max(0, float(row['yhat_upper'])),
                    model_used="Prophet"
                )
                db.add(pred)
                
            db.commit()
            log.info("demand_forecast_stored", sku=sku, dates_predicted=len(forecast_df))
            
    except Exception as e:
        db.rollback()
        log.error("demand_forecast_error", error=str(e))
    finally:
        db.close()

if __name__ == "__main__":
    generate_and_store_forecasts()
