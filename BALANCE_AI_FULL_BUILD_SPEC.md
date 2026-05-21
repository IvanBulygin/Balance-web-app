# Balance AI — Full Build Spec

## Source Code Repository

Fetch everything from GitHub:
- **Repo:** `https://github.com/IvanBulygin/Balance-web-app`
- **Branch:** `claude/balance-ai-product-agent-zbC53`

### Files to fetch and their purpose

| Path | Purpose |
|------|---------|
| `agent_site/static/index.html` | Complete frontend — single file, ~2050 lines, all 15 screens, CSS, JS |
| `agent_site/app.py` | FastAPI backend — Gemini API integration, RAG pipeline, SSE streaming |
| `agent_site/retrieval.py` | BM25 search engine over supplement guide text files |
| `agent_site/system_prompt.md` | System prompt controlling Gemini response format |
| `agent_site/requirements.txt` | Python dependencies |
| `agent_site/data/pdfs/*.txt` | 19 supplement guide text files — the knowledge base (~2.4MB) |
| `Balance AI/design_handoff_balance_ai/*.html` | Design reference wireframes |

The `index.html` is the design spec. The `.txt` files are the database. The `system_prompt.md` is the AI behavior spec. Replicate them exactly.

---

## What This App Does

Balance AI is a mobile-first wellness chatbot that helps users find evidence-based supplement recommendations. Users ask questions. The app searches 19 supplement guide text files using BM25 retrieval, feeds the top matching passages to Google Gemini 3.5 Flash, and Gemini answers strictly from those passages (RAG pattern). Responses stream in real-time via Server-Sent Events (SSE). Every surface where supplements appear has iHerb affiliate buy buttons.

---

## Architecture

### Backend — Python / FastAPI

```
agent_site/
├── app.py                    # FastAPI server + Gemini API + SSE streaming
├── retrieval.py              # BM25 search engine
├── system_prompt.md          # System prompt for Claude
├── requirements.txt          # Python deps
├── static/
│   └── index.html            # Entire frontend (single file)
└── data/pdfs/
    ├── supplement-guide-sleep.txt
    ├── supplement-guide-stress-anxiety.txt
    ├── supplement-guide-fat-loss.txt
    ├── supplement-guide-memory-focus.txt
    ├── supplement-guide-muscle-gain.txt
    ├── supplement-guide-cardiovascular-health.txt
    ├── supplement-guide-allergies-immunity.txt
    ├── supplement-guide-joint-health.txt
    ├── supplement-guide-blood-sugar.txt
    ├── supplement-guide-bone-health.txt
    ├── supplement-guide-healthy-aging.txt
    ├── supplement-guide-libido.txt
    ├── supplement-guide-liver-health.txt
    ├── supplement-guide-mood-depression.txt
    ├── supplement-guide-recovery-wellness.txt
    ├── supplement-guide-skin-hair-nails.txt
    ├── supplement-guide-testosterone.txt
    ├── supplement-guide-vegetarians-vegans.txt
    └── supplement-guide-evidence-database.txt
```

### Backend flow

1. **Startup:** Load all 19 `.txt` files, split into ~1200-char chunks with 150-char overlap at paragraph boundaries, build BM25 index in memory
2. **Each chat request** (`POST /api/chat/stream` — primary, SSE streaming):
   - Extract user's latest question plus one prior message for context
   - BM25 search returns top 15 matching chunks
   - Inject chunks into Gemini's system instruction as "Retrieved passages"
   - Gemini answers ONLY from those passages
   - Stream response tokens as SSE events: `data: {"text": "chunk"}` for each token batch
   - Final event: `data: {"done": true, "sources": [...]}` with source guide names
3. **Fallback** (`POST /api/chat` — non-streaming):
   - Same RAG pipeline, returns full JSON response `{reply, sources}`
4. `GET /` serves the single-page frontend
5. `GET /api/health` returns status with model name and chunk count

### Backend code — app.py

```python
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
    print(f"Index ready. {len(index.chunks):,} chunks from {len({c.source for c in index.chunks})} guides.")
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
    return {"status": "ok", "model": CHAT_MODEL, "chunks": len(idx.chunks) if idx else 0}

def _build_query(messages: list[Message]) -> str:
    user_turns = [m.content for m in messages if m.role == "user"]
    if not user_turns:
        return ""
    if len(user_turns) >= 2:
        return f"{user_turns[-2]}\n{user_turns[-1]}"
    return user_turns[-1]

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
        "Use only these passages to answer. If they don't cover the question, say so.\n\n"
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

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.messages:
        raise HTTPException(400, "messages required")
    convo, system_instruction, sources = _prepare_chat(req.messages)
    response = state["client"].models.generate_content(
        model=CHAT_MODEL, contents=convo,
        config={"system_instruction": system_instruction, "max_output_tokens": MAX_TOKENS, "temperature": 0.7},
    )
    reply = response.text or ""
    return ChatResponse(reply=reply, sources=sources)

@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    if not req.messages:
        raise HTTPException(400, "messages required")
    convo, system_instruction, sources = _prepare_chat(req.messages)
    def generate():
        stream = state["client"].models.generate_content_stream(
            model=CHAT_MODEL, contents=convo,
            config={"system_instruction": system_instruction, "max_output_tokens": MAX_TOKENS, "temperature": 0.7},
        )
        for chunk in stream:
            text = chunk.text or ""
            if text:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

### Backend code — retrieval.py

```python
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-']*")
_STOPWORDS = frozenset(
    """a an the and or but if then else of in on at to for with by from as is are was were be been being
    this that these those it its it's they them their there here what which who whom whose when where why how
    do does did doing done have has had having i you he she we us our your my me mine yours his hers ours theirs
    about above below between under over into through during before after than so not no yes also just only very much
    can could should would may might will shall must""".split()
)

def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]

@dataclass
class Chunk:
    source: str
    text: str

def _split_into_chunks(text: str, target_chars: int = 1200, overlap: int = 150) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for para in paragraphs:
        if buf_len + len(para) + 2 > target_chars and buf:
            chunks.append("\n\n".join(buf))
            tail = chunks[-1][-overlap:]
            buf = [tail, para] if tail else [para]
            buf_len = sum(len(x) for x in buf) + 2 * (len(buf) - 1)
        else:
            buf.append(para)
            buf_len += len(para) + 2
    if buf:
        chunks.append("\n\n".join(buf))
    return [c for c in chunks if len(c) > 80]

def _source_label(path: Path) -> str:
    name = path.stem
    if name.startswith("supplement-guide-"):
        name = name[len("supplement-guide-"):]
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
    if not hits:
        return "(no relevant passages retrieved)"
    blocks = []
    for i, (chunk, score) in enumerate(hits, 1):
        blocks.append(f"[{i}] source: supplement-guide-{chunk.source} (score {score:.2f})\n{chunk.text}")
    return "\n\n---\n\n".join(blocks)
```

### Dependencies — requirements.txt

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
google-genai==1.14.0
python-dotenv==1.0.1
pydantic==2.9.2
rank_bm25==0.2.2
numpy==1.26.4
```

### Environment variables

```
GOOGLE_API_KEY=AIza...
```

Get a key from [Google AI Studio](https://aistudio.google.com/apikey).

---

## System Prompt

Fetch the full file from `agent_site/system_prompt.md` in the repo. Here is the complete content:

```markdown
# Balance.ai Wellbeing Agent — System Prompt

You are the **Balance.ai Wellbeing Agent**. Your job is to answer questions
about wellbeing, health, and supplements using the supplement-guide passages
retrieved for each question — and to help users know exactly what to buy.

## Core rule

Answer **only** from the retrieved passages shown in the user turn. If the
retrieved passages do not contain the answer, say so plainly — do not guess,
do not draw on outside knowledge, and do not speculate.

The retrieved passages come from 19 evidence-based supplement guides covering:
allergies & immunity, blood sugar, bone health, cardiovascular health,
evidence database (189 supplements with Cochrane/PubMed ratings), fat
loss, healthy aging, joint health, libido, liver health, memory & focus,
mood & depression, muscle gain, recovery & wellness, skin/hair/nails, sleep,
stress & anxiety, testosterone, and vegetarians & vegans.

If a question is outside wellbeing / supplements, politely decline.

## Response structure (required)

Every answer about supplements or wellbeing **must** follow this exact
structure:

### 1. Short intro (2-3 sentences)

Explain what the evidence says about the user's question. Cite the source
guide inline, e.g. *(supplement-guide-sleep)*. Be direct and friendly.

### 2. Supplement list

After the intro, output this heading exactly:

### Recommended supplements

Then a numbered list. Each supplement follows this **exact** markdown format
(use inline code backticks for the tier label — this matters for styling):

1. **Supplement Name** `Primary`
   - **Form:** specific form (e.g. magnesium glycinate, EPA/DHA, KSM-66)
   - **Dose:** dose from the guide (e.g. 200-400 mg/day)
   - **Timing:** when/how to take (e.g. 30 min before bed, with food)
   - **Evidence:** one-line strength summary

**Tier labels** (use the exact word, wrapped in backticks):
- `Primary` — strongest evidence, recommended as first-line
- `Secondary` — good evidence, useful as second-line
- `Promising` — emerging evidence, worth considering
- `Combo` — ingredient in a recommended combo stack
- `Unproven` — only include if specifically asked; weak evidence

**Ordering:** Primary first, then Secondary, then Promising. Within a tier,
put the most impactful supplement first.

**Content rules:**
- **Be exhaustive.** Include **every single supplement** mentioned in the
  retrieved passages — do NOT skip any. The user needs a complete shopping
  list. If the passages mention 12 supplements, list all 12. Omitting
  supplements that appear in the passages is a failure.
- If the passages don't give a specific dose or form, write
  `Check label for dosing` in that field. Don't invent numbers.
- Keep each field to one line.
- Don't use emojis.
- Don't invent supplements, doses, forms, or brands not in the passages.
- When multiple guides are relevant, merge supplements from all of them
  into one unified list (no duplicates). If two guides mention the same
  supplement with different details, combine the information.

### 3. Closing callout

End with a blockquote for the safety note:

> Always check with your healthcare provider before starting any new
> supplement, especially if you take medication or have a health condition.

## Safety

- You are **not a doctor**. Don't diagnose, prescribe, or replace medical
  advice. Recommend a qualified healthcare professional for any personal
  medical decision — especially around medication interactions, pregnancy,
  chronic conditions, or children.
- If symptoms may be serious (chest pain, suicidal ideation, severe allergic
  reaction, etc.), urge urgent medical care.

## Out of scope

- Recommending supplements to treat specific diseases or replace medication.
- Doses for children or pregnant people unless explicitly in the retrieved
  passages.
- Anything not grounded in the retrieved passages.

## Substance recovery & detox questions

When a user asks about detox from drugs, alcohol, narcotics, or substance
withdrawal:

1. **Always lead with a disclaimer:**
   Start your answer with a prominent warning that substance withdrawal can be
   medically dangerous and must be supervised by a healthcare professional.
   Include: "If you or someone you know needs help, contact SAMHSA's National
   Helpline at 1-800-662-4357 (free, confidential, 24/7)."

2. **Stay in the supplement lane:**
   You may recommend supplements from the retrieved passages that support
   general recovery and wellness — sleep, stress, liver health, nutrition —
   but frame them as *complementary to medical care*, never as a replacement.

3. **Never provide:**
   - Specific drug/narcotic detox protocols or tapering schedules
   - Advice on managing withdrawal symptoms without medical supervision
   - Claims that any supplement can treat addiction or replace medical detox
```

---

## Knowledge Base — 19 Supplement Guide Files

Fetch all from `agent_site/data/pdfs/` in the repo. Total: 62,000 lines / 2.4MB.

| # | File | Lines |
|---|------|-------|
| 1 | supplement-guide-muscle-gain.txt | 7,132 |
| 2 | supplement-guide-fat-loss.txt | 5,027 |
| 3 | supplement-guide-cardiovascular-health.txt | 4,989 |
| 4 | supplement-guide-skin-hair-nails.txt | 4,844 |
| 5 | supplement-guide-blood-sugar.txt | 4,755 |
| 6 | supplement-guide-healthy-aging.txt | 4,632 |
| 7 | supplement-guide-mood-depression.txt | 3,772 |
| 8 | supplement-guide-allergies-immunity.txt | 3,606 |
| 9 | supplement-guide-vegetarians-vegans.txt | 3,163 |
| 10 | supplement-guide-stress-anxiety.txt | 3,145 |
| 11 | supplement-guide-joint-health.txt | 2,940 |
| 12 | supplement-guide-testosterone.txt | 2,706 |
| 13 | supplement-guide-evidence-database.txt | 2,322 |
| 14 | supplement-guide-bone-health.txt | 2,298 |
| 15 | supplement-guide-memory-focus.txt | 2,178 |
| 16 | supplement-guide-sleep.txt | 1,951 |
| 17 | supplement-guide-liver-health.txt | 1,316 |
| 18 | supplement-guide-libido.txt | 1,279 |
| 19 | supplement-guide-recovery-wellness.txt | 270 |

Each guide follows: Introduction → Combos → Primary Supplements → Secondary Supplements → Promising Supplements → Unproven Supplements → FAQ.

The evidence database (`supplement-guide-evidence-database.txt`) contains 189 supplement-condition pairs scored 0-6, organized by 19 health categories, sourced from Cochrane/PubMed.

---

## Design System

All inline in `index.html`. Fetch from repo for exact values.

### Colors
```
--brand: #5521E5        (primary purple)
--brand-deep: #20056C   (dark purple for text)
--brand-soft: #ECE5FC   (light purple bg)
--accent: #E978DA       (pink)
--accent-soft: #FDE2F8  (light pink bg)
--green: #7AC97F        (buy buttons, positive)
--green-soft: #D8F1DA   (green bg)
--c-cyan: #56B6C6       (Combo tier)
--c-violet: #8E77E2     (Promising tier)
--c-pink: #F3A9FD       (accent highlights)
--bg: #FFFFFF
--surface: #FFFFFF
--ink: #050304
--ink-3: #7F7F7F
--rule: #E5E5E5
```

### Fonts
```
Body: Inter (400, 500, 600, 700)
Headings: Fraunces (variable, opsz 9-144, weight 400-900, serif)
Code/Tiers: JetBrains Mono (400, 500)
```

### Phone Shell
```
Width: 390px, Height: 844px
Border-radius: 54px
Dynamic island: 120x34px centered notch
Inner border-radius: 46px
On mobile <430px: fullscreen, no shell, no dynamic island
```

### Components
```
.bal-card   — white card, border-radius 26px, box-shadow
.bal-pill   — pill badge (brand/accent/dark/light variants)
.ev-badge   — evidence grade circle 22x22px (A=purple, B=pink, C=light)
.tabbar     — bottom nav, blur backdrop, 5 items
.tab-item   — icon + label, active = brand color
```

### Tier Badge Colors (applied to Gemini response parsing)
```
Primary    → background: var(--brand-soft), color: var(--brand)
Secondary  → background: var(--accent-soft), color: var(--brand)
Promising  → background: rgba(142,119,226,.15), color: #8E77E2
Combo      → background: rgba(86,182,198,.15), color: #56B6C6
Unproven   → background: var(--surface-3), color: var(--ink-3)
```

---

## All 15 Screens

### Screen 1: scr-onboard (Landing Page)
- Purple background (`var(--brand)`)
- Top-left: Balance AI logo (leaf SVG icon + "Balance AI" text)
- Center: 140px gradient orb (radial gradient: pink → purple)
- Below orb: "Your Wellness Buddy" (centered, 14px, light text)
- Headline: "What your body really needs," (white, 28px serif) + line break + "no marketing and BS" (pink #f3a9fd, italic)
- Description: "Ask anything about improving sleep, stress and anxiety, memory and focus, libido, healthy aging and more. We search the evidence and return a ranked stack — with dose, timing, and useful perks."
- Sub-text: "Evaluating supplementation options can be overwhelming. Balance AI is here to help."
- CTA button: "Get started" (pink accent bg, white text, 14px border-radius)
- Below: "I already have an account" link
- Disclaimer: "This guide is for general-health education. It does not constitute medical advice. Please consult a medical or health professional before you begin any exercise-, nutrition-, or supplementation-related program, or if you have questions about your health."

### Screen 2: scr-intake (Goal Selection — Step 2)
- Purple background
- Progress dots: 3 dots, second one active
- "Step 2 of 3" label
- Heading: "What are your goals?"
- Subtext: "Pick all that apply — we'll customize your recommendations."
- 8 toggle cards in a grid (2 columns):
  - Sleep (moon icon), Stress (leaf icon), Energy (sun icon), Focus (brain icon)
  - Muscle (arm icon), Heart (heart icon), Immunity (shield icon), Joints (bone icon)
- Each card: icon + label + description, toggles on tap with visual state change
- `selectedGoals` array tracks selections
- "Continue" button (white bg, dark text)
- "Skip" link

### Screen 3: scr-step3 (Education — Step 3)
- Purple background
- Progress dots: 3 dots, third one active
- "Step 3 of 3" label
- Title: goal name (e.g. "Sleep")
- Intro paragraph from guide data
- **"THE PROBLEM"** section header (uppercase, muted)
  - 3 cards with reddish number badges (rgba(255,100,100,.2) bg, rgba(255,180,180,.9) text)
  - Each card: number + bold heading + description paragraph
- **"WHAT YOU CAN DO"** section header (uppercase, muted)
  - 3 cards with green number badges (rgba(100,220,100,.2) bg, rgba(180,255,180,.9) text)
  - Each card: number + bold heading + description paragraph
- "Build my supplement stack" CTA button
- "Skip" link

Education data for all 8 goals (from the GOAL_EDUCATION object in index.html):

**Sleep:**
- Intro: "Even mild sleep loss impairs focus, skill acquisition, and glucose metabolism. It increases inflammation, raises cardiovascular risk, and hinders muscle gain. As you sleep less you eat more — partial sleep deprivation can cause a 20% increase in voluntary energy intake."
- Problems: Impaired focus & skill learning | Increased inflammation & fat gain | Impaired cardiovascular & metabolic health
- Solutions: Schedule enough time | Consistent bedtime | Avoid blue light before bed

**Stress & Anxiety:**
- Intro: "Up to a third of the world experiences significant stress or anxiety. Chronic stress triggers the fight-or-flight response, which if prolonged can lead to general adaptation syndrome — bodily damage from sustained cortisol elevation, impaired sleep, and metabolic disruption."
- Problems: Fight-or-flight overload | Anxiety vs. stress confusion | The vicious cycle
- Solutions: Therapy & CBT | Exercise | Meditation & breathing

**Energy & Fat Loss:**
- Intro: "Everyone wants a quick fix for fat loss, but most supplements marketed for this are backed by extremely poor studies. The real formula is simple: take in less energy than you expend. Exercise helps, but not as much as diet. Supplements are secondary to fundamentals."
- Problems: Calorie balance is king | Body composition confusion | Insecurity & poor body image
- Solutions: Protein is the foundation | Address sleep & stress first | Sustainable deficit

**Memory & Focus:**
- Intro: "Some mornings we feel sharp and capable; other days feel slow and foggy. Sleep deprivation, aging, and nutritional deficiencies all impair cognitive function. The brain uses 15% of blood flow each heartbeat and demands constant fuel, oxygen, and micronutrients."
- Problems: Sleep deprivation | Age-related cognitive decline | Nutritional deficiencies
- Solutions: Adequate energy supply | Blood flow & exercise | Neurotransmitter support

**Muscle & Performance:**
- Intro: "To build muscle, exercise is a necessity — unlike fat loss, where diet alone can work. Any supplement that helps you train harder can help build stronger muscles, and stronger muscles let you train harder, creating a positive feedback loop. But genetics, fiber type, and training style all matter."
- Problems: Genetics & individual variation | Recovery limitations | Nutrition misconceptions
- Solutions: Protein throughout the day | Train for your goal | Sleep & recovery first

**Cardiovascular Health:**
- Intro: "For decades the advice was simple: avoid cholesterol and saturated fat. But recent evidence shows the picture is far more nuanced. The diet-heart hypothesis has been challenged, and cardiovascular health depends on the whole dietary pattern, not single nutrients."
- Problems: The cholesterol confusion | Standard tests fall short | Inflammation is key
- Solutions: Diet quality over single nutrients | Exercise & lifestyle | Know your real numbers

**Immunity & Allergies:**
- Intro: "In good health, we barely notice our immune system. But it is constantly fighting an invisible horde that evolves faster than we can. The system has two arms: innate (first responders) and adaptive (targeted, memory-based) — and their coordination determines how well you fight infections."
- Problems: Innate vs. adaptive imbalance | Immune boosters are a myth | Vitamin D deficiency is widespread
- Solutions: Sleep is #1 | Maintain vitamin D levels | Act fast at cold onset

**Joint Health:**
- Intro: "Joint health is highly complex — there is no simple formula like 'eat less, move more.' Joints can be damaged by forcing past their range of motion, repetitive stress, aging, disease, or genetics. The multiplicity of causes makes addressing joint pain uniquely difficult."
- Problems: No single cause | Misdiagnosis is common | Sleep & pain cycle
- Solutions: Get a proper diagnosis | Address inflammation first | Collagen & structural support

### Screen 4: scr-today (Home)
- White background
- Top: time-of-day greeting ("Good morning" / "Good afternoon" / "Good evening") + date
- Supplement stack grouped by timing:
  - Morning supplements (sun icon)
  - Afternoon supplements
  - Evening supplements (moon icon)
- Each supplement row: name, dose, form, green "Buy" pill linking to iHerb
- If stack is empty: prompt to use the Ask screen or add supplements
- Tab bar at bottom

### Screen 5: scr-ask (AI Chat)
- White background
- Top header: "Ask" + guide count badge ("searched 19 guides")
- **Welcome state** (before first message):
  - Centered icon (sparkle SVG)
  - "What do you need supplements for?" heading
  - "I search 19 evidence-based guides..." description
  - Quick-start suggestion pills:
    - "Best for sleep?"
    - "Afternoon energy"
    - "Stress relief"
    - "Muscle recovery"
    - "Recovery & detox"
  - Each pill triggers `sendMessage()` with a pre-written question
- **Chat state:**
  - User messages: right-aligned, purple background
  - AI messages: left-aligned, white card with shadow
  - **Real-time SSE streaming:** tokens appear instantly as Gemini generates them via `fetch()` + `ReadableStream` reader consuming `text/event-stream` from `/api/chat/stream`
  - Markdown rendered progressively via marked.js + DOMPurify as chunks arrive
  - Tier labels (`Primary`, `Secondary`, etc.) parsed and colored as pill badges after stream completes
  - After each AI response:
    - Source tags (which guides were searched)
    - Follow-up suggestion pills
    - "Shop supplements on iHerb" CTA with detected supplement names
- Composer: text input + send button (purple circle with arrow icon)
- Tapping the message area dismisses the keyboard (blur input)
- Scroll behavior: auto-scrolls to END of AI message as tokens stream in

### Screen 6: scr-stack (My Stack)
- List of user's added supplements
- Each row: name, dose, timing, "Buy" pill
- "Buy entire stack on iHerb" button at bottom (opens iHerb for each item)
- Empty state if no supplements added

### Screen 7: scr-learn (Library)
- Browse all 19 guides as category cards
- Each card: category name, brief description, tap to explore

### Screen 8: scr-me (Profile/Settings)
- User's selected goals
- Reset options
- App info

### Screen 9: scr-detail (Supplement Detail)
- Evidence grade badge (A/B/C)
- Supplement name (large serif heading)
- Form, dose, timing, evidence fields
- "Add to my stack" / "Remove from stack" toggle button
- Large green "Buy on iHerb" CTA:
  - "Shop verified" sub-label
  - "Buy on iHerb" main label
  - Arrow icon

### Screen 10: scr-add (Add to Stack)
- Supplement info display
- "Add to my stack" button
- iHerb buy button below

### Screens 11-15: Secondary (placeholder UI is fine)
- **scr-signin** — Email + password fields, Apple/Google social buttons (visual only)
- **scr-profile** — Edit profile form
- **scr-paywall** — Premium subscription pitch
- **scr-reminders** — Reminder time settings
- **scr-history** — List of past conversations

### Vitamin Chooser Modal (post-onboarding)
- Bottom-sheet overlay (opens after education step 3)
- Title: "Your recommended stack"
- Shows supplements FILTERED by user's selected goals
- Each vitamin has a `goals:[]` array — only matching ones are shown
- Card per supplement: name, evidence grade, "Buy" badge
- Checkboxes to select which to add
- "Add selected to stack" button
- "Buy all on iHerb" button
- `buySelectedVitamins()` opens iHerb for each selected supplement

---

## Monetization — iHerb Buy Buttons

Buy buttons appear on EVERY surface where supplements are shown:

| Surface | Button Type |
|---------|-------------|
| Today screen | Green "Buy" pill per supplement row |
| Stack screen | "Buy" per item + "Buy entire stack on iHerb" button |
| Detail screen | Large green CTA: "Shop verified / Buy on iHerb" |
| Add-to-stack screen | Below the add button |
| Vitamin chooser modal | Badge per card + "Buy all on iHerb" |
| Chat responses | "Shop supplements on iHerb" CTA after AI response |

Link format (no affiliate ID yet):
```
https://www.iherb.com/search?kw={supplement_name}
```

Key functions:
- `iherbUrl(id)` — generates iHerb search URL for a supplement
- `buyEntireStack()` — opens iHerb for each supplement in the user's stack
- `buySelectedVitamins()` — opens iHerb for selected supplements in vitamin chooser
- `SUPP_DETECT` — array of supplement names used for consistent detection in AI responses

---

## State Management

All client-side, localStorage only. No auth, no database, no user accounts.

```javascript
// User state — persisted in localStorage as 'balance_app_state'
{
    goals: ['sleep', 'stress'],      // selected during onboarding step 2
    stack: [{id, name, dose, timing, form, ...}],  // user's supplement stack
    onboarded: true                   // completed onboarding flow
}

// Chat history — persisted in localStorage as 'balance_conversations'
[
    {
        id: 'conv_1234567890',
        title: 'Sleep supplements',
        messages: [
            {role: 'user', content: 'What helps me fall asleep faster?'},
            {role: 'assistant', content: '### Recommended supplements\n\n1. **Melatonin** `Primary`...'}
        ]
    }
]
```

---

## Navigation

- Tab bar at bottom with 5 items: Today, Ask, Stack, Learn, Me
- `nav(screenId)` function handles screen transitions with opacity fade
- `goBack()` for back navigation with history stack
- Screens shown/hidden via `.active` class (display:flex + opacity:1)
- All screens are absolutely positioned (`position:absolute; inset:0`)

---

## Key Frontend Functions

| Function | Purpose |
|----------|---------|
| `nav(id)` | Navigate to screen, manage history |
| `goBack()` | Back navigation |
| `sendMessage(text)` | Send user message, stream SSE from `/api/chat/stream`, render tokens in real-time |
| `md(text)` | Markdown to HTML via marked.js + DOMPurify |
| `tagTiers(el)` | Parse and color-code tier labels in AI response |
| `showVitaminChooser()` | Open filtered vitamin chooser modal |
| `showGoalEducation()` | Render education step 3 with problems/solutions |
| `finishEducation()` | Complete onboarding, go to today, show vitamin chooser |
| `iherbUrl(id)` | Generate iHerb search URL |
| `buyEntireStack()` | Open iHerb for all stack supplements |
| `openModal(html)` / `closeModal()` | Bottom-sheet modal system |
| `renderToday()` | Render home screen with stack grouped by timing |
| `renderStack()` | Render my stack screen |
| `renderLearn()` | Render library with guide cards |
| `saveState()` / `loadState()` | localStorage persistence |

---

## Critical Implementation Details

1. **Real-time SSE streaming is required** — AI responses stream token-by-token via Server-Sent Events from `/api/chat/stream`. The backend uses Gemini's `generate_content_stream()` and yields `data: {"text": "..."}` events. The frontend reads chunks via `fetch()` + `response.body.getReader()` and renders markdown progressively. Responses must NOT wait for full completion before displaying.
2. **RAG pipeline is mandatory** — Gemini must answer only from retrieved guide passages. Without retrieval, it is just a generic chatbot and loses all value.
3. **Tier badge parsing** — Frontend scans backtick-wrapped tier labels in AI response and replaces them with colored pill badges. System prompt format and frontend parser must match exactly.
4. **BM25 chunking params** — 1200 char target, 150 char overlap, paragraph boundary splitting, top 15 results per query.
5. **Keyboard dismiss** — Tapping chat message area calls `document.getElementById('ask-input').blur()`.
6. **Scroll during streaming** — As tokens arrive, auto-scroll to the END of the AI message bubble so the user sees the latest content.
7. **Education screen shows problems + solutions, NOT supplements** — This is a deliberate design decision. Step 3 educates about the health topic before recommending products.
8. **Vitamin chooser filters by goals** — Each vitamin has a `goals:[]` array. Only supplements matching the user's selected goals appear.
9. **19 guides** — This number appears in the welcome screen, chat header, and learn screen. Keep it consistent.
10. **No emojis** — The system prompt and UI do not use emojis. Keep it clean.
11. **Gemini message format** — Gemini uses `"model"` role instead of `"assistant"`, and messages use `{"role": "model", "parts": [{"text": "..."}]}` format. The system prompt is passed as a single `system_instruction` string (not array blocks).
12. **Exhaustive supplement listing** — A "Reminder" section is appended to the system instruction forcing Gemini to list ALL supplements from the retrieved passages, not just the top 1-2. MAX_TOKENS is set to 8192 to accommodate long lists.

---

## Onboarding Flow (4 steps)

```
Step 1: Landing page → tap "Get started"
Step 2: Goal picker → select 1+ of 8 goals → tap "Continue"
Step 3: Education → read problems & solutions → tap "Build my supplement stack"
Step 4: Vitamin chooser modal → select supplements → add to stack / buy on iHerb
        → Land on Today screen (home)
```

---

## How to Build This

1. **Fetch the repo** — Clone `https://github.com/IvanBulygin/Balance-web-app` branch `claude/balance-ai-product-agent-zbC53`
2. **Set up the backend** — `app.py` + `retrieval.py` + all 19 `.txt` files in `data/pdfs/`
3. **Set up the frontend** — `index.html` is the complete reference. Replicate pixel-for-pixel.
4. **Configure the system prompt** — `system_prompt.md` controls AI behavior and response format
5. **Set GOOGLE_API_KEY** — Required for Gemini API calls. Get from [Google AI Studio](https://aistudio.google.com/apikey)
6. **Run:** `uvicorn app:app --host 0.0.0.0 --port 8000`

The `index.html` IS the design spec. The `.txt` files ARE the database. The `system_prompt.md` IS the AI behavior spec. Everything needed is in the repo.

### Deployment — Render

The app deploys to Render. Config in `render.yaml`:

```yaml
services:
  - type: web
    name: balance-ai-project-agent
    runtime: python
    rootDir: agent_site
    plan: starter
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app:app --host 0.0.0.0 --port $PORT
    autoDeploy: true
    envVars:
      - key: GOOGLE_API_KEY
        sync: false
      - key: PYTHON_VERSION
        value: "3.11"
```

Set `GOOGLE_API_KEY` in Render's environment variables dashboard (not committed to git).
