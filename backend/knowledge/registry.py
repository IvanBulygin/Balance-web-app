"""Source registry — licence facts, verified before any ingestion.

`verified_at = None` means the licence could NOT be confirmed. The ingestion
runner refuses to import from an unverified source; that is the mechanism that
stops us quietly copying data we may have no right to redistribute.

Verification notes (August 2026):
  * USDA FoodData Central — USDA food composition data are public domain /
    CC0; attribution requested, not required. API needs a free data.gov key
    (the shared DEMO_KEY is rate limited); bulk downloads are published.
  * Dr. Duke's Phytochemical and Ethnobotanical Databases — released CC0 via
    USDA Ag Data Commons as a CSV archive. No official API exists; the web
    search UI is not an API and must not be scraped as one.
  * PubMed / NCBI E-utilities — metadata is freely usable; 3 requests/second,
    10 with an API key. Full text is a separate matter: only the PMC Open
    Access Subset is licensed for reuse, so we store metadata and abstracts
    only where the record permits, never full text.
  * NCCIH — NIH content is public domain unless marked with ©; credit NCCIH.
    There is no API, so this adapter is manual/curated rather than automated.
  * Kew POWO — NOT VERIFIED. The Kew terms-of-use page returned HTTP 403 and
    the secondary sources conflict (dataset metadata described as CC BY, which
    permits commercial use with attribution, while a third-party catalogue
    marks POWO commercial use as "No"). No publicly documented API was found.
    Left unverified on purpose: the adapter exists but refuses to import.
"""

from __future__ import annotations

from .db import Database, utcnow

SOURCES = [
    {
        "source_name": "USDA FoodData Central",
        "license": "Public domain (CC0)",
        "commercial_use": "yes",
        "redistribution_allowed": "yes",
        "attribution_required": "no",   # requested, not required
        "api_available": "yes",
        "download_available": "yes",
        "terms_url": "https://fdc.nal.usda.gov/api-guide",
        "rate_limit": "1000 requests/hour with a free data.gov key",
        "notes": "US Government work, not copyrighted. USDA asks to be credited "
                 "as the data source. Requires FDC_API_KEY; DEMO_KEY is shared "
                 "and rate limited.",
        "verified": True,
    },
    {
        "source_name": "Dr. Duke's Phytochemical and Ethnobotanical Databases",
        "license": "CC0 1.0 Universal (public domain dedication)",
        "commercial_use": "yes",
        "redistribution_allowed": "yes",
        "attribution_required": "no",
        "api_available": "no",
        "download_available": "yes",
        "terms_url": "https://phytochem.nal.usda.gov/",
        "rate_limit": "n/a (bulk CSV)",
        "notes": "Distributed as a CSV archive via USDA Ag Data Commons. No "
                 "official API — the public search UI must not be scraped in "
                 "place of one. Ethnobotanical rows are TRADITIONAL USE and are "
                 "loaded into traditional_use, never into evidence_claim.",
        "verified": True,
    },
    {
        "source_name": "PubMed (NCBI E-utilities)",
        "license": "Metadata freely usable; full text varies per article",
        "commercial_use": "yes",
        "redistribution_allowed": "unknown",   # per-article for abstracts/full text
        "attribution_required": "yes",
        "api_available": "yes",
        "download_available": "yes",
        "terms_url": "https://www.ncbi.nlm.nih.gov/home/about/policies/",
        "rate_limit": "3 requests/second, 10 with an API key",
        "notes": "We store citation metadata (PMID, DOI, title, journal, date, "
                 "publication types). Abstracts are stored only when the record "
                 "permits. Copyrighted full text is never downloaded; only the "
                 "PMC Open Access Subset is licensed for reuse.",
        "verified": True,
    },
    {
        "source_name": "NCCIH (NIH)",
        "license": "Public domain unless marked with a copyright symbol",
        "commercial_use": "yes",
        "redistribution_allowed": "yes",
        "attribution_required": "yes",
        "api_available": "no",
        "download_available": "no",
        "terms_url": "https://www.nccih.nih.gov/",
        "rate_limit": "n/a",
        "notes": "Authoritative for safety, cautions, interactions and "
                 "traditional-use-versus-evidence framing. No API, so entries "
                 "are curated by hand with the page URL as provenance. Content "
                 "marked (c) belongs to third parties and is excluded.",
        "verified": True,
    },
    {
        "source_name": "Kew Plants of the World Online",
        "license": "UNVERIFIED",
        "commercial_use": "unknown",
        "redistribution_allowed": "unknown",
        "attribution_required": "yes",
        "api_available": "unknown",
        "download_available": "unknown",
        "terms_url": "https://www.kew.org/science/collections-and-resources/data-and-digital/terms-of-use",
        "rate_limit": "unknown",
        "notes": "BLOCKED. Terms page returned HTTP 403 and secondary sources "
                 "conflict on commercial use. No publicly documented API found. "
                 "The adapter is a stub that refuses to import until Kew "
                 "confirms terms in writing. Taxonomy meanwhile comes from USDA "
                 "and Dr. Duke.",
        "verified": False,
    },
]


def seed(db: Database) -> dict[str, int]:
    """Insert the registry (idempotent) and return {source_name: id}."""
    ids: dict[str, int] = {}
    for s in SOURCES:
        existing = db.one("SELECT id FROM source_registry WHERE source_name=?",
                          (s["source_name"],))
        if existing:
            ids[s["source_name"]] = existing["id"]
            continue
        ids[s["source_name"]] = db.insert(
            """INSERT INTO source_registry
               (source_name, license, commercial_use, redistribution_allowed,
                attribution_required, api_available, download_available,
                terms_url, rate_limit, notes, verified_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (s["source_name"], s["license"], s["commercial_use"],
             s["redistribution_allowed"], s["attribution_required"],
             s["api_available"], s["download_available"], s["terms_url"],
             s["rate_limit"], s["notes"], utcnow() if s["verified"] else None),
        )
    db.commit()
    return ids


def is_ingestible(db: Database, source_name: str) -> bool:
    """A source may only be imported once its licence has been verified."""
    row = db.one("SELECT verified_at, redistribution_allowed FROM source_registry "
                 "WHERE source_name=?", (source_name,))
    return bool(row and row["verified_at"])
