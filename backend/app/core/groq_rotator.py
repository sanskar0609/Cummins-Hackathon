"""
groq_rotator.py — Groq API Key Rotator

Reads up to 5 Groq API keys from environment variables:
  GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3, GROQ_API_KEY_4, GROQ_API_KEY_5

Keys are used in round-robin. On a 429 / rate-limit error the rotator
automatically switches to the next key and retries — transparently.
"""

import os
import time
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any

# ── Load .env early so os.environ is populated before any key reads ──────────
try:
    from dotenv import load_dotenv as _load_dotenv
    _env_path = Path(__file__).resolve().parents[3] / ".env"
    _load_dotenv(dotenv_path=_env_path, override=False)
except Exception:
    pass   # dotenv not installed or file missing — fall through to os.environ

try:
    from groq import Groq as GroqClient
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False

# ─── Key Pool ────────────────────────────────────────────────────────────────
def _load_keys() -> List[str]:
    raw = [
        os.environ.get("GROQ_API_KEY",   ""),
        os.environ.get("GROQ_API_KEY_2", ""),
        os.environ.get("GROQ_API_KEY_3", ""),
        os.environ.get("GROQ_API_KEY_4", ""),
        os.environ.get("GROQ_API_KEY_5", ""),
    ]
    return [k.strip() for k in raw if k.strip()]

_lock   = threading.Lock()
_keys:  List[str] = []
_index: int = 0

def _init():
    global _keys, _index
    _keys  = _load_keys()
    _index = 0
    if not _keys:
        # Not fatal — Groq is optional (falls back to Gemini)
        print("[GroqRotator] No Groq keys found — Groq disabled.")
        return
    print(f"[GroqRotator] Loaded {len(_keys)} key(s) — round-robin active.")

_init()

def _next_key() -> Optional[str]:
    global _index
    if not _keys:
        return None
    with _lock:
        key = _keys[_index % len(_keys)]
        _index += 1
        return key

def is_available() -> bool:
    return _GROQ_AVAILABLE and len(_keys) > 0

# ─── Sync call with rotation ─────────────────────────────────────────────────
def chat_with_rotation(
    messages: List[Dict[str, str]],
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.1,
    max_tokens: int = 512,
    response_format: Optional[Dict] = None,
    max_retries: Optional[int] = None,
) -> str:
    """
    Calls Groq chat completions with automatic key rotation on 429 / rate-limit.
    Returns the message content string.
    Raises RuntimeError if no keys are available or all keys are exhausted.
    """
    if not _GROQ_AVAILABLE:
        raise RuntimeError("groq package not installed — pip install groq")
    if not _keys:
        raise RuntimeError("No Groq API keys configured.")

    attempts = min(len(_keys), max_retries) if max_retries else len(_keys)
    last_err = None

    for attempt in range(attempts):
        api_key = _next_key()
        try:
            client = GroqClient(api_key=api_key)
            kwargs: Dict[str, Any] = dict(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if response_format:
                kwargs["response_format"] = response_format

            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content

        except Exception as e:
            err_str = str(e)
            is_rate = (
                "429" in err_str
                or "rate_limit" in err_str.lower()
                or "quota" in err_str.lower()
                or "too many" in err_str.lower()
            )
            if is_rate:
                print(f"[GroqRotator] Rate-limit hit (attempt {attempt+1}/{attempts}), rotating key...")
                last_err = e
                # NO sleep — fail fast so we don't block the asyncio thread pool
                continue
            raise   # non-rate errors bubble up immediately

    raise RuntimeError(f"All {len(_keys)} Groq key(s) exhausted. Last error: {last_err}")


# ─── Async wrapper ────────────────────────────────────────────────────────────
async def async_chat_with_rotation(
    messages: List[Dict[str, str]],
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.1,
    max_tokens: int = 512,
    response_format: Optional[Dict] = None,
) -> str:
    import asyncio
    return await asyncio.to_thread(
        chat_with_rotation, messages, model, temperature, max_tokens, response_format
    )
