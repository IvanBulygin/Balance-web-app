"""Agent tool surface.

Every tool returns narrow, structured JSON with provenance — never a document
dump. The division of labour is fixed (spec §29): this layer owns facts,
identity, evidence classification, citations and safety; the model owns
understanding the question and phrasing the answer.
"""

from __future__ import annotations

from typing import Any, Optional

from . import evidence as ev
from . import ontology as onto
from . import retrieval as R
from .db import Database
from .resolution import find_entity


def _resolve(db: Database, name_or_id: str) -> Optional[str]:
    if db.one("SELECT 1 AS x FROM canonical_entity WHERE id=?", (name_or_id,)):
        return name_or_id
    return find_entity(db, name_or_id)


def _entity_in_query(db: Database, query: str) -> Optional[str]:
    """Find the entity a free-text query is about.

    Matches against every alias, not just the primary name — users write
    "ginger", while the canonical name is "Zingiber officinale". Longest alias
    first so a specific name beats a generic one.
    """
    qn = f" {onto.normalise_name(query)} "
    best, best_len = None, 0
    for row in db.query("SELECT entity_id, alias_norm FROM entity_alias"):
        a = row["alias_norm"]
        if len(a) > best_len and f" {a} " in qn:
            best, best_len = row["entity_id"], len(a)
    return best


def _provenance(rows: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in rows:
        u = r.get("source_url")
        if u and u not in seen:
            seen.add(u)
            out.append({"source_url": u})
    return out


# --------------------------------------------------------------- food tools
def search_food(db: Database, query: str, limit: int = 10) -> dict:
    hits = [h for h in R.search_entity(db, query, limit=limit) if h]
    return {"query": query, "results": [
        {"id": h["id"], "name": h["primary_name"],
         "classifications": h["classifications"]} for h in hits]}


def get_food(db: Database, name_or_id: str) -> dict:
    eid = _resolve(db, name_or_id)
    if not eid:
        return {"found": False, "query": name_or_id,
                "message": "No entity in the knowledge base matches that name."}
    e = R.get_entity(db, eid)
    return {"found": True, "entity": {
        "id": e["id"], "name": e["primary_name"],
        "scientific_name": e["scientific_name"],
        "classifications": e["classifications"], "aliases": e["aliases"][:12]},
        "sources": e["sources"]}


def get_food_nutrients(db: Database, name_or_id: str) -> dict:
    eid = _resolve(db, name_or_id)
    if not eid:
        return {"found": False, "query": name_or_id}
    rows = R.food_nutrients(db, eid)
    return {"found": True, "entity_id": eid,
            "nutrition": [{"nutrient": r["name"], "amount": r["amount"],
                           "unit": r["unit"],
                           "per": f"{r['per_amount']}{r['per_unit']}"} for r in rows],
            "sources": _provenance(rows)}


def find_foods_by_nutrient(db: Database, nutrient: str, limit: int = 20) -> dict:
    rows = R.foods_by_nutrient(db, nutrient, limit=limit)
    return {"nutrient": nutrient,
            "ranked_by": "amount per 100 g, from USDA structured data",
            "results": [{"id": r["entity_id"], "food": r["food"],
                         "amount": r["amount"], "unit": r["unit"],
                         "per": f"{r['per_amount']}{r['per_unit']}"} for r in rows],
            "sources": _provenance(rows)}


def compare_foods(db: Database, names: list[str],
                  nutrients: Optional[list[str]] = None) -> dict:
    ids = [i for i in (_resolve(db, n) for n in names) if i]
    return R.compare_foods(db, ids, nutrients)


# -------------------------------------------------------------- plant tools
def search_plant(db: Database, query: str, limit: int = 10) -> dict:
    return search_food(db, query, limit)


def get_plant(db: Database, name_or_id: str) -> dict:
    return get_food(db, name_or_id)


def search_herb(db: Database, query: str, limit: int = 10) -> dict:
    hits = [h for h in R.search_entity(db, query, limit=limit) if h]
    herbs = [h for h in hits if {"HERB", "MEDICINAL_PLANT", "SPICE"} & set(h["classifications"])]
    return {"query": query, "results": [
        {"id": h["id"], "name": h["primary_name"],
         "classifications": h["classifications"]} for h in (herbs or hits)]}


def get_herb(db: Database, name_or_id: str) -> dict:
    return get_food(db, name_or_id)


# ----------------------------------------------------------- compound tools
def find_compounds(db: Database, name_or_id: str) -> dict:
    eid = _resolve(db, name_or_id)
    if not eid:
        return {"found": False, "query": name_or_id}
    rows = R.entity_compounds(db, eid)
    return {"found": True, "entity_id": eid,
            "compounds": [{"compound": r["compound"], "plant_part": r["plant_part"]}
                          for r in rows],
            "note": "Presence of a compound is not evidence of a health effect.",
            "sources": _provenance(rows)}


def find_foods_containing_compound(db: Database, compound: str, limit: int = 25) -> dict:
    rows = R.entities_containing_compound(db, compound, limit=limit)
    return {"compound": compound,
            "results": [{"id": r["entity_id"], "name": r["name"]} for r in rows],
            "note": "Composition data. Not a claim that eating these has an effect.",
            "sources": _provenance(rows)}


def find_plants_containing_compound(db: Database, compound: str, limit: int = 25) -> dict:
    return find_foods_containing_compound(db, compound, limit)


def find_compounds_by_activity(db: Database, activity: str, limit: int = 50) -> dict:
    rows = R.compounds_with_activity(db, activity, limit=limit)
    return {"activity": activity,
            "results": [{"compound": r["compound"], "activity": r["activity"]} for r in rows],
            "note": "A biological activity is a laboratory property, not a health benefit.",
            "sources": _provenance(rows)}


# ----------------------------------------------------------- evidence tools
def find_health_evidence(db: Database, entity: Optional[str] = None,
                         outcome: Optional[str] = None, human_only: bool = False,
                         limit: int = 25) -> dict:
    claims = R.health_evidence(db, entity=entity, outcome=outcome,
                               human_only=human_only, limit=limit)
    return {"entity": entity, "outcome": outcome,
            "ranked_by": "evidence level (study design), then study count",
            "claims": [{
                "id": c["id"], "entity": c.get("entity_name"), "outcome": c["outcome"],
                "health_category": c["category"], "evidence_level": c["evidence_level"],
                "direction": c["direction"], "certainty": c["certainty"],
                "study_count": c["study_count"], "preparation_form": c["preparation_form"],
                "applies_to_food": c["applies_to_food"], "phrasing": c["phrasing"],
                "caveats": c["caveats"], "claim": c["claim_text"],
            } for c in claims]}


def get_traditional_use(db: Database, name_or_id: str) -> dict:
    """Traditional use only. Explicitly separated from clinical evidence."""
    eid = _resolve(db, name_or_id)
    if not eid:
        return {"found": False, "query": name_or_id}
    rows = ev.traditional_use_for(db, eid)
    return {"found": True, "entity_id": eid, "evidence_level": "TRADITIONAL_USE",
            "is_clinical_evidence": False,
            "traditional_uses": [{"use": r["use_text"], "tradition": r["tradition"],
                                  "plant_part": r["plant_part"]} for r in rows],
            "caveat": "Traditional or historical use. Not clinical evidence.",
            "sources": _provenance(rows)}


def find_studies(db: Database, entity: Optional[str] = None,
                 outcome: Optional[str] = None, limit: int = 20) -> dict:
    claims = R.health_evidence(db, entity=entity, outcome=outcome, limit=limit)
    studies = []
    for c in claims:
        studies.extend(R.studies_for_claim(db, c["id"]))
    return {"studies": [{"pmid": s["pmid"], "doi": s["doi"], "title": s["title"],
                         "journal": s["journal"], "published_at": s["published_at"],
                         "study_design": s["study_design"], "relation": s["relation"],
                         "url": s["source_url"]} for s in studies[:limit]]}


def get_evidence_for_claim(db: Database, claim_id: int) -> dict:
    row = db.one("""SELECT c.*, o.name AS outcome, p.name AS preparation_form
                    FROM evidence_claim c
                    JOIN health_outcome o ON o.id = c.health_outcome_id
                    JOIN preparation_form p ON p.id = c.preparation_form_id
                    WHERE c.id=?""", (claim_id,))
    if not row:
        return {"found": False, "claim_id": claim_id}
    return {"found": True, "claim": ev.qualify_claim(db, row),
            "studies": R.studies_for_claim(db, claim_id)}


def get_safety_information(db: Database, name_or_id: str) -> dict:
    eid = _resolve(db, name_or_id)
    if not eid:
        return {"found": False, "query": name_or_id}
    data = R.safety_for(db, eid)
    return {"found": True, "entity_id": eid, "safety": data["safety"],
            "note": "Absence of a safety record is not evidence of safety.",
            "sources": _provenance(data["safety"])}


def get_interactions(db: Database, name_or_id: str) -> dict:
    eid = _resolve(db, name_or_id)
    if not eid:
        return {"found": False, "query": name_or_id}
    data = R.safety_for(db, eid)
    return {"found": True, "entity_id": eid, "interactions": data["interactions"],
            "note": "Not exhaustive. An unlisted combination is not proven safe.",
            "sources": _provenance(data["interactions"])}


# ------------------------------------------------------------ router
def knowledge_search(db: Database, query: str) -> dict:
    """Route a natural-language query to the right retrieval strategy.

    Intent is decided by structure, not by a vector search over everything.
    """
    q = query.lower()
    intents: list[str] = []
    result: dict[str, Any] = {"query": query}

    nutrient = next((n for n in ("magnesium", "potassium", "fiber", "fibre", "vitamin c",
                                 "calcium", "iron", "folate", "zinc", "vitamin d")
                     if n in q), None)
    if nutrient and any(w in q for w in ("high in", "rich in", "most", "source of",
                                         "increase", "contain")):
        intents.append("nutrient_ranking")
        result["foods_by_nutrient"] = find_foods_by_nutrient(db, nutrient)

    for c in ("quercetin", "curcumin", "gingerol", "allicin", "catechin"):
        if c in q:
            intents.append("compound_lookup")
            result["foods_with_compound"] = find_foods_containing_compound(db, c)
            break

    if "traditional" in q or "traditionally used" in q:
        intents.append("traditional_use")
        ent = _entity_in_query(db, q)
        if ent:
            result["traditional_use"] = get_traditional_use(db, ent)

    if any(w in q for w in ("evidence", "studies", "clinical", "research", "trial",
                            "does the science", "what does science")):
        intents.append("evidence")
        outcome = next((o for o in onto.HEALTH_OUTCOMES if o.lower() in q), None)
        entity = _entity_in_query(db, q)
        result["evidence"] = find_health_evidence(db, entity=entity, outcome=outcome,
                                                  human_only="human" in q)

    if any(w in q for w in ("safe", "safety", "interact", "side effect")):
        intents.append("safety")
        ent = _entity_in_query(db, q)
        if ent:
            result["safety"] = get_safety_information(db, ent)
            result["interactions"] = get_interactions(db, ent)

    if not intents:
        intents.append("entity_search")
        result["entities"] = search_food(db, query)

    result["intents"] = intents
    result["contract"] = ("Facts, evidence levels and citations come from the "
                          "knowledge base. Do not add evidence that is not here; "
                          "if it is missing, say so.")
    return result


TOOLS = {
    "search_food": search_food, "get_food": get_food,
    "get_food_nutrients": get_food_nutrients,
    "find_foods_by_nutrient": find_foods_by_nutrient, "compare_foods": compare_foods,
    "search_plant": search_plant, "get_plant": get_plant,
    "search_herb": search_herb, "get_herb": get_herb,
    "find_compounds": find_compounds,
    "find_foods_containing_compound": find_foods_containing_compound,
    "find_plants_containing_compound": find_plants_containing_compound,
    "find_compounds_by_activity": find_compounds_by_activity,
    "find_health_evidence": find_health_evidence,
    "get_traditional_use": get_traditional_use,
    "find_studies": find_studies, "get_evidence_for_claim": get_evidence_for_claim,
    "get_safety_information": get_safety_information,
    "get_interactions": get_interactions, "knowledge_search": knowledge_search,
}
