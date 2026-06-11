import pandas as pd
from services.database import get_connection


def get_all_teams() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM teams ORDER BY group_letter, name", conn)
    conn.close()
    return df


def get_team_by_name(name: str):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM teams WHERE name = ?", conn, params=(name,))
    conn.close()
    return df.iloc[0] if len(df) > 0 else None


def get_teams_by_group(group_letter: str) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM teams WHERE group_letter = ? ORDER BY fifa_ranking",
        conn, params=(group_letter,)
    )
    conn.close()
    return df


def get_all_group_letters() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT group_letter FROM teams ORDER BY group_letter"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_flag(team_name: str) -> str:
    conn = get_connection()
    row = conn.execute(
        "SELECT flag_emoji FROM teams WHERE name = ?", (team_name,)
    ).fetchone()
    conn.close()
    return row[0] if row else "🏳️"
