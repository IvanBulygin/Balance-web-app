# Balance.ai — Phase 0 Demo RAG

A standalone, deployable RAG over the 17 supplement guide PDFs in
`../backend/data/pdfs/`. Answers questions via GPT-4o grounded in
retrieved chunks, with inline source citations.

**This is a demo**, not the documented Balance.ai production RAG.
The production system uses Supabase + pgvector (see Phase 1A in the
project docs). This demo uses a pickled numpy index for zero-infra
deployment.

## What's in here

| File | Purpose |
|---|---|
| `app.py` | FastAPI app — serves the chat UI and `/api/ask` endpoint |
| `build_index.py` | Reads `.txt` files, chunks + embeds, writes `index.pkl` |
| `static/index.html` | Single-page chat UI (vanilla JS) |
| `requirements.txt` | Python deps |
| `render.yaml` | Render Blueprint — one-click deploy |
| `railway.json` | Railway config (alternative) |
| `Procfile` | Heroku-style start command (alternative) |

## Deploy to Render (recommended — easiest)

1. Push this repo to GitHub (already done if you're reading this there).
2. Go to <https://dashboard.render.com> → sign up with GitHub.
3. Click **New → Blueprint**.
4. Select this repo. Render auto-detects `rag_demo/render.yaml`.
5. When prompted, paste your **OPENAI_API_KEY** (get one at
   <https://platform.openai.com/api-keys>).
6. Click **Apply**. Render runs `pip install` + `python build_index.py`
   (embeddings cost ≈ $0.05 once) then starts the server.
7. After ~3–5 min the service is live at
   `https://balance-ai-rag-demo.onrender.com` (or a similar URL Render
   assigns). That's your link.

Free tier sleeps after 15 min idle; first request after sleep takes
~30 s to wake. Upgrade to Starter ($7/mo) for always-on.

## Deploy to Railway (alternative)

1. <https://railway.app> → New Project → Deploy from GitHub repo.
2. Set **Root Directory** to `rag_demo`.
3. Add env var `OPENAI_API_KEY`.
4. Railway picks up `railway.json` automatically.
5. Generate a public domain from the service settings.

## Run locally

```bash
cd rag_demo
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env, paste your OPENAI_API_KEY
python build_index.py        # one-time, ~2 min, costs ≈ $0.05
uvicorn app:app --reload
```

Open <http://localhost:8000>.

## How it works

1. `build_index.py` reads every `*.txt` in `../backend/data/pdfs/`.
2. Each file is chunked (1200 chars, 150 overlap, sentence-aware).
3. Every chunk is embedded with `text-embedding-3-small` (1536 dims).
4. The full `(N, 1536)` matrix is L2-normalized and pickled to
   `index.pkl` along with chunk metadata.
5. At query time, `app.py` embeds the question, computes cosine
   similarity via dot product (matrix is pre-normalized), takes top-8.
6. Retrieved chunks are injected as context into a GPT-4o chat
   completion with a citation-enforcing system prompt.
7. The API returns the answer plus deduped source citations.

## Known limitations

- **Copyright**: the PDFs are Examine.com supplement guides. Per
  `CLAUDE.md`, production must not store full text — link out instead.
  This demo is for dev/internal use only.
- **No persistence**: conversations aren't saved. No user accounts.
- **No streaming**: responses come back all at once.
- **No pgvector**: rebuilds `index.pkl` on every deploy. Fine for 17
  docs, won't scale past ~100k chunks.
- **Not the Balance.ai production RAG.** When Phase 1A lands, this
  demo should be deleted and replaced by the `backend/app/services/`
  pipeline hitting Supabase.
