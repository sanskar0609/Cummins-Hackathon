import os
import sys
import json
import random
from datetime import datetime, timedelta

# Ensure python path matches if orchestrated explicitly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.supplier import Supplier, SupplierTier
from app.models.route import Route, TransportMode
from app.models.risk_score import RiskScore, EntityType
from app.models.demand_forecast import DemandForecast
from app.models.alert_log import AlertLog, AlertSeverity, AlertStatus
from app.db.redis import redis_client
from app.services.ais_stream import REDIS_AIS_KEY

def seed_db():
    print("Connecting to PostgreSQL and building schema...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Clear existing tables safely
        print("Clearing existing data...")
        db.query(DemandForecast).delete()
        db.query(AlertLog).delete()
        db.query(RiskScore).delete()
        db.query(Route).delete()
        db.query(Supplier).delete()

        # 1. Suppliers
        print("Inserting 20 suppliers...")
        countries = ["Taiwan", "Vietnam", "Malaysia", "Germany", "Mexico", "Canada", "Singapore"]
        for i in range(1, 21):
            health = random.uniform(0.1, 0.99)
            s = Supplier(
                name=f"GlobalTech Corp {i}",
                domain=f"gtm{i}.tech",
                tier=random.choice(list(SupplierTier)),
                location=random.choice(countries),
                health_score=health,
                health_status="CRITICAL" if health < 0.3 else "WARNING" if health < 0.6 else "HEALTHY"
            )
            db.add(s)

        # 2. Routes (associated with Chokepoints and embedding real coordinates per instructions)
        print("Inserting 15 routes...")
        chokepoints = [
            ("Suez Canal", [30.5852, 32.2654]),
            ("Strait of Hormuz", [26.5667, 56.2500]),
            ("Malacca Strait", [2.9000, 101.2667]),
            ("Panama Canal", [9.1000, -79.6333]),
            ("Bab-el-Mandeb", [12.5833, 43.3333]),
            ("Cape of Good Hope", [-34.3548, 18.4698])
        ]
        
        for i in range(15):
            cp_name, coords = random.choice(chokepoints)
            r = Route(
                origin_node=f"Port_{random.randint(1,100)}",
                destination_node=f"Facility_{random.randint(1,100)}",
                transport_mode=TransportMode.SEA,
                average_time_hours=random.uniform(72, 500),
                chokepoint_associated=f"{cp_name} (Lat: {coords[0]}, Lon: {coords[1]})"
            )
            db.add(r)

        # 3. Risk Scores
        print("Inserting Risk Scores (3 Critical, 4 High, 5 Medium, 3 Low)...")
        cps = ["SUEZ", "HORMUZ", "MALACCA", "TAIWAN", "PANAMA", "BOSPORUS", "DOVER", "BABELM", 
               "GIBRALTAR", "CAPE", "MAGELLAN", "BERING", "BOSPHORUS", "MANDEN", "FLORIDA"]
        
        # Ranges map roughly to frontend enums CRITICAL(0.75+), HIGH(0.5+), MEDIUM(0.25+), LOW(0+)
        levels = [0.85]*3 + [0.65]*4 + [0.35]*5 + [0.15]*3 
        
        for idx, lvl in enumerate(levels):
            sc = RiskScore(
                entity_type=EntityType.CHOKEPOINT,
                entity_id=cps[idx],
                score=lvl + random.uniform(-0.05, 0.05),
                vessel_count=random.randint(10, 200),
                avg_speed_knots=random.uniform(5.0, 15.0),
                congestion_index=lvl
            )
            db.add(sc)

        # 4. Demand Forecast
        print("Inserting 2 years of daily demand for 5 SKUs...")
        skus = ["SKU-101", "SKU-205", "SKU-310", "SKU-499", "SKU-500"]
        start_date = datetime.utcnow().date() - timedelta(days=365)
        
        forecasts = []
        for sku in skus:
            for d in range(730):  # 2 years natively mapped
                f_date = start_date + timedelta(days=d)
                base = 15000 + random.randint(-5000, 5000)
                forecasts.append(
                    DemandForecast(
                        sku=sku,
                        forecast_date=f_date,
                        predicted_demand=base,
                        lower_bound=base * 0.8,
                        upper_bound=base * 1.2,
                        model_used="prophet"
                    )
                )
        db.bulk_save_objects(forecasts)

        # 5. Alert History Records
        print("Inserting 10 alerts...")
        for i in range(10):
            al = AlertLog(
                alert_type="SUPPLY_WARNING" if i % 2 == 0 else "ROUTE_CONGESTION",
                message=f"Simulation anomaly detected on edge vector #{i*15}",
                severity=random.choice(list(AlertSeverity)),
                status=random.choice(list(AlertStatus))
            )
            db.add(al)

        db.commit()
        print("PostgreSQL operations OK.")

    except Exception as e:
        db.rollback()
        print(f"Error during Postgres insert: {e}")
    finally:
        db.close()

def seed_redis():
    print("Inserting 5 vessel positions to Redis natively as GeoJSON properties...")
    redis_client.delete(REDIS_AIS_KEY)
    
    # 5 Real Coordinates for Suez Canonical bounds
    coords = [
        [32.3, 30.5],
        [32.4, 30.2],
        [32.2, 30.0],
        [32.5, 29.8],
        [32.3, 29.5]
    ]

    for i, (lon, lat) in enumerate(coords):
        payload = {
            "Message": {
                "PositionReport": {
                    "UserID": 100000000 + i,
                    "Latitude": lat,
                    "Longitude": lon,
                    "Sog": random.uniform(8.0, 15.0),
                    "TrueHeading": random.randint(0, 360),
                    "NavigationalStatus": 0
                }
            },
            "TimeUtc": datetime.utcnow().isoformat()
        }
        redis_client.lpush(REDIS_AIS_KEY, json.dumps(payload))
        
    print("Redis operations OK.")

if __name__ == "__main__":
    seed_db()
    seed_redis()
    print("Demo Seed Complete.")
