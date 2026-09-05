"""RAG evaluation harness for Balance AI.

Runs a small starter QA suite through the same retrieval + Gemini pipeline the
live app uses, then scores each answer for two standard RAG metrics — Answer
Relevancy and Faithfulness (Groundedness) — using ``gemini-2.5-flash`` as the
LLM-as-a-judge (the exact same model as the chatbot itself).

Designed for the Google AI Studio free tier: strictly sequential, with sleeps
between generations and per-metric backoff so the whole run stays inside the
free-tier request-per-minute budget. Reads the API key from ``GOOGLE_API_KEY``
(same env var the app uses).

Exit code:
    0 - all metric assertions passed
    1 - one or more metrics fell below their threshold
    2 - configuration / import error (e.g. missing key or dep)

Run locally::

    GOOGLE_API_KEY=... python test_rag.py

In CI it is triggered by ``.github/workflows/rag-tests.yml`` on every push.
"""

from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

# --- 1. Bootstrap --------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
APP_DIR = REPO_ROOT / "agent_site"
sys.path.insert(0, str(APP_DIR))

API_KEY = os.environ.get("GOOGLE_API_KEY", "").strip()
if not API_KEY:
    print("ERROR: GOOGLE_API_KEY env var is required.", file=sys.stderr)
    sys.exit(2)

# The same model powers both the app under test AND the judge, per the spec.
MODEL = "gemini-2.5-flash"

# Free-tier throttling knobs.
GEN_SLEEP_S = 6.0        # pause between test-case answer generations
JUDGE_SLEEP_S = 4.0      # pause between judge LLM calls (a metric may issue several)
BACKOFF_S = 30.0         # sleep when the API returns 429 / RESOURCE_EXHAUSTED
MAX_RETRIES = 6

# Pass thresholds for the two metrics (0.0-1.0). Tuned for a starter MVP suite.
RELEVANCY_THRESHOLD = 0.70
FAITHFULNESS_THRESHOLD = 0.70

# --- 2. RAG pipeline (identical config to the running app) ---------------------

try:
    from retrieval import build_index, format_context  # type: ignore
    from google import genai  # type: ignore
except ImportError as exc:  # pragma: no cover - env issue, surfaces clearly in CI
    print(f"ERROR: failed to import RAG dependencies: {exc}", file=sys.stderr)
    sys.exit(2)


SYSTEM_PROMPT = (APP_DIR / "system_prompt.md").read_text(encoding="utf-8")
INDEX = build_index(APP_DIR / "data" / "pdfs")
CLIENT = genai.Client(api_key=API_KEY)


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower()


def generate_answer(question: str) -> tuple[str, list[str]]:
    """Retrieve context and generate an answer using the same config as the app."""
    hits = INDEX.guide_aware_search(question, k=8)
    context_chunks = [chunk.text for chunk, _ in hits]
    system_instruction = (
        SYSTEM_PROMPT + "\n\n## Retrieved passages\n\n" + format_context(hits)
    )
    config = {
        "system_instruction": system_instruction,
        "max_output_tokens": 8192,
        "temperature": 0.3,
        # Match the deployed app: thinking off so answers don't truncate.
        "thinking_config": {"thinking_budget": 0},
    }
    contents = [{"role": "user", "parts": [{"text": question}]}]
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = CLIENT.models.generate_content(
                model=MODEL, contents=contents, config=config
            )
            return response.text or "", context_chunks
        except Exception as exc:  # noqa: BLE001
            if _is_quota_error(exc) and attempt < MAX_RETRIES:
                print(f"  [gen] 429; sleeping {BACKOFF_S:.0f}s (attempt {attempt})")
                time.sleep(BACKOFF_S)
                continue
            raise
    raise RuntimeError("Answer generation failed after retries (quota exhausted?)")


# --- 3. deepeval judge (same model) with throttling + 429 backoff --------------

try:
    from deepeval.models import GeminiModel  # type: ignore
    from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric  # type: ignore
    from deepeval.test_case import LLMTestCase  # type: ignore
except ImportError as exc:
    print(
        "ERROR: deepeval is not installed. Add it via requirements-dev.txt.\n"
        f"       {exc}",
        file=sys.stderr,
    )
    sys.exit(2)


class ThrottledGeminiJudge(GeminiModel):
    """A GeminiModel wrapper that sleeps between calls and retries on 429.

    Deepeval issues several judge calls per metric (statement extraction,
    verdict, reason). The base class raises on 429; wrapping ``generate`` and
    ``a_generate`` here keeps the whole eval inside the free-tier RPM.
    """

    def generate(self, prompt: str, schema: Any = None):  # type: ignore[override]
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = super().generate(prompt, schema)
                time.sleep(JUDGE_SLEEP_S)
                return result
            except Exception as exc:  # noqa: BLE001
                if _is_quota_error(exc) and attempt < MAX_RETRIES:
                    print(
                        f"  [judge] 429; sleeping {BACKOFF_S:.0f}s (attempt {attempt})"
                    )
                    time.sleep(BACKOFF_S)
                    continue
                raise

    async def a_generate(self, prompt: str, schema: Any = None):  # type: ignore[override]
        # Force sync execution so throttling is honoured. Deepeval accepts this.
        return self.generate(prompt, schema)


JUDGE = ThrottledGeminiJudge(
    model=MODEL,
    api_key=API_KEY,
    temperature=0.0,
    generation_kwargs={"thinking_config": {"thinking_budget": 0}},
)

METRICS = [
    AnswerRelevancyMetric(
        threshold=RELEVANCY_THRESHOLD, model=JUDGE, include_reason=True, async_mode=False
    ),
    FaithfulnessMetric(
        threshold=FAITHFULNESS_THRESHOLD, model=JUDGE, include_reason=True, async_mode=False
    ),
]

# --- 4. Starter dataset --------------------------------------------------------

# A minimal, opinionated MVP set: one representative question per major goal.
# Add more as the RAG matures — the harness scales linearly with rate limits.
TEST_CASES: list[dict[str, str]] = [
    {"q": "What supplements help me fall asleep faster?"},
    {"q": "Best supplements for sore joints?"},
    {"q": "How can I lose body fat?"},
    {"q": "What supplements support muscle recovery?"},
    {"q": "Supplements for heart health and cholesterol?"},
    {"q": "What supplements help with stress and anxiety?"},
    {"q": "How do I improve memory and focus?"},
    {"q": "What supplements support immunity?"},
]

# --- 5. Run --------------------------------------------------------------------


def main() -> int:
    print(
        f"Loaded {len(INDEX.chunks):,} chunks; running {len(TEST_CASES)} cases "
        f"against {MODEL} (judge and chatbot)."
    )

    passed = 0
    failed = 0
    per_case_summary: list[str] = []

    for i, tc in enumerate(TEST_CASES, 1):
        question = tc["q"]
        print(f"\n[{i}/{len(TEST_CASES)}] {question}")
        try:
            answer, context_chunks = generate_answer(question)
        except Exception as exc:  # noqa: BLE001
            print(f"  answer generation FAILED: {exc}")
            failed += 1
            per_case_summary.append(f"[FAIL] {question} — generation error")
            continue

        if not answer:
            print("  empty answer (safety block?); recording as failure")
            failed += 1
            per_case_summary.append(f"[FAIL] {question} — empty answer")
            continue

        case = LLMTestCase(
            input=question,
            actual_output=answer,
            retrieval_context=context_chunks,
        )

        scores: list[str] = []
        case_ok = True
        for metric in METRICS:
            name = metric.__class__.__name__.replace("Metric", "")
            try:
                metric.measure(case)
                score = float(getattr(metric, "score", 0.0) or 0.0)
                ok = bool(getattr(metric, "success", False))
                scores.append(f"{name}={score:.2f}{' PASS' if ok else ' FAIL'}")
                if ok:
                    passed += 1
                else:
                    failed += 1
                    case_ok = False
            except Exception as exc:  # noqa: BLE001
                traceback.print_exc()
                scores.append(f"{name}=ERROR")
                failed += 1
                case_ok = False

        print("  " + " | ".join(scores))
        per_case_summary.append(("[PASS] " if case_ok else "[FAIL] ") + question)

        # Rate-limit friendly pause before the next case.
        time.sleep(GEN_SLEEP_S)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("-" * 60)
    for line in per_case_summary:
        print(line)
    total = passed + failed
    print("-" * 60)
    print(f"metric assertions: {passed} passed / {failed} failed / {total} total")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
