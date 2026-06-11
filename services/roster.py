"""
Roster service. All access to world_cup_rosters.csv / world_cup_players_slugged.csv
/ world_cup_team_summary.csv goes through here.

Do not import these CSVs directly from pages.
"""
import os
import re
import pandas as pd
from datetime import date

_DIR = os.path.dirname(__file__)
_DATA = os.path.join(_DIR, '..', 'data')

# ── Team name mapping: app names → roster CSV names ───────────────────────────
_APP_TO_ROSTER: dict[str, str] = {
    'Bosnia and Herzegovina': 'Bosnia And Herzegovina',
    'Cape Verde':             'Cabo Verde',
    'DR Congo':               'Congo DR',
    'Ivory Coast':            "Côte D'Ivoire",
    'Iran':                   'IR Iran',
    'South Korea':            'Korea Republic',
}

# ── Module-level caches ───────────────────────────────────────────────────────
_rosters:  pd.DataFrame | None = None
_summary:  pd.DataFrame | None = None
_slugged:  pd.DataFrame | None = None


def _today() -> date:
    return date.today()


def _compute_age(birthdate_str) -> int:
    try:
        bd = pd.to_datetime(birthdate_str).date()
        today = _today()
        return (today - bd).days // 365
    except Exception:
        return 0


def _load_rosters() -> pd.DataFrame:
    global _rosters
    if _rosters is None:
        df = pd.read_csv(os.path.join(_DATA, 'world_cup_rosters.csv'))
        df['age'] = df['birthdate'].apply(_compute_age)
        df['club_short'] = df['club'].apply(_club_short)
        _rosters = df
    return _rosters


def _load_summary() -> pd.DataFrame:
    global _summary
    if _summary is None:
        _summary = pd.read_csv(os.path.join(_DATA, 'world_cup_team_summary.csv'))
    return _summary


def _load_slugged() -> pd.DataFrame:
    global _slugged
    if _slugged is None:
        df = pd.read_csv(os.path.join(_DATA, 'world_cup_players_slugged.csv'))
        df['age'] = df['birthdate'].apply(_compute_age)
        df['club_short'] = df['club'].apply(_club_short)
        _slugged = df
    return _slugged


def _roster_name(app_name: str) -> str:
    return _APP_TO_ROSTER.get(app_name, app_name)


def _club_short(club: str) -> str:
    """'Real Madrid (ESP)' → 'Real Madrid'"""
    if pd.isna(club):
        return ''
    m = re.match(r'^(.+?)\s*\([A-Z]{2,3}\)$', str(club))
    return m.group(1).strip() if m else str(club).strip()


def _club_country_code(club: str) -> str:
    """'Real Madrid (ESP)' → 'ESP'"""
    if pd.isna(club):
        return ''
    m = re.search(r'\(([A-Z]{2,3})\)$', str(club))
    return m.group(1) if m else ''


# ── Public API ────────────────────────────────────────────────────────────────

def get_team_roster(team: str) -> pd.DataFrame:
    """All 26 players for a team, sorted by shirt number."""
    df = _load_rosters()
    rname = _roster_name(team)
    result = df[df['team'] == rname].copy()
    return result.sort_values('shirt_number').reset_index(drop=True)


def get_team_summary(team: str) -> dict:
    """Squad summary stats (player count, position counts, avg age)."""
    df = _load_summary()
    rname = _roster_name(team)
    row = df[df['team'] == rname]
    if row.empty:
        return {}
    return row.iloc[0].to_dict()


def get_mls_players(team: str) -> pd.DataFrame:
    """Players at USA-based clubs (MLS and US lower divisions)."""
    roster = get_team_roster(team)
    if roster.empty:
        return roster
    mask = roster['club'].str.contains(r'\(USA\)', na=False)
    return roster[mask].copy().reset_index(drop=True)


def get_featured_players(team: str, captain_name: str = '') -> list[dict]:
    """
    Returns up to 5 featured player dicts for card display.
    Includes: captain, youngest, oldest, MLS players, top-shirt starters.
    """
    roster = get_team_roster(team)
    if roster.empty:
        return []

    featured: list[dict] = []
    seen: set[int] = set()

    def _add(row, role: str):
        num = int(row['shirt_number'])
        if num in seen:
            return
        seen.add(num)
        featured.append({
            'name': row['player_name'],
            'shirt_number': num,
            'position': row['position'],
            'club': row['club'],
            'club_short': row['club_short'],
            'age': int(row['age']),
            'role': role,
        })

    # Captain (fuzzy last-name match)
    if captain_name:
        last = captain_name.split()[-1].lower()
        caps = roster[roster['player_name'].str.lower().str.contains(last, na=False, regex=False)]
        if not caps.empty:
            _add(caps.iloc[0], '🎖️ Captain')

    # Youngest
    youngest_row = roster.loc[roster['age'].idxmin()]
    _add(youngest_row, '🌱 Youngest')

    # Oldest
    oldest_row = roster.loc[roster['age'].idxmax()]
    _add(oldest_row, '📅 Oldest')

    # MLS players (up to 2)
    mls = get_mls_players(team)
    for _, r in mls.head(2).iterrows():
        _add(r, '🏟️ MLS')

    # Fill from shirt 1–11 (traditional starters)
    for _, r in roster[roster['shirt_number'] <= 11].iterrows():
        if len(featured) >= 5:
            break
        _add(r, '⚽ Squad')

    return featured[:5]


def get_player(player_slug: str) -> dict | None:
    """
    Look up a player by slug. Used for future player profile pages.
    Returns None if not found.
    """
    df = _load_slugged()
    row = df[df['player_slug'] == player_slug]
    if row.empty:
        return None
    r = row.iloc[0]
    return {
        'name': r['player_name'],
        'shirt_number': int(r['shirt_number']),
        'position': r['position'],
        'club': r['club'],
        'club_short': r['club_short'],
        'age': int(r['age']),
        'birthdate': str(r['birthdate']),
        'team': r['team'],
        'player_slug': r['player_slug'],
        'team_slug': r['team_slug'],
    }


def get_all_roster_team_names() -> list[str]:
    """All team names as they appear in the roster CSV."""
    return sorted(_load_rosters()['team'].unique().tolist())


# ── Position helpers ──────────────────────────────────────────────────────────

_POS_ICON = {
    'Goalkeeper': '🧤',
    'Defender':   '🛡️',
    'Midfielder': '⚙️',
    'Forward':    '⚽',
}

_POS_ORDER = ['Goalkeeper', 'Defender', 'Midfielder', 'Forward']


def get_roster_by_position(team: str) -> dict[str, pd.DataFrame]:
    """Returns {position: DataFrame} for tab display."""
    roster = get_team_roster(team)
    return {
        pos: roster[roster['position'] == pos].reset_index(drop=True)
        for pos in _POS_ORDER
    }


def pos_icon(position: str) -> str:
    return _POS_ICON.get(position, '⚽')
