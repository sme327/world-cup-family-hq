import re
import sqlite3
import pandas as pd
from services.database import get_connection

_ROUND_ORDER = ["r32", "r16", "qf", "sf", "third_place", "final"]
_ROUND_LABELS = {
    "r32": "Round of 32",
    "r16": "Round of 16",
    "qf": "Quarterfinals",
    "sf": "Semifinals",
    "third_place": "3rd Place",
    "final": "Final",
}
_EXPECTED_COUNTS = {"r32": 16, "r16": 8, "qf": 4, "sf": 2, "final": 1, "third_place": 1}

# Matches source strings like "1st Group A", "2nd Group B", "3rd Group L"
_SOURCE_RE = re.compile(r'^(\d+)(?:st|nd|rd|th)\s+Group\s+([A-L])$', re.IGNORECASE)

_QUERY = """
    SELECT
        km.id, km.round, km.bracket_slot,
        km.home_score, km.away_score, km.status,
        km.home_source, km.away_source,
        km.match_date, km.kickoff_time_et,
        km.venue, km.city, km.match_number,
        km.winner_to_id, km.loser_to_id,
        km.winner_to_slot, km.loser_to_slot,
        km.home_team_id, km.away_team_id, km.winner_team_id,
        th.name AS home_name, th.flag_emoji AS home_flag,
        ta.name AS away_name, ta.flag_emoji AS away_flag,
        tw.name AS winner_name
    FROM knockout_matches km
    LEFT JOIN teams th ON km.home_team_id = th.id
    LEFT JOIN teams ta ON km.away_team_id = ta.id
    LEFT JOIN teams tw ON km.winner_team_id = tw.id
    ORDER BY km.round, km.bracket_slot
"""


# ── R32 auto-population from group standings ──────────────────────────────────

def _resolve_slot(source: str, standings: dict, team_map: dict) -> tuple[bool, int | None]:
    """Parse a group-position source string and resolve it to a team ID.

    Returns (should_update, team_id):
      (False, None)   parse error — leave existing DB value untouched
      (True,  None)   group has no results yet — set slot to NULL (TBD)
      (True,  int)    resolved team ID from current standings
    """
    if not source:
        return False, None

    m = _SOURCE_RE.match(source.strip())
    if not m:
        return False, None  # Not a group-position string (e.g., "W M74") — skip

    pos   = int(m.group(1)) - 1   # 1-based → 0-indexed
    group = m.group(2).upper()

    group_rows = standings.get(group, [])
    if not group_rows:
        return True, None  # Group unknown — TBD

    # If no matches have been played yet, leave TBD rather than showing an
    # alphabetical sort artifact (all teams at 0 pts would sort by name).
    games_played = sum(r["p"] for r in group_rows)
    if games_played == 0:
        return True, None

    if pos >= len(group_rows):
        return True, None  # Position out of range — TBD

    team_name = group_rows[pos]["team"]
    team_id   = team_map.get(team_name)
    return True, team_id   # team_id may still be None if name not in DB


def _sync_r32_from_standings() -> None:
    """Auto-fill R32 home_team_id / away_team_id from current group standings.

    Called at the start of get_knockout_rounds() and get_knockout_admin_data().
    Rules:
      - Only touches round='r32' matches with status='scheduled'.
      - Uses get_group_standings() (actual results from the matches table).
      - If a group has no completed matches: slot → NULL (TBD).
      - If a group is partial or complete: slot → current or confirmed qualifier.
      - If source string can't be parsed (e.g., "W M74"): leave slot untouched.
      - Never touches R16+ matches.
    """
    try:
        from services.scoring import get_group_standings
        standings = get_group_standings()
    except Exception:
        return  # Don't crash if standings unavailable

    conn = get_connection()
    cur  = conn.cursor()

    # Build team name → id mapping
    team_map: dict[str, int] = {
        name: tid
        for tid, name in cur.execute("SELECT id, name FROM teams").fetchall()
    }

    # Only scheduled R32 matches — never overwrite a completed match's teams
    r32 = cur.execute("""
        SELECT id, home_source, away_source
        FROM knockout_matches
        WHERE round = 'r32' AND status = 'scheduled'
    """).fetchall()

    for mid, h_src, a_src in r32:
        h_update, h_id = _resolve_slot(h_src or "", standings, team_map)
        a_update, a_id = _resolve_slot(a_src or "", standings, team_map)

        if h_update:
            cur.execute("UPDATE knockout_matches SET home_team_id=? WHERE id=?", (h_id, mid))
        if a_update:
            cur.execute("UPDATE knockout_matches SET away_team_id=? WHERE id=?", (a_id, mid))

    conn.commit()
    conn.close()


# ── Bracket data loader ───────────────────────────────────────────────────────

def _empty_match_dict(match_id=None) -> dict:
    return {
        "match_id": match_id,
        "team1": None, "team2": None,
        "flag1": None, "flag2": None,
        "score1": None, "score2": None,
        "winner": None,
    }


def get_knockout_rounds() -> dict:
    """Return bracket data matching the shape expected by render_knockout_bracket_shell().

    Automatically syncs R32 teams from current group standings before returning.
    Falls back to empty placeholders if the table doesn't exist.
    """
    _sync_r32_from_standings()

    rounds: dict = {k: [] for k in _EXPECTED_COUNTS}

    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        rows = conn.execute(_QUERY).fetchall()
        conn.close()
    except Exception:
        return {k: [_empty_match_dict(f"{k}_{i+1}") for i in range(n)]
                for k, n in _EXPECTED_COUNTS.items()}

    for row in rows:
        rnd = row["round"]
        if rnd not in rounds:
            continue

        h_name = row["home_name"]
        a_name = row["away_name"]
        w_name = row["winner_name"]
        hs     = row["home_score"]
        as_    = row["away_score"]
        is_complete = row["status"] == "completed" and hs is not None

        if w_name:
            winner = "team1" if w_name == h_name else "team2"
        else:
            winner = None

        rounds[rnd].append({
            "match_id": row["id"],
            "team1":    h_name,
            "team2":    a_name,
            "flag1":    row["home_flag"],
            "flag2":    row["away_flag"],
            "score1":   int(hs)  if is_complete and hs  is not None else None,
            "score2":   int(as_) if is_complete and as_ is not None else None,
            "winner":   winner,
        })

    # Pad any round that came back short (shouldn't happen with a clean seed)
    for rnd, count in _EXPECTED_COUNTS.items():
        while len(rounds[rnd]) < count:
            rounds[rnd].append(_empty_match_dict(f"{rnd}_pad_{len(rounds[rnd])+1}"))

    return rounds


def get_knockout_admin_data(round_name: str = None) -> list[dict]:
    """Return knockout match data for the admin UI.

    Syncs R32 teams from standings first so the admin sees current qualifiers.
    """
    _sync_r32_from_standings()

    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        if round_name:
            rows = conn.execute(
                _QUERY.replace("ORDER BY", "WHERE km.round = ? ORDER BY"),
                (round_name,)
            ).fetchall()
        else:
            rows = conn.execute(_QUERY).fetchall()
        conn.close()
    except Exception:
        return []

    return [dict(row) for row in rows]


# ── Score entry and advancement ───────────────────────────────────────────────

def save_knockout_result(match_id: int, home_score: int, away_score: int,
                         winner_team_id: int) -> None:
    """Save a knockout match result and advance the winner to the next round.

    For SF matches, also routes the loser to the 3rd place match.
    """
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        UPDATE knockout_matches
        SET home_score=?, away_score=?, winner_team_id=?, status='completed'
        WHERE id=?
    """, (home_score, away_score, winner_team_id, match_id))

    row = cur.execute("""
        SELECT winner_to_id, winner_to_slot, loser_to_id, loser_to_slot,
               home_team_id, away_team_id
        FROM knockout_matches WHERE id=?
    """, (match_id,)).fetchone()

    if row:
        w_to_id, w_to_slot, l_to_id, l_to_slot, home_id, away_id = row

        if w_to_id and w_to_slot:
            col = "home_team_id" if w_to_slot == "home" else "away_team_id"
            cur.execute(f"UPDATE knockout_matches SET {col}=? WHERE id=?",
                        (winner_team_id, w_to_id))

        if l_to_id and l_to_slot:
            loser_id = away_id if winner_team_id == home_id else home_id
            if loser_id:
                col = "home_team_id" if l_to_slot == "home" else "away_team_id"
                cur.execute(f"UPDATE knockout_matches SET {col}=? WHERE id=?",
                            (loser_id, l_to_id))

    conn.commit()
    conn.close()


def reset_knockout_result(match_id: int) -> tuple[bool, str]:
    """Clear a knockout match result.

    Returns (success, message).
    Refuses if a downstream match already has a result — admin must reset
    that match first. No silent cascade.
    """
    conn = get_connection()
    cur  = conn.cursor()

    row = cur.execute("""
        SELECT winner_to_id, winner_to_slot, loser_to_id, loser_to_slot,
               winner_team_id, home_team_id, away_team_id
        FROM knockout_matches WHERE id=?
    """, (match_id,)).fetchone()

    if not row:
        conn.close()
        return False, "Match not found."

    w_to_id, w_to_slot, l_to_id, l_to_slot, cur_winner, home_id, away_id = row

    if w_to_id:
        ds = cur.execute(
            "SELECT status FROM knockout_matches WHERE id=?", (w_to_id,)
        ).fetchone()
        if ds and ds[0] == "completed":
            conn.close()
            return False, (
                f"Cannot reset: the next-round match (ID {w_to_id}) already has a result. "
                "Reset that match first."
            )

    if l_to_id:
        ds_l = cur.execute(
            "SELECT status FROM knockout_matches WHERE id=?", (l_to_id,)
        ).fetchone()
        if ds_l and ds_l[0] == "completed":
            conn.close()
            return False, (
                f"Cannot reset: the 3rd-place match (ID {l_to_id}) already has a result. "
                "Reset that match first."
            )

    # Safe to reset
    cur.execute("""
        UPDATE knockout_matches
        SET home_score=NULL, away_score=NULL, winner_team_id=NULL, status='scheduled'
        WHERE id=?
    """, (match_id,))

    # Clear the winner slot in the downstream match
    if w_to_id and w_to_slot and cur_winner:
        col = "home_team_id" if w_to_slot == "home" else "away_team_id"
        cur.execute(f"UPDATE knockout_matches SET {col}=NULL WHERE id=?", (w_to_id,))

    # Clear the loser slot in the 3rd-place match
    if l_to_id and l_to_slot and cur_winner:
        loser_id = away_id if cur_winner == home_id else home_id
        if loser_id:
            col = "home_team_id" if l_to_slot == "home" else "away_team_id"
            cur.execute(f"UPDATE knockout_matches SET {col}=NULL WHERE id=?", (l_to_id,))

    conn.commit()
    conn.close()
    return True, "Match reset to scheduled."
