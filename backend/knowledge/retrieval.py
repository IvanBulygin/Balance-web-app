"""Hybrid retrieval: structured SQL, graph traversal, and optional semantics.

Numbers and rankings are answered in SQL. Relationships are answered with graph
queries. Only free text (literature, traditional descriptions) is a candidate
for semantic search — nutrient values are never embedded, so a vector index can
never be the reason a number is wrong.
"""

from __future__ import annotations

from typing import Optional

from . import evidence as ev
from . import ontology as onto
from .db import Database
from .resolution import find_entity

# ------------------------------------------------------------------ entities
def get_entity(db: Database, entity_id: str) -> Optional[dict]:
    e = db.one("SELECT * FROM canonical_entity WHERE id=?", (entity_id,))
    if not e:
        return None
    e["classifications"] = [r["classification"] for r in db.query(
        "SELECT classification FROM entity_classification WHERE entity_id=?", (entity_id,))]
    e["aliases"] = [r["alias"] for r in db.query(
        "SELECT alias FROM entity_alias WHERE entity_id=? ORDER BY alias_type", (entity_id,))]
    e["sources"] = db.query(
        """SELECT sr.source_name, esi.external_id, esi.external_url
           FROM entity_source_id esi JOIN source_registry sr ON sr.id = esi.source_id
           WHERE esi.entity_id=?""", (entity_id,))
    return e


def search_entity(db: Database, name: str, *, limit: int = 10) -> list[dict]:
    """Resolve a name, else offer alias matches ranked by exactness."""
    hit = find_entity(db, name)
    if hit:
        return [get_entity(db, hit)]
    norm = onto.normalise_name(name)
    rows = db.query(
        """SELECT DISTINCT entity_id, alias, alias_norm FROM entity_alias
           WHERE alias_norm LIKE ? LIMIT ?""", (f"%{norm}%", limit))
    return [get_entity(db, r["entity_id"]) for r in rows]


# ----------------------------------------------------------------- nutrients
def food_nutrients(db: Database, entity_id: str) -> list[dict]:
    return db.query(
        """SELECT n.name, n.unit, fn.amount, fn.per_amount, fn.per_unit,
                  sr.source_url, sr.retrieved_at
           FROM food_nutrient fn
           JOIN nutrient n ON n.id = fn.nutrient_id
           JOIN source_record sr ON sr.id = fn.source_record_id
           WHERE fn.entity_id = ? ORDER BY n.name""", (entity_id,))


def foods_by_nutrient(db: Database, nutrient_name: str, *, limit: int = 20,
                      min_amount: float = 0.0) -> list[dict]:
    """Ranked by amount per standardised 100 g — a SQL question, not a vector one."""
    return db.query(
        """SELECT ce.id AS entity_id, ce.primary_name AS food, n.name AS nutrient,
                  fn.amount, n.unit, fn.per_amount, fn.per_unit, sr.source_url
           FROM food_nutrient fn
           JOIN nutrient n ON n.id = fn.nutrient_id
           JOIN canonical_entity ce ON ce.id = fn.entity_id
           JOIN source_record sr ON sr.id = fn.source_record_id
           WHERE lower(n.name) LIKE ? AND fn.amount >= ?
           ORDER BY fn.amount DESC LIMIT ?""",
        (f"%{nutrient_name.lower()}%", min_amount, limit))


def compare_foods(db: Database, entity_ids: list[str],
                  nutrients: Optional[list[str]] = None) -> dict:
    """Side-by-side composition. Values are quoted, never recomputed."""
    out: dict = {"foods": [], "nutrients": {}}
    for eid in entity_ids:
        e = get_entity(db, eid)
        if e:
            out["foods"].append({"id": eid, "name": e["primary_name"]})
    for eid in entity_ids:
        for row in food_nutrients(db, eid):
            if nutrients and not any(n.lower() in row["name"].lower() for n in nutrients):
                continue
            out["nutrients"].setdefault(row["name"], {})[eid] = {
                "amount": row["amount"], "unit": row["unit"],
                "per": f"{row['per_amount']}{row['per_unit']}"}
    return out


# ----------------------------------------------------------------- compounds
def entity_compounds(db: Database, entity_id: str) -> list[dict]:
    return db.query(
        """SELECT c.name AS compound, pp.name AS plant_part, sr.source_url
           FROM entity_compound ec
           JOIN compound c ON c.id = ec.compound_id
           LEFT JOIN plant_part pp ON pp.id = ec.plant_part_id
           JOIN source_record sr ON sr.id = ec.source_record_id
           WHERE ec.entity_id = ?""", (entity_id,))


def entities_containing_compound(db: Database, compound: str, *,
                                 limit: int = 25) -> list[dict]:
    return db.query(
        """SELECT DISTINCT ce.id AS entity_id, ce.primary_name AS name,
                  c.name AS compound, sr.source_url
           FROM entity_compound ec
           JOIN compound c ON c.id = ec.compound_id
           JOIN canonical_entity ce ON ce.id = ec.entity_id
           JOIN source_record sr ON sr.id = ec.source_record_id
           WHERE c.name_norm LIKE ? LIMIT ?""",
        (f"%{onto.normalise_name(compound)}%", limit))


def compounds_with_activity(db: Database, activity: str, *, limit: int = 50) -> list[dict]:
    """Compounds with a biological activity — an activity, not a health benefit."""
    return db.query(
        """SELECT DISTINCT c.name AS compound, ba.name AS activity, sr.source_url
           FROM compound_activity ca
           JOIN compound c ON c.id = ca.compound_id
           JOIN biological_activity ba ON ba.id = ca.activity_id
           JOIN source_record sr ON sr.id = ca.source_record_id
           WHERE lower(ba.name) LIKE ? LIMIT ?""", (f"%{activity.lower()}%", limit))


# ------------------------------------------------------------------- graph
def neighbours(db: Database, entity_id: str, depth: int = 1) -> list[dict]:
    """Bounded traversal of typed edges. Two or three hops is all this needs,
    which is why a graph database would be overkill here."""
    seen, frontier, out = {entity_id}, [entity_id], []
    for _ in range(max(1, depth)):
        if not frontier:
            break
        placeholders = ",".join("?" for _ in frontier)
        rows = db.query(
            f"""SELECT from_id, relation, to_id FROM entity_relationship
                WHERE from_id IN ({placeholders}) OR to_id IN ({placeholders})""",
            frontier + frontier)
        nxt = []
        for r in rows:
            out.append(r)
            for side in (r["from_id"], r["to_id"]):
                if side not in seen:
                    seen.add(side)
                    nxt.append(side)
        frontier = nxt
    return out


# ------------------------------------------------------------------ evidence
def health_evidence(db: Database, *, entity: Optional[str] = None,
                    outcome: Optional[str] = None, human_only: bool = False,
                    limit: int = 25) -> list[dict]:
    """Evidence ranked by strength of design, then study count — never by
    semantic similarity (spec §26)."""
    sql = """SELECT c.*, ce.primary_name AS entity_name, o.name AS outcome,
                    hc.name AS category, p.name AS preparation_form, p.is_concentrated
             FROM evidence_claim c
             JOIN canonical_entity ce ON ce.id = c.entity_id
             JOIN health_outcome o ON o.id = c.health_outcome_id
             JOIN health_category hc ON hc.id = o.category_id
             JOIN preparation_form p ON p.id = c.preparation_form_id
             WHERE 1=1"""
    params: list = []
    if entity:
        eid = find_entity(db, entity) or entity
        sql += " AND c.entity_id = ?"
        params.append(eid)
    if outcome:
        sql += " AND lower(o.name) = ?"
        params.append(outcome.lower())
    rows = db.query(sql, params)
    if human_only:
        rows = [r for r in rows if onto.is_human_evidence(r["evidence_level"])]
    rows.sort(key=lambda r: (-onto.EVIDENCE_RANK.get(r["evidence_level"], 0),
                             -(r["study_count"] or 0)))
    return [ev.qualify_claim(db, r) for r in rows[:limit]]


def studies_for_claim(db: Database, claim_id: int) -> list[dict]:
    return db.query(
        """SELECT s.pmid, s.doi, s.title, s.journal, s.published_at,
                  s.study_design, es.relation, sr.source_url
           FROM evidence_study es
           JOIN study s ON s.id = es.study_id
           JOIN source_record sr ON sr.id = s.source_record_id
           WHERE es.claim_id = ?""", (claim_id,))


# -------------------------------------------------------------------- safety
def safety_for(db: Database, entity_id: str) -> dict:
    return {
        "safety": db.query(
            """SELECT s.kind, s.text, s.severity, p.name AS preparation_form,
                      sr.source_url
               FROM safety_record s
               LEFT JOIN preparation_form p ON p.id = s.preparation_form_id
               JOIN source_record sr ON sr.id = s.source_record_id
               WHERE s.entity_id=?""", (entity_id,)),
        "interactions": db.query(
            """SELECT i.interacts_with, i.severity, i.mechanism, i.text, sr.source_url
               FROM interaction_record i
               JOIN source_record sr ON sr.id = i.source_record_id
               WHERE i.entity_id=?""", (entity_id,)),
    }


# ------------------------------------------------------------------ semantic
def semantic_search(db: Database, query: str, *, kind: Optional[str] = None,
                    limit: int = 10) -> list[dict]:
    """Text search over the embedding_text table.

    Falls back to keyword matching when no embedding backend is configured —
    which keeps the system honest rather than silently returning nothing.
    """
    sql = "SELECT owner_kind, owner_id, text FROM embedding_text WHERE 1=1"
    params: list = []
    if kind:
        sql += " AND owner_kind = ?"
        params.append(kind)
    rows = db.query(sql, params)
    terms = [t for t in onto.normalise_name(query).split() if len(t) > 2]
    scored = []
    for r in rows:
        hay = onto.normalise_name(r["text"])
        score = sum(1 for t in terms if t in hay)
        if score:
            scored.append({**r, "score": score / max(1, len(terms))})
    scored.sort(key=lambda r: -r["score"])
    return scored[:limit]
