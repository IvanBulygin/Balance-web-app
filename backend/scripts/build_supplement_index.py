"""
Build a supplement taxonomy / link-out index from the extracted guide text.

Cross-references the canonical Examine supplement list
(``backend/data/examine_supplements.json`` — names + link-out URLs only)
against the ``.txt`` extracts in ``backend/data/pdfs/`` and records, per
supplement, which guides mention it plus its examine.com link-out URL.

Copyright note: this deliberately stores only supplement *names* (facts),
the public link-out *URL*, and the *source filename* — never the guides'
text. That matches the project rule of "link out, don't store full text".

Usage:
    python backend/scripts/build_supplement_index.py
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INDEX_FILE = DATA_DIR / "examine_supplements.json"   # canonical names + URLs
TXT_DIR = DATA_DIR / "pdfs"                           # extracted guide text
OUTPUT_FILE = DATA_DIR / "supplement_index.json"

# Surface forms that are ordinary English words / generic categories. For these
# we require a CASE-SENSITIVE match so "dim the lights" or a passing use of
# "fiber" doesn't get tagged. Prune/extend to taste.
FORCE_CASE_SENSITIVE = {
    "DIM", "GABA", "HMB", "DHA", "EPA", "EAA", "EFA", "NAC", "CBD",
    "DMAE", "DHEA", "Iron", "Fiber", "Dill", "Kanna", "Acetate",
    "B Vitamins", "Antioxidants", "Electrolytes", "Flavonoids",
    "Flavonols", "Flavanols", "Carotenoids", "Essential Fatty Acid",
}

# Alias map: canonical name -> extra surface forms found in real prose. This is
# what turns exact-string scanning into real normalization. Grow it as you see
# how the guides actually refer to things.
ALIASES = {
    "N-Acetylcysteine": ["NAC", "n-acetyl cysteine", "n-acetyl-l-cysteine"],
    "Epigallocatechin Gallate": ["EGCG"],
    "Vitamin C": ["ascorbic acid", "ascorbate"],
    "Vitamin D": ["cholecalciferol", "vitamin D3", "vitamin D2"],
    "Vitamin E": ["tocopherol", "alpha-tocopherol"],
    "Fish Oil": ["omega-3", "omega 3", "n-3 fatty acids"],
    "Docosahexaenoic Acid (DHA)": ["DHA"],
    "Eicosapentaenoic Acid (EPA)": ["EPA"],
    "Alpha-Lipoic Acid": ["ALA", "lipoic acid", "thioctic acid"],
    "Folic Acid (Vitamin B9)": ["folate", "vitamin B9"],
    "Biotin (Vitamin B7)": ["biotin", "vitamin B7"],
    "Cannabidiol (CBD)": ["CBD", "cannabidiol"],
    "CDP-Choline": ["citicoline"],
    "Beta-Alanine": ["beta alanine"],
    "L-Tyrosine": ["tyrosine"],
    "L-Carnitine": ["carnitine", "acetyl-l-carnitine", "ALCAR"],
}

# Map unicode apostrophes/quotes/dashes to ASCII so "Cat's Claw" (straight)
# matches a guide's "Cat's Claw" (curly), etc.
_APOSTROPHES = dict.fromkeys(map(ord, "‘’ʼ′`´"), "'")
_DASHES = dict.fromkeys(map(ord, "‐‑‒–—−"), "-")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return text.translate(_APOSTROPHES).translate(_DASHES)


def surface_forms(name: str) -> set[str]:
    """Strings to search for a canonical name: base + parenthetical + aliases."""
    forms: set[str] = set()
    m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", name)
    if m:
        base, paren = m.group(1).strip(), m.group(2).strip()
        forms.update(f for f in (base, paren) if f)
    else:
        forms.add(name.strip())
    forms.update(a.strip() for a in ALIASES.get(name, []) if a.strip())
    return forms


def is_case_sensitive(form: str) -> bool:
    # All-caps acronyms, very short tokens, or explicitly-listed generic words
    # match case-sensitively to cut false positives.
    return form in FORCE_CASE_SENSITIVE or form.isupper() or len(form) <= 4


def compile_matchers(supplements: list[dict]) -> dict[str, list[re.Pattern]]:
    matchers: dict[str, list[re.Pattern]] = {}
    for supp in supplements:
        name = supp["name"]
        compiled = []
        for form in surface_forms(name):
            pattern = r"(?<!\w)" + re.escape(normalize(form)) + r"(?!\w)"
            flags = 0 if is_case_sensitive(form) else re.IGNORECASE
            compiled.append(re.compile(pattern, flags))
        matchers[name] = compiled
    return matchers


def main() -> None:
    if not INDEX_FILE.exists():
        raise SystemExit(f"Canonical index not found: {INDEX_FILE}")
    supplements = json.loads(INDEX_FILE.read_text(encoding="utf-8")).get("supplements", [])
    if not supplements:
        raise SystemExit("Canonical index contained no supplements.")

    matchers = compile_matchers(supplements)
    url_by_name = {s["name"]: s["url"] for s in supplements}

    txt_files = sorted(TXT_DIR.glob("*.txt"))
    if not txt_files:
        raise SystemExit(f"No .txt extracts found in {TXT_DIR}")

    database: dict[str, dict] = {}
    for txt_file in txt_files:
        content = normalize(txt_file.read_text(encoding="utf-8", errors="replace"))
        for name, regexes in matchers.items():
            if any(rx.search(content) for rx in regexes):
                entry = database.setdefault(name, {
                    "canonical_name": name,
                    "reference_url": url_by_name.get(name, ""),  # link-out only
                    "found_in_guides": [],
                })
                if txt_file.name not in entry["found_in_guides"]:
                    entry["found_in_guides"].append(txt_file.name)

    output = {
        "system_description": "Supplement taxonomy / link-out index built from "
                              "guide text. Stores names + link-out URLs + source "
                              "filenames only (no guide text).",
        "supplement_count": len(database),
        "data": dict(sorted(database.items())),
    }
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Done. {len(database)} supplements matched across {len(txt_files)} "
          f"guide(s). Wrote {OUTPUT_FILE.relative_to(DATA_DIR.parent.parent)}")


if __name__ == "__main__":
    main()
