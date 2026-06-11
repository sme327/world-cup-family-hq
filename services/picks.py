import pandas as pd
from datetime import datetime
from services.database import get_connection


def get_picks_for_match(match_id: int) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql("""
        SELECT p.*, u.name AS user_name, u.avatar, u.theme_color
        FROM picks p
        JOIN users u ON p.user_id = u.id
        WHERE p.match_id = ?
        ORDER BY u.id
    """, conn, params=(match_id,))
    conn.close()
    return df


def get_picks_for_user(user_id: int) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql("""
        SELECT p.*, m.home_team, m.away_team, m.match_date, m.kickoff_time_et,
               m.home_score, m.away_score, m.status, m.group_letter
        FROM picks p
        JOIN matches m ON p.match_id = m.id
        WHERE p.user_id = ?
        ORDER BY m.match_date, m.kickoff_time_et
    """, conn, params=(user_id,))
    conn.close()
    return df


def save_pick(user_id: int, match_id: int, picked_team: str):
    now = datetime.now().isoformat()
    conn = get_connection()

    # Check if this is their very first pick ever (before inserting)
    existing_count = conn.execute(
        "SELECT COUNT(*) FROM picks WHERE user_id=?", (user_id,)
    ).fetchone()[0]

    conn.execute("""
        INSERT INTO picks (user_id, match_id, picked_team, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, match_id)
        DO UPDATE SET picked_team = excluded.picked_team, created_at = excluded.created_at
    """, (user_id, match_id, picked_team, now))
    conn.commit()
    conn.close()

    # Only log the very first pick as a meaningful activity moment
    if existing_count == 0:
        from services.activity import log_activity
        log_activity(user_id, 'first_pick',
                     country_name=picked_team, match_id=match_id,
                     message=f"made their very first pick: {picked_team}!")


def get_all_picks() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql("""
        SELECT p.*, u.name AS user_name, u.avatar, u.theme_color,
               m.home_team, m.away_team, m.match_date, m.home_score, m.away_score, m.status
        FROM picks p
        JOIN users u ON p.user_id = u.id
        JOIN matches m ON p.match_id = m.id
        ORDER BY m.match_date, m.kickoff_time_et, u.id
    """, conn)
    conn.close()
    return df


def get_all_users() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM users ORDER BY id", conn)
    conn.close()
    return df
