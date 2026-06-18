import streamlit as st
import pandas as pd
from services.database import get_connection

# ── Official Round of 32 bracket (FIFA 2026) ─────────────────────────────────
# Format: (match_num, slot_A, slot_B, third_groups_for_A, third_groups_for_B)
# "3rd" means the slot is filled by a best third-place team from those groups.
_R32 = [
    (73,  "2A",  "2B",  None,        None),
    (74,  "1E",  "3rd", None,        "A/B/C/D/F"),
    (75,  "1F",  "2C",  None,        None),
    (76,  "1C",  "2F",  None,        None),
    (77,  "1I",  "3rd", None,        "C/D/F/G/H"),
    (78,  "2E",  "2I",  None,        None),
    (79,  "1A",  "3rd", None,        "C/E/F/H/I"),
    (80,  "1L",  "3rd", None,        "E/H/I/J/K"),
    (81,  "1D",  "3rd", None,        "B/E/F/I/J"),
    (82,  "1G",  "3rd", None,        "A/E/H/I/J"),
    (83,  "2K",  "2L",  None,        None),
    (84,  "1H",  "2J",  None,        None),
    (85,  "1B",  "3rd", None,        "E/F/G/I/J"),
    (86,  "1J",  "2H",  None,        None),
    (87,  "1K",  "3rd", None,        "D/E/I/J/L"),
    (88,  "2D",  "2G",  None,        None),
]

# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def _load_data():
    conn = get_connection()
    matches = pd.read_sql(
        "SELECT * FROM matches WHERE status='completed' ORDER BY match_date, kickoff_time_et",
        conn,
    )
    teams = pd.read_sql("SELECT name, flag_emoji, group_letter FROM teams", conn)
    conn.close()
    return matches, teams


def _compute_standings(matches: pd.DataFrame, teams: pd.DataFrame) -> dict:
    stats: dict = {}
    for _, t in teams.iterrows():
        g = t["group_letter"]
        if g not in stats:
            stats[g] = {}
        stats[g][t["name"]] = dict(
            team=t["name"], flag=t["flag_emoji"], group=g,
            p=0, w=0, d=0, l=0, gf=0, ga=0,
        )
    for _, m in matches.iterrows():
        ht, at = m["home_team"], m["away_team"]
        hs, as_ = int(m["home_score"]), int(m["away_score"])
        team_row = teams[teams["name"] == ht]
        if team_row.empty:
            continue
        g = team_row.iloc[0]["group_letter"]
        if g not in stats or ht not in stats[g] or at not in stats[g]:
            continue
        h = stats[g][ht]; a = stats[g][at]
        h["p"] += 1; a["p"] += 1
        h["gf"] += hs; h["ga"] += as_
        a["gf"] += as_; a["ga"] += hs
        if hs > as_:
            h["w"] += 1; a["l"] += 1
        elif hs < as_:
            a["w"] += 1; h["l"] += 1
        else:
            h["d"] += 1; a["d"] += 1

    result = {}
    for g, td in sorted(stats.items()):
        rows = list(td.values())
        df = pd.DataFrame(rows)
        df["pts"] = df["w"] * 3 + df["d"]
        df["gd"]  = df["gf"] - df["ga"]
        df = df.sort_values(
            ["pts", "gd", "gf", "team"],
            ascending=[False, False, False, True],
        ).reset_index(drop=True)
        result[g] = df
    return result


def _group_played(matches: pd.DataFrame, teams: pd.DataFrame, group: str) -> int:
    group_teams = set(teams[teams["group_letter"] == group]["name"].tolist())
    return sum(
        1 for _, m in matches.iterrows()
        if m["home_team"] in group_teams and m["away_team"] in group_teams
    )


def _top8_third(standings: dict) -> list[dict]:
    """Return sorted list of all 3rd-place teams (best first)."""
    thirds = []
    for g, df in standings.items():
        if len(df) >= 3:
            row = df.iloc[2]
            thirds.append({
                "team": row["team"], "flag": row["flag"], "group": g,
                "pts": row["pts"], "gd": row["gd"], "gf": row["gf"],
            })
    thirds.sort(key=lambda x: (-x["pts"], -x["gd"], -x["gf"], x["team"]))
    return thirds[:8]


def _resolve_slot(code: str, third_groups: str | None,
                  standings: dict) -> tuple[str, str, bool]:
    """(flag, name, is_tbd)"""
    if code == "3rd":
        # Don't try to name a specific 3rd-place team — the 495-scenario seeding
        # means multiple slots share eligible groups. Just show the group labels.
        return "🎯", f"Best 3rd ({third_groups})", True
    pos   = int(code[0]) - 1
    group = code[1]
    df    = standings.get(group)
    if df is not None and len(df) > pos:
        row = df.iloc[pos]
        return row["flag"], row["team"], row["p"] == 0
    return "❓", code, True


# ── Rendering helpers ─────────────────────────────────────────────────────────

_POS_STYLE = {
    0: ("rgba(16,185,129,.18)", "#4ADE80"),
    1: ("rgba(16,185,129,.12)", "#4ADE80"),
    2: ("rgba(251,191,36,.12)", "#FCD34D"),
    3: ("rgba(148,163,184,.06)", "#94A3B8"),
}


def _render_group_card(group: str, df: pd.DataFrame, played: int):
    badge = (
        "<span style='background:#4ADE80;color:#0F172A;border-radius:5px;"
        "padding:.06rem .38rem;font-size:.65rem;font-weight:800;margin-left:.45rem'>FINAL</span>"
        if played == 6 else
        f"<span style='background:rgba(251,191,36,.22);color:#FCD34D;border-radius:5px;"
        f"padding:.06rem .38rem;font-size:.65rem;font-weight:700;margin-left:.45rem'>{played}/6</span>"
    )
    st.markdown(
        f"<div style='font-size:1.05rem;font-weight:900;letter-spacing:.06em;"
        f"color:#F8FAFC;margin-bottom:.45rem'>GROUP {group}{badge}</div>",
        unsafe_allow_html=True,
    )
    # Header row
    st.markdown(
        "<div style='display:grid;grid-template-columns:1.4rem 1fr repeat(7,.82rem);"
        "gap:.08rem;font-size:.65rem;font-weight:700;color:#64748B;"
        "text-transform:uppercase;letter-spacing:.04em;"
        "padding:.18rem .35rem;border-bottom:1px solid rgba(148,163,184,.15)'>"
        "<span></span><span>Team</span>"
        "<span style='text-align:center'>P</span>"
        "<span style='text-align:center'>W</span>"
        "<span style='text-align:center'>D</span>"
        "<span style='text-align:center'>L</span>"
        "<span style='text-align:center'>GF</span>"
        "<span style='text-align:center'>GA</span>"
        "<span style='text-align:right'>Pts</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    for i, row in df.iterrows():
        bg, accent = _POS_STYLE.get(i, ("", "#F8FAFC"))
        st.markdown(
            f"<div style='display:grid;grid-template-columns:1.4rem 1fr repeat(7,.82rem);"
            f"gap:.08rem;align-items:center;padding:.3rem .35rem;"
            f"background:{bg};border-radius:6px;margin:.08rem 0'>"
            f"<span style='font-size:.7rem;color:{accent};font-weight:700;"
            f"text-align:center'>{i+1}</span>"
            f"<span style='font-size:.88rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>"
            f"<span style='font-size:1.05rem'>{row['flag']}</span> "
            f"<span style='font-weight:600;color:#F1F5F9'>{row['team']}</span></span>"
            f"<span style='text-align:center;font-size:.78rem;color:#CBD5E1'>{row['p']}</span>"
            f"<span style='text-align:center;font-size:.78rem;color:#CBD5E1'>{row['w']}</span>"
            f"<span style='text-align:center;font-size:.78rem;color:#CBD5E1'>{row['d']}</span>"
            f"<span style='text-align:center;font-size:.78rem;color:#CBD5E1'>{row['l']}</span>"
            f"<span style='text-align:center;font-size:.78rem;color:#CBD5E1'>{row['gf']}</span>"
            f"<span style='text-align:center;font-size:.78rem;color:#CBD5E1'>{row['ga']}</span>"
            f"<span style='text-align:right;font-size:.92rem;font-weight:900;color:{accent}'>{row['pts']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_r32_card(num: int, f1: str, n1: str, f2: str, n2: str, tbd: bool):
    alpha = ".5" if tbd else "1"
    border = "rgba(148,163,184,.12)" if tbd else "rgba(99,102,241,.28)"
    st.markdown(
        f"<div style='background:rgba(15,23,42,.6);border:1px solid {border};"
        f"border-radius:12px;padding:.7rem 1rem;opacity:{alpha};margin:.2rem 0'>"
        f"<div style='font-size:.6rem;color:#475569;font-weight:700;"
        f"letter-spacing:.06em;margin-bottom:.5rem'>MATCH {num}</div>"
        # Team 1
        f"<div style='display:flex;align-items:center;gap:.55rem;margin-bottom:.3rem'>"
        f"<span style='font-size:2rem;line-height:1;flex-shrink:0'>{f1}</span>"
        f"<span style='font-weight:700;font-size:.95rem;color:#F1F5F9'>{n1}</span>"
        f"</div>"
        # VS divider
        f"<div style='font-size:.7rem;font-weight:900;color:#475569;"
        f"letter-spacing:.1em;padding:.1rem 0 .3rem .1rem'>VS</div>"
        # Team 2
        f"<div style='display:flex;align-items:center;gap:.55rem'>"
        f"<span style='font-size:2rem;line-height:1;flex-shrink:0'>{f2}</span>"
        f"<span style='font-weight:700;font-size:.95rem;color:#F1F5F9'>{n2}</span>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Page ──────────────────────────────────────────────────────────────────────

st.markdown("## 📊 Group Stage Standings")
st.caption("Updated from scores entered in Admin. Top 2 per group advance; best 8 third-place teams also advance.")

matches, teams = _load_data()
standings      = _compute_standings(matches, teams)

# Summary bar
total_played   = len(matches)
complete_groups = sum(1 for g in standings if _group_played(matches, teams, g) == 6)
pct            = int(total_played / 72 * 100)

m1, m2, m3 = st.columns(3)
m1.metric("Matches Played", f"{total_played} / 72")
m2.metric("Groups Complete", f"{complete_groups} / 12")
m3.metric("Tournament Progress", f"{pct}%")
st.progress(pct / 100)

# Legend
st.markdown(
    "<div style='display:flex;gap:1.4rem;flex-wrap:wrap;margin:.6rem 0 .8rem'>"
    "<span><span style='display:inline-block;width:.65rem;height:.65rem;"
    "background:rgba(16,185,129,.4);border-radius:2px;margin-right:.3rem'></span>"
    "<span style='font-size:.8rem;color:#94A3B8'>Top 2 — advancing</span></span>"
    "<span><span style='display:inline-block;width:.65rem;height:.65rem;"
    "background:rgba(251,191,36,.35);border-radius:2px;margin-right:.3rem'></span>"
    "<span style='font-size:.8rem;color:#94A3B8'>3rd — best 8 also advance</span></span>"
    "<span><span style='display:inline-block;width:.65rem;height:.65rem;"
    "background:rgba(148,163,184,.15);border-radius:2px;margin-right:.3rem'></span>"
    "<span style='font-size:.8rem;color:#94A3B8'>4th — eliminated</span></span>"
    "</div>",
    unsafe_allow_html=True,
)

st.divider()

# ── Group standings grid (2 columns) ─────────────────────────────────────────
groups      = list(standings.keys())
rows_of_2   = [groups[i:i+2] for i in range(0, len(groups), 2)]

for row_groups in rows_of_2:
    cols = st.columns(2, gap="medium")
    for col, g in zip(cols, row_groups):
        with col:
            with st.container(border=True):
                played = _group_played(matches, teams, g)
                _render_group_card(g, standings[g], played)

st.divider()

# ── "If It Ended Today" bracket ───────────────────────────────────────────────
st.markdown("## 🎯 If It Ended Today — Round of 32")
st.caption(
    "Based on current standings. Matches involving best 3rd-place teams "
    "show the top-ranked eligible team (subject to change as groups finish)."
)

top8 = _top8_third(standings)

# Who's in — quick summary strip
advancing_flags = []
for g in sorted(standings.keys()):
    df = standings[g]
    for i in range(min(2, len(df))):
        advancing_flags.append(df.iloc[i]["flag"])

st.markdown(
    "<div style='margin:.5rem 0 1rem'>"
    "<div style='font-size:.75rem;font-weight:700;color:#64748B;"
    "text-transform:uppercase;letter-spacing:.06em;margin-bottom:.4rem'>"
    "🟢 Advancing — current top 2 from each group</div>"
    "<div style='font-size:1.8rem;line-height:1.4;letter-spacing:.05rem'>"
    + "".join(advancing_flags) +
    "</div></div>",
    unsafe_allow_html=True,
)

if top8:
    third_flags = "".join(t["flag"] for t in top8)
    st.markdown(
        "<div style='margin:.3rem 0 1.2rem'>"
        "<div style='font-size:.75rem;font-weight:700;color:#64748B;"
        "text-transform:uppercase;letter-spacing:.06em;margin-bottom:.4rem'>"
        "🟡 Best 3rd-place race — top 8 advance (in pts order)</div>"
        "<div style='font-size:1.8rem;line-height:1.4;letter-spacing:.05rem'>"
        + third_flags +
        "</div></div>",
        unsafe_allow_html=True,
    )

st.divider()

# Build matchup data
matchups = []
for num, slot_a, slot_b, third_a, third_b in _R32:
    f1, n1, tbd1 = _resolve_slot(slot_a, third_a, standings)
    f2, n2, tbd2 = _resolve_slot(slot_b, third_b, standings)
    tbd = tbd1 or tbd2
    matchups.append((num, f1, n1, f2, n2, tbd))

# Display in 2 columns, sorted by match number
left  = [m for i, m in enumerate(matchups) if i % 2 == 0]
right = [m for i, m in enumerate(matchups) if i % 2 == 1]

col_l, col_r = st.columns(2, gap="medium")
with col_l:
    for num, f1, n1, f2, n2, tbd in left:
        _render_r32_card(num, f1, n1, f2, n2, tbd)
with col_r:
    for num, f1, n1, f2, n2, tbd in right:
        _render_r32_card(num, f1, n1, f2, n2, tbd)

st.divider()
st.caption(
    "⚽ Standings tiebreakers: Points → Goal Difference → Goals For → Team name  |  "
    "3rd-place bracket slots follow FIFA's official 2026 bracket (495 possible seedings — "
    "final assignment determined when all group stage matches complete June 27)."
)
