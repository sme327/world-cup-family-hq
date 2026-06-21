import sqlite3
import os
import pandas as pd

_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(_DIR, '..', 'data', 'worldcup.db')
DATA_DIR = os.path.join(_DIR, '..', 'data')

_SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    country_code    TEXT,
    flag_emoji      TEXT,
    group_letter    TEXT,
    confederation   TEXT,
    fifa_ranking    INTEGER,
    coach           TEXT,
    captain         TEXT,
    capital         TEXT,
    population      TEXT,
    languages       TEXT,
    currency        TEXT,
    wc_appearances  INTEGER,
    best_finish     TEXT,
    fun_fact        TEXT,
    animals         TEXT,
    foods           TEXT,
    landmarks       TEXT,
    cheer_reasons   TEXT,
    mls_connections TEXT,
    key_players     TEXT
);

CREATE TABLE IF NOT EXISTS matches (
    id              INTEGER PRIMARY KEY,
    match_number    INTEGER,
    group_letter    TEXT,
    home_team       TEXT,
    away_team       TEXT,
    match_date      TEXT,
    kickoff_time_et TEXT,
    venue           TEXT,
    city            TEXT,
    host_country    TEXT,
    home_score      INTEGER,
    away_score      INTEGER,
    status          TEXT DEFAULT 'scheduled'
);

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    avatar      TEXT,
    theme_color TEXT,
    picks_only  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS picks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    match_id    INTEGER NOT NULL,
    picked_team TEXT NOT NULL,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (match_id) REFERENCES matches(id),
    UNIQUE(user_id, match_id)
);

CREATE TABLE IF NOT EXISTS discoveries (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    country_name     TEXT NOT NULL,
    first_visited_at TEXT NOT NULL,
    visit_count      INTEGER DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, country_name)
);

CREATE TABLE IF NOT EXISTS activity_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp      TEXT NOT NULL,
    user_id        INTEGER NOT NULL,
    event_type     TEXT NOT NULL,
    country_name   TEXT,
    match_id       INTEGER,
    achievement_id TEXT,
    message        TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_achievements (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    achievement_id TEXT NOT NULL,
    unlocked_at    TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, achievement_id)
);

CREATE TABLE IF NOT EXISTS family_achievements (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    achievement_id TEXT NOT NULL UNIQUE,
    unlocked_at    TEXT NOT NULL
);
"""


def get_connection():
    return sqlite3.connect(os.path.abspath(DB_PATH))


def _restore_from_backup(cursor) -> tuple[int, int]:
    """Restore picks and scores from committed backup CSVs.
    Called automatically when the picks table is empty (e.g. after a cloud sleep/wake cycle).
    Handles both the full backup format (with user_id/match_id) and the Admin download
    format (with user_name/home_team/away_team/match_date). Returns (picks_restored, scores_restored).
    """
    picks_path  = os.path.join(DATA_DIR, 'picks_backup.csv')
    scores_path = os.path.join(DATA_DIR, 'scores_backup.csv')
    n_picks = n_scores = 0

    if os.path.exists(picks_path):
        df = pd.read_csv(picks_path)
        has_ids = 'user_id' in df.columns and 'match_id' in df.columns
        for _, row in df.iterrows():
            try:
                if has_ids:
                    uid = int(row['user_id'])
                    mid = int(row['match_id'])
                else:
                    # Look up IDs by name/match — handles Admin-format CSV
                    u = cursor.execute(
                        "SELECT id FROM users WHERE name=?", (str(row['user_name']),)
                    ).fetchone()
                    m = cursor.execute(
                        "SELECT id FROM matches WHERE home_team=? AND away_team=? AND match_date=?",
                        (str(row['home_team']), str(row['away_team']), str(row['match_date'])),
                    ).fetchone()
                    if not u or not m:
                        continue
                    uid, mid = u[0], m[0]
                cursor.execute(
                    "INSERT OR IGNORE INTO picks (user_id, match_id, picked_team) VALUES (?,?,?)",
                    (uid, mid, str(row['picked_team'])),
                )
                n_picks += cursor.rowcount
            except Exception:
                pass

    if os.path.exists(scores_path):
        df = pd.read_csv(scores_path)
        for _, row in df.iterrows():
            try:
                cursor.execute(
                    """UPDATE matches SET home_score=?, away_score=?, status='completed'
                       WHERE home_team=? AND away_team=? AND match_date=?""",
                    (int(row['home_score']), int(row['away_score']),
                     str(row['home_team']), str(row['away_team']), str(row['match_date'])),
                )
                if cursor.rowcount:
                    n_scores += 1
            except Exception:
                pass

    return n_picks, n_scores


def init_db():
    conn = get_connection()
    conn.executescript(_SCHEMA)
    conn.commit()
    cursor = conn.cursor()

    if cursor.execute("SELECT COUNT(*) FROM teams").fetchone()[0] == 0:
        df = pd.read_csv(os.path.join(DATA_DIR, 'teams.csv'))
        df.to_sql('teams', conn, if_exists='append', index=False)

    if cursor.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 0:
        df = pd.read_csv(os.path.join(DATA_DIR, 'world_cup_2026_matches.csv'))
        df.to_sql('matches', conn, if_exists='append', index=False)
    else:
        # Always sync schedule fields from CSV so time/venue corrections take effect
        # without a full DB reset. Preserves scores and status.
        df = pd.read_csv(os.path.join(DATA_DIR, 'world_cup_2026_matches.csv'))
        for _, row in df.iterrows():
            cursor.execute("""
                UPDATE matches
                SET match_date=?, kickoff_time_et=?, venue=?, city=?, host_country=?
                WHERE id=?
            """, (str(row['match_date']), str(row['kickoff_time_et']),
                  str(row['venue']), str(row['city']), str(row['host_country']),
                  int(row['id'])))

    # Always upsert users from CSV so new family members appear without a DB reset
    df = pd.read_csv(os.path.join(DATA_DIR, 'users.csv'))
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT OR REPLACE INTO users (id, name, avatar, theme_color, picks_only)
            VALUES (?, ?, ?, ?, ?)
        """, (int(row['id']), str(row['name']), str(row['avatar']),
              str(row['theme_color']), int(row.get('picks_only', 0))))

    # Auto-restore picks + scores from backup CSVs when the DB is freshly created
    # (catches Streamlit Cloud sleep/wake cycles where worldcup.db is rebuilt from scratch)
    if cursor.execute("SELECT COUNT(*) FROM picks").fetchone()[0] == 0:
        picks_path = os.path.join(DATA_DIR, 'picks_backup.csv')
        if os.path.exists(picks_path):
            n_picks, n_scores = _restore_from_backup(cursor)
            conn.commit()

    conn.commit()
    conn.close()
