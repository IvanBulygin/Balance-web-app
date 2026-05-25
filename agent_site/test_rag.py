"""
Automated RAG evaluation harness for the Balance.ai Wellbeing Agent.

What it does
------------
For each question in a small starter dataset it runs the *real* RAG pipeline
(BM25 retrieval over the supplement guides + a gemini-2.5-flash answer grounded
in the retrieved passages), then scores the answer with two deepeval metrics:

* **Answer Relevancy** — does the answer actually address the question?
* **Faithfulness (Groundedness)** — is every claim supported by the retrieved
  passages, i.e. no hallucinations?

Both metrics are judged by gemini-2.5-flash itself (see ``gemini_eval.py``), so
the harness needs only one provider and one key — ``GOOGLE_API_KEY`` — shared
by the pipeline and the judge. Every Gemini call (answers + judging) flows
through a single shared rate limiter to respect the free-tier RPM cap.

Run it
------
    cd agent_site
    GOOGLE_API_KEY=... python -m pytest test_rag.py -v

If ``GOOGLE_API_KEY`` is absent the suite skips rather than failing, so it stays
green on forked-PR builds that have no secret access.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

import pytest
from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase
from google.genai import types

from gemini_eval import LIMITER, DEFAULT_MODEL, GeminiJudge, generate_content, get_client
from retrieval import BM25Index, build_index, format_context

ROOT = Path(__file__).resolve().parent
PROMPT_PATH = ROOT / "system_prompt.md"
PDF_TEXT_DIR = ROOT / "data" / "pdfs"

TOP_K = 8
# Thresholds are deliberately moderate for an MVP starter harness — high enough
# to catch off-topic answers and hallucinations, low enough to tolerate the
# natural variance of an LLM judge. Tune via env as the corpus matures.
ANSWER_RELEVANCY_THRESHOLD = float(os.environ.get("ANSWER_RELEVANCY_THRESHOLD", "0.7"))
FAITHFULNESS_THRESHOLD = float(os.environ.get("FAITHFULNESS_THRESHOLD", "0.7"))

# Starter evaluation dataset: questions that map cleanly onto the supplement
# guides in data/pdfs. ``reference`` documents the gist of a good answer; the
# two metrics in use don't require a gold answer, but it keeps the dataset
# self-documenting and ready for ground-truth metrics later.
DATASET = [
    {
        "input": "What supplements can help me sleep better?",
        "reference": "Melatonin and magnesium are commonly recommended for sleep.",
    },
    {
        "input": "Which supplements support muscle gain?",
        "reference": "Creatine and adequate protein support muscle growth.",
    },
    {
        "input": "What can I take to help with stress and anxiety?",
        "reference": "Ashwagandha and related adaptogens may help with stress.",
    },
    {
        "input": "Which supplements are recommended for joint health?",
        "reference": "Glucosamine, chondroitin, and omega-3s are used for joints.",
    },
    {
        "input": "How can I improve my memory and focus?",
        "reference": "Caffeine, L-theanine, and creatine are linked to focus.",
    },
    {
        "input": "What helps with managing blood sugar levels?",
        "reference": "Berberine and chromium are studied for blood sugar control.",
    },
    {
        "input": "Which supplements support cardiovascular health?",
        "reference": "Omega-3 fish oil and CoQ10 support heart health.",
    },
]


# ---------------------------------------------------------------------------
# Fixtures — built once per test session and reused across every case.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def api_key() -> str:
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        pytest.skip("GOOGLE_API_KEY not set — skipping live RAG evaluation.")
    return key


@pytest.fixture(scope="session")
def index() -> BM25Index:
    return build_index(PDF_TEXT_DIR)


@pytest.fixture(scope="session")
def system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def rag_client(api_key: str):
    return get_client(api_key)


@pytest.fixture(scope="session")
def judge(api_key: str) -> GeminiJudge:
    return GeminiJudge(model_name=DEFAULT_MODEL, api_key=api_key)


@pytest.fixture(scope="session")
def metrics(judge: GeminiJudge):
    # async_mode=False so calls are serialized and the shared rate limiter
    # actually governs throughput (async mode would fire bursts in parallel).
    return [
        AnswerRelevancyMetric(
            threshold=ANSWER_RELEVANCY_THRESHOLD,
            model=judge,
            include_reason=True,
            async_mode=False,
        ),
        FaithfulnessMetric(
            threshold=FAITHFULNESS_THRESHOLD,
            model=judge,
            include_reason=True,
            async_mode=False,
        ),
    ]


# ---------------------------------------------------------------------------
# RAG pipeline under test — mirrors agent_site/app.py's single-turn behavior.
# ---------------------------------------------------------------------------
def run_rag(question: str, index: BM25Index, system_prompt: str, client) -> tuple[str, List[str]]:
    """Answer one question with the production retrieval + generation settings.

    Returns the model's answer and the list of retrieved passages, which become
    the ``retrieval_context`` the Faithfulness metric checks the answer against.
    """
    hits = index.guide_aware_search(question, k=TOP_K)
    retrieval_context = [
        f"[supplement-guide-{chunk.source}] {chunk.text}" for chunk, _ in hits
    ]

    instruction = (
        system_prompt + "\n\n## Retrieved passages\n\n" + format_context(hits)
    )
    config = types.GenerateContentConfig(
        system_instruction=instruction,
        max_output_tokens=8192,
        temperature=0.3,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )
    response = generate_content(
        client,
        [{"role": "user", "parts": [{"text": question}]}],
        config,
        model=DEFAULT_MODEL,
        limiter=LIMITER,
    )
    answer = response.text or ""
    if not answer.strip():
        raise RuntimeError(f"RAG pipeline returned an empty answer for: {question!r}")
    return answer, retrieval_context


# ---------------------------------------------------------------------------
# The test: one parametrized case per QA pair.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("case", DATASET, ids=[c["input"] for c in DATASET])
def test_rag_quality(case, index, system_prompt, rag_client, metrics):
    answer, retrieval_context = run_rag(case["input"], index, system_prompt, rag_client)

    test_case = LLMTestCase(
        input=case["input"],
        actual_output=answer,
        retrieval_context=retrieval_context,
        expected_output=case.get("reference"),
    )
    # run_async=False serializes the two metrics so all judge calls stay within
    # the shared rate-limit budget.
    assert_test(test_case, metrics, run_async=False)
