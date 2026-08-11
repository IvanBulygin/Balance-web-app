-- Balance AI — Food & Herbs Knowledge Base
-- Portable DDL: runs on SQLite (dev/tests) and PostgreSQL (production).
-- Postgres-only extras (pgvector, GIN indexes) live in schema_pg.sql and are
-- applied on top when the target is PostgreSQL.
--
-- Design rules enforced structurally, not by prompting:
--   1. TRADITIONAL_USE is its own table. It is absent from the evidence_level
--      CHECK, so traditional use can never be stored as clinical evidence.
--   2. evidence_claim.preparation_form_id is NOT NULL, so evidence about a
--      standardised extract cannot be rendered as advice about a food.
--   3. Every fact row references source_record, so provenance is always
--      answerable.

-- ---------------------------------------------------------------- provenance
CREATE TABLE IF NOT EXISTS source_registry (
  id                    INTEGER PRIMARY KEY,
  source_name           TEXT NOT NULL UNIQUE,
  license               TEXT NOT NULL,
  commercial_use        TEXT NOT NULL,      -- yes | no | unknown
  redistribution_allowed TEXT NOT NULL,     -- yes | no | unknown
  attribution_required  TEXT NOT NULL,      -- yes | no | unknown
  api_available         TEXT NOT NULL,      -- yes | no | unknown
  download_available    TEXT NOT NULL,      -- yes | no | unknown
  terms_url             TEXT,
  rate_limit            TEXT,
  notes                 TEXT,
  verified_at           TEXT                -- NULL = licence NOT verified; do not ingest
);

CREATE TABLE IF NOT EXISTS source_import (
  id              INTEGER PRIMARY KEY,
  source_id       INTEGER NOT NULL REFERENCES source_registry(id),
  dataset_version TEXT,
  started_at      TEXT NOT NULL,
  finished_at     TEXT,
  status          TEXT NOT NULL,            -- running | success | failed | partial
  record_count    INTEGER DEFAULT 0,
  changed_count   INTEGER DEFAULT 0,
  error_log       TEXT
);

-- One row per record as it arrived from a source. Raw payload kept so an
-- import can be re-normalised without re-fetching.
CREATE TABLE IF NOT EXISTS source_record (
  id                 INTEGER PRIMARY KEY,
  source_id          INTEGER NOT NULL REFERENCES source_registry(id),
  import_id          INTEGER REFERENCES source_import(id),
  original_entity_id TEXT,                  -- the source's own identifier
  source_url         TEXT,
  retrieved_at       TEXT NOT NULL,
  published_at       TEXT,
  dataset_version    TEXT,
  license            TEXT,
  content_hash       TEXT,                  -- changed-record detection
  raw_payload        TEXT                   -- JSON
);
CREATE INDEX IF NOT EXISTS idx_source_record_orig
  ON source_record(source_id, original_entity_id);

-- ------------------------------------------------------------- entity core
CREATE TABLE IF NOT EXISTS canonical_entity (
  id              TEXT PRIMARY KEY,         -- 'plant:zingiber_officinale'
  primary_name    TEXT NOT NULL,
  scientific_name TEXT,
  rank            TEXT,                     -- species | genus | cultivar | n/a
  created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entity_alias (
  id         INTEGER PRIMARY KEY,
  entity_id  TEXT NOT NULL REFERENCES canonical_entity(id),
  alias      TEXT NOT NULL,
  alias_norm TEXT NOT NULL,                 -- lowercased, de-accented, author-stripped
  alias_type TEXT NOT NULL,                 -- COMMON|SCIENTIFIC|SYNONYM|FOOD_NAME|SPELLING
  lang       TEXT DEFAULT 'en',
  source_id  INTEGER REFERENCES source_registry(id)
);
CREATE INDEX IF NOT EXISTS idx_alias_norm ON entity_alias(alias_norm);
CREATE UNIQUE INDEX IF NOT EXISTS uq_alias
  ON entity_alias(entity_id, alias_norm, alias_type);

CREATE TABLE IF NOT EXISTS entity_classification (
  entity_id      TEXT NOT NULL REFERENCES canonical_entity(id),
  classification TEXT NOT NULL,             -- FOOD|HERB|SPICE|CULINARY_PLANT|
                                            -- MEDICINAL_PLANT|MUSHROOM|BEVERAGE|
                                            -- FOOD_INGREDIENT|SUPPLEMENT
  PRIMARY KEY (entity_id, classification)
);

CREATE TABLE IF NOT EXISTS entity_source_id (
  entity_id    TEXT NOT NULL REFERENCES canonical_entity(id),
  source_id    INTEGER NOT NULL REFERENCES source_registry(id),
  external_id  TEXT NOT NULL,               -- FDC ID, Duke plant ID, Kew taxon ID
  external_url TEXT,
  PRIMARY KEY (source_id, external_id)
);

-- Names that could not be resolved deterministically. Never auto-merged.
CREATE TABLE IF NOT EXISTS unresolved_entity (
  id           INTEGER PRIMARY KEY,
  raw_name     TEXT NOT NULL,
  source_id    INTEGER REFERENCES source_registry(id),
  external_id  TEXT,
  best_guess   TEXT REFERENCES canonical_entity(id),
  score        REAL,
  status       TEXT NOT NULL DEFAULT 'open', -- open | merged | rejected
  seen_at      TEXT NOT NULL
);

-- ------------------------------------------------------------- composition
CREATE TABLE IF NOT EXISTS nutrient (
  id               INTEGER PRIMARY KEY,
  name             TEXT NOT NULL UNIQUE,
  unit             TEXT NOT NULL,
  usda_nutrient_id INTEGER
);

CREATE TABLE IF NOT EXISTS food_nutrient (
  id               INTEGER PRIMARY KEY,
  entity_id        TEXT NOT NULL REFERENCES canonical_entity(id),
  nutrient_id      INTEGER NOT NULL REFERENCES nutrient(id),
  amount           REAL NOT NULL,
  per_amount       REAL NOT NULL DEFAULT 100,
  per_unit         TEXT NOT NULL DEFAULT 'g',
  data_points      INTEGER,
  derivation       TEXT,
  source_record_id INTEGER NOT NULL REFERENCES source_record(id)
);
CREATE INDEX IF NOT EXISTS idx_food_nutrient ON food_nutrient(nutrient_id, amount);
CREATE INDEX IF NOT EXISTS idx_food_nutrient_entity ON food_nutrient(entity_id);

CREATE TABLE IF NOT EXISTS plant_part (
  id   INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE               -- root|rhizome|leaf|seed|fruit|flower|bark
);

CREATE TABLE IF NOT EXISTS compound (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,
  name_norm   TEXT NOT NULL,
  pubchem_cid TEXT,
  class       TEXT
);
CREATE INDEX IF NOT EXISTS idx_compound_norm ON compound(name_norm);

CREATE TABLE IF NOT EXISTS entity_compound (
  id               INTEGER PRIMARY KEY,
  entity_id        TEXT NOT NULL REFERENCES canonical_entity(id),
  compound_id      INTEGER NOT NULL REFERENCES compound(id),
  plant_part_id    INTEGER REFERENCES plant_part(id),
  amount_low       REAL,
  amount_high      REAL,
  unit             TEXT,
  source_record_id INTEGER NOT NULL REFERENCES source_record(id)
);
CREATE INDEX IF NOT EXISTS idx_entity_compound ON entity_compound(compound_id);
CREATE INDEX IF NOT EXISTS idx_entity_compound_e ON entity_compound(entity_id);

-- A biological activity is NOT a health benefit. Kept deliberately separate
-- from health_outcome so the two can never be conflated.
CREATE TABLE IF NOT EXISTS biological_activity (
  id   INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS compound_activity (
  compound_id      INTEGER NOT NULL REFERENCES compound(id),
  activity_id      INTEGER NOT NULL REFERENCES biological_activity(id),
  source_record_id INTEGER NOT NULL REFERENCES source_record(id),
  PRIMARY KEY (compound_id, activity_id, source_record_id)
);

-- -------------------------------------------------------- dose / form (§12)
CREATE TABLE IF NOT EXISTS preparation_form (
  id                INTEGER PRIMARY KEY,
  name              TEXT NOT NULL UNIQUE,
  is_concentrated   INTEGER NOT NULL DEFAULT 0,  -- 1 = extract/isolate
  concentration_note TEXT
);

-- ------------------------------------------------------ health & evidence
CREATE TABLE IF NOT EXISTS health_category (
  id   INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS health_outcome (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,
  category_id INTEGER NOT NULL REFERENCES health_category(id)
);

CREATE TABLE IF NOT EXISTS study (
  id               INTEGER PRIMARY KEY,
  pmid             TEXT UNIQUE,
  doi              TEXT,
  title            TEXT NOT NULL,
  journal          TEXT,
  published_at     TEXT,
  study_design     TEXT NOT NULL,           -- drives evidence_level
  population       TEXT,
  sample_size      INTEGER,
  abstract         TEXT,                    -- stored only where licence permits
  source_record_id INTEGER NOT NULL REFERENCES source_record(id)
);
CREATE INDEX IF NOT EXISTS idx_study_pmid ON study(pmid);

-- Traditional / ethnobotanical use. Deliberately a DIFFERENT TABLE from
-- evidence_claim: there is no code path that promotes a row from here into
-- clinical evidence.
CREATE TABLE IF NOT EXISTS traditional_use (
  id                INTEGER PRIMARY KEY,
  entity_id         TEXT NOT NULL REFERENCES canonical_entity(id),
  health_outcome_id INTEGER REFERENCES health_outcome(id),
  use_text          TEXT NOT NULL,
  tradition         TEXT,
  plant_part_id     INTEGER REFERENCES plant_part(id),
  source_record_id  INTEGER NOT NULL REFERENCES source_record(id)
);
CREATE INDEX IF NOT EXISTS idx_trad_entity ON traditional_use(entity_id);

CREATE TABLE IF NOT EXISTS evidence_claim (
  id                  INTEGER PRIMARY KEY,
  entity_id           TEXT NOT NULL REFERENCES canonical_entity(id),
  health_outcome_id   INTEGER NOT NULL REFERENCES health_outcome(id),
  preparation_form_id INTEGER NOT NULL REFERENCES preparation_form(id),
  evidence_level      TEXT NOT NULL,
  direction           TEXT NOT NULL,        -- SUPPORTS|DOES_NOT_SUPPORT|INCONCLUSIVE
  effect_size         TEXT,
  certainty           TEXT NOT NULL,        -- very_low|low|moderate|high
  study_count         INTEGER NOT NULL DEFAULT 0,
  claim_text          TEXT NOT NULL,
  last_verified       TEXT,
  source_record_id    INTEGER NOT NULL REFERENCES source_record(id),
  CHECK (evidence_level IN (
    'IN_VITRO','ANIMAL','MECHANISTIC','OBSERVATIONAL_HUMAN',
    'CLINICAL_TRIAL','SYSTEMATIC_REVIEW','META_ANALYSIS','CLINICAL_GUIDELINE')),
  CHECK (direction IN ('SUPPORTS','DOES_NOT_SUPPORT','INCONCLUSIVE')),
  CHECK (certainty IN ('very_low','low','moderate','high'))
);
CREATE INDEX IF NOT EXISTS idx_claim_entity ON evidence_claim(entity_id);
CREATE INDEX IF NOT EXISTS idx_claim_outcome ON evidence_claim(health_outcome_id);

CREATE TABLE IF NOT EXISTS evidence_study (
  claim_id INTEGER NOT NULL REFERENCES evidence_claim(id),
  study_id INTEGER NOT NULL REFERENCES study(id),
  relation TEXT NOT NULL,                   -- SUPPORTS|DOES_NOT_SUPPORT|INCONCLUSIVE
  PRIMARY KEY (claim_id, study_id)
);

-- ---------------------------------------------------------------- safety
CREATE TABLE IF NOT EXISTS safety_record (
  id                  INTEGER PRIMARY KEY,
  entity_id           TEXT NOT NULL REFERENCES canonical_entity(id),
  preparation_form_id INTEGER REFERENCES preparation_form(id),
  kind                TEXT NOT NULL,        -- adverse_effect|contraindication|
                                            -- pregnancy|dose_concern|extract_concern
  text                TEXT NOT NULL,
  severity            TEXT,
  source_record_id    INTEGER NOT NULL REFERENCES source_record(id)
);
CREATE INDEX IF NOT EXISTS idx_safety_entity ON safety_record(entity_id);

CREATE TABLE IF NOT EXISTS interaction_record (
  id               INTEGER PRIMARY KEY,
  entity_id        TEXT NOT NULL REFERENCES canonical_entity(id),
  interacts_with   TEXT NOT NULL,           -- drug class or another entity
  severity         TEXT,
  mechanism        TEXT,
  text             TEXT NOT NULL,
  source_record_id INTEGER NOT NULL REFERENCES source_record(id)
);
CREATE INDEX IF NOT EXISTS idx_interaction_entity ON interaction_record(entity_id);

-- --------------------------------------------------- generic graph edges
-- Typed relationships for traversals the normalised tables don't cover
-- (e.g. HAS_SYNONYM, DERIVED_FROM). Every edge carries provenance.
CREATE TABLE IF NOT EXISTS entity_relationship (
  id               INTEGER PRIMARY KEY,
  from_id          TEXT NOT NULL REFERENCES canonical_entity(id),
  relation         TEXT NOT NULL,
  to_id            TEXT NOT NULL REFERENCES canonical_entity(id),
  source_record_id INTEGER NOT NULL REFERENCES source_record(id)
);
CREATE INDEX IF NOT EXISTS idx_rel_from ON entity_relationship(from_id, relation);
CREATE INDEX IF NOT EXISTS idx_rel_to ON entity_relationship(to_id, relation);

-- ------------------------------------------------------- semantic layer
-- Text only. Nutrient numbers are never embedded — they are queried in SQL.
CREATE TABLE IF NOT EXISTS embedding_text (
  id         INTEGER PRIMARY KEY,
  owner_kind TEXT NOT NULL,                 -- entity | study | traditional_use
  owner_id   TEXT NOT NULL,
  text       TEXT NOT NULL,
  model      TEXT,
  vector     TEXT                           -- JSON on SQLite; vector() on Postgres
);
CREATE INDEX IF NOT EXISTS idx_embed_owner ON embedding_text(owner_kind, owner_id);
