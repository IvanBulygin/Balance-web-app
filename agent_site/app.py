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
from pydantic import BaseModel, Field

from categories import CategoryCache, CategoryResponse, DISPLAY_TITLES, available_slugs
from gemini_client import get_client
from retrieval import BM25Index, BOOST_MIN_SCORE, build_index, format_context

load_dotenv()

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
PROMPT_PATH = ROOT / "system_prompt.md"
PDF_TEXT_DIR = ROOT / "data" / "pdfs"

# Primary is 2.5 Flash — capable, with a much higher free-tier daily quota than
# 3.5 Flash (which the free tier caps at 20 requests/day). Fallback matches;
# both are overridable via env. (When the two match, only one model is tried.)
CHAT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash")
CHAT_MODELS = [CHAT_MODEL] + (
    [FALLBACK_MODEL] if FALLBACK_MODEL and FALLBACK_MODEL != CHAT_MODEL else []
)
MAX_TOKENS = 8192
MAX_HISTORY = 6
# Number of query-specific BM25 hits to include alongside any guide injection.
# Kept a bit above 5 so a precise follow-up ("best time to take it?") still
# pulls in the exact passage, which can sit just outside the top few.
TOP_K = 8

state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not PROMPT_PATH.exists():
        raise RuntimeError(f"Missing {PROMPT_PATH}")
    state["system_prompt"] = PROMPT_PATH.read_text(encoding="utf-8")

    state["client"] = get_client()  # reads GOOGLE_API_KEY, raises if missing

    print(f"Building BM25 index from {PDF_TEXT_DIR}...")
    index: BM25Index = build_index(PDF_TEXT_DIR)
    state["index"] = index
    state["category_cache"] = CategoryCache()
    print(
        f"Index ready. {len(index.chunks):,} chunks from "
        f"{len({c.source for c in index.chunks})} guides."
    )
    print(f"Agent ready. Models (in order): {CHAT_MODELS}.")
    yield


app = FastAPI(title="Balance.ai Wellbeing Agent", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.middleware("http")
async def revalidate_html_and_jsx(request, call_next):
    """Force browsers to revalidate the app shell on every load.

    The HTML and JSX change on every deploy; without this, browsers
    heuristically cache them and users keep seeing the previous build until
    a manual hard-refresh. ``no-cache`` still allows caching but requires a
    conditional request (304 when unchanged), so deploys appear immediately
    on a normal reload. Fonts/other static assets keep their default caching.
    """
    response = await call_next(request)
    path = request.url.path
    if path in ("/", "/chat") or path.endswith((".html", ".jsx")):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


class Message(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    stack: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    sources: list[str]


@app.get("/")
def index():
    # New guided Learn-grid → Detail → Stack flow.
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/chat")
def chat_page():
    # Open chat UI, still reachable alongside the guided flow.
    return FileResponse(STATIC_DIR / "chat.html")


@app.get("/api/health")
def health():
    idx: BM25Index | None = state.get("index")
    return {
        "status": "ok",
        "model": CHAT_MODEL,
        "models": CHAT_MODELS,
        "chunks": len(idx.chunks) if idx else 0,
    }


class CategorySummary(BaseModel):
    slug: str
    title: str


@app.get("/api/categories", response_model=list[CategorySummary])
def list_categories():
    idx: BM25Index | None = state.get("index")
    if idx is None:
        raise HTTPException(503, "index not ready")
    summaries = [
        CategorySummary(slug=slug, title=DISPLAY_TITLES.get(slug, slug.replace("-", " ").title()))
        for slug in available_slugs(idx)
    ]
    return summaries


@app.get("/api/category/{slug}", response_model=CategoryResponse)
def get_category(slug: str):
    idx: BM25Index | None = state.get("index")
    cache: CategoryCache | None = state.get("category_cache")
    if idx is None or cache is None:
        raise HTTPException(503, "index not ready")
    if slug not in available_slugs(idx):
        raise HTTPException(404, f"unknown category '{slug}'")
    try:
        return cache.get_or_fetch(state["client"], idx, slug)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:  # noqa: BLE001 - surface friendly to UI
        print(f"[category {slug}] {exc}")
        raise HTTPException(503, _friendly_error(exc))


def _build_query(messages: list[Message]) -> str:
    """Build a retrieval query from the latest question plus recent context.

    A self-contained question ("how to improve afternoon energy?") is used on
    its own — folding in the previous exchange would drag a fresh topic toward
    whatever was discussed before. A vague follow-up ("best time to take it?",
    "any side effects?") carries no topic words, so we fold in the last
    assistant turn and prior user turn to resolve what it refers to.
    """
    user_turns = [m.content for m in messages if m.role == "user"]
    if not user_turns:
        return ""
    current = user_turns[-1]

    index: BM25Index | None = state.get("index")
    if index is not None and index.topical_score(current) >= BOOST_MIN_SCORE:
        return current  # self-contained — don't pollute with prior context

    assistant_turns = [m.content for m in messages if m.role == "assistant"]
    parts: list[str] = []
    if len(user_turns) >= 2:
        parts.append(user_turns[-2])
    if assistant_turns:
        parts.append(assistant_turns[-1][:2000])
    parts.append(current)
    return "\n".join(parts)


def _friendly_error(exc: Exception) -> str:
    msg = str(exc)
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
        return (
            "⚠️ We've reached today's usage limit for the AI service. "
            "Please try again later."
        )
    return "⚠️ The assistant is temporarily unavailable — please try again in a moment."


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.messages:
        raise HTTPException(400, "messages required")

    convo, system_instruction, sources = _prepare_chat(req.messages, req.stack)

    gen_config = {
        "system_instruction": system_instruction,
        "max_output_tokens": MAX_TOKENS,
        "temperature": 0.3,
        # 2.5 Flash is a thinking model; left on, thinking tokens consume the
        # output budget and truncate long answers (finishReason=MAX_TOKENS).
        # This RAG task just formats retrieved facts, so disable thinking for
        # complete (and faster) responses.
        "thinking_config": {"thinking_budget": 0},
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
        raise HTTPException(503, _friendly_error(last_err))
    return ChatResponse(reply=reply, sources=sources)


def _prepare_chat(messages: list[Message], stack: list[str] | None = None):
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
    if stack:
        names = ", ".join(s.strip() for s in stack if s.strip())
        if names:
            system_instruction += (
                "\n\n## User's current stack\n\n"
                f"The user already takes: {names}. "
                "When they ask about stacking, combining, or interactions with "
                '"my current supps", reason about these specific supplements '
                "using the retrieved passages."
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

    convo, system_instruction, sources = _prepare_chat(req.messages, req.stack)

    gen_config = {
        "system_instruction": system_instruction,
        "max_output_tokens": MAX_TOKENS,
        "temperature": 0.3,
        # 2.5 Flash is a thinking model; left on, thinking tokens consume the
        # output budget and truncate long answers (finishReason=MAX_TOKENS).
        # This RAG task just formats retrieved facts, so disable thinking for
        # complete (and faster) responses.
        "thinking_config": {"thinking_budget": 0},
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
            note = "\n\n" + _friendly_error(last_err)
            yield f"data: {json.dumps({'text': note})}\n\n"
        yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
