"""Bracket picks service — locked full bracket picks for knockout stage.

Scoring:
  +1 for each correct pick (R32, R16, QF, SF, Final)
  +2 for each correct QF pick (semifinalist bonus) → QF winner = 3 pts total
  +5 for correct Final pick (champion bonus) → champion = 6 pts total
  Max = 31 picks × 1 = 31 base, +8 semis bonus, +5 champ = 44 pts
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from services.database import get_connection

REQUIRED_PICKS:   int      = 31
EXCLUDED_MATCHES: set[int] = {131}        # 3rd place — not part of bracket picks
QF_MATCH_IDS:     set[int] = {125, 126, 127, 128}
SF_MATCH_IDS:     set[int] = {129, 130}
FINAL_MATCH_ID:   int      = 132

ROUND_ORDER = ["r32", "r16", "qf", "sf", "final"]

ROUND_LABELS = {
    "r32":   "Round of 32",
    "r16":   "Round of 16",
    "qf":    "Quarterfinals",
    "sf":    "Semifinals",
    "final": "Final",
}


# ── Internal helpers ───────────────────────────────────────────────────────────

def _get_team_map(conn) -> dict[int, dict]:
    rows = conn.execute("SELECT id, name, flag_emoji FROM teams").fetchall()
    return {r[0]: {"name": r[1], "flag": r[2] or ""} for r in rows}


def _get_structure(conn) -> dict[int, dict]:
    """All knockout matches except 131, keyed by ID."""
    rows = conn.execute("""
        SELECT id, round, bracket_slot, match_number,
               home_team_id, away_team_id,
               winner_to_id, winner_to_slot
        FROM knockout_matches
        WHERE id != 131
        ORDER BY round, bracket_slot
    """).fetchall()
    return {
        r[0]: {
            "id": r[0], "round": r[1], "bracket_slot": r[2], "match_number": r[3],
            "home_team_id": r[4], "away_team_id": r[5],
            "winner_to_id": r[6], "winner_to_slot": r[7],
        }
        for r in rows
    }


def _downstream_ids(start_id: int, structure: dict) -> list[int]:
    """BFS from start_id through winner_to_id, excluding EXCLUDED_MATCHES."""
    found: list[int] = []
    queue = [start_id]
    while queue:
        mid = queue.pop(0)
        nxt = structure.get(mid, {}).get("winner_to_id")
        if nxt and nxt not in EXCLUDED_MATCHES and nxt not in found:
            found.append(nxt)
            queue.append(nxt)
    return found


# ── Team helpers ───────────────────────────────────────────────────────────────

def get_team_map() -> dict[int, dict]:
    conn = get_connection()
    m = _get_team_map(conn)
    conn.close()
    return m


# ── Lock ───────────────────────────────────────────────────────────────────────

def get_bracket_lock() -> dict:
    conn = get_connection()
    row = conn.execute(
        "SELECT is_locked, locked_at, locked_by FROM bracket_lock WHERE id=1"
    ).fetchone()
    conn.close()
    if row is None:
        return {"is_locked": False, "locked_at": None, "locked_by": None}
    return {"is_locked": bool(row[0]), "locked_at": row[1], "locked_by": row[2]}


def set_bracket_lock(is_locked: bool, locked_by: str = "Admin") -> None:
    now = datetime.now().isoformat() if is_locked else None
    conn = get_connection()
    conn.execute(
        "UPDATE bracket_lock SET is_locked=?, locked_at=?, locked_by=? WHERE id=1",
        (1 if is_locked else 0, now, locked_by if is_locked else None),
    )
    conn.commit()
    conn.close()


# ── Pick storage ───────────────────────────────────────────────────────────────

def save_bracket_pick(user_id: int, knockout_match_id: int, team_id: int) -> None:
    """Upsert one pick. Clears all downstream picks. Raises ValueError if locked."""
    lock = get_bracket_lock()
    if lock["is_locked"]:
        raise ValueError("Brackets are locked — no changes allowed.")
    if knockout_match_id in EXCLUDED_MATCHES:
        raise ValueError("3rd place match is not included in bracket picks.")

    now = datetime.now().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    structure = _get_structure(conn)

    # Clear downstream picks so bracket stays internally consistent
    downstream = _downstream_ids(knockout_match_id, structure)
    if downstream:
        ph = ",".join("?" * len(downstream))
        cur.execute(
            f"DELETE FROM bracket_picks WHERE user_id=? AND knockout_match_id IN ({ph})",
            [user_id] + downstream,
        )

    # Upsert the pick
    cur.execute("""
        INSERT INTO bracket_picks (user_id, knockout_match_id, picked_team_id, created_at, updated_at)
        VALUES (?,?,?,?,?)
        ON CONFLICT(user_id, knockout_match_id)
        DO UPDATE SET picked_team_id=excluded.picked_team_id, updated_at=excluded.updated_at
    """, (user_id, knockout_match_id, team_id, now, now))

    # Update completion cache
    count = cur.execute(
        "SELECT COUNT(*) FROM bracket_picks WHERE user_id=?", (user_id,)
    ).fetchone()[0]
    complete = 1 if count >= REQUIRED_PICKS else 0
    cur.execute("""
        INSERT INTO bracket_submissions (user_id, is_complete)
        VALUES (?,?)
        ON CONFLICT(user_id)
        DO UPDATE SET is_complete=excluded.is_complete
    """, (user_id, complete))

    conn.commit()
    conn.close()


def get_bracket_picks(user_id: int) -> dict[int, int]:
    """Return {knockout_match_id: picked_team_id} for the user."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT knockout_match_id, picked_team_id FROM bracket_picks WHERE user_id=?",
        (user_id,),
    ).fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


def clear_bracket_picks(user_id: int) -> None:
    lock = get_bracket_lock()
    if lock["is_locked"]:
        raise ValueError("Brackets are locked — cannot clear picks.")
    conn = get_connection()
    conn.execute("DELETE FROM bracket_picks WHERE user_id=?", (user_id,))
    conn.execute(
        "UPDATE bracket_submissions SET is_complete=0, submitted_at=NULL WHERE user_id=?",
        (user_id,),
    )
    conn.commit()
    conn.close()


# ── Computed pick bracket ──────────────────────────────────────────────────────

def compute_pick_bracket(user_id: int) -> dict[int, dict]:
    """Build match detail dicts for all 31 bracket picks, keyed by match_id.

    R32 teams come from knockout_matches (standings-synced).
    R16+ teams are derived from the user's upstream picks via winner_to_id routing.
    """
    conn = get_connection()
    structure = _get_structure(conn)
    team_map = _get_team_map(conn)
    conn.close()

    user_picks = get_bracket_picks(user_id)

    # Build reverse lookup: target_match_id → {slot: source_match_id}
    incoming: dict[int, dict[str, int]] = {}
    for mid, m in structure.items():
        wto = m["winner_to_id"]
        if wto:
            incoming.setdefault(wto, {})[m["winner_to_slot"]] = mid

    def _tinfo(tid):
        if not tid:
            return None, None, ""
        t = team_map.get(tid, {})
        return tid, t.get("name"), t.get("flag", "")

    result: dict[int, dict] = {}
    for mid, m in structure.items():
        rnd = m["round"]
        if rnd == "r32":
            h_id, h_name, h_flag = _tinfo(m["home_team_id"])
            a_id, a_name, a_flag = _tinfo(m["away_team_id"])
        else:
            inc = incoming.get(mid, {})
            h_id, h_name, h_flag = _tinfo(user_picks.get(inc.get("home")))
            a_id, a_name, a_flag = _tinfo(user_picks.get(inc.get("away")))

        result[mid] = {
            "match_id":       mid,
            "round":          rnd,
            "bracket_slot":   m["bracket_slot"],
            "match_number":   m["match_number"],
            "home_team_id":   h_id,
            "home_name":      h_name,
            "home_flag":      h_flag,
            "away_team_id":   a_id,
            "away_name":      a_name,
            "away_flag":      a_flag,
            "picked_team_id": user_picks.get(mid),
        }

    return result


# ── Submission ─────────────────────────────────────────────────────────────────

def is_bracket_complete(user_id: int) -> bool:
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM bracket_picks WHERE user_id=?", (user_id,)
    ).fetchone()[0]
    conn.close()
    return count >= REQUIRED_PICKS


def is_bracket_submitted(user_id: int) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT submitted_at FROM bracket_submissions WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return row is not None and row[0] is not None


def submit_bracket(user_id: int) -> tuple[bool, str]:
    if not is_bracket_complete(user_id):
        return False, f"Complete all {REQUIRED_PICKS} picks before submitting."
    lock = get_bracket_lock()
    if lock["is_locked"]:
        return False, "Brackets are locked — contact Admin."
    now = datetime.now().isoformat()
    conn = get_connection()
    conn.execute("""
        INSERT INTO bracket_submissions (user_id, submitted_at, is_complete)
        VALUES (?,?,1)
        ON CONFLICT(user_id)
        DO UPDATE SET submitted_at=excluded.submitted_at, is_complete=1
    """, (user_id, now))
    conn.commit()
    conn.close()
    return True, "Bracket submitted! ✅"


def unsubmit_bracket(user_id: int) -> None:
    lock = get_bracket_lock()
    if lock["is_locked"]:
        raise ValueError("Brackets are locked — cannot unsubmit.")
    conn = get_connection()
    conn.execute(
        "UPDATE bracket_submissions SET submitted_at=NULL WHERE user_id=?", (user_id,)
    )
    conn.commit()
    conn.close()


# ── Admin status ───────────────────────────────────────────────────────────────

def get_bracket_status_all_users() -> list[dict]:
    """Per-user status rows, sorted by most-complete first."""
    conn = get_connection()
    users = conn.execute("SELECT id, name, avatar FROM users ORDER BY id").fetchall()
    pick_counts = {
        r[0]: r[1]
        for r in conn.execute(
            "SELECT user_id, COUNT(*) FROM bracket_picks GROUP BY user_id"
        ).fetchall()
    }
    subs = {
        r[0]: {"submitted_at": r[1], "is_complete": r[2]}
        for r in conn.execute(
            "SELECT user_id, submitted_at, is_complete FROM bracket_submissions"
        ).fetchall()
    }
    conn.close()

    _order = {"submitted": 0, "complete": 1, "in_progress": 2, "not_started": 3}
    result = []
    for uid, name, avatar in users:
        count = pick_counts.get(uid, 0)
        sub = subs.get(uid, {})
        submitted_at = sub.get("submitted_at")
        is_complete = count >= REQUIRED_PICKS

        if submitted_at:
            status = "submitted"
        elif is_complete:
            status = "complete"
        elif count > 0:
            status = "in_progress"
        else:
            status = "not_started"

        result.append({
            "user_id":      uid,
            "name":         name,
            "avatar":       avatar,
            "pick_count":   count,
            "is_complete":  is_complete,
            "is_submitted": bool(submitted_at),
            "submitted_at": submitted_at,
            "status":       status,
        })

    result.sort(key=lambda x: (_order.get(x["status"], 9), -x["pick_count"]))
    return result


# ── Scoring ────────────────────────────────────────────────────────────────────

def score_bracket(user_id: int) -> dict:
    """Score a user's bracket against actual knockout results."""
    user_picks = get_bracket_picks(user_id)
    empty = {
        "total": 0.0, "correct": 0, "picks_total": len(user_picks),
        "semifinalist_bonus": 0, "champion_bonus": 0, "by_round": {},
    }
    if not user_picks:
        return empty

    conn = get_connection()
    completed = conn.execute("""
        SELECT id, round, winner_team_id FROM knockout_matches
        WHERE status='completed' AND winner_team_id IS NOT NULL AND id != 131
    """).fetchall()
    conn.close()

    by_round: dict[str, int] = {}
    correct = sf_bonus = champ_bonus = 0
    total = 0.0

    for mid, rnd, actual_winner in completed:
        if user_picks.get(mid) == actual_winner:
            correct += 1
            total += 1.0
            by_round[rnd] = by_round.get(rnd, 0) + 1
            if mid in QF_MATCH_IDS:
                sf_bonus += 2
                total += 2.0
            if mid == FINAL_MATCH_ID:
                champ_bonus += 5
                total += 5.0

    return {
        "total":              total,
        "correct":            correct,
        "picks_total":        len(user_picks),
        "semifinalist_bonus": sf_bonus,
        "champion_bonus":     champ_bonus,
        "by_round":           by_round,
    }


def get_bracket_leaderboard() -> list[dict]:
    conn = get_connection()
    users = conn.execute(
        "SELECT id, name, avatar, theme_color FROM users ORDER BY id"
    ).fetchall()
    has_picks = {
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT user_id FROM bracket_picks"
        ).fetchall()
    }
    conn.close()

    scores = []
    for uid, name, avatar, color in users:
        if uid not in has_picks:
            continue
        s = score_bracket(uid)
        s.update({"user_id": uid, "name": name, "avatar": avatar, "color": color})
        scores.append(s)

    scores.sort(key=lambda x: (-x["total"], x["name"]))
    for i, s in enumerate(scores):
        s["rank"] = i + 1
    return scores


def get_actual_results() -> dict[int, int]:
    """Return {knockout_match_id: winner_team_id} for completed matches (excl. 131)."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, winner_team_id FROM knockout_matches
        WHERE status='completed' AND winner_team_id IS NOT NULL AND id != 131
    """).fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}
