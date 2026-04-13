# Balance.ai Project Agent — Hosted Website

A deployable web chatbot that hosts the **Balance.ai Project Agent**. Visitors
ask product questions (phases, database schema, XP economy, roadmap, cost
estimates) and get answers grounded in the project documentation — with the
same Core Rule behavior as the agent in Claude.ai.

## What's in here

| File | Purpose |
|---|---|
| `app.py` | FastAPI — serves the chat UI and `/api/chat` endpoint |
| `system_prompt.md` | Section A + Section B combined — the agent's entire knowledge base |
| `static/index.html` | Single-page chat UI with conversation history |
| `requirements.txt` | Python deps |
| `render.yaml` | Render Blueprint — one-click deploy |
| `railway.json` | Railway alternative |
| `Procfile` | Heroku-style start command |

## How it differs from `rag_demo/`

- **`agent_site/` (this)** = product-level Q&A from documentation. No PDFs, no
  vector search. Just the agent persona + system prompt.
- **`rag_demo/`** = content Q&A over the 17 supplement guide PDFs. Uses
  embeddings + retrieval.

They're independent services. Deploy either, both, or neither.

## Deploy to Render

1. <https://dashboard.render.com> → sign up with GitHub.
2. **New → Blueprint**.
3. Select this repo. Render detects `agent_site/render.yaml`.
4. Paste **OPENAI_API_KEY** when prompted.
5. **Apply**. Build + start in ~2 min.
6. Live at `https://balance-ai-project-agent.onrender.com` (or similar).

Free tier sleeps after 15 min idle. Starter ($7/mo) is always-on.

## Deploy to Railway

1. <https://railway.app> → New Project → from GitHub repo.
2. Set **Root Directory** to `agent_site`.
3. Add env var `OPENAI_API_KEY`.
4. Generate a public domain in service settings.

## Run locally

```bash
cd agent_site
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit, paste your OPENAI_API_KEY
uvicorn app:app --reload
```

Open <http://localhost:8000>.

## Updating the agent's knowledge

Edit `system_prompt.md`. Restart the server (or redeploy). Every request
reads the prompt from memory at startup.

## Cost & limits

- Each message: ≈ 3–6k input tokens (the full system prompt) + ≤1k output.
  At GPT-4o pricing that's ≈ $0.02–0.03 per reply.
- No streaming — replies return all at once.
- No persistence — history lives in the browser tab only.
- Conversation capped at last 30 turns sent to the model.
