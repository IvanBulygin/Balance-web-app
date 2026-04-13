"""
Build a vector index from extracted PDF text files.

Reads every .txt file in ../backend/data/pdfs/, chunks each file, embeds
every chunk with OpenAI text-embedding-3-small, and pickles the result to
index.pkl next to this script.

Run once locally before deploying, or let Render's build step invoke it.
Requires OPENAI_API_KEY in the environment.
"""

from __future__ import annotations

import os
import pickle
import re
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ROOT = Path(__file__).resolve().parent
TXT_DIR = ROOT.parent / "backend" / "data" / "pdfs"
INDEX_PATH = ROOT / "index.pkl"

EMBED_MODEL = "text-embedding-3-small"  # 1536 dims, matches Balance.ai docs
CHUNK_SIZE = 1200  # chars
CHUNK_OVERLAP = 150
BATCH_SIZE = 64


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text on paragraph-ish boundaries with a sliding window."""
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        # try to break on a paragraph or sentence boundary
        if end < n:
            window = text[start:end]
            split = max(window.rfind("\n\n"), window.rfind(". "))
            if split > size // 2:
                end = start + split + 1
        chunks.append(text[start:end].strip())
        if end == n:
            break
        start = end - overlap
    return [c for c in chunks if c]


def embed_batch(client: OpenAI, texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY not set")
    client = OpenAI(api_key=api_key)

    txt_files = sorted(TXT_DIR.glob("*.txt"))
    if not txt_files:
        raise SystemExit(f"No .txt files found in {TXT_DIR}")

    chunks: list[dict] = []
    for f in txt_files:
        text = f.read_text(encoding="utf-8")
        source = f.stem.replace("supplement-guide-", "").replace("-", " ").title()
        for i, piece in enumerate(chunk_text(text)):
            chunks.append({"source": source, "file": f.name, "chunk_index": i, "text": piece})
        print(f"{f.name}: {sum(1 for c in chunks if c['file'] == f.name)} chunks")

    print(f"\nTotal chunks: {len(chunks)}. Embedding in batches of {BATCH_SIZE}...")
    vectors: list[list[float]] = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = [c["text"] for c in chunks[i : i + BATCH_SIZE]]
        vectors.extend(embed_batch(client, batch))
        print(f"  embedded {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)}")

    matrix = np.asarray(vectors, dtype=np.float32)
    # pre-normalize for fast cosine via dot product
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    matrix = matrix / norms

    with INDEX_PATH.open("wb") as f:
        pickle.dump({"chunks": chunks, "matrix": matrix, "model": EMBED_MODEL}, f)
    print(f"\nWrote {INDEX_PATH} ({matrix.shape[0]} vectors, dim {matrix.shape[1]})")


if __name__ == "__main__":
    main()
