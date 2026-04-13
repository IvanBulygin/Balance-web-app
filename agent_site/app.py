"""
Balance.ai Project Agent — hosted as a web chatbot.

Serves a chat UI at / that talks to GPT-4o with the Balance.ai Project
Agent system prompt from system_prompt.md. Visitors can ask product
questions (phases, schemas, XP economy, roadmap) and get answers
grounded in the documented project.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
PROMPT_PATH = ROOT / "system_prompt.md"

CHAT_MODEL = "gpt-4o"
MAX_HISTORY = 30  # trailing messages to keep when the client sends more

state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not PROMPT_PATH.exists():
        raise RuntimeError(f"Missing {PROMPT_PATH}")
    state["system_prompt"] = PROMPT_PATH.read_text(encoding="utf-8")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    state["client"] = OpenAI(api_key=api_key)
    print(f"Agent ready. System prompt: {len(state['system_prompt']):,} chars")
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
    convo = [{"role": "system", "content": state["system_prompt"]}]
    convo.extend({"role": m.role, "content": m.content} for m in trimmed)

    completion = state["client"].chat.completions.create(
        model=CHAT_MODEL,
        messages=convo,
        temperature=0.3,
    )
    reply = completion.choices[0].message.content or ""
    return ChatResponse(reply=reply)
