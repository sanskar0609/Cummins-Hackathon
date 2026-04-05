from sqlalchemy import text
from app.db.session import engine

with engine.begin() as conn:
    # Explicitly check for column existence first to avoid errors
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='warehouses' AND column_name='demand'"))
    if not res.fetchone():
        print("Adding 'demand' column...")
        conn.execute(text("ALTER TABLE warehouses ADD COLUMN demand FLOAT DEFAULT 0.0"))
        print("Added.")
    else:
        print("'demand' column already exists.")
