import streamlit as st
import pandas as pd
from services.database import get_connection
from services.teams import get_all_teams

# ── Data ──────────────────────────────────────────────────────────────────────

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


def _compute_standings(matches: pd.DataFrame, teams: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return {group_letter: standings_df} sorted by FIFA tiebreaker."""
    stats: dict[str, dict[str, dict]] = {}

    for _, t in teams.iterrows():
        g = t["group_letter"]
        if g not in stats:
            stats[g] = {}
        stats[g][t["name"]] = dict(
            team=t["name"], flag=t["flag_emoji"],
            p=0, w=0, d=0, l=0, gf=0, ga=0,
        )

    for _, m in matches.iterrows():
        ht, at = m["home_team"], m["away_team"]
        hs, as_ = int(m["home_score"]), int(m["away_score"])

        # find group (use home team)
        team_row = teams[teams["name"] == ht]
        if team_row.empty:
            continue
        g = team_row.iloc[0]["group_letter"]

        if g not in stats or ht not in stats[g] or at not in stats[g]:
            continue

        h = stats[g][ht]
        a = stats[g][at]

        h["p"] += 1;  a["p"] += 1
        h["gf"] += hs; h["ga"] += as_
        a["gf"] += as_; a["ga"] += hs

        if hs > as_:
            h["w"] += 1; a["l"] += 1
        elif hs < as_:
            a["w"] += 1; h["l"] += 1
        else:
            h["d"] += 1; a["d"] += 1

    result = {}
    for g, teams_dict in sorted(stats.items()):
        rows = list(teams_dict.values())
        df = pd.DataFrame(rows)
        df["pts"] = df["w"] * 3 + df["d"]
        df["gd"] = df["gf"] - df["ga"]
        df = df.sort_values(
            ["pts", "gd", "gf", "team"],
            ascending=[False, False, False, True],
        ).reset_index(drop=True)
        result[g] = df

    return result


def _group_matches_played(matches: pd.DataFrame, teams: pd.DataFrame, group: str) -> int:
    group_teams = set(teams[teams["group_letter"] == group]["name"].tolist())
    count = 0
    for _, m in matches.iterrows():
        if m["home_team"] in group_teams and m["away_team"] in group_teams:
            count += 1
    return count


# ── Row colours ───────────────────────────────────────────────────────────────

_POS_STYLES = {
    0: ("rgba(16,185,129,.18)", "#4ADE80", "✅ Advancing"),   # 1st
    1: ("rgba(16,185,129,.12)", "#4ADE80", "✅ Advancing"),   # 2nd
    2: ("rgba(251,191,36,.12)", "#FCD34D", "⚡ In contention"), # 3rd
    3: ("rgba(148,163,184,.08)", "#94A3B8", ""),               # 4th
}


def _render_group_card(group: str, df: pd.DataFrame, played: int):
    total_matches = 6  # 4 teams × 3 matchday × ... = C(4,2) = 6 per group
    complete = played == total_matches
    header_badge = (
        "<span style='background:#4ADE80;color:#0F172A;border-radius:6px;"
        "padding:.08rem .42rem;font-size:.68rem;font-weight:800;margin-left:.5rem'>"
        "FINAL</span>" if complete else
        f"<span style='background:rgba(251,191,36,.22);color:#FCD34D;border-radius:6px;"
        f"padding:.08rem .42rem;font-size:.68rem;font-weight:700;margin-left:.5rem'>"
        f"{played}/6</span>"
    )

    st.markdown(
        f"<div style='font-size:1.1rem;font-weight:900;letter-spacing:.06em;"
        f"color:#F8FAFC;margin-bottom:.5rem'>"
        f"GROUP {group}{header_badge}</div>",
        unsafe_allow_html=True,
    )

    # Table header
    st.markdown(
        "<div style='display:grid;grid-template-columns:1.6rem 1fr .9rem .9rem .9rem .9rem .9rem .9rem 1.1rem;"
        "gap:.1rem;font-size:.68rem;font-weight:700;color:#94A3B8;text-transform:uppercase;"
        "letter-spacing:.04em;padding:.2rem .4rem;border-bottom:1px solid rgba(148,163,184,.18)'>"
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
        bg, accent, _ = _POS_STYLES.get(i, ("", "#F8FAFC", ""))
        gd_str = f"+{row['gd']}" if row['gd'] > 0 else str(row['gd'])
        pos_num = i + 1

        st.markdown(
            f"<div style='display:grid;grid-template-columns:1.6rem 1fr .9rem .9rem .9rem .9rem .9rem .9rem 1.1rem;"
            f"gap:.1rem;align-items:center;padding:.32rem .4rem;"
            f"background:{bg};border-radius:6px;margin:.1rem 0'>"
            f"<span style='font-size:.72rem;color:{accent};font-weight:700;text-align:center'>{pos_num}</span>"
            f"<span style='font-size:.92rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>"
            f"<span style='font-size:1.1rem'>{row['flag']}</span> "
            f"<span style='font-weight:600;color:#F1F5F9'>{row['team']}</span></span>"
            f"<span style='text-align:center;font-size:.8rem;color:#CBD5E1'>{row['p']}</span>"
            f"<span style='text-align:center;font-size:.8rem;color:#CBD5E1'>{row['w']}</span>"
            f"<span style='text-align:center;font-size:.8rem;color:#CBD5E1'>{row['d']}</span>"
            f"<span style='text-align:center;font-size:.8rem;color:#CBD5E1'>{row['l']}</span>"
            f"<span style='text-align:center;font-size:.8rem;color:#CBD5E1'>{row['gf']}</span>"
            f"<span style='text-align:center;font-size:.8rem;color:#CBD5E1'>{row['ga']}</span>"
            f"<span style='text-align:right;font-size:.95rem;font-weight:900;color:{accent}'>{row['pts']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ── Page ──────────────────────────────────────────────────────────────────────

st.markdown("## 📊 Group Stage Standings")
st.caption("Updated from scores entered in Admin. Top 2 advance; best 8 third-place teams also advance.")

matches, teams = _load_data()
standings = _compute_standings(matches, teams)

# Summary bar
total_played = len(matches)
total_matches = 72
pct = int(total_played / total_matches * 100)
complete_groups = sum(
    1 for g, df in standings.items()
    if _group_matches_played(matches, teams, g) == 6
)

m1, m2, m3 = st.columns(3)
m1.metric("Matches Played", f"{total_played} / 72")
m2.metric("Groups Complete", f"{complete_groups} / 12")
m3.metric("Tournament Progress", f"{pct}%")

st.progress(pct / 100)
st.divider()

# Legend
st.markdown(
    "<div style='display:flex;gap:1.2rem;flex-wrap:wrap;margin-bottom:.8rem'>"
    "<span><span style='display:inline-block;width:.7rem;height:.7rem;"
    "background:rgba(16,185,129,.35);border-radius:2px;margin-right:.3rem'></span>"
    "<span style='font-size:.82rem;color:#94A3B8'>Top 2 — Advancing to Round of 32</span></span>"
    "<span><span style='display:inline-block;width:.7rem;height:.7rem;"
    "background:rgba(251,191,36,.3);border-radius:2px;margin-right:.3rem'></span>"
    "<span style='font-size:.82rem;color:#94A3B8'>3rd place — Best 8 also advance</span></span>"
    "</div>",
    unsafe_allow_html=True,
)

# Groups grid — 3 columns
groups = list(standings.keys())  # A–L
rows_of_3 = [groups[i:i+3] for i in range(0, len(groups), 3)]

for row_groups in rows_of_3:
    cols = st.columns(len(row_groups), gap="medium")
    for col, g in zip(cols, row_groups):
        with col:
            with st.container(border=True):
                played = _group_matches_played(matches, teams, g)
                _render_group_card(g, standings[g], played)

st.divider()
st.caption("⚽ Standings use standard FIFA tiebreakers: Points → Goal Difference → Goals For → Team name")
