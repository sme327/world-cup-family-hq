"""
Activity log service. Only meaningful family events reach the feed.
"""
import pandas as pd
from datetime import datetime
from services.database import get_connection

# Event types that are meaningful enough to surface in the feed
_MEANINGFUL = (
    'country_discovered',
    'achievement_unlocked',
    'continent_completed',
    'first_pick',
    'points_earned',
)


def log_activity(user_id: int, event_type: str, *,
                 country_name: str = None, match_id: int = None,
                 achievement_id: str = None, message: str = None):
    now = datetime.now().isoformat()
    conn = get_connection()
    conn.execute("""
        INSERT INTO activity_log
            (timestamp, user_id, event_type, country_name, match_id, achievement_id, message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (now, user_id, event_type, country_name, match_id, achievement_id, message))
    conn.commit()
    conn.close()


def log_discovery_activity(user_id: int, country_name: str):
    """Log first-visit discovery only (idempotent)."""
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM activity_log WHERE user_id=? AND event_type='country_discovered' AND country_name=?",
        (user_id, country_name)
    ).fetchone()
    conn.close()
    if not existing:
        log_activity(user_id, 'country_discovered',
                     country_name=country_name,
                     message=f"discovered {country_name}")


def log_achievement_activity(user_id: int, achievement_id: str, achievement_name: str):
    log_activity(user_id, 'achievement_unlocked',
                 achievement_id=achievement_id,
                 message=achievement_name)


def get_meaningful_activity(limit: int = 15) -> pd.DataFrame:
    """Returns only interesting, story-worthy events (not every pick)."""
    placeholders = ','.join('?' * len(_MEANINGFUL))
    conn = get_connection()
    df = pd.read_sql(f"""
        SELECT a.*, u.name AS user_name, u.avatar, u.theme_color
        FROM activity_log a
        JOIN users u ON a.user_id = u.id
        WHERE a.event_type IN ({placeholders})
        ORDER BY a.timestamp DESC
        LIMIT ?
    """, conn, params=(*_MEANINGFUL, limit))
    conn.close()
    return df


_PRIORITY_ORDER = {
    'achievement_unlocked': 0,
    'points_earned': 1,
    'continent_completed': 2,
    'first_pick': 3,
    'country_discovered': 4,
}

# Tier 1 = major milestones, Tier 2 = exploration, Tier 3 = routine
STORY_TIERS: dict[str, int] = {
    'achievement_unlocked': 1,
    'continent_completed':  1,
    'first_pick':           1,
    'country_discovered':   2,
    'points_earned':        3,
}


def get_best_activity_per_user(user_ids_ordered: list[int]) -> dict:
    """
    Returns {user_id: row_dict | None} with the single best activity per user.
    Priority: achievement > points > continent > first_pick > discovered.
    Users with no activity get None.
    """
    placeholders = ','.join('?' * len(_MEANINGFUL))
    conn = get_connection()
    df = pd.read_sql(f"""
        SELECT a.*, u.name AS user_name, u.avatar, u.theme_color
        FROM activity_log a
        JOIN users u ON a.user_id = u.id
        WHERE a.event_type IN ({placeholders})
        ORDER BY a.timestamp DESC
    """, conn, params=(*_MEANINGFUL,))
    conn.close()

    result: dict = {}
    for uid in user_ids_ordered:
        user_df = df[df['user_id'] == uid]
        if user_df.empty:
            result[uid] = None
            continue
        u2 = user_df.copy()
        u2['_prio'] = u2['event_type'].map(_PRIORITY_ORDER).fillna(99)
        best = u2.sort_values(['_prio', 'timestamp'], ascending=[True, False]).iloc[0]
        result[uid] = best.to_dict()
    return result


def get_tiered_family_activity(limit: int = 8) -> pd.DataFrame:
    """
    Recent family activity sorted by story tier (major milestones first),
    then by recency within each tier.
    """
    event_types = list(STORY_TIERS.keys())
    placeholders = ','.join('?' * len(event_types))
    conn = get_connection()
    # Fetch a generous pool so tier-based reordering surfaces the best events
    df = pd.read_sql(f"""
        SELECT a.*, u.name AS user_name, u.avatar, u.theme_color
        FROM activity_log a
        JOIN users u ON a.user_id = u.id
        WHERE a.event_type IN ({placeholders})
        ORDER BY a.timestamp DESC
        LIMIT ?
    """, conn, params=(*event_types, limit * 4))
    conn.close()
    if df.empty:
        return df
    df['_tier'] = df['event_type'].map(STORY_TIERS).fillna(3).astype(int)
    return (
        df.sort_values(['_tier', 'timestamp'], ascending=[True, False])
        .head(limit)
        .reset_index(drop=True)
    )


def get_recent_family_discoveries(limit: int = 4) -> pd.DataFrame:
    """Most recently discovered countries across all family members."""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT a.country_name, a.timestamp, u.name AS user_name, u.avatar
        FROM activity_log a
        JOIN users u ON a.user_id = u.id
        WHERE a.event_type = 'country_discovered'
        ORDER BY a.timestamp DESC
        LIMIT ?
    """, conn, params=(limit,))
    conn.close()
    return df


def get_recent_activity(limit: int = 20) -> pd.DataFrame:
    """All events (kept for admin/debug use)."""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT a.*, u.name AS user_name, u.avatar, u.theme_color
        FROM activity_log a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.timestamp DESC
        LIMIT ?
    """, conn, params=(limit,))
    conn.close()
    return df


# ── Story-like message formatters ─────────────────────────────────────────────

_EVENT_ICONS = {
    'country_discovered': '🌍',
    'achievement_unlocked': '🎖',
    'continent_completed': '🗺️',
    'first_pick': '⚽',
    'points_earned': '🏆',
}


def format_activity_message(row) -> tuple[str, str]:
    """Returns (icon, narrative_string) for display."""
    et = str(row.get('event_type', ''))
    country = str(row.get('country_name', ''))
    msg = str(row.get('message', ''))
    icon = _EVENT_ICONS.get(et, '📌')

    narratives = {
        'country_discovered': f"discovered **{country}**",
        'achievement_unlocked': f"unlocked **{msg}**" if msg else "unlocked an achievement!",
        'continent_completed': f"explored all of **{country}**! 🎉",
        'first_pick': f"picked **{country}**",
        'points_earned': f"earned points with **{country}**",
    }
    return icon, narratives.get(et, msg or et)
