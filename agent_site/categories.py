"""
Structured per-guide responses for the Balance.ai category-based UI.

Backs ``GET /api/category/{slug}``. For a given supplement-guide source we
gather the guide's Introduction (for PROBLEMS / WHAT YOU CAN DO) plus its
recommendation sections (Combos, Primary, Secondary, Promising), then ask
gemini-2.5-flash to emit a structured :class:`CategoryGuide` via
``response_schema``. The server then drops anything that didn't come back with a
Primary/Secondary/Promising tier (so Unproven/Inadvisable can't sneak through),
orders by tier, and attaches an iHerb search URL per supplement so the UI can
link straight out to buy.

Results are cached in-process per slug — each guide-level extraction is
deterministic-enough and one Gemini call costs a free-tier minute, so caching
matters here.
"""

from __future__ import annotations

import json
import threading
import urllib.parse
from pathlib import Path
from typing import Dict, List, Literal, Optional

from google.genai import types
from pydantic import BaseModel

from gemini_client import DEFAULT_MODEL, LIMITER, generate_content
from retrieval import BM25Index, Chunk

# Section labels emitted by retrieval._SECTION_HEADER_RE.
_INTRO_SECTIONS = ("", "introduction")
_RECO_SECTIONS = (
    "combos",
    "primary supplements",
    "secondary supplements",
    "promising supplements",
)
# Tiers we'll surface to the UI, in presentation order. Anything else
# (Unproven, Inadvisable, or a model hallucination) is dropped server-side.
_TIER_ORDER = {"Primary": 0, "Secondary": 1, "Promising": 2}

# Friendly titles. If a slug isn't listed we fall back to the model's title.
DISPLAY_TITLES: Dict[str, str] = {
    "memory-focus": "Memory & Focus",
    "sleep": "Sleep",
    "stress-anxiety": "Stress & Anxiety",
    "mood-depression": "Mood",
    "muscle-gain": "Muscle Gain",
    "fat-loss": "Fat Loss",
    "cardiovascular-health": "Heart Health",
    "joint-health": "Joint Health",
    "allergies-immunity": "Immunity",
    "skin-hair-nails": "Skin, Hair & Nails",
    "libido": "Libido",
    "liver-health": "Liver Health",
    "bone-health": "Bone Health",
    "blood-sugar": "Blood Sugar",
    "testosterone": "Testosterone",
    "recovery-wellness": "Recovery",
    "vegetarians-vegans": "Vegetarian & Vegan",
    "healthy-aging": "Healthy Aging",
}


class CauseFactor(BaseModel):
    title: str
    description: str


class Lever(BaseModel):
    title: str
    description: str


class Supplement(BaseModel):
    name: str
    tier: Literal["Primary", "Secondary", "Promising"]
    form: str = ""
    dose: str
    timing: str = ""
    evidence: str


class CategoryGuide(BaseModel):
    """Schema the model is asked to populate."""

    title: str
    problems: List[CauseFactor]
    what_you_can_do: List[Lever]
    supplements: List[Supplement]


class SupplementWithLink(Supplement):
    iherb_url: str


class CategoryResponse(BaseModel):
    """Schema the API returns (model output + server-attached iHerb URLs)."""

    slug: str
    title: str
    problems: List[CauseFactor]
    what_you_can_do: List[Lever]
    supplements: List[SupplementWithLink]


SYSTEM_PROMPT = """You are extracting structured information from a single supplement guide.

You will be given excerpts from one guide. Produce a JSON object matching the
requested schema using ONLY information from the excerpts.

Field rules:
- title: the human-readable name for this guide (e.g. "Memory & Focus").
- problems: 3-5 specific causes/contributors the guide names. Each is a short
  title (2-5 words) plus a single-sentence description.
- what_you_can_do: 3-5 actionable strategies/levers the guide presents. Each is
  a short title (2-5 words) plus a single-sentence description.
- supplements: EVERY supplement the guide marks as Primary, Secondary, or
  Promising. DO NOT include anything the guide marks as Unproven or Inadvisable.
  - name: the supplement name as written in the guide.
  - tier: EXACTLY "Primary", "Secondary", or "Promising" matching the guide's
    own labelling for that supplement.
  - form: the specific form if the guide names one; empty string if not.
  - dose: the dose from the guide, including units (e.g. "300-600 mg/day").
  - timing: when/how to take it; empty string if the guide doesn't say.
  - evidence: a one-sentence summary of why the guide recommends this supplement.

If the guide describes a combo/protocol (e.g. "200 mg caffeine + 200 mg
theanine"), list each component as its own supplement entry and reference the
combo in the timing or evidence field.

Use plain text. No markdown, no citations, no emojis."""


def _iherb_url(name: str) -> str:
    return "https://www.iherb.com/search?kw=" + urllib.parse.quote_plus(name.strip())


def _gather_chunks(index: BM25Index, source: str) -> tuple[List[Chunk], List[Chunk]]:
    """Pull this source's intro chunks and its recommendation-section chunks."""
    intro, reco = [], []
    for chunk in index.chunks:
        if chunk.source != source:
            continue
        if chunk.section in _INTRO_SECTIONS:
            intro.append(chunk)
        elif chunk.section in _RECO_SECTIONS:
            reco.append(chunk)
    return intro, reco


def _build_prompt(slug: str, intro: List[Chunk], reco: List[Chunk]) -> str:
    sections: List[str] = [f"# guide: supplement-guide-{slug}"]
    if intro:
        sections.append(
            "## Introduction\n\n" + "\n\n".join(c.text for c in intro)
        )
    if reco:
        sections.append(
            "## Recommendations\n\n"
            + "\n\n---\n\n".join(
                f"[section: {c.section}]\n{c.text}" for c in reco
            )
        )
    return "\n\n".join(sections)


def _extract(client, slug: str, index: BM25Index) -> CategoryResponse:
    intro, reco = _gather_chunks(index, slug)
    if not intro and not reco:
        raise LookupError(f"No content for category slug '{slug}'.")

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.2,
        max_output_tokens=8192,
        response_mime_type="application/json",
        response_schema=CategoryGuide,
        # The structured-output prompt is explicit; thinking would chew the
        # output budget and risk truncating the JSON.
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )
    response = generate_content(
        client,
        _build_prompt(slug, intro, reco),
        config,
        model=DEFAULT_MODEL,
        limiter=LIMITER,
    )

    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, CategoryGuide):
        guide = parsed
    else:
        guide = CategoryGuide.model_validate_json(response.text or "{}")

    # Drop anything that came back with a tier outside the allowed set
    # (defensive — Unproven/Inadvisable should never appear, but the Literal
    # would also fail validation if the model tried), and present by tier.
    keep = [s for s in guide.supplements if s.tier in _TIER_ORDER]
    keep.sort(key=lambda s: _TIER_ORDER[s.tier])
    enriched = [
        SupplementWithLink(**s.model_dump(), iherb_url=_iherb_url(s.name))
        for s in keep
    ]

    return CategoryResponse(
        slug=slug,
        title=DISPLAY_TITLES.get(slug, guide.title),
        problems=guide.problems,
        what_you_can_do=guide.what_you_can_do,
        supplements=enriched,
    )


class CategoryCache:
    """Cache keyed by slug, backed by an on-disk JSON store.

    Category guides are deterministic per slug, so we never want to pay the
    Gemini extraction more than once. Lookup order is: in-memory → disk →
    Gemini (then written through to both). Committing ``cache_dir`` into the
    repo makes every guide load instantly in production with zero LLM calls —
    important on hosts with an ephemeral filesystem (e.g. Render free tier),
    where a runtime-only cache is lost on each cold start.
    """

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        self._lock = threading.Lock()
        self._cache: Dict[str, CategoryResponse] = {}
        self._dir = Path(cache_dir) if cache_dir else None

    def _path(self, slug: str) -> Optional[Path]:
        return (self._dir / f"{slug}.json") if self._dir else None

    def _load_disk(self, slug: str) -> Optional[CategoryResponse]:
        path = self._path(slug)
        if not path or not path.exists():
            return None
        try:
            return CategoryResponse.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - a corrupt cache file shouldn't 500
            print(f"[category {slug}] ignoring bad cache file: {exc}")
            return None

    def _save_disk(self, slug: str, response: CategoryResponse) -> None:
        path = self._path(slug)
        if not path:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001 - caching is best-effort
            print(f"[category {slug}] could not write cache: {exc}")

    def get_or_fetch(
        self, client, index: BM25Index, slug: str, *, force: bool = False
    ) -> CategoryResponse:
        if not force:
            cached = self._cache.get(slug)
            if cached is not None:
                return cached
            disk = self._load_disk(slug)
            if disk is not None:
                with self._lock:
                    self._cache[slug] = disk
                return disk
        # Miss: pay the one Gemini extraction, then write through to memory+disk.
        response = _extract(client, slug, index)
        with self._lock:
            self._cache[slug] = response
        self._save_disk(slug, response)
        return response

    def invalidate(self, slug: Optional[str] = None) -> None:
        with self._lock:
            if slug is None:
                self._cache.clear()
            else:
                self._cache.pop(slug, None)


def available_slugs(index: BM25Index) -> List[str]:
    """Return slugs that have any retrievable content (excludes the evidence DB)."""
    seen: set[str] = set()
    for chunk in index.chunks:
        if chunk.source and chunk.source != "evidence-database":
            seen.add(chunk.source)
    return sorted(seen)
