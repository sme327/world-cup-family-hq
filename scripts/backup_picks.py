"""
Export all picks, scores, and activity to CSV backup files.

Run from the project root:
    python scripts/backup_picks.py

Files written (safe to commit to git):
    data/picks_backup.csv          — all picks
    data/scores_backup.csv         — completed match scores
    data/achievements_backup.csv   — earned achievements
    data/activity_backup.csv       — activity log
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
conn.row_factory = sqlite3.Row

def _export(query: str, outfile: str, label: str):
    rows = conn.execute(query).fetchall()
    if not rows:
        print(f"  {label}: 0 rows — skipping")
        return 0
    path = os.path.join(DATA, outfile)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])
    print(f"  {label}: {len(rows)} rows → {outfile}")
    return len(rows)

print(f"\n📦 Backing up worldcup.db — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

_export(
    """SELECT p.id, u.name AS user_name, u.id AS user_id,
              m.id AS match_id, m.home_team, m.away_team, m.match_date,
              p.picked_team, p.created_at
       FROM picks p
       JOIN users u ON p.user_id = u.id
       JOIN matches m ON p.match_id = m.id
       ORDER BY m.match_date, m.id, u.id""",
    "picks_backup.csv", "Picks"
)

_export(
    """SELECT id, home_team, away_team, match_date, kickoff_time_et,
              group_letter, home_score, away_score, status
       FROM matches WHERE status = 'completed'
       ORDER BY match_date, kickoff_time_et""",
    "scores_backup.csv", "Scores"
)

_export(
    """SELECT ua.id, u.name AS user_name, u.id AS user_id,
              ua.achievement_id, ua.unlocked_at
       FROM user_achievements ua
       JOIN users u ON ua.user_id = u.id
       ORDER BY ua.unlocked_at""",
    "achievements_backup.csv", "User achievements"
)

_export(
    """SELECT al.id, al.timestamp, u.name AS user_name, u.id AS user_id,
              al.event_type, al.country_name, al.match_id,
              al.achievement_id, al.message
       FROM activity_log al
       LEFT JOIN users u ON al.user_id = u.id
       ORDER BY al.timestamp""",
    "activity_backup.csv", "Activity log"
)

conn.close()
print("\n✅ Backup complete. Commit data/*_backup.csv to preserve picks across deployments.\n")
print("   git add data/picks_backup.csv data/scores_backup.csv")
print("   data/achievements_backup.csv data/activity_backup.csv")
print("   git commit -m 'backup picks'\n")
