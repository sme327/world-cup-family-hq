"""
ESPN public API service for match recaps and key events.
No API key required. Degrades gracefully — always returns search links even if
ESPN data is unavailable.

ESPN endpoint: site.api.espn.com/apis/site/v2/sports/soccer/fifa.world
"""

import requests
import streamlit as st

_ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"
_TIMEOUT   = 8

# Our app team names → ESPN display names (where they differ)
_TO_ESPN: dict[str, str] = {
    "USA":                    "United States",
    "DR Congo":               "Congo DR",
    "Türkiye":                "Turkey",
    "Czechia":                "Czech Republic",
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "Ivory Coast":            "Côte d'Ivoire",
    "South Korea":            "Korea Republic",
    "Iran":                   "IR Iran",
    "Cape Verde":             "Cabo Verde",
    "Curaçao":                "Curaçao",
}


def _espn_name(app_name: str) -> str:
    return _TO_ESPN.get(app_name, app_name)


def _names_match(a: str, b: str) -> bool:
    """Fuzzy match — handles 'Bosnia' matching 'Bosnia-Herzegovina' etc."""
    a, b = a.lower().strip(), b.lower().strip()
    return a == b or a in b or b in a


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_scoreboard(date_str: str) -> list[dict]:
    """All ESPN events for a given date (YYYY-MM-DD)."""
    try:
        resp = requests.get(
            f"{_ESPN_BASE}/scoreboard",
            params={"dates": date_str.replace("-", "")},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("events", [])
    except Exception:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_summary(event_id: str) -> dict:
    """ESPN match summary for a specific event ID."""
    try:
        resp = requests.get(
            f"{_ESPN_BASE}/summary",
            params={"event": event_id},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def _find_event_id(home_team: str, away_team: str, match_date: str) -> str | None:
    """Search ESPN scoreboard to find the event ID for this match."""
    events = _fetch_scoreboard(match_date)
    espn_home = _espn_name(home_team)
    espn_away = _espn_name(away_team)

    for event in events:
        comps = event.get("competitions", [{}])
        if not comps:
            continue
        competitors = comps[0].get("competitors", [])
        team_map = {c.get("homeAway", ""): c.get("team", {}).get("displayName", "") for c in competitors}

        h, a = team_map.get("home", ""), team_map.get("away", "")

        # Try both orientations (ESPN home/away may differ from CSV)
        if (_names_match(espn_home, h) and _names_match(espn_away, a)) or \
           (_names_match(espn_home, a) and _names_match(espn_away, h)):
            return event.get("id")

    return None


def _player_from_text(text: str) -> str:
    """Extract player name from ESPN event text like 'Goal! Team 1, Team 2. Player Name (Team...'"""
    import re
    # Pattern: last ". Name (Team" before the parenthesis
    m = re.search(r'\.\s+([A-Z][A-Za-z\s\-\'\.]+?)\s*\(', text)
    return m.group(1).strip() if m else ""


def _clock_key(clock_str: str) -> tuple[int, int]:
    """Sort key for '45+2'' → (45, 2), '78'' → (78, 0)."""
    try:
        clean = clock_str.replace("'", "").strip()
        parts = clean.split("+")
        return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except Exception:
        return (999, 0)


def _parse_key_events(summary: dict) -> list[dict]:
    """Extract goals and red cards from ESPN summary keyEvents."""
    events = []
    for ev in summary.get("keyEvents", []):
        ev_type = ev.get("type", {}).get("text", "").lower()

        if "goal" in ev_type:
            icon = "😬" if "own goal" in ev_type else "⚽"
        elif "red card" in ev_type or "ejection" in ev_type:
            icon = "🟥"
        else:
            continue  # skip yellows, subs, delays, halftime, etc.

        clock     = ev.get("clock", {}).get("displayValue", "")
        team_name = ev.get("team", {}).get("displayName", "")
        ev_text   = ev.get("text", "")

        # ESPN often omits participants — extract name from text field instead
        player = _player_from_text(ev_text) if ev_text else ""
        if not player:
            participants = ev.get("participants", [])
            if participants:
                ath = participants[0].get("athlete", {})
                player = ath.get("shortName") or ath.get("displayName", "")

        events.append({
            "clock":  clock,
            "icon":   icon,
            "player": player,
            "team":   team_name,
        })

    events.sort(key=lambda e: _clock_key(e["clock"]))
    return events


@st.cache_data(ttl=300, show_spinner=False)
def get_match_recap(home_team: str, away_team: str, match_date: str) -> dict:
    """
    Fetch ESPN recap data for a completed match.
    Always returns a usable dict — at minimum the generated search links.

    Keys:
        found (bool)           — True if ESPN key events were retrieved
        key_events (list)      — goals/red cards [{clock, icon, player, team}]
        youtube_url (str)      — YouTube highlights search link
        news_url (str)         — Google News search link
        fifa_url (str)         — FIFA.com match centre search
    """
    youtube_url = (
        "https://www.youtube.com/results?search_query="
        + requests.utils.quote(f"{home_team} {away_team} 2026 FIFA World Cup highlights")
    )
    news_url = (
        "https://news.google.com/search?q="
        + requests.utils.quote(f"{home_team} {away_team} 2026 World Cup")
    )
    fifa_url = "https://www.fifa.com/fifaplus/en/tournaments/mens/worldcup/canadamexicousa2026/match-centre"

    base = {
        "found":       False,
        "key_events":  [],
        "youtube_url": youtube_url,
        "news_url":    news_url,
        "fifa_url":    fifa_url,
    }

    event_id = _find_event_id(home_team, away_team, match_date)
    if not event_id:
        return base

    summary = _fetch_summary(event_id)
    if not summary:
        return {**base, "found": True}  # found the event but no detail yet

    key_events = _parse_key_events(summary)
    return {**base, "found": True, "key_events": key_events}
