"""
Balance.ai Wellbeing Agent — hosted as a web chatbot.

Serves a chat UI at / that talks to Google Gemini. Every user question
triggers BM25 retrieval over 19 supplement-guide text files; the top matching
passages are injected into the system prompt so Gemini answers only from
the retrieved evidence.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from retrieval import BM25Index, build_index, format_context

load_dotenv()

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
PROMPT_PATH = ROOT / "system_prompt.md"
PDF_TEXT_DIR = ROOT / "data" / "pdfs"

CHAT_MODEL = "gemini-3.5-flash"
MAX_TOKENS = 8192
MAX_HISTORY = 20
TOP_K = 15

state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not PROMPT_PATH.exists():
        raise RuntimeError(f"Missing {PROMPT_PATH}")
    state["system_prompt"] = PROMPT_PATH.read_text(encoding="utf-8")

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set")
    state["client"] = genai.Client(api_key=api_key)

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
    if len(user_turns) >= 2:
        return f"{user_turns[-2]}\n{user_turns[-1]}"
    return user_turns[-1]


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.messages:
        raise HTTPException(400, "messages required")

    convo, system_instruction, sources = _prepare_chat(req.messages)

    response = state["client"].models.generate_content(
        model=CHAT_MODEL,
        contents=convo,
        config={
            "system_instruction": system_instruction,
            "max_output_tokens": MAX_TOKENS,
            "temperature": 0.7,
        },
    )
    reply = response.text or ""
    return ChatResponse(reply=reply, sources=sources)


def _prepare_chat(messages: list[Message]):
    trimmed = messages[-MAX_HISTORY:]
    query = _build_query(trimmed)

    index: BM25Index = state["index"]
    hits = index.search(query, k=TOP_K) if query else []
    context_block = format_context(hits)
    sources = sorted({f"supplement-guide-{c.source}" for c, _ in hits})

    system_instruction = (
        state["system_prompt"]
        + "\n\n## Retrieved passages\n\n"
        "Use only these passages to answer. If they don't cover the "
        "question, say so.\n\n"
        + context_block
        + "\n\n## Reminder\n\n"
        "You MUST list EVERY supplement mentioned in the passages above. "
        "Do NOT stop after one or two. Include ALL Primary, Secondary, "
        "and Promising supplements with their Form, Dose, Timing, and "
        "Evidence fields. The user needs a COMPLETE shopping list."
    )

    convo = []
    for m in trimmed:
        role = "model" if m.role == "assistant" else "user"
        convo.append({"role": role, "parts": [{"text": m.content}]})

    return convo, system_instruction, sources


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    if not req.messages:
        raise HTTPException(400, "messages required")

    convo, system_instruction, sources = _prepare_chat(req.messages)

    def generate():
        stream = state["client"].models.generate_content_stream(
            model=CHAT_MODEL,
            contents=convo,
            config={
                "system_instruction": system_instruction,
                "max_output_tokens": MAX_TOKENS,
                "temperature": 0.7,
            },
        )
        for chunk in stream:
            text = chunk.text or ""
            if text:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
