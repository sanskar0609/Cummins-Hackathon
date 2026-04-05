from app.db.session import SessionLocal
from app.models.alert_log import Alert, AlertLog, AlertSeverity
from app.models.po_draft import PODraft
from app.models.supplier import Supplier
from sqlalchemy import text

def seed():
    db = SessionLocal()
    try:
        # Clear existing to avoid duplicates in demo
        db.execute(text("TRUNCATE TABLE alerts RESTART IDENTITY CASCADE"))
        db.execute(text("TRUNCATE TABLE alert_logs RESTART IDENTITY CASCADE"))
        db.execute(text("TRUNCATE TABLE po_drafts RESTART IDENTITY CASCADE"))

        # 1. System Alerts
        db.add(Alert(
            title="SUEZ CONGESTION", 
            severity="CRITICAL", 
            message="Suez Canal blockage detected. Global transit time for SKU-001 delayed by +14 days. Re-routing mandatory."
        ))
        db.add(Alert(
            title="GEOPOLITICAL ALERT", 
            severity="WARNING", 
            message="High volatility in Port of Singapore. Loading capacity reduced by 30% for South-East Asian shipments."
        ))
        db.add(Alert(
            title="D/S RATIO CRITICAL", 
            severity="CRITICAL", 
            message="SKU-001 Demand/Supply ratio hit 2.8x in Pune West Hub. Imminent stockout risk detected."
        ))

        # 2. Alert Logs (Agentic Audit)
        db.add(AlertLog(
            alert_type="ROUTING_AGENT",
            message="Autonomous routing agent proposed stock shift from Bangalore to Chennai to bridge regional deficit.",
            severity=AlertSeverity.INFO,
            company_profile_id=None # Null-safe for demo
        ))

        # 3. Create a Dummy Supplier for the PO
        supplier = db.query(Supplier).filter(Supplier.name == "Global Logistics Corp").first()
        if not supplier:
            supplier = Supplier(name="Global Logistics Corp", location="Singapore", health_score=0.95, health_status="HEALTHY")
            db.add(supplier)
            db.flush()

        # 4. PO Drafts
        db.add(PODraft(
            company_profile_id=None, # Null-safe for demo
            supplier_id=supplier.id,
            sku="SKU-001",
            quantity=5000,
            estimated_cost=42500.0,
            status="PENDING_APPROVAL",
            justification="AI Sensing detected demand surge. Emergency procurement of 5000 units recommended."
        ))

        db.commit()
        print("Alerts & POs successfully seeded! Intelligence Timeline refined.")
    except Exception as e:
        print(f"Seeding failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
