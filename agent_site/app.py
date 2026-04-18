"""
Balance.ai Wellbeing Agent — hosted as a web chatbot.

Serves a chat UI at / that talks to Anthropic Claude. Every user question
triggers BM25 retrieval over 17 supplement-guide PDFs; the top matching
passages are injected into the system prompt so Claude answers only from
the retrieved evidence.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from retrieval import BM25Index, build_index, format_context

load_dotenv()

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
PROMPT_PATH = ROOT / "system_prompt.md"
PDF_TEXT_DIR = ROOT / "data" / "pdfs"

CHAT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
MAX_HISTORY = 20  # trailing messages to keep when the client sends more
TOP_K = 15  # retrieved chunks per question

state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not PROMPT_PATH.exists():
        raise RuntimeError(f"Missing {PROMPT_PATH}")
    state["system_prompt"] = PROMPT_PATH.read_text(encoding="utf-8")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    state["client"] = Anthropic(api_key=api_key)

    print(f"Building BM25 index from {PDF_TEXT_DIR}...")
    index: BM25Index = build_index(PDF_TEXT_DIR)
    state["index"] = index
    print(
        f"Index ready. {len(index.chunks):,} chunks from "
        f"{len({c.source for c in index.chunks})} guides."
    )
    print(f"Agent ready. Model: {CHAT_MODEL}.")
    yield


app = FastAPI(title="Balance.ai Wellbeing Agent", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class Message(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class ChatResponse(BaseModel):
    reply: str
    sources: list[str]


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    idx: BM25Index | None = state.get("index")
    return {
        "status": "ok",
        "model": CHAT_MODEL,
        "chunks": len(idx.chunks) if idx else 0,
    }


def _build_query(messages: list[Message]) -> str:
    """Use the latest user message plus a bit of prior context for retrieval."""
    user_turns = [m.content for m in messages if m.role == "user"]
    if not user_turns:
        return ""
    # Most recent user turn carries the weight; include the one before it
    # if present, to catch pronoun/topic references.
    if len(user_turns) >= 2:
        return f"{user_turns[-2]}\n{user_turns[-1]}"
    return user_turns[-1]


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.messages:
        raise HTTPException(400, "messages required")

    trimmed = req.messages[-MAX_HISTORY:]
    query = _build_query(trimmed)

    index: BM25Index = state["index"]
    hits = index.search(query, k=TOP_K) if query else []
    context_block = format_context(hits)
    sources = sorted({f"supplement-guide-{c.source}" for c, _ in hits})

    # Put the system prompt first (cacheable-shaped) and append retrieved
    # passages as a secondary system block so they can vary per request.
    system_blocks = [
        {"type": "text", "text": state["system_prompt"]},
        {
            "type": "text",
            "text": (
                "## Retrieved passages\n\n"
                "Use only these passages to answer. If they don't cover the "
                "question, say so.\n\n"
                f"{context_block}"
            ),
        },
    ]

    convo = [{"role": m.role, "content": m.content} for m in trimmed]

    response = state["client"].messages.create(
        model=CHAT_MODEL,
        max_tokens=MAX_TOKENS,
        system=system_blocks,
        messages=convo,
    )
    reply = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    return ChatResponse(reply=reply, sources=sources)
