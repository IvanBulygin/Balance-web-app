"""
Pre-generate every category guide to the on-disk cache.

Category guides are deterministic per slug, so generating them once and
committing the JSON makes them load instantly in production with zero LLM
calls at request time — which matters on hosts with an ephemeral filesystem
(e.g. Render free tier), where a runtime-only cache is wiped on every cold
start and each guide would otherwise be slow on first visit.

Run it once (with your key), then commit the generated files:

    cd agent_site
    GOOGLE_API_KEY=... python warm_categories.py
    git add data/categories && git commit -m "Warm category guide cache"

Re-run after editing a guide's source text to refresh that slug.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from categories import CategoryCache, available_slugs
from gemini_client import get_client
from retrieval import build_index

ROOT = Path(__file__).resolve().parent
PDF_TEXT_DIR = ROOT / "data" / "pdfs"
CACHE_DIR = ROOT / "data" / "categories"


def main() -> int:
    client = get_client()  # reads GOOGLE_API_KEY, raises if missing
    index = build_index(PDF_TEXT_DIR)
    cache = CategoryCache(cache_dir=CACHE_DIR)
    slugs = available_slugs(index)
    print(f"Warming {len(slugs)} category guides -> {CACHE_DIR.relative_to(ROOT)}")

    ok, failed = 0, []
    for i, slug in enumerate(slugs, 1):
        t0 = time.time()
        try:
            cache.get_or_fetch(client, index, slug, force=True)
            print(f"  [{i}/{len(slugs)}] {slug:28} {time.time()-t0:4.1f}s  ok")
            ok += 1
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"  [{i}/{len(slugs)}] {slug:28} FAILED: {exc}")
            failed.append(slug)

    print(f"\nDone: {ok} ok, {len(failed)} failed." + (f" Failed: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
