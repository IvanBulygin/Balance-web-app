"""Food & herb knowledge for the running agent.

Loads the USDA seed (public domain, values verbatim from FoodData Central) plus
the curated plant/compound/traditional-use table, and answers the structured
questions in SQL-ish Python rather than by asking the model.

The rules from the knowledge-base design are kept here too:
  * traditional use is returned separately and labelled, never as evidence
  * a compound being present is composition, not a health claim
  * nutrient numbers are quoted, never computed by a model
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

DATA = Path(__file__).resolve().parent / "data"
SEED_PATH = DATA / "usda_seed.json"
HERBS_PATH = DATA / "herbs_seed.json"
GOALS_PATH = DATA / "goal_foods.json"

# Nutrients kept from a live FoodData Central record — the same set the seed
# was built with, so live and shipped entries look identical downstream.
KEEP_NUTRIENTS = {
    "Magnesium, Mg", "Potassium, K", "Calcium, Ca", "Iron, Fe", "Zinc, Zn",
    "Sodium, Na", "Phosphorus, P", "Selenium, Se", "Copper, Cu",
    "Vitamin C, total ascorbic acid", "Vitamin D (D2 + D3)",
    "Vitamin E (alpha-tocopherol)", "Vitamin K (phylloquinone)",
    "Vitamin B-6", "Vitamin B-12", "Folate, total", "Niacin", "Riboflavin",
    "Thiamin", "Vitamin A, RAE",
    "Fiber, total dietary", "Protein", "Total lipid (fat)",
    "Carbohydrate, by difference", "Energy", "Sugars, total including NLEA",
    "Fatty acids, total polyunsaturated", "Fatty acids, total saturated",
}
_live_cache: dict[str, Any] = {}

# Friendly aliases -> the USDA nutrient names in the seed.
NUTRIENT_ALIASES = {
    "magnesium": "Magnesium, Mg", "potassium": "Potassium, K",
    "calcium": "Calcium, Ca", "iron": "Iron, Fe", "zinc": "Zinc, Zn",
    "selenium": "Selenium, Se", "copper": "Copper, Cu",
    "sodium": "Sodium, Na", "phosphorus": "Phosphorus, P",
    "fiber": "Fiber, total dietary", "fibre": "Fiber, total dietary",
    "protein": "Protein", "fat": "Total lipid (fat)",
    "carbs": "Carbohydrate, by difference",
    "carbohydrate": "Carbohydrate, by difference",
    "sugar": "Sugars, total including NLEA", "energy": "Energy",
    "calories": "Energy",
    "vitamin c": "Vitamin C, total ascorbic acid",
    "vitamin d": "Vitamin D (D2 + D3)",
    "vitamin e": "Vitamin E (alpha-tocopherol)",
    "vitamin k": "Vitamin K (phylloquinone)",
    "vitamin a": "Vitamin A, RAE",
    "vitamin b6": "Vitamin B-6", "b6": "Vitamin B-6",
    "vitamin b12": "Vitamin B-12", "b12": "Vitamin B-12",
    "folate": "Folate, total", "folic acid": "Folate, total",
    "niacin": "Niacin", "riboflavin": "Riboflavin", "thiamin": "Thiamin",
    "omega-3": "Fatty acids, total polyunsaturated",
    # Russian — users type these too.
    "магни": "Magnesium, Mg", "калий": "Potassium, K", "кальци": "Calcium, Ca",
    "желез": "Iron, Fe", "цинк": "Zinc, Zn", "селен": "Selenium, Se",
    "клетчатк": "Fiber, total dietary", "белок": "Protein",
    "витамин c": "Vitamin C, total ascorbic acid", "витамин д": "Vitamin D (D2 + D3)",
    "витамин e": "Vitamin E (alpha-tocopherol)", "фолиев": "Folate, total",
}

_state: dict[str, Any] = {"foods": [], "herbs": [], "goals": {},
                          "attribution": "", "goal_disclaimer": ""}


def _norm(s: str) -> str:
    """Fold a name to a comparable key.

    Unicode-aware on purpose: an ASCII-only class would strip Cyrillic
    entirely, so Russian names would silently never match.
    """
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w]+", " ", s.lower(), flags=re.UNICODE).split())


def load() -> dict:
    """Load the seeds once at startup. Missing files degrade quietly."""
    try:
        seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        _state["foods"] = seed.get("foods", [])
        _state["attribution"] = seed.get("attribution", "")
    except FileNotFoundError:
        _state["foods"] = []
    try:
        _state["herbs"] = json.loads(HERBS_PATH.read_text(encoding="utf-8")).get("herbs", [])
    except FileNotFoundError:
        _state["herbs"] = []
    try:
        g = json.loads(GOALS_PATH.read_text(encoding="utf-8"))
        _state["goals"] = g.get("goals", {})
        _state["goal_disclaimer"] = g.get("disclaimer", "")
    except FileNotFoundError:
        _state["goals"] = {}
    return {"foods": len(_state["foods"]), "herbs": len(_state["herbs"]),
            "goals": len(_state["goals"])}


# ------------------------------------------------------------------ lookup
def resolve_nutrient(text: str) -> Optional[str]:
    t = _norm(text)
    for alias, usda in sorted(NUTRIENT_ALIASES.items(), key=lambda kv: -len(kv[0])):
        if alias in t:
            return usda
    return None


def is_seasoning(description: str) -> bool:
    """Dried spices and herbs are eaten by the pinch, not by the 100 g.

    USDA publishes their composition per 100 g like any other food, so dried
    basil outranks every real source of magnesium. Ranking them alongside
    foods would tell someone to eat 100 g of dried thyme, so they are marked
    and kept out of food rankings.
    """
    d = (description or "").lower()
    return d.startswith(("spices,", "seasoning")) or "dried" in d.split(",")[0]


def foods_by_nutrient(nutrient: str, limit: int = 8,
                      include_seasonings: bool = False) -> list[dict]:
    """Foods ranked by amount per 100 g. Values quoted from USDA."""
    usda = resolve_nutrient(nutrient) or nutrient
    out = []
    for f in _state["foods"]:
        for n in f["nutrients"]:
            if n["name"] == usda:
                seasoning = is_seasoning(f["description"])
                if seasoning and not include_seasonings:
                    break
                out.append({"food": f["description"], "fdc_id": f["fdc_id"],
                            "amount": n["amount"], "unit": n["unit"],
                            "nutrient": n["name"], "is_seasoning": seasoning})
                break
    out.sort(key=lambda r: -r["amount"])
    return out[:limit]


def live_lookup(name: str) -> Optional[dict]:
    """Query FoodData Central for a food that isn't in the shipped seed.

    The seed covers common whole foods; this extends coverage to the rest of
    USDA's database at runtime. Results are cached in memory for the life of
    the process. Values are stored exactly as USDA returns them.

    Returns None when no key is configured or the API is unreachable — the
    caller then behaves as it did before, rather than inventing anything.
    """
    key = os.environ.get("FDC_API_KEY")
    if not key or not name.strip():
        return None
    ck = _norm(name)
    if ck in _live_cache:
        return _live_cache[ck]

    url = (f"https://api.nal.usda.gov/fdc/v1/foods/search"
           f"?query={urllib.parse.quote(name.strip())}"
           f"&dataType={urllib.parse.quote('Foundation,SR Legacy')}"
           f"&pageSize=1&api_key={key}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BalanceAI/1.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            payload = json.loads(r.read())
    except Exception as exc:  # noqa: BLE001 - degrade quietly, never fabricate
        print(f"[usda] live lookup failed for {name!r}: {exc}")
        _live_cache[ck] = None
        return None

    foods = payload.get("foods") or []
    if not foods:
        _live_cache[ck] = None
        return None
    food = foods[0]

    # The search endpoint returns an abridged nutrient list, so a food can come
    # back without magnesium even though USDA holds a value. Fetch the full
    # record for complete composition.
    try:
        durl = (f"https://api.nal.usda.gov/fdc/v1/food/{food['fdcId']}"
                f"?api_key={key}")
        dreq = urllib.request.Request(durl, headers={"User-Agent": "BalanceAI/1.0"})
        with urllib.request.urlopen(dreq, timeout=12) as r:
            detail = json.loads(r.read())
        if detail.get("foodNutrients"):
            food = {
                "fdcId": detail.get("fdcId", food["fdcId"]),
                "description": detail.get("description", food["description"]),
                "dataType": detail.get("dataType", food.get("dataType")),
                "foodNutrients": [
                    {"nutrientName": (n.get("nutrient") or {}).get("name"),
                     "value": n.get("amount"),
                     "unitName": (n.get("nutrient") or {}).get("unitName"),
                     "nutrientId": (n.get("nutrient") or {}).get("id")}
                    for n in detail["foodNutrients"]
                ],
            }
    except Exception as exc:  # noqa: BLE001 - the abridged record still works
        print(f"[usda] detail fetch failed for {name!r}: {exc}")

    nutrients = [
        {"name": n["nutrientName"], "amount": n["value"],
         "unit": (n.get("unitName") or "").lower(),
         "usda_nutrient_id": n.get("nutrientId")}
        for n in food.get("foodNutrients", [])
        if n.get("nutrientName") in KEEP_NUTRIENTS and n.get("value") is not None
    ]
    if not nutrients:
        _live_cache[ck] = None
        return None
    entry = {"fdc_id": food["fdcId"], "description": food["description"],
             "data_type": food.get("dataType"), "query": name,
             "nutrients": nutrients, "live": True}
    _live_cache[ck] = entry
    return entry


def find_food(name: str) -> Optional[dict]:
    n = _norm(name)
    if not n:
        return None
    best, best_len = None, 0
    for f in _state["foods"]:
        d = _norm(f["description"])
        q = _norm(f.get("query", ""))
        for hay in (d, q):
            for token in (n, *n.split()):
                if len(token) > 2 and token in hay and len(token) > best_len:
                    best, best_len = f, len(token)
    return best


def nutrients_for(name: str, top: int = 12) -> Optional[dict]:
    """Composition for a food. Falls back to a live USDA query when the food
    isn't in the shipped seed, so coverage isn't limited to the seeded list."""
    f = find_food(name) or live_lookup(name)
    if not f:
        return None
    return {"food": f["description"], "fdc_id": f["fdc_id"],
            "nutrients": f["nutrients"][:top], "live": f.get("live", False)}


def find_herb(name: str) -> Optional[dict]:
    n = _norm(name)
    for h in _state["herbs"]:
        names = [h["name"], h.get("scientific_name", ""), *h.get("aliases", [])]
        if any(_norm(x) and _norm(x) in n for x in names):
            return h
    return None


def herbs_with_compound(compound: str) -> list[dict]:
    """One row per plant, listing every matching compound it contains.

    Related compounds (curcumin, demethoxycurcumin, ...) would otherwise repeat
    the same plant several times.
    """
    c = _norm(compound)
    if not c:
        return []
    out = []
    for h in _state["herbs"]:
        matches = [comp for comp in h.get("compounds", []) if c in _norm(comp)]
        if matches:
            out.append({"name": h["name"],
                        "scientific_name": h.get("scientific_name"),
                        "compound": ", ".join(matches)})
    return out


def foods_with_compound(compound: str) -> list[dict]:
    """Compound presence is composition data, not a health claim."""
    return herbs_with_compound(compound)


# ------------------------------------------------------------------ router
_NUTRIENT_CUE = re.compile(
    r"high in|rich in|most |source of|sources of|contain|increase my|boost my|"
    r"how much|good source", re.I)
_TRAD_CUE = re.compile(r"traditional|traditionally|folk (use|medicine)|ayurved", re.I)
_COMPOUND_CUE = re.compile(
    r"curcumin|quercetin|gingerol|allicin|catechin|piperine|capsaicin|"
    r"sulforaphane|resveratrol|anthocyanin", re.I)


def for_goal(slug: str, foods_per_nutrient: int = 4) -> Optional[dict]:
    """Foods and herbs for a health goal, for the goal/category screen.

    Foods are ranked from USDA measured composition against the nutrients
    mapped to that goal. Herbs carry their own evidence level. Nothing here
    claims a food treats anything — the nutrient link is dietary context.
    """
    goal = _state["goals"].get(slug)
    if not goal:
        return None

    seen: set[str] = set()
    nutrients = []
    for n in goal.get("nutrients", []):
        rows = [r for r in foods_by_nutrient(n["name"], limit=foods_per_nutrient * 3)
                if r["food"] not in seen]
        rows = rows[:foods_per_nutrient]
        for r in rows:
            seen.add(r["food"])
        if rows:
            nutrients.append({"nutrient": n["name"], "why": n["why"], "foods": rows})

    herbs = []
    for name in goal.get("herbs", []):
        h = next((x for x in _state["herbs"] if x["name"] == name), None)
        if not h:
            continue
        herbs.append({
            "name": h["name"], "scientific_name": h.get("scientific_name"),
            "compounds": h.get("compounds", [])[:4],
            "human_evidence": h.get("human_evidence", []),
            "traditional_uses": h.get("traditional_uses", []),
            "safety": h.get("safety"), "source": h.get("source"),
        })
    # Strongest human evidence first; herbs with none fall to the bottom.
    rank = {"META_ANALYSIS": 5, "SYSTEMATIC_REVIEW": 4, "CLINICAL_TRIAL": 3,
            "OBSERVATIONAL_HUMAN": 2}
    herbs.sort(key=lambda h: -max([rank.get(e["evidence_level"], 0)
                                   for e in h["human_evidence"]] or [0]))

    if not nutrients and not herbs:
        return None
    return {"goal": slug, "title": goal.get("title", slug),
            "nutrients": nutrients, "herbs": herbs,
            "attribution": _state["attribution"],
            "disclaimer": _state["goal_disclaimer"]}


def lookup(name: str) -> Optional[dict]:
    """Full entry for a bare name — "ginger", "spinach", "turmeric".

    A bare name is itself a request for everything we hold, so this returns the
    herb dossier (or food composition) without needing a question phrased
    around it.
    """
    h = find_herb(name)
    if h:
        return {"kind": "herb", "herb": h["name"],
                "scientific_name": h.get("scientific_name"),
                "compounds": h.get("compounds", []),
                "traditional_uses": h.get("traditional_uses", []),
                "human_evidence": h.get("human_evidence", []),
                "safety": h.get("safety"), "source": h.get("source"),
                "attribution": _state["attribution"],
                "caveat": "Traditional use and human evidence are different things "
                          "and are listed separately above."}
    # A nutrient name on its own means the nutrient, not a medicine that happens
    # to contain it — "magnesium" must never resolve to esomeprazole magnesium.
    usda = resolve_nutrient(name)
    if usda:
        rows = foods_by_nutrient(usda)
        if rows:
            return {"kind": "nutrient_ranking", "nutrient": usda,
                    "ranked_by": "amount per 100 g (USDA structured data)",
                    "results": rows, "attribution": _state["attribution"]}

    f = nutrients_for(name)
    if f:
        return {"kind": "food_nutrition", **f, "attribution": _state["attribution"]}
    return None


def answer(query: str) -> Optional[dict]:
    """Return structured knowledge for a food/herb question, or None.

    None means "not a knowledge question" — the caller falls through to the
    normal supplement-guide flow.
    """
    q = query or ""
    result: dict[str, Any] = {"kind": None, "attribution": _state["attribution"]}

    m = _COMPOUND_CUE.search(q)
    if m:
        hits = foods_with_compound(m.group(0))
        if hits:
            return {**result, "kind": "compound", "compound": m.group(0).lower(),
                    "sources_note": "Composition data. Presence of a compound is "
                                    "not evidence that eating it has an effect.",
                    "results": hits}

    if _TRAD_CUE.search(q):
        h = find_herb(q)
        if h and h.get("traditional_uses"):
            return {**result, "kind": "traditional", "herb": h["name"],
                    "scientific_name": h.get("scientific_name"),
                    "traditional_uses": h["traditional_uses"],
                    "evidence_level": "TRADITIONAL_USE",
                    "is_clinical_evidence": False,
                    "caveat": "Traditional or historical use. This is not clinical "
                              "evidence that it works.",
                    "source": h.get("source")}

    nutrient = resolve_nutrient(q)
    if nutrient and _NUTRIENT_CUE.search(q):
        rows = foods_by_nutrient(nutrient)
        if rows:
            return {**result, "kind": "nutrient_ranking", "nutrient": nutrient,
                    "ranked_by": "amount per 100 g (USDA structured data)",
                    "results": rows}

    # "what is in spinach", "nutrition of kale"
    if re.search(r"nutrition|nutrients? (in|of)|what.s in ", q, re.I):
        f = nutrients_for(q)
        if f:
            return {**result, "kind": "food_nutrition", **f}

    h = find_herb(q)
    if h and re.search(r"evidence|studies|research|what does .* do|about ", q, re.I):
        return {**result, "kind": "herb", "herb": h["name"],
                "scientific_name": h.get("scientific_name"),
                "compounds": h.get("compounds", []),
                "traditional_uses": h.get("traditional_uses", []),
                "human_evidence": h.get("human_evidence", []),
                "safety": h.get("safety"), "source": h.get("source"),
                "caveat": "Traditional use and human evidence are different things "
                          "and are listed separately above."}
    return None


def format_for_agent(data: dict) -> str:
    """Render the structured result as context the model must not contradict."""
    k = data["kind"]
    lines: list[str] = []
    if k == "nutrient_ranking":
        lines.append(f"### Foods highest in {data['nutrient']} "
                     f"({data['ranked_by']})")
        for r in data["results"]:
            lines.append(f"- {r['food']}: {r['amount']} {r['unit']} per 100 g "
                         f"(USDA FDC {r['fdc_id']})")
        lines.append("These are USDA measured values. Do not alter the numbers, "
                     "and do not add foods that are not listed.")
    elif k == "food_nutrition":
        lines.append(f"### {data['food']} — per 100 g (USDA FDC {data['fdc_id']})")
        for n in data["nutrients"]:
            lines.append(f"- {n['name']}: {n['amount']} {n['unit']}")
    elif k == "compound":
        lines.append(f"### Plants/foods containing {data['compound']}")
        for r in data["results"]:
            lines.append(f"- {r['name']} ({r.get('scientific_name') or '—'}): {r['compound']}")
        lines.append(data["sources_note"])
    elif k == "traditional":
        lines.append(f"### {data['herb']} — TRADITIONAL USE ONLY")
        for u in data["traditional_uses"]:
            lines.append(f"- {u}")
        lines.append(data["caveat"])
        lines.append("Do NOT describe these as proven, clinical or evidence-based.")
    elif k == "herb":
        lines.append(f"### {data['herb']} ({data.get('scientific_name') or ''})")
        if data.get("compounds"):
            lines.append("Compounds: " + ", ".join(data["compounds"]))
        if data.get("traditional_uses"):
            lines.append("TRADITIONAL USE (not clinical evidence): " +
                         "; ".join(data["traditional_uses"]))
        for e in data.get("human_evidence", []):
            lines.append(f"HUMAN EVIDENCE [{e['evidence_level']}] {e['outcome']}: "
                         f"{e['summary']} (preparation: {e['preparation']}"
                         f"{'; ' + e['pmid'] if e.get('pmid') else ''})")
        if data.get("safety"):
            lines.append(f"Safety: {data['safety']}")
        lines.append(data["caveat"])
    if data.get("attribution"):
        lines.append(f"Attribution: {data['attribution']}")
    return "\n".join(lines)
