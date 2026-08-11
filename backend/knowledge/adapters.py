"""Data source adapters.

Every source implements the same contract so new sources can be added without
touching the schema or the retrieval layer:

    discover()  -> dataset version / whether anything changed
    fetch()     -> raw records straight from the source
    normalize() -> plain dicts in our vocabulary
    load(db)    -> canonical rows + a source_record for every fact

An adapter must refuse to run when its licence is unverified (Kew).
"""

from __future__ import annotations

import csv
import io
import json
import os
import time
import urllib.parse
import urllib.request
import zipfile
from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional

from . import ontology as onto
from .db import Database
from .registry import is_ingestible


class LicenceBlocked(RuntimeError):
    """Raised when an adapter is asked to import from an unverified source."""


def _get(url: str, *, timeout: int = 30, headers: Optional[dict] = None) -> bytes:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "BalanceAI-KB/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


class DataSourceAdapter(ABC):
    source_name: str = ""

    def __init__(self, db: Database, source_id: int):
        self.db = db
        self.source_id = source_id

    def guard(self) -> None:
        if not is_ingestible(self.db, self.source_name):
            raise LicenceBlocked(
                f"{self.source_name}: licence not verified — refusing to import. "
                "Confirm terms and set verified_at in source_registry first."
            )

    def discover(self) -> dict:
        return {"dataset_version": "unknown"}

    @abstractmethod
    def fetch(self, **kw) -> Iterable[Any]: ...

    @abstractmethod
    def normalize(self, raw: Any) -> Optional[dict]: ...

    @abstractmethod
    def load(self, records: Iterable[dict], import_id: Optional[int] = None) -> int: ...

    def run(self, **kw) -> dict:
        """Full import with status tracking and failure recovery."""
        self.guard()
        version = self.discover().get("dataset_version", "")
        import_id = self.db.start_import(self.source_id, version)
        count = 0
        try:
            records = [n for n in (self.normalize(r) for r in self.fetch(**kw)) if n]
            count = self.load(records, import_id)
            self.db.finish_import(import_id, "success", records=count)
            return {"status": "success", "records": count, "import_id": import_id}
        except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
            self.db.finish_import(import_id, "failed", records=count, error=str(exc))
            raise


# ------------------------------------------------------------------ USDA
class USDAFoodDataCentralAdapter(DataSourceAdapter):
    """Food identity and nutrient composition.

    Numbers come from USDA's structured fields verbatim — no model ever
    interprets a nutrient value (spec §2).
    """

    source_name = "USDA FoodData Central"
    BASE = "https://api.nal.usda.gov/fdc/v1"

    def __init__(self, db, source_id, api_key: Optional[str] = None):
        super().__init__(db, source_id)
        self.api_key = api_key or os.environ.get("FDC_API_KEY") or "DEMO_KEY"

    def discover(self) -> dict:
        return {"dataset_version": f"fdc-api-{time.strftime('%Y-%m')}"}

    def fetch(self, queries: Iterable[str] = (), data_type: str = "Foundation,SR Legacy",
              page_size: int = 10, **kw) -> Iterable[dict]:
        """Search FDC for each query term and yield full food records."""
        for q in queries:
            url = (f"{self.BASE}/foods/search?query={urllib.parse.quote(q)}"
                   f"&dataType={urllib.parse.quote(data_type)}"
                   f"&pageSize={page_size}&api_key={self.api_key}")
            payload = json.loads(_get(url))
            if "foods" not in payload:
                raise RuntimeError(
                    f"FDC search failed for {q!r}: {payload.get('error', payload)}")
            for food in payload["foods"]:
                yield food
            time.sleep(0.2)   # stay well inside the hourly limit

    def fetch_bulk(self, zip_path: str, **kw) -> Iterable[dict]:
        """Alternative path: read an official FDC bulk CSV export."""
        with zipfile.ZipFile(zip_path) as z:
            name = next(n for n in z.namelist() if n.endswith("food.csv"))
            with z.open(name) as fh:
                for row in csv.DictReader(io.TextIOWrapper(fh, "utf-8")):
                    yield row

    def normalize(self, raw: dict) -> Optional[dict]:
        fdc_id = raw.get("fdcId") or raw.get("fdc_id")
        desc = raw.get("description") or raw.get("descrip")
        if not fdc_id or not desc:
            return None
        nutrients = []
        for n in raw.get("foodNutrients", []) or []:
            name = n.get("nutrientName") or n.get("name")
            amount = n.get("value", n.get("amount"))
            unit = n.get("unitName") or n.get("unitname")
            if not name or amount is None:
                continue
            nutrients.append({
                "name": name, "amount": float(amount),
                "unit": (unit or "").lower(),
                "usda_nutrient_id": n.get("nutrientId") or n.get("nutrientNumber"),
            })
        return {
            "external_id": str(fdc_id),
            "name": desc,
            "data_type": raw.get("dataType"),
            "category": raw.get("foodCategory"),
            "nutrients": nutrients,
            "raw": raw,
        }

    def load(self, records, import_id=None) -> int:
        from .resolution import resolve_or_create
        n = 0
        for rec in records:
            src = self.db.record_source(
                self.source_id, original_entity_id=rec["external_id"],
                source_url=f"https://fdc.nal.usda.gov/food-details/{rec['external_id']}",
                dataset_version="fdc", license="Public domain (CC0)",
                raw=rec["raw"], import_id=import_id)
            entity_id = resolve_or_create(
                self.db, rec["name"], kind="food",
                classifications=("FOOD",), source_id=self.source_id,
                external_id=rec["external_id"],
                external_url=f"https://fdc.nal.usda.gov/food-details/{rec['external_id']}")
            for nut in rec["nutrients"]:
                nid = _upsert_nutrient(self.db, nut["name"], nut["unit"],
                                       nut.get("usda_nutrient_id"))
                self.db.insert(
                    """INSERT INTO food_nutrient
                       (entity_id, nutrient_id, amount, per_amount, per_unit,
                        derivation, source_record_id)
                       VALUES (?,?,?,100,'g',?,?)""",
                    (entity_id, nid, nut["amount"], rec.get("data_type"), src))
            n += 1
        self.db.commit()
        return n


def _upsert_nutrient(db: Database, name: str, unit: str, usda_id=None) -> int:
    row = db.one("SELECT id FROM nutrient WHERE name=?", (name,))
    if row:
        return row["id"]
    return db.insert("INSERT INTO nutrient (name, unit, usda_nutrient_id) VALUES (?,?,?)",
                     (name, unit or "", int(usda_id) if str(usda_id or "").isdigit() else None))


# ------------------------------------------------------------ Dr. Duke
class DrDukeAdapter(DataSourceAdapter):
    """Plant → phytochemical → biological activity, plus ethnobotanical use.

    Ethnobotanical rows are TRADITIONAL USE. They are written to
    traditional_use and never to evidence_claim (spec §4).
    """

    source_name = "Dr. Duke's Phytochemical and Ethnobotanical Databases"

    def fetch(self, rows: Iterable[dict] = (), csv_path: str = "", **kw) -> Iterable[dict]:
        if csv_path:
            with open(csv_path, newline="", encoding="utf-8") as fh:
                yield from csv.DictReader(fh)
        else:
            yield from rows

    def normalize(self, raw: dict) -> Optional[dict]:
        plant = (raw.get("taxon") or raw.get("plant") or "").strip()
        if not plant:
            return None
        return {
            "plant": plant,
            "common_name": (raw.get("common_name") or "").strip(),
            "compound": (raw.get("chemical") or raw.get("compound") or "").strip(),
            "activity": (raw.get("activity") or "").strip(),
            "plant_part": (raw.get("part") or "").strip().lower(),
            "ethnobotanical_use": (raw.get("ethnobotanical_use") or raw.get("use") or "").strip(),
            "duke_id": (raw.get("duke_id") or plant).strip(),
            "raw": raw,
        }

    def load(self, records, import_id=None) -> int:
        from .resolution import resolve_or_create
        n = 0
        for rec in records:
            src = self.db.record_source(
                self.source_id, original_entity_id=rec["duke_id"],
                source_url="https://phytochem.nal.usda.gov/",
                dataset_version="duke-csv", license="CC0 1.0",
                raw=rec["raw"], import_id=import_id)
            entity_id = resolve_or_create(
                self.db, rec["plant"], kind="plant",
                classifications=("MEDICINAL_PLANT",), source_id=self.source_id,
                external_id=rec["duke_id"],
                aliases=[(rec["common_name"], "COMMON")] if rec["common_name"] else None)

            part_id = _upsert_named(self.db, "plant_part", rec["plant_part"]) \
                if rec["plant_part"] else None

            if rec["compound"]:
                cid = _upsert_compound(self.db, rec["compound"])
                self.db.insert(
                    """INSERT INTO entity_compound
                       (entity_id, compound_id, plant_part_id, source_record_id)
                       VALUES (?,?,?,?)""", (entity_id, cid, part_id, src))
                if rec["activity"]:
                    aid = _upsert_named(self.db, "biological_activity", rec["activity"])
                    self.db.execute(
                        """INSERT OR IGNORE INTO compound_activity
                           (compound_id, activity_id, source_record_id)
                           VALUES (?,?,?)""" if not self.db.is_postgres else
                        """INSERT INTO compound_activity
                           (compound_id, activity_id, source_record_id)
                           VALUES (?,?,?) ON CONFLICT DO NOTHING""",
                        (cid, aid, src))

            # Traditional use — its own table, by design.
            if rec["ethnobotanical_use"]:
                self.db.insert(
                    """INSERT INTO traditional_use
                       (entity_id, use_text, tradition, plant_part_id, source_record_id)
                       VALUES (?,?,?,?,?)""",
                    (entity_id, rec["ethnobotanical_use"], "ethnobotanical",
                     part_id, src))
            n += 1
        self.db.commit()
        return n


def _upsert_named(db: Database, table: str, name: str) -> int:
    name = name.strip()
    row = db.one(f"SELECT id FROM {table} WHERE name=?", (name,))
    if row:
        return row["id"]
    return db.insert(f"INSERT INTO {table} (name) VALUES (?)", (name,))


def _upsert_compound(db: Database, name: str) -> int:
    norm = onto.normalise_name(name)
    row = db.one("SELECT id FROM compound WHERE name_norm=?", (norm,))
    if row:
        return row["id"]
    return db.insert("INSERT INTO compound (name, name_norm) VALUES (?,?)",
                     (name.strip(), norm))


# ---------------------------------------------------------------- PubMed
class PubMedAdapter(DataSourceAdapter):
    """Citation metadata via E-utilities. Never full text.

    The evidence level is derived from the publication type, not from how many
    papers were found (spec §13).
    """

    source_name = "PubMed (NCBI E-utilities)"
    BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, db, source_id, api_key: Optional[str] = None):
        super().__init__(db, source_id)
        self.api_key = api_key or os.environ.get("NCBI_API_KEY") or ""

    def _key(self) -> str:
        return f"&api_key={self.api_key}" if self.api_key else ""

    def fetch(self, term: str = "", retmax: int = 20, **kw) -> Iterable[dict]:
        url = (f"{self.BASE}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(term)}"
               f"&retmax={retmax}&retmode=json{self._key()}")
        ids = json.loads(_get(url))["esearchresult"].get("idlist", [])
        if not ids:
            return
        time.sleep(0.35 if not self.api_key else 0.11)   # 3/s, or 10/s with a key
        surl = (f"{self.BASE}/esummary.fcgi?db=pubmed&id={','.join(ids)}"
                f"&retmode=json{self._key()}")
        result = json.loads(_get(surl)).get("result", {})
        for pmid in ids:
            rec = result.get(pmid)
            if rec:
                yield rec

    def normalize(self, raw: dict) -> Optional[dict]:
        pmid = raw.get("uid")
        title = raw.get("title")
        if not pmid or not title:
            return None
        pubtypes = raw.get("pubtype", []) or []
        design = next((onto.PUBTYPE_TO_DESIGN[p] for p in pubtypes
                       if p in onto.PUBTYPE_TO_DESIGN), "observational study")
        doi = next((i.get("value") for i in raw.get("articleids", [])
                    if i.get("idtype") == "doi"), None)
        return {
            "pmid": str(pmid), "title": title, "doi": doi,
            "journal": raw.get("fulljournalname") or raw.get("source"),
            "published_at": raw.get("pubdate"),
            "study_design": design,
            "raw": raw,
        }

    def load(self, records, import_id=None) -> int:
        n = 0
        for rec in records:
            if self.db.one("SELECT id FROM study WHERE pmid=?", (rec["pmid"],)):
                continue
            src = self.db.record_source(
                self.source_id, original_entity_id=rec["pmid"],
                source_url=f"https://pubmed.ncbi.nlm.nih.gov/{rec['pmid']}/",
                published_at=rec.get("published_at") or "",
                dataset_version="eutils", license="Metadata freely usable",
                raw=rec["raw"], import_id=import_id)
            self.db.insert(
                """INSERT INTO study
                   (pmid, doi, title, journal, published_at, study_design, source_record_id)
                   VALUES (?,?,?,?,?,?,?)""",
                (rec["pmid"], rec.get("doi"), rec["title"], rec.get("journal"),
                 rec.get("published_at"), rec["study_design"], src))
            n += 1
        self.db.commit()
        return n


# ---------------------------------------------------------------- NCCIH
class NCCIHAdapter(DataSourceAdapter):
    """Safety, cautions and interactions.

    NCCIH publishes no API, so entries are curated by hand with the page URL as
    provenance rather than scraped.
    """

    source_name = "NCCIH (NIH)"

    def fetch(self, entries: Iterable[dict] = (), **kw) -> Iterable[dict]:
        yield from entries

    def normalize(self, raw: dict) -> Optional[dict]:
        if not raw.get("entity") or not raw.get("text"):
            return None
        return {
            "entity": raw["entity"], "kind": raw.get("kind", "adverse_effect"),
            "text": raw["text"], "severity": raw.get("severity"),
            "url": raw.get("url", "https://www.nccih.nih.gov/"),
            "interacts_with": raw.get("interacts_with"),
            "preparation_form": raw.get("preparation_form"),
            "raw": raw,
        }

    def load(self, records, import_id=None) -> int:
        from .resolution import resolve_or_create
        n = 0
        for rec in records:
            src = self.db.record_source(
                self.source_id, original_entity_id=rec["entity"],
                source_url=rec["url"], dataset_version="nccih",
                license="Public domain (NIH)", raw=rec["raw"], import_id=import_id)
            entity_id = resolve_or_create(self.db, rec["entity"], kind="plant",
                                          source_id=self.source_id)
            form_id = None
            if rec.get("preparation_form"):
                r = self.db.one("SELECT id FROM preparation_form WHERE name=?",
                                (rec["preparation_form"],))
                form_id = r["id"] if r else None
            if rec.get("interacts_with"):
                self.db.insert(
                    """INSERT INTO interaction_record
                       (entity_id, interacts_with, severity, text, source_record_id)
                       VALUES (?,?,?,?,?)""",
                    (entity_id, rec["interacts_with"], rec.get("severity"),
                     rec["text"], src))
            else:
                self.db.insert(
                    """INSERT INTO safety_record
                       (entity_id, preparation_form_id, kind, text, severity, source_record_id)
                       VALUES (?,?,?,?,?,?)""",
                    (entity_id, form_id, rec["kind"], rec["text"],
                     rec.get("severity"), src))
            n += 1
        self.db.commit()
        return n


# ------------------------------------------------------------------ Kew
class KewAdapter(DataSourceAdapter):
    """Plant taxonomy and synonymy — BLOCKED pending licence confirmation.

    Kept as a working interface so the rest of the system is written against
    it, but `guard()` refuses to run while source_registry marks Kew
    unverified. Nothing from Kew is copied in the meantime.
    """

    source_name = "Kew Plants of the World Online"

    def fetch(self, **kw):
        raise LicenceBlocked(
            "Kew POWO: terms of use could not be confirmed (HTTP 403) and no "
            "public API is documented. Obtain written terms from Kew, then set "
            "verified_at in source_registry.")

    def normalize(self, raw): return None

    def load(self, records, import_id=None) -> int: return 0


ADAPTERS = {
    "USDA FoodData Central": USDAFoodDataCentralAdapter,
    "Dr. Duke's Phytochemical and Ethnobotanical Databases": DrDukeAdapter,
    "PubMed (NCBI E-utilities)": PubMedAdapter,
    "NCCIH (NIH)": NCCIHAdapter,
    "Kew Plants of the World Online": KewAdapter,
}
