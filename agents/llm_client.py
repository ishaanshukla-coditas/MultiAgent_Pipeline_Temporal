import hashlib
import json
import time
import httpx
import os
import logging

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# In-memory LLM response cache: hash -> (response_str, expires_at)
# Prevents duplicate API calls on Temporal retries within the same worker process.
# TTL matches the Temporal retry window (3 attempts over ~30s max).
_LLM_CACHE: dict[str, tuple[str, float]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _cache_key(system: str | None, prompt: str, json_mode: bool) -> str:
    raw = f"{json_mode}|||{system or ''}|||{prompt}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def call_llm(prompt: str, system: str = None) -> str:
    """Call Groq and return plain text. Cached by prompt hash for retry safety."""
    key = _cache_key(system, prompt, json_mode=False)
    cached = _get_cached(key)
    if cached is not None:
        return cached

    result = await _call_groq(prompt, system, json_mode=False)
    _set_cached(key, result)
    return result


async def call_llm_json(prompt: str, system: str = None) -> dict:
    """Call Groq in JSON mode and return parsed dict. Cached by prompt hash."""
    key = _cache_key(system, prompt, json_mode=True)
    cached = _get_cached(key)
    if cached is not None:
        return json.loads(cached)

    raw = await _call_groq(prompt, system, json_mode=True)
    _set_cached(key, raw)
    return json.loads(raw)


async def _call_groq(prompt: str, system: str | None, json_mode: bool) -> str:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in environment variables")

    # System prompt is intentionally kept stable (no dynamic data) so that
    # provider-side prefix caching kicks in across requests of the same agent type.
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body: dict = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 4096,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    logger.info(f"Calling Groq model={GROQ_MODEL} json_mode={json_mode}")
    logger.info(f"Prompt preview: {prompt[:120]}...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"]
        logger.info(f"Groq responded ({len(result)} chars)")
        return result


def _get_cached(key: str) -> str | None:
    entry = _LLM_CACHE.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if time.monotonic() > expires_at:
        del _LLM_CACHE[key]
        return None
    logger.info("LLM cache hit — skipping API call")
    return value


def _set_cached(key: str, value: str) -> None:
    _LLM_CACHE[key] = (value, time.monotonic() + _CACHE_TTL_SECONDS)
