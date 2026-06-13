import pandas as pd
from datetime import date, datetime, timedelta
from services.database import get_connection


def get_all_matches() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM matches ORDER BY match_date, kickoff_time_et",
        conn
    )
    conn.close()
    return df


def get_upcoming_matches(n: int = 5) -> pd.DataFrame:
    conn = get_connection()
    today = (datetime.utcnow() - timedelta(hours=7)).date().isoformat()  # PDT = UTC-7
    df = pd.read_sql(
        "SELECT * FROM matches WHERE status='scheduled' AND match_date >= ? "
        "ORDER BY match_date, kickoff_time_et LIMIT ?",
        conn, params=(today, n)
    )
    conn.close()
    return df


def get_recent_completed_matches(n: int = 5) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM matches WHERE status='completed' "
        "ORDER BY match_date DESC, kickoff_time_et DESC LIMIT ?",
        conn, params=(n,)
    )
    conn.close()
    return df


def get_match_by_id(match_id: int):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM matches WHERE id = ?", conn, params=(match_id,))
    conn.close()
    return df.iloc[0] if len(df) > 0 else None


def get_matches_by_group(group_letter: str) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM matches WHERE group_letter = ? ORDER BY match_date, kickoff_time_et",
        conn, params=(group_letter,)
    )
    conn.close()
    return df


def get_matches_by_team(team_name: str) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM matches WHERE home_team = ? OR away_team = ? "
        "ORDER BY match_date, kickoff_time_et",
        conn, params=(team_name, team_name)
    )
    conn.close()
    return df


def update_match_score(match_id: int, home_score: int, away_score: int):
    conn = get_connection()
    conn.execute(
        "UPDATE matches SET home_score=?, away_score=?, status='completed' WHERE id=?",
        (home_score, away_score, match_id)
    )
    conn.commit()
    conn.close()
    _log_points_earned(match_id, home_score, away_score)


def reset_match(match_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE matches SET home_score=NULL, away_score=NULL, status='scheduled' WHERE id=?",
        (match_id,)
    )
    conn.commit()
    conn.close()


def _log_points_earned(match_id: int, home_score: int, away_score: int):
    """After a score is saved, log points_earned for any user who earned points."""
    from services.activity import log_activity
    conn = get_connection()
    picks = conn.execute("""
        SELECT p.user_id, p.picked_team, m.home_team, m.away_team
        FROM picks p
        JOIN matches m ON p.match_id = m.id
        WHERE p.match_id = ?
    """, (match_id,)).fetchall()
    conn.close()

    for user_id, picked_team, home_team, away_team in picks:
        if home_score == away_score:
            pts = 0.5
        elif (home_score > away_score and picked_team == home_team) or \
             (away_score > home_score and picked_team == away_team):
            pts = 1.0
        else:
            pts = 0.0

        if pts > 0:
            log_activity(user_id, 'points_earned',
                        country_name=picked_team, match_id=match_id,
                        message=f"earned {pts:.1f}pts with {picked_team}")
