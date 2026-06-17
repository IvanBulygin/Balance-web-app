"""
Deterministic evaluation harness for the Balance chat RAG pipeline.

Why this exists
---------------
``test_rag.py`` already scores answers with two LLM-as-a-judge metrics
(Answer Relevancy + Faithfulness). Those are useful but slow, cost API calls,
and carry judge variance — so they're a poor ruler for "did this change make
retrieval better?". This harness adds the missing ruler: a fast, free,
*deterministic* score for the things that actually drive answer quality here —
whether retrieval finds the right guide, and whether the supplements a correct
answer must list actually make it into the context (and the answer).

It has two layers:

* **Retrieval (no API key, instant).** For each golden query, does
  ``guide_aware_search`` surface the expected guide, and do the retrieved
  passages contain the supplements a good answer must mention? This is where
  most planned improvements live (query expansion, multi-guide injection,
  score normalization), so you can measure them without spending a token.

* **Answers (opt-in, needs GOOGLE_API_KEY).** Runs the real generation and
  checks supplement recall, groundedness (no supplement listed that isn't in
  the retrieved passages), and format adherence.

Usage
-----
    cd agent_site
    python -m eval.run_eval                 # retrieval layer only (fast/free)
    GOOGLE_API_KEY=... python -m eval.run_eval --answers
    python -m eval.run_eval --save baseline # snapshot scores to eval/baselines/
    python -m eval.run_eval --compare eval/baselines/<file>.json
    python -m eval.run_eval --answers --fail-under 0.8   # CI gate on overall

The scorecard is printed to stdout; a machine-readable snapshot is written when
``--save`` is given so gains can be tracked across commits.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow `python -m eval.run_eval` from agent_site/ and direct execution.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from retrieval import BM25Index, build_index, format_context  # noqa: E402

PDF_TEXT_DIR = ROOT / "data" / "pdfs"
PROMPT_PATH = ROOT / "system_prompt.md"
GOLDEN_PATH = Path(__file__).resolve().parent / "golden_set.json"
BASELINE_DIR = Path(__file__).resolve().parent / "baselines"

TOP_K = 8
try:
    from retrieval import BOOST_MIN_SCORE
except ImportError:  # pragma: no cover - retrieval always defines it
    BOOST_MIN_SCORE = 50.0


# ---------------------------------------------------------------------------
# Supplement matching: name -> aliases, matched on word boundaries so "iron"
# doesn't fire inside "environment" and "glycine" doesn't fire inside
# "glycinate" (the same boundary rule the front-end detector uses).
# ---------------------------------------------------------------------------
ALIASES: dict[str, list[str]] = {
    "Melatonin": ["melatonin"],
    "Lavender": ["lavender", "silexan"],
    "Ashwagandha": ["ashwagandha", "ksm-66"],
    "Lemon Balm": ["lemon balm", "melissa officinalis", "melissa"],
    "Saffron": ["saffron", "crocus"],
    "L-Theanine": ["l-theanine", "theanine"],
    "Magnesium": ["magnesium"],
    "Caffeine": ["caffeine"],
    "Bacopa Monnieri": ["bacopa"],
    "Creatine": ["creatine"],
    "Protein": ["protein", "whey"],
    "Beta-Alanine": ["beta-alanine", "beta alanine"],
    "Citrulline": ["citrulline"],
    "Glucosamine": ["glucosamine"],
    "Chondroitin": ["chondroitin"],
    "Curcumin": ["curcumin", "turmeric"],
    "Boswellia": ["boswellia"],
    "Collagen": ["collagen"],
    "Berberine": ["berberine"],
    "Chromium": ["chromium"],
    "Cinnamon": ["cinnamon"],
    "Inositol": ["inositol"],
    "Fiber": ["fiber", "fibre", "psyllium", "glucomannan"],
    "Omega-3": ["omega-3", "omega 3", "fish oil", "epa", "dha"],
    "Garlic": ["garlic", "allicin"],
    "CoQ10": ["coq10", "coenzyme q10", "ubiquinol"],
    "Zinc": ["zinc"],
    "Fenugreek": ["fenugreek"],
    "DHEA": ["dhea"],
    "Maca": ["maca"],
    "Tongkat Ali": ["tongkat ali", "tongkat", "eurycoma", "longjack"],
    "Tribulus": ["tribulus"],
    "Vitamin D": ["vitamin d", "vit d", "d3", "cholecalciferol"],
    "Rhodiola": ["rhodiola"],
    "Milk Thistle": ["milk thistle", "silymarin"],
    "NAC": ["nac", "n-acetyl", "acetylcysteine"],
    "TUDCA": ["tudca"],
    "SAMe": ["sam-e", "s-adenosyl"],
    "Vitamin C": ["vitamin c", "ascorbic"],
    "Echinacea": ["echinacea"],
    "Calcium": ["calcium"],
    "Vitamin K": ["vitamin k", "menaquinone", "phylloquinone", "k2"],
    "Green Tea": ["green tea", "egcg"],
    "Vitamin B12": ["vitamin b12", "b12", "b-12", "cobalamin"],
    "Iron": ["iron", "ferrous"],
    "Iodine": ["iodine", "kelp"],
}
# Names matched case-sensitively (where a lowercase alias would collide with a
# common English word, e.g. "SAMe" vs "same").
CASED_ALIASES: dict[str, list[str]] = {
    "SAMe": ["SAMe", "SAM-e"],
}


def _default_aliases(name: str) -> list[str]:
    low = name.lower()
    out = {low}
    if low.endswith("s"):
        out.add(low[:-1])
    return list(out)


def _boundary(alias: str) -> re.Pattern:
    return re.compile(r"(?:^|[^a-z0-9])" + re.escape(alias) + r"(?:[^a-z0-9]|$)")


def mentions(text: str, name: str) -> bool:
    """True if `name` (by any alias, on a word boundary) appears in `text`."""
    low = text.lower()
    for alias in ALIASES.get(name, _default_aliases(name)):
        if _boundary(alias).search(low):
            return True
    for cased in CASED_ALIASES.get(name, []):
        if re.search(r"(?:^|[^A-Za-z0-9])" + re.escape(cased) + r"(?:[^A-Za-z0-9]|$)", text):
            return True
    return False


_BOLD_ITEM_RE = re.compile(r"^\s*\d+\.\s*\*\*(.+?)\*\*", re.MULTILINE)


def listed_supplements(answer: str) -> list[str]:
    """Names the answer formally lists, e.g. '1. **Magnesium** `Primary`'."""
    return [m.group(1).strip() for m in _BOLD_ITEM_RE.finditer(answer)]


# ---------------------------------------------------------------------------
# Pipeline pieces (mirror app.py without importing FastAPI).
# ---------------------------------------------------------------------------
def retrieve(index: BM25Index, query: str):
    hits = index.guide_aware_search(query, k=TOP_K)
    sources = sorted({c.source for c, _ in hits})
    context = "\n\n".join(c.text for c, _ in hits)
    return hits, sources, context


def generate_answer(client, system_prompt: str, query: str, hits) -> str:
    from google.genai import types

    from gemini_client import DEFAULT_MODEL, LIMITER, generate_content

    instruction = system_prompt + "\n\n## Retrieved passages\n\n" + format_context(hits)
    config = types.GenerateContentConfig(
        system_instruction=instruction,
        max_output_tokens=8192,
        temperature=0.3,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )
    resp = generate_content(
        client,
        [{"role": "user", "parts": [{"text": query}]}],
        config,
        model=DEFAULT_MODEL,
        limiter=LIMITER,
    )
    return resp.text or ""


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def recall(text: str, expected: list[str]) -> tuple[float, list[str]]:
    if not expected:
        return 1.0, []
    missing = [s for s in expected if not mentions(text, s)]
    return (len(expected) - len(missing)) / len(expected), missing


def evaluate(do_answers: bool):
    golden = json.loads(GOLDEN_PATH.read_text())
    cases = golden["cases"]
    index = build_index(PDF_TEXT_DIR)

    client = system_prompt = None
    if do_answers:
        from gemini_client import get_client

        client = get_client()  # raises if GOOGLE_API_KEY missing
        system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    rows = []
    for c in cases:
        query, guide, must = c["query"], c.get("guide"), c.get("must_include", [])
        hits, sources, context = retrieve(index, query)
        topical = float(index.topical_score(query))

        if guide is None:
            # Off-topic: success = NOT confidently routed to any guide.
            guide_hit = bool(topical < BOOST_MIN_SCORE)
        else:
            guide_hit = bool(guide in sources)

        ctx_recall, ctx_missing = recall(context, must)

        row = {
            "id": c["id"],
            "query": query,
            "guide": guide,
            "guide_hit": guide_hit,
            "ctx_recall": round(ctx_recall, 3),
            "ctx_missing": ctx_missing,
            "topical": round(topical, 1),
        }

        if do_answers and guide is not None:
            answer = generate_answer(client, system_prompt, query, hits)
            ans_recall, ans_missing = recall(answer, must)
            listed = listed_supplements(answer)
            unsupported = [s for s in listed if not mentions(context, s) and len(s) > 2]
            grounded = 1.0 if not listed else (len(listed) - len(unsupported)) / len(listed)
            fmt_ok = ("### Recommended supplements" in answer) and (
                "healthcare provider" in answer.lower()
            )
            row.update(
                ans_recall=round(ans_recall, 3),
                ans_missing=ans_missing,
                groundedness=round(grounded, 3),
                unsupported=unsupported,
                format_ok=fmt_ok,
            )
        rows.append(row)
    return rows


def aggregate(rows: list[dict], do_answers: bool) -> dict:
    routed = [r for r in rows if r["guide"] is not None]
    have_must = [r for r in routed if r["ctx_missing"] or r["ctx_recall"] < 1.0 or True]
    agg = {
        "n_cases": len(rows),
        "guide_hit_rate": round(sum(r["guide_hit"] for r in rows) / len(rows), 3),
        "ctx_recall": round(sum(r["ctx_recall"] for r in routed) / max(len(routed), 1), 3),
    }
    if do_answers:
        ans = [r for r in rows if "ans_recall" in r]
        if ans:
            agg["ans_recall"] = round(sum(r["ans_recall"] for r in ans) / len(ans), 3)
            agg["groundedness"] = round(sum(r["groundedness"] for r in ans) / len(ans), 3)
            agg["format_ok_rate"] = round(sum(r["format_ok"] for r in ans) / len(ans), 3)
    # Single headline number: average of the available aggregate metrics.
    metric_vals = [v for k, v in agg.items() if k not in ("n_cases",)]
    agg["overall"] = round(sum(metric_vals) / len(metric_vals), 3)
    return agg


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def print_scorecard(rows, agg, do_answers):
    print("\n" + "=" * 78)
    print("BALANCE RAG EVAL — retrieval" + (" + answers" if do_answers else " only"))
    print("=" * 78)
    hdr = f"{'case':24} {'guide✓':7} {'ctxRcl':7}"
    if do_answers:
        hdr += f" {'ansRcl':7} {'grnd':6} {'fmt':4}"
    print(hdr)
    print("-" * 78)
    for r in rows:
        line = f"{r['id']:24} {('yes' if r['guide_hit'] else 'NO'):7} {r['ctx_recall']:<7.2f}"
        if do_answers and "ans_recall" in r:
            line += f" {r['ans_recall']:<7.2f} {r['groundedness']:<6.2f} {('ok' if r['format_ok'] else 'BAD'):4}"
        print(line)
        if r["ctx_missing"]:
            print(f"{'':26}↳ context missing: {', '.join(r['ctx_missing'])}")
        if do_answers and r.get("unsupported"):
            print(f"{'':26}↳ unsupported in answer: {', '.join(r['unsupported'])}")
    print("-" * 78)
    print("AGGREGATE:", json.dumps(agg))
    print("=" * 78 + "\n")


def main():
    ap = argparse.ArgumentParser(description="Balance RAG evaluation harness")
    ap.add_argument("--answers", action="store_true", help="run live generation (needs GOOGLE_API_KEY)")
    ap.add_argument("--save", metavar="NAME", help="save a baseline snapshot under eval/baselines/")
    ap.add_argument("--compare", metavar="PATH", help="diff aggregate against a saved baseline JSON")
    ap.add_argument("--fail-under", type=float, default=None, help="exit non-zero if 'overall' < threshold")
    ap.add_argument("--json", action="store_true", help="print machine-readable JSON only")
    args = ap.parse_args()

    if args.answers and not os.environ.get("GOOGLE_API_KEY"):
        print(
            "--answers needs GOOGLE_API_KEY (live generation). "
            "Run without --answers for the retrieval-only layer.",
            file=sys.stderr,
        )
        sys.exit(2)

    t0 = time.time()
    rows = evaluate(args.answers)
    agg = aggregate(rows, args.answers)
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha(),
        "answers": args.answers,
        "aggregate": agg,
        "rows": rows,
        "elapsed_s": round(time.time() - t0, 1),
    }

    if args.json:
        print(json.dumps(snapshot, indent=2))
    else:
        print_scorecard(rows, agg, args.answers)

    if args.compare:
        base = json.loads(Path(args.compare).read_text())["aggregate"]
        print("DELTA vs", args.compare)
        for k in sorted(set(agg) | set(base)):
            if isinstance(agg.get(k), (int, float)) and isinstance(base.get(k), (int, float)):
                d = round(agg[k] - base[k], 3)
                sign = "+" if d >= 0 else ""
                print(f"  {k:18} {base.get(k)} -> {agg.get(k)}  ({sign}{d})")
        print()

    if args.save:
        BASELINE_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        out = BASELINE_DIR / f"{args.save}-{stamp}.json"
        out.write_text(json.dumps(snapshot, indent=2))
        print(f"Saved baseline -> {out.relative_to(ROOT)}")

    if args.fail_under is not None and agg["overall"] < args.fail_under:
        print(f"FAIL: overall {agg['overall']} < {args.fail_under}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
