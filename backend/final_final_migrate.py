from app.db.declarative import Base
from app.db.session import engine
from sqlalchemy import text

# Import ALL models so Base knows about them
from app.models.warehouse import Warehouse
# Assuming there is a company profile model
# Let me search for it
import os

def reset():
    print("Force adding demand column via ALTER SQL...")
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE warehouses ADD COLUMN IF NOT EXISTS demand FLOAT DEFAULT 0.0"))
            print("SQL ALTER success.")
    except Exception as e:
        print(f"SQL ALTER failed: {str(e)}")

if __name__ == "__main__":
    reset()
