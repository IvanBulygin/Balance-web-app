"""Canonical ontology for the Food & Herbs Knowledge Base.

Controlled vocabularies live here rather than being invented at query time.
The evidence model is the important part: TRADITIONAL_USE is deliberately NOT
an evidence level — traditional use is stored in its own table and can never be
promoted into a clinical claim.
"""

from __future__ import annotations

import re
import unicodedata

# --------------------------------------------------------------- classification
CLASSIFICATIONS = (
    "FOOD", "HERB", "SPICE", "CULINARY_PLANT", "MEDICINAL_PLANT",
    "MUSHROOM", "BEVERAGE", "FOOD_INGREDIENT", "SUPPLEMENT",
)

PLANT_PARTS = ("root", "rhizome", "leaf", "seed", "fruit", "flower", "bark",
               "stem", "whole plant", "aerial parts", "peel", "bulb")

# --------------------------------------------------------------- preparation
# is_concentrated drives the guard that stops extract evidence being presented
# as advice about eating the food.
PREPARATION_FORMS = (
    ("whole_food_raw", 0, "Food eaten raw"),
    ("whole_food_cooked", 0, "Food as cooked"),
    ("dried_herb", 0, "Dried culinary/medicinal herb"),
    ("tea", 0, "Water infusion"),
    ("powder", 0, "Ground whole material"),
    ("tincture", 1, "Alcoholic extract"),
    ("standardised_extract", 1, "Extract standardised to a marker compound"),
    ("isolated_compound", 1, "Single purified compound"),
    ("supplement_capsule", 1, "Encapsulated concentrate"),
)
CONCENTRATED_FORMS = {n for n, c, _ in PREPARATION_FORMS if c}

# --------------------------------------------------------------- health model
HEALTH_CATEGORIES = (
    "digestive health", "cardiovascular health", "metabolic health",
    "immune function", "cognitive health", "bone health", "skin health",
    "sleep", "energy", "exercise recovery", "inflammation", "oxidative stress",
)

# outcome -> category. Outcomes are research endpoints, not diagnoses.
HEALTH_OUTCOMES = {
    "nausea": "digestive health",
    "constipation": "digestive health",
    "bloating": "digestive health",
    "indigestion": "digestive health",
    "blood pressure": "cardiovascular health",
    "LDL cholesterol": "cardiovascular health",
    "triglycerides": "cardiovascular health",
    "glycemic control": "metabolic health",
    "insulin sensitivity": "metabolic health",
    "body weight": "metabolic health",
    "C-reactive protein": "inflammation",
    "joint symptoms": "inflammation",
    "oxidative stress markers": "oxidative stress",
    "cognitive performance": "cognitive health",
    "sleep quality": "sleep",
    "upper respiratory infection": "immune function",
    "muscle soreness": "exercise recovery",
    "bone mineral density": "bone health",
}

BIOLOGICAL_ACTIVITIES = (
    "antioxidant activity", "anti-inflammatory activity", "antimicrobial activity",
    "antiemetic activity", "hypoglycaemic activity", "hypolipidaemic activity",
    "antiplatelet activity", "hepatoprotective activity",
)

# --------------------------------------------------------------- evidence
# Ordered weakest -> strongest. TRADITIONAL_USE is intentionally absent.
EVIDENCE_LEVELS = (
    "IN_VITRO", "ANIMAL", "MECHANISTIC", "OBSERVATIONAL_HUMAN",
    "CLINICAL_TRIAL", "SYSTEMATIC_REVIEW", "META_ANALYSIS", "CLINICAL_GUIDELINE",
)
EVIDENCE_RANK = {lvl: i for i, lvl in enumerate(EVIDENCE_LEVELS)}
HUMAN_LEVELS = {"OBSERVATIONAL_HUMAN", "CLINICAL_TRIAL", "SYSTEMATIC_REVIEW",
                "META_ANALYSIS", "CLINICAL_GUIDELINE"}

# Study design -> evidence level. The level comes from the design, never from
# how many papers happen to exist (spec §13).
DESIGN_TO_LEVEL = {
    "meta-analysis": "META_ANALYSIS",
    "systematic review": "SYSTEMATIC_REVIEW",
    "randomized controlled trial": "CLINICAL_TRIAL",
    "clinical trial": "CLINICAL_TRIAL",
    "cohort study": "OBSERVATIONAL_HUMAN",
    "case-control study": "OBSERVATIONAL_HUMAN",
    "cross-sectional study": "OBSERVATIONAL_HUMAN",
    "observational study": "OBSERVATIONAL_HUMAN",
    "animal study": "ANIMAL",
    "in vitro study": "IN_VITRO",
    "mechanistic study": "MECHANISTIC",
    "practice guideline": "CLINICAL_GUIDELINE",
}

# PubMed publication types -> our design vocabulary.
PUBTYPE_TO_DESIGN = {
    "Meta-Analysis": "meta-analysis",
    "Systematic Review": "systematic review",
    "Randomized Controlled Trial": "randomized controlled trial",
    "Clinical Trial": "clinical trial",
    "Controlled Clinical Trial": "clinical trial",
    "Observational Study": "observational study",
    "Practice Guideline": "practice guideline",
    "Guideline": "practice guideline",
}

CERTAINTY = ("very_low", "low", "moderate", "high")


def level_for_design(design: str) -> str:
    """Map a study design to an evidence level. Unknown designs stay lowest."""
    return DESIGN_TO_LEVEL.get((design or "").strip().lower(), "MECHANISTIC")


def is_human_evidence(level: str) -> bool:
    return level in HUMAN_LEVELS


# --------------------------------------------------------------- normalisation
_AUTHOR_SUFFIX = re.compile(
    r"\s+(?:L\.|Roscoe|Mill\.|DC\.|Linn\.?|Sm\.|Benth\.|Hook\.f\.|Kuntze|"
    r"Willd\.|Lam\.|Thunb\.|Vahl|Stokes|Blanco|Rosc\.)\s*$", re.I)
_PARENS = re.compile(r"\([^)]*\)")
_NONWORD = re.compile(r"[^a-z0-9]+")


def normalise_name(name: str) -> str:
    """Fold a name to a comparable key.

    Lowercases, strips accents, drops parentheticals and botanical author
    abbreviations ("Zingiber officinale Roscoe" -> "zingiber officinale"),
    then collapses to single spaces.
    """
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = _PARENS.sub(" ", s)
    s = _AUTHOR_SUFFIX.sub("", s.strip())
    s = _NONWORD.sub(" ", s.lower())
    return " ".join(s.split())


def canonical_id(kind: str, name: str) -> str:
    """Stable canonical id, e.g. ('plant', 'Zingiber officinale Roscoe')
    -> 'plant:zingiber_officinale'."""
    return f"{kind}:{normalise_name(name).replace(' ', '_')}"
