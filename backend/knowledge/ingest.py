"""Bootstrap and ingestion CLI.

    python -m backend.knowledge.ingest init            # schema + vocabularies
    python -m backend.knowledge.ingest status          # sources and imports
    python -m backend.knowledge.ingest usda spinach kale
    python -m backend.knowledge.ingest pubmed "ginger nausea systematic review"

Controlled vocabularies are seeded here so outcomes, categories and preparation
forms can never be invented at query time.
"""

from __future__ import annotations

import sys

from . import ontology as onto
from . import registry
from .adapters import ADAPTERS, LicenceBlocked
from .db import Database, connect


def seed_vocabularies(db: Database) -> None:
    for name in onto.PLANT_PARTS:
        if not db.one("SELECT 1 AS x FROM plant_part WHERE name=?", (name,)):
            db.insert("INSERT INTO plant_part (name) VALUES (?)", (name,))
    for name, conc, note in onto.PREPARATION_FORMS:
        if not db.one("SELECT 1 AS x FROM preparation_form WHERE name=?", (name,)):
            db.insert("""INSERT INTO preparation_form
                         (name, is_concentrated, concentration_note) VALUES (?,?,?)""",
                      (name, conc, note))
    for name in onto.HEALTH_CATEGORIES:
        if not db.one("SELECT 1 AS x FROM health_category WHERE name=?", (name,)):
            db.insert("INSERT INTO health_category (name) VALUES (?)", (name,))
    for outcome, category in onto.HEALTH_OUTCOMES.items():
        if db.one("SELECT 1 AS x FROM health_outcome WHERE name=?", (outcome,)):
            continue
        cat = db.one("SELECT id FROM health_category WHERE name=?", (category,))
        db.insert("INSERT INTO health_outcome (name, category_id) VALUES (?,?)",
                  (outcome, cat["id"]))
    for name in onto.BIOLOGICAL_ACTIVITIES:
        if not db.one("SELECT 1 AS x FROM biological_activity WHERE name=?", (name,)):
            db.insert("INSERT INTO biological_activity (name) VALUES (?)", (name,))
    db.commit()


def init(db: Database) -> dict[str, int]:
    db.migrate()
    ids = registry.seed(db)
    seed_vocabularies(db)
    return ids


def adapter_for(db: Database, source_name: str):
    row = db.one("SELECT id FROM source_registry WHERE source_name=?", (source_name,))
    if not row:
        raise SystemExit(f"Unknown source {source_name!r}. Run `init` first.")
    return ADAPTERS[source_name](db, row["id"])


def status(db: Database) -> None:
    print("Sources:")
    for s in db.query("SELECT * FROM source_registry ORDER BY source_name"):
        state = "verified" if s["verified_at"] else "BLOCKED (licence unverified)"
        print(f"  {s['source_name']:<58} {s['license']:<42} {state}")
    print("\nImports:")
    rows = db.query("""SELECT si.*, sr.source_name FROM source_import si
                       JOIN source_registry sr ON sr.id = si.source_id
                       ORDER BY si.id DESC LIMIT 10""")
    if not rows:
        print("  (none yet)")
    for r in rows:
        print(f"  #{r['id']} {r['source_name']:<50} {r['status']:<8} "
              f"records={r['record_count']} {r['error_log'] or ''}")
    counts = {t: db.one(f"SELECT COUNT(*) AS n FROM {t}")["n"] for t in
              ("canonical_entity", "entity_alias", "food_nutrient", "compound",
               "entity_compound", "traditional_use", "study", "evidence_claim",
               "safety_record", "unresolved_entity")}
    print("\nCounts:")
    for k, v in counts.items():
        print(f"  {k:<22} {v}")


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "status"
    db = connect()
    if cmd == "init":
        ids = init(db)
        print(f"Initialised. {len(ids)} sources registered.")
        status(db)
        return 0
    if cmd == "status":
        status(db)
        return 0
    if cmd == "usda":
        terms = argv[2:] or ["spinach"]
        a = adapter_for(db, "USDA FoodData Central")
        print(a.run(queries=terms))
        return 0
    if cmd == "pubmed":
        a = adapter_for(db, "PubMed (NCBI E-utilities)")
        print(a.run(term=argv[2] if len(argv) > 2 else "ginger nausea"))
        return 0
    if cmd == "kew":
        try:
            adapter_for(db, "Kew Plants of the World Online").run()
        except LicenceBlocked as e:
            print(f"BLOCKED: {e}")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
