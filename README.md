# ⚽ Espinosa World Cup Family HQ

A local-first family World Cup clubhouse for the 2026 FIFA World Cup. Part pick'em tracker, part country encyclopedia, part passport adventure, part digital sticker book.

**Built for:** Shawn 🐘 · Jennie 🌻 · Daphne 🐿️ · Elliot 🦚 · Wyatt 🐯 · Grandpa By 🦅 · Grandma Cathy 🐼

> **Reusing this for a different tournament** (e.g. the 2027 Women's World Cup)? See
> [`docs/REUSING_FOR_A_NEW_TOURNAMENT.md`](docs/REUSING_FOR_A_NEW_TOURNAMENT.md) for a
> step-by-step porting checklist. This README documents the app as it stands for 2026.

---

## What It Does

- **Home** — clubhouse lobby: today's matches, the current knockout round, Country of the Day, family activity feed, favorites, and a compact leaderboard.
- **Schedule** — all 72 group-stage matches with inline pick buttons.
- **Matchups** — a Game Day Program per match (flags, family picks, country comparison, who to cheer for, players to watch, MLS/US connections, host city).
- **Knockout bracket** — a radial 32-team bracket on the Home page; picks per knockout match; automatic winner advancement.
- **Country Profiles** — National Geographic-style page for all 48 countries (animals, foods, landmarks, culture, soccer team). Opening one logs a discovery.
- **My Passport / Family Passport** — visual stamp collection tracking discovered / cheered / won countries, with continent progress and favorites.
- **Achievements** — individual and family achievements across Explorer, Passport, Picks, Winning, Continents, Family, and Hidden categories.
- **Standings / Leaderboard** — group tables and the family points race.
- **Host Cities / World Atlas / World Cup History** — exploration pages. Seattle (the family's home-area host city) is treated as special.
- **Admin** — score entry for group and knockout matches, plus data review tools (Shawn).

---

## Scoring

**Group stage** — each member picks one team per match (no draws are picked):

| Result | Points |
|--------|--------|
| Your team wins | 1.0 |
| Draw | 0.5 |
| Your team loses | 0.0 |

**Knockout stage** — points scale up by round (see `KO_ROUND_POINTS` in `services/ko_picks.py`):

| Round | Points |
|-------|--------|
| Round of 32 | 2 |
| Round of 16 | 3 |
| Quarterfinal | 4 |
| Semifinal / 3rd Place | 5 |
| Final | 8 |

No pick locking — picks can be changed any time.

---

## Tech Stack

| Layer | Tool |
|-------|------|
| UI | Streamlit ≥ 1.36 |
| Data | Pandas + SQLite |
| Maps / charts | Plotly |
| Images | Pillow (local curated photos, embedded as data URIs) |
| Runtime | Python 3.11+ |

Dependencies are in `requirements.txt`. No external match-data API is required — scores are entered by hand in Admin.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app (from the project folder)
cd world-cup-family-hq
streamlit run app.py
```

Opens at `http://localhost:8501`. Pick a family member on the welcome screen. The database (`data/worldcup.db`) is created automatically on first run from the CSV seed files.

---

## Data Model

**CSV files in `data/` are the source of truth.** `worldcup.db` is *generated* — never hand-edit it. Rebuild it from the CSVs with `scripts/reset_db.py`.

### Seed CSVs (source of truth)

| File | What it holds |
|------|---------------|
| `world_cup_2026_matches.csv` | 72 group-stage matches. Times stored in **ET**, displayed in **PT**. Source: FIFA/ESPN. |
| `knockout_matches.csv` | The 32-match knockout bracket (R32→Final + 3rd place), with `home_source`/`away_source` slot descriptors and `winner_to`/`loser_to` advancement wiring. |
| `teams.csv` | 48 teams — country facts + soccer info (`group_letter`, `confederation`, `fifa_ranking`, `coach`, `captain`, `capital`, `population`, `languages`, `fun_fact`, `animals`, `foods`, `landmarks`, `cheer_reasons`, `mls_connections`, `key_players`, …). |
| `country_metadata.csv` | **Canonical** passport/continent data: `country`, `continent`, `stamp_emoji`, `stamp_label`, `flag_fact`. All passport/matchup/profile code reads this. |
| `users.csv` | Family members: `id`, `name`, `avatar`, `theme_color`, `picks_only`. |
| `achievements.csv` | Achievement definitions: `achievement_id`, `name`, `description`, `category`, `scope`, `hidden`, `emoji`, `rule_type`, `threshold`. |
| `world_cup_rosters.csv` | 26 players per team (`team`, `shirt_number`, `player_name`, `position`, `club`, `birthdate`). |
| `world_cup_players_slugged.csv` | Same as above plus `player_slug` / `team_slug` (ready for future player pages). |
| `world_cup_team_summary.csv` | One row per team: position counts + average age. |
| `country_details.json` | Extended country content used by profile pages. |
| `*_image_manifest.csv` | Manifests mapping countries/cities to local curated images in `country_images/`, `country_card_images/`, `city_images/`. |

`picks_only` (in `users.csv`) marks members who take part in picks but not the full exploration/passport experience (Grandpa By, Grandma Cathy).

### Generated database

`data/worldcup.db` — tables: `teams`, `matches`, `knockout_matches`, `users`, `picks`, `knockout_live_picks`, `bracket_picks`, `bracket_submissions`, `bracket_lock`, `discoveries`, `player_discoveries`, `activity_log`, `user_achievements`, `family_achievements`.

---

## Backups & Deployment

The app can run **locally** or on **Streamlit Cloud**. Because Streamlit Cloud storage is ephemeral (the DB resets on sleep/wake), family-entered data is mirrored to CSV backups and auto-committed to GitHub.

### How backups work

- On every score save (group or knockout) and on manual Admin backup, `services/github_backup.py` writes the live tables out to `*_backup.csv` and commits them to the GitHub repo (`master`).
- Backup files: `picks_backup.csv`, `scores_backup.csv`, `ko_results_backup.csv`, `ko_live_picks_backup.csv`, `achievements_backup.csv`, `activity_backup.csv`.
- **GitHub is the durable source of truth for family-entered data.** A working copy on any machine may be an older checkout — `git pull` before trusting local backup CSVs.

Requires these secrets (in `.streamlit/secrets.toml` or the Streamlit Cloud dashboard, or as environment variables):

```toml
GITHUB_TOKEN = "ghp_..."                 # fine-grained token, Contents: read+write
GITHUB_REPO  = "sme327/world-cup-family-hq"
```

### Restoring after a reset

`scripts/reset_db.py` wipes and reseeds the DB, then automatically restores family data from the backup CSVs:

```bash
python scripts/reset_db.py          # backup picks → wipe → reseed → restore picks/scores/KO
python scripts/reset_db.py --wipe   # full wipe with NO restore (loses picks) — rarely wanted
```

`scripts/restore_picks.py` loads `picks_backup.csv`, `scores_backup.csv`, `ko_results_backup.csv`, `ko_live_picks_backup.csv`, `achievements_backup.csv`, and `activity_backup.csv` back into the DB, then calls `resync_bracket_advancement()` so knockout winners are re-linked into the next round.

---

## Knockout Bracket

- **Data:** `knockout_matches.csv` seeds 32 matches. R32 team slots are auto-filled from live group standings (`_sync_r32_from_standings` in `services/knockout.py`); later rounds fill in as winners are saved.
- **Advancement:** each row carries `winner_to_id` / `winner_to_slot` (and `loser_to_*` for SF→3rd place). Saving a result advances the winner automatically. `resync_bracket_advancement()` rebuilds all links from completed results (used after a restore).
- **Rendering:** `components/radial_bracket.py` draws the circular bracket as inline SVG. Flag sizing is round-aware and centralized at the top of that file (outer team flags shrink once the R32 round is complete; deeper-round winner flags grow toward the trophy).
- **Sourcing notes / match IDs:** see [`docs/knockout_sources.md`](docs/knockout_sources.md).

---

## Project Structure

```
world-cup-family-hq/
├── app.py                         # Entry point — navigation, global CSS, "playing as" user
├── requirements.txt
│
├── data/                          # Source-of-truth CSVs + generated worldcup.db + images
│
├── pages/
│   ├── home.py                    # Clubhouse lobby (matches, current KO round, activity, leaderboard)
│   ├── schedule.py                # Group-stage schedule with pick buttons
│   ├── standings.py               # Group tables
│   ├── matchup.py                 # Game Day Program per group match
│   ├── ko_matchup.py              # Game Day Program per knockout match
│   ├── bracket.py / bracket_picks.py  # Full bracket view + bracket prediction game
│   ├── pick_tracker.py            # Family Picks (by match / by person)
│   ├── leaderboard.py             # Points race
│   ├── country_profile.py         # National Geographic-style country page (logs discovery)
│   ├── passport_individual.py     # Personal passport + stamp collection
│   ├── passport_family.py         # Family stamp wall + comparisons
│   ├── achievements.py            # Achievement tracker
│   ├── discovery_race.py          # Exploration leaderboard
│   ├── host_cities.py             # 16 host-city explorer (Seattle is special)
│   ├── map.py                     # World Atlas
│   ├── world_cup_history.py       # World Cup history
│   └── admin.py                   # Score entry (group + KO), data review, manual backup
│
├── components/
│   ├── radial_bracket.py          # Circular knockout bracket (inline SVG)
│   └── bracket_board.py           # Bracket board layout
│
├── services/
│   ├── database.py                # SQLite schema, init, seeding from CSVs
│   ├── matches.py / teams.py      # Match + team queries
│   ├── picks.py / scoring.py      # Pick CRUD + leaderboard/result math
│   ├── knockout.py                # KO bracket data, R32 sync, advancement, resync
│   ├── ko_picks.py                # Knockout pick CRUD + KO scoring constants
│   ├── bracket_picks.py           # Full-bracket prediction game
│   ├── passport.py                # Discovery tracking, favorites, Country of the Day
│   ├── activity.py                # Activity feed read/write
│   ├── achievements.py            # Achievement check + award
│   ├── roster.py                  # Squad access (name mapping, featured players, MLS)
│   ├── player_cards.py            # Player card + modal rendering
│   ├── images.py                  # Local image lookup → data URIs
│   ├── explorer.py                # Exploration leaderboard math
│   ├── map_utils.py               # Plotly atlas figures + ISO maps
│   ├── espn.py                    # (Optional) ESPN data helpers
│   ├── github_backup.py           # Auto-commit backup CSVs to GitHub
│   └── time_utils.py              # ET → PT conversion + display formatting
│
├── scripts/
│   ├── reset_db.py                # Wipe + reseed + auto-restore
│   ├── restore_picks.py           # Restore family data from backup CSVs
│   ├── backup_picks.py            # Write backup CSVs from the DB
│   ├── extract_rosters.py         # Build roster CSVs
│   └── download_*.py              # Fetch/curate country + city images
│
└── docs/
    ├── knockout_sources.md        # Knockout data sourcing + match IDs
    └── REUSING_FOR_A_NEW_TOURNAMENT.md   # Porting guide (e.g. 2027 Women's World Cup)
```

---

## Times Are Pacific (PT)

Match times in the CSVs are stored in **ET**. The app converts everything to **PT** in `services/time_utils.py`. In summer 2026 (EDT → PDT) the offset is exactly **−3 hours**, and "today" is computed as `utcnow − 7h` (PDT). These offsets are **hardcoded** for North America 2026 — a tournament in another region needs them changed (see the porting guide).

---

## Design Principles

Full product decisions live in [`../CLAUDE.md`](../CLAUDE.md) (one level up). In short: this is a **family clubhouse and passport adventure**, not a sportsbook or analytics dashboard. Prefer exploration over statistics, big readable text and large emoji, cards over dense tables, and features that pass the "Kid Test" (could Daphne find it? could Elliot understand it? would Wyatt enjoy pressing it?).
