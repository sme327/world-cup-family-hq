"""
Download one representative image per 2026 World Cup country from Wikimedia Commons.

Usage:
    python scripts/download_country_images.py            # download all missing
    python scripts/download_country_images.py --overwrite  # re-download everything
    python scripts/download_country_images.py --dry-run    # preview without saving

Images are saved to: data/country_images/{country_slug}.jpg
Metadata saved to:   data/country_images/image_sources.csv
Manifest saved to:   data/country_image_manifest.csv

Requires: requests, Pillow  (pip install requests Pillow)
"""

import argparse
import csv
import io
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
import requests
from PIL import Image
Image.MAX_IMAGE_PIXELS = None  # suppress decompression bomb warning for large source images

BASE_DIR = Path(__file__).parent.parent
IMG_DIR  = BASE_DIR / "data" / "country_images"
SOURCES_CSV   = IMG_DIR / "image_sources.csv"
MISSING_TXT   = IMG_DIR / "missing_images.txt"
MANIFEST_CSV  = BASE_DIR / "data" / "country_image_manifest.csv"

TARGET_W, TARGET_H = 1200, 800
JPEG_QUALITY = 85
REQUEST_TIMEOUT = 40
RATE_LIMIT_S = 8.0   # polite delay between countries (avoids CDN rate limits)
MAX_RETRIES = 3      # retry on non-429 errors
RATE_LIMIT_PAUSE = 90  # seconds to pause when 429 is received

HEADERS = {"User-Agent": "WorldCupFamilyHQ/1.0 (local family app; educational use)"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ── Country list ──────────────────────────────────────────────────────────────
COUNTRIES = [
    "Algeria", "Argentina", "Australia", "Austria", "Belgium",
    "Bosnia and Herzegovina", "Brazil", "Cabo Verde", "Canada", "Colombia",
    "Congo DR", "Croatia", "Curaçao", "Czechia", "Côte d'Ivoire",
    "Ecuador", "Egypt", "England", "France", "Germany", "Ghana", "Haiti",
    "IR Iran", "Iraq", "Japan", "Jordan", "Korea Republic", "Mexico",
    "Morocco", "Netherlands", "New Zealand", "Norway", "Panama", "Paraguay",
    "Portugal", "Qatar", "Saudi Arabia", "Scotland", "Senegal",
    "South Africa", "Spain", "Sweden", "Switzerland", "Tunisia",
    "Türkiye", "Uruguay", "USA", "Uzbekistan",
]

# ── Curated search terms per country (tried in order until one works) ─────────
SEARCH_TERMS = {
    "Algeria":                 ["Sahara Desert Algeria", "Casbah Algiers", "Tassili n'Ajjer"],
    "Argentina":               ["Iguazu Falls Argentina", "Buenos Aires obelisk", "Patagonia Argentina landscape"],
    "Australia":               ["Sydney Opera House", "Uluru rock Australia", "Great Barrier Reef Australia"],
    "Austria":                 ["Hallstatt Austria", "Vienna Schönbrunn Palace", "Austrian Alps landscape"],
    "Belgium":                 ["Grand Place Brussels", "Bruges Belgium canal", "Ghent Belgium"],
    "Bosnia and Herzegovina":  ["Stari Most Mostar bridge", "Sarajevo old town", "Plitvice Bosnia"],
    "Brazil":                  ["Christ the Redeemer Rio de Janeiro", "Iguazu Falls Brazil", "Amazon rainforest Brazil"],
    "Cabo Verde":              ["Pico do Fogo Cape Verde volcano", "Cabo Verde beach", "Sal island Cape Verde"],
    "Canada":                  ["Banff National Park Canada", "Niagara Falls Canada", "Toronto skyline"],
    "Colombia":                ["Cartagena de Indias Colombia", "Cocora Valley Colombia palms", "Bogotá Colombia"],
    "Congo DR":                ["Virunga National Park Congo", "Congo River", "Mountain gorilla Congo"],
    "Croatia":                 ["Plitvice Lakes Croatia", "Dubrovnik old town", "Diocletian's Palace Split Croatia"],
    "Curaçao":                 ["Willemstad Curaçao colorful buildings", "Curaçao beach", "Queen Emma Bridge Curaçao"],
    "Czechia":                 ["Prague Charles Bridge", "Prague Castle", "Czech Republic Cesky Krumlov"],
    "Côte d'Ivoire":           ["Yamoussoukro Basilica exterior aerial", "Abidjan Ivory Coast lagoon", "Grand Bassam Ivory Coast beach"],
    "Ecuador":                 ["Galápagos Islands Ecuador", "Quito Ecuador old town", "Cotopaxi volcano Ecuador"],
    "Egypt":                   ["Pyramids of Giza Egypt", "Great Sphinx Giza", "Nile River Egypt Luxor"],
    "England":                 ["Tower Bridge London river Thames", "Stonehenge England sunrise", "Westminster Palace London"],
    "France":                  ["Eiffel Tower Paris", "Mont Saint-Michel France", "Loire Valley France"],
    "Germany":                 ["Neuschwanstein Castle Germany", "Brandenburg Gate Berlin", "Cologne Cathedral"],
    "Ghana":                   ["Cape Coast Castle Ghana", "Kakum National Park Ghana", "Accra Ghana skyline"],
    "Haiti":                   ["Citadelle Laferrière Haiti", "Haiti Caribbean beach", "Sans-Souci Palace Haiti"],
    "IR Iran":                 ["Nasir al-Mulk Mosque Iran", "Persepolis Iran", "Isfahan Iran"],
    "Iraq":                    ["Ziggurat of Ur Iraq", "Baghdad Iraq Al-Mustansiriya", "Marshes of Mesopotamia Iraq"],
    "Japan":                   ["Mount Fuji Japan", "Fushimi Inari Japan", "Shibuya crossing Tokyo"],
    "Jordan":                  ["Petra Jordan", "Wadi Rum Jordan", "Dead Sea Jordan"],
    "Korea Republic":          ["Gyeongbokgung Palace Seoul", "Bukhansan National Park Korea", "Seoul South Korea skyline"],
    "Mexico":                  ["Chichen Itza Mexico", "Mexico City Zocalo", "Teotihuacan pyramids Mexico"],
    "Morocco":                 ["Marrakech Djemaa el-Fna square", "Sahara Desert Morocco dunes", "Fes medina Morocco"],
    "Netherlands":             ["Amsterdam canal Netherlands", "Windmills Kinderdijk Netherlands", "Tulip fields Netherlands"],
    "New Zealand":             ["Milford Sound New Zealand", "Hobbiton New Zealand", "Mount Cook New Zealand"],
    "Norway":                  ["Northern Lights Norway fjord", "Preikestolen cliff Norway", "Bergen wharf Norway Bryggen"],
    "Panama":                  ["Panama Canal", "San Blas Islands Panama", "Panama City skyline"],
    "Paraguay":                ["Jesuit missions ruins Paraguay", "Asuncion Paraguay skyline", "Trinidad Jesuit ruins Paraguay"],
    "Portugal":                ["Belém Tower Lisbon", "Douro Valley Portugal", "Sintra Portugal palace"],
    "Qatar":                   ["Doha skyline Qatar", "Museum of Islamic Art Doha", "Qatar desert landscape"],
    "Saudi Arabia":            ["Al-Ula Saudi Arabia Hegra", "Riyadh skyline Saudi Arabia", "Edge of the World Saudi Arabia"],
    "Scotland":                ["Edinburgh Castle Scotland", "Scottish Highlands landscape", "Loch Ness Scotland"],
    "Senegal":                 ["African Renaissance Monument Dakar", "Pink Lake Senegal Retba", "Dakar Senegal"],
    "South Africa":            ["Table Mountain Cape Town", "Kruger National Park South Africa", "Cape of Good Hope"],
    "Spain":                   ["Sagrada Familia Barcelona exterior facade", "Alhambra Granada Spain palace", "Park Güell Barcelona Gaudí"],
    "Sweden":                  ["Stockholm Sweden old town Gamla Stan", "Swedish Lapland Northern Lights", "Gothenburg Sweden"],
    "Switzerland":             ["Matterhorn Switzerland", "Lucerne bridge Switzerland", "Jungfrau Switzerland Alps"],
    "Tunisia":                 ["Amphitheatre El Jem Tunisia", "Tunis medina Tunisia", "Sidi Bou Said Tunisia"],
    "Türkiye":                 ["Hagia Sophia Istanbul", "Cappadocia hot air balloon Turkey", "Pamukkale Turkey travertine"],
    "Uruguay":                 ["Montevideo Uruguay rambla", "Colonia del Sacramento Uruguay", "Uruguay beaches Punta del Este"],
    "USA":                     ["Grand Canyon USA", "Statue of Liberty New York", "Yosemite National Park USA"],
    "Uzbekistan":              ["Registan Samarkand Uzbekistan", "Bukhara Uzbekistan", "Khiva Uzbekistan"],
}


# ── Slug helper ───────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("'", "").replace("'", "")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


# ── Wikimedia Commons API ─────────────────────────────────────────────────────
COMMONS_API = "https://commons.wikimedia.org/w/api.php"


def _get_with_retry(url: str, params: dict | None = None, allow_429_pause: bool = False) -> requests.Response | None:
    """GET with retry. On 429: pause RATE_LIMIT_PAUSE seconds then retry once."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = SESSION.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 429:
                if allow_429_pause:
                    print(f"    CDN rate-limited — pausing {RATE_LIMIT_PAUSE}s before retry...")
                    time.sleep(RATE_LIMIT_PAUSE)
                    allow_429_pause = False  # only pause once per call
                    continue
                print(f"    CDN rate-limited (giving up for this image)")
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
    """Search Wikimedia Commons. Returns candidates; download uses original URL (no thumb CDN)."""
    params = {
        "action": "query",
        "generator": "search",
        "gsrnamespace": "6",
        "gsrsearch": query,
        "gsrlimit": "15",
        "prop": "imageinfo",
        # No iiurlwidth — we want original URL only to avoid thumb CDN rate-limiting
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
        mime = ii.get("mime", "")
        if mime not in ("image/jpeg", "image/png", "image/webp"):
            continue
        url = ii.get("url", "")
        if not url:
            continue
        meta = ii.get("extmetadata", {})
        w = ii.get("width", 0)
        h = ii.get("height", 0)
        results.append({
            "title": page.get("title", ""),
            "url": url,
            "width": w,
            "height": h,
            "author": _meta_val(meta, "Artist"),
            "license": _meta_val(meta, "LicenseShortName"),
            "description": _meta_val(meta, "ImageDescription"),
            "source_page": f"https://commons.wikimedia.org/wiki/{page.get('title', '').replace(' ', '_')}",
        })
    # Prefer landscape and large images; skip tiny thumbnails (< 400px)
    results = [r for r in results if r["width"] >= 400]
    results.sort(key=lambda r: (r["width"] < r["height"], -(r["width"] * r["height"])))
    return results


def _meta_val(meta: dict, key: str) -> str:
    val = meta.get(key, {}).get("value", "")
    return re.sub(r"<[^>]+>", "", val).strip()[:300]


def download_image(file_title: str) -> bytes | None:
    """Download image via Commons Special:Redirect (avoids on-the-fly thumb generation).
    file_title: e.g. 'File:Iguazu_Cataratas2.jpg'
    """
    # Strip 'File:' prefix and spaces → underscores
    filename = file_title.removeprefix("File:").replace(" ", "_")
    url = f"https://commons.wikimedia.org/wiki/Special:Redirect/file/{requests.utils.quote(filename)}?width=1280"
    resp = _get_with_retry(url, allow_429_pause=True)
    return resp.content if resp else None


def resize_and_save(image_bytes: bytes, out_path: Path) -> bool:
    """Resize image to TARGET_W×TARGET_H (center-crop) and save as JPEG."""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        # Smart crop: scale so shorter side fills target, then center-crop
        orig_w, orig_h = img.size
        scale = max(TARGET_W / orig_w, TARGET_H / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - TARGET_W) // 2
        top  = (new_h - TARGET_H) // 2
        img = img.crop((left, top, left + TARGET_W, top + TARGET_H))
        img.save(out_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
        return True
    except Exception as e:
        print(f"    Image processing error: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Download country images from Wikimedia Commons")
    parser.add_argument("--overwrite", action="store_true", help="Re-download images that already exist")
    parser.add_argument("--dry-run",   action="store_true", help="Show what would be downloaded without saving")
    parser.add_argument("--country",   help="Download a single country only (for testing)")
    args = parser.parse_args()

    if not args.dry_run:
        IMG_DIR.mkdir(parents=True, exist_ok=True)

    target_countries = COUNTRIES
    if args.country:
        target_countries = [c for c in COUNTRIES if args.country.lower() in c.lower()]
        if not target_countries:
            print(f"No country matching '{args.country}'")
            sys.exit(1)

    # Load existing sources CSV
    existing_rows: dict[str, dict] = {}
    if SOURCES_CSV.exists():
        with open(SOURCES_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing_rows[row["country"]] = row

    results = []
    downloaded = skipped = failed = 0
    missing_countries = []

    for country in target_countries:
        slug = slugify(country)
        out_path = IMG_DIR / f"{slug}.jpg"

        if out_path.exists() and not args.overwrite:
            print(f"  ↷  {country} ({slug}.jpg) — already exists, skipping")
            skipped += 1
            # Keep existing metadata
            if country in existing_rows:
                results.append(existing_rows[country])
            else:
                results.append({
                    "country": country, "country_slug": slug,
                    "image_filename": f"{slug}.jpg", "image_url": "",
                    "source_page": "", "author": "", "license": "",
                    "description": "", "status": "existing",
                })
            continue

        search_queries = SEARCH_TERMS.get(country, [f"{country} landmark", f"{country} landscape"])
        found = False

        for query in search_queries:
            print(f"  ↓  {country} — searching: '{query}'")
            if args.dry_run:
                print(f"     [dry-run] would search and download")
                found = True
                results.append({
                    "country": country, "country_slug": slug,
                    "image_filename": f"{slug}.jpg", "image_url": "(dry-run)",
                    "source_page": "(dry-run)", "author": "", "license": "",
                    "description": f"Search: {query}", "status": "dry-run",
                })
                break

            hits = search_commons(query)
            if not hits:
                time.sleep(RATE_LIMIT_S)
                continue

            best = hits[0]
            print(f"     Found: {best['title'][:60]}")
            img_bytes = download_image(best["title"])
            if not img_bytes:
                time.sleep(RATE_LIMIT_S)
                continue

            if resize_and_save(img_bytes, out_path):
                print(f"     ✓ Saved {slug}.jpg  ({TARGET_W}×{TARGET_H})")
                results.append({
                    "country": country,
                    "country_slug": slug,
                    "image_filename": f"{slug}.jpg",
                    "image_url": best.get("url", best["source_page"]),
                    "source_page": best["source_page"],
                    "author": best["author"],
                    "license": best["license"],
                    "description": best["description"],
                    "status": "downloaded",
                })
                downloaded += 1
                found = True
                time.sleep(RATE_LIMIT_S)
                break

            time.sleep(RATE_LIMIT_S)

        if not found and not args.dry_run:
            print(f"     ✗ FAILED — no image found for {country}")
            failed += 1
            missing_countries.append(country)
            results.append({
                "country": country, "country_slug": slug,
                "image_filename": f"{slug}.jpg", "image_url": "",
                "source_page": "", "author": "", "license": "",
                "description": "", "status": "missing",
            })

    # Write outputs
    if not args.dry_run:
        FIELDS = ["country", "country_slug", "image_filename", "image_url",
                  "source_page", "author", "license", "description", "status"]
        with open(SOURCES_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(results)

        manifest_rows = [
            {"country": r["country"],
             "country_slug": r["country_slug"],
             "image_path": f"data/country_images/{r['image_filename']}"}
            for r in results
        ]
        with open(MANIFEST_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["country", "country_slug", "image_path"])
            w.writeheader()
            w.writerows(manifest_rows)

        if missing_countries:
            with open(MISSING_TXT, "w", encoding="utf-8") as f:
                f.write("\n".join(missing_countries) + "\n")
        elif MISSING_TXT.exists():
            MISSING_TXT.unlink()

    # Summary
    print("\n" + "=" * 50)
    print("DOWNLOAD SUMMARY")
    print("=" * 50)
    print(f"  Total countries : {len(target_countries)}")
    print(f"  Downloaded      : {downloaded}")
    print(f"  Skipped (exist) : {skipped}")
    print(f"  Failed          : {failed}")
    if missing_countries:
        print(f"\n  Missing:")
        for c in missing_countries:
            print(f"    - {c}")


if __name__ == "__main__":
    main()
