import asyncio
import hashlib
import json
import time
import httpx
import os
import logging

from temporalio.exceptions import ApplicationError

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# If Retry-After <= this, sleep inside the activity and retry the HTTP call.
# Per-minute rate limits from Groq are typically 20-60s — handle them silently.
_MAX_INTERNAL_WAIT_SECS = 60

# If Retry-After > _MAX_INTERNAL_WAIT_SECS, fail fast and let Temporal retry
# with backoff. Avoids hanging the activity for quota-exhaustion waits (hours).
_MAX_RATE_LIMIT_RETRIES = 4

# In-memory LLM response cache: hash -> (response_str, expires_at)
# Prevents duplicate API calls on Temporal retries within the same worker process.
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

    req_headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    logger.info(f"Calling Groq model={GROQ_MODEL} json_mode={json_mode}")
    logger.info(f"Prompt preview: {prompt[:120]}...")

    for rl_attempt in range(_MAX_RATE_LIMIT_RETRIES):
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(GROQ_API_URL, headers=req_headers, json=body)

        if response.status_code == 429:
            wait_secs = _parse_retry_after(response, default=30)

            if wait_secs > _MAX_INTERNAL_WAIT_SECS:
                # Quota exhaustion — the wait is too long to block the activity.
                # Fail fast so Temporal retries with its own backoff schedule.
                raise ApplicationError(
                    f"Groq quota exhausted: Retry-After={wait_secs}s "
                    f"(limit={_MAX_INTERNAL_WAIT_SECS}s). "
                    "Check your Groq dashboard for quota usage.",
                    "RateLimitQuotaExhausted",
                    non_retryable=False,
                )

            logger.warning(
                f"Groq 429 rate limit — waiting {wait_secs}s "
                f"(internal retry {rl_attempt + 1}/{_MAX_RATE_LIMIT_RETRIES})"
            )
            await _sleep_with_heartbeat(
                wait_secs,
                label=f"Groq rate-limited: {wait_secs}s cooldown",
            )
            continue

        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"]
        logger.info(f"Groq responded ({len(result)} chars)")
        return result

    raise ApplicationError(
        f"Groq rate limit persisted after {_MAX_RATE_LIMIT_RETRIES} internal retries "
        f"({_MAX_RATE_LIMIT_RETRIES * _MAX_INTERNAL_WAIT_SECS}s+ of waiting). "
        "Temporal will retry the activity.",
        "RateLimitPersisted",
        non_retryable=False,
    )


def _parse_retry_after(response: httpx.Response, default: int = 30) -> int:
    """Read Retry-After header (seconds). Falls back to default if absent or unparseable."""
    raw = response.headers.get("retry-after") or response.headers.get("x-ratelimit-reset-requests")
    if raw:
        try:
            return max(1, int(float(raw)))
        except ValueError:
            pass
    return default


async def _sleep_with_heartbeat(seconds: int, label: str) -> None:
    """Sleep in ≤20s chunks, sending Temporal heartbeats to keep the activity alive."""
    from temporalio import activity as _activity

    waited = 0
    while waited < seconds:
        chunk = min(20, seconds - waited)
        await asyncio.sleep(chunk)
        waited += chunk
        try:
            _activity.heartbeat(f"{label} ({waited}/{seconds}s waited)")
        except Exception:
            pass  # Outside activity context (e.g. unit tests)


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
