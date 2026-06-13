"""
Passport service: discovery tracking, favorites, continent progress, Country of the Day.
All continent/stamp/flag data sourced from data/country_metadata.csv.
"""
import os
import json as _json
import urllib.request as _urllib
import urllib.parse as _urlparse
import pandas as pd
from datetime import date, datetime, timedelta
from services.database import get_connection, DATA_DIR

_META_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'country_metadata.csv')
_meta_cache: pd.DataFrame | None = None

# ── Wikipedia image fetcher ───────────────────────────────────────────────────
# Maps team names to Wikipedia article titles where they differ
_WIKI_TITLES: dict[str, str] = {
    'USA': 'United_States',
    'South Korea': 'South_Korea',
    'Türkiye': 'Turkey',
    'DR Congo': 'Democratic_Republic_of_the_Congo',
    'Bosnia and Herzegovina': 'Bosnia_and_Herzegovina',
    'Ivory Coast': 'Ivory_Coast',
    'Cape Verde': 'Cape_Verde',
    'New Zealand': 'New_Zealand',
    'Saudi Arabia': 'Saudi_Arabia',
    'South Africa': 'South_Africa',
    'Czechia': 'Czechia',
    'Curaçao': 'Cura%C3%A7ao',
}
_image_cache: dict[str, str] = {}


def get_country_image_url(country: str) -> str:
    """Return Wikipedia's lead image URL for a country. Cached per process."""
    if country in _image_cache:
        return _image_cache[country]
    wiki = _WIKI_TITLES.get(country, country.replace(' ', '_'))
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{_urlparse.quote(wiki)}"
        req = _urllib.Request(url, headers={'User-Agent': 'WorldCupFamilyHQ/1.0'})
        with _urllib.urlopen(req, timeout=4) as resp:
            data = _json.loads(resp.read())
        src = (data.get('originalimage') or data.get('thumbnail') or {}).get('source', '')
        _image_cache[country] = src
        return src
    except Exception:
        _image_cache[country] = ''
        return ''


# ── Metadata ──────────────────────────────────────────────────────────────────

def get_country_metadata() -> pd.DataFrame:
    global _meta_cache
    if _meta_cache is None:
        _meta_cache = pd.read_csv(_META_PATH)
    return _meta_cache


def get_stamp(country: str) -> dict:
    meta = get_country_metadata()
    row = meta[meta['country'] == country]
    if row.empty:
        return {'country': country, 'continent': 'Unknown',
                'stamp_emoji': '🌍', 'stamp_label': country, 'flag_fact': ''}
    r = row.iloc[0]

    def _s(key):
        val = r.get(key, '')
        return '' if pd.isna(val) else str(val)

    return {
        'country':          _s('country'),
        'continent':        _s('continent'),
        'stamp_emoji':      _s('stamp_emoji'),
        'stamp_label':      _s('stamp_label'),
        'flag_fact':        _s('flag_fact'),
        'hero_emoji':       _s('hero_emoji') or _s('stamp_emoji'),
        'hero_image_path':  _s('hero_image_path'),
        'hero_image_url':   _s('hero_image_url'),
        'hero_image_alt':   _s('hero_image_alt'),
        'hero_image_credit': _s('hero_image_credit'),
    }


def get_continent_teams() -> dict[str, list[str]]:
    meta = get_country_metadata()
    result: dict[str, list[str]] = {}
    for _, row in meta.iterrows():
        result.setdefault(row['continent'], []).append(row['country'])
    return result


# ── Picks-only helper ─────────────────────────────────────────────────────────

def _user_picks_only(user_id: int) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT picks_only FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return bool(row[0]) if row and row[0] else False


def _passport_user_ids() -> list[int]:
    """IDs of users who participate in passport tracking (not picks-only)."""
    conn = get_connection()
    df = pd.read_sql(
        "SELECT id FROM users WHERE picks_only = 0 OR picks_only IS NULL ORDER BY id", conn
    )
    conn.close()
    return df['id'].tolist()


# ── Discovery tracking ────────────────────────────────────────────────────────

def log_discovery(user_id: int, country_name: str):
    """Log or update a profile visit. Fires activity log on first visit.
    Skipped silently for picks-only users."""
    if _user_picks_only(user_id):
        return

    from services.activity import log_discovery_activity

    now = datetime.now().isoformat()
    conn = get_connection()

    existing = conn.execute(
        "SELECT visit_count FROM discoveries WHERE user_id=? AND country_name=?",
        (user_id, country_name)
    ).fetchone()

    is_first = existing is None

    conn.execute("""
        INSERT INTO discoveries (user_id, country_name, first_visited_at, visit_count)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(user_id, country_name)
        DO UPDATE SET visit_count = visit_count + 1
    """, (user_id, country_name, now))
    conn.commit()
    conn.close()

    if is_first:
        log_discovery_activity(user_id, country_name)
        _check_continent_completion(user_id, country_name)


def _check_continent_completion(user_id: int, newly_discovered: str):
    """Log a continent_completed event if all countries in the continent are now discovered."""
    from services.activity import log_activity
    meta = get_country_metadata()
    row = meta[meta['country'] == newly_discovered]
    if row.empty:
        return
    continent = row.iloc[0]['continent']
    continent_countries = set(meta[meta['continent'] == continent]['country'].tolist())
    disc = get_discoveries(user_id)
    disc_countries = set(disc['country_name'].tolist()) if not disc.empty else set()
    if continent_countries.issubset(disc_countries):
        conn = get_connection()
        already = conn.execute(
            "SELECT id FROM activity_log WHERE user_id=? AND event_type='continent_completed' AND country_name=?",
            (user_id, continent)
        ).fetchone()
        conn.close()
        if not already:
            log_activity(user_id, 'continent_completed',
                        country_name=continent,
                        message=f"explored all of {continent}!")


def get_discoveries(user_id: int) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM discoveries WHERE user_id=? ORDER BY first_visited_at",
        conn, params=(user_id,)
    )
    conn.close()
    return df


# ── Picks-derived stats ───────────────────────────────────────────────────────

def _picks_with_results(user_id: int) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql("""
        SELECT p.picked_team, m.home_team, m.away_team,
               m.home_score, m.away_score, m.status
        FROM picks p
        JOIN matches m ON p.match_id = m.id
        WHERE p.user_id = ?
    """, conn, params=(user_id,))
    conn.close()

    def _r(row):
        if row['status'] != 'completed' or pd.isna(row['home_score']):
            return None
        hs, as_ = int(row['home_score']), int(row['away_score'])
        if hs == as_:
            return 0.5
        return 1.0 if row['picked_team'] == (row['home_team'] if hs > as_ else row['away_team']) else 0.0

    df['result'] = df.apply(_r, axis=1)
    return df


def get_cheered_for(user_id: int) -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT picked_team FROM picks WHERE user_id=?", (user_id,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_won_with(user_id: int) -> list[str]:
    df = _picks_with_results(user_id)
    won = df[df['result'].notna() & (df['result'] > 0)]
    return list(won['picked_team'].unique())


def get_points_per_country(user_id: int) -> dict[str, float]:
    df = _picks_with_results(user_id)
    c = df[df['result'].notna()]
    return c.groupby('picked_team')['result'].sum().to_dict() if not c.empty else {}


def get_picks_per_country(user_id: int) -> dict[str, int]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT picked_team, COUNT(*) FROM picks WHERE user_id=?
        GROUP BY picked_team
    """, (user_id,)).fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


# ── Favorites ─────────────────────────────────────────────────────────────────

def _fav_score(country, disc_df, picks_per, points_per) -> float:
    visits = 0
    if not disc_df.empty and country in disc_df['country_name'].values:
        visits = int(disc_df[disc_df['country_name'] == country]['visit_count'].iloc[0])
    return visits * 1.0 + picks_per.get(country, 0) * 2.0 + points_per.get(country, 0.0) * 3.0


def get_top_favorites(user_id: int, n: int = 3) -> list[str]:
    meta = get_country_metadata()
    disc = get_discoveries(user_id)
    picks_per = get_picks_per_country(user_id)
    points_per = get_points_per_country(user_id)
    scored = [(c, _fav_score(c, disc, picks_per, points_per)) for c in meta['country']]
    scored = [(c, s) for c, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored[:n]]


# ── Continent progress ────────────────────────────────────────────────────────

def get_continent_progress(user_id: int) -> dict:
    ct = get_continent_teams()
    disc = set(get_discoveries(user_id)['country_name'].tolist()
               if not get_discoveries(user_id).empty else [])
    cheered = set(get_cheered_for(user_id))
    won = set(get_won_with(user_id))
    return {
        continent: {
            'total': len(teams), 'teams': teams,
            'discovered': sum(1 for t in teams if t in disc),
            'cheered': sum(1 for t in teams if t in cheered),
            'won': sum(1 for t in teams if t in won),
        }
        for continent, teams in ct.items()
    }


# ── Family passport ───────────────────────────────────────────────────────────

def get_all_users_summary() -> pd.DataFrame:
    conn = get_connection()
    users = pd.read_sql(
        "SELECT * FROM users WHERE picks_only = 0 OR picks_only IS NULL ORDER BY id", conn
    )
    conn.close()
    rows = []
    for _, user in users.iterrows():
        uid = int(user['id'])
        disc = get_discoveries(uid)
        cheered = get_cheered_for(uid)
        won = get_won_with(uid)
        favs = get_top_favorites(uid, 3)
        rows.append({
            'id': uid, 'name': user['name'],
            'avatar': user['avatar'], 'theme_color': user['theme_color'],
            'discovered_count': len(disc),
            'cheered_count': len(cheered),
            'won_count': len(won),
            'fav1': favs[0] if len(favs) > 0 else None,
            'fav2': favs[1] if len(favs) > 1 else None,
            'fav3': favs[2] if len(favs) > 2 else None,
        })
    return pd.DataFrame(rows)


def get_family_stamp_statuses() -> dict[str, dict]:
    conn = get_connection()
    users = pd.read_sql(
        "SELECT * FROM users WHERE picks_only = 0 OR picks_only IS NULL ORDER BY id", conn
    )
    conn.close()
    meta = get_country_metadata()
    statuses: dict[str, dict] = {
        c: {'discovered': False, 'cheered': False, 'won': False,
            'discoverers': [], 'cheerleaders': [], 'winners': []}
        for c in meta['country'].tolist()
    }
    for _, user in users.iterrows():
        uid = int(user['id'])
        label = f"{user['avatar']} {user['name']}"
        disc_countries = set(get_discoveries(uid)['country_name'].tolist()
                             if not get_discoveries(uid).empty else [])
        cheered = set(get_cheered_for(uid))
        won = set(get_won_with(uid))
        for c in statuses:
            if c in disc_countries:
                statuses[c]['discovered'] = True
                statuses[c]['discoverers'].append(label)
            if c in cheered:
                statuses[c]['cheered'] = True
                statuses[c]['cheerleaders'].append(label)
            if c in won:
                statuses[c]['won'] = True
                statuses[c]['winners'].append(label)
    return statuses


def get_family_country_card(country: str) -> dict:
    conn = get_connection()
    users = pd.read_sql(
        "SELECT * FROM users WHERE picks_only = 0 OR picks_only IS NULL ORDER BY id", conn
    )
    conn.close()
    discoverers, cheerleaders, winners = [], [], []
    for _, user in users.iterrows():
        uid = int(user['id'])
        label = f"{user['avatar']} {user['name']}"
        disc = get_discoveries(uid)
        if not disc.empty and country in disc['country_name'].values:
            discoverers.append(label)
        if country in get_cheered_for(uid):
            cheerleaders.append(label)
        if country in get_won_with(uid):
            winners.append(label)
    return {'country': country, 'stamp': get_stamp(country),
            'discoverers': discoverers, 'cheerleaders': cheerleaders, 'winners': winners}


def get_family_continent_progress() -> dict:
    conn = get_connection()
    users = pd.read_sql(
        "SELECT id FROM users WHERE picks_only = 0 OR picks_only IS NULL", conn
    )
    conn.close()
    ct = get_continent_teams()
    fam_disc, fam_cheered, fam_won = set(), set(), set()
    for uid in users['id'].tolist():
        disc = get_discoveries(int(uid))
        if not disc.empty:
            fam_disc.update(disc['country_name'].tolist())
        fam_cheered.update(get_cheered_for(int(uid)))
        fam_won.update(get_won_with(int(uid)))
    return {
        continent: {
            'total': len(teams), 'teams': teams,
            'discovered': sum(1 for t in teams if t in fam_disc),
            'cheered': sum(1 for t in teams if t in fam_cheered),
            'won': sum(1 for t in teams if t in fam_won),
        }
        for continent, teams in ct.items()
    }


def get_family_top_favorites(n: int = 5) -> list[str]:
    conn = get_connection()
    users = pd.read_sql(
        "SELECT id FROM users WHERE picks_only = 0 OR picks_only IS NULL", conn
    )
    conn.close()
    meta = get_country_metadata()
    totals: dict[str, float] = {}
    for uid in users['id'].tolist():
        disc = get_discoveries(int(uid))
        picks_per = get_picks_per_country(int(uid))
        points_per = get_points_per_country(int(uid))
        for c in meta['country']:
            totals[c] = totals.get(c, 0.0) + _fav_score(c, disc, picks_per, points_per)
    scored = [(c, s) for c, s in totals.items() if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored[:n]]


# ── Country of the Day ────────────────────────────────────────────────────────

def get_country_of_the_day() -> dict:
    """
    Returns a deterministic daily country (doesn't change on page refresh).
    Logic: if matches today → pick a playing country; else → lesser-discovered.
    """
    from services.teams import get_team_by_name
    from services.teams import get_flag

    today = (datetime.utcnow() - timedelta(hours=7)).date()  # PDT = UTC-7
    seed = today.toordinal()

    # Check for matches today
    conn = get_connection()
    today_str = today.isoformat()
    matches = pd.read_sql(
        "SELECT * FROM matches WHERE match_date=? ORDER BY kickoff_time_et",
        conn, params=(today_str,)
    )
    conn.close()

    reason = "Featured country"
    if not matches.empty:
        candidates = list(set(matches['home_team'].tolist() + matches['away_team'].tolist()))
        candidates.sort()
        country = candidates[seed % len(candidates)]
        reason = "Playing today ⚽"
    else:
        # Pick lesser-discovered country
        statuses = get_family_stamp_statuses()
        undiscovered = sorted([c for c, s in statuses.items() if not s['discovered']])
        if undiscovered:
            country = undiscovered[seed % len(undiscovered)]
            reason = "Less discovered country 🌍"
        else:
            meta = get_country_metadata()
            all_c = sorted(meta['country'].tolist())
            country = all_c[seed % len(all_c)]
            reason = "Featured country 🌟"

    stamp = get_stamp(country)
    team = get_team_by_name(country)
    flag = get_flag(country)

    def _safe_str(val):
        return '' if val is None or (isinstance(val, float) and __import__('math').isnan(val)) else str(val)

    fun_fact = _safe_str(team.get('fun_fact', '') if team is not None else '')
    cheer_raw = _safe_str(team.get('cheer_reasons', '') if team is not None else '')
    cheer_reasons = [s.strip() for s in cheer_raw.split('|') if s.strip()][:4]

    # today's opponent context for "playing today" reason
    opp_label = ""
    if "Playing today" in reason and not matches.empty:
        opponents = [m['away_team'] if m['home_team'] == country else m['home_team']
                     for _, m in matches.iterrows()
                     if m['home_team'] == country or m['away_team'] == country]
        if opponents:
            opp_label = f" vs {opponents[0]}"

    # Wikipedia image = tertiary fallback only
    hero_image_wiki = get_country_image_url(country)

    return {
        'country':           country,
        'flag':              flag,
        'stamp_emoji':       stamp['stamp_emoji'],
        'stamp_label':       stamp['stamp_label'],
        'hero_emoji':        stamp.get('hero_emoji', stamp['stamp_emoji']),
        # Curated image fields (from country_metadata.csv — preferred)
        'hero_image_path':   stamp.get('hero_image_path', ''),
        'hero_image_url':    stamp.get('hero_image_url', ''),
        'hero_image_alt':    stamp.get('hero_image_alt', ''),
        'hero_image_credit': stamp.get('hero_image_credit', ''),
        # Wikipedia image (tertiary fallback)
        'hero_image_wiki':   hero_image_wiki,
        'flag_fact':         stamp.get('flag_fact', ''),
        'fun_fact':          fun_fact,
        'cheer_reasons':     cheer_reasons,
        'reason':            reason,
        'reason_detail':     opp_label,
        'continent':         stamp['continent'],
    }
