from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, JSON
from pydantic import BaseModel
from typing import List
import json
import pandas as pd
import io
import os
from app.core.config import settings

from app.db.session import get_db, engine
from app.db.base import Base, CompanyProfile
from app.core.logging import log

# In a real app we'd use Alembic. For hackathon, create tables:
Base.metadata.create_all(bind=engine)

router = APIRouter()

class SKUExtractRequest(BaseModel):
    description: str

class SEARCHResearchRequest(BaseModel):
    company_name: str

class SKUSaveRequest(BaseModel):
    name: str
    industry: str
    skus: List[dict]
    csv_path: str = None

@router.post("/extract-skus")
async def extract_skus_from_text(payload: SKUExtractRequest):
    from app.services.agents.product_researcher import research_products_via_search
    
    clean_desc = payload.description.strip()
    
    # If the input looks like a simple company name or a URL, use search research:
    if len(clean_desc.split()) < 5 or clean_desc.startswith("http"):
        log.info("triggering_search_based_research", query=clean_desc)
        research_result = await research_products_via_search(clean_desc)
        return research_result
    
    # Otherwise, fallback to the existing direct AI extraction from the text:
    from app.core.gemini_rotator import async_generate_with_retry
    prompt = f"""
    You are a supply chain categorization AI. The user has described their business/products.
    Extract the distinct products they sell into structured JSON.
    User description: "{clean_desc}"
    Return ONLY valid JSON (no markdown, no backticks, no text) in this exact format:
    [
      {{"sku": "AUTO-GEN-001", "name": "Product Name", "category": "Category", "description": "some info"}}
    ]
    """
    try:
        raw = await async_generate_with_retry(prompt)
        # Basic cleanup
        clean = raw.strip()
        if clean.startswith("```json"): clean = clean[7:-3].strip()
        elif clean.startswith("```"): clean = clean[3:-3].strip()
        
        start = clean.find('[')
        end = clean.rfind(']')
        if start != -1 and end != -1:
            clean = clean[start:end+1]
        data = json.loads(clean)
        return {"skus": data, "count": len(data), "csv_path": None}
    except Exception as e:
        log.error("ai_sku_extract_failed", error=str(e))
        # If Gemini is failing, maybe it's because of the model version or key issues.
        # We can try to provide a more helpful error message.
        error_msg = str(e)
        if "429" in error_msg:
            error_msg = "Gemini API rate limit reached. Please wait a moment or try again later."
        elif "not found" in error_msg.lower():
            error_msg = "Gemini model not found or access denied. Check your API keys and model permissions."
            
        return {"error": error_msg, "skus": [], "count": 0}

@router.post("/upload-csv")
async def upload_csv_to_skus(file: UploadFile = File(...)):
    """
    Allows user to upload a CSV file with SKUs.
    Expected columns: sku, name, category, description
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    
    try:
        contents = await file.read()
        # Handle different encodings
        try:
            df = pd.read_csv(io.BytesIO(contents))
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(contents), encoding='latin1')

        # Clean column names (strip whitespace and lower case for matching)
        df.columns = [c.strip().lower() for c in df.columns]
        
        # Mapping logic
        mapping = {
            'sku': ['sku', 'id', 'product id', 'part number'],
            'name': ['name', 'product name', 'title', 'item'],
            'category': ['category', 'type', 'group'],
            'description': ['description', 'info', 'details', 'summary']
        }
        
        final_df = pd.DataFrame()
        for target, aliases in mapping.items():
            found = False
            for alias in aliases:
                if alias in df.columns:
                    final_df[target] = df[alias]
                    found = True
                    break
            if not found:
                if target == 'sku': final_df['sku'] = [f"SKU-{i+1:03d}" for i in range(len(df))]
                elif target == 'category': final_df['category'] = "Uncategorized"
                elif target == 'description': final_df['description'] = ""
                else: final_df[target] = "Unknown"

        skus = final_df.to_dict(orient='records')[:20]
        
        # Save the uploaded file to data/processed for consistency
        os.makedirs(settings.DATA_PROCESSED_PATH, exist_ok=True)
        save_path = os.path.join(settings.DATA_PROCESSED_PATH, f"uploaded_{file.filename}")
        with open(save_path, "wb") as f:
            f.write(contents)

        return {
            "skus": skus, 
            "count": len(skus), 
            "csv_path": save_path
        }
    except Exception as e:
        log.error("csv_upload_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {str(e)}")


@router.post("/scrape-search-to-db")
async def scrape_search_to_db(payload: SEARCHResearchRequest, db: Session = Depends(get_db)):
    """
    1. Searches for company info via search engine.
    2. Extracts structured SKU data.
    3. Saves into the CompanyProfile and generates a CSV.
    """
    from app.services.agents.product_researcher import research_products_via_search
    import uuid

    try:
        # Step 1 & 2: Search research
        research_result = await research_products_via_search(payload.company_name)
        
        if not research_result.get("skus"):
             return {"status": "error", "message": "No products found."}

        # Step 3: Automatically Save into Database
        profile = db.query(CompanyProfile).first()
        if not profile:
            profile = CompanyProfile(name=payload.company_name, industry="Auto-Detected")
            db.add(profile)
            db.commit()
            db.refresh(profile)
            
        profile.skus = research_result["skus"]
        profile.csv_path = research_result["csv_path"]
        db.commit()
        db.refresh(profile)
        
        return {
            "status": "success",
            "message": "Market research complete and products saved to dashboard.",
            "extracted_count": research_result["count"],
            "csv_path": research_result["csv_path"],
            "all_skus": profile.skus
        }

    except Exception as e:
        log.error("search_to_db_failed", query=payload.company_name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Market research failed: {str(e)}")


@router.post("/save")
def save_company_profile(payload: SKUSaveRequest, db: Session = Depends(get_db)):
    try:
        profile = CompanyProfile()
        db.add(profile)
        
        profile.name = payload.name
        profile.industry = payload.industry
        profile.skus = payload.skus
        profile.csv_path = payload.csv_path if payload.csv_path else ""
        db.commit()
        db.refresh(profile)
        return {"status": "success", "message": "Company profile and SKUs saved.", "company_id": profile.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile")
def get_company_profile(company_id: int = Query(None), db: Session = Depends(get_db)):
    if company_id:
        profile = db.query(CompanyProfile).filter(CompanyProfile.id == company_id).first()
    else:
        profile = db.query(CompanyProfile).order_by(CompanyProfile.id.desc()).first()

    if profile:
        return {
            "id": profile.id,
            "name": profile.name,
            "industry": profile.industry,
            "skus": profile.skus,
        }
    return {"id": None, "name": "", "industry": "", "skus": []}
