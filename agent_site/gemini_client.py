"""
Production-safe Gemini client utilities.

Two things live here:

1. A process-wide :class:`RateLimiter` and a retrying :func:`generate_content`
   wrapper. Every Gemini call in the app and in the eval harness flows through
   the same limiter so the single Google AI Studio free-tier key stays under
   its requests-per-minute cap, with exponential backoff if a 429 slips through.
2. :func:`get_client`, the one place that reads ``GOOGLE_API_KEY`` and builds
   a ``google-genai`` client.

This module deliberately has NO dependency on deepeval — it's imported by the
FastAPI app at runtime. The evaluator-only :class:`GeminiJudge` lives in
``gemini_eval.py`` and imports from here.
"""

from __future__ import annotations

import os
import re
import threading
import time
from typing import Optional

from google import genai
from google.genai import errors, types

DEFAULT_MIN_INTERVAL = float(os.environ.get("GEMINI_MIN_REQUEST_INTERVAL", "7.0"))
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
MAX_RETRIES = 5
_RETRY_DELAY_RE = re.compile(r"retry.{0,30}?(\d+(?:\.\d+)?)\s*s", re.IGNORECASE)


class RateLimiter:
    """Thread-safe minimum-interval throttle shared across all API callers."""

    def __init__(self, min_interval: float = DEFAULT_MIN_INTERVAL) -> None:
        self.min_interval = max(min_interval, 0.0)
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            sleep_for = self._next_allowed - now
            if sleep_for > 0:
                time.sleep(sleep_for)
                now = time.monotonic()
            self._next_allowed = now + self.min_interval


# One limiter for the entire process: the chat, the new category endpoint, and
# the eval judge all share the same key, so they must share the same budget.
LIMITER = RateLimiter()


def get_client(api_key: Optional[str] = None) -> genai.Client:
    """Build a Gemini client, reading ``GOOGLE_API_KEY`` if no key is passed."""
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY is not set.")
    return genai.Client(api_key=key)


def _is_rate_limited(exc: Exception) -> bool:
    if isinstance(exc, errors.APIError) and getattr(exc, "code", None) == 429:
        return True
    text = str(exc).upper()
    return "RESOURCE_EXHAUSTED" in text or "429" in text


def _suggested_delay(exc: Exception) -> Optional[float]:
    """Honor the server's RetryInfo delay if the error mentions one."""
    match = _RETRY_DELAY_RE.search(str(exc))
    return float(match.group(1)) if match else None


def generate_content(
    client: genai.Client,
    contents,
    config: types.GenerateContentConfig,
    *,
    model: str = DEFAULT_MODEL,
    limiter: RateLimiter = LIMITER,
    max_retries: int = MAX_RETRIES,
) -> types.GenerateContentResponse:
    """Throttled ``generate_content`` with exponential backoff on rate limits."""
    backoff = 2.0
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        limiter.wait()
        try:
            return client.models.generate_content(
                model=model, contents=contents, config=config
            )
        except Exception as exc:  # noqa: BLE001 - inspect, then re-raise non-429s
            last_exc = exc
            if not _is_rate_limited(exc) or attempt == max_retries:
                raise
            delay = _suggested_delay(exc) or backoff
            print(
                f"[gemini] rate limited (attempt {attempt}/{max_retries}); "
                f"backing off {delay:.1f}s"
            )
            time.sleep(delay)
            backoff = min(backoff * 2, 60.0)
    raise last_exc  # type: ignore[misc]
