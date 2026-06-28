# Knockout Stage Data Sources

## Data fetched: 2026-06-23

## Primary source
Wikipedia — 2026 FIFA World Cup knockout stage article
- Full bracket structure, all 32 match slots
- Venue assignments per round
- Official match numbers (M73–M104)
- Kickoff times in local timezone with UTC offset

## Cross-referenced with
- Yahoo Sports 2026 World Cup knockout bracket
- Fox Sports / CBS Sports R32 pairings

## Bracket structure

32 teams → 16 R32 matches (M73–M88) → 8 R16 matches (M89–M96) → 4 QF (M97–M100) → 2 SF (M101–M102) → Final (M104) + 3rd Place (M103)

## R32 group source verification

Each R32 slot is determined by the FIFA bracket draw (group finish position).
Sources: Yahoo Sports + Wikipedia bracket article.

Key resolution note: Austria (M84) is **2nd Group J** (runner-up), NOT 3rd.
Yahoo Sports listed "3rd Group J" for Austria — this is an error.
Fox Sports and CBS Sports confirm Austria as Group J runner-up.

Group J final standings: Argentina 1st, Austria 2nd, Algeria 3rd (advanced as best 3rd), [4th eliminated].

## Timezone conversion notes

All kickoff times converted to US Eastern Time (EDT = UTC-4):
- UTC-4 venues (East Coast): time as listed
- UTC-5 venues (Central): listed local time + 1 hour
- UTC-6 venues (Mountain/Mexico): listed local time + 2 hours
- UTC-7 venues (Pacific): listed local time + 3 hours

## City note

Estadio BBVA is located in **Guadalupe**, Nuevo León — not Monterrey proper.
The stadium is colloquially associated with Monterrey but sits in Guadalupe city limits.
This file uses "Guadalupe" as the city for accuracy.

## Advancement routing

`winner_to_id` / `winner_to_slot` wire the bracket automatically:
- When admin saves a match result, the winner's team_id is written into the next match's home_team_id or away_team_id based on the slot column.
- SF losers are routed to `loser_to_id` / `loser_to_slot` → 3rd Place match.

## IDs used

- R32: IDs 101–116
- R16: IDs 117–124
- QF:  IDs 125–128
- SF:  IDs 129–130
- 3rd Place: ID 131
- Final: ID 132

Group stage match IDs remain 1–72 (unchanged).

## Known assumptions

1. The official bracket draw assigned group finishes to specific R32 slots. These assignments are based on pre-tournament draws and are correct per Wikipedia.
2. Kickoff times are pre-tournament schedule and may shift slightly. Admin can enter actual results regardless.
3. The group stage is assumed complete before R32 begins (June 28). Team names are pre-seeded in the DB from teams.csv.
