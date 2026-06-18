#!/usr/bin/env python3
"""
Wipe and reseed worldcup.db from the CSV files in data/.

Usage:
    python scripts/reset_db.py          # backup picks first, then reset + restore
    python scripts/reset_db.py --wipe   # full wipe with NO restore (loses picks)
"""
import os
import sys
import subprocess

# Make project root importable
ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, ROOT)

from services.database import DB_PATH, init_db

db_path    = os.path.abspath(DB_PATH)
backup_py  = os.path.join(os.path.dirname(__file__), 'backup_picks.py')
restore_py = os.path.join(os.path.dirname(__file__), 'restore_picks.py')
full_wipe  = '--wipe' in sys.argv

# ── Auto-backup before wiping (unless --wipe requested) ──────────────────────
# Only auto-backup if the DB has MORE picks than the existing backup file,
# so we never silently overwrite a fresher cloud backup with stale local data.
def _backup_pick_count() -> int:
    import csv
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'picks_backup.csv')
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return 0
    with open(path) as f:
        return max(0, sum(1 for _ in f) - 1)  # subtract header row

def _db_pick_count() -> int:
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        n = conn.execute("SELECT COUNT(*) FROM picks").fetchone()[0]
        conn.close()
        return n
    except Exception:
        return 0

if os.path.exists(db_path) and not full_wipe:
    db_picks  = _db_pick_count()
    bak_picks = _backup_pick_count()
    if db_picks >= bak_picks:
        print(f"📦 Backing up picks before reset... (DB: {db_picks}, backup: {bak_picks})")
        subprocess.run([sys.executable, backup_py], check=False)
    else:
        print(
            f"⚠️  Skipping auto-backup: existing backup ({bak_picks} picks) has MORE data "
            f"than local DB ({db_picks} picks). Keeping backup file as-is."
        )
else:
    if full_wipe:
        print("⚠️  --wipe flag set: skipping backup and restore. Picks will be lost.")
    else:
        print("No existing database found — creating fresh.")

# ── Wipe ─────────────────────────────────────────────────────────────────────
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted: {db_path}")

init_db()
print(f"Database rebuilt: {db_path}")

# ── Restore picks from backup CSVs ───────────────────────────────────────────
if not full_wipe and os.path.exists(restore_py):
    print("\n🔄 Restoring picks from backup...")
    subprocess.run([sys.executable, restore_py], check=False)

print("\nDone.")
