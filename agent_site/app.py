"""
Balance.ai Project Agent — hosted as a web chatbot.

Serves a chat UI at / that talks to Anthropic Claude with the Balance.ai
Project Agent system prompt from system_prompt.md. Visitors can ask
product questions (phases, schemas, XP economy, roadmap) and get
answers grounded in the documented project.
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

load_dotenv()

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
PROMPT_PATH = ROOT / "system_prompt.md"

CHAT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048
MAX_HISTORY = 30  # trailing messages to keep when the client sends more

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
    print(f"Agent ready. Model: {CHAT_MODEL}. System prompt: {len(state['system_prompt']):,} chars")
    yield


app = FastAPI(title="Balance.ai Project Agent", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class Message(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class ChatResponse(BaseModel):
    reply: str


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "model": CHAT_MODEL}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.messages:
        raise HTTPException(400, "messages required")

    trimmed = req.messages[-MAX_HISTORY:]
    convo = [{"role": m.role, "content": m.content} for m in trimmed]

    response = state["client"].messages.create(
        model=CHAT_MODEL,
        max_tokens=MAX_TOKENS,
        system=state["system_prompt"],
        messages=convo,
    )
    reply = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    return ChatResponse(reply=reply)
