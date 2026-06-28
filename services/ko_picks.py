"""Live knockout picks service.

Each family member picks the winner of each knockout match before it starts,
just like group-stage daily picks — but stored separately (knockout_live_picks)
and scored at round-specific point values.

No draw option: every knockout match has a definitive winner.

Note on pick locking: no kickoff-time lock is enforced in Phase 6D.1.
Users can change their pick at any time until the result is entered.
This mirrors current group-stage behavior ("no pick locking in version 1").
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from services.database import get_connection

# ── Round point values ─────────────────────────────────────────────────────────

KO_ROUND_POINTS: dict[str, int] = {
    "r32":         2,
    "r16":         3,
    "qf":          4,
    "sf":          5,
    "third_place": 5,
    "final":       8,
}

KO_ROUND_LABELS: dict[str, str] = {
    "r32":         "Round of 32",
    "r16":         "Round of 16",
    "qf":          "Quarterfinals",
    "sf":          "Semifinals",
    "third_place": "3rd Place",
    "final":       "Final",
}


# ── Self-initializing schema ───────────────────────────────────────────────────

def _boot() -> None:
    from services.database import init_db
    init_db()

_boot()


# ── Save / retrieve picks ──────────────────────────────────────────────────────

def save_ko_pick(user_id: int, knockout_match_id: int, team_id: int) -> None:
    """Upsert a live knockout pick.

    Raises ValueError if:
    - The match is completed (result already entered)
    - Either team slot is still TBD (team_id not yet known)
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT status, home_team_id, away_team_id FROM knockout_matches WHERE id=?",
        (knockout_match_id,),
    ).fetchone()
    conn.close()

    if row is None:
        raise ValueError(f"Knockout match {knockout_match_id} not found.")
    status, home_id, away_id = row
    if status == "completed":
        raise ValueError("Match is already completed — picks are frozen.")
    if home_id is None or away_id is None:
        raise ValueError("Both teams must be known before picks are allowed.")
    if team_id not in (home_id, away_id):
        raise ValueError(f"team_id {team_id} is not playing in match {knockout_match_id}.")

    now = datetime.now().isoformat()
    conn = get_connection()
    conn.execute("""
        INSERT INTO knockout_live_picks (user_id, knockout_match_id, picked_team_id, created_at, updated_at)
        VALUES (?,?,?,?,?)
        ON CONFLICT(user_id, knockout_match_id)
        DO UPDATE SET picked_team_id=excluded.picked_team_id, updated_at=excluded.updated_at
    """, (user_id, knockout_match_id, team_id, now, now))
    conn.commit()
    conn.close()


def get_ko_pick(user_id: int, knockout_match_id: int) -> int | None:
    """Return the picked team_id for one user/match, or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT picked_team_id FROM knockout_live_picks WHERE user_id=? AND knockout_match_id=?",
        (user_id, knockout_match_id),
    ).fetchone()
    conn.close()
    return row[0] if row else None


def get_ko_picks_for_match(knockout_match_id: int) -> list[dict]:
    """Return all family picks for one knockout match.

    Each dict: {user_id, name, avatar, theme_color, picked_team_id, team_name, team_flag}
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT klp.user_id, u.name, u.avatar, u.theme_color,
               klp.picked_team_id, t.name AS team_name, t.flag_emoji
        FROM knockout_live_picks klp
        JOIN users u ON klp.user_id = u.id
        JOIN teams t ON klp.picked_team_id = t.id
        WHERE klp.knockout_match_id = ?
        ORDER BY u.id
    """, (knockout_match_id,)).fetchall()
    conn.close()
    return [
        {
            "user_id":       r[0],
            "name":          r[1],
            "avatar":        r[2],
            "theme_color":   r[3],
            "picked_team_id": r[4],
            "team_name":     r[5],
            "team_flag":     r[6] or "",
        }
        for r in rows
    ]


def get_ko_picks_for_user(user_id: int) -> list[dict]:
    """All KO live picks for one user, with match and team info."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT klp.knockout_match_id, klp.picked_team_id,
               km.round, km.match_number, km.status,
               km.home_team_id, km.away_team_id,
               km.home_score, km.away_score, km.winner_team_id,
               km.match_date, km.kickoff_time_et, km.venue, km.city,
               th.name AS home_name, th.flag_emoji AS home_flag,
               ta.name AS away_name, ta.flag_emoji AS away_flag,
               tp.name AS picked_name, tp.flag_emoji AS picked_flag
        FROM knockout_live_picks klp
        JOIN knockout_matches km ON klp.knockout_match_id = km.id
        LEFT JOIN teams th ON km.home_team_id = th.id
        LEFT JOIN teams ta ON km.away_team_id = ta.id
        LEFT JOIN teams tp ON klp.picked_team_id = tp.id
        WHERE klp.user_id = ?
        ORDER BY km.match_date, km.kickoff_time_et
    """, (user_id,)).fetchall()
    conn.close()
    cols = [
        "knockout_match_id", "picked_team_id",
        "round", "match_number", "status",
        "home_team_id", "away_team_id",
        "home_score", "away_score", "winner_team_id",
        "match_date", "kickoff_time_et", "venue", "city",
        "home_name", "home_flag", "away_name", "away_flag",
        "picked_name", "picked_flag",
    ]
    return [dict(zip(cols, r)) for r in rows]


# ── Scoring ────────────────────────────────────────────────────────────────────

def score_ko_live(user_id: int) -> dict:
    """Score all live KO picks for a user.

    Returns:
        total          — total points earned
        correct        — count of correct picks
        picks_total    — count of picks against completed matches
        by_round       — {round_key: points_earned_in_round}
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT km.round, klp.picked_team_id, km.winner_team_id
        FROM knockout_live_picks klp
        JOIN knockout_matches km ON klp.knockout_match_id = km.id
        WHERE klp.user_id = ?
          AND km.status = 'completed'
          AND km.winner_team_id IS NOT NULL
    """, (user_id,)).fetchall()
    conn.close()

    total = 0.0
    correct = 0
    by_round: dict[str, float] = {}

    for rnd, picked_id, winner_id in rows:
        pts = KO_ROUND_POINTS.get(rnd, 0)
        if picked_id == winner_id:
            correct += 1
            total += pts
            by_round[rnd] = by_round.get(rnd, 0.0) + pts

    return {
        "total":       total,
        "correct":     correct,
        "picks_total": len(rows),
        "by_round":    by_round,
    }


def get_ko_live_leaderboard() -> list[dict]:
    """KO live scores for all users, sorted by total descending."""
    conn = get_connection()
    users = conn.execute(
        "SELECT id, name, avatar, theme_color FROM users ORDER BY id"
    ).fetchall()
    conn.close()

    scores = []
    for uid, name, avatar, color in users:
        s = score_ko_live(uid)
        scores.append({
            "user_id": uid,
            "name":    name,
            "avatar":  avatar,
            "color":   color,
            **s,
        })
    scores.sort(key=lambda x: (-x["total"], x["name"]))
    for i, s in enumerate(scores):
        s["rank"] = i + 1
    return scores


# ── KO match data for schedule/display ────────────────────────────────────────

def get_all_ko_matches_display() -> list[dict]:
    """All knockout matches with team info, for schedule rendering.

    Each dict has:
      id, round, round_label, points, match_number, bracket_slot, status,
      home_team_id, away_team_id, home_name, away_name, home_flag, away_flag,
      home_score, away_score, winner_team_id, winner_name,
      match_date, kickoff_time_et, venue, city, host_country
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT km.id, km.round, km.match_number, km.bracket_slot, km.status,
               km.home_team_id, km.away_team_id,
               km.home_score, km.away_score, km.winner_team_id,
               km.home_penalties, km.away_penalties,
               km.match_date, km.kickoff_time_et, km.venue, km.city, km.host_country,
               th.name AS home_name, th.flag_emoji AS home_flag,
               ta.name AS away_name, ta.flag_emoji AS away_flag,
               tw.name AS winner_name
        FROM knockout_matches km
        LEFT JOIN teams th ON km.home_team_id = th.id
        LEFT JOIN teams ta ON km.away_team_id = ta.id
        LEFT JOIN teams tw ON km.winner_team_id = tw.id
        ORDER BY km.match_date, km.kickoff_time_et, km.bracket_slot
    """).fetchall()
    conn.close()

    cols = [
        "id", "round", "match_number", "bracket_slot", "status",
        "home_team_id", "away_team_id",
        "home_score", "away_score", "winner_team_id",
        "home_penalties", "away_penalties",
        "match_date", "kickoff_time_et", "venue", "city", "host_country",
        "home_name", "home_flag", "away_name", "away_flag", "winner_name",
    ]
    result = []
    for r in rows:
        d = dict(zip(cols, r))
        d["round_label"] = KO_ROUND_LABELS.get(d["round"], d["round"])
        d["points"]      = KO_ROUND_POINTS.get(d["round"], 0)
        d["home_flag"]   = d["home_flag"] or ""
        d["away_flag"]   = d["away_flag"] or ""
        d["home_name"]   = d["home_name"] or None
        d["away_name"]   = d["away_name"] or None
        # Penalty display string (only for tied completed matches)
        hs, as_ = d.get("home_score"), d.get("away_score")
        hp, ap  = d.get("home_penalties"), d.get("away_penalties")
        if (d["status"] == "completed" and hs is not None and as_ is not None
                and int(hs) == int(as_) and hp is not None and ap is not None):
            d["pens_str"] = f"{int(hp)}–{int(ap)} pens"
        else:
            d["pens_str"] = ""
        result.append(d)
    return result
