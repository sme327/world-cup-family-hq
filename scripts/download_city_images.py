"""
Download two images per 2026 World Cup host city from Wikimedia Commons:
  1. The stadium itself
  2. A memorable city landmark

Usage:
    python scripts/download_city_images.py             # download all missing
    python scripts/download_city_images.py --overwrite # re-download everything
    python scripts/download_city_images.py --dry-run   # preview without saving
    python scripts/download_city_images.py --city seattle

Saves to: data/city_images/{city-slug}-stadium.jpg
          data/city_images/{city-slug}-landmark.jpg
Metadata: data/city_images/image_sources.csv
Manifest: data/city_image_manifest.csv

Requires: requests, Pillow
"""

import argparse
import csv
import io
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests
from PIL import Image

Image.MAX_IMAGE_PIXELS = None  # large source images are fine

BASE_DIR    = Path(__file__).parent.parent
IMG_DIR     = BASE_DIR / "data" / "city_images"
SOURCES_CSV = IMG_DIR / "image_sources.csv"
MISSING_TXT = IMG_DIR / "missing_images.txt"
MANIFEST_CSV = BASE_DIR / "data" / "city_image_manifest.csv"

TARGET_W, TARGET_H = 1200, 800
JPEG_QUALITY       = 85
REQUEST_TIMEOUT    = 40
RATE_LIMIT_S       = 8.0   # seconds between downloads
MAX_RETRIES        = 3
RATE_LIMIT_PAUSE   = 90    # seconds to wait on 429

HEADERS = {"User-Agent": "WorldCupFamilyHQ/1.0 (local family app; educational use)"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

COMMONS_API = "https://commons.wikimedia.org/w/api.php"

# ── Host cities: city_slug, display_name, country, stadium_name ──────────────
HOST_CITIES = [
    # slug              display_name                country   stadium
    ("new-york",        "New York / New Jersey",    "USA",    "MetLife Stadium"),
    ("dallas",          "Dallas / Arlington",       "USA",    "AT&T Stadium"),
    ("los-angeles",     "Los Angeles",              "USA",    "SoFi Stadium"),
    ("san-francisco",   "San Francisco Bay Area",   "USA",    "Levi's Stadium"),
    ("philadelphia",    "Philadelphia",             "USA",    "Lincoln Financial Field"),
    ("miami",           "Miami",                    "USA",    "Hard Rock Stadium"),
    ("kansas-city",     "Kansas City",              "USA",    "Arrowhead Stadium"),
    ("boston",          "Boston",                   "USA",    "Gillette Stadium"),
    ("atlanta",         "Atlanta",                  "USA",    "Mercedes-Benz Stadium"),
    ("seattle",         "Seattle",                  "USA",    "Lumen Field"),
    ("houston",         "Houston",                  "USA",    "NRG Stadium"),
    ("vancouver",       "Vancouver",                "Canada", "BC Place"),
    ("toronto",         "Toronto",                  "Canada", "BMO Field"),
    ("mexico-city",     "Mexico City",              "Mexico", "Estadio Azteca"),
    ("guadalajara",     "Guadalajara",              "Mexico", "Estadio Akron"),
    ("monterrey",       "Monterrey",                "Mexico", "Estadio BBVA"),
]

# ── Curated search terms: (stadium_searches, landmark_searches) ───────────────
CITY_IMAGES = {
    "new-york": (
        # stadium
        ["MetLife Stadium aerial New Jersey",
         "MetLife Stadium East Rutherford",
         "Giants Stadium New Jersey"],
        # landmark
        ["New York City skyline Manhattan",
         "Statue of Liberty New York harbor",
         "Brooklyn Bridge New York"],
    ),
    "dallas": (
        ["AT&T Stadium Arlington Texas interior",
         "AT&T Stadium Cowboys aerial",
         "AT&T Stadium Dallas Cowboys"],
        ["Dallas Texas skyline downtown",
         "Dallas Reunion Tower skyline",
         "Fort Worth Texas skyline"],
    ),
    "los-angeles": (
        ["SoFi Stadium Inglewood aerial",
         "SoFi Stadium Los Angeles",
         "SoFi Stadium exterior night"],
        ["Los Angeles skyline downtown",
         "Hollywood Sign Los Angeles hills",
         "Santa Monica Pier Los Angeles"],
    ),
    "san-francisco": (
        ["Levis Stadium Santa Clara California",
         "Levis Stadium football 49ers game",
         "Santa Clara stadium California aerial"],
        ["Golden Gate Bridge San Francisco",
         "San Francisco Bay skyline",
         "Alcatraz Island San Francisco"],
    ),
    "philadelphia": (
        ["Lincoln Financial Field Philadelphia aerial",
         "Lincoln Financial Field Eagles Philadelphia",
         "Philadelphia Eagles stadium"],
        ["Philadelphia skyline Delaware River night",
         "Philadelphia City Hall Penn statue skyline",
         "Independence Hall Philadelphia"],
    ),
    "miami": (
        ["Hard Rock Stadium Miami Gardens aerial",
         "Hard Rock Stadium exterior Miami",
         "Hard Rock Stadium Miami Dolphins"],
        ["Miami Beach South Beach aerial",
         "Miami skyline Brickell",
         "Art Deco Miami Beach"],
    ),
    "kansas-city": (
        ["Arrowhead Stadium Kansas City aerial",
         "Arrowhead Stadium Chiefs Kansas City",
         "Arrowhead Stadium exterior"],
        ["Kansas City skyline Missouri",
         "Kansas City Union Station",
         "Kansas City Plaza lights"],
    ),
    "boston": (
        ["Gillette Stadium Foxborough aerial",
         "Gillette Stadium New England Patriots",
         "Gillette Stadium exterior"],
        ["Boston skyline Massachusetts",
         "Boston Harbor sunset",
         "Fenway Park Boston"],
    ),
    "atlanta": (
        ["Mercedes-Benz Stadium Atlanta aerial",
         "Mercedes-Benz Stadium interior",
         "Atlanta Falcons stadium exterior"],
        ["Atlanta skyline Georgia peach",
         "Centennial Olympic Park Atlanta",
         "Atlanta Georgia skyline night"],
    ),
    "seattle": (
        ["Lumen Field Seattle aerial",
         "Lumen Field Seahawks stadium",
         "CenturyLink Field Seattle exterior"],
        ["Space Needle Seattle",
         "Seattle skyline Mount Rainier",
         "Pike Place Market Seattle"],
    ),
    "houston": (
        ["NRG Stadium Houston aerial",
         "NRG Stadium exterior Texas",
         "Houston Texans stadium NRG"],
        ["Houston skyline Texas",
         "Houston downtown skyline night",
         "NASA Johnson Space Center Houston"],
    ),
    "vancouver": (
        ["BC Place Stadium Vancouver aerial",
         "BC Place exterior Vancouver",
         "BC Place roof Vancouver"],
        ["Vancouver skyline British Columbia mountains",
         "Vancouver harbour mountains",
         "Stanley Park Vancouver"],
    ),
    "toronto": (
        ["BMO Field Toronto aerial",
         "BMO Field stadium Toronto",
         "Toronto FC BMO Field"],
        ["Toronto CN Tower skyline",
         "Toronto waterfront skyline",
         "Niagara Falls Ontario Canada"],
    ),
    "mexico-city": (
        ["Estadio Azteca Mexico City aerial",
         "Estadio Azteca exterior",
         "Azteca Stadium Mexico City"],
        ["Palacio de Bellas Artes Mexico City facade",
         "Mexico City skyline Torre Latinoamericana",
         "Zocalo Mexico City cathedral aerial"],
    ),
    "guadalajara": (
        ["Estadio Akron Guadalajara aerial",
         "Estadio Akron exterior Guadalajara",
         "Chivas Guadalajara stadium Akron"],
        ["Guadalajara Cathedral Jalisco Mexico",
         "Guadalajara historic center Mexico",
         "Tequila Jalisco Mexico agave"],
    ),
    "monterrey": (
        ["Estadio BBVA Monterrey aerial",
         "Estadio BBVA exterior Rayados",
         "BBVA Bancomer Stadium Monterrey"],
        ["Monterrey Mexico Cerro de la Silla mountain",
         "Monterrey skyline Macroplaza",
         "Macroplaza Monterrey Mexico"],
    ),
}


# ── Core utilities (mirrors download_country_images.py) ──────────────────────

def _get_with_retry(url: str, params: dict | None = None, allow_429_pause: bool = False) -> requests.Response | None:
    for attempt in range(MAX_RETRIES):
        try:
            resp = SESSION.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 429:
                if allow_429_pause:
                    print(f"    CDN rate-limited — pausing {RATE_LIMIT_PAUSE}s...")
                    time.sleep(RATE_LIMIT_PAUSE)
                    allow_429_pause = False
                    continue
                print("    CDN rate-limited (giving up for this image)")
                return None
            resp.raise_for_status()
            return resp
        except requests.exceptions.HTTPError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
            else:
                print(f"    HTTP error: {e}")
        except Exception as e:
            print(f"    Request error: {e}")
            return None
    return None


def search_commons(query: str) -> list[dict]:
    params = {
        "action": "query",
        "generator": "search",
        "gsrnamespace": "6",
        "gsrsearch": query,
        "gsrlimit": "15",
        "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata",
        "format": "json",
    }
    resp = _get_with_retry(COMMONS_API, params)
    if not resp:
        return []
    try:
        pages = resp.json().get("query", {}).get("pages", {})
    except Exception:
        return []

    results = []
    for page in pages.values():
        ii = page.get("imageinfo", [{}])[0]
        if ii.get("mime", "") not in ("image/jpeg", "image/png", "image/webp"):
            continue
        url = ii.get("url", "")
        if not url:
            continue
        meta = ii.get("extmetadata", {})
        w, h = ii.get("width", 0), ii.get("height", 0)
        results.append({
            "title":       page.get("title", ""),
            "url":         url,
            "width":       w,
            "height":      h,
            "author":      _meta_val(meta, "Artist"),
            "license":     _meta_val(meta, "LicenseShortName"),
            "description": _meta_val(meta, "ImageDescription"),
            "source_page": f"https://commons.wikimedia.org/wiki/{page.get('title','').replace(' ','_')}",
        })
    results = [r for r in results if r["width"] >= 400]
    results.sort(key=lambda r: (r["width"] < r["height"], -(r["width"] * r["height"])))
    return results


def _meta_val(meta: dict, key: str) -> str:
    return re.sub(r"<[^>]+>", "", meta.get(key, {}).get("value", "")).strip()[:300]


def download_image(file_title: str) -> bytes | None:
    filename = file_title.removeprefix("File:").replace(" ", "_")
    url = f"https://commons.wikimedia.org/wiki/Special:Redirect/file/{requests.utils.quote(filename)}?width=1280"
    resp = _get_with_retry(url, allow_429_pause=True)
    return resp.content if resp else None


def resize_and_save(image_bytes: bytes, out_path: Path) -> bool:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        orig_w, orig_h = img.size
        scale = max(TARGET_W / orig_w, TARGET_H / orig_h)
        new_w, new_h = int(orig_w * scale), int(orig_h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - TARGET_W) // 2
        top  = (new_h - TARGET_H) // 2
        img = img.crop((left, top, left + TARGET_W, top + TARGET_H))
        img.save(out_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
        return True
    except Exception as e:
        print(f"    Image processing error: {e}")
        return False


# Titles that look like signs, maps, diagrams, or logos rather than photos
_SKIP_PATTERNS = re.compile(
    r"(street.sign|road.sign|logo|diagram|map|chart|coat.of.arms|flag.of|emblem|icon|plaque|"
    r"locator|template|schematic|blueprint|badge|crest|seal\.svg|\.svg$)",
    re.IGNORECASE,
)


def try_download_one(queries: list[str], out_path: Path, label: str) -> dict | None:
    """Try each query in order until one succeeds. Returns metadata dict or None."""
    for query in queries:
        print(f"    [{label}] searching: '{query}'")
        if "dry-run" in label:
            return {"title": f"(dry-run) {query}", "url": "", "source_page": "", "author": "", "license": "", "description": f"Search: {query}"}
        hits = search_commons(query)
        # Filter out non-photo results
        hits = [h for h in hits if not _SKIP_PATTERNS.search(h["title"])]
        if not hits:
            time.sleep(1)
            continue
        best = hits[0]
        print(f"           Found: {best['title'][:65]}")
        img_bytes = download_image(best["title"])
        if img_bytes and resize_and_save(img_bytes, out_path):
            print(f"           ✓ Saved {out_path.name}  ({TARGET_W}×{TARGET_H})")
            return best
        time.sleep(RATE_LIMIT_S)
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--city",      help="Process one city slug only (e.g. seattle)")
    args = parser.parse_args()

    if not args.dry_run:
        IMG_DIR.mkdir(parents=True, exist_ok=True)

    target_cities = HOST_CITIES
    if args.city:
        target_cities = [c for c in HOST_CITIES if args.city.lower() in c[0]]
        if not target_cities:
            print(f"No city matching '{args.city}'")
            sys.exit(1)

    existing_rows: dict[str, dict] = {}
    if SOURCES_CSV.exists():
        with open(SOURCES_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing_rows[row["image_filename"]] = row

    all_results   = []
    manifest_rows = []
    downloaded = skipped = failed = 0
    missing_items = []

    for slug, display_name, country, stadium_name in target_cities:
        stadium_queries, landmark_queries = CITY_IMAGES[slug]
        stadium_file  = f"{slug}-stadium.jpg"
        landmark_file = f"{slug}-landmark.jpg"

        print(f"\n  ── {display_name} ({slug}) ──")

        # ── Stadium image ────────────────────────────────────────────────────
        stadium_path = IMG_DIR / stadium_file
        if stadium_path.exists() and not args.overwrite:
            print(f"    [stadium]  ↷ {stadium_file} already exists")
            skipped += 1
            all_results.append(existing_rows.get(stadium_file, {
                "city_slug": slug, "display_name": display_name, "country": country,
                "image_type": "stadium", "stadium_name": stadium_name,
                "image_filename": stadium_file, "image_url": "", "source_page": "",
                "author": "", "license": "", "description": "", "status": "existing",
            }))
        else:
            if args.dry_run:
                print(f"    [stadium]  would search: '{stadium_queries[0]}'")
                all_results.append({"city_slug": slug, "display_name": display_name,
                    "country": country, "image_type": "stadium", "stadium_name": stadium_name,
                    "image_filename": stadium_file, "image_url": "(dry-run)", "source_page": "",
                    "author": "", "license": "", "description": "", "status": "dry-run"})
                downloaded += 1
            else:
                meta = try_download_one(stadium_queries, stadium_path, "stadium")
                if meta:
                    downloaded += 1
                    all_results.append({
                        "city_slug": slug, "display_name": display_name, "country": country,
                        "image_type": "stadium", "stadium_name": stadium_name,
                        "image_filename": stadium_file,
                        "image_url": meta.get("url", ""),
                        "source_page": meta.get("source_page", ""),
                        "author": meta.get("author", ""),
                        "license": meta.get("license", ""),
                        "description": meta.get("description", ""),
                        "status": "downloaded",
                    })
                    time.sleep(RATE_LIMIT_S)
                else:
                    failed += 1
                    missing_items.append(f"{display_name} (stadium)")
                    all_results.append({
                        "city_slug": slug, "display_name": display_name, "country": country,
                        "image_type": "stadium", "stadium_name": stadium_name,
                        "image_filename": stadium_file, "image_url": "", "source_page": "",
                        "author": "", "license": "", "description": "", "status": "missing",
                    })

        # ── Landmark image ───────────────────────────────────────────────────
        landmark_path = IMG_DIR / landmark_file
        if landmark_path.exists() and not args.overwrite:
            print(f"    [landmark] ↷ {landmark_file} already exists")
            skipped += 1
            all_results.append(existing_rows.get(landmark_file, {
                "city_slug": slug, "display_name": display_name, "country": country,
                "image_type": "landmark", "stadium_name": stadium_name,
                "image_filename": landmark_file, "image_url": "", "source_page": "",
                "author": "", "license": "", "description": "", "status": "existing",
            }))
        else:
            if args.dry_run:
                print(f"    [landmark] would search: '{landmark_queries[0]}'")
                all_results.append({"city_slug": slug, "display_name": display_name,
                    "country": country, "image_type": "landmark", "stadium_name": stadium_name,
                    "image_filename": landmark_file, "image_url": "(dry-run)", "source_page": "",
                    "author": "", "license": "", "description": "", "status": "dry-run"})
                downloaded += 1
            else:
                meta = try_download_one(landmark_queries, landmark_path, "landmark")
                if meta:
                    downloaded += 1
                    all_results.append({
                        "city_slug": slug, "display_name": display_name, "country": country,
                        "image_type": "landmark", "stadium_name": stadium_name,
                        "image_filename": landmark_file,
                        "image_url": meta.get("url", ""),
                        "source_page": meta.get("source_page", ""),
                        "author": meta.get("author", ""),
                        "license": meta.get("license", ""),
                        "description": meta.get("description", ""),
                        "status": "downloaded",
                    })
                    time.sleep(RATE_LIMIT_S)
                else:
                    failed += 1
                    missing_items.append(f"{display_name} (landmark)")
                    all_results.append({
                        "city_slug": slug, "display_name": display_name, "country": country,
                        "image_type": "landmark", "stadium_name": stadium_name,
                        "image_filename": landmark_file, "image_url": "", "source_page": "",
                        "author": "", "license": "", "description": "", "status": "missing",
                    })

        # Manifest row covers both images for this city
        manifest_rows.append({
            "city_slug":     slug,
            "display_name":  display_name,
            "country":       country,
            "stadium_name":  stadium_name,
            "stadium_image": f"data/city_images/{stadium_file}",
            "landmark_image": f"data/city_images/{landmark_file}",
        })

    # ── Write outputs ─────────────────────────────────────────────────────────
    if not args.dry_run:
        SOURCE_FIELDS = ["city_slug", "display_name", "country", "image_type",
                         "stadium_name", "image_filename", "image_url", "source_page",
                         "author", "license", "description", "status"]
        with open(SOURCES_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SOURCE_FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(all_results)

        MANIFEST_FIELDS = ["city_slug", "display_name", "country", "stadium_name",
                           "stadium_image", "landmark_image"]
        with open(MANIFEST_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
            w.writeheader()
            w.writerows(manifest_rows)

        if missing_items:
            with open(MISSING_TXT, "w", encoding="utf-8") as f:
                f.write("\n".join(missing_items) + "\n")
        elif MISSING_TXT.exists():
            MISSING_TXT.unlink()

    print("\n" + "=" * 52)
    print("DOWNLOAD SUMMARY")
    print("=" * 52)
    print(f"  Cities processed : {len(target_cities)}")
    print(f"  Images target    : {len(target_cities) * 2}")
    print(f"  Downloaded       : {downloaded}")
    print(f"  Skipped (exist)  : {skipped}")
    print(f"  Failed           : {failed}")
    if missing_items:
        print(f"\n  Missing:")
        for m in missing_items:
            print(f"    - {m}")


if __name__ == "__main__":
    main()
