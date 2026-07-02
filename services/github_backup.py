"""
Auto-commit backup CSVs to GitHub so data survives Streamlit Cloud sleep/wake cycles.

Requires in Streamlit secrets (.streamlit/secrets.toml or Cloud dashboard):
    GITHUB_TOKEN = "ghp_..."          # fine-grained token, Contents: read+write
    GITHUB_REPO  = "sme327/world-cup-family-hq"

Usage:
    from services.github_backup import push_backups_to_github
    ok, msg = push_backups_to_github()
"""
import base64
import io
import csv
import sqlite3
import urllib.request
import urllib.error
import json
from datetime import datetime

import streamlit as st

from services.database import get_connection, DATA_DIR
import os

# ── GitHub API helpers ────────────────────────────────────────────────────────

def _get_token() -> str | None:
    try:
        return st.secrets.get("GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
    except Exception:
        return os.environ.get("GITHUB_TOKEN")


def _get_repo() -> str:
    try:
        return st.secrets.get("GITHUB_REPO", "sme327/world-cup-family-hq")
    except Exception:
        return os.environ.get("GITHUB_REPO", "sme327/world-cup-family-hq")


def _api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    url = f"https://api.github.com/repos/{_get_repo()}/contents/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def _get_sha(path: str, token: str) -> str | None:
    try:
        resp = _api("GET", path, token)
        return resp.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _push_file(path: str, content_bytes: bytes, token: str, message: str) -> bool:
    sha = _get_sha(path, token)
    body: dict = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode(),
        "branch": "master",
    }
    if sha:
        body["sha"] = sha
    _api("PUT", path, token, body)
    return True


# ── CSV builders ──────────────────────────────────────────────────────────────

def _to_csv(rows: list, headers: list) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerows(rows)
    return buf.getvalue().encode()


def _build_csvs() -> dict[str, bytes]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row

    picks = conn.execute("""
        SELECT u.name AS user_name, p.user_id, p.match_id,
               m.home_team, m.away_team, m.match_date, p.picked_team
        FROM picks p
        JOIN users u ON p.user_id = u.id
        JOIN matches m ON p.match_id = m.id
        ORDER BY m.match_date, m.id, u.id
    """).fetchall()

    scores = conn.execute("""
        SELECT home_team, away_team, match_date, home_score, away_score, status
        FROM matches WHERE status='completed' ORDER BY match_date
    """).fetchall()

    ko_results = conn.execute("""
        SELECT km.id, km.round, km.bracket_slot, km.match_number,
               km.home_team_id, km.away_team_id,
               ht.name AS home_name, at2.name AS away_name,
               km.match_date, km.home_score, km.away_score,
               km.winner_team_id, km.status, km.home_penalties, km.away_penalties
        FROM knockout_matches km
        LEFT JOIN teams ht  ON km.home_team_id  = ht.id
        LEFT JOIN teams at2 ON km.away_team_id = at2.id
        WHERE km.home_score IS NOT NULL OR km.winner_team_id IS NOT NULL
        ORDER BY km.match_date, km.id
    """).fetchall()

    ko_picks = conn.execute("""
        SELECT u.name AS user_name, u.id AS user_id,
               klp.knockout_match_id, klp.picked_team_id,
               t.name AS picked_team_name,
               km.round, km.bracket_slot, km.match_date,
               klp.created_at, klp.updated_at
        FROM knockout_live_picks klp
        JOIN users u ON klp.user_id = u.id
        JOIN teams t ON klp.picked_team_id = t.id
        JOIN knockout_matches km ON klp.knockout_match_id = km.id
        ORDER BY km.match_date, km.id, u.id
    """).fetchall()

    conn.close()

    return {
        "data/picks_backup.csv": _to_csv(
            [list(r) for r in picks],
            ["user_name","user_id","match_id","home_team","away_team","match_date","picked_team"],
        ),
        "data/scores_backup.csv": _to_csv(
            [list(r) for r in scores],
            ["home_team","away_team","match_date","home_score","away_score","status"],
        ),
        "data/ko_results_backup.csv": _to_csv(
            [list(r) for r in ko_results],
            ["id","round","bracket_slot","match_number","home_team_id","away_team_id",
             "home_name","away_name","match_date","home_score","away_score",
             "winner_team_id","status","home_penalties","away_penalties"],
        ),
        "data/ko_live_picks_backup.csv": _to_csv(
            [list(r) for r in ko_picks],
            ["user_name","user_id","knockout_match_id","picked_team_id","picked_team_name",
             "round","bracket_slot","match_date","created_at","updated_at"],
        ),
    }


# ── Public API ────────────────────────────────────────────────────────────────

def push_backups_to_github(label: str = "auto") -> tuple[bool, str]:
    """Commit all 4 backup CSVs to GitHub. Returns (success, message)."""
    token = _get_token()
    if not token:
        return False, "No GITHUB_TOKEN in secrets — add it in the Streamlit Cloud dashboard."

    try:
        csvs = _build_csvs()
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        msg = f"Auto-backup ({label}) — {ts}"
        for path, content in csvs.items():
            _push_file(path, content, token, msg)
        return True, f"✅ Backed up to GitHub at {ts}"
    except Exception as e:
        return False, f"❌ GitHub backup failed: {e}"


def github_backup_available() -> bool:
    """True if a GitHub token is configured."""
    return bool(_get_token())
