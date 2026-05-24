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
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from pydantic import BaseModel, Field

from retrieval import BM25Index, build_index, format_context

load_dotenv()

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
PROMPT_PATH = ROOT / "system_prompt.md"
PDF_TEXT_DIR = ROOT / "data" / "pdfs"

# Primary is the fast/cheap Flash-Lite tier. If that exact ID is not enabled on
# the API key, fall back to a known-good model so chat keeps working. Both are
# overridable via env without a code change.
CHAT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash")
CHAT_MODELS = [CHAT_MODEL] + (
    [FALLBACK_MODEL] if FALLBACK_MODEL and FALLBACK_MODEL != CHAT_MODEL else []
)
MAX_TOKENS = 4096
MAX_HISTORY = 6
TOP_K = 5

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
    print(f"Agent ready. Models (in order): {CHAT_MODELS}.")
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
        "models": CHAT_MODELS,
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

    gen_config = {
        "system_instruction": system_instruction,
        "max_output_tokens": MAX_TOKENS,
        "temperature": 0.7,
    }
    reply = ""
    last_err: Exception | None = None
    for model in CHAT_MODELS:
        try:
            response = state["client"].models.generate_content(
                model=model, contents=convo, config=gen_config
            )
            reply = response.text or ""
            last_err = None
            break
        except Exception as exc:  # noqa: BLE001 - surface model/runtime errors
            last_err = exc
            print(f"[chat] model {model} failed: {exc}")
    if last_err is not None and not reply:
        raise HTTPException(502, f"Model error: {last_err}")
    return ChatResponse(reply=reply, sources=sources)


def _prepare_chat(messages: list[Message]):
    trimmed = messages[-MAX_HISTORY:]
    query = _build_query(trimmed)

    index: BM25Index = state["index"]
    hits = index.guide_aware_search(query, k=TOP_K) if query else []
    context_block = format_context(hits)
    sources = sorted({f"supplement-guide-{c.source}" for c, _ in hits})

    system_instruction = (
        state["system_prompt"]
        + "\n\n## Retrieved passages\n\n"
        + context_block
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

    gen_config = {
        "system_instruction": system_instruction,
        "max_output_tokens": MAX_TOKENS,
        "temperature": 0.7,
    }

    def generate():
        last_err: Exception | None = None
        for model in CHAT_MODELS:
            produced = False
            try:
                stream = state["client"].models.generate_content_stream(
                    model=model, contents=convo, config=gen_config
                )
                for chunk in stream:
                    text = chunk.text or ""
                    if text:
                        produced = True
                        yield f"data: {json.dumps({'text': text})}\n\n"
                last_err = None
                break
            except Exception as exc:  # noqa: BLE001 - surface model/runtime errors
                last_err = exc
                print(f"[chat] stream model {model} failed: {exc}")
                if produced:
                    break  # already streamed partial output; retrying would duplicate
        if last_err is not None:
            note = f"\n\n⚠️ The AI service returned an error: {last_err}"
            yield f"data: {json.dumps({'text': note})}\n\n"
        yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
