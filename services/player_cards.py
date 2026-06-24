"""
Player card service: card data, discovery logging, featured-player-of-day, modal rendering.

All player card UI in the app renders through render_player_modal_content().
Each page defines its own @st.dialog wrapper that calls that function.
"""
from __future__ import annotations
import os
import pandas as pd
from datetime import date, datetime
from services.database import get_connection
from services.roster import get_player, _load_slugged, _roster_name, _compute_age, pos_icon

# ── Hardcoded "One Thing To Remember" for prominent players ──────────────────
# Keyed by player_slug from world_cup_players_slugged.csv (verified against the actual 2026 WC roster).
_ONE_THING: dict[str, str] = {
    # USA
    "christian-mate-pulisic":          "Captain and best player of the US national team — plays for AC Milan in Italy.",
    "giovanni-alejandro-reyna":        "His father Claudio Reyna captained the US national team — soccer runs in the family.",
    "tyler-shaan-adams":               "A former US captain known for his boundless energy in midfield.",
    "timothy-tarpeh-weah":            "Son of former world player of the year George Weah — plays in Serie A.",
    # Brazil
    "vinicius-jose-paixao-de-oliveira-junior": "One of the fastest and most exciting players in the world — won the Champions League with Real Madrid.",
    "endrick-felipe-moreira-de-sousa-pessoa":  "Signed for Real Madrid at age 17 — the next big Brazilian superstar.",
    # Argentina
    "lionel-andres-messi":             "Led Argentina to the 2022 World Cup title — considered by many as the greatest player in history.",
    "rodrigo-javier-de-paul":          "The engine of Argentina's midfield — known for his non-stop energy all 90 minutes.",
    # France
    "kylian-mbappe-lottin":            "One of the fastest players in the world — won the World Cup in 2018 aged just 19.",
    "masour-ousmane-dembele":          "Known for incredible dribbling speed — plays for Paris Saint-Germain in France.",
    # England
    "jude-victor-william-bellingham":  "Became Real Madrid's most important player at just 20 years old.",
    "harry-edward-kane":               "England's all-time top goal scorer — plays for Bayern Munich in Germany.",
    "bukayo-ayoyinka-saka":            "Arsenal's star winger and one of the most exciting young players in the world.",
    # Germany
    "florian-richard-wirtz":           "Considered Germany's best young player — a creative midfielder for Bayer Leverkusen.",
    "jamal-musiala":                   "Born in Germany, grew up in England — plays for Bayern Munich and can do things others can't.",
    # Spain
    "lamine-yamal-nasraoui-ebana":     "The youngest player ever at a European Championship — scored in the 2024 Euro final aged just 16.",
    # Portugal
    "cristiano-ronaldo-dos-santos-aveiro": "Has scored over 900 professional career goals — one of the most famous athletes in the world.",
    "bernardo-mota-veiga-de-carvalho-e-silva": "Plays for Manchester City and is known for his creativity and footwork.",
    # Netherlands
    "virgil-van-dijk":                 "Considered the best defender in the world — led Liverpool to the Champions League in 2019.",
    # Japan
    "takefusa-kubo":                   "Trained at Real Madrid's academy as a teenager — now a star in Spain for Real Sociedad.",
    # Morocco
    "achraf-hakimi":                   "Moroccan right back who plays for PSG — one of the best defenders in the world.",
}

# ── Club country code → readable league name ──────────────────────────────────
_LEAGUE_NAMES: dict[str, str] = {
    "ENG": "England (Premier League)",
    "ESP": "Spain (La Liga)",
    "GER": "Germany (Bundesliga)",
    "ITA": "Italy (Serie A)",
    "FRA": "France (Ligue 1)",
    "NED": "Netherlands (Eredivisie)",
    "POR": "Portugal (Primeira Liga)",
    "USA": "USA (MLS)",
    "SAU": "Saudi Arabia (Pro League)",
    "TUR": "Turkey (Süper Lig)",
    "MXN": "Mexico (Liga MX)",
    "BEL": "Belgium (Pro League)",
    "SCO": "Scotland (Premiership)",
    "GRE": "Greece",
    "AUT": "Austria",
    "UKR": "Ukraine",
    "RUS": "Russia",
    "CHN": "China",
    "JPN": "Japan (J1 League)",
    "KOR": "South Korea (K League)",
}


def _club_country_code(club: str) -> str:
    import re
    m = re.search(r'\(([A-Z]{2,3})\)$', str(club))
    return m.group(1) if m else ''


def _club_short(club: str) -> str:
    import re
    m = re.match(r'^(.+?)\s*\([A-Z]{2,3}\)$', str(club))
    return m.group(1).strip() if m else str(club).strip()


# ── Captain lookup ────────────────────────────────────────────────────────────

def _get_team_captain(roster_team_name: str) -> str:
    """Look up team captain from the teams table (by roster CSV name)."""
    from services.database import get_connection
    conn = get_connection()
    # teams table uses app names; try to find via reverse mapping
    row = conn.execute("SELECT captain FROM teams WHERE name = ?", (roster_team_name,)).fetchone()
    conn.close()
    if row and row[0]:
        return str(row[0])
    # Try reverse-mapped name
    from services.roster import _APP_TO_ROSTER
    for app_name, roster_name in _APP_TO_ROSTER.items():
        if roster_name == roster_team_name:
            conn = get_connection()
            row2 = conn.execute("SELECT captain FROM teams WHERE name = ?", (app_name,)).fetchone()
            conn.close()
            if row2 and row2[0]:
                return str(row2[0])
    return ""


# ── Core card data ────────────────────────────────────────────────────────────

def get_player_card_data(player_slug: str) -> dict | None:
    """
    Build the full player card data dict for a given slug.
    Returns None if slug not found.
    """
    from services.teams import get_flag
    from services.roster import get_mls_players, get_team_roster

    player = get_player(player_slug)
    if player is None:
        return None

    roster_team = player['team']   # as stored in roster CSV
    name        = player['name']
    position    = player['position']
    club        = player['club']
    shirt_num   = player['shirt_number']
    age         = player['age']
    birthdate   = player.get('birthdate', '')
    club_sh     = player['club_short']
    club_code   = _club_country_code(club)

    # App-name team (for flag lookup, etc.)
    from services.roster import _APP_TO_ROSTER
    _rev = {v: k for k, v in _APP_TO_ROSTER.items()}
    app_team = _rev.get(roster_team, roster_team)
    flag     = get_flag(app_team)

    # Captain check
    captain_name = _get_team_captain(roster_team)
    is_captain   = False
    if captain_name:
        cap_last = captain_name.split()[-1].lower()
        is_captain = cap_last in name.lower()

    # Youngest / oldest on team
    roster = get_team_roster(app_team)
    is_youngest = False
    is_veteran  = False
    if not roster.empty:
        youngest_name = roster.loc[roster['age'].idxmin(), 'player_name']
        oldest_name   = roster.loc[roster['age'].idxmax(), 'player_name']
        is_youngest   = name == youngest_name
        is_veteran    = name == oldest_name and age >= 32

    # MLS check
    is_mls = '(USA)' in str(club)

    # Quick fact badges
    quick_facts: list[str] = []
    if is_captain:          quick_facts.append("🎖️ Captain")
    if is_youngest:         quick_facts.append("🌱 Youngest on Squad")
    if is_veteran:          quick_facts.append("📅 Veteran")
    if is_mls:              quick_facts.append("🏟️ MLS Player")
    if club_code == "ENG":  quick_facts.append("🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League")
    if club_code == "ESP":  quick_facts.append("🇪🇸 La Liga")
    if club_code == "GER":  quick_facts.append("🇩🇪 Bundesliga")
    if club_code == "ITA":  quick_facts.append("🇮🇹 Serie A")
    if club_code == "FRA":  quick_facts.append("🇫🇷 Ligue 1")
    if not quick_facts:
        quick_facts.append(f"{pos_icon(position)} {position}")

    # Why you might know them
    why_parts: list[str] = []
    if is_captain:
        why_parts.append(f"Captain of {app_team}.")
    if is_mls:
        why_parts.append(f"Plays in MLS for {club_sh}.")
    elif club_sh:
        league = _LEAGUE_NAMES.get(club_code, '')
        if league:
            why_parts.append(f"Plays for **{club_sh}** in {league}.")
        else:
            why_parts.append(f"Plays for **{club_sh}**.")
    if is_youngest:
        why_parts.append(f"One of the youngest players at the 2026 World Cup — just {age} years old.")
    if is_veteran:
        why_parts.append(f"A tournament veteran at {age} years old — one of the most experienced players on the squad.")
    why_know = " ".join(why_parts) if why_parts else f"Representing {app_team} as a {position}."

    # One thing to remember
    one_thing = _ONE_THING.get(player_slug, "")
    if not one_thing:
        # Auto-generate fallback
        if is_captain:
            one_thing = f"The captain and leader of {app_team}."
        elif is_youngest:
            one_thing = f"One of the youngest players at the 2026 World Cup — just {age} years old."
        elif club_code == "ENG":
            one_thing = f"Plays in the Premier League, one of the most-watched soccer leagues in the world, for {club_sh}."
        elif club_code in ("ESP", "GER", "ITA", "FRA"):
            one_thing = f"Plays in one of Europe's top leagues for {club_sh}."
        else:
            one_thing = f"A {position.lower()} representing {app_team} at the 2026 World Cup."

    # Similar players — same team, same position, different player
    similar: list[dict] = []
    if not roster.empty:
        same_pos = roster[
            (roster['position'] == position) &
            (roster['player_name'] != name)
        ].sort_values('shirt_number')
        for _, r in same_pos.head(3).iterrows():
            similar.append({
                'name':         r['player_name'],
                'shirt_number': int(r['shirt_number']),
                'position':     r['position'],
                'club_short':   r['club_short'],
                'age':          int(r['age']),
            })

    return {
        'player_slug':  player_slug,
        'name':         name,
        'team':         app_team,
        'roster_team':  roster_team,
        'flag':         flag,
        'position':     position,
        'club':         club,
        'club_short':   club_sh,
        'club_code':    club_code,
        'shirt_number': shirt_num,
        'age':          age,
        'birthdate':    birthdate,
        'is_captain':   is_captain,
        'is_youngest':  is_youngest,
        'is_veteran':   is_veteran,
        'is_mls':       is_mls,
        'quick_facts':  quick_facts,
        'why_know':     why_know,
        'one_thing':    one_thing,
        'similar':      similar,
    }


# ── Player discovery tracking ─────────────────────────────────────────────────

def log_player_discovery(
    user_id: int, player_slug: str, player_name: str,
    team: str, is_captain: bool = False,
) -> bool:
    """
    Log or update a player profile view for a user.
    Returns True if this was the user's first time viewing this player.
    """
    conn0 = get_connection()
    po = conn0.execute("SELECT picks_only FROM users WHERE id=?", (user_id,)).fetchone()
    conn0.close()
    if po and po[0]:
        return False

    now = datetime.now().isoformat()
    conn = get_connection()
    existing = conn.execute(
        "SELECT visit_count FROM player_discoveries WHERE user_id=? AND player_slug=?",
        (user_id, player_slug),
    ).fetchone()
    is_first = existing is None
    conn.execute("""
        INSERT INTO player_discoveries (user_id, player_slug, player_name, team, first_visited_at, visit_count)
        VALUES (?, ?, ?, ?, ?, 1)
        ON CONFLICT(user_id, player_slug)
        DO UPDATE SET visit_count = visit_count + 1
    """, (user_id, player_slug, player_name, team, now))
    conn.commit()
    conn.close()

    if is_first:
        from services.activity import log_activity
        log_activity(user_id, 'player_discovered',
                     country_name=team,
                     message=f"discovered {player_name} ({team})")
        # Check player achievements
        from services.achievements import check_individual_achievements
        check_individual_achievements(user_id)

    return is_first


def get_player_discoveries_count(user_id: int) -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) FROM player_discoveries WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def get_player_captain_discovered(user_id: int) -> bool:
    """Has user discovered any team captain?"""
    conn = get_connection()
    # We stored is_captain metadata? No — but we can check against team captains.
    # Simpler: check if any discovered player is a captain by re-deriving.
    rows = conn.execute(
        "SELECT player_slug FROM player_discoveries WHERE user_id=?", (user_id,)
    ).fetchall()
    conn.close()
    for (slug,) in rows:
        data = get_player_card_data(slug)
        if data and data.get('is_captain'):
            return True
    return False


def get_mls_discoveries_count(user_id: int) -> int:
    """Count distinct MLS players discovered by user."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT player_slug FROM player_discoveries WHERE user_id=?", (user_id,)
    ).fetchall()
    conn.close()
    count = 0
    for (slug,) in rows:
        data = get_player_card_data(slug)
        if data and data.get('is_mls'):
            count += 1
    return count


def get_player_team_count(user_id: int) -> int:
    """Count of distinct teams from player discoveries."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(DISTINCT team) FROM player_discoveries WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else 0


# ── Featured Player of the Day ────────────────────────────────────────────────

def get_featured_player_of_day() -> dict | None:
    """
    Deterministic daily featured player (changes once per day, not per refresh).
    Logic: if matches today → pick a featured player from one of today's teams.
    Otherwise → rotate through all player slugs.
    """
    from services.teams import get_flag
    from services.database import get_connection as _gc

    today = date.today()
    seed  = today.toordinal()

    df = _load_slugged()
    if df.empty:
        return None

    # Try to pick from today's matches
    conn = _gc()
    today_matches = pd.read_sql(
        "SELECT home_team, away_team FROM matches WHERE match_date=? AND status='scheduled'",
        conn, params=(today.isoformat(),),
    )
    conn.close()

    if not today_matches.empty:
        today_teams: list[str] = []
        for _, m in today_matches.iterrows():
            today_teams += [m['home_team'], m['away_team']]
        roster_names = {_roster_name(t) for t in today_teams}
        pool = df[df['team'].isin(roster_names)]
        if pool.empty:
            pool = df
    else:
        pool = df

    idx    = seed % len(pool)
    row    = pool.iloc[idx]
    slug   = row['player_slug']
    data   = get_player_card_data(slug)
    return data


# ── Streamlit modal renderer ──────────────────────────────────────────────────

def render_player_modal_content(slug: str, user_id: int) -> None:
    """
    Renders the full player card inside a Streamlit @st.dialog.
    Call this from a @st.dialog-decorated function in each page.
    """
    import streamlit as st

    data = get_player_card_data(slug)
    if data is None:
        st.error("Player not found. The roster data may not be loaded.")
        return

    # Log the discovery
    is_first = log_player_discovery(
        user_id, slug, data['name'], data['team'], data.get('is_captain', False)
    )

    # ── First discovery celebration ─────────────────────────────────
    if is_first:
        count = get_player_discoveries_count(user_id)
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#052e16,#166534);"
            f"border:1px solid #4ADE80;border-radius:10px;padding:.6rem 1rem;"
            f"margin-bottom:.6rem;font-size:.82rem;color:#4ADE80;font-weight:700'>"
            f"🎉 New player discovered! {data['name']} added to your collection. "
            f"You've now discovered {count} player{'s' if count != 1 else ''}!</div>",
            unsafe_allow_html=True,
        )

    # ── Header ──────────────────────────────────────────────────────
    h_flag, h_info = st.columns([1, 3])
    with h_flag:
        st.markdown(
            f"<div style='text-align:center'>"
            f"<div style='font-size:4rem;line-height:1'>{data['flag']}</div>"
            f"<div style='font-size:2rem;font-weight:900;color:#FCD34D;margin-top:.2rem'>"
            f"#{data['shirt_number']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with h_info:
        st.markdown(
            f"<div style='padding:.2rem 0'>"
            f"<div style='font-size:1.6rem;font-weight:900;color:#F1F5F9;line-height:1.15'>"
            f"{data['name']}</div>"
            f"<div style='font-size:1rem;color:#94A3B8;margin-top:.2rem'>"
            f"{data['flag']} {data['team']}</div>"
            f"<div style='font-size:.88rem;color:#CBD5E1;margin-top:.15rem'>"
            f"{data['position']} · Age {data['age']}"
            f"{'  ·  🎂 ' + data['birthdate'][:4] if data.get('birthdate') else ''}"
            f"</div>"
            f"<div style='font-size:.85rem;color:#64748B;margin-top:.1rem'>"
            f"🏟️ {data['club_short']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Quick fact badges ────────────────────────────────────────────
    if data['quick_facts']:
        badges = " ".join(
            f"<span style='display:inline-block;background:rgba(99,102,241,.2);"
            f"border:1px solid rgba(99,102,241,.4);border-radius:20px;"
            f"font-size:.72rem;font-weight:700;padding:.15rem .55rem;"
            f"color:#A5B4FC;margin:.15rem .1rem'>{f}</span>"
            for f in data['quick_facts']
        )
        st.markdown(
            f"<div style='margin:.3rem 0 .5rem'>{badges}</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Why you might know them ──────────────────────────────────────
    st.markdown(
        "<div style='font-size:.68rem;font-weight:800;color:#64748B;"
        "text-transform:uppercase;letter-spacing:.06em'>Why You Might Know Them</div>",
        unsafe_allow_html=True,
    )
    st.markdown(data['why_know'])

    # ── One thing to remember ────────────────────────────────────────
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#1E293B,#0F172A);"
        f"border-left:4px solid #F59E0B;border-radius:0 10px 10px 0;"
        f"padding:.65rem .9rem;margin:.5rem 0'>"
        f"<div style='font-size:.65rem;font-weight:800;color:#D97706;"
        f"text-transform:uppercase;letter-spacing:.06em;margin-bottom:.2rem'>"
        f"⭐ One Thing To Remember</div>"
        f"<div style='font-size:.88rem;color:#F1F5F9;line-height:1.55'>{data['one_thing']}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Similar players ──────────────────────────────────────────────
    if data['similar']:
        st.divider()
        st.markdown(
            "<div style='font-size:.68rem;font-weight:800;color:#64748B;"
            "text-transform:uppercase;letter-spacing:.06em;margin-bottom:.4rem'>"
            "You Might Also Like</div>",
            unsafe_allow_html=True,
        )
        sim_cols = st.columns(len(data['similar']))
        for scol, sim in zip(sim_cols, data['similar']):
            with scol:
                st.markdown(
                    f"<div style='background:rgba(30,41,59,.7);border:1px solid rgba(148,163,184,.15);"
                    f"border-radius:10px;padding:.6rem .5rem;text-align:center'>"
                    f"<div style='font-size:1.3rem;font-weight:900;color:#FCD34D'>#{sim['shirt_number']}</div>"
                    f"<div style='font-size:.78rem;font-weight:700;color:#F1F5F9;line-height:1.2'>{sim['name']}</div>"
                    f"<div style='font-size:.65rem;color:#64748B;margin-top:.1rem'>{sim['club_short']}</div>"
                    f"<div style='font-size:.62rem;color:#475569'>Age {sim['age']}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Footer link to country profile ──────────────────────────────
    st.divider()
    st.page_link(
        "pages/country_profile.py",
        label=f"Explore {data['team']} →",
        icon=data['flag'],
    )
