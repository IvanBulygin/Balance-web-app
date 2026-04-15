"""
Balance.ai Phase 0 demo RAG.

Serves a single-page chat UI at / and a POST /api/ask endpoint that
answers questions from the Examine.com supplement guides using
OpenAI GPT-4o grounded in retrieved chunks from index.pkl.

This is a STANDALONE DEMO — not the documented Balance.ai production
stack. The production RAG uses Supabase + pgvector per Phase 1A.
"""

from __future__ import annotations

import os
import pickle
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / "index.pkl"
STATIC_DIR = ROOT / "static"

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o"
TOP_K = 8

SYSTEM_PROMPT = (
    "You are Balance.ai's research assistant. Answer the user's question using "
    "ONLY the supplement guide excerpts provided in the context. Cite sources "
    "inline as [Source: <name>] immediately after claims. If the context does "
    "not contain the answer, say so plainly — do not guess. Be concise and "
    "evidence-focused."
)


state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    state["client"] = OpenAI(api_key=api_key)

    if not INDEX_PATH.exists():
        print(f"No index found at {INDEX_PATH}. Building on first boot...")
        import build_index  # local module, same directory
        build_index.main()

    with INDEX_PATH.open("rb") as f:
        data = pickle.load(f)
    state["chunks"] = data["chunks"]
    state["matrix"] = data["matrix"]  # (N, 1536) pre-normalized float32
    print(f"Loaded index: {state['matrix'].shape[0]} chunks")
    yield


app = FastAPI(title="Balance.ai Demo RAG", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class AskRequest(BaseModel):
    question: str


class Citation(BaseModel):
    source: str
    file: str
    snippet: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]


def embed_query(text: str) -> np.ndarray:
    resp = state["client"].embeddings.create(model=EMBED_MODEL, input=[text])
    v = np.asarray(resp.data[0].embedding, dtype=np.float32)
    n = np.linalg.norm(v) or 1.0
    return v / n


def retrieve(query_vec: np.ndarray, k: int = TOP_K) -> list[dict]:
    scores = state["matrix"] @ query_vec  # cosine since both normalized
    top_idx = np.argsort(-scores)[:k]
    return [{**state["chunks"][i], "score": float(scores[i])} for i in top_idx]


def build_context(hits: list[dict]) -> str:
    blocks = []
    for h in hits:
        blocks.append(f"[Source: {h['source']}]\n{h['text']}")
    return "\n\n---\n\n".join(blocks)


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "chunks": len(state.get("chunks", []))}


@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "empty question")

    qv = embed_query(question)
    hits = retrieve(qv)
    context = build_context(hits)

    completion = state["client"].chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n\n{context}\n\nQuestion: {question}"},
        ],
        temperature=0.2,
    )
    answer = completion.choices[0].message.content or ""

    seen: set[str] = set()
    citations: list[Citation] = []
    for h in hits:
        if h["source"] in seen:
            continue
        seen.add(h["source"])
        snippet = h["text"][:240].replace("\n", " ").strip() + "..."
        citations.append(Citation(source=h["source"], file=h["file"], snippet=snippet))

    return AskResponse(answer=answer, citations=citations)
