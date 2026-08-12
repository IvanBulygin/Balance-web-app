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
import re
import unicodedata
from pathlib import Path
from typing import Any, Optional

DATA = Path(__file__).resolve().parent / "data"
SEED_PATH = DATA / "usda_seed.json"
HERBS_PATH = DATA / "herbs_seed.json"

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
}

_state: dict[str, Any] = {"foods": [], "herbs": [], "attribution": ""}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


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
    return {"foods": len(_state["foods"]), "herbs": len(_state["herbs"])}


# ------------------------------------------------------------------ lookup
def resolve_nutrient(text: str) -> Optional[str]:
    t = _norm(text)
    for alias, usda in sorted(NUTRIENT_ALIASES.items(), key=lambda kv: -len(kv[0])):
        if alias in t:
            return usda
    return None


def foods_by_nutrient(nutrient: str, limit: int = 8) -> list[dict]:
    """Foods ranked by amount per 100 g. Values quoted from USDA."""
    usda = resolve_nutrient(nutrient) or nutrient
    out = []
    for f in _state["foods"]:
        for n in f["nutrients"]:
            if n["name"] == usda:
                out.append({"food": f["description"], "fdc_id": f["fdc_id"],
                            "amount": n["amount"], "unit": n["unit"],
                            "nutrient": n["name"]})
                break
    out.sort(key=lambda r: -r["amount"])
    return out[:limit]


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
    f = find_food(name)
    if not f:
        return None
    return {"food": f["description"], "fdc_id": f["fdc_id"],
            "nutrients": f["nutrients"][:top]}


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
