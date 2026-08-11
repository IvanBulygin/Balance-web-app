"""Evidence engine and medical-claim safeguards.

Three rules are enforced in code, not in a prompt:

  1. Traditional use is never evidence. It lives in its own table and
     `traditional_use_for()` returns it labelled as such.
  2. Evidence about a concentrated preparation is never presented as advice
     about eating the food. `applies_to_food()` decides, and
     `qualify_claim()` attaches the caveat.
  3. The evidence level comes from the study design. More papers raise
     confidence, never the level (spec §13).
"""

from __future__ import annotations

from typing import Optional

from . import ontology as onto
from .db import Database

# Language the response layer is allowed to use for each level. Deliberately
# cautious: nothing here says "treats", "cures" or "proven".
LEVEL_PHRASING = {
    "IN_VITRO": "studied only in laboratory settings",
    "ANIMAL": "studied in animals, not in people",
    "MECHANISTIC": "supported by proposed mechanisms rather than outcomes in people",
    "OBSERVATIONAL_HUMAN": "associated with the outcome in observational studies, "
                           "which cannot establish cause",
    "CLINICAL_TRIAL": "examined in human clinical trials",
    "SYSTEMATIC_REVIEW": "assessed in a systematic review of human studies",
    "META_ANALYSIS": "pooled in a meta-analysis of human studies",
    "CLINICAL_GUIDELINE": "addressed in a clinical guideline",
}

BANNED_CLAIM_WORDS = ("treats", "cures", "prevents", "heals", "eliminates",
                      "guarantees", "proven to treat")


def certainty_from(level: str, study_count: int, direction: str) -> str:
    """Confidence, bounded by design. Volume alone never yields 'high'."""
    if direction == "INCONCLUSIVE":
        return "very_low"
    rank = onto.EVIDENCE_RANK.get(level, 0)
    if rank <= onto.EVIDENCE_RANK["MECHANISTIC"]:
        return "very_low"
    if level == "OBSERVATIONAL_HUMAN":
        return "low"
    if level == "CLINICAL_TRIAL":
        return "moderate" if study_count >= 2 else "low"
    return "high" if study_count >= 2 else "moderate"


def applies_to_food(db: Database, preparation_form_id: int) -> bool:
    """False when the evidence concerns a concentrated preparation."""
    row = db.one("SELECT name, is_concentrated FROM preparation_form WHERE id=?",
                 (preparation_form_id,))
    return bool(row) and not row["is_concentrated"]


def qualify_claim(db: Database, claim: dict) -> dict:
    """Attach the caveats the response layer must carry."""
    level = claim["evidence_level"]
    form = db.one("SELECT name, is_concentrated FROM preparation_form WHERE id=?",
                  (claim["preparation_form_id"],)) or {}
    caveats = []
    if form.get("is_concentrated"):
        caveats.append(
            f"This evidence concerns {form.get('name','a concentrated preparation')}, "
            "which is not the same as eating the food in normal culinary amounts.")
    if not onto.is_human_evidence(level):
        caveats.append("No human outcome evidence — this is laboratory or animal work.")
    if claim.get("direction") == "INCONCLUSIVE":
        caveats.append("Findings are mixed or inconclusive.")
    if claim.get("direction") == "DOES_NOT_SUPPORT":
        caveats.append("The evidence did not support a benefit.")
    return {
        **claim,
        "phrasing": LEVEL_PHRASING.get(level, "studied"),
        "applies_to_food": not form.get("is_concentrated", 0),
        "caveats": caveats,
    }


def validate_claim_text(text: str) -> Optional[str]:
    """Reject wording that turns evidence into a medical claim."""
    low = (text or "").lower()
    for w in BANNED_CLAIM_WORDS:
        if w in low:
            return (f"Claim text contains disallowed wording {w!r}. Describe what "
                    "was studied and how strong the evidence is instead.")
    return None


def add_claim(db: Database, *, entity_id: str, outcome: str, preparation_form: str,
              study_design: str, direction: str, claim_text: str,
              source_record_id: int, study_ids: Optional[list[int]] = None,
              effect_size: str = "") -> int:
    """Create an evidence claim. The level is derived, never passed in."""
    err = validate_claim_text(claim_text)
    if err:
        raise ValueError(err)

    level = onto.level_for_design(study_design)
    outcome_row = db.one("SELECT id FROM health_outcome WHERE name=?", (outcome,))
    if not outcome_row:
        raise ValueError(f"Unknown health outcome {outcome!r} — outcomes are a "
                         "controlled vocabulary, not free text.")
    form_row = db.one("SELECT id FROM preparation_form WHERE name=?", (preparation_form,))
    if not form_row:
        raise ValueError(f"Unknown preparation form {preparation_form!r}.")

    n = len(study_ids or [])
    claim_id = db.insert(
        """INSERT INTO evidence_claim
           (entity_id, health_outcome_id, preparation_form_id, evidence_level,
            direction, effect_size, certainty, study_count, claim_text,
            last_verified, source_record_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (entity_id, outcome_row["id"], form_row["id"], level, direction,
         effect_size or None, certainty_from(level, n, direction), n, claim_text,
         __import__("datetime").datetime.now().date().isoformat(), source_record_id))
    for sid in (study_ids or []):
        db.insert("INSERT INTO evidence_study (claim_id, study_id, relation) "
                  "VALUES (?,?,?)", (claim_id, sid, direction))
    db.commit()
    return claim_id


def claims_for(db: Database, entity_id: str, *, outcome: Optional[str] = None,
               human_only: bool = False, food_forms_only: bool = False) -> list[dict]:
    """Evidence claims, strongest first — ranked by level, not by similarity."""
    sql = """SELECT c.*, o.name AS outcome, hc.name AS category,
                    p.name AS preparation_form, p.is_concentrated
             FROM evidence_claim c
             JOIN health_outcome o ON o.id = c.health_outcome_id
             JOIN health_category hc ON hc.id = o.category_id
             JOIN preparation_form p ON p.id = c.preparation_form_id
             WHERE c.entity_id = ?"""
    params: list = [entity_id]
    if outcome:
        sql += " AND o.name = ?"
        params.append(outcome)
    if food_forms_only:
        sql += " AND p.is_concentrated = 0"
    rows = db.query(sql, params)
    if human_only:
        rows = [r for r in rows if onto.is_human_evidence(r["evidence_level"])]
    rows.sort(key=lambda r: (-onto.EVIDENCE_RANK.get(r["evidence_level"], 0),
                             -(r["study_count"] or 0)))
    return [qualify_claim(db, r) for r in rows]


def traditional_use_for(db: Database, entity_id: str) -> list[dict]:
    """Traditional use, explicitly labelled as not being clinical evidence."""
    rows = db.query(
        """SELECT t.use_text, t.tradition, pp.name AS plant_part,
                  sr.source_url, sr.retrieved_at
           FROM traditional_use t
           LEFT JOIN plant_part pp ON pp.id = t.plant_part_id
           JOIN source_record sr ON sr.id = t.source_record_id
           WHERE t.entity_id = ?""", (entity_id,))
    for r in rows:
        r["evidence_level"] = "TRADITIONAL_USE"
        r["is_clinical_evidence"] = False
        r["caveat"] = ("Traditional or historical use. This is not clinical "
                       "evidence that it works.")
    return rows
