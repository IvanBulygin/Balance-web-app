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
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from categories import CategoryCache, CategoryResponse, DISPLAY_TITLES, available_slugs
from gemini_client import get_client
from retrieval import BM25Index, BOOST_MIN_SCORE, build_index, format_context

import httpx
from cartai import CheckoutRequest, create_checkout, get_checkout, is_enabled as cartai_enabled

load_dotenv()

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
PROMPT_PATH = ROOT / "system_prompt.md"
PDF_TEXT_DIR = ROOT / "data" / "pdfs"
MUSHROOMS_PATH = ROOT / "data" / "functional_mushrooms.json"
INTERACTIONS_PATH = ROOT / "data" / "interactions.json"
DRUG_EFFECTS_PATH = ROOT / "data" / "drug_effects.json"

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
    state["category_cache"] = CategoryCache(cache_dir=ROOT / "data" / "categories")
    try:
        state["mushrooms"] = json.loads(MUSHROOMS_PATH.read_text(encoding="utf-8"))
        print(f"Loaded functional-mushroom DB: {len(state['mushrooms'].get('mushrooms', []))} entries.")
    except FileNotFoundError:
        state["mushrooms"] = {"mushrooms": []}
        print("No functional-mushroom DB found.")
    try:
        state["interactions"] = json.loads(INTERACTIONS_PATH.read_text(encoding="utf-8"))
        print(f"Loaded interaction DB: {len(state['interactions'].get('rules', []))} rules.")
    except FileNotFoundError:
        state["interactions"] = {"rules": []}
        print("No interaction DB found.")
    try:
        state["drug_effects"] = json.loads(DRUG_EFFECTS_PATH.read_text(encoding="utf-8"))
        print(f"Loaded substance-effects DB: {len(state['drug_effects'].get('substances', []))} entries.")
    except FileNotFoundError:
        state["drug_effects"] = {"substances": []}
        print("No substance-effects DB found.")
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
    # The classic standalone chat UI is retired — its design is superseded by
    # the in-app Ask screen. Redirect old links to the current app.
    return RedirectResponse("/", status_code=307)


@app.get("/api/health")
def health():
    idx: BM25Index | None = state.get("index")
    return {
        "status": "ok",
        "model": CHAT_MODEL,
        "models": CHAT_MODELS,
        "chunks": len(idx.chunks) if idx else 0,
    }


@app.get("/api/mushrooms")
def mushrooms():
    """Functional-mushroom evidence DB — powers the in-chat curated card (b)."""
    return state.get("mushrooms", {"mushrooms": []})


@app.get("/api/interactions")
def interactions():
    """Curated dangerous-combination rules — powers the in-chat warning card."""
    return state.get("interactions", {"rules": []})


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


@app.get("/api/checkout/config")
def checkout_config():
    """UI probe: should the 'Buy my stack' button be visible?"""
    return {"enabled": cartai_enabled(), "mode": "test"}


def _cartai_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            detail = exc.response.json()
        except Exception:
            detail = exc.response.text or str(exc)
        return HTTPException(exc.response.status_code, detail)
    if isinstance(exc, httpx.HTTPError):
        return HTTPException(502, f"CartAI request failed: {exc}")
    return HTTPException(500, str(exc))


@app.post("/api/checkout")
def checkout_create(req: CheckoutRequest):
    try:
        return create_checkout(req)
    except RuntimeError as e:
        # CARTAI_API_KEY not configured.
        raise HTTPException(503, str(e))
    except Exception as e:  # noqa: BLE001
        print(f"[cartai] create_checkout failed: {e}")
        raise _cartai_http_error(e)


@app.get("/api/checkout/{task_id}")
def checkout_status(task_id: str):
    try:
        return get_checkout(task_id)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:  # noqa: BLE001
        print(f"[cartai] get_checkout failed: {e}")
        raise _cartai_http_error(e)


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


# Extra aliases so mushroom mentions are caught regardless of naming.
_MUSHROOM_ALIASES = {
    "Cordyceps": ["cordyceps"],
    "Lion's Mane": ["lion's mane", "lions mane", "lion’s mane", "hericium"],
    "Reishi": ["reishi", "ganoderma", "lingzhi"],
}


def _aliases_for(m: dict) -> set[str]:
    al = {m["name"].lower()}
    for tok in re.split(r"[\s/(),]+", (m.get("latin") or "").lower()):
        if len(tok) > 4:
            al.add(tok)
    al.update(a.lower() for a in _MUSHROOM_ALIASES.get(m["name"], []))
    return {a for a in al if a}


def find_mushrooms(text: str) -> list[dict]:
    t = (text or "").lower()
    return [m for m in state.get("mushrooms", {}).get("mushrooms", []) if any(a in t for a in _aliases_for(m))]


def format_mushroom_block(hits: list[dict]) -> str:
    lines: list[str] = []
    for m in hits:
        lines.append(f"### {m['name']} ({m['latin']})")
        for b in m.get("benefits", []):
            src = "; ".join(f"{s['type']}: {s['url']}" for s in b.get("sources", []))
            lines.append(
                f"- [{b['evidence_tier']}] {b['benefit']} — {b['summary']} "
                f"Caveats: {b.get('caveats', 'n/a')}. Sources: {src}"
            )
    return "\n".join(lines)


def _wb(alias: str, t: str) -> bool:
    # Word-boundary match so short aliases ("ket", "oxy", "meth") don't fire
    # inside unrelated words ("jacket", "oxygen", "method").
    return re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", t) is not None


def _lev(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 2:
        return 99
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _fuzzy_hit(alias: str, tokens: list[str]) -> bool:
    # Typo tolerance for single-word aliases ≥6 chars ("alchohol"→"alcohol").
    if " " in alias or len(alias) < 6:
        return False
    tol = 2 if len(alias) >= 10 else 1
    return any(abs(len(tok) - len(alias)) <= 2 and _lev(tok, alias) <= tol for tok in tokens)


def _alias_present(alias: str, t: str, tokens: list[str]) -> bool:
    return _wb(alias, t) or _fuzzy_hit(alias, tokens)


def find_interactions(text: str) -> list[dict]:
    """Curated dangerous-combination rules that match the text (both sides present)."""
    t = (text or "").lower()
    tokens = [w for w in re.split(r"[^\w']+", t) if w]  # \w is Unicode-aware (Cyrillic)
    out = []
    for r in state.get("interactions", {}).get("rules", []):
        if any(_alias_present(a, t, tokens) for a in r.get("a", [])) and any(
            _alias_present(b, t, tokens) for b in r.get("b", [])
        ):
            out.append(r)
    order = {"Dangerous": 0, "Serious": 1, "Caution": 2}
    return sorted(out, key=lambda r: order.get(r.get("severity"), 9))


def format_interaction_block(hits: list[dict]) -> str:
    return "\n".join(f"- [{r['severity']}] {r['label']}: {r['reason']}" for r in hits)


# ---- Medication lookup: RxNav (typo-correct) → openFDA (official label) ----
_MED_INTENT = re.compile(
    r"side[\s-]?effect|adverse|medication|prescription|\bdrug\b|dosage|\bdose[sd]?\b"
    r"|contraindicat|interaction|\bpill\b|tablet|what (is|are)|tell me about"
    r"|is .{2,25} (safe|bad|dangerous|harmful|addictive)|what does .{2,25} do"
    r"|effects? of|harms?|risks?|danger|withdrawal|overdose|long[\s-]?term"
    r"|how to (reduce|lower|avoid|minimi[sz]e|prevent|ease)|reduce .{0,20}(effect|harm|risk|damage)"
    r"|comedown|come down|hangover|safer|harm reduction|recover from"
    # Russian phrasings — users ask in Russian too.
    r"|побочк|побочн|как снизить|как уменьшить|снизить вред|вред|риск|опасн"
    r"|передозировк|ломк|отмен|похмель|отходняк|что будет|чем опасен|последстви",
    re.I,
)
_DRUG_STOP = {
    "what", "whats", "are", "is", "the", "side", "sideeffect", "sideeffects", "effect",
    "effects", "adverse", "reaction", "reactions", "of", "for", "with", "and", "can",
    "take", "taking", "my", "does", "dosage", "dose", "doses", "medication", "medications",
    "med", "meds", "drug", "drugs", "prescription", "pill", "pills", "tablet", "safe",
    "about", "tell", "use", "used", "using", "should", "this", "that", "between", "combine",
    "mix", "have", "from", "your", "you", "any", "info", "information", "please",
}
_drug_cache: dict[str, Any] = {}


def _drug_candidates(text: str) -> list[str]:
    toks = re.findall(r"[a-zA-Z][a-zA-Z\-']{3,}", (text or "").lower())
    seen, out = set(), []
    for t in toks:
        if t not in _DRUG_STOP and t not in seen:
            seen.add(t)
            out.append(t)
    return out[:4]


def _resolve_drug(term: str) -> Optional[str]:
    try:
        r = httpx.get(
            "https://rxnav.nlm.nih.gov/REST/approximateTerm.json",
            params={"term": term, "maxEntries": 1}, timeout=8,
        )
        for c in r.json().get("approximateGroup", {}).get("candidate", []):
            if c.get("name"):
                return c["name"]
    except Exception as exc:  # noqa: BLE001
        print(f"[drug] RxNav '{term}' failed: {exc}")
    return None


def _fetch_drug_label(name: str) -> Optional[dict]:
    def _first(d: dict, k: str) -> str:
        v = d.get(k)
        return v[0] if isinstance(v, list) and v else (v if isinstance(v, str) else "")
    def _score(res: dict) -> tuple:
        """Prefer a label for the single drug asked about, that actually has content."""
        gen = " ".join(res.get("openfda", {}).get("generic_name", [])).lower()
        # Combination products list several ingredients — penalise them so
        # "metformin" doesn't resolve to "Sitagliptin and Metformin".
        exact = gen.strip() == name.lower()
        combo = (" and " in gen) or ("," in gen)
        has_ae = bool(_first(res, "adverse_reactions"))
        return (exact, has_ae, not combo)

    try:
        candidates: list[dict] = []
        for field in ("openfda.generic_name", "openfda.brand_name"):
            r = httpx.get(
                "https://api.fda.gov/drug/label.json",
                params={"search": f'{field}:"{name}"', "limit": 10}, timeout=10,
            )
            if r.status_code == 200:
                candidates.extend(r.json().get("results", []))
            if candidates:
                break
        if not candidates:
            return None
        # Best = exact single-ingredient match with adverse-reaction text.
        res = max(candidates, key=_score)
        of = res.get("openfda", {})
        return {
            "name": (of.get("generic_name") or [name])[0].title(),
            "brand": (of.get("brand_name") or [""])[0],
            "indications": _first(res, "indications_and_usage")[:1000],
            "side_effects": _first(res, "adverse_reactions")[:2000],
            "warnings": (_first(res, "warnings_and_cautions") or _first(res, "warnings")
                         or _first(res, "boxed_warning"))[:1500],
            "interactions": _first(res, "drug_interactions")[:1500],
            "dosage": _first(res, "dosage_and_administration")[:800],
        }
    except Exception as exc:  # noqa: BLE001
        print(f"[drug] openFDA '{name}' failed: {exc}")
    return None


def lookup_drug(text: str) -> Optional[dict]:
    """Resolve a (possibly misspelled) drug in the text to its official FDA label."""
    key = (text or "").lower().strip()
    if key in _drug_cache:
        return _drug_cache[key]
    result = None
    for cand in _drug_candidates(text):
        name = _resolve_drug(cand)
        if name:
            label = _fetch_drug_label(name)
            if label:
                result = label
                break
    _drug_cache[key] = result
    return result


def find_substance_effects(text: str, limit: int = 3) -> list[dict]:
    """Curated effects entries for every recreational substance mentioned.

    Returns all matches (capped) so a question like "weed and cocaine" gets
    both, rather than silently answering only the first.
    """
    t = (text or "").lower()
    tokens = [w for w in re.split(r"[^\w']+", t) if w]  # \w is Unicode-aware (Cyrillic)
    out = []
    for s in state.get("drug_effects", {}).get("substances", []):
        if any(_alias_present(a, t, tokens) for a in s.get("aliases", [])):
            out.append(s)
            if len(out) >= limit:
                break
    return out


def format_substance_block(s: dict) -> str:
    parts = [f"### {s['name']}"]
    for label, key in (("Short-term effects", "short_term"), ("Longer-term effects", "longer_term"),
                       ("Key risks", "key_risks"),
                       ("How to reduce harm / side effects", "harm_reduction"),
                       ("Notes", "notes")):
        if s.get(key):
            parts.append(f"**{label}:** {s[key]}")
    if s.get("supplements"):
        parts.append(
            "**Nutritional support (curated list — mention these when asked how to "
            "reduce side effects):** " + ", ".join(s["supplements"])
        )
    return "\n\n".join(parts)


def format_drug_block(d: dict) -> str:
    parts = [f"### {d['name']}" + (f" (brand: {d['brand']})" if d.get("brand") else "")]
    for label, key in (("Indications", "indications"), ("Side effects / adverse reactions", "side_effects"),
                       ("Warnings", "warnings"), ("Drug interactions", "interactions"),
                       ("Dosage (reference only)", "dosage")):
        if d.get(key):
            parts.append(f"**{label}:** {d[key]}")
    return "\n\n".join(parts)


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

    # (a) Inject the curated functional-mushroom evidence DB when relevant. The
    # guides don't cover these, so this is the authoritative source for them.
    recent_user = "\n".join(m.content for m in trimmed if m.role == "user")
    mush = find_mushrooms(query or recent_user)
    if mush:
        system_instruction += (
            "\n\n## Functional-mushroom evidence database (AUTHORITATIVE — use "
            "this, not the guide passages, for these mushrooms)\n\n"
            + format_mushroom_block(mush)
            + "\n\nWhen answering about these mushrooms: use ONLY this database, "
            "state each benefit's evidence tier, include the caveats, never "
            "overstate or invent benefits/doses, and note this isn't medical "
            "advice. " + (state.get("mushrooms", {}).get("agent_guidance", ""))
        )

    # Medication questions: pull the official FDA label (via openFDA, with RxNav
    # typo-correction) so the agent can answer instead of refusing.
    if _MED_INTENT.search(recent_user):
        # Recreational substances have no FDA label — use the curated
        # harm-reduction entry, and check it first so "weed"/"alcohol" aren't
        # mis-resolved to an unrelated pharmaceutical by the fuzzy drug lookup.
        substances = find_substance_effects(recent_user)
        drug = None if substances else lookup_drug(recent_user)
        if substances:
            sdb = state.get("drug_effects", {})
            system_instruction += (
                "\n\n## Substance effects (AUTHORITATIVE — curated harm-reduction data)\n\n"
                + "\n\n".join(format_substance_block(s) for s in substances)
                + f"\n\nThe user asked about {len(substances)} substance(s); an entry is "
                "provided for EACH — cover every one of them, and answer using ONLY the "
                "data above (ignore the supplement response format for this). "
                + sdb.get("agent_guidance", "") + " " + sdb.get("supplements_note", "")
                + " " + sdb.get("disclaimer", "")
            )
            # The answer came from this database, not the supplement guides —
            # don't mislabel it with unrelated guide citations.
            sources = ["harm-reduction reference"]
        elif drug:
            system_instruction += (
                "\n\n## FDA drug label (AUTHORITATIVE — official openFDA data)\n\n"
                + format_drug_block(drug)
                + "\n\nThe user is asking about this MEDICATION. You MAY answer using "
                "ONLY the FDA label data above (ignore the supplement response format "
                "for this). Summarise in plain, calm language, focusing on what they "
                "asked (e.g. common side effects). Then always add that this is general "
                "information from the official FDA label — not medical advice — and that "
                "they should check with their doctor or pharmacist. Do not recommend "
                "changing any medication. If the label doesn't cover their question, say so."
            )
            sources = [f"FDA label: {drug['name']}"]

    # Dangerous-combination warnings (curated). Inject whenever the message
    # matches a known interaction so the agent warns from vetted data, not guesses.
    inter = find_interactions(recent_user)
    if inter:
        idb = state.get("interactions", {})
        system_instruction += (
            "\n\n## Dangerous-combination warnings (AUTHORITATIVE — curated)\n\n"
            + format_interaction_block(inter)
            + "\n\n" + idb.get("agent_guidance", "")
            + " " + idb.get("emergency", "") + " " + idb.get("not_exhaustive", "")
        )
    if stack:
        names = ", ".join(s.strip() for s in stack if s.strip())
        if names:
            system_instruction += (
                "\n\n## User's current stack\n\n"
                f"The user already takes: {names}.\n\n"
                "Take this into account in EVERY answer, not only when they ask "
                "about combining:\n"
                "- If a supplement you would recommend is already in their stack, "
                "say so plainly (\"you already take magnesium — it also helps here\") "
                "instead of presenting it as something new to start.\n"
                "- Lead with what would ADD to what they already have, so the answer "
                "complements the stack rather than repeating it.\n"
                "- Still list the guide's full tiers, but mark the ones they already "
                "take as already covered.\n"
                "- If something in their stack is relevant to their question — "
                "including timing or a caution against a new item — mention it.\n"
                "Never tell them to stop or change a prescribed medication."
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
