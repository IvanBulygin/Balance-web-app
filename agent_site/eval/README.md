# Balance RAG evaluation harness

A fast, deterministic ruler for chat answer quality — built to **measure the
gain** from retrieval/prompt changes before and after they ship.

It complements `../test_rag.py` (LLM-as-a-judge: Answer Relevancy + Faithfulness),
which is slower, costs API calls, and has judge variance. This harness scores
the things that most drive quality here — does retrieval find the right guide,
and do the supplements a correct answer must list actually reach the context
(and the answer) — with exact, repeatable numbers.

## Layers

- **Retrieval (default, no API key, ~instant).** Per golden query: did
  `guide_aware_search` surface the expected guide, and what fraction of the
  must-have supplements appear in the retrieved passages?
- **Answers (`--answers`, needs `GOOGLE_API_KEY`).** Runs real generation and
  adds: supplement recall in the answer, groundedness (no listed supplement
  that's absent from the retrieved passages), and format adherence.

## Run

```bash
cd agent_site
python -m eval.run_eval                      # retrieval layer (fast/free)
GOOGLE_API_KEY=... python -m eval.run_eval --answers
python -m eval.run_eval --save baseline      # snapshot to eval/baselines/
python -m eval.run_eval --compare eval/baselines/<file>.json   # show deltas
python -m eval.run_eval --answers --fail-under 0.8             # CI gate
```

## Metrics

| metric           | meaning                                                        |
|------------------|----------------------------------------------------------------|
| `guide_hit_rate` | share of queries routed to the expected guide (off-topic = not routed) |
| `ctx_recall`     | share of must-have supplements present in the retrieved passages |
| `ans_recall`     | share of must-have supplements named in the generated answer (`--answers`) |
| `groundedness`   | share of answer-listed supplements that are supported by the passages (`--answers`) |
| `format_ok_rate` | share of answers with the required heading + safety note (`--answers`) |
| `overall`        | mean of the above — one number to track per commit             |

## Workflow for measuring a change

1. `python -m eval.run_eval --save before`
2. make the retrieval/prompt change
3. `python -m eval.run_eval --compare eval/baselines/before-<stamp>.json`

The delta block shows exactly which aggregate metrics moved.

## Ground truth

Queries live in `golden_set.json`: each maps to the guide it should retrieve
and a curated set of must-have supplements. The must-have lists are drawn from
each guide's own "How to take X" entries (the authoritative recommended,
dosed supplements), so they stay faithful to the corpus. Supplement names are
matched by alias on word boundaries (e.g. `iron` won't fire inside
`environment`), mirroring the front-end detector.
