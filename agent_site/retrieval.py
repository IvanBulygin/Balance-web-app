"""
BM25 retrieval over the 17 supplement-guide text files.

No embedding API key needed — classic term-frequency retrieval, tokenized
with a simple regex and a small English stopword list. Fast enough that
we build the index on startup and keep it in memory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-']*")

# Body section headers in the guides are prefixed with a form-feed (page break);
# the same names also appear in the table of contents WITHOUT a form-feed, so the
# form-feed is what lets us tell a real section header from a TOC line.
_SECTION_HEADER_RE = re.compile(
    r"^\f[ \t]*("
    r"introduction|combos|primary supplements|secondary supplements|"
    r"promising supplements|unproven supplements|inadvisable supplements|faq|references"
    r")[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)

# Sections that actually recommend supplements (with doses/tiers). When a guide
# clearly dominates a query, these get injected so the answer can list every
# supplement, not just the ones whose prose happens to echo the query words.
RECOMMENDATION_SECTIONS = ("combos", "primary supplements", "secondary supplements", "promising supplements")
_SECTION_ORDER = {name: i for i, name in enumerate(RECOMMENDATION_SECTIONS)}

# Aggregated BM25 score a guide must reach for a query to count as clearly
# "about" that guide — used both to gate the recommendation injection and to
# tell a self-contained question from a vague follow-up.
BOOST_MIN_SCORE = 50.0

# Within a supplement entry, these phrases mark the chunks that name the
# supplement / its tier ("What makes X a secondary supplement") and its dose
# ("How to take X") — the parts an answer actually needs.
_KEY_RECO_RE = re.compile(r"what makes |how to take ", re.IGNORECASE)
# A dose, e.g. "5 g", "2000 IU", "300 mg", "10 billion CFU" — marks the chunks
# in the Combos section that hold real protocols rather than boilerplate.
_DOSE_RE = re.compile(r"\d[\d,.]*\s?(?:mg|mcg|µg|g|grams?|iu|ml|billion)\b", re.IGNORECASE)


def _reco_priority(chunk: Chunk) -> int:
    # Surface actionable content first: per-supplement intro/dosing headers and
    # combo protocols that carry doses, then any other chunk that states a dose
    # (timing/how-much detail often spills past the "How to take" header), then
    # the rest. Combos boilerplate (quality disclaimers, "why we don't recommend
    # brands") sinks to the bottom.
    if _KEY_RECO_RE.search(chunk.text):
        return 0
    if chunk.section == "combos":
        return 0 if _DOSE_RE.search(chunk.text) else 2
    if _DOSE_RE.search(chunk.text):
        return 1
    return 2

# Minimal stopword list. Kept short on purpose — BM25 handles common terms
# reasonably well, we just drop the truly noisy ones.
_STOPWORDS = frozenset(
    """a an the and or but if then else of in on at to for with by from as is are was were be been being
    this that these those it its it's they them their there here what which who whom whose when where why how
    do does did doing done have has had having i you he she we us our your my me mine yours his hers ours theirs
    about above below between under over into through during before after than so not no yes also just only very much
    can could should would may might will shall must
    """.split()
)


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


@dataclass
class Chunk:
    source: str  # e.g. "sleep"
    text: str
    section: str = ""  # normalized section name, e.g. "secondary supplements"


def _split_into_chunks(text: str, target_chars: int = 600, overlap: int = 100) -> list[str]:
    """Split text into chunks of ~target_chars, breaking on paragraph boundaries
    where possible. Small overlap keeps context across chunk boundaries."""
    # Normalize whitespace but preserve paragraph breaks. Drop form-feeds
    # (page-break markers) so they never leak into chunk text.
    paragraphs = [p.replace("\f", " ").strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for para in paragraphs:
        if buf_len + len(para) + 2 > target_chars and buf:
            chunks.append("\n\n".join(buf))
            # carry tail as overlap
            tail = chunks[-1][-overlap:]
            buf = [tail, para] if tail else [para]
            buf_len = sum(len(x) for x in buf) + 2 * (len(buf) - 1)
        else:
            buf.append(para)
            buf_len += len(para) + 2
    if buf:
        chunks.append("\n\n".join(buf))
    # Filter out anything trivially short.
    return [c for c in chunks if len(c) > 80]


def _split_into_sections(text: str) -> list[tuple[str, str]]:
    """Split a guide into (section_name, body) pairs on its form-feed section
    headers. Text before the first recognized header is labeled "" (preamble).
    Guides without these headers (e.g. the evidence database) yield a single
    untagged section, so they still get indexed and searched normally."""
    matches = list(_SECTION_HEADER_RE.finditer(text))
    if not matches:
        return [("", text)]
    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        sections.append(("", text[: matches[0].start()]))
    for i, m in enumerate(matches):
        name = m.group(1).strip().lower()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((name, text[start:end]))
    return sections


def _source_label(path: Path) -> str:
    # "supplement-guide-sleep.txt" -> "sleep"
    name = path.stem
    if name.startswith("supplement-guide-"):
        name = name[len("supplement-guide-") :]
    return name


class BM25Index:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        tokenized = [_tokenize(c.text) for c in chunks]
        self.bm25 = BM25Okapi(tokenized)
        # source -> indices of its recommendation-section chunks, ordered so the
        # most useful land first: the Combos summary, then each supplement's
        # "What makes..." intro and "How to take..." dosing, then the rest
        # (mechanism/warnings prose). This lets us cap the injection to a budget
        # without dropping any supplement's name or dose.
        self._reco_index: dict[str, list[int]] = {}
        for i, c in enumerate(chunks):
            if c.section in _SECTION_ORDER:
                self._reco_index.setdefault(c.source, []).append(i)
        for src, idxs in self._reco_index.items():
            idxs.sort(key=lambda i: (_reco_priority(chunks[i]), _SECTION_ORDER[chunks[i].section], i))

    def search(self, query: str, k: int = 5) -> list[tuple[Chunk, float]]:
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        # argsort desc, take top-k with positive score
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        out: list[tuple[Chunk, float]] = []
        for i in ranked[:k]:
            if scores[i] <= 0:
                break
            out.append((self.chunks[i], float(scores[i])))
        return out

    def guide_aware_search(
        self,
        query: str,
        k: int = 5,
        pool: int = 40,
        max_reco_chunks: int = 30,
        boost_min_score: float = BOOST_MIN_SCORE,
    ) -> list[tuple[Chunk, float]]:
        """Retrieve, then — if one guide clearly owns the query — inject that
        guide's recommendation sections.

        Plain BM25 ranks chunks by how often they echo the query words, which
        surfaces topical prose ("...sore joints...") while burying the chunks
        that actually name and dose supplements (those often share almost no
        words with a question like "best supplements for sore joints"). Worse,
        the single top-scoring chunk is noisy — for "increase testosterone" one
        stray blood-sugar chunk can outrank the whole testosterone guide. So we
        pick the dominant guide by *aggregating* BM25 score per guide across the
        pool, and only inject when that guide clears a score floor (off-topic or
        vague queries like "what's the weather" stay well below it and fall back
        to plain ranking). The injected Combos/Primary/Secondary/Promising
        sections let the model list every recommended supplement; the top BM25
        hits are appended for context.
        """
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        top = [i for i in ranked[:pool] if scores[i] > 0]
        if not top:
            return []

        # Dominant guide = the recommendation-having guide with the highest total
        # BM25 score across the pool, provided it clears the boost floor.
        agg: dict[str, float] = {}
        for i in top:
            agg[self.chunks[i].source] = agg.get(self.chunks[i].source, 0.0) + scores[i]
        reco_sources = [s for s in sorted(agg, key=lambda s: -agg[s]) if s in self._reco_index]
        dominant = (
            reco_sources[0]
            if reco_sources and agg[reco_sources[0]] >= boost_min_score
            else None
        )

        selected: list[int] = []
        seen: set[int] = set()
        if dominant:
            for i in self._reco_index[dominant][:max_reco_chunks]:
                selected.append(i)
                seen.add(i)
        for i in top[:k]:
            if i not in seen:
                selected.append(i)
                seen.add(i)
        return [(self.chunks[i], float(scores[i])) for i in selected]

    def topical_score(self, query: str, pool: int = 40) -> float:
        """Highest aggregated BM25 score among recommendation-having guides for
        the query on its own. Lets callers tell a self-contained question
        ("how to improve afternoon energy?") from a vague follow-up ("best time
        to take it?") that needs conversation context to resolve."""
        tokens = _tokenize(query)
        if not tokens:
            return 0.0
        scores = self.bm25.get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        agg: dict[str, float] = {}
        for i in ranked[:pool]:
            if scores[i] <= 0:
                continue
            src = self.chunks[i].source
            if src in self._reco_index:
                agg[src] = agg.get(src, 0.0) + scores[i]
        return max(agg.values(), default=0.0)


def build_index(pdf_text_dir: Path) -> BM25Index:
    files = sorted(pdf_text_dir.glob("*.txt"))
    if not files:
        raise RuntimeError(f"No .txt files found in {pdf_text_dir}")
    chunks: list[Chunk] = []
    for f in files:
        source = _source_label(f)
        raw = f.read_text(encoding="utf-8", errors="ignore")
        for section, body in _split_into_sections(raw):
            for piece in _split_into_chunks(body):
                chunks.append(Chunk(source=source, text=piece, section=section))
    return BM25Index(chunks)


def format_context(hits: list[tuple[Chunk, float]]) -> str:
    """Render retrieved chunks as a context block for the system prompt."""
    if not hits:
        return "(no relevant passages retrieved)"
    blocks = []
    for i, (chunk, score) in enumerate(hits, 1):
        label = f"supplement-guide-{chunk.source}"
        if chunk.section in _SECTION_ORDER:
            # Expose the tier so the model labels supplements correctly.
            label += f" · {chunk.section}"
        blocks.append(f"[{i}] source: {label} (score {score:.2f})\n{chunk.text}")
    return "\n\n---\n\n".join(blocks)
