import asyncio
import json
import os
import aiohttp
from datetime import datetime, timedelta
import google.generativeai as genai
from typing import Dict, Any, List
from dotenv import load_dotenv
import threading
import time

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# --- Gemini Multi-Key Rotator (inline for standalone agent) ---
def _load_gemini_keys():
    raw = [
        os.environ.get("GEMINI_API_KEY",   ""),
        os.environ.get("GEMINI_API_KEY_2", ""),
        os.environ.get("GEMINI_API_KEY_3", ""),
        os.environ.get("GEMINI_API_KEY_4", ""),
        os.environ.get("GEMINI_API_KEY_5", ""),
    ]
    return [k.strip() for k in raw if k.strip()]

_gemini_keys  = _load_gemini_keys()
_gemini_lock  = threading.Lock()
_gemini_idx   = 0
print(f"[GeminiRotator] Loaded {len(_gemini_keys)} Gemini key(s)")

def _next_gemini_key():
    global _gemini_idx
    if not _gemini_keys:
        return None
    with _gemini_lock:
        key = _gemini_keys[_gemini_idx % len(_gemini_keys)]
        _gemini_idx += 1
        return key

def _gemini_generate(prompt: str, model_name: str = "gemini-2.0-flash") -> str:
    """Rotates through all Gemini keys on 429, then falls back to Groq."""
    last_err = None
    for attempt in range(max(len(_gemini_keys), 1)):
        key = _next_gemini_key()
        if not key:
            break
        try:
            genai.configure(api_key=key)
            m = genai.GenerativeModel(model_name)
            resp = m.generate_content(prompt)
            return resp.text
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "rate" in err.lower():
                print(f"[GeminiRotator] Key quota hit (attempt {attempt+1}), rotating...")
                last_err = e
                time.sleep(0.3 * (attempt + 1))
                continue
            raise
    # All Gemini keys exhausted — try Groq
    print("[GeminiRotator] All Gemini keys exhausted — falling back to Groq...")
    return _groq_generate(prompt)

# --- Groq Multi-Key Rotator (inline for standalone agent) ---
def _load_groq_keys():
    raw = [
        os.environ.get("GROQ_API_KEY",   ""),
        os.environ.get("GROQ_API_KEY_2", ""),
        os.environ.get("GROQ_API_KEY_3", ""),
        os.environ.get("GROQ_API_KEY_4", ""),
        os.environ.get("GROQ_API_KEY_5", ""),
    ]
    return [k.strip() for k in raw if k.strip()]

_groq_keys = _load_groq_keys()
_groq_lock  = threading.Lock()
_groq_idx   = 0
print(f"[GroqRotator]   Loaded {len(_groq_keys)} Groq key(s)")

def _next_groq_key():
    global _groq_idx
    if not _groq_keys:
        return None
    with _groq_lock:
        key = _groq_keys[_groq_idx % len(_groq_keys)]
        _groq_idx += 1
        return key

def _groq_generate(prompt: str) -> str:
    """Rotates through all Groq keys on 429."""
    try:
        from groq import Groq as GroqClient
    except ImportError:
        raise RuntimeError("groq package not installed.")
    last_err = None
    for attempt in range(max(len(_groq_keys), 1)):
        key = _next_groq_key()
        if not key:
            raise RuntimeError("No Groq API keys configured.")
        try:
            client = GroqClient(api_key=key)
            resp = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful supply chain AI assistant."},
                    {"role": "user",   "content": prompt},
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                max_tokens=2048,
            )
            return resp.choices[0].message.content
        except Exception as e:
            err = str(e)
            if "429" in err or "rate" in err.lower() or "quota" in err.lower():
                print(f"[GroqRotator] Key rate-limited (attempt {attempt+1}), rotating...")
                last_err = e
                time.sleep(0.3 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"All Groq keys exhausted. Last error: {last_err}")

# --- 1. Parsing Query ---
async def parse_query_with_gemini(raw_query: str) -> Dict[str, Any]:
    """
    Takes the raw user text and returns structured parameters for searching.
    """
    prompt = f"""
    You are an AI demand sensing assistant. Extract the search parameters from the user's query.
    Return ONLY a valid JSON object with the following schema:
    {{
        "keywords": ["list", "of", "search", "terms"],
        "location": "geographic location if mentioned, or 'Global'",
        "product_category": "the core product being requested",
        "timeframe_days": integer (e.g., 30 for last month, default to 30)
    }}

    User Query: "{raw_query}"
    Output only raw JSON, no markdown blocks.
    """
    try:
        raw = await asyncio.to_thread(_gemini_generate, prompt)
        clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception as e:
        print(f"Error parsing query: {e}")
        return {
            "keywords": [raw_query.split()[0]],
            "location": "Global",
            "product_category": raw_query,
            "timeframe_days": 30
        }

# --- 2. Fetching Sources ---
async def fetch_youtube(session: aiohttp.ClientSession, params: dict) -> List[dict]:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    query = " ".join(params['keywords'])
    if not api_key:
        return [{"source": "YouTube", "error": "Missing YOUTUBE_API_KEY", "content": f"Simulated YT result for {query}"}]
    
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&maxResults=10&key={api_key}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                results = []
                for item in data.get("items", []):
                    snippet = item.get("snippet", {})
                    results.append({
                        "source": "YouTube",
                        "title": snippet.get("title"),
                        "content": snippet.get("description"),
                        "published_at": snippet.get("publishedAt")
                    })
                return results
            else:
                return [{"source": "YouTube", "error": f"API Error {response.status}"}]
    except Exception as e:
        return [{"source": "YouTube", "error": str(e)}]

async def fetch_newsapi(session: aiohttp.ClientSession, params: dict) -> List[dict]:
    api_key = os.environ.get("NEWS_API_KEY")
    query = " ".join(params['keywords'])
    if not api_key:
        return [{"source": "NewsAPI", "error": "Missing NEWS_API_KEY", "content": f"Simulated News result for {query}"}]
    
    url = f"https://newsapi.org/v2/everything?q={query}&sortBy=relevancy&pageSize=10&apiKey={api_key}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                results = []
                for article in data.get("articles", []):
                    results.append({
                        "source": "News",
                        "title": article.get("title"),
                        "content": article.get("description"),
                        "published_at": article.get("publishedAt")
                    })
                return results
            else:
                return [{"source": "News", "error": f"API Error {response.status}"}]
    except Exception as e:
        return [{"source": "News", "error": str(e)}]

async def fetch_reddit(session: aiohttp.ClientSession, params: dict) -> List[dict]:
    # Reddit search via JSON endpoint without auth (rate limited but works for small requests)
    query = " ".join(params['keywords'])
    url = f"https://www.reddit.com/search.json?q={query}&sort=new&limit=10"
    headers = {"User-Agent": "DemandSensingAgent/1.0"}
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                results = []
                for post in data.get("data", {}).get("children", []):
                    post_data = post.get("data", {})
                    results.append({
                        "source": "Reddit",
                        "title": post_data.get("title"),
                        "content": post_data.get("selftext"),
                        "score": post_data.get("score", 0)
                    })
                return results
            else:
                return [{"source": "Reddit", "error": f"API Error {response.status}"}]
    except Exception as e:
        return [{"source": "Reddit", "error": str(e)}]

def _sync_fetch_pytrends(params: dict) -> List[dict]:
    # pytrends is synchronous, wrapping in thread
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        kw_list = params['keywords'][:5] # Max 5 for pytrends
        if not kw_list:
            return []
        pytrends.build_payload(kw_list, cat=0, timeframe='today 1-m', geo='')
        df = pytrends.interest_over_time()
        if df.empty:
            return []
        
        # Get recent trend
        recent_data = df.tail(7).to_dict()
        return [{"source": "Google Trends", "content": f"Recent trend data: {recent_data}"}]
    except Exception as e:
        return [{"source": "Google Trends", "error": str(e)}]

async def fetch_pytrends(params: dict) -> List[dict]:
    return await asyncio.to_thread(_sync_fetch_pytrends, params)

async def fetch_all_sources(params: dict) -> Dict[str, List[dict]]:
    """
    Calls YouTube, NewsAPI, Reddit and Pytrends in parallel.
    """
    async with aiohttp.ClientSession() as session:
        yt_task = fetch_youtube(session, params)
        news_task = fetch_newsapi(session, params)
        reddit_task = fetch_reddit(session, params)
        trends_task = fetch_pytrends(params)
        
        # Run all concurrently
        yt_data, news_data, reddit_data, trends_data = await asyncio.gather(
            yt_task, news_task, reddit_task, trends_task
        )
        
        return {
            "youtube": yt_data,
            "news": news_data,
            "reddit": reddit_data,
            "trends": trends_data
        }

# --- 3. Filtering and Tagging ---
async def filter_with_groq(raw_data: Dict[str, List[dict]], params: dict) -> List[Dict]:
    """
    Sends results to Groq with a tight prompt that only keeps relevant items and tags them 
    as demand/disruption/sentiment signals.
    """
    # Flatten data to a single list of strings
    items_to_evaluate = []
    for source, items in raw_data.items():
        if not items: continue
        for item in items:
            if "error" in item: continue
            text = f"Source: {item.get('source')} | Title: {item.get('title', '')} | Content: {item.get('content', '')}"
            items_to_evaluate.append(text)
            
    # If no data or too large, batch or truncate
    text_corpus = "\n---\n".join(items_to_evaluate)[:15000] # Cap roughly at ~3500 tokens for safety
    
    prompt = f"""
    You are a supply chain intelligence filter. Review the following scraped data items.
    The primary context is: Product: {params.get('product_category')}, Location: {params.get('location')}.
    
    Keep ONLY the items that are directly relevant to demand changes, supply chain disruptions, or consumer sentiment.
    Tag each relevant item with:
    - type: "demand" or "disruption" or "sentiment"
    - signal_strength: an integer from 1 to 10 (10 being a massive impact)
    - summary: a short 1-sentence reason why it's relevant
    
    Return a strictly valid JSON object with a single key "signals" containing an array of objects with the schema:
    [{{ "source": "...", "type": "...", "signal_strength": X, "summary": "..." }}]
    
    Items:
    {text_corpus}
    """
    
    try:
        from groq import Groq as GroqClient
        last_err = None
        attempts = min(len(_groq_keys), 5) if _groq_keys else 0
        for attempt in range(max(attempts, 1)):
            api_key = _next_groq_key()
            if not api_key:
                print("No Groq keys available for filtering")
                return []
            try:
                client = GroqClient(api_key=api_key)
                response = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a helpful JSON-only assistant. Return valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
                data = json.loads(content)
                tags = data.get("signals", [])
                return tags if isinstance(tags, list) else []
            except Exception as inner_e:
                err_str = str(inner_e)
                if "429" in err_str or "rate" in err_str.lower() or "quota" in err_str.lower():
                    print(f"[GroqRotator] Key rate-limited (attempt {attempt+1}), rotating...")
                    last_err = inner_e
                    time.sleep(0.3 * (attempt + 1))
                    continue
                raise
        print(f"All Groq keys exhausted: {last_err}")
        return []
    except Exception as e:
        print(f"Error in filter_with_groq: {e}")
        return []

# --- 4. Prediction Engine ---
def predict_requirement(filtered_signals: List[Dict], baseline_units: int = 1000) -> Dict[str, Any]:
    """
    Computes a weighted demand score, applies disruption penalty, and outputs units needed + conf interval.
    """
    demand_multiplier = 1.0
    disruption_penalty = 1.0
    sentiment_boost = 1.0
    
    signal_count = len(filtered_signals)
    confidence = min(40 + (signal_count * 5), 95) # Baseline 40%, capped at 95%
    
    for signal in filtered_signals:
        strength = signal.get("signal_strength", 5) / 10.0 # Normalize 0 to 1
        
        if signal.get("type") == "demand":
            demand_multiplier += (0.1 * strength) # Up to 10% increase per strong signal
        elif signal.get("type") == "disruption":
            disruption_penalty -= (0.15 * strength) # Up to 15% drop in availability / need
        elif signal.get("type") == "sentiment":
            sentiment_boost += (0.05 * strength) # Up to 5% boost for positive hype
            
    # Keep bounds realistic
    disruption_penalty = max(disruption_penalty, 0.4) 
    
    # Calculate final units
    final_multiplier = demand_multiplier * sentiment_boost * disruption_penalty
    predicted_units = int(baseline_units * final_multiplier)
    
    # Establish a rough confidence interval
    margin = (100 - confidence) / 100.0
    lower_bound = int(predicted_units * (1 - margin))
    upper_bound = int(predicted_units * (1 + margin))
    
    # Sort signals by signal_strength descending for Explainable AI
    sorted_signals = sorted(filtered_signals, key=lambda x: x.get("signal_strength", 0), reverse=True)
    
    return {
        "baseline_units": baseline_units,
        "predicted_units": predicted_units,
        "confidence_interval": f"{lower_bound} - {upper_bound}",
        "confidence_percentage": f"{confidence}%",
        "factors": {
            "demand_multiplier": round(demand_multiplier, 2),
            "disruption_penalty": round(disruption_penalty, 2),
            "sentiment_boost": round(sentiment_boost, 2)
        },
        "extracted_signals": signal_count,
        "xai_signals": sorted_signals[:5]  # Top 5 signals for XAI
    }

# --- 5. Generate Insights ---
async def generate_insights_with_gemini(filtered_signals: List[Dict], target: Dict[str, Any], params: dict) -> str:
    """
    Generates supply chain insights — uses Gemini rotator, falls back to Groq.
    """
    prompt = f"""
    Based on the following extracted supply chain signals for {params.get('product_category')} in {params.get('location')},
    and the computed demand parameters: {json.dumps(target)}, generate exactly 3 highly actionable strategic insights.
    
    Signals: {json.dumps(filtered_signals)}
    """
    try:
        return await asyncio.to_thread(_gemini_generate, prompt)
    except Exception as e:
        print(f"Error generating insights: {e}")
        return "Insight generation failed."

# --- Main Orchestrator ---
async def run_pipeline(user_query: str, baseline_units: int = 1000):
    print(f"1. Parsing Query: '{user_query}'...")
    params = await parse_query_with_gemini(user_query)
    print(f"   Parsed Params: {params}")
    
    print("\n2. Fetching Raw Sources (YouTube, NewsAPI, Reddit, Google Trends) concurrently...")
    raw_data = await fetch_all_sources(params)
    total_items = sum(len(items) for items in raw_data.values())
    print(f"   Fetched {total_items} raw items from {len(raw_data)} sources.")
    
    print("\n3. Filtering & Tagging Signals with Groq...")
    filtered_signals = await filter_with_groq(raw_data, params)
    print(f"   Kept {len(filtered_signals)} highly relevant signals.")
    for sig in filtered_signals:
        print(f"     - [{sig.get('type', 'N/A').upper()}] (Strength {sig.get('signal_strength')}): {sig.get('summary')}")
        
    print("\n4. Predicting Requirements...")
    target = predict_requirement(filtered_signals, baseline_units)
    
    print("\n5. Generating Insights with Gemini...")
    insights = await generate_insights_with_gemini(filtered_signals, target, params)
    target["insights"] = insights
    
    print("\n===============================")
    print("      FINAL PREDICTION         ")
    print("===============================")
    print(json.dumps(target, indent=2))
    return target

# If run directly as a script
if __name__ == "__main__":
    test_query = "Surge in demand for heavy-duty diesel engines and generators in India, coupled with severe high-grade steel import shortages and port delays."
    asyncio.run(run_pipeline(test_query, baseline_units=8500))
