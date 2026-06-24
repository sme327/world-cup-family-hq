"""
Achievement system. Checks rules and awards individual/family achievements.
"""
import os
import pandas as pd
from datetime import datetime
from services.database import get_connection, DATA_DIR


def get_all_achievements() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, 'achievements.csv')
    return pd.read_csv(path)


def get_recent_achievement_unlocks(limit: int = 5) -> pd.DataFrame:
    """Recent unlocks across all family members, joined with achievement metadata."""
    all_ach = get_all_achievements()
    ach_dict = {str(r['achievement_id']): r for _, r in all_ach.iterrows()}

    conn = get_connection()
    df = pd.read_sql("""
        SELECT ua.achievement_id, ua.unlocked_at, u.name, u.avatar, u.theme_color
        FROM user_achievements ua
        JOIN users u ON ua.user_id = u.id
        ORDER BY ua.unlocked_at DESC
        LIMIT ?
    """, conn, params=(limit,))
    conn.close()

    if df.empty:
        return df

    df['ach_name'] = df['achievement_id'].apply(
        lambda x: str(ach_dict.get(str(x), {}).get('name', ''))
    )
    df['ach_emoji'] = df['achievement_id'].apply(
        lambda x: str(ach_dict.get(str(x), {}).get('emoji', '🏅'))
    )
    return df


def get_user_achievements(user_id: int) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM user_achievements WHERE user_id = ? ORDER BY unlocked_at DESC",
        conn, params=(user_id,)
    )
    conn.close()
    return df


def get_family_achievements() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM family_achievements ORDER BY unlocked_at DESC", conn)
    conn.close()
    return df


def _award_individual(user_id: int, achievement_id: str) -> bool:
    """Awards achievement if not already earned. Returns True if newly awarded."""
    now = datetime.now().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO user_achievements (user_id, achievement_id, unlocked_at)
        VALUES (?, ?, ?)
    """, (user_id, achievement_id, now))
    newly = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return newly


def _award_family(achievement_id: str) -> bool:
    now = datetime.now().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO family_achievements (achievement_id, unlocked_at)
        VALUES (?, ?)
    """, (achievement_id, now))
    newly = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return newly


def _get_user_stats(user_id: int) -> dict:
    from services.passport import (
        get_discoveries, get_cheered_for, get_won_with,
        get_continent_progress, get_country_metadata,
    )
    from services.scoring import get_leaderboard

    disc = get_discoveries(user_id)
    disc_count = len(disc)
    disc_countries = set(disc['country_name'].tolist()) if not disc.empty else set()

    cheered = get_cheered_for(user_id)
    won = get_won_with(user_id)

    conn = get_connection()
    picks_count = conn.execute(
        "SELECT COUNT(*) FROM picks WHERE user_id=?", (user_id,)
    ).fetchone()[0]
    conn.close()

    board = get_leaderboard()
    user_row = board[board['id'] == user_id]
    total_points = float(user_row['total_points'].iloc[0]) if not user_row.empty else 0.0

    continent_prog = get_continent_progress(user_id)

    meta = get_country_metadata()
    na_countries = set(meta[meta['continent'] == 'North America']['country'].tolist())
    sa_countries = set(meta[meta['continent'] == 'South America']['country'].tolist())
    pacific_rim = {'Japan', 'South Korea', 'Australia', 'New Zealand'}
    host_countries = {'USA', 'Canada', 'Mexico'}

    from services.player_cards import (
        get_player_discoveries_count, get_player_captain_discovered,
        get_mls_discoveries_count, get_player_team_count,
    )
    players_discovered = get_player_discoveries_count(user_id)

    return {
        'disc_count': disc_count,
        'disc_countries': disc_countries,
        'cheered_count': len(cheered),
        'won_count': len(won),
        'picks_count': picks_count,
        'total_points': total_points,
        'continent_prog': continent_prog,
        'pacific_rim_done': pacific_rim.issubset(disc_countries),
        'all_americas_done': (na_countries | sa_countries).issubset(disc_countries),
        'host_countries_done': host_countries.issubset(disc_countries),
        'players_discovered': players_discovered,
        'captain_discovered': get_player_captain_discovered(user_id) if players_discovered > 0 else False,
        'mls_players_discovered': get_mls_discoveries_count(user_id) if players_discovered > 0 else 0,
        'player_team_count': get_player_team_count(user_id) if players_discovered > 0 else 0,
    }


def _check_rule(rule: str, threshold, stats: dict, user_id: int) -> bool:
    t = str(threshold).strip() if pd.notna(threshold) else ''
    cp = stats['continent_prog']

    if rule == 'countries_discovered':
        return stats['disc_count'] >= int(t)
    if rule == 'countries_cheered':
        return stats['cheered_count'] >= int(t)
    if rule == 'countries_won':
        return stats['won_count'] >= int(t)
    if rule == 'picks_made':
        return stats['picks_count'] >= int(t)
    if rule == 'first_pick':
        return stats['picks_count'] >= 1
    if rule == 'first_point':
        return stats['total_points'] > 0
    if rule == 'points_earned':
        return stats['total_points'] >= float(t)
    if rule == 'continent_all_discovered':
        prog = cp.get(t, {})
        return prog.get('total', 0) > 0 and prog.get('discovered', 0) == prog.get('total', 0)
    if rule == 'any_continent_all_discovered':
        return any(
            p.get('total', 0) > 0 and p.get('discovered', 0) == p.get('total', 0)
            for p in cp.values()
        )
    if rule == 'pacific_rim_discovered':
        return stats['pacific_rim_done']
    if rule == 'all_americas_discovered':
        return stats['all_americas_done']
    if rule == 'host_countries_discovered':
        return stats['host_countries_done']
    if rule == 'loyal_3_matches':
        return _check_loyal_fan(user_id)
    if rule == 'players_discovered':
        return stats.get('players_discovered', 0) >= int(t)
    if rule == 'captain_discovered':
        return stats.get('captain_discovered', False)
    if rule == 'mls_players_discovered':
        return stats.get('mls_players_discovered', 0) >= int(t)
    if rule == 'player_countries':
        return stats.get('player_team_count', 0) >= int(t)
    return False


def _check_loyal_fan(user_id: int) -> bool:
    """User picked same country in all 3 of that country's group matches."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.picked_team, COUNT(*) as cnt
        FROM picks p
        JOIN matches m ON p.match_id = m.id
        WHERE p.user_id = ?
        GROUP BY p.picked_team
        HAVING cnt >= 3
    """, (user_id,)).fetchall()
    conn.close()
    return len(rows) > 0


def check_individual_achievements(user_id: int) -> list[str]:
    """Check and award individual achievements. Returns list of newly unlocked IDs."""
    from services.activity import log_achievement_activity

    all_ach = get_all_achievements()
    individual = all_ach[all_ach['scope'] == 'individual']
    already = set(get_user_achievements(user_id)['achievement_id'].tolist()
                  if not get_user_achievements(user_id).empty else [])

    stats = _get_user_stats(user_id)
    newly_unlocked = []

    for _, ach in individual.iterrows():
        aid = str(ach['achievement_id'])
        if aid in already:
            continue
        if _check_rule(str(ach['rule_type']), ach.get('threshold'), stats, user_id):
            if _award_individual(user_id, aid):
                newly_unlocked.append(aid)
                log_achievement_activity(user_id, aid, str(ach['name']))

    return newly_unlocked


def check_family_achievements() -> list[str]:
    """Check family-scope achievements. Returns newly unlocked IDs."""
    from services.passport import get_family_stamp_statuses, get_country_metadata
    from services.picks import get_all_users
    from services.activity import log_activity

    all_ach = get_all_achievements()
    family_ach = all_ach[all_ach['scope'] == 'family']
    already = set(get_family_achievements()['achievement_id'].tolist()
                  if not get_family_achievements().empty else [])

    statuses = get_family_stamp_statuses()
    meta = get_country_metadata()
    total = len(meta)

    family_disc = sum(1 for s in statuses.values() if s['discovered'])
    family_cheered = sum(1 for s in statuses.values() if s['cheered'])

    users = get_all_users()
    newly_unlocked = []

    for _, ach in family_ach.iterrows():
        aid = str(ach['achievement_id'])
        if aid in already:
            continue

        rule = str(ach['rule_type'])
        t = str(ach.get('threshold', '')).strip()

        earned = False
        if rule == 'family_discovered' and t.isdigit():
            earned = family_disc >= int(t)
        elif rule == 'family_all_started':
            from services.passport import get_discoveries
            earned = all(
                not get_discoveries(int(u['id'])).empty
                for _, u in users.iterrows()
            )
        elif rule == 'family_same_pick':
            earned = _check_family_same_pick(users)

        if earned and _award_family(aid):
            newly_unlocked.append(aid)

    return newly_unlocked


def _check_family_same_pick(users) -> bool:
    """All family members have picked the same country at least once."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT picked_team FROM picks WHERE user_id=?",
        (int(users.iloc[0]['id']),)
    ).fetchall()
    conn.close()
    if not rows:
        return False
    user_pick_sets = []
    for _, u in users.iterrows():
        conn = get_connection()
        picks = set(r[0] for r in conn.execute(
            "SELECT DISTINCT picked_team FROM picks WHERE user_id=?", (int(u['id']),)
        ).fetchall())
        conn.close()
        user_pick_sets.append(picks)
    common = user_pick_sets[0]
    for s in user_pick_sets[1:]:
        common &= s
    return len(common) > 0
