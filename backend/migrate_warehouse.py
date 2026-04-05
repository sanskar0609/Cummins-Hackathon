from sqlalchemy import text
from app.db.session import engine

def migrate():
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE warehouses ADD COLUMN IF NOT EXISTS demand FLOAT DEFAULT 0.0"))
            print("Successfully added 'demand' column to 'warehouses' table.")
    except Exception as e:
        print(f"Migration Failed: {str(e)}")

if __name__ == "__main__":
    migrate()
