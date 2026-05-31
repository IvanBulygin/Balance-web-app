"""
LLM-as-a-judge adapter for the RAG evaluation harness.

Hosts only the deepeval-dependent piece — :class:`GeminiJudge` — so the rest of
the app can stay deepeval-free. The shared rate limiter, client, and retrying
:func:`generate_content` live in :mod:`gemini_client`.
"""

from __future__ import annotations

from typing import Optional, Type

from deepeval.models import DeepEvalBaseLLM
from google import genai
from google.genai import types
from pydantic import BaseModel

from gemini_client import (
    DEFAULT_MODEL,
    LIMITER,
    RateLimiter,
    generate_content,
    get_client,
)

# Re-export so existing callers (test_rag.py) keep working.
__all__ = [
    "DEFAULT_MODEL",
    "LIMITER",
    "RateLimiter",
    "GeminiJudge",
    "generate_content",
    "get_client",
]

MAX_OUTPUT_TOKENS = 8192


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
            temperature=0.0,
            max_output_tokens=MAX_OUTPUT_TOKENS,
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
            return response.text or ""
        return response.text or ""

    async def a_generate(self, prompt: str, schema: Optional[Type[BaseModel]] = None):
        return self.generate(prompt, schema)

    def get_model_name(self) -> str:
        return self.model_name
