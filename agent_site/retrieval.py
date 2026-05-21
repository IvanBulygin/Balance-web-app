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


def _split_into_chunks(text: str, target_chars: int = 600, overlap: int = 100) -> list[str]:
    """Split text into chunks of ~target_chars, breaking on paragraph boundaries
    where possible. Small overlap keeps context across chunk boundaries."""
    # Normalize whitespace but preserve paragraph breaks.
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
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


def build_index(pdf_text_dir: Path) -> BM25Index:
    files = sorted(pdf_text_dir.glob("*.txt"))
    if not files:
        raise RuntimeError(f"No .txt files found in {pdf_text_dir}")
    chunks: list[Chunk] = []
    for f in files:
        source = _source_label(f)
        raw = f.read_text(encoding="utf-8", errors="ignore")
        for piece in _split_into_chunks(raw):
            chunks.append(Chunk(source=source, text=piece))
    return BM25Index(chunks)


def format_context(hits: list[tuple[Chunk, float]]) -> str:
    """Render retrieved chunks as a context block for the system prompt."""
    if not hits:
        return "(no relevant passages retrieved)"
    blocks = []
    for i, (chunk, score) in enumerate(hits, 1):
        blocks.append(
            f"[{i}] source: supplement-guide-{chunk.source} (score {score:.2f})\n{chunk.text}"
        )
    return "\n\n---\n\n".join(blocks)
