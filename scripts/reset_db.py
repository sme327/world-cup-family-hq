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
if os.path.exists(db_path) and not full_wipe:
    print("📦 Backing up picks before reset...")
    subprocess.run([sys.executable, backup_py], check=False)
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
