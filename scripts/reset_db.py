#!/usr/bin/env python3
"""
Wipe and reseed worldcup.db from the CSV files in data/.

Usage:
    python scripts/reset_db.py
"""
import os
import sys

# Make project root importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.database import DB_PATH, init_db

db_path = os.path.abspath(DB_PATH)

if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted: {db_path}")
else:
    print("No existing database found — creating fresh.")

init_db()
print(f"Database rebuilt: {db_path}")
print("Done.")
