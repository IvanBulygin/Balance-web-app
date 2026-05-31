"""
Shared evaluation infrastructure for the Balance.ai RAG test harness.

Holds two things the test suite needs:

1. A process-wide :class:`RateLimiter` and a retrying ``generate_content``
   wrapper. The whole harness — both the RAG pipeline under test and the
   LLM-as-a-judge — runs against a SINGLE Google AI Studio free-tier key, so
   every call (answer generation + every metric sub-call) is funnelled through
   one limiter to stay under the free-tier requests-per-minute cap, with
   exponential backoff if a 429 slips through anyway.

2. :class:`GeminiJudge`, a ``deepeval`` model adapter that makes
   ``gemini-2.5-flash`` itself the evaluator — the exact same model the chatbot
   uses — so Answer Relevancy and Faithfulness are scored with no extra
   provider, no OpenAI key, and no embeddings.

Both the pipeline and the judge read the key from ``GOOGLE_API_KEY``.
"""

from __future__ import annotations

import os
import re
import threading
import time
from typing import Optional, Type

from deepeval.models import DeepEvalBaseLLM
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

# Free-tier gemini-2.5-flash is capped at ~10 requests/minute. We space calls a
# touch wider than 60/10 = 6s to leave headroom for clock skew and the
# occasional burst. Override via env when running against a paid key.
DEFAULT_MIN_INTERVAL = float(os.environ.get("GEMINI_MIN_REQUEST_INTERVAL", "7.0"))
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
MAX_OUTPUT_TOKENS = 8192
MAX_RETRIES = 5
_RETRY_DELAY_RE = re.compile(r"retry.{0,30}?(\d+(?:\.\d+)?)\s*s", re.IGNORECASE)


class RateLimiter:
    """Thread-safe minimum-interval throttle shared across all API callers."""

    def __init__(self, min_interval: float = DEFAULT_MIN_INTERVAL) -> None:
        self.min_interval = max(min_interval, 0.0)
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        """Block until at least ``min_interval`` has passed since the last call."""
        with self._lock:
            now = time.monotonic()
            sleep_for = self._next_allowed - now
            if sleep_for > 0:
                time.sleep(sleep_for)
                now = time.monotonic()
            self._next_allowed = now + self.min_interval


# One limiter for the entire process: RAG answers and judge calls share the
# same key, so they must share the same budget.
LIMITER = RateLimiter()


def get_client(api_key: Optional[str] = None) -> genai.Client:
    """Build a Gemini client, reading ``GOOGLE_API_KEY`` if no key is passed."""
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Export it locally or provide it via "
            "GitHub Secrets so both the RAG pipeline and the judge can authenticate."
        )
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
    """Throttled ``generate_content`` with exponential backoff on rate limits.

    Non-rate-limit errors propagate immediately — we only retry the thing the
    free tier actually throws under load (429 / RESOURCE_EXHAUSTED).
    """
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
    # Unreachable: the loop either returns or raises, but keeps type-checkers happy.
    raise last_exc  # type: ignore[misc]


class GeminiJudge(DeepEvalBaseLLM):
    """Use gemini-2.5-flash as the deepeval LLM-as-a-judge.

    deepeval metrics call ``generate(prompt, schema=PydanticModel)`` and accept
    either a populated schema instance or a JSON string. We ask Gemini for
    structured JSON output bound to that schema, return the parsed instance when
    the SDK gives us one, and fall back to the raw JSON text otherwise.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        limiter: RateLimiter = LIMITER,
    ) -> None:
        self.model_name = model_name
        self.limiter = limiter
        self._client = get_client(api_key)
        super().__init__(model_name)

    def load_model(self) -> genai.Client:
        return self._client

    def _config(self, schema: Optional[Type[BaseModel]]) -> types.GenerateContentConfig:
        config = types.GenerateContentConfig(
            temperature=0.0,  # deterministic scoring
            max_output_tokens=MAX_OUTPUT_TOKENS,
            # gemini-2.5-flash is a thinking model; thinking tokens eat the
            # output budget and can truncate the JSON verdict. The judging
            # prompts are explicit enough that thinking adds little here.
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        if schema is not None:
            config.response_mime_type = "application/json"
            config.response_schema = schema
        return config

    def generate(self, prompt: str, schema: Optional[Type[BaseModel]] = None):
        response = generate_content(
            self._client,
            prompt,
            self._config(schema),
            model=self.model_name,
            limiter=self.limiter,
        )
        if schema is not None:
            parsed = getattr(response, "parsed", None)
            if isinstance(parsed, schema):
                return parsed
            # Fall back to raw JSON text; deepeval parses it itself.
            return response.text or ""
        return response.text or ""

    async def a_generate(self, prompt: str, schema: Optional[Type[BaseModel]] = None):
        # The harness runs metrics synchronously (async_mode=False) so the shared
        # limiter stays effective; delegate to the sync path for one code path.
        return self.generate(prompt, schema)

    def get_model_name(self) -> str:
        return self.model_name
