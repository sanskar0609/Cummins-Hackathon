from app.db.declarative import Base
from app.db.session import engine
from app.models.warehouse import Warehouse

def reset():
    print("Dropping all tables...")
    # NOTE: This is destructive for a hackathon, but since we re-seed on compute, it's fine for the warehouse table
    # To be safer, just drop the warehouses table
    Warehouse.__table__.drop(engine, checkfirst=True)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. Re-check the column status...")
    from sqlalchemy import text
    with engine.connect() as conn:
        res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='warehouses'"))
        cols = [r[0] for r in res.fetchall()]
        print(f"Current columns in 'warehouses': {cols}")

if __name__ == "__main__":
    reset()
