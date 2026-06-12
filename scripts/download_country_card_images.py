"""
Download country card images from Wikimedia Commons.

Reads data/country_card_image_targets.csv and downloads one image per unique
(country_slug, item_slug) pair into data/country_card_images/{country_slug}/{item_slug}.jpg

Saves download metadata to data/country_card_images/image_sources.csv and
records items that could not be found in data/country_card_images/missing_images.txt

Usage:
    python scripts/download_country_card_images.py              # download all missing
    python scripts/download_country_card_images.py --overwrite  # re-download everything
    python scripts/download_country_card_images.py --dry-run    # preview without saving
    python scripts/download_country_card_images.py --country mexico
    python scripts/download_country_card_images.py --section landmarks
    python scripts/download_country_card_images.py --limit 20   # stop after N downloads

Requires: requests, Pillow
"""

import argparse
import csv
import io
import re
import sys
import time
from pathlib import Path

import requests
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

BASE_DIR    = Path(__file__).parent.parent
TARGETS_CSV = BASE_DIR / "data" / "country_card_image_targets.csv"
IMG_BASE    = BASE_DIR / "data" / "country_card_images"
SOURCES_CSV = IMG_BASE / "image_sources.csv"
MISSING_TXT = IMG_BASE / "missing_images.txt"

TARGET_W, TARGET_H = 600, 400
JPEG_QUALITY       = 82
REQUEST_TIMEOUT    = 40
RATE_LIMIT_S       = 8.0
MAX_RETRIES        = 3
RATE_LIMIT_PAUSE   = 90

COMMONS_API = "https://commons.wikimedia.org/w/api.php"

HEADERS = {"User-Agent": "WorldCupFamilyHQ/1.0 (local family app; educational use)"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ── Filter out non-photo results ─────────────────────────────────────────────
_SKIP_PATTERNS = re.compile(
    r"(street.sign|road.sign|logo|diagram|map|chart|coat.of.arms|flag.of|emblem|"
    r"icon|plaque|locator|template|schematic|blueprint|badge|crest|\.svg$|"
    r"satellite|aster|false.color|infrared)",
    re.IGNORECASE,
)

# ── Section download priority (lower = earlier) ───────────────────────────────
_SECTION_ORDER = {"landmarks": 0, "animals": 1, "foods": 2, "cheer_reasons": 3}


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _get_with_retry(url: str, params=None, allow_429_pause: bool = False):
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


def _meta_val(meta: dict, key: str) -> str:
    return re.sub(r"<[^>]+>", "", meta.get(key, {}).get("value", "")).strip()[:300]


def search_commons(query: str) -> list[dict]:
    params = {
        "action":       "query",
        "generator":    "search",
        "gsrnamespace": "6",
        "gsrsearch":    query,
        "gsrlimit":     "15",
        "prop":         "imageinfo",
        "iiprop":       "url|mime|size|extmetadata",
        "format":       "json",
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
            "source_page": "https://commons.wikimedia.org/wiki/"
                           + page.get("title", "").replace(" ", "_"),
        })

    # Prefer landscape, filter tiny images, sort by pixel count descending
    results = [r for r in results if r["width"] >= 300]
    results = [r for r in results if not _SKIP_PATTERNS.search(r["title"])]
    results.sort(key=lambda r: (r["width"] < r["height"], -(r["width"] * r["height"])))
    return results


def download_image(file_title: str) -> bytes | None:
    filename = file_title.removeprefix("File:").replace(" ", "_")
    url = (
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/"
        + requests.utils.quote(filename)
        + "?width=1280"
    )
    resp = _get_with_retry(url, allow_429_pause=True)
    return resp.content if resp else None


def resize_and_save(image_bytes: bytes, out_path: Path) -> bool:
    try:
        img  = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        ow, oh = img.size
        scale  = max(TARGET_W / ow, TARGET_H / oh)
        nw, nh = int(ow * scale), int(oh * scale)
        img    = img.resize((nw, nh), Image.LANCZOS)
        left   = (nw - TARGET_W) // 2
        top    = (nh - TARGET_H) // 2
        img    = img.crop((left, top, left + TARGET_W, top + TARGET_H))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
        return True
    except Exception as e:
        print(f"    Image processing error: {e}")
        return False


def try_download_one(queries: list[str], out_path: Path, label: str) -> dict | None:
    """Try each query in order until one succeeds. Returns metadata dict or None."""
    for query in queries:
        print(f"    [{label}] → '{query}'")
        hits = search_commons(query)
        if not hits:
            time.sleep(1)
            continue
        best = hits[0]
        print(f"           Found: {best['title'][:65]}")
        img_bytes = download_image(best["title"])
        if img_bytes and resize_and_save(img_bytes, out_path):
            print(f"           ✓ Saved ({TARGET_W}×{TARGET_H})")
            return best
        time.sleep(RATE_LIMIT_S)
    return None


# ── Fallback query builder ────────────────────────────────────────────────────

def _fallback_queries(row: dict) -> list[str]:
    """Up to 3 queries: primary, then alternatives."""
    primary = row["search_query"]
    name    = row["item_name"]
    country = row["country"]
    sec     = row["section"]
    queries = [primary]

    # Secondary: name alone (without country)
    if country in primary:
        queries.append(name)
    # Tertiary: section-specific suffix
    if sec == "animals":
        queries.append(f"{name} wildlife photography")
    elif sec == "foods":
        queries.append(f"{name} traditional dish")
    elif sec == "landmarks":
        queries.append(f"{name} tourism")
    else:
        queries.append(f"{name}")

    # Deduplicate while preserving order
    seen_q: set[str] = set()
    result = []
    for q in queries:
        if q not in seen_q:
            seen_q.add(q)
            result.append(q)
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Download country card images")
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-download even if file already exists")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Preview without saving anything")
    parser.add_argument("--country",   help="Restrict to one country slug (e.g. mexico)")
    parser.add_argument("--section",   help="Restrict to one section (e.g. landmarks)")
    parser.add_argument("--limit",     type=int, default=0,
                        help="Stop after N successful downloads (0 = unlimited)")
    args = parser.parse_args()

    if not TARGETS_CSV.exists():
        print(f"ERROR: {TARGETS_CSV} not found. Run build_country_card_image_targets.py first.")
        sys.exit(1)

    with open(TARGETS_CSV, encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    # ── Build download queue: unique image_path from non-duplicate rows ────────
    # Sort so landmarks → animals → foods → cheer_reasons
    unique_rows: dict[str, dict] = {}
    for row in sorted(all_rows, key=lambda r: _SECTION_ORDER.get(r["section"], 9)):
        if row["is_duplicate"] == "yes":
            continue
        img_path = row["image_path"]
        if img_path not in unique_rows:
            unique_rows[img_path] = row

    # ── Apply filters ──────────────────────────────────────────────────────────
    queue: list[dict] = list(unique_rows.values())

    if args.country:
        queue = [r for r in queue if args.country.lower() in r["country_slug"]]
    if args.section:
        queue = [r for r in queue if r["section"] == args.section]

    print(f"Queue: {len(queue)} unique images to consider")
    if args.dry_run:
        print("(DRY RUN — nothing will be saved)")

    # ── Load existing sources ──────────────────────────────────────────────────
    existing_sources: dict[str, dict] = {}
    if SOURCES_CSV.exists():
        with open(SOURCES_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing_sources[row.get("image_path", "")] = row

    # ── Download loop ─────────────────────────────────────────────────────────
    downloaded = skipped = failed = 0
    new_sources: list[dict] = []
    tried_paths: set[str]   = set()
    success_paths: set[str] = set()
    missing_items: list[str] = []

    for row in queue:
        img_rel  = row["image_path"]
        out_path = BASE_DIR / img_rel

        print(f"\n  {row['country']} / {row['section']} / {row['item_name']}")

        if out_path.exists() and not args.overwrite:
            print(f"    ↷ already exists, skipping")
            skipped += 1
            success_paths.add(img_rel)
            existing_src = existing_sources.get(img_rel, {})
            new_sources.append(existing_src or {
                "image_path":   img_rel,
                "country":      row["country"],
                "country_slug": row["country_slug"],
                "section":      row["section"],
                "item_name":    row["item_name"],
                "item_slug":    row["item_slug"],
                "search_query": row["search_query"],
                "image_url":    "",
                "source_page":  "",
                "author":       "",
                "license":      "",
                "description":  "",
                "status":       "existing",
            })
            continue

        tried_paths.add(img_rel)

        if args.dry_run:
            queries = _fallback_queries(row)
            print(f"    would search: '{queries[0]}'")
            downloaded += 1
            continue

        queries = _fallback_queries(row)
        meta    = try_download_one(queries, out_path, row["section"])

        if meta:
            downloaded += 1
            success_paths.add(img_rel)
            new_sources.append({
                "image_path":   img_rel,
                "country":      row["country"],
                "country_slug": row["country_slug"],
                "section":      row["section"],
                "item_name":    row["item_name"],
                "item_slug":    row["item_slug"],
                "search_query": row["search_query"],
                "image_url":    meta.get("url", ""),
                "source_page":  meta.get("source_page", ""),
                "author":       meta.get("author", ""),
                "license":      meta.get("license", ""),
                "description":  meta.get("description", ""),
                "status":       "downloaded",
            })
            time.sleep(RATE_LIMIT_S)
        else:
            failed += 1
            missing_items.append(f"{row['country']} / {row['section']} / {row['item_name']}")
            new_sources.append({
                "image_path":   img_rel,
                "country":      row["country"],
                "country_slug": row["country_slug"],
                "section":      row["section"],
                "item_name":    row["item_name"],
                "item_slug":    row["item_slug"],
                "search_query": row["search_query"],
                "image_url":    "",
                "source_page":  "",
                "author":       "",
                "license":      "",
                "description":  "",
                "status":       "missing",
            })

        if args.limit and downloaded >= args.limit:
            print(f"\n  --limit {args.limit} reached, stopping.")
            break

    # ── Write outputs ──────────────────────────────────────────────────────────
    if not args.dry_run:
        IMG_BASE.mkdir(parents=True, exist_ok=True)

        SOURCE_FIELDS = [
            "image_path", "country", "country_slug", "section", "item_name", "item_slug",
            "search_query", "image_url", "source_page", "author", "license", "description", "status",
        ]

        # Merge new_sources with any existing entries not in this run
        merged: dict[str, dict] = {r.get("image_path", ""): r for r in new_sources}
        for k, v in existing_sources.items():
            if k and k not in merged:
                merged[k] = v

        with open(SOURCES_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SOURCE_FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(merged.values())

        # Update status in targets CSV
        status_map: dict[str, str] = {}
        for img_rel in success_paths:
            status_map[img_rel] = "downloaded"
        for img_rel in tried_paths - success_paths:
            status_map[img_rel] = "missing"

        for row in all_rows:
            img_rel = row["image_path"]
            if row["is_duplicate"] == "yes":
                canonical = img_rel  # same path, check disk
                row["status"] = "downloaded" if (BASE_DIR / canonical).exists() else "pending"
            elif img_rel in status_map:
                row["status"] = status_map[img_rel]
            elif (BASE_DIR / img_rel).exists():
                row["status"] = "downloaded"

        with open(TARGETS_CSV, "w", newline="", encoding="utf-8") as f:
            if all_rows:
                w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
                w.writeheader()
                w.writerows(all_rows)

        if missing_items:
            with open(MISSING_TXT, "w", encoding="utf-8") as f:
                f.write("\n".join(missing_items) + "\n")
        elif MISSING_TXT.exists():
            MISSING_TXT.unlink()

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 54)
    print("DOWNLOAD SUMMARY")
    print("=" * 54)
    print(f"  Queue processed : {len(queue)}")
    print(f"  Downloaded      : {downloaded}")
    print(f"  Skipped (exist) : {skipped}")
    print(f"  Failed          : {failed}")
    if missing_items:
        print(f"\n  Missing ({len(missing_items)}):")
        for m in missing_items[:20]:
            print(f"    - {m}")
        if len(missing_items) > 20:
            print(f"    ... and {len(missing_items) - 20} more (see {MISSING_TXT.name})")


if __name__ == "__main__":
    main()
