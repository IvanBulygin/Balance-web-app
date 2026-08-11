"""Integration tests for the Food & Herbs Knowledge Base.

Runs entirely offline against a temporary SQLite database — no network, no
API keys. The USDA fixture holds real FDC-shaped records so ingestion is
exercised without inventing nutrient values at query time.

    python3 -m backend.knowledge.tests.test_kb
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from .. import evidence as ev
from .. import ontology as onto
from .. import retrieval as R
from .. import tools as T
from ..adapters import (DrDukeAdapter, LicenceBlocked, NCCIHAdapter,
                        PubMedAdapter, USDAFoodDataCentralAdapter, KewAdapter)
from ..db import connect
from ..ingest import init
from ..resolution import resolve_or_create

PASS, FAIL = [], []


def check(desc: str, cond: bool) -> None:
    (PASS if cond else FAIL).append(desc)
    print(f"{'PASS' if cond else 'FAIL'} — {desc}")


# --------------------------------------------------------------- fixtures
# Shaped exactly like FoodData Central search results.
USDA_FIXTURE = [
    {"fdcId": 168390, "description": "Spinach, raw", "dataType": "SR Legacy",
     "foodNutrients": [
         {"nutrientId": 1090, "nutrientName": "Magnesium, Mg", "unitName": "MG", "value": 79.0},
         {"nutrientId": 1092, "nutrientName": "Potassium, K", "unitName": "MG", "value": 558.0},
         {"nutrientId": 1079, "nutrientName": "Fiber, total dietary", "unitName": "G", "value": 2.2}]},
    {"fdcId": 168421, "description": "Kale, raw", "dataType": "SR Legacy",
     "foodNutrients": [
         {"nutrientId": 1090, "nutrientName": "Magnesium, Mg", "unitName": "MG", "value": 47.0},
         {"nutrientId": 1092, "nutrientName": "Potassium, K", "unitName": "MG", "value": 491.0},
         {"nutrientId": 1079, "nutrientName": "Fiber, total dietary", "unitName": "G", "value": 4.1}]},
    {"fdcId": 169231, "description": "Pumpkin seeds, raw", "dataType": "SR Legacy",
     "foodNutrients": [
         {"nutrientId": 1090, "nutrientName": "Magnesium, Mg", "unitName": "MG", "value": 592.0}]},
]

DUKE_FIXTURE = [
    {"taxon": "Zingiber officinale Roscoe", "common_name": "Ginger", "duke_id": "duke-ginger",
     "chemical": "Gingerol", "activity": "antiemetic activity", "part": "rhizome",
     "ethnobotanical_use": "Traditionally used for digestive complaints and nausea"},
    {"taxon": "Curcuma longa", "common_name": "Turmeric", "duke_id": "duke-turmeric",
     "chemical": "Curcumin", "activity": "anti-inflammatory activity", "part": "rhizome",
     "ethnobotanical_use": "Traditionally used for joint discomfort"},
    {"taxon": "Allium sativum", "common_name": "Garlic", "duke_id": "duke-garlic",
     "chemical": "Allicin", "activity": "antimicrobial activity", "part": "bulb",
     "ethnobotanical_use": ""},
]

PUBMED_FIXTURE = [
    {"uid": "99000001", "title": "Ginger for nausea: a systematic review",
     "fulljournalname": "J Test Med", "pubdate": "2024 Mar",
     "pubtype": ["Systematic Review"], "articleids": [{"idtype": "doi", "value": "10.1000/x"}]},
    {"uid": "99000002", "title": "Ginger extract in an animal model of inflammation",
     "fulljournalname": "J Test Bio", "pubdate": "2023 Jan", "pubtype": [], "articleids": []},
]

NCCIH_FIXTURE = [
    {"entity": "Zingiber officinale", "kind": "adverse_effect",
     "text": "Mild side effects such as heartburn have been reported.",
     "url": "https://www.nccih.nih.gov/health/ginger"},
    {"entity": "Zingiber officinale", "interacts_with": "anticoagulants",
     "severity": "caution", "text": "May affect bleeding risk with blood thinners.",
     "url": "https://www.nccih.nih.gov/health/ginger"},
]


def build() -> tuple:
    tmp = Path(tempfile.mkdtemp()) / "kb_test.db"
    db = connect(str(tmp))
    ids = init(db)
    usda = USDAFoodDataCentralAdapter(db, ids["USDA FoodData Central"])
    usda.load([n for n in (usda.normalize(r) for r in USDA_FIXTURE) if n])
    duke = DrDukeAdapter(db, ids["Dr. Duke's Phytochemical and Ethnobotanical Databases"])
    duke.load([n for n in (duke.normalize(r) for r in DUKE_FIXTURE) if n])
    pm = PubMedAdapter(db, ids["PubMed (NCBI E-utilities)"])
    pm.load([n for n in (pm.normalize(r) for r in PUBMED_FIXTURE) if n])
    nc = NCCIHAdapter(db, ids["NCCIH (NIH)"])
    nc.load([n for n in (nc.normalize(r) for r in NCCIH_FIXTURE) if n])
    return db, ids


def main() -> int:
    db, ids = build()

    # ---------------------------------------------------- data integrity
    print("\n### Data integrity")
    dupes = db.query("""SELECT alias_norm, COUNT(DISTINCT entity_id) n
                        FROM entity_alias GROUP BY alias_norm HAVING n > 1""")
    check("no alias maps to two entities", not dupes)
    orphan = db.one("""SELECT COUNT(*) n FROM food_nutrient fn
                       LEFT JOIN source_record sr ON sr.id = fn.source_record_id
                       WHERE sr.id IS NULL""")["n"]
    check("every nutrient row has provenance", orphan == 0)
    check("USDA foods ingested", db.one("SELECT COUNT(*) n FROM food_nutrient")["n"] == 7)
    check("FDC ids mapped", bool(db.one(
        "SELECT 1 x FROM entity_source_id WHERE external_id='168390'")))

    # -------------------------------------------------- entity resolution
    print("\n### Entity resolution")
    base = T.get_food(db, "Zingiber officinale")
    check("'Zingiber officinale' resolves", base["found"])
    eid = base["entity"]["id"]
    for variant in ("ginger", "Ginger", "Zingiber officinale Roscoe", "zingiber officinale"):
        got = T.get_food(db, variant)
        check(f"{variant!r} resolves to the same entity",
              got["found"] and got["entity"]["id"] == eid)
    n_ginger = db.one("SELECT COUNT(*) n FROM canonical_entity WHERE id LIKE '%zingiber%'")["n"]
    check("no duplicate ginger entity created", n_ginger == 1)
    resolve_or_create(db, "Totally Unknown Plant XYZ", kind="plant")
    check("unknown name creates a new entity, not a bad merge",
          bool(db.one("SELECT 1 x FROM canonical_entity WHERE id LIKE '%totally_unknown%'")))

    # ------------------------------------------------------- nutrients
    print("\n### Nutrient retrieval (structured, not semantic)")
    mag = T.find_foods_by_nutrient(db, "magnesium")
    names = [r["food"] for r in mag["results"]]
    check("magnesium query returns foods", len(names) >= 3)
    check("ranked by amount (pumpkin seeds first)", names[0].startswith("Pumpkin"))
    check("values quoted verbatim from source", mag["results"][0]["amount"] == 592.0)
    check("nutrient results carry sources", bool(mag["sources"]))
    cmp_ = T.compare_foods(db, ["Spinach, raw", "Kale, raw"], ["Fiber"])
    fiber = next((v for k, v in cmp_["nutrients"].items() if "Fiber" in k), {})
    check("food comparison returns both foods", len(cmp_["foods"]) == 2)
    check("comparison keeps per-food values", len(fiber) == 2)

    # ------------------------------------------------------- compounds
    print("\n### Compounds")
    q = T.find_foods_containing_compound(db, "curcumin")
    check("compound lookup finds turmeric",
          any("Curcuma" in r["name"] for r in q["results"]))
    check("compound result warns it is not a health claim", "not a claim" in q["note"].lower())
    act = T.find_compounds_by_activity(db, "anti-inflammatory")
    check("activity lookup works", bool(act["results"]))
    check("activity is flagged as not a health benefit",
          "not a health benefit" in act["note"].lower())

    # ------------------------------- traditional use vs clinical evidence
    print("\n### Traditional use never becomes clinical evidence")
    trad = T.get_traditional_use(db, "ginger")
    check("traditional use is returned", bool(trad["traditional_uses"]))
    check("labelled TRADITIONAL_USE", trad["evidence_level"] == "TRADITIONAL_USE")
    check("explicitly not clinical evidence", trad["is_clinical_evidence"] is False)
    check("TRADITIONAL_USE is absent from evidence levels",
          "TRADITIONAL_USE" not in onto.EVIDENCE_LEVELS)
    leaked = db.one("SELECT COUNT(*) n FROM evidence_claim WHERE evidence_level='TRADITIONAL_USE'")["n"]
    check("no traditional row leaked into evidence_claim", leaked == 0)
    try:
        db.execute("""INSERT INTO evidence_claim
            (entity_id, health_outcome_id, preparation_form_id, evidence_level,
             direction, certainty, study_count, claim_text, source_record_id)
            VALUES (?,1,1,'TRADITIONAL_USE','SUPPORTS','high',1,'x',1)""", (eid,))
        db.commit()
        blocked = False
    except Exception:
        blocked = True
    check("database rejects TRADITIONAL_USE as an evidence level", blocked)

    # ------------------------------------------- evidence level integrity
    print("\n### Evidence levels come from design, not volume")
    check("animal design -> ANIMAL", onto.level_for_design("animal study") == "ANIMAL")
    check("in vitro -> IN_VITRO", onto.level_for_design("in vitro study") == "IN_VITRO")
    check("RCT -> CLINICAL_TRIAL",
          onto.level_for_design("randomized controlled trial") == "CLINICAL_TRIAL")
    check("animal evidence is not human", not onto.is_human_evidence("ANIMAL"))
    check("100 animal studies never reach 'high' certainty",
          ev.certainty_from("ANIMAL", 100, "SUPPORTS") == "very_low")
    check("one RCT stays 'low'", ev.certainty_from("CLINICAL_TRIAL", 1, "SUPPORTS") == "low")

    # ------------------------------------ claims: wording and dose/form
    print("\n### Claim safeguards")
    src = db.one("SELECT id FROM source_record LIMIT 1")["id"]
    try:
        ev.add_claim(db, entity_id=eid, outcome="nausea",
                     preparation_form="standardised_extract",
                     study_design="systematic review", direction="SUPPORTS",
                     claim_text="Ginger treats nausea", source_record_id=src)
        rejected = False
    except ValueError:
        rejected = True
    check("'treats' wording is rejected", rejected)

    extract_claim = ev.add_claim(
        db, entity_id=eid, outcome="nausea", preparation_form="standardised_extract",
        study_design="systematic review", direction="SUPPORTS",
        claim_text="Studied for nausea in trials of a standardised extract",
        source_record_id=src,
        study_ids=[db.one("SELECT id FROM study WHERE pmid='99000001'")["id"]])
    got = T.get_evidence_for_claim(db, extract_claim)["claim"]
    check("extract claim is level SYSTEMATIC_REVIEW",
          got["evidence_level"] == "SYSTEMATIC_REVIEW")
    check("extract claim does NOT apply to eating the food",
          got["applies_to_food"] is False)
    check("extract caveat is attached",
          any("not the same as eating" in c for c in got["caveats"]))

    animal_claim = ev.add_claim(
        db, entity_id=eid, outcome="C-reactive protein", preparation_form="isolated_compound",
        study_design="animal study", direction="SUPPORTS",
        claim_text="Examined in an animal model", source_record_id=src)
    ac = T.get_evidence_for_claim(db, animal_claim)["claim"]
    check("animal claim flags no human evidence",
          any("laboratory or animal" in c for c in ac["caveats"]))

    try:
        ev.add_claim(db, entity_id=eid, outcome="cures everything",
                     preparation_form="tea", study_design="clinical trial",
                     direction="SUPPORTS", claim_text="ok", source_record_id=src)
        vocab = False
    except ValueError:
        vocab = True
    check("invented health outcomes are rejected", vocab)

    # -------------------------------------------------- evidence ranking
    print("\n### Evidence ranking and filtering")
    all_ev = T.find_health_evidence(db, entity="ginger")
    check("evidence ranked strongest first",
          all_ev["claims"][0]["evidence_level"] == "SYSTEMATIC_REVIEW")
    human = T.find_health_evidence(db, entity="ginger", human_only=True)
    check("human_only filters out animal evidence",
          all(c["evidence_level"] in onto.HUMAN_LEVELS for c in human["claims"]))
    food_only = R.health_evidence(db, entity="ginger")
    check("food applicability exposed per claim",
          all("applies_to_food" in c for c in food_only))
    studies = T.find_studies(db, entity="ginger")
    check("studies carry PMID and URL",
          bool(studies["studies"]) and studies["studies"][0]["pmid"] == "99000001")

    # ------------------------------------------------------------ safety
    print("\n### Safety")
    saf = T.get_safety_information(db, "ginger")
    check("safety records returned", bool(saf["safety"]))
    check("absence of records is not called safe",
          "not evidence of safety" in saf["note"].lower())
    inter = T.get_interactions(db, "ginger")
    check("interactions returned", bool(inter["interactions"]))
    check("interactions marked non-exhaustive", "not proven safe" in inter["note"].lower())

    # ------------------------------------------------------- provenance
    print("\n### Provenance")
    prov = db.one("""SELECT sr.source_url, sr.retrieved_at, sr.license
                     FROM food_nutrient fn JOIN source_record sr ON sr.id=fn.source_record_id
                     LIMIT 1""")
    check("nutrient rows trace to a source URL", bool(prov and prov["source_url"]))
    check("licence recorded with the data", bool(prov and prov["license"]))

    # ------------------------------------------------------- licensing
    print("\n### Licensing enforcement")
    kew = KewAdapter(db, ids["Kew Plants of the World Online"])
    try:
        kew.run()
        blocked_kew = False
    except LicenceBlocked:
        blocked_kew = True
    check("Kew import is blocked while unverified", blocked_kew)
    check("Kew marked unverified in the registry", db.one(
        "SELECT verified_at FROM source_registry WHERE source_name LIKE 'Kew%'")["verified_at"] is None)

    # --------------------------------------------------- agent query set
    print("\n### Agent queries from the spec")
    r = T.knowledge_search(db, "What foods are high in magnesium?")
    check("Q: high in magnesium -> nutrient ranking",
          "nutrient_ranking" in r["intents"] and r["foods_by_nutrient"]["results"])
    r = T.knowledge_search(db, "Which foods contain quercetin?")
    check("Q: contains quercetin -> compound lookup", "compound_lookup" in r["intents"])
    r = T.knowledge_search(db, "What is ginger traditionally used for?")
    check("Q: traditionally used -> traditional use intent", "traditional_use" in r["intents"])
    check("Q: traditional answer is labelled non-clinical",
          r.get("traditional_use", {}).get("is_clinical_evidence") is False)
    r = T.knowledge_search(db, "What does human evidence say about ginger and nausea?")
    check("Q: human evidence -> evidence intent", "evidence" in r["intents"])
    check("Q: human evidence returns only human levels",
          all(c["evidence_level"] in onto.HUMAN_LEVELS for c in r["evidence"]["claims"]))
    r = T.knowledge_search(db, "Is ginger safe with blood thinners?")
    check("Q: safety -> safety intent", "safety" in r["intents"])
    r = T.knowledge_search(db, "Which foods provide the most potassium?")
    check("Q: most potassium -> ranking", bool(r.get("foods_by_nutrient", {}).get("results")))
    check("router states the response contract", "Do not add evidence" in r["contract"])
    r = T.knowledge_search(db, "What herbs have evidence for nausea?")
    check("Q: herbs with evidence for nausea", "evidence" in r["intents"])

    print(f"\n{'='*60}\nPASSED {len(PASS)}   FAILED {len(FAIL)}")
    for f in FAIL:
        print("  FAILED:", f)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
