import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

# Matches the constant defined in the digest generator
REPORTS_DIR = Path("data/reports")

@router.get("/weekly", summary="Fetch Latest Weekly Digest", tags=["Reports"])
async def get_latest_weekly_digest():
    """
    Returns the most recently generated weekly digest (PDF or HTML fallback).
    Returns 404 if the Airflow cron job has never executed successfully.
    """
    if not REPORTS_DIR.exists():
        raise HTTPException(status_code=404, detail="Reports directory empty. Airflow job has never executed.")
    
    # Grab all generated reports in the volume
    files = []
    for ext in ("*.pdf", "*.html"):
        files.extend(list(REPORTS_DIR.glob(ext)))
        
    if not files:
        raise HTTPException(status_code=404, detail="No digests exist yet. Wait for Monday 8AM UTC or manually trigger Airflow DAG.")
        
    # Sort files strictly by modification time descending
    files.sort(key=os.path.getmtime, reverse=True)
    latest = files[0]
    
    return FileResponse(
        str(latest.absolute()),
        media_type="application/pdf" if latest.suffix == ".pdf" else "text/html",
        filename=latest.name
    )
