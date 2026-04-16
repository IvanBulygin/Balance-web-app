# Balance.ai Wellbeing Agent — Hosted Website

A deployable web chatbot that answers wellbeing and supplement questions from
17 evidence-based supplement guides. Every user question triggers BM25
retrieval over the guide text; the top passages are injected into the system
prompt so Claude answers only from the retrieved evidence.

Powered by **Anthropic Claude** (`claude-sonnet-4-6`). Requires an Anthropic
API key (get one at <https://console.anthropic.com>). No embedding provider
needed — retrieval is pure-Python BM25.

## What's in here

| File | Purpose |
|---|---|
| `app.py` | FastAPI — serves the chat UI and `/api/chat` endpoint |
| `retrieval.py` | BM25 index build + search over the guide text files |
| `system_prompt.md` | Agent persona, core rule, safety guardrails |
| `data/pdfs/*.txt` | The 17 extracted supplement guides (knowledge base) |
| `static/index.html` | Single-page chat UI with conversation history + source chips |
| `requirements.txt` | Python deps |
| `render.yaml` | Render Blueprint — one-click deploy |
| `railway.json` | Railway alternative |
| `Procfile` | Heroku-style start command |

## How it works

1. **Startup**: `app.py` reads `data/pdfs/*.txt`, chunks each file
   (~1200 chars with 150-char overlap), tokenizes, and builds an in-memory
   BM25 index. Takes a couple seconds for ~2300 chunks.
2. **Per request**: we take the latest user turn (plus the prior one for
   pronoun context) and run BM25 to get the top 6 relevant chunks.
3. The retrieved passages are appended to the system prompt as a second
   system block. Claude is instructed to only use these passages.
4. The reply is returned with a list of source guides, rendered as chips
   below each bot message.

Out-of-scope questions (the retriever returns zero hits, or the passages
don't cover the topic) are politely refused by the agent.

## Deploy to Render

1. <https://dashboard.render.com> → sign up with GitHub.
2. **New → Blueprint**.
3. Select this repo. Render detects `render.yaml` at the repo root.
4. Paste **ANTHROPIC_API_KEY** when prompted.
5. **Apply**. Build + start in ~2 min.
6. Live at `https://balance-ai-project-agent.onrender.com` (or similar).

Free tier sleeps after 15 min idle. Starter ($7/mo) is always-on.

## Deploy to Railway

1. <https://railway.app> → New Project → from GitHub repo.
2. Set **Root Directory** to `agent_site`.
3. Add env var `ANTHROPIC_API_KEY`.
4. Generate a public domain in service settings.

## Run locally

```bash
cd agent_site
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit, paste your ANTHROPIC_API_KEY
uvicorn app:app --reload
```

Open <http://localhost:8000>.

## Updating the knowledge base

To add or update guides:

1. Put the new `.txt` files in `agent_site/data/pdfs/`. The source name
   displayed in chips is derived from the filename
   (`supplement-guide-<topic>.txt` → `supplement-guide-<topic>`).
2. Restart the server. The BM25 index rebuilds on startup.

To change behavior (tone, safety rules, scope), edit `system_prompt.md`.

## Cost & limits

- Per message: ~2–4k input tokens (short system prompt + ~6 retrieved
  chunks) + ≤1k output. At Claude Sonnet 4.6 pricing that's typically
  under a cent per reply.
- No streaming — replies return all at once.
- No persistence — history lives in the browser tab only.
- Conversation capped at last 20 turns sent to the model.
- Retrieval is BM25 (lexical). A keyword match between the question and
  the guides is what drives precision — for very abstract questions,
  results will be weaker than a dense-embedding retriever.
