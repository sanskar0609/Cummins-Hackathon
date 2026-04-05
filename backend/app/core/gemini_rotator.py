"""
gemini_rotator.py — Gemini + Groq Unified Key Rotator

Reads up to 5 Gemini API keys from environment variables:
  GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3, GEMINI_API_KEY_4, GEMINI_API_KEY_5

Strategy:
  1. Try Gemini keys round-robin. On 429/quota, rotate to next key.
  2. If ALL Gemini keys fail → automatically fall back to Groq (llama-3.3-70b).
  3. If Groq also fails → raise final error.

Supports both:
  - google.generativeai  (legacy genai)
  - google.genai Client  (new SDK)
"""

import os
import threading
import time
from pathlib import Path
from typing import Optional, List

# ── Load .env early so os.environ is populated before any key reads ──────────
try:
    from dotenv import load_dotenv as _load_dotenv
    _env_path = Path(__file__).resolve().parents[3] / ".env"
    _load_dotenv(dotenv_path=_env_path, override=False)
except Exception:
    pass   # dotenv not installed or file missing — fall through to os.environ

# ─── Gemini Key Pool ──────────────────────────────────────────────────────────
def _load_gemini_keys() -> List[str]:
    raw_keys = [
        os.environ.get("GEMINI_API_KEY",   ""),
        os.environ.get("GEMINI_API_KEY_2", ""),
        os.environ.get("GEMINI_API_KEY_3", ""),
        os.environ.get("GEMINI_API_KEY_4", ""),
        os.environ.get("GEMINI_API_KEY_5", ""),
    ]
    return [k.strip() for k in raw_keys if k.strip()]

_lock  = threading.Lock()
_keys: List[str] = []
_index: int = 0

def _init():
    global _keys, _index
    _keys  = _load_gemini_keys()
    _index = 0
    if not _keys:
        print("[GeminiRotator] WARNING: No Gemini API keys found — Groq fallback only.")
        return
    print(f"[GeminiRotator] Loaded {len(_keys)} Gemini key(s) — round-robin active.")

_init()

def _next_gemini_key() -> Optional[str]:
    global _index
    if not _keys:
        return None
    with _lock:
        key = _keys[_index % len(_keys)]
        _index += 1
        return key

def get_current_key() -> Optional[str]:
    """Returns the current active Gemini key (for direct client construction)."""
    return _next_gemini_key()

# ─── Groq fallback helper ─────────────────────────────────────────────────────
def _groq_fallback(prompt: str) -> str:
    """Falls back to Groq rotator when all Gemini keys are exhausted."""
    try:
        from app.core.groq_rotator import chat_with_rotation as _groq_chat, is_available
        if not is_available():
            raise RuntimeError("Groq not available (no keys or package missing).")
        print("[GeminiRotator] ⚠ All Gemini keys failed — falling back to Groq...")
        return _groq_chat(
            messages=[
                {"role": "system", "content": "You are a helpful supply chain AI assistant."},
                {"role": "user",   "content": prompt},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=512,
        )
    except Exception as groq_err:
        raise RuntimeError(
            f"Both Gemini (all keys exhausted) and Groq fallback failed. "
            f"Groq error: {groq_err}"
        )

# ─── Legacy google.generativeai wrapper ──────────────────────────────────────
def generate_with_retry(
    prompt: str,
    model_name: str = "gemini-1.5-flash",
    max_retries: Optional[int] = None,
) -> str:
    """
    Calls Gemini generate_content with automatic key rotation on 429.
    On full Gemini exhaustion → falls back to Groq automatically.
    """
    try:
        import google.generativeai as genai
    except ImportError:
        print("[GeminiRotator] google.generativeai not installed — using Groq fallback.")
        return _groq_fallback(prompt)

    attempts = min(len(_keys), max_retries) if (max_retries and _keys) else (len(_keys) or 1)
    last_err = None

    for attempt in range(attempts):
        key = _next_gemini_key()
        if not key:
            break
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name)
            safe_prompt = prompt[:4000]
            resp  = model.generate_content(
                safe_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=512,
                    temperature=0.3
                )
            )
            return resp.text
        except Exception as e:
            err_str = str(e)
            print(f"[GeminiRotator] Error with key {key[:8]}... : {err_str[:80]}")
            is_quota = "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower()
            if is_quota:
                print(f"[GeminiRotator] Key quota hit (attempt {attempt+1}/{attempts}), rotating...")
                last_err = e
                # NO sleep — failing fast so we don't block the asyncio thread pool
                continue
            if "not found" in err_str.lower() and model_name == "gemini-2.0-flash":
                print("[GeminiRotator] Model 2.0-flash not found, falling back to 1.5-flash...")
                return generate_with_retry(prompt, model_name="gemini-1.5-flash", max_retries=max_retries)
            raise

    # All Gemini keys exhausted or none configured — try Groq
    return _groq_fallback(prompt)

# ─── New google.genai Client wrapper ─────────────────────────────────────────
def get_genai_client():
    """
    Returns a google.genai Client with the next Gemini key.
    Raises RuntimeError if no Gemini keys are available.
    """
    try:
        from google import genai
    except ImportError:
        raise RuntimeError("google-genai package not installed.")
    key = _next_gemini_key()
    if not key:
        raise RuntimeError("No Gemini API keys configured.")
    return genai.Client(api_key=key)

def generate_content_with_retry(
    prompt: str,
    model_name: str = "gemini-1.5-flash",
    config=None,
    max_retries: Optional[int] = None,
) -> str:
    """
    Calls google.genai Client.models.generate_content with key rotation.
    On full Gemini exhaustion → falls back to Groq automatically.
    """
    try:
        from google import genai as new_genai
    except ImportError:
        print("[GeminiRotator] google-genai not installed — using Groq fallback.")
        return _groq_fallback(prompt)

    attempts = min(len(_keys), max_retries) if (max_retries and _keys) else (len(_keys) or 1)
    last_err = None

    for attempt in range(attempts):
        key = _next_gemini_key()
        if not key:
            break
        try:
            client = new_genai.Client(api_key=key)
            safe_prompt = prompt[:4000]
            safe_config = config
            if safe_config is None:
                from google.genai import types
                safe_config = types.GenerateContentConfig(
                    max_output_tokens=512,
                    temperature=0.3
                )
            kwargs = dict(model=model_name, contents=safe_prompt, config=safe_config)
            resp = client.models.generate_content(**kwargs)
            return resp.text
        except Exception as e:
            err_str = str(e)
            print(f"[GeminiRotator] Error with key {key[:8]}... : {err_str[:80]}")
            is_quota = "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower()
            if is_quota:
                print(f"[GeminiRotator] Key quota hit (attempt {attempt+1}/{attempts}), rotating...")
                last_err = e
                # NO sleep — fail fast
                continue
            if "not found" in err_str.lower() and model_name == "gemini-2.0-flash":
                print("[GeminiRotator] Model 2.0-flash not found, falling back to 1.5-flash...")
                return generate_content_with_retry(prompt, model_name="gemini-1.5-flash", config=config, max_retries=max_retries)
            raise

    return _groq_fallback(prompt)

# ─── Async wrappers ───────────────────────────────────────────────────────────
async def async_generate_with_retry(
    prompt: str,
    model_name: str = "gemini-2.0-flash",
) -> str:
    import asyncio
    return await asyncio.to_thread(generate_content_with_retry, prompt, model_name)

async def async_generate_content_with_retry(
    prompt: str,
    model_name: str = "gemini-2.0-flash",
    config=None,
) -> str:
    import asyncio
    return await asyncio.to_thread(generate_content_with_retry, prompt, model_name, config)
