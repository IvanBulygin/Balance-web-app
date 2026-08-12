"""Build the redistributable USDA seed used by the running app.

USDA FoodData Central is public domain (CC0), so the extracted values may be
stored in this repository and shipped with the service. Numbers are copied
verbatim from USDA's structured fields — nothing is derived or estimated.

    FDC_API_KEY=... python3 -m backend.knowledge.build_seed

Writes agent_site/data/usda_seed.json. The API key is never written to disk.
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "agent_site" / "data" / "usda_seed.json"
BASE = "https://api.nal.usda.gov/fdc/v1"

# Nutrients the app actually reasons about. Keeps the seed small enough to ship
# and load at startup instead of standing up a database for the prototype.
KEEP_NUTRIENTS = {
    "Magnesium, Mg", "Potassium, K", "Calcium, Ca", "Iron, Fe", "Zinc, Zn",
    "Sodium, Na", "Phosphorus, P", "Selenium, Se", "Copper, Cu",
    "Vitamin C, total ascorbic acid", "Vitamin D (D2 + D3)",
    "Vitamin E (alpha-tocopherol)", "Vitamin K (phylloquinone)",
    "Vitamin B-6", "Vitamin B-12", "Folate, total", "Niacin", "Riboflavin",
    "Thiamin", "Vitamin A, RAE",
    "Fiber, total dietary", "Protein", "Total lipid (fat)",
    "Carbohydrate, by difference", "Energy", "Sugars, total including NLEA",
    "Fatty acids, total polyunsaturated", "Fatty acids, total saturated",
}

# Whole foods, herbs and spices — the vocabulary the wellness app talks about.
FOODS = [
    "spinach raw", "kale raw", "broccoli raw", "swiss chard raw", "collards raw",
    "pumpkin seeds", "almonds", "cashews", "peanuts", "walnuts", "sunflower seeds",
    "chia seeds", "flaxseed", "sesame seeds",
    "black beans", "lentils raw", "chickpeas", "kidney beans", "soybeans",
    "quinoa raw", "oats raw", "brown rice raw", "buckwheat", "barley",
    "banana raw", "avocado raw", "blueberries raw", "strawberries raw",
    "raspberries raw", "orange raw", "apple raw", "kiwifruit raw", "papaya raw",
    "sweet potato raw", "potato raw", "beets raw", "carrots raw", "tomatoes raw",
    "garlic raw", "onions raw", "ginger root raw", "turmeric ground",
    "cinnamon ground", "black pepper", "cumin seed", "coriander seed",
    "rosemary dried", "thyme dried", "oregano dried", "basil dried",
    "peppermint fresh", "parsley raw", "cayenne pepper",
    "salmon raw", "sardines", "tuna raw", "eggs raw", "yogurt plain",
    "milk whole", "cheddar cheese", "tofu raw", "tempeh",
    "dark chocolate", "green tea brewed", "mushrooms white raw",
    "shiitake mushrooms raw", "seaweed kelp raw", "cocoa powder unsweetened",
]


def fetch(query: str, api_key: str) -> dict | None:
    url = (f"{BASE}/foods/search?query={urllib.parse.quote(query)}"
           f"&dataType={urllib.parse.quote('Foundation,SR Legacy')}"
           f"&pageSize=1&api_key={api_key}")
    req = urllib.request.Request(url, headers={"User-Agent": "BalanceAI-KB/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.loads(r.read())
    foods = payload.get("foods") or []
    return foods[0] if foods else None


def main() -> int:
    api_key = os.environ.get("FDC_API_KEY")
    if not api_key:
        raise SystemExit("Set FDC_API_KEY (free at https://fdc.nal.usda.gov/api-key-signup/)")

    out: list[dict] = []
    for q in FOODS:
        try:
            food = fetch(q, api_key)
        except Exception as exc:  # noqa: BLE001
            print(f"  !! {q}: {exc}")
            continue
        if not food:
            print(f"  -- {q}: no match")
            continue
        nutrients = [
            {"name": n["nutrientName"], "amount": n["value"],
             "unit": n["unitName"].lower(), "usda_nutrient_id": n.get("nutrientId")}
            for n in food.get("foodNutrients", [])
            if n.get("nutrientName") in KEEP_NUTRIENTS and n.get("value") is not None
        ]
        if not nutrients:
            continue
        out.append({
            "fdc_id": food["fdcId"],
            "description": food["description"],
            "data_type": food.get("dataType"),
            "query": q,
            "nutrients": nutrients,
        })
        print(f"  ok {food['fdcId']:>8}  {food['description'][:52]:<52} "
              f"{len(nutrients)} nutrients")
        time.sleep(0.15)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "source": "USDA FoodData Central",
        "license": "Public domain (CC0)",
        "attribution": "Data source: USDA FoodData Central, fdc.nal.usda.gov",
        "retrieved": time.strftime("%Y-%m-%d"),
        "note": "Values copied verbatim from USDA structured data, per 100 g.",
        "foods": out,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nWrote {OUT} — {len(out)} foods, "
          f"{sum(len(f['nutrients']) for f in out)} nutrient values")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
