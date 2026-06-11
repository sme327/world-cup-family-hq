# ⚽ Espinosa World Cup Family HQ

A local-first family World Cup clubhouse for the 2026 FIFA World Cup. Part pick'em tracker, part country encyclopedia, part passport adventure, part digital sticker book.

**Built for:** Shawn 🐘 · Jennie 🌻 · Daphne 🦊 · Elliot 🐰 · Wyatt 🦖

---

## What It Does

- **Today's Matches** — see what's playing right now and tomorrow
- **Make Picks** — each family member picks a team for every match
- **Game Day Program** — deep-dive matchup page per match (flags, picks, country compare, who to cheer for, players, MLS connections, host city)
- **Country Profiles** — National Geographic-style page for all 48 countries (animals, foods, landmarks, soccer team)
- **Family Passport** — visual stamp collection tracking discovered / cheered / won countries
- **My Passport** — individual passport with continent progress and favorites
- **Achievements** — 33+ individual and family achievements
- **Host Cities** — explorer for all 16 World Cup venues across USA, Canada, and Mexico
- **Activity Feed** — live family activity log on the home page
- **Admin** — score entry and data review tools for Shawn

---

## Scoring

| Result | Points |
|--------|--------|
| Your team wins | 1.0 |
| Draw | 0.5 |
| Your team loses | 0.0 |

No pick locking — picks can be changed any time.

---

## Tech Stack

| Layer | Tool |
|-------|------|
| UI | Streamlit 1.36+ |
| Data | Pandas + SQLite |
| Maps | Plotly (planned) |
| Runtime | Python 3.11+ |

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
cd world-cup-family-hq
streamlit run app.py
```

The database (`data/worldcup.db`) is created automatically on first run from the CSV seed files.

To reset all picks, discoveries, and activity back to a clean state:

```bash
python scripts/reset_db.py
```

---

## Project Structure

```
world-cup-family-hq/
│
├── app.py                        # Main entry point — navigation + global CSS
├── requirements.txt
│
├── data/
│   ├── world_cup_2026_matches.csv   # 72 group stage matches (verify with FIFA.com)
│   ├── teams.csv                    # 48 teams — country facts, soccer info, stamps
│   ├── users.csv                    # 5 family members — avatars, theme colors
│   ├── country_metadata.csv         # Continent, stamp emoji, stamp label, flag fact
│   ├── achievements.csv             # 33+ achievements — rules, categories, scope
│   └── worldcup.db                  # ← GENERATED. Do not hand-edit. Run reset_db.py.
│
├── pages/
│   ├── home.py                      # Clubhouse lobby — matches, COTD, activity, leaderboard
│   ├── schedule.py                  # Full match schedule with pick buttons
│   ├── matchup.py                   # Game Day Program per match
│   ├── country_profile.py           # National Geographic-style country page
│   ├── passport_individual.py       # Personal passport + stamp collection
│   ├── passport_family.py           # Family stamp wall + comparisons
│   ├── achievements.py              # Achievement tracker
│   ├── host_cities.py               # 16 host city explorer (Seattle is special)
│   └── admin.py                     # Score entry + data review (Shawn)
│
├── services/
│   ├── database.py                  # SQLite schema + init + seeding
│   ├── matches.py                   # Match queries + score updates
│   ├── teams.py                     # Team queries + flag helper
│   ├── picks.py                     # Pick CRUD + activity logging
│   ├── scoring.py                   # Leaderboard + pick result math
│   ├── passport.py                  # Discovery tracking, favorites, COTD, family stats
│   ├── activity.py                  # Activity log read/write
│   ├── achievements.py              # Achievement check + award logic
│   └── time_utils.py                # ET → PT conversion, display formatting
│
└── scripts/
    └── reset_db.py                  # Wipe and reseed worldcup.db from CSVs
```

---

## Data Files

### `data/world_cup_2026_matches.csv`
72 group stage matches (June 11–27, 2026). Times stored in ET; displayed in PT throughout the app.  
**Source:** ESPN / official FIFA schedule. Verify at [fifa.com](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/scores-fixtures).

### `data/teams.csv`
48 teams. Key fields: `name`, `flag_emoji`, `group_letter`, `confederation`, `fifa_ranking`, `coach`, `captain`, `capital`, `population`, `languages`, `currency`, `fun_fact`, `animals`, `foods`, `landmarks`, `cheer_reasons`, `key_players`, `mls_connections`.

### `data/country_metadata.csv`
Canonical source for passport stamps and continents. Fields: `country`, `continent`, `stamp_emoji`, `stamp_label`, `flag_fact`.  
All passport, matchup, and country profile code reads from this file.

### `data/achievements.csv`
Achievement definitions. Fields: `achievement_id`, `name`, `description`, `category`, `scope` (individual/family), `hidden`, `emoji`, `rule_type`, `threshold`.

### `data/users.csv`
Family members. Fields: `id`, `name`, `avatar`, `theme_color`.

### `data/worldcup.db`
SQLite database. Tables: `teams`, `matches`, `users`, `picks`, `discoveries`, `activity_log`, `user_achievements`, `family_achievements`.  
**Do not hand-edit.** Regenerated by `scripts/reset_db.py`.

---

## Resetting the Database

Picks, discoveries, activity, and achievements all live in `worldcup.db`. To start fresh:

```bash
python scripts/reset_db.py
```

This deletes the database and reseeds it from the CSV files. Picks and activity will be lost.

---

## All Times Are Pacific (PT)

Match times in the CSV are stored in ET (Eastern). The app converts everything to PT using `services/time_utils.py`. In summer 2026 (EDT → PDT), the offset is exactly –3 hours. This is hardcoded — no external timezone library needed.

---

## Continuing Development

Key decisions documented in `../CLAUDE.md` (one level up from this folder).

Build priorities (next up):
- Pick Tracker page (by match + by person)
- Leaderboard dedicated page  
- Interactive map of host cities
- Country Profile map section (Plotly choropleth)
- Knockout rounds (post group stage)
