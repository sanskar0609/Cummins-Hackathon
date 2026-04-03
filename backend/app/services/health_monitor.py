import asyncio
import httpx
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import log
from app.models.health_signal import SupplierHealthSignal

async def _fetch_hunter_data(domain: str) -> dict:
    if not settings.HUNTER_API_KEY or not domain:
        return {"error": "Missing Hunter API key or domain placeholder"}
    
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={settings.HUNTER_API_KEY}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                return {
                    "pattern": data.get("pattern"),
                    "emails_found": len(data.get("emails", [])),
                    "disposable": data.get("disposable"),
                    "webmail": data.get("webmail"),
                    "organization": data.get("organization")
                }
            else:
                return {"status": "not_found", "code": resp.status_code}
    except Exception as e:
        log.error("hunter_api_error", error=str(e))
    return {}

async def _fetch_news_sentiment(company_name: str) -> dict:
    if not settings.NEWS_API_KEY:
        return {"error": "Missing NewsAPI Key"}
        
    date_from = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    url = f"https://newsapi.org/v2/everything?q={company_name}&from={date_from}&sortBy=relevancy&apiKey={settings.NEWS_API_KEY}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                articles = resp.json().get("articles", [])
                
                # NLP-lite: Flag negative sentiment context locally
                negative_keywords = ["layoff", "bankrupt", "lawsuit", "closure", "strike", "violation", "debt", "crisis"]
                flagged_articles = []
                
                # Check top 15 results
                for art in articles[:15]:
                    title = art.get("title", "").lower() if art.get("title") else ""
                    desc = art.get("description", "").lower() if art.get("description") else ""
                    
                    if any(kw in title or kw in desc for kw in negative_keywords):
                        flagged_articles.append({
                            "title": art.get("title"),
                            "url": art.get("url"),
                            "publishedAt": art.get("publishedAt")
                        })
                
                return {
                    "total_articles_30d": len(articles),
                    "flagged_issues_count": len(flagged_articles),
                    "flagged_articles": flagged_articles
                }
            else:
                return {"status": "api_quota_or_error", "code": resp.status_code}
    except Exception as e:
        log.error("news_api_error", error=str(e))
    return {}

async def _fetch_rapidapi_company_data(company_name: str) -> dict:
    """ Using Yahoo Finance endpoint off RapidAPI as a D&B proxy. """
    if not settings.RAPIDAPI_KEY:
        return {"error": "Missing RapidAPI key"}
        
    url = f"https://yahoo-finance187.p.rapidapi.com/v1/finance/search"
    headers = {
        "x-rapidapi-key": settings.RAPIDAPI_KEY,
        "x-rapidapi-host": "yahoo-finance187.p.rapidapi.com"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params={"q": company_name}, headers=headers)
            if resp.status_code == 200:
                quotes = resp.json().get("quotes", [])
                if quotes:
                    best_match = quotes[0]
                    return {
                        "exchange": best_match.get("exchange"),
                        "ticker": best_match.get("symbol"),
                        "long_name": best_match.get("longname"),
                        "sector": best_match.get("sector"),
                        "score": best_match.get("score")
                    }
    except Exception as e:
        log.error("rapidapi_company_error", error=str(e))
        
    return {"status": "Unlisted / Private"}

async def gather_and_save_health_signals(db: Session, supplier_id: str, company_name: str, domain: str=""):
    """
    Consumes all 3 operational OSINT APIs concurrently and persists the JSON payloads natively.
    """
    guess_domain = domain if domain else f"{company_name.lower().replace(' ', '')}.com"
    
    hunter_task = asyncio.create_task(_fetch_hunter_data(guess_domain))
    news_task = asyncio.create_task(_fetch_news_sentiment(company_name))
    rapid_task = asyncio.create_task(_fetch_rapidapi_company_data(company_name))
    
    hunter_res, news_res, rapid_res = await asyncio.gather(hunter_task, news_task, rapid_task)
    
    signal = SupplierHealthSignal(
        supplier_id=supplier_id,
        hunter_data=hunter_res,
        news_data=news_res,
        rapidapi_data=rapid_res
    )
    
    db.add(signal)
    db.commit()
    db.refresh(signal)
    
    log.info("supplier_health_harvested", supplier=company_name, id=supplier_id)
    return signal
