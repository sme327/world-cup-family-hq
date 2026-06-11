"""
Extract FIFA World Cup 2026 squad lists from official PDF.

Source PDF: https://fdp.fifa.org/assetspublic/ce281/pdf/SquadLists-English.pdf

To re-extract when FIFA releases updated squad lists:
  1. Download the latest PDF and save to data/SquadLists-English.pdf
  2. Run: python scripts/extract_rosters.py
  3. This overwrites data/world_cup_rosters.csv, world_cup_team_summary.csv,
     and world_cup_players_slugged.csv

Handles all column-layout variants observed across the 48-page PDF.
Requires: pdfplumber  (pip install pdfplumber)
"""

import re
import csv
import unicodedata
from datetime import datetime, date
from collections import Counter, defaultdict
from pathlib import Path
import pdfplumber
import warnings
warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).parent.parent
PDF_PATH = BASE_DIR / "data" / "SquadLists-English.pdf"
OUT_MASTER  = BASE_DIR / "data" / "world_cup_rosters.csv"
OUT_SUMMARY = BASE_DIR / "data" / "world_cup_team_summary.csv"
OUT_SLUGGED = BASE_DIR / "data" / "world_cup_players_slugged.csv"

POSITION_MAP = {"GK": "Goalkeeper", "DF": "Defender", "MF": "Midfielder", "FW": "Forward"}
KEY_HEADERS  = ["#", "POS", "FIRST NAME(S)", "LAST NAME(S)", "DOB", "CLUB"]


def find_col(header_row: list, label: str) -> int:
    for i, cell in enumerate(header_row):
        if cell and cell.strip().upper() == label.upper():
            return i
    return -1


def title_case_name(name: str) -> str:
    if not name:
        return name
    particles = {"de", "del", "da", "di", "van", "von", "der", "den", "al", "el",
                 "bin", "du", "dos", "das", "le", "la", "les", "e"}
    result = []
    for i, word in enumerate(name.split()):
        if "-" in word:
            result.append("-".join(p.capitalize() for p in word.split("-")))
        elif word.lower() in particles and i > 0:
            result.append(word.lower())
        else:
            result.append(word.capitalize())
    return " ".join(result)


def parse_date(dob_str: str) -> str:
    if not dob_str:
        return ""
    dob_str = dob_str.strip()
    try:
        return datetime.strptime(dob_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return dob_str


def fix_encoding(text: str) -> str:
    if not text:
        return text
    text = text.replace("\x00", "").strip()
    return unicodedata.normalize("NFC", text)


def get_cell(row: list, idx: int) -> str:
    if idx < 0 or idx >= len(row):
        return ""
    return fix_encoding(row[idx] or "")


def extract_team_from_page(page) -> tuple[str, list[dict]]:
    text = page.extract_text() or ""
    lines = text.split("\n")

    team_name = ""
    for line in lines[:10]:
        line = line.strip()
        m = re.match(r"^(.+?)\s*\([A-Z]{2,4}\)\s*$", line)
        if m and "FIFA" not in line and "SQUAD" not in line and "June" not in line and "#" not in line:
            team_name = fix_encoding(m.group(1).strip())
            break

    if not team_name:
        return "", []

    tables = page.extract_tables()
    if not tables:
        return team_name, []

    players = []
    for table in tables:
        if not table or len(table) < 2:
            continue

        header_row = None
        data_start = 0
        for i, row in enumerate(table):
            if row and any(c and c.strip() == "#" for c in row) and any(c and c.strip() == "POS" for c in row):
                header_row = row
                data_start = i + 1
                break

        if header_row is None:
            continue

        col = {key: find_col(header_row, key) for key in KEY_HEADERS}
        if col["LAST NAME(S)"] < 0:
            col["LAST NAME(S)"] = find_col(header_row, "LAST NAME")

        for row in table[data_start:]:
            if not row:
                continue
            shirt_raw = get_cell(row, col["#"])
            if not shirt_raw.isdigit():
                continue

            shirt_number = int(shirt_raw)
            pos_raw = get_cell(row, col["POS"])
            position = POSITION_MAP.get(pos_raw, pos_raw)

            first_names = get_cell(row, col["FIRST NAME(S)"])
            last_name_upper = get_cell(row, col["LAST NAME(S)"])
            last_name_cased = title_case_name(last_name_upper)

            if first_names and last_name_cased:
                player_name = f"{first_names} {last_name_cased}"
            elif first_names:
                player_name = first_names
            elif last_name_cased:
                player_name = last_name_cased
            else:
                pn_col = find_col(header_row, "PLAYER NAME")
                raw_pn = get_cell(row, pn_col)
                parts = raw_pn.split(" ", 1)
                player_name = (f"{parts[1]} {title_case_name(parts[0])}"
                               if len(parts) == 2 else title_case_name(raw_pn))

            birthdate = parse_date(get_cell(row, col["DOB"]))
            club = get_cell(row, col["CLUB"])

            players.append({
                "team": team_name,
                "shirt_number": shirt_number,
                "player_name": player_name,
                "position": position,
                "club": club,
                "birthdate": birthdate,
            })

    return team_name, players


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def main():
    if not PDF_PATH.exists():
        print(f"PDF not found at {PDF_PATH}")
        print("Download from: https://fdp.fifa.org/assetspublic/ce281/pdf/SquadLists-English.pdf")
        return

    all_players = []
    print(f"Extracting rosters from {PDF_PATH}...")

    with pdfplumber.open(PDF_PATH) as pdf:
        print(f"Total pages: {len(pdf.pages)}\n")
        for pg_num, page in enumerate(pdf.pages):
            team_name, players = extract_team_from_page(page)
            if team_name and players:
                all_players.extend(players)
                print(f"  Page {pg_num+1:2d}: {team_name} — {len(players)} players")
            else:
                print(f"  Page {pg_num+1:2d}: WARNING — no data extracted")

    FIELDS = ["team", "shirt_number", "player_name", "position", "club", "birthdate"]

    with open(OUT_MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(all_players)
    print(f"\n✓ {OUT_MASTER}  ({len(all_players)} rows)")

    # Team summary
    teams_map = defaultdict(list)
    for p in all_players:
        teams_map[p["team"]].append(p)

    today = date.today()
    SUMMARY_FIELDS = ["team", "player_count", "goalkeepers", "defenders",
                      "midfielders", "forwards", "average_age"]
    with open(OUT_SUMMARY, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        w.writeheader()
        for team, players in sorted(teams_map.items()):
            pc = Counter(p["position"] for p in players)
            ages = []
            for p in players:
                try:
                    bd = datetime.strptime(p["birthdate"], "%Y-%m-%d").date()
                    ages.append((today - bd).days / 365.25)
                except (ValueError, AttributeError):
                    pass
            w.writerow({
                "team": team,
                "player_count": len(players),
                "goalkeepers": pc.get("Goalkeeper", 0),
                "defenders": pc.get("Defender", 0),
                "midfielders": pc.get("Midfielder", 0),
                "forwards": pc.get("Forward", 0),
                "average_age": round(sum(ages) / len(ages), 1) if ages else "",
            })
    print(f"✓ {OUT_SUMMARY}")

    # Slugged
    SLUGGED_FIELDS = FIELDS + ["player_slug", "team_slug"]
    with open(OUT_SLUGGED, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SLUGGED_FIELDS)
        w.writeheader()
        for p in all_players:
            row = dict(p)
            row["player_slug"] = slugify(p["player_name"])
            row["team_slug"] = slugify(p["team"])
            w.writerow(row)
    print(f"✓ {OUT_SLUGGED}")

    # Quick validation summary
    print("\n--- Validation ---")
    print(f"Teams: {len(teams_map)}  |  Players: {len(all_players)}")
    bad_dates = [p for p in all_players if p["birthdate"] and not re.match(r"\d{4}-\d{2}-\d{2}$", p["birthdate"])]
    if bad_dates:
        print(f"⚠️  Birthdate issues: {len(bad_dates)}")
    else:
        print("✓ All birthdates parsed")
    missing_clubs = [p for p in all_players if not p["club"]]
    if missing_clubs:
        print(f"⚠️  Missing clubs: {len(missing_clubs)}")
    else:
        print("✓ All clubs present")


if __name__ == "__main__":
    main()
