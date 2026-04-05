import asyncio
import httpx
import json
import os
import re
from datetime import datetime
from app.core.config import settings
from app.services.kafka_producer import publish_message
from app.core.logging import log

# Simple NLP severity scorer — negative keywords → higher score
_NEG_KEYWORDS = ["attack", "explosion", "closure", "sanction", "conflict",
                  "strike", "protest", "earthquake", "typhoon", "war", "seized"]
def _score_severity(title: str) -> float:
    title_lo = title.lower()
    hits = sum(1 for kw in _NEG_KEYWORDS if kw in title_lo)
    return min(1.0, round(0.2 + hits * 0.15, 2))

POLL_INTERVAL_SECONDS = 21600 # 6 hours

# Key keywords to filter out non-relevant news
RISK_KEYWORDS = [
    "conflict", "strike", "port closure", "sanctions", 
    "protest", "earthquake", "typhoon"
]

# Core countries / regions relevant to our chokepoints
REGIONS = [
    "Taiwan", "China", "Yemen", "Egypt", "Panama", 
    "Iran", "South Africa", "Denmark", "Red Sea", "Suez"
]

async def fetch_gdelt(client: httpx.AsyncClient) -> list:
    """
    Fetch articles from GDELT 2.0 API matching our risk keywords and core regions.
    """
    url = settings.GDELT_BASE_URL
    # Construct a GDELT query: (keyword OR keyword) (Region OR Region)
    kw_query = " OR ".join(f'"{kw}"' if " " in kw else kw for kw in RISK_KEYWORDS)
    reg_query = " OR ".join(f'"{reg}"' if " " in reg else reg for reg in REGIONS)
    query = f"({kw_query}) ({reg_query})"
    
    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
    }
    
    log.debug("gdelt_polling_start", query=query)
    
    try:
        response = await client.get(url, params=params, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        articles = data.get("articles", [])
        
        parsed_events = []
        for art in articles:
            parsed_events.append({
                "source": "GDELT",
                "title": art.get("title", ""),
                "url": art.get("url", ""),
                "domain": art.get("domain", ""),
                "seendate": art.get("seendate", ""),
                "timestamp_utc": datetime.utcnow().isoformat()
            })
        log.info("gdelt_polling_success", events_found=len(parsed_events))
        return parsed_events
    except httpx.HTTPStatusError as he:
        log.warning("gdelt_http_error", status=he.response.status_code)
        return []
    except Exception as e:
        log.error("gdelt_error", error=str(e))
        return []

async def fetch_rapidapi_supply_chain(client: httpx.AsyncClient) -> list:
    """
    Fetch news from the RapidAPI supply chain news endpoint.
    Filters the response internally against RISK_KEYWORDS.
    """
    if not settings.RAPIDAPI_KEY:
        log.warning("rapidapi_skip", reason="RAPIDAPI_KEY not configured")
        return []

    url = f"https://{settings.RAPIDAPI_HOST_SUPPLYCHAIN}/news"
    headers = {
        "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
        "X-RapidAPI-Host": settings.RAPIDAPI_HOST_SUPPLYCHAIN
    }
    
    try:
        response = await client.get(url, headers=headers, timeout=15.0)
        response.raise_for_status()
        
        # RapidAPI typically returns a list of articles or a dict containing a list
        data = response.json()
        articles = data if isinstance(data, list) else data.get("news", [])
        if not articles and isinstance(data, dict):
             # Try common fallback keys
             articles = data.get("articles", []) or data.get("data", [])

        # Local Keyword Filter since this API might just return raw supply chain news
        filter_pattern = re.compile("|".join(RISK_KEYWORDS), re.IGNORECASE)
        
        parsed_events = []
        for art in articles:
            title = art.get("title", "")
            description = art.get("description", "")
            content_to_check = f"{title} {description}"
            
            if filter_pattern.search(content_to_check):
                parsed_events.append({
                    "source": "RapidAPI_SupplyChain",
                    "title": title,
                    "url": art.get("url", art.get("link", "")),
                    "domain": art.get("source", ""),
                    "seendate": art.get("pubDate", art.get("publishedAt", "")),
                    "timestamp_utc": datetime.utcnow().isoformat()
                })
        log.info("rapidapi_polling_success", events_found=len(parsed_events))
        return parsed_events

    except httpx.HTTPStatusError as he:
        log.warning("rapidapi_http_error", status=he.response.status_code)
        return []
    except Exception as e:
        log.error("rapidapi_error", error=str(e))
        return []

async def poll_geo_events():
    """
    Background loop polling geopolitical sources every 6 hours.
    """
    os.makedirs(settings.DATA_RAW_PATH, exist_ok=True)
    geo_raw_path = os.path.join(settings.DATA_RAW_PATH, "geo")
    os.makedirs(geo_raw_path, exist_ok=True)

    async with httpx.AsyncClient() as client:
        while True:
            log.info("geo_polling_batch_started")
            
            # Fetch concurrently
            gdelt_task = fetch_gdelt(client)
            rapidapi_task = fetch_rapidapi_supply_chain(client)
            
            results = await asyncio.gather(gdelt_task, rapidapi_task, return_exceptions=True)
            
            batch_events = []
            for res in results:
                if isinstance(res, list):
                    batch_events.extend(res)
            
            if batch_events:
                # 1. Store to local JSON lines
                raw_log_file = os.path.join(geo_raw_path, f"geo_raw_{datetime.utcnow().strftime('%Y%m%d')}.jsonl")
                with open(raw_log_file, "a", encoding="utf-8") as f:
                    for ev in batch_events:
                        f.write(json.dumps(ev) + "\n")
                        
                        # Use URL as the unique Kafka key, fallback to timestamp
                        key = ev.get("url") or ev["timestamp_utc"]
                        
                        # 2. Publish to Kafka geo-events topic
                        publish_message(settings.KAFKA_TOPIC_GEO_EVENTS, key=key, message=ev)

                # 3. ── NEW: Persist to geo_risk_events PostgreSQL table ──────
                try:
                    from app.db.session import SessionLocal
                    from app.models.geo_risk_event import GeoRiskEvent
                    db = SessionLocal()
                    inserted = 0
                    try:
                        for ev in batch_events:
                            url = ev.get("url", "") or ""
                            title = ev.get("title", "") or ""
                            # Skip duplicates by URL
                            if url:
                                exists = db.query(GeoRiskEvent).filter(GeoRiskEvent.url == url).first()
                                if exists:
                                    continue
                            
                            # Extract rough affected region from title
                            affected = next(
                                (reg for reg in REGIONS if reg.lower() in title.lower()), None
                            )
                            
                            row = GeoRiskEvent(
                                source        = ev.get("source", "GDELT"),
                                title         = title[:500],
                                url           = url[:1000] if url else None,
                                domain        = ev.get("domain", "")[:200],
                                event_type    = next((kw for kw in RISK_KEYWORDS if kw in title.lower()), "general"),
                                affected_region = affected,
                                severity_score  = _score_severity(title),
                                seendate        = ev.get("seendate", "")[:50],
                            )
                            db.add(row)
                            inserted += 1
                        
                        db.commit()
                        log.info("geo_events_persisted_to_postgres", inserted=inserted, total=len(batch_events))
                    except Exception as db_err:
                        db.rollback()
                        log.error("geo_events_db_write_error", error=str(db_err))
                    finally:
                        db.close()
                except Exception as import_err:
                    log.error("geo_events_db_import_error", error=str(import_err))

            log.info("geo_polling_batch_complete", total_events_published=len(batch_events))
            
            # Wait 6 hours
            log.info("geo_polling_sleep", seconds=POLL_INTERVAL_SECONDS)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

# To run independently:
if __name__ == "__main__":
    asyncio.run(poll_geo_events())
