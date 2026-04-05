import os
import json
import pandas as pd
from ddgs import DDGS
from app.core.gemini_rotator import async_generate_with_retry
from app.core.config import settings
from app.core.logging import log

async def research_products_via_search(query: str):
    """
    Search DuckDuckGo for products/catalogs of a company or topic,
    extract them via Gemini, and save to a CSV.
    """
    log.info("research_products_started", query=query)
    
    # 1. Search DuckDuckGo
    search_results = []
    try:
        with DDGS() as ddgs:
            search_query = f"{query} product catalog list price"
            log.info("searching_duckduckgo", query=search_query)
            # Use max_results generator
            results = ddgs.text(search_query, max_results=10)
            for r in results:
                log.info("search_result_found", title=r.get('title'))
                search_results.append(f"Title: {r.get('title')}\nSnippet: {r.get('body')}\nURL: {r.get('href')}")
            log.info("search_complete", found_count=len(search_results))
    except Exception as e:
        log.error("duckduckgo_search_failed", error=str(e))
        search_results = ["Search failed, relying on internal knowledge."]

    corpus = "\n\n---\n\n".join(search_results)

    # 2. Extract structured SKUs via Gemini
    prompt = f"""
    You are a supply chain intelligence agent.
    Based on the following search results about "{query}", extract a list of distinct products/SKUs.
    If the search results are insufficient, use your internal knowledge about "{query}" to provide a realistic product range.
    
    Search Results:
    {corpus}
    
    Return ONLY a valid JSON array of objects with exactly this schema:
    [
      {{"sku": "SKU-ID", "name": "Product Name", "category": "Product Category", "description": "Brief info"}}
    ]
    """
    
    try:
        log.info("sending_to_ai_for_extraction", results_count=len(search_results))
        raw_response = await async_generate_with_retry(prompt)
        log.info("ai_extraction_received")
        
        clean_json = raw_response.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:-3].strip()
        elif clean_json.startswith("```"):
            clean_json = clean_json[3:-3].strip()
            
        products = json.loads(clean_json)
        log.info("parsing_complete", product_count=len(products) if isinstance(products, list) else 0)
        
        # 3. Save to CSV
        if products:
            df = pd.DataFrame(products)
            # Ensure directory exists
            os.makedirs(settings.DATA_PROCESSED_PATH, exist_ok=True)
            filename = f"products_{query.lower().replace(' ', '_')}.csv"
            file_path = os.path.join(settings.DATA_PROCESSED_PATH, filename)
            df.to_csv(file_path, index=False)
            log.info("products_csv_saved", path=file_path)
            
            return {
                "skus": products,
                "csv_path": file_path,
                "count": len(products)
            }
            
        return {"skus": [], "csv_path": None, "count": 0}

    except Exception as e:
        log.error("product_research_extraction_failed", error=str(e))
        return {"error": str(e), "skus": [], "csv_path": None, "count": 0}
