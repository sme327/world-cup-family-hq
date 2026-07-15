# Reusing This App For A New Tournament

This app was built for the **2026 FIFA Men's World Cup** (48 teams, 12 groups, hosted across
USA / Canada / Mexico). The design, family features, passport system, and most page logic are
tournament-agnostic and carry over unchanged. What's specific to 2026 is concentrated in a small
number of **data files** and a few **hardcoded structural constants**.

This guide is the checklist for pointing it at a new tournament. The worked example is the
**2027 FIFA Women's World Cup** (Brazil), because that's the intended next use.

> **The single biggest structural difference for 2027:** the men's 48-team format has a
> **Round of 32** (32 teams reach the knockouts). The women's 32-team format has **no Round of
> 32** — the knockouts start at the **Round of 16** (top 2 of each of 8 groups → 16 teams).
> Wherever this app says "R32 is the first knockout round," that becomes "R16."

---

## 2027 Women's World Cup — the facts you'll seed

| Thing | 2026 Men's (current) | 2027 Women's (target) |
|-------|----------------------|------------------------|
| Host(s) | USA, Canada, Mexico | Brazil |
| Teams | 48 | 32 |
| Groups | 12 (A–L) | 8 (A–H) |
| Advance from groups | Top 2 + 8 best 3rd → 32 | Top 2 → 16 |
| First knockout round | Round of 32 (16 matches) | **Round of 16** (8 matches) |
| Knockout shape | R32 → R16 → QF → SF → 3rd/Final | **R16 → QF → SF → 3rd/Final** |
| Dates | Jun 11 – Jul 19, 2026 | ~Jun 24 – Jul 25, 2027 (verify) |
| Time zone | ET-stored, PT-displayed (US DST) | Brazil is mostly UTC−3; decide storage/display |
| Club connections | MLS / US clubs | NWSL / US clubs |
| Family home city | Seattle (a host city) | Seattle (not a host — reframe as "home") |

Verify all 2027 specifics against FIFA before seeding — dates and venues shift.

---

## Before you start

Do this on a **fresh branch or a copy of the repo**, not on top of live 2026 data. The 2026
family picks and results live in the GitHub backup CSVs; a new tournament is a clean slate, so
you don't want to overwrite or restore that history. Either:
- start a new repo (recommended — new `GITHUB_REPO` secret, new backup history), or
- branch and clear the backup CSVs so `reset_db.py` doesn't restore 2026 picks.

---

## Phase 1 — Data & content (the bulk of the work, no code)

All of these are CSV/JSON/image files in `data/`. **CSVs are the source of truth; `worldcup.db`
is generated.** Replace the *contents*, keep the *column headers*.

1. **`teams.csv`** — the 32 women's teams. Keep every column. Set `group_letter` to A–H. Fill
   country facts (`capital`, `population`, `fun_fact`, `animals`, `foods`, `landmarks`,
   `cheer_reasons`, …), soccer info (`coach`, `captain`, `fifa_ranking`, `confederation`,
   `best_finish`), and `mls_connections` → rename/repurpose for **NWSL** (see Phase 4).
2. **`country_metadata.csv`** — the canonical passport/continent file. One row per team country:
   `country`, `continent`, `stamp_emoji`, `stamp_label`, `flag_fact`. Everything passport-related
   reads this, so get the country names **exactly matching `teams.csv`**.
3. **`<tournament>_matches.csv`** — the group-stage schedule. For 32 teams / 8 groups that's
   **48 group matches** (not 72). Keep columns (`home_team`, `away_team`, `match_date`,
   `kickoff_time_et`, `group_letter`, `city`, `venue`, …). Decide your time convention first
   (Phase 3). Rename the file and update the reference in `services/database.py` seeding.
4. **`knockout_matches.csv`** — rebuild the bracket. For 32 teams: **R16 (8) → QF (4) → SF (2)
   → 3rd place (1) + Final (1) = 16 matches** (down from 32). Set `home_source`/`away_source`
   slot descriptors (e.g. `"1st Group A"`, `"2nd Group B"` — **no 3rd-place sources**) and the
   `winner_to_id` / `winner_to_slot` (and `loser_to_*` for SF→3rd) wiring. Reassign match IDs and
   numbers. See `docs/knockout_sources.md` for how the 2026 bracket was sourced and wired.
5. **Rosters** — `world_cup_rosters.csv`, `world_cup_players_slugged.csv`,
   `world_cup_team_summary.csv`. Regenerate for the women's squads (`scripts/extract_rosters.py`
   is the builder). Check the team-name mapping table in `services/roster.py` — roster-source
   names may differ from `teams.csv` names.
6. **`achievements.csv`** — review thresholds that reference tournament size. "Discover all
   countries" style achievements are **/32**, not /48; continent-completion thresholds change
   with the new team distribution. Update `threshold` values and any copy that says "48".
7. **`country_details.json`** and the **image sets** (`country_images/`, `country_card_images/`,
   `city_images/` + their `*_image_manifest.csv`). Recurate for the new countries and host
   cities. `scripts/download_*.py` help fetch/curate.
8. **`users.csv`** — the family stays the same; no change needed unless the roster of players
   changes.

---

## Phase 2 — Bracket structure code (the only structural code changes)

Because the knockouts start at R16 (not R32), update these. Search-and-verify each:

1. **`services/knockout.py`**
   - `_SOURCE_RE` — group letter regex `[A-L]` → `[A-H]`.
   - `_ROUND_ORDER` and `_EXPECTED_COUNTS` — drop `"r32"`; set counts to
     `{"r16": 8, "qf": 4, "sf": 2, "final": 1, "third_place": 1}`.
   - `_sync_r32_from_standings()` — this auto-fills the **first** knockout round from group
     standings. Rename/retarget it to sync **R16** instead of R32 (round key `'r16'`), and note
     the source strings now only reference 1st/2nd (no best-3rd logic).
2. **`services/ko_picks.py`**
   - `KO_ROUND_POINTS` — remove the `"r32"` entry; rescale if desired (e.g. R16=2, QF=3, SF=4,
     3rd=4, Final=6).
   - `KO_ROUND_LABELS` — remove `"r32"`.
3. **`components/radial_bracket.py`** — the circular bracket geometry assumes 32 outer teams:
   - `N = 32` → `N = 16` (outer team positions).
   - Ring radii `R_R32 / R_R16 / R_QF / R_SF` — the outer ring is now R16; remove the R32 ring
     and re-space the remaining rings outward-to-inward. Expect to tune these visually.
   - `range(1, 17)` loops (there are two: one building `outer[...]`, one computing `r32_done`)
     → `range(1, 9)`; the outer array is 16 long, not 32.
   - `r32_done` / `OUTER_FLAG_PRE`/`OUTER_FLAG_POST` — rename the "first round complete" concept
     to R16. Flag-sizing knobs are centralized at the top of the file and are safe to re-tune.
   - `_SHORT` — the 3-letter country codes dict: replace with the 2027 teams.
4. **`pages/home.py`** — the "current knockout round" home section:
   - `_KO_PHASES` — the phase list. Drop any R32 grouping; keep QF / SF / "Final & 3rd Place".
     The "first round" that triggers the full-round view is now R16.
   - `_current_phase()` / `_is_qf_plus()` — these key off round names; verify they still make
     sense when R16 is the opener (and confirm the `third_place` round string, already fixed
     for 2026).

That's the whole structural surface. Group standings, qualification sorting, picks, scoring,
passport, achievements-checking, and every content page read from the DB/CSVs and need **no code
change** — only new data.

---

## Phase 3 — Region & time

The app stores match times in **ET** and displays **PT**, with hardcoded DST offsets. Brazil is
a different region. Decide a convention (simplest: store times already in the family's viewing
zone), then update:

- **`services/time_utils.py`** — `et_to_pt()` uses `−3h`; `today_pt()` uses `utcnow − 7h`.
  Change both to your chosen offsets (or generalize to a single configurable offset).
- **`pages/home.py`** — `today = utcnow − 7h` (line ~567), `now_pt = utcnow − 7h`, and a
  `−3h` conversion in the countdown. Same offsets as above.
- **`components/radial_bracket.py`** — `_today = utcnow − 7h` and a `−3h` conversion inside the
  node tooltip time formatter.
- **`pages/home.py`** — `wc_start = date(2026,6,11)` / `wc_end = date(2026,7,19)`: set to the
  2027 tournament window (drives the "Day N" banner and "in tournament" logic).

Grep for `hours=7`, `hours=3`, and `date(2026` to find them all.

---

## Phase 4 — Labels & framing

- **MLS → NWSL.** `services/roster.py` detects US-based clubs by `(USA)` in the club field and
  the app labels it "MLS & US Connections." The *detection* still works for any US club; update
  the **label** to "NWSL & US Connections" in `services/roster.py`, `services/player_cards.py`,
  `pages/matchup.py`, `pages/country_profile.py`, `pages/host_cities.py` (grep `MLS`).
- **Host country / venues.** `pages/host_cities.py` describes the 16 North American venues.
  Rewrite for the 2027 Brazilian host cities and stadiums.
- **Seattle.** The family is in Seattle, which was a 2026 *host* city (treated as special). In
  2027 Seattle is **home but not a host** — reframe "Seattle is special because it's hosting" as
  "here's how far these countries are from home." Grep `Seattle`.
- **Copy that says "48" / "12 groups" / "104 matches" / "North America".** Grep for these strings
  across `pages/`, `README.md`, and the parent `CLAUDE.md`, and update. (`CLAUDE.md`'s
  "Current Tournament Scope" and "Official Venues" sections are 2026-specific and should be
  rewritten for the new tournament; the product philosophy above/around them carries over.)
- **App title / branding.** "World Cup Family HQ" still fits; update any "2026" or "Men's"
  references.

---

## Phase 5 — Rebuild, verify, deploy

1. **Rebuild the DB from the new CSVs:**
   ```bash
   python scripts/reset_db.py --wipe      # clean build, no 2026 restore
   ```
   Use `--wipe` so it does **not** try to restore 2026 backup picks. (Once the new tournament is
   live and families are picking, plain `reset_db.py` restores *their* backups as normal.)
2. **Run locally and click through:**
   ```bash
   streamlit run app.py
   ```
   Check: group standings populate; a group match's picks/scoring work; the bracket renders with
   16 outer teams; entering a knockout result advances the winner; a country profile logs a
   discovery; the passport counts show `/32`.
3. **Point backups at a new repo.** Update the `GITHUB_REPO` (and `GITHUB_TOKEN`) secret so the
   new tournament's backups don't collide with the 2026 history. Clear the old `*_backup.csv`
   files.
4. **Deploy** to Streamlit Cloud (or run locally) as before.

---

## Quick reference — where the tournament is hardcoded

| Concern | File(s) | Symbol / marker |
|--------|---------|-----------------|
| Group letters A–L | `services/knockout.py` | `_SOURCE_RE` (`[A-L]`) |
| Knockout rounds & counts | `services/knockout.py` | `_ROUND_ORDER`, `_EXPECTED_COUNTS` |
| First round = R32 sync | `services/knockout.py` | `_sync_r32_from_standings()` |
| KO points / labels | `services/ko_picks.py` | `KO_ROUND_POINTS`, `KO_ROUND_LABELS` |
| Bracket geometry (32 teams) | `components/radial_bracket.py` | `N`, `R_R32…R_SF`, `range(1,17)`, `r32_done`, `_SHORT` |
| Home "current round" phases | `pages/home.py` | `_KO_PHASES`, `_current_phase`, `_is_qf_plus` |
| Tournament dates | `pages/home.py` | `wc_start`, `wc_end` |
| Time-zone offsets | `services/time_utils.py`, `pages/home.py`, `components/radial_bracket.py` | `hours=3`, `hours=7` |
| MLS labeling | `services/roster.py`, `services/player_cards.py`, `pages/matchup.py`, `pages/country_profile.py`, `pages/host_cities.py` | `MLS` strings |
| Venues / host cities | `pages/host_cities.py` | venue data |
| Seattle-is-host framing | (grep) | `Seattle` |
| Tournament scope & venues (design doc) | `../CLAUDE.md` | "Current Tournament Scope", "Official Venues" |

## What you do NOT need to touch

Group standings math, qualification sorting, pick CRUD and scoring, the passport/discovery/
favorites system, achievement checking, the activity feed, leaderboards, country-profile and
matchup page layouts, and the backup/restore machinery are all data-driven. Give them new CSV
data and they work — no code changes.
