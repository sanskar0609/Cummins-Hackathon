"""
demand_agent_service.py — Multi-Source Real-Time Demand Sensing Agent

Sources (all date-filtered to last 90 days):
  1. YouTube          — video metadata + top comments (consumer voice)
  2. NewsAPI          — supply chain & product news
  3. Reddit           — public JSON API, subreddits for product sentiment
  4. Google Trends    — pytrends interest over time (last 3 months)
  5. DuckDuckGo       — e-commerce & web results for product demand signals
  6. Fake Store API   — e-commerce product category pricing signals (public)
  7. GDELT            — geopolitical event signals affecting supply chains

All signals are scored by recency. Signals older than 90 days are discarded.
Gemini then performs deep semantic analysis on the collected corpus.
"""

import asyncio
import json
import os
import time
import hashlib
import aiohttp
import google.generativeai as genai
try:
    from groq import Groq as GroqClient
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..", ".env"))
load_dotenv(env_path)

# ─── TTL Cache (30 minutes) ───────────────────────────────────────────────────
_CACHE: Dict[str, Dict] = {}          # key → {"result": ..., "ts": epoch_float}
_CACHE_TTL_SECONDS = 1800             # 30 minutes

def _cache_key(user_query: str, baseline_units: int) -> str:
    raw = f"{user_query.strip().lower()}|{baseline_units}"
    return hashlib.md5(raw.encode()).hexdigest()

def _cache_get(key: str):
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL_SECONDS:
        return entry["result"]
    return None

def _cache_set(key: str, result: Dict):
    _CACHE[key] = {"result": result, "ts": time.time()}

# ─── Recency Config ───────────────────────────────────────────────────────────
MAX_SIGNAL_AGE_DAYS = 180         # signals older than this are discarded
RECENCY_TIERS = {
    "last_7_days":  1.5,
    "last_30_days": 1.3,
    "last_90_days": 1.1,
    "last_180_days": 1.0,
}

def _recency_score(published_str: str) -> float:
    """Returns a recency multiplier. Returns 0 if too old."""
    if not published_str:
        return 1.0
    try:
        dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - dt).days
        if age_days > MAX_SIGNAL_AGE_DAYS:
            return 0.0  # too stale — discard
        if age_days <= 7:
            return RECENCY_TIERS["last_7_days"]
        if age_days <= 30:
            return RECENCY_TIERS["last_30_days"]
        if age_days <= 90:
            return RECENCY_TIERS["last_90_days"]
        return RECENCY_TIERS["last_180_days"]
    except Exception:
        return 1.0

# ─── Gemini Setup (Key Rotator) ──────────────────────────────────────────────
try:
    from app.core.gemini_rotator import async_generate_with_retry as _gemini_gen
    _GEMINI_ROTATOR = True
except ImportError:
    _GEMINI_ROTATOR = False
    def _setup_gemini():
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set.")
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-1.5-flash")
    model = _setup_gemini()

# ─── Groq Setup (Key Rotator — ultra-fast, free tier) ─────────────────────────
try:
    from app.core.groq_rotator import async_chat_with_rotation as _groq_chat, is_available as _groq_available
    _GROQ_ROTATOR = _groq_available()
except ImportError:
    _GROQ_ROTATOR = False

# ─── Step 1: Deep Intent Extraction (Groq → Gemini fallback) ───────────────
async def extract_intent(raw_query: str) -> Dict[str, Any]:
    today = datetime.now().strftime("%B %d, %Y")
    # Lean prompt — same structured output, fewer wasted tokens
    prompt = f"""Today is {today}. Supply chain query: "{raw_query}"
Enrich the search queries using your broad knowledge of CURRENT global macroeconomic events, supply chain drivers, and specific raw materials used to assemble these products. For example, if the query is "induction stove", you MUST consider why demand might be surging, and trace it back to raw materials like copper, steel, or specific semiconductor chips. Add these contextual keywords to the news and youtube queries so we pull highly relevant data!

Return ONLY valid JSON:
{{"brand_or_context":"<brand/topic>","primary_product":"<most in-demand product now>","product_categories":["<c1>","<c2>","<c3>"],"impacted_raw_materials":["<m1>","<m2>"],"youtube_query":"<enriched YouTube search>","news_query":"<enriched news search containing macro trends/shortages/raw materials>","reddit_subreddits":["<sub1>","<sub2>"],"reddit_query":"<Reddit search>","ecommerce_category":"<product category>","location":"<region or Global>","baseline_units_30day":<realistic 30d units>}}"""

    # ── Try Groq first (llama-3.3-70b — sub-second, rotated keys) ────────────
    if _GROQ_ROTATOR:
        try:
            raw = await asyncio.wait_for(
                _groq_chat(
                    messages=[
                        {"role": "system", "content": "You are a supply chain AI that returns only valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=512,
                    response_format={"type": "json_object"},
                ),
                timeout=25.0   # hard 25s cap — prevents silent hang on rate-limit retry
            )
            print("   [Intent] Groq ✓ (llama-3.3-70b, rotated keys)")
            return json.loads(raw)
        except asyncio.TimeoutError:
            print("   [Intent] Groq timed out (>25s), falling back to Gemini...")
        except Exception as e:
            print(f"   [Intent] Groq failed ({e}), falling back to Gemini...")

    # ── Gemini fallback ───────────────────────────────────────────────────
    print("   [Intent] Gemini fallback")
    try:
        if _GEMINI_ROTATOR:
            raw = await asyncio.wait_for(_gemini_gen(prompt), timeout=30.0)
        else:
            resp = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt), timeout=30.0
            )
            raw = resp.text
        clean = raw.strip()
        start_idx = clean.find('{')
        end_idx   = clean.rfind('}')
        if start_idx != -1 and end_idx != -1:
            clean = clean[start_idx:end_idx+1]
        return json.loads(clean)
    except (asyncio.TimeoutError, Exception) as e:
        print(f"   [Intent] Gemini also failed ({e}). Using keyword-only fallback.")

    # ── Fast local keyword fallback (no LLM needed) ───────────────────────
    words = raw_query.lower().split()
    return {
        "brand_or_context":    raw_query,
        "primary_product":     raw_query,
        "product_categories":  words[:3],
        "impacted_raw_materials": [],
        "youtube_query":       f"{raw_query} supply chain demand 2025",
        "news_query":          f"{raw_query} shortage supply chain disruption",
        "reddit_subreddits":   ["supplychain", "economics"],
        "reddit_query":        raw_query,
        "ecommerce_category":  raw_query,
        "location":            "Global",
        "baseline_units_30day": 1000
    }


# ─── Source 1: YouTube (videos + comments, date-filtered) ────────────────────
async def fetch_youtube(session: aiohttp.ClientSession, intent: Dict) -> List[Dict]:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return []

    # Fetch videos published in last 180 days for full 90v90 comparison
    published_after = (datetime.utcnow() - timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")
    search_url = (
        f"https://www.googleapis.com/youtube/v3/search"
        f"?part=snippet&q={intent['youtube_query']}&type=video&maxResults=5"
        f"&publishedAfter={published_after}&relevanceLanguage=en&key={api_key}"
    )

    signals = []
    try:
        async with session.get(search_url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()

        video_ids = []
        for item in data.get("items", []):
            vid_id = item.get("id", {}).get("videoId")
            published = item.get("snippet", {}).get("publishedAt", "")
            recency = _recency_score(published)
            if recency == 0:
                continue
            title = item.get("snippet", {}).get("title", "")
            desc = item.get("snippet", {}).get("description", "")[:200]
            signals.append({
                "source": "YouTube",
                "content": f"[VIDEO] {title} — {desc}",
                "published": published,
                "recency_score": recency,
                "type": "video_metadata"
            })
            if vid_id:
                video_ids.append(vid_id)

        # Fetch comments from top video
        if video_ids:
            comments_url = (
                f"https://www.googleapis.com/youtube/v3/commentThreads"
                f"?part=snippet&videoId={video_ids[0]}&maxResults=40&order=relevance&key={api_key}"
            )
            async with session.get(comments_url) as resp:
                if resp.status == 200:
                    cdata = await resp.json()
                    for item in cdata.get("items", []):
                        tc = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                        text = tc.get("textDisplay", "")
                        published = tc.get("publishedAt", "")
                        recency = _recency_score(published)
                        if recency == 0 or len(text) < 15:
                            continue
                        signals.append({
                            "source": "YouTube Comment",
                            "content": text[:300],
                            "published": published,
                            "recency_score": recency,
                            "likes": tc.get("likeCount", 0),
                            "type": "consumer_opinion"
                        })
    except Exception as e:
        print(f"[YouTube Error] {e}")

    return signals


# ─── Source 2: NewsAPI (date-filtered to last 30 days) ───────────────────────
async def fetch_news(session: aiohttp.ClientSession, intent: Dict) -> List[Dict]:
    api_key = os.environ.get("NEWS_API_KEY")
    if not api_key:
        return []

    from_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    url = (
        f"https://newsapi.org/v2/everything?q={intent['news_query']}"
        f"&from={from_date}&sortBy=publishedAt&pageSize=15&language=en&apiKey={api_key}"
    )
    signals = []
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            for article in data.get("articles", []):
                published = article.get("publishedAt", "")
                recency = _recency_score(published)
                if recency == 0:
                    continue
                text = f"{article.get('title', '')} — {article.get('description', '')}"
                signals.append({
                    "source": "News",
                    "content": text[:400],
                    "published": published,
                    "recency_score": recency,
                    "type": "news"
                })
    except Exception as e:
        print(f"[News Error] {e}")

    return signals


# ─── Source 3: Reddit (public API, no auth, date-filtered) ───────────────────
async def fetch_reddit(session: aiohttp.ClientSession, intent: Dict) -> List[Dict]:
    query = intent.get("reddit_query", intent.get("primary_product", ""))
    signals = []

    # Search global Reddit
    url = f"https://www.reddit.com/search.json?q={query}&sort=new&t=month&limit=20"
    headers = {"User-Agent": "SupplyChainOS/1.0"}
    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            now_ts = datetime.utcnow().timestamp()
            for post in data.get("data", {}).get("children", []):
                pd = post.get("data", {})
                created_ts = pd.get("created_utc", 0)
                age_days = (now_ts - created_ts) / 86400
                if age_days > MAX_SIGNAL_AGE_DAYS:
                    continue
                recency = 1.5 if age_days <= 7 else (1.2 if age_days <= 30 else 1.0)
                title = pd.get("title", "")
                selftext = pd.get("selftext", "")[:200]
                score = pd.get("score", 0)
                signals.append({
                    "source": "Reddit",
                    "content": f"{title}. {selftext}".strip(),
                    "recency_score": recency,
                    "score": score,
                    "type": "social_media"
                })
    except Exception as e:
        print(f"[Reddit Error] {e}")

    return signals


# ─── Source 4: Google Trends via Pytrends (last 3 months) ────────────────────
async def fetch_trends(intent: Dict) -> List[Dict]:
    def _sync_trends():
        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl='en-US', tz=330)
            keywords = [intent.get("primary_product", "")][:5]
            pytrends.build_payload(keywords, cat=0, timeframe='today 3-m', geo='')
            df = pytrends.interest_over_time()
            if df.empty:
                return []
            recent = df.tail(4)
            kw = keywords[0]
            avg = float(recent[kw].mean()) if kw in recent.columns else 50.0
            trend_direction = "rising" if float(recent[kw].iloc[-1]) > float(recent[kw].iloc[0]) else "declining"
            return [{
                "source": "Google Trends",
                "content": f"'{kw}' search interest avg {avg:.0f}/100 over last 4 weeks, trend is {trend_direction}.",
                "recency_score": 1.5,
                "type": "trend"
            }]
        except Exception as e:
            print(f"[Trends Error] {e}")
            return []
    return await asyncio.to_thread(_sync_trends)


# ─── Source 5: DuckDuckGo (e-commerce & web demand signals) ──────────────────
async def fetch_duckduckgo(session: aiohttp.ClientSession, intent: Dict) -> List[Dict]:
    """
    Uses DuckDuckGo Instant Answer API (no auth, free) to grab web summaries
    about product demand, reviews, and pricing trends.
    """
    query = f"{intent.get('primary_product')} review demand 2024 2025"
    url = f"https://api.duckduckgo.com/?q={query}&format=json&no_redirect=1&no_html=1&skip_disambig=1"
    signals = []
    try:
        async with session.get(url, headers={"User-Agent": "SupplyChainOS/1.0"}) as resp:
            if resp.status != 200:
                return []
            data = await resp.json(content_type=None)

            # Related topics are reliable demand signals
            for topic in data.get("RelatedTopics", [])[:8]:
                text = topic.get("Text", "")
                if text and len(text) > 20:
                    signals.append({
                        "source": "DuckDuckGo Web",
                        "content": text[:300],
                        "recency_score": 1.2,
                        "type": "web_demand"
                    })

            # Abstract (if any) is often a quality signal
            abstract = data.get("Abstract", "")
            if abstract:
                signals.append({
                    "source": "DuckDuckGo Web",
                    "content": abstract[:400],
                    "recency_score": 1.2,
                    "type": "web_demand"
                })
    except Exception as e:
        print(f"[DuckDuckGo Error] {e}")

    return signals


# ─── Source 6: Fake Store API (public e-commerce pricing/category data) ───────
async def fetch_ecommerce_signals(session: aiohttp.ClientSession, intent: Dict) -> List[Dict]:
    """
    Uses fakestoreapi.com (public, no auth) to get product category price data.
    In a real deployment this would be replaced by Amazon Product API / Shopify.
    """
    url = "https://fakestoreapi.com/products"
    signals = []
    category = intent.get("ecommerce_category", "").lower()
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            products = await resp.json()
            for p in products:
                p_cat = p.get("category", "").lower()
                p_title = p.get("title", "")
                p_price = p.get("price", 0)
                rating = p.get("rating", {})
                rate = rating.get("rate", 0)
                count = rating.get("count", 0)
                # Match on category similarity
                if any(kw in p_cat for kw in category.split()) or any(kw in p_title.lower() for kw in intent.get("product_categories", [])):
                    if count > 100:  # only popular products
                        signals.append({
                            "source": "E-Commerce",
                            "content": f"Product: '{p_title}' | Category: {p_cat} | Price: ${p_price} | Rating: {rate}/5 ({count} reviews) — high review count suggests strong demand.",
                            "recency_score": 1.0,
                            "type": "ecommerce"
                        })
    except Exception as e:
        print(f"[Ecommerce Error] {e}")

    return signals


# ─── Source 7: GDELT (geopolitical supply chain events, last 7 days) ──────────
async def fetch_gdelt(session: aiohttp.ClientSession, intent: Dict) -> List[Dict]:
    """
    GDELT Project — free public API for global event monitoring.
    Queries for supply chain / trade disruption events related to the product.
    """
    query = f"{intent.get('primary_product')} supply chain disruption trade"
    url = (
        f"https://api.gdeltproject.org/api/v2/doc/doc"
        f"?query={query}&mode=artlist&maxrecords=10&timespan=7d&format=json"
    )
    signals = []
    try:
        async with session.get(url, headers={"User-Agent": "SupplyChainOS/1.0"}) as resp:
            if resp.status != 200:
                return []
            data = await resp.json(content_type=None)
            for art in data.get("articles", [])[:8]:
                title = art.get("title", "")
                url_art = art.get("url", "")
                if title:
                    signals.append({
                        "source": "GDELT Global Events",
                        "content": f"{title} ({url_art[:60]}...)",
                        "recency_score": 1.5,  # GDELT is always last 7 days
                        "type": "disruption"
                    })
    except Exception as e:
        print(f"[GDELT Error] {e}")

    return signals


# ─── Step 3: Gemini Deep Semantic Analysis ────────────────────────────────────
def _split_by_recency(signals: List[Dict]):
    """
    Splits signals into two comparison windows:
      - recent   : recency_score >= 1.1  (last 90 days)
      - previous : recency_score == 1.0  (91–180 days)
    Returns counts and average signal content length as a proxy for volume/richness.
    """
    recent   = [s for s in signals if s.get("recency_score", 1.0) >= 1.1]
    previous = [s for s in signals if s.get("recency_score", 1.0) < 1.1]
    return {
        "recent_count":   len(recent),
        "previous_count": len(previous),
        "recent_signals":   recent,
        "previous_signals": previous,
    }

def _deduplicate_signals(signals: List[Dict], max_per_source: int = 5) -> List[Dict]:
    """
    Deduplicate signals by source — keep the top `max_per_source` freshest per
    source, then sort globally. This removes redundancy without losing diversity.
    """
    from collections import defaultdict
    by_source: Dict[str, List] = defaultdict(list)
    for s in signals:
        by_source[s.get("source", "Unknown")].append(s)

    deduped = []
    for src_signals in by_source.values():
        # Within each source keep the freshest / highest recency
        top = sorted(src_signals, key=lambda x: x.get("recency_score", 1.0), reverse=True)[:max_per_source]
        deduped.extend(top)

    # Final global sort by recency
    return sorted(deduped, key=lambda x: x.get("recency_score", 1.0), reverse=True)


async def analyze_all_signals(signals: List[Dict], intent: Dict) -> Dict:
    today = datetime.now().strftime("%B %d, %Y")

    # Deduplicate across sources then cap at 30 — enough statistical diversity,
    # much cheaper than sending 70 signals verbatim.
    signals_deduped = _deduplicate_signals(signals, max_per_source=5)
    signals_top = signals_deduped[:30]

    # Build corpus with source metadata (200 chars per signal is ample context)
    corpus_lines = []
    for s in signals_top:
        src = s.get("source", "Unknown")
        content = s.get("content", "")
        recency = s.get("recency_score", 1.0)
        freshness = "🔥7d" if recency >= 1.5 else ("✅30d" if recency >= 1.2 else "📅90d")
        corpus_lines.append(f"[{src}|{freshness}] {content[:200]}")

    corpus = "\n".join(corpus_lines) if corpus_lines else f"No signals. Use knowledge about {intent.get('brand_or_context')} as of {today}."

    # Split corpus into two time windows for comparative analysis
    split = _split_by_recency(signals)
    recent_count   = split["recent_count"]    # last 90 days
    previous_count = split["previous_count"]  # 91–180 days

    prompt = f"""
Today is {today}.
You are a supply chain demand analyst. Your job is to compare demand signal VOLUME and SENTIMENT
between two time windows and report a honest % change — NOT predict absolute unit numbers.

Product: "{intent.get('primary_product')}" | Brand/Context: "{intent.get('brand_or_context')}"

=== RECENT SIGNALS (last 90 days) — {recent_count} signals ===
{chr(10).join(corpus_lines[:15])}

=== PREVIOUS SIGNALS (91–180 days ago) — {previous_count} signals ===
{chr(10).join(corpus_lines[15:])}
=== END ===

Your task:
1. Compare volume + sentiment of RECENT vs PREVIOUS signals.
2. Derive a realistic demand trend percentage: positive = demand growing, negative = shrinking.
   Base this ONLY on signal evidence — do NOT fabricate numbers.
3. Be conservative: if signals are mixed or thin, say so in confidence.

Respond ONLY with this JSON (no units, no made-up numbers, DO NOT use '+' for positive numbers):
{{
    "product_in_demand": "<most demanded specific product>",
    "demand_sentiment": "HIGH" | "MEDIUM" | "LOW",
    "demand_trend_pct": <int, e.g. 23 or -8, % change vs previous window>,
    "trend_direction": "rising" | "declining" | "stable",
    "signal_volume_recent": {recent_count},
    "signal_volume_previous": {previous_count},
    "disruption_flag": true | false,
    "disruption_summary": "<one sentence on supply disruption risk, or 'None detected'>",
    "impacted_raw_materials": ["<list 1-3 raw materials used to build this product that are heavily affected by this trend>"],
    "confidence_percentage": <int 30-90, lower if signal count is thin>,
    "sources_used": ["<list of sources that had signals>"],
    "key_signals": [
        {{
            "source": "<source name>",
            "type": "demand" | "disruption" | "sentiment",
            "signal_strength": <int 1-10>,
            "freshness": "last_7_days" | "last_30_days" | "last_90_days",
            "summary": "<quote or paraphrase from actual signal content>"
        }}
    ],
    "analyst_narrative": "<2-3 sentences comparing the two windows with evidence>",
    "supply_chain_recommendation": "<one actionable recommendation referencing the % change>"
}}
"""
    try:
        if _GEMINI_ROTATOR:
            raw_text = await asyncio.wait_for(_gemini_gen(prompt), timeout=45.0)
        else:
            resp = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt), timeout=45.0
            )
            raw_text = resp.text
    except asyncio.TimeoutError:
        print("   [Analysis] Gemini timed out (>45s) — returning conservative stub.")
        return {
            "product_in_demand": intent.get("primary_product", "Unknown"),
            "demand_sentiment": "MEDIUM",
            "demand_trend_pct": 0,
            "trend_direction": "stable",
            "signal_volume_recent": len([s for s in signals if s.get("recency_score",1)>=1.1]),
            "signal_volume_previous": len([s for s in signals if s.get("recency_score",1)<1.1]),
            "disruption_flag": False,
            "disruption_summary": "Analysis timed out — LLM rate limited. Try again.",
            "impacted_raw_materials": [],
            "confidence_percentage": 30,
            "key_signals": [],
            "analyst_narrative": "Analysis timed out.",
            "supply_chain_recommendation": "Retry in 60 seconds."
        }
    clean = raw_text.strip()
    # Safely extract JSON between first { and last }
    start_idx = clean.find('{')
    end_idx = clean.rfind('}')
    if start_idx != -1 and end_idx != -1:
        clean = clean[start_idx:end_idx+1]

    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        safe_clean = clean.encode('ascii', errors='replace').decode('ascii')
        print(f"   [Analysis] JSON parse error: {e}. Raw Output: {safe_clean}")
        return {
            "product_in_demand": intent.get("primary_product", "Unknown"),
            "demand_sentiment": "MEDIUM",
            "demand_trend_pct": 0,
            "trend_direction": "stable",
            "signal_volume_recent": recent_count,
            "signal_volume_previous": previous_count,
            "disruption_flag": False,
            "disruption_summary": "None detected",
            "impacted_raw_materials": [],
            "confidence_percentage": 50,
            "key_signals": [],
            "analyst_narrative": "AI generated invalid response format.", "supply_chain_recommendation": ""
        }


# ─── Step 4: Build Final Result ───────────────────────────────────────────────
def build_result(analysis: Dict, intent: Dict, total_raw: int) -> Dict:
    confidence  = analysis.get("confidence_percentage", 50)
    trend_pct   = analysis.get("demand_trend_pct", 0)      # e.g. +23 or -8
    direction   = analysis.get("trend_direction", "stable")
    recent_vol  = analysis.get("signal_volume_recent", 0)
    prev_vol    = analysis.get("signal_volume_previous", 0)

    key_signals = analysis.get("key_signals", [])
    # Sort: disruptions first, then by strength
    sorted_signals = sorted(
        key_signals,
        key=lambda x: (x.get("type") == "disruption", x.get("signal_strength", 0)),
        reverse=True
    )

    # Human-readable trend label
    trend_label = (
        f"+{trend_pct}% vs prev quarter" if trend_pct > 0
        else f"{trend_pct}% vs prev quarter" if trend_pct < 0
        else "Stable vs prev quarter"
    )

    return {
        "query_context":               intent.get("brand_or_context"),
        "product_in_demand":           analysis.get("product_in_demand", intent.get("primary_product")),
        "demand_sentiment":            analysis.get("demand_sentiment", "MEDIUM"),
        # ── Comparative trend (honest, signal-grounded) ──
        "demand_trend_pct":            trend_pct,
        "trend_direction":             direction,
        "trend_label":                 trend_label,
        "signal_window_recent_90d":    recent_vol,
        "signal_window_previous_90d":  prev_vol,
        # ── Disruption ──
        "disruption_flag":             analysis.get("disruption_flag", False),
        "disruption_summary":          analysis.get("disruption_summary", "None detected"),
        "impacted_raw_materials":      analysis.get("impacted_raw_materials", []),
        # ── Confidence ──
        "confidence_percentage":       f"{confidence}%",
        # ── Meta ──
        "total_raw_signals":           total_raw,
        "extracted_signals":           len(key_signals),
        "sources_used":                analysis.get("sources_used", []),
        "xai_signals":                 sorted_signals[:8],
        "analyst_narrative":           analysis.get("analyst_narrative", ""),
        "supply_chain_recommendation": analysis.get("supply_chain_recommendation", ""),
        "data_freshness":              f"Signals from last {MAX_SIGNAL_AGE_DAYS} days only",
    }


# ─── Main Orchestrator ────────────────────────────────────────────────────────
async def run_pipeline(user_query: str, baseline_units: int = 1000) -> Dict[str, Any]:
    print(f"\n{'='*60}")
    print(f"[DemandAgent] Query: '{user_query}' | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    # ── Cache check (30-min TTL) ──────────────────────────────────────────────
    ckey = _cache_key(user_query, baseline_units)
    cached = _cache_get(ckey)
    if cached:
        print("[CACHE HIT] Returning cached result — 0 Gemini tokens used.")
        return {**cached, "cache_hit": True}

    # Step 1: Understand intent
    print("[1/4] Extracting intent via Gemini...")
    intent = await extract_intent(user_query)
    print(f"   → Brand: {intent.get('brand_or_context')}")
    print(f"   → Product: {intent.get('primary_product')}")
    print(f"   → Baseline: {intent.get('baseline_units_30day')} units")

    # Step 2: Parallel multi-source fetch
    print("[2/4] Fetching signals from all sources (last 90 days only)...")
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            fetch_youtube(session, intent),
            fetch_news(session, intent),
            fetch_reddit(session, intent),
            fetch_trends(intent),
            fetch_duckduckgo(session, intent),
            fetch_ecommerce_signals(session, intent),
            fetch_gdelt(session, intent),
            return_exceptions=True
        )

    all_signals = []
    source_names = ["YouTube", "News", "Reddit", "Trends", "DuckDuckGo", "E-Commerce", "GDELT"]
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"   [!] {source_names[i]} failed: {result}")
        elif isinstance(result, list):
            valid = [s for s in result if s.get("recency_score", 1) > 0]
            print(f"   ✓ {source_names[i]}: {len(valid)} fresh signals")
            all_signals.extend(valid)

    print(f"   → Total raw: {len(all_signals)} | Deduped corpus will be ≤30 signals")

    # Step 3: Gemini deep analysis
    print("[3/4] Running Gemini semantic analysis (deduped corpus)...")
    analysis = await analyze_all_signals(all_signals, intent)
    print(f"   → Sentiment: {analysis.get('demand_sentiment')} | Predicted: {analysis.get('predicted_units_30day')} units")

    # Step 4: Package result
    result = build_result(analysis, intent, total_raw=len(all_signals))
    result["cache_hit"] = False
    print(f"[4/4] Done. Product: '{result['product_in_demand']}' | Trend: {result.get('trend_label', 'Unknown')}")

    # ── Store in cache ────────────────────────────────────────────────────────
    _cache_set(ckey, result)
    return result
