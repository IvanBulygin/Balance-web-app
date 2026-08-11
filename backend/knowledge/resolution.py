"""Entity resolution.

Deterministic and auditable. No model decides that "ginger" and
"Zingiber officinale Roscoe" are the same plant — the pipeline does, in a fixed
order, and anything it cannot settle goes to `unresolved_entity` for a human
rather than being merged on a guess.

Order:
  1. exact external id already mapped for this source
  2. exact normalised name match on any alias
  3. scientific-name match after stripping botanical author suffixes
  4. token-overlap similarity above a threshold
  5. otherwise: create a new entity, and if something was close, log it
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

from . import ontology as onto
from .db import Database, utcnow

SIMILARITY_THRESHOLD = 0.86
LOG_NEAR_MISS_ABOVE = 0.60


def _similarity(a: str, b: str) -> float:
    """Token-level Jaccard, with a small bonus for a shared leading token."""
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return 0.0
    j = len(ta & tb) / len(ta | tb)
    if a.split()[:1] == b.split()[:1]:
        j = min(1.0, j + 0.08)
    return j


def find_entity(db: Database, name: str, *, source_id: Optional[int] = None,
                external_id: Optional[str] = None) -> Optional[str]:
    """Return a canonical entity id for `name`, or None."""
    if external_id and source_id:
        row = db.one("SELECT entity_id FROM entity_source_id "
                     "WHERE source_id=? AND external_id=?", (source_id, external_id))
        if row:
            return row["entity_id"]

    norm = onto.normalise_name(name)
    if not norm:
        return None

    row = db.one("SELECT entity_id FROM entity_alias WHERE alias_norm=?", (norm,))
    if row:
        return row["entity_id"]

    row = db.one("SELECT id FROM canonical_entity WHERE lower(scientific_name)=?",
                 (norm,))
    if row:
        return row["id"]
    return None


def best_fuzzy(db: Database, norm: str) -> tuple[Optional[str], float]:
    """Closest existing entity by token overlap."""
    best_id, best_score = None, 0.0
    for row in db.query("SELECT entity_id, alias_norm FROM entity_alias"):
        s = _similarity(norm, row["alias_norm"])
        if s > best_score:
            best_id, best_score = row["entity_id"], s
    return best_id, best_score


def resolve_or_create(
    db: Database, name: str, *, kind: str = "plant",
    classifications: Sequence[str] = (), source_id: Optional[int] = None,
    external_id: Optional[str] = None, external_url: str = "",
    aliases: Optional[Iterable[tuple[str, str]]] = None,
    scientific_name: Optional[str] = None,
) -> str:
    """Resolve `name` to a canonical entity, creating one if needed."""
    entity_id = find_entity(db, name, source_id=source_id, external_id=external_id)
    norm = onto.normalise_name(name)

    if entity_id is None:
        cand, score = best_fuzzy(db, norm)
        if cand and score >= SIMILARITY_THRESHOLD:
            entity_id = cand
        else:
            entity_id = onto.canonical_id(kind, name)
            if not db.one("SELECT id FROM canonical_entity WHERE id=?", (entity_id,)):
                looks_scientific = len(norm.split()) == 2 and kind in ("plant", "herb")
                db.insert(
                    """INSERT INTO canonical_entity
                       (id, primary_name, scientific_name, rank, created_at)
                       VALUES (?,?,?,?,?)""",
                    (entity_id, name.strip(),
                     scientific_name or (name.strip() if looks_scientific else None),
                     "species" if looks_scientific else None, utcnow()))
            if cand and score >= LOG_NEAR_MISS_ABOVE:
                # Close but not close enough — a human decides, we do not.
                db.insert(
                    """INSERT INTO unresolved_entity
                       (raw_name, source_id, external_id, best_guess, score, seen_at)
                       VALUES (?,?,?,?,?,?)""",
                    (name, source_id, external_id, cand, score, utcnow()))

    _add_alias(db, entity_id, name, _alias_type(name), source_id)
    if scientific_name:
        _add_alias(db, entity_id, scientific_name, "SCIENTIFIC", source_id)
    for alias, atype in (aliases or ()):
        if alias:
            _add_alias(db, entity_id, alias, atype, source_id)

    for c in classifications:
        if c in onto.CLASSIFICATIONS:
            _add_classification(db, entity_id, c)

    if source_id and external_id:
        if not db.one("SELECT 1 AS x FROM entity_source_id "
                      "WHERE source_id=? AND external_id=?", (source_id, external_id)):
            db.insert(
                """INSERT INTO entity_source_id
                   (entity_id, source_id, external_id, external_url) VALUES (?,?,?,?)""",
                (entity_id, source_id, external_id, external_url or None))
    return entity_id


def _alias_type(name: str) -> str:
    norm = onto.normalise_name(name)
    return "SCIENTIFIC" if len(norm.split()) == 2 and norm[:1].isalpha() and \
        name.strip()[:1].isupper() else "COMMON"


def _add_alias(db: Database, entity_id: str, alias: str, atype: str,
               source_id: Optional[int]) -> None:
    norm = onto.normalise_name(alias)
    if not norm:
        return
    exists = db.one("SELECT 1 AS x FROM entity_alias "
                    "WHERE entity_id=? AND alias_norm=? AND alias_type=?",
                    (entity_id, norm, atype))
    if exists:
        return
    db.insert("""INSERT INTO entity_alias
                 (entity_id, alias, alias_norm, alias_type, source_id)
                 VALUES (?,?,?,?,?)""",
              (entity_id, alias.strip(), norm, atype, source_id))


def _add_classification(db: Database, entity_id: str, classification: str) -> None:
    if not db.one("SELECT 1 AS x FROM entity_classification "
                  "WHERE entity_id=? AND classification=?", (entity_id, classification)):
        db.insert("INSERT INTO entity_classification (entity_id, classification) "
                  "VALUES (?,?)", (entity_id, classification))


def link(db: Database, from_id: str, relation: str, to_id: str,
         source_record_id: int) -> None:
    """Add a typed graph edge with provenance."""
    db.insert("""INSERT INTO entity_relationship
                 (from_id, relation, to_id, source_record_id) VALUES (?,?,?,?)""",
              (from_id, relation, to_id, source_record_id))
