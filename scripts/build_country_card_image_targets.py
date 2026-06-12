"""
Build country_card_image_targets.csv from teams.csv.

For each country, extracts every item from: animals, foods, landmarks, cheer_reasons.
Generates search queries and flat target image paths.
Marks cross-section duplicates (same country + item_slug) so the download script
can skip re-downloading the same subject.

Usage:
    python scripts/build_country_card_image_targets.py

Output: data/country_card_image_targets.csv
"""

import csv
import re
import unicodedata
from pathlib import Path

BASE_DIR   = Path(__file__).parent.parent
TEAMS_CSV  = BASE_DIR / "data" / "teams.csv"
OUTPUT_CSV = BASE_DIR / "data" / "country_card_image_targets.csv"
IMG_BASE   = "data/country_card_images"

# Process in this order — first section to claim an item_slug wins
SECTIONS = ["animals", "foods", "landmarks", "cheer_reasons"]

# Broad emoji + variation-selector regex
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF"
    "\U00002702-\U000027B0"
    "\U0000FE00-\U0000FE0F"
    "☀-⛿"
    "⭐⭕▪-◾☔♈-♓]+",
    flags=re.UNICODE,
)


def _strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub("", text).strip()


def _country_slug(name: str) -> str:
    s = name.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("'", "").replace("’", "")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def _item_slug(name: str) -> str:
    s = _strip_emoji(name).lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", "_", s.strip())
    return s.strip("_")


def _search_query(section: str, item_name: str, country: str) -> str:
    if section == "animals":
        # Animal names are specific enough without country context
        return item_name
    # foods, landmarks, cheer_reasons → add country for disambiguation
    return f"{item_name} {country}"


def main():
    with open(TEAMS_CSV, encoding="utf-8") as f:
        teams = list(csv.DictReader(f))

    rows: list[dict] = []
    # Track (country_slug, item_slug) → first section that claimed it
    seen: dict[tuple[str, str], str] = {}

    for team in teams:
        cname = team.get("name", "").strip()
        if not cname:
            continue
        cslug = _country_slug(cname)

        for section in SECTIONS:
            raw = team.get(section, "")
            if not raw:
                continue

            items = [x.strip() for x in str(raw).split("|") if x.strip()]
            for item in items:
                clean_name = _strip_emoji(item).strip()
                if not clean_name:
                    continue

                islug = _item_slug(clean_name)
                if not islug:
                    continue

                key = (cslug, islug)
                if key in seen:
                    is_dup = True
                    first_section = seen[key]
                else:
                    is_dup = False
                    first_section = section
                    seen[key] = section

                rows.append({
                    "country":       cname,
                    "country_slug":  cslug,
                    "section":       section,
                    "item_name":     clean_name,
                    "item_slug":     islug,
                    "search_query":  _search_query(section, clean_name, cname),
                    "image_path":    f"{IMG_BASE}/{cslug}/{islug}.jpg",
                    "is_duplicate":  "yes" if is_dup else "no",
                    "first_section": first_section,
                    "status":        "pending",
                })

    FIELDS = [
        "country", "country_slug", "section", "item_name", "item_slug",
        "search_query", "image_path", "is_duplicate", "first_section", "status",
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    # ── Stats ──────────────────────────────────────────────────────────────────
    total   = len(rows)
    unique  = sum(1 for r in rows if r["is_duplicate"] == "no")
    dups    = total - unique
    by_sec  = {}
    for r in rows:
        by_sec[r["section"]] = by_sec.get(r["section"], 0) + 1

    print(f"\n✅  Wrote {total} rows → {OUTPUT_CSV.name}")
    print(f"    Unique images to download : {unique}")
    print(f"    Duplicates (reuse image)  : {dups}")
    print()
    for s in SECTIONS:
        n = by_sec.get(s, 0)
        print(f"    {s:<20s}: {n} items")


if __name__ == "__main__":
    main()
