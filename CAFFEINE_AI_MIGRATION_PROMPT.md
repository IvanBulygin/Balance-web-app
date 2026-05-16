# Balance AI — Complete Migration Prompt for Caffeine AI

## What is this app?

Balance AI is a mobile wellness chatbot that helps users find evidence-based supplement recommendations. It has:

1. **A single-file frontend** (`index.html`, ~2050 lines, ~156KB) rendered inside a 390x844 phone shell
2. **A FastAPI + Python backend** that serves a chat API powered by Claude Sonnet 4.6
3. **A BM25 retrieval system** (no embeddings, no API keys) that searches 19 supplement guide text files
4. **19 supplement guide databases** (~2.4MB of text) covering every major health category
5. **An iHerb affiliate integration** for monetization — buy buttons everywhere

The entire UI is a single HTML file with inline CSS and JavaScript. No React, no build tools, no npm. Just one HTML file that does everything.

---

## ARCHITECTURE

### Backend (Python/FastAPI)

```
agent_site/
├── app.py              # FastAPI server, Claude API integration
├── retrieval.py         # BM25 search engine over text files
├── system_prompt.md     # System prompt for Claude
├── requirements.txt     # Python deps
├── static/
│   └── index.html       # THE ENTIRE FRONTEND (single file)
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
    └── supplement-guide-evidence-database.txt  # 189 supplements with scores
```

### How the backend works

1. On startup: loads all 19 `.txt` files, splits them into ~1200-char chunks with 150-char overlap, builds a BM25 index in memory
2. On each chat request (`POST /api/chat`):
   - Extracts the user's latest question (plus one prior message for context)
   - Runs BM25 search, returns top 15 matching chunks
   - Injects those chunks into Claude's system prompt as "Retrieved passages"
   - Claude answers ONLY from those passages (RAG pattern)
   - Returns the response + list of source guide names

### Key backend code

**app.py:**
```python
from anthropic import Anthropic
from fastapi import FastAPI
from retrieval import BM25Index, build_index, format_context

CHAT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
TOP_K = 15  # retrieved chunks per question

@app.post("/api/chat")
def chat(req: ChatRequest):
    trimmed = req.messages[-20:]  # keep last 20 messages
    query = _build_query(trimmed)
    
    hits = index.search(query, k=TOP_K)
    context_block = format_context(hits)
    sources = sorted({f"supplement-guide-{c.source}" for c, _ in hits})
    
    system_blocks = [
        {"type": "text", "text": system_prompt},
        {"type": "text", "text": f"## Retrieved passages\n\n{context_block}"},
    ]
    
    response = client.messages.create(
        model=CHAT_MODEL, max_tokens=MAX_TOKENS,
        system=system_blocks, messages=convo,
    )
    return {"reply": reply_text, "sources": sources}
```

**retrieval.py:**
```python
from rank_bm25 import BM25Okapi

def _tokenize(text): 
    # regex tokenizer, lowercase, remove stopwords
    
def _split_into_chunks(text, target_chars=1200, overlap=150):
    # paragraph-boundary splitting with overlap

class BM25Index:
    def search(self, query, k=5):
        # returns list of (Chunk, score) tuples

def build_index(pdf_text_dir):
    # reads all .txt files, chunks them, builds BM25 index
```

**requirements.txt:**
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
anthropic==0.42.0
python-dotenv==1.0.1
pydantic==2.9.2
rank_bm25==0.2.2
numpy==1.26.4
```

### Environment variables needed
```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## SYSTEM PROMPT (for Claude)

The system prompt instructs Claude to:

1. Answer ONLY from retrieved passages (strict RAG)
2. Follow an exact response format:
   - 2-3 sentence intro citing the source guide
   - `### Recommended supplements` heading
   - Numbered list with exact format: **Name** `Tier` then Form/Dose/Timing/Evidence fields
   - Tier labels: `Primary`, `Secondary`, `Promising`, `Combo`, `Unproven`
   - Safety blockquote at the end
3. Be exhaustive — include EVERY supplement from the passages
4. Never invent supplements, doses, or brands not in the passages
5. Handle substance recovery questions with SAMHSA disclaimer
6. Decline questions outside wellbeing/supplements

Full system prompt:
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

Every answer about supplements or wellbeing **must** follow this exact structure:

### 1. Short intro (2–3 sentences)
Explain what the evidence says about the user's question. Cite the source
guide inline, e.g. *(supplement-guide-sleep)*. Be direct and friendly.

### 2. Supplement list
After the intro, output this heading exactly:
### Recommended supplements

Then a numbered list. Each supplement follows this **exact** markdown format
(use inline code backticks for the tier label — this matters for styling):

1. **Supplement Name** `Primary`
   - **Form:** specific form (e.g. magnesium glycinate, EPA/DHA, KSM-66)
   - **Dose:** dose from the guide (e.g. 200–400 mg/day)
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
  retrieved passages — do NOT skip any.
- If the passages don't give a specific dose or form, write
  `Check label for dosing` in that field.
- Keep each field to one line.
- Don't use emojis.
- Don't invent supplements, doses, forms, or brands not in the passages.
- When multiple guides are relevant, merge supplements into one unified list.

### 3. Closing callout
End with:
> Always check with your healthcare provider before starting any new
> supplement, especially if you take medication or have a health condition.

## Safety
- You are **not a doctor**. Don't diagnose, prescribe, or replace medical advice.
- If symptoms may be serious, urge urgent medical care.

## Substance recovery & detox questions
When a user asks about detox from drugs, alcohol, narcotics:
1. Lead with SAMHSA disclaimer (1-800-662-4357)
2. Stay in the supplement lane — complementary to medical care only
3. Never provide detox protocols or tapering schedules
```

---

## FRONTEND (index.html) — COMPLETE FEATURE LIST

The frontend is a single HTML file (~2050 lines) that looks and feels like a native iOS app. Here is every feature:

### Design System
- **Phone shell**: 390x844px with 54px border-radius, dynamic island notch
- **Responsive**: On mobile (<430px) goes fullscreen, hides phone shell
- **Fonts**: Inter (body), Fraunces (serif headings), JetBrains Mono (code/tiers)
- **Colors**: Purple brand (#5521E5), pink accent (#E978DA), gradient accents
- **Card system**: `.bal-card` with shadow, `.bal-pill` badges, `.ev-badge` evidence grades

### Screens (all in one HTML file, shown/hidden via JS)
1. **scr-onboard** — Landing page with gradient orb, "Your Wellness Buddy" subtitle, "What your body really needs, no marketing and BS" headline, disclaimer
2. **scr-intake** — Goal selection (step 2 of onboarding), 8 goals: sleep, stress, energy, focus, muscle, heart, immunity, joints. Multi-select with toggle cards
3. **scr-step3** — Education screen (step 3). Shows problems + solutions from guide data for selected goal. "The problem" cards (red accent numbers) and "What you can do" cards (green accent numbers)
4. **scr-today** — Home screen. Shows time-of-day greeting, current supplement stack with timing groups (morning/afternoon/evening), buy buttons per supplement
5. **scr-ask** — AI chat. Welcome state with quick-start pills, full conversation history, markdown rendering with tier-colored badges, streaming text animation (word-by-word), source tags, follow-up suggestions, iHerb buy CTA after each AI response
6. **scr-stack** — My Stack. Shows added supplements with timing, "Buy entire stack on iHerb" button
7. **scr-learn** — Library. Browse all 19 guides with category cards
8. **scr-me** — Profile. Settings, goals, reset options
9. **scr-detail** — Supplement detail page with evidence grade, form, dose, timing, buy button
10. **scr-add** — Add supplement to stack, with iHerb buy button
11. **scr-signin** — Sign in screen (UI only, no auth backend)
12. **scr-profile** — Edit profile
13. **scr-paywall** — Premium subscription pitch
14. **scr-reminders** — Reminder settings
15. **scr-history** — Chat history

### Key Frontend Features

**Streaming text animation:**
```javascript
function streamText(el, raw, cb) {
    var words = raw.split(/(\s+)/);
    var i = 0; var buf = '';
    var wrapper = el.closest('.msg-ai') || el.parentElement;
    wrapper.scrollIntoView({behavior:'smooth', block:'start'});
    function tick() {
        var chunk = Math.min(3, words.length - i);
        for (var j = 0; j < chunk; j++) buf += words[i++];
        el.innerHTML = md(buf);
        if (i < words.length) requestAnimationFrame(tick);
        else { tagTiers(el); if (cb) cb(); }
    }
    requestAnimationFrame(tick);
}
```

**Markdown rendering with tier badges:**
- Parses Claude's markdown response
- Colors tier labels: Primary=brand purple, Secondary=accent pink, Promising=violet, Combo=cyan, Unproven=gray
- Renders evidence badges with letter grades

**iHerb affiliate integration:**
- `iherbUrl(supplementId)` generates iHerb search URLs
- Buy buttons on: Today screen (per supplement), Stack screen (per supplement + "buy all"), Detail screen (large CTA), Add screen, Vitamin chooser, Chat responses (after AI response)
- `buyEntireStack()` opens iHerb for each supplement in stack
- `SUPP_DETECT` array for consistent supplement name detection across all surfaces

**State management (localStorage):**
```javascript
// balance_app_state: {goals:[], stack:[], onboarded:bool, ...}
// balance_conversations: [{id, title, messages:[{role,content}]}]
```

**Vitamin chooser (post-onboarding):**
- Modal overlay showing recommended supplements filtered by user's selected goals
- Each vitamin tagged with `goals:[]` array
- Cards with evidence grade, buy badges
- "Add selected to stack" + "Buy all on iHerb" buttons
- Only shows supplements relevant to the user's chosen goals

**Education screen (step 3) data structure:**
```javascript
var GOAL_EDUCATION = {
    sleep: {
        title: 'Sleep',
        intro: 'Even mild sleep loss impairs focus...',
        problems: [
            {h: 'Impaired focus & skill learning', t: 'Sleep deprivation reduces...'},
            // ... 3 problem cards per goal
        ],
        solutions: [
            {h: 'Schedule enough time', t: 'No supplement will pack 8 hours...'},
            // ... 3 solution cards per goal
        ]
    },
    // stress, energy, focus, muscle, heart, immunity, joints
};
```

All 8 goals have problems and solutions sourced from the actual supplement guide PDFs.

### Navigation
- Tab bar at bottom: Today, Ask, Stack, Learn, Me
- `nav(screenId)` function handles screen transitions with fade
- `goBack()` for back navigation with history stack
- Keyboard dismiss on tap in chat area

---

## SUPPLEMENT GUIDE DATA (19 files)

These are the knowledge base files. Each is a plain text extraction from a PDF guide. They follow a consistent structure:

```
[Guide Title]
Table of Contents
Introduction
Combos (recommended supplement stacks)
Primary Supplements (strongest evidence)
Secondary Supplements (good evidence)  
Promising Supplements (emerging evidence)
Unproven Supplements (weak evidence)
FAQ
```

### Guide list with sizes:
1. `supplement-guide-muscle-gain.txt` — 7,132 lines
2. `supplement-guide-fat-loss.txt` — 5,027 lines
3. `supplement-guide-cardiovascular-health.txt` — 4,989 lines
4. `supplement-guide-skin-hair-nails.txt` — 4,844 lines
5. `supplement-guide-blood-sugar.txt` — 4,755 lines
6. `supplement-guide-healthy-aging.txt` — 4,632 lines
7. `supplement-guide-mood-depression.txt` — 3,772 lines
8. `supplement-guide-allergies-immunity.txt` — 3,606 lines
9. `supplement-guide-vegetarians-vegans.txt` — 3,163 lines
10. `supplement-guide-stress-anxiety.txt` — 3,145 lines
11. `supplement-guide-joint-health.txt` — 2,940 lines
12. `supplement-guide-testosterone.txt` — 2,706 lines
13. `supplement-guide-evidence-database.txt` — 2,322 lines (189 supplements w/ scores)
14. `supplement-guide-bone-health.txt` — 2,298 lines
15. `supplement-guide-memory-focus.txt` — 2,178 lines
16. `supplement-guide-sleep.txt` — 1,951 lines
17. `supplement-guide-liver-health.txt` — 1,316 lines
18. `supplement-guide-libido.txt` — 1,279 lines
19. `supplement-guide-recovery-wellness.txt` — 270 lines

**Total: ~62,000 lines / 2.4 MB of text**

These files need to be uploaded to whatever file storage Caffeine AI supports, and the retrieval system needs to index them.

### Evidence Database (supplement-guide-evidence-database.txt)

This special file contains 189 supplement-condition pairs scored 0-6:
```
Category: Sleep
Supplement: Melatonin
Condition/Benefit: Sleep quality
Evidence Score: 5
Direction: Positive
Summary: Strong evidence from multiple trials...
Sources: Cochrane, PubMed
```

Organized by 19 health categories. Cross-listed entries where supplements appear in multiple categories.

---

## MONETIZATION (iHerb Affiliate)

The app generates revenue through iHerb affiliate links. Buy buttons appear on EVERY surface where supplements are shown:

1. **Today screen** — green "Buy" pill next to each supplement
2. **Stack screen** — "Buy" per item + "Buy entire stack on iHerb" button
3. **Detail screen** — large green CTA with "Shop verified / Buy on iHerb"
4. **Add-to-stack screen** — below the add button
5. **Vitamin chooser modal** — badges per card + "Buy all on iHerb"
6. **Chat responses** — "Shop supplements on iHerb" CTA after AI response with detected supplement names

iHerb URLs are generated via search: `https://www.iherb.com/search?kw={supplement_name}`

---

## ONBOARDING FLOW

1. **Step 1** — Landing page: "Balance AI / Your Wellness Buddy / What your body really needs, no marketing and BS" → "Get started"
2. **Step 2** — Goal selection: Pick 1+ goals from 8 options (sleep, stress, energy, focus, muscle, heart, immunity, joints)
3. **Step 3** — Education: Shows "The problem" (3 cards with issues from guide data) and "What you can do" (3 solution cards) for the user's primary selected goal
4. **Vitamin chooser modal** — Shows recommended supplements filtered by selected goals, user can add to stack and buy on iHerb
5. **Today screen** — User lands on the home screen with their stack

---

## WHAT YOU NEED TO RECREATE

1. **Upload all 19 supplement guide text files** as the knowledge base
2. **Recreate the backend**: RAG pipeline with BM25 (or equivalent) retrieval over the guides, feeding top-15 chunks to Claude with the system prompt
3. **Recreate the frontend**: All screens, the chat with streaming, tier-colored badges, iHerb buy buttons, onboarding flow, education screen with problems/solutions, vitamin chooser with goal filtering
4. **Set up the system prompt** exactly as specified above — the response format matters for frontend parsing
5. **Configure Claude Sonnet 4.6** as the model with 4096 max tokens
6. **Add the ANTHROPIC_API_KEY** environment variable

### Critical details not to miss:
- The streaming text animation (word-by-word with requestAnimationFrame)
- Tier badge coloring (Primary=purple, Secondary=pink, Promising=violet, Combo=cyan)
- iHerb buy buttons on EVERY supplement surface
- The vitamin chooser filtering by selected goals
- The education screen sourcing from actual guide data (problems + solutions, NOT supplement info)
- Keyboard dismiss on chat area tap
- Scroll-to-top when AI response starts streaming
- Conversation persistence in localStorage
- The evidence database (189 supplements with scores) — this powers the vitamin chooser and detail screens
