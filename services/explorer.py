"""Explorer service: Discovery Race scores, streaks, momentum, and badge data."""
from __future__ import annotations
import pandas as pd
from datetime import date, datetime, timedelta
from services.database import get_connection
from services.passport import (
    get_discoveries, get_cheered_for, get_won_with,
    get_continent_progress, get_continent_teams,
)
from services.achievements import get_user_achievements


# ── Badge definitions (threshold, title, emoji) ───────────────────────────────
BADGES = [
    (0,  "Scout",          "🗺️"),
    (10, "Explorer",       "🧭"),
    (25, "World Traveler", "✈️"),
    (40, "Globe Trotter",  "🌍"),
    (60, "Master Explorer","👑"),
]

CONTINENT_ORDER = [
    "North America", "South America", "Europe", "Africa", "Asia", "Oceania",
]

CONTINENT_EMOJI = {
    "North America": "🌎",
    "South America": "🌎",
    "Europe":        "🌍",
    "Africa":        "🌍",
    "Asia":          "🌏",
    "Oceania":       "🌏",
}

MILESTONES = [5, 10, 20, 30, 40, 48]

_MILESTONE_LABELS = {
    5:  "First Adventure",
    10: "Double Digits",
    20: "Globetrotter",
    30: "World Explorer",
    40: "Almost There",
    48: "Complete Collection! 🎉",
}


# ── Badge helpers ─────────────────────────────────────────────────────────────

def get_badge(score: int) -> tuple[str, str]:
    """Return (title, emoji) for the given Explorer Score."""
    title, emoji = BADGES[0][1], BADGES[0][2]
    for threshold, t, e in BADGES:
        if score >= threshold:
            title, emoji = t, e
    return title, emoji


def get_badge_progress(score: int) -> dict:
    """Return current badge, next badge, progress fraction, and pts to next level."""
    idx = 0
    for i, (threshold, _, __) in enumerate(BADGES):
        if score >= threshold:
            idx = i
    cur = BADGES[idx]
    nxt = BADGES[idx + 1] if idx + 1 < len(BADGES) else None
    if nxt:
        span     = nxt[0] - cur[0]
        progress = min(1.0, (score - cur[0]) / span) if span > 0 else 1.0
        pts_left = max(0, nxt[0] - score)
    else:
        progress = 1.0
        pts_left = 0
    return {
        'current_title':     cur[1],
        'current_emoji':     cur[2],
        'current_threshold': cur[0],
        'next_title':        nxt[1] if nxt else None,
        'next_emoji':        nxt[2] if nxt else None,
        'next_threshold':    nxt[0] if nxt else None,
        'progress':          progress,
        'pts_to_next':       pts_left,
    }


# ── Core score ────────────────────────────────────────────────────────────────

def get_explorer_score(user_id: int) -> dict:
    """Compute Explorer Score and component breakdown for one user."""
    disc_df    = get_discoveries(user_id)
    discovered = len(disc_df)
    cheered    = len(get_cheered_for(user_id))
    won        = len(get_won_with(user_id))

    ach_df = get_user_achievements(user_id)
    ach    = len(ach_df) if not ach_df.empty else 0

    cont  = get_continent_progress(user_id)
    conts = sum(1 for d in cont.values() if d['total'] > 0 and d['discovered'] == d['total'])

    score = discovered * 1 + cheered * 2 + won * 3 + ach * 3 + conts * 10
    badge_title, badge_emoji = get_badge(score)
    bp = get_badge_progress(score)

    return {
        'score':                score,
        'discovered':           discovered,
        'cheered':              cheered,
        'won':                  won,
        'achievements':         ach,
        'continents_completed': conts,
        'badge_title':          badge_title,
        'badge_emoji':          badge_emoji,
        'badge_progress':       bp,
    }


# ── Leaderboard ───────────────────────────────────────────────────────────────

def get_explorer_leaderboard() -> list[dict]:
    """All passport users sorted by Explorer Score (desc), name (asc) for ties."""
    conn = get_connection()
    users = pd.read_sql(
        "SELECT * FROM users WHERE picks_only = 0 OR picks_only IS NULL ORDER BY id",
        conn,
    )
    conn.close()

    rows = []
    for _, u in users.iterrows():
        uid  = int(u['id'])
        data = get_explorer_score(uid)
        data.update({
            'user_id':     uid,
            'name':        u['name'],
            'avatar':      u['avatar'],
            'theme_color': str(u.get('theme_color', '#94A3B8') or '#94A3B8'),
        })
        rows.append(data)

    rows.sort(key=lambda x: (-x['score'], x['name']))
    return rows


# ── Momentum: recent discoveries ──────────────────────────────────────────────

def get_discovery_momentum(days: int = 7) -> list[dict]:
    """Per-user count of first-visit discoveries in the last `days` days."""
    conn = get_connection()
    users = pd.read_sql(
        "SELECT * FROM users WHERE picks_only = 0 OR picks_only IS NULL ORDER BY id",
        conn,
    )
    conn.close()

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    result = []
    for _, u in users.iterrows():
        uid = int(u['id'])
        conn2 = get_connection()
        df = pd.read_sql(
            "SELECT country_name FROM discoveries "
            "WHERE user_id=? AND first_visited_at >= ? ORDER BY first_visited_at DESC",
            conn2, params=(uid, cutoff),
        )
        conn2.close()
        result.append({
            'user_id':     uid,
            'name':        u['name'],
            'avatar':      u['avatar'],
            'theme_color': str(u.get('theme_color', '#94A3B8') or '#94A3B8'),
            'count':       len(df),
            'countries':   df['country_name'].tolist() if not df.empty else [],
        })

    result.sort(key=lambda x: -x['count'])
    return result


# ── Weekly explorer ───────────────────────────────────────────────────────────

def get_weekly_explorer() -> dict | None:
    """User with the most new discoveries in the last 7 days, or None if no activity."""
    momentum = get_discovery_momentum(days=7)
    return momentum[0] if momentum and momentum[0]['count'] > 0 else None


# ── Discovery streaks ─────────────────────────────────────────────────────────

def get_discovery_streak(user_id: int) -> int:
    """Consecutive calendar days (through today or yesterday) with at least one new discovery."""
    conn = get_connection()
    df = pd.read_sql(
        "SELECT first_visited_at FROM discoveries WHERE user_id=? ORDER BY first_visited_at",
        conn, params=(user_id,),
    )
    conn.close()

    if df.empty:
        return 0

    dates: set[date] = set()
    for ts in df['first_visited_at']:
        try:
            dates.add(datetime.fromisoformat(str(ts)).date())
        except Exception:
            pass

    today = date.today()
    # Count backward from today
    streak, check = 0, today
    while check in dates:
        streak += 1
        check -= timedelta(days=1)

    # If today had no discovery, count backward from yesterday
    if streak == 0:
        check = today - timedelta(days=1)
        while check in dates:
            streak += 1
            check -= timedelta(days=1)

    return streak


# ── Continent explorer ────────────────────────────────────────────────────────

def get_continent_progress_all_users() -> dict:
    """
    Return {continent: {user_id: {name, avatar, theme_color, discovered, total}}}
    for all passport users. Used for the family continent map.
    """
    conn = get_connection()
    users = pd.read_sql(
        "SELECT * FROM users WHERE picks_only = 0 OR picks_only IS NULL ORDER BY id",
        conn,
    )
    conn.close()

    ct = get_continent_teams()
    result: dict[str, dict] = {cont: {} for cont in ct}

    for _, u in users.iterrows():
        uid = int(u['id'])
        disc_df = get_discoveries(uid)
        disc_set = set(disc_df['country_name'].tolist()) if not disc_df.empty else set()
        for cont, teams in ct.items():
            result[cont][uid] = {
                'name':        u['name'],
                'avatar':      u['avatar'],
                'theme_color': str(u.get('theme_color', '#94A3B8') or '#94A3B8'),
                'discovered':  sum(1 for t in teams if t in disc_set),
                'total':       len(teams),
            }

    return result


# ── Collector milestones ──────────────────────────────────────────────────────

def get_collector_milestone(count: int) -> tuple[int, str] | None:
    """Return (milestone, label) for the most recently crossed milestone, or None."""
    for m in sorted(MILESTONES, reverse=True):
        if count >= m:
            return m, _MILESTONE_LABELS.get(m, f"{m} Countries")
    return None
