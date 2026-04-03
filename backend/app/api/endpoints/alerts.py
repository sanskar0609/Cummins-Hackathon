from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

@router.get("", response_model=List[Dict[str, Any]])
async def get_active_alerts(db: Session = Depends(get_db)):
    """
    Returns a list of active alerts by reading from the alerts table directly using raw SQL.
    """
    try:
        query = text("SELECT id, title, severity, message, created_at FROM alerts")
        result = db.execute(query)
        rows = result.fetchall()
        
        return [
            {
                "id": str(row[0]),
                "type": str(row[1]),
                "severity": str(row[2]).lower(),
                "summary": str(row[3]),
                "timestamp": str(row[4]) if row[4] else "Recent",
                "affected": "System",
                "recommendedAction": "Inspect parameters.", 
                "rawSource": "database"
            }
            for row in rows
        ]
    except Exception as e:
        print(f"Alerts extraction error: {e}")
        return []
