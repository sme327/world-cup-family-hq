"""
Restore picks, scores, and achievements from backup CSVs into worldcup.db.

Run from the project root AFTER reset_db.py:
    python scripts/restore_picks.py

Reads (if present):
    data/picks_backup.csv
    data/scores_backup.csv
    data/achievements_backup.csv
    data/activity_backup.csv
    data/ko_results_backup.csv
    data/ko_live_picks_backup.csv
"""
import os, sys, sqlite3, csv
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB   = os.path.join(ROOT, "data", "worldcup.db")
DATA = os.path.join(ROOT, "data")

if not os.path.exists(DB):
    print("ERROR: worldcup.db not found. Run reset_db.py first.")
    sys.exit(1)

conn = sqlite3.connect(DB)

def _read_csv(filename):
    path = os.path.join(DATA, filename)
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))

print(f"\n🔄 Restoring from backup CSVs — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

# ── Picks ─────────────────────────────────────────────────────────────────────
picks_rows = _read_csv("picks_backup.csv")
if picks_rows:
    # Build user_name→id and match lookup from live DB
    users = {r[0]: r[1] for r in conn.execute("SELECT name, id FROM users").fetchall()}
    matches_by_teams_date = {
        (r[0], r[1], r[2]): r[3]
        for r in conn.execute(
            "SELECT home_team, away_team, match_date, id FROM matches"
        ).fetchall()
    }
    inserted = skipped = 0
    for row in picks_rows:
        uid = users.get(row.get("user_name",""))
        mid = matches_by_teams_date.get(
            (row.get("home_team",""), row.get("away_team",""), row.get("match_date",""))
        )
        if uid is None or mid is None:
            skipped += 1
            continue
        existing = conn.execute(
            "SELECT id FROM picks WHERE user_id=? AND match_id=?", (uid, mid)
        ).fetchone()
        if existing:
            skipped += 1
            continue
        conn.execute(
            "INSERT INTO picks (user_id, match_id, picked_team) VALUES (?,?,?)",
            (uid, mid, row.get("picked_team",""))
        )
        inserted += 1
    conn.commit()
    print(f"  Picks: {inserted} restored, {skipped} skipped (already exist or no match)")
else:
    print("  Picks: no backup found")

# ── Scores ────────────────────────────────────────────────────────────────────
scores_rows = _read_csv("scores_backup.csv")
if scores_rows:
    updated = 0
    for row in scores_rows:
        hs = row.get("home_score")
        as_ = row.get("away_score")
        if hs in (None, "", "None") or as_ in (None, "", "None"):
            continue
        conn.execute(
            """UPDATE matches SET home_score=?, away_score=?, status='completed'
               WHERE home_team=? AND away_team=? AND match_date=?""",
            (int(float(hs)), int(float(as_)),
             row.get("home_team",""), row.get("away_team",""), row.get("match_date",""))
        )
        updated += 1
    conn.commit()
    print(f"  Scores: {updated} matches updated")
else:
    print("  Scores: no backup found")

# ── Achievements ──────────────────────────────────────────────────────────────
ach_rows = _read_csv("achievements_backup.csv")
if ach_rows:
    users = {r[0]: r[1] for r in conn.execute("SELECT name, id FROM users").fetchall()}
    inserted = skipped = 0
    for row in ach_rows:
        uid = users.get(row.get("user_name",""))
        aid = row.get("achievement_id","")
        if not uid or not aid:
            skipped += 1
            continue
        existing = conn.execute(
            "SELECT id FROM user_achievements WHERE user_id=? AND achievement_id=?", (uid, aid)
        ).fetchone()
        if existing:
            skipped += 1
            continue
        conn.execute(
            "INSERT INTO user_achievements (user_id, achievement_id, unlocked_at) VALUES (?,?,?)",
            (uid, aid, row.get("unlocked_at", datetime.now().isoformat()))
        )
        inserted += 1
    conn.commit()
    print(f"  Achievements: {inserted} restored, {skipped} skipped")
else:
    print("  Achievements: no backup found")

# ── Activity log ──────────────────────────────────────────────────────────────
act_rows = _read_csv("activity_backup.csv")
if act_rows:
    users = {r[0]: r[1] for r in conn.execute("SELECT name, id FROM users").fetchall()}
    inserted = 0
    for row in act_rows:
        uid = users.get(row.get("user_name",""))
        conn.execute(
            """INSERT OR IGNORE INTO activity_log
               (timestamp, user_id, event_type, country_name, match_id, achievement_id, message)
               VALUES (?,?,?,?,?,?,?)""",
            (row.get("timestamp"), uid,
             row.get("event_type"), row.get("country_name") or None,
             row.get("match_id") or None, row.get("achievement_id") or None,
             row.get("message") or None)
        )
        inserted += 1
    conn.commit()
    print(f"  Activity log: {inserted} events restored")
else:
    print("  Activity log: no backup found")

# ── KO Match Results ──────────────────────────────────────────────────────────
ko_results = _read_csv("ko_results_backup.csv")
if ko_results:
    updated = 0
    for row in ko_results:
        hs  = row.get("home_score")
        as_ = row.get("away_score")
        wid = row.get("winner_team_id")
        hp  = row.get("home_penalties")
        ap  = row.get("away_penalties")
        if hs in (None, "", "None") and wid in (None, "", "None"):
            continue
        conn.execute(
            """UPDATE knockout_matches
               SET home_score=?, away_score=?, winner_team_id=?,
                   home_penalties=?, away_penalties=?, status=?
               WHERE id=?""",
            (
                int(float(hs))  if hs  not in (None, "", "None") else None,
                int(float(as_)) if as_ not in (None, "", "None") else None,
                int(float(wid)) if wid not in (None, "", "None") else None,
                int(float(hp))  if hp  not in (None, "", "None") else None,
                int(float(ap))  if ap  not in (None, "", "None") else None,
                row.get("status", "completed"),
                int(row["id"]),
            )
        )
        updated += 1
    conn.commit()
    print(f"  KO results: {updated} matches updated")
else:
    print("  KO results: no backup found")

# ── KO Live Picks ─────────────────────────────────────────────────────────────
ko_picks = _read_csv("ko_live_picks_backup.csv")
if ko_picks:
    users = {r[0]: r[1] for r in conn.execute("SELECT name, id FROM users").fetchall()}
    inserted = skipped = 0
    for row in ko_picks:
        uid  = users.get(row.get("user_name", ""))
        kmid = row.get("knockout_match_id")
        tid  = row.get("picked_team_id")
        if not uid or not kmid or not tid:
            skipped += 1
            continue
        existing = conn.execute(
            "SELECT id FROM knockout_live_picks WHERE user_id=? AND knockout_match_id=?",
            (uid, int(kmid))
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE knockout_live_picks SET picked_team_id=?, updated_at=?
                   WHERE user_id=? AND knockout_match_id=?""",
                (int(tid), row.get("updated_at", datetime.now().isoformat()),
                 uid, int(kmid))
            )
            skipped += 1
        else:
            conn.execute(
                """INSERT INTO knockout_live_picks
                   (user_id, knockout_match_id, picked_team_id, created_at, updated_at)
                   VALUES (?,?,?,?,?)""",
                (uid, int(kmid), int(tid),
                 row.get("created_at", datetime.now().isoformat()),
                 row.get("updated_at", datetime.now().isoformat()))
            )
            inserted += 1
    conn.commit()
    print(f"  KO live picks: {inserted} restored, {skipped} updated/skipped")
else:
    print("  KO live picks: no backup found")

conn.close()
print("\n✅ Restore complete.\n")
