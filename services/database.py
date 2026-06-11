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

    if cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        df = pd.read_csv(os.path.join(DATA_DIR, 'users.csv'))
        df.to_sql('users', conn, if_exists='append', index=False)

    conn.commit()
    conn.close()
