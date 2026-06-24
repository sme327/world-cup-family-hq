import streamlit as st
import pandas as pd
from services.database import get_connection
from services.scoring import classify_group_statuses

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
        return "🎯", "Best 3rd Place 🏅", True
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


def _group_summary(rows: list[dict]) -> str:
    """One-sentence narrative for the top of a group card."""
    if not any(r['p'] > 0 for r in rows):
        return "⏳ Group stage hasn't started yet."

    locked1    = [r['team'] for r in rows if r['status'] == '🔒 Locked 1st']
    locked2    = [r['team'] for r in rows if r['status'] == '🔒 Locked 2nd']
    adv        = [r['team'] for r in rows if r['status'] == '✅ Advanced']
    good       = [r['team'] for r in rows if r['status'] == '🟢 In good shape']
    alive      = [r['team'] for r in rows if r['status'] == '🟡 Still alive']
    third      = [r['team'] for r in rows if r['status'] == '🟡 3rd place']
    needs      = [r['team'] for r in rows if r['status'] == '🟠 Needs help']
    elim       = [r['team'] for r in rows if r['status'] == '❌ Eliminated']

    # Wide-open shortcut — nothing decided yet
    if not locked1 and not locked2 and not adv and not elim and not third:
        if len(alive) + len(good) == 4:
            return "🌍 Wide open — all four teams are still fighting!"

    parts = []
    for t in locked1:
        parts.append(f"🔒 {t} has locked 1st place.")
    for t in locked2:
        parts.append(f"🔒 {t} has locked 2nd place.")
    if len(adv) == 2:
        parts.append(f"✅ {adv[0]} and {adv[1]} have advanced.")
    elif len(adv) == 1:
        parts.append(f"✅ {adv[0]} is through.")
    if good and not (locked1 or locked2 or adv):
        if len(good) == 2:
            parts.append(f"🟢 {good[0]} and {good[1]} are in good shape.")
        else:
            parts.append(f"🟢 {good[0]} is in good shape.")
    if len(alive) == 2:
        parts.append(f"🟡 {alive[0]} and {alive[1]} are still alive.")
    elif len(alive) == 1:
        parts.append(f"🟡 {alive[0]} is still alive.")
    for t in third:
        parts.append(f"🟡 {t} finished 3rd — still alive, competing for a best 3rd-place spot.")
    if needs:
        n = " and ".join(needs)
        verb = "need" if len(needs) > 1 else "needs"
        parts.append(f"🟠 {n} {verb} a miracle.")
    if len(elim) == 2:
        parts.append(f"❌ {elim[0]} and {elim[1]} have been eliminated.")
    elif len(elim) == 1:
        parts.append(f"❌ {elim[0]} has been eliminated.")

    return " ".join(parts) if parts else "📊 Group stage in progress."


def _render_group_card(group: str, rows: list[dict], played: int):
    # Header with progress badge
    badge = (
        "<span style='background:#4ADE80;color:#0F172A;border-radius:5px;"
        "padding:.06rem .38rem;font-size:.65rem;font-weight:800;margin-left:.45rem'>FINAL</span>"
        if played == 6 else
        f"<span style='background:rgba(251,191,36,.22);color:#FCD34D;border-radius:5px;"
        f"padding:.06rem .38rem;font-size:.65rem;font-weight:700;margin-left:.45rem'>{played}/6</span>"
    )
    st.markdown(
        f"<div style='font-size:1.05rem;font-weight:900;letter-spacing:.06em;"
        f"color:#F8FAFC;margin-bottom:.3rem'>GROUP {group}{badge}</div>",
        unsafe_allow_html=True,
    )

    # Summary sentence
    summary = _group_summary(rows)
    st.markdown(
        f"<div style='font-size:.73rem;color:#CBD5E1;margin-bottom:.5rem;"
        f"padding:.28rem .4rem;background:rgba(255,255,255,.04);"
        f"border-radius:6px;border-left:2px solid rgba(148,163,184,.25)'>"
        f"{summary}</div>",
        unsafe_allow_html=True,
    )

    # Column header
    st.markdown(
        "<div style='display:grid;"
        "grid-template-columns:1.2rem 1fr 2.2rem 4.2rem 1.8rem 5.2rem;"
        "gap:.08rem;font-size:.58rem;font-weight:700;color:#64748B;"
        "text-transform:uppercase;letter-spacing:.04em;"
        "padding:.15rem .35rem;border-bottom:1px solid rgba(148,163,184,.15)'>"
        "<span></span><span>Team</span>"
        "<span style='text-align:center'>Pts</span>"
        "<span style='text-align:center'>W-D-L</span>"
        "<span style='text-align:center'>GD</span>"
        "<span style='text-align:right'>Status</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    for i, r in enumerate(rows):
        bg, accent    = _POS_STYLE.get(i, ("", "#F8FAFC"))
        gd_val        = int(r['gd'])
        gd_str        = f"+{gd_val}" if gd_val > 0 else str(gd_val)
        record        = f"{r['w']}-{r['d']}-{r['l']}"
        status_lbl    = r.get('status', '')
        status_color  = r.get('status_color', '#94A3B8')
        # Hex alpha: append 20 (≈ 12 % opacity) for pill background
        status_bg     = status_color + "22"

        st.markdown(
            f"<div style='display:grid;"
            f"grid-template-columns:1.2rem 1fr 2.2rem 4.2rem 1.8rem 5.2rem;"
            f"gap:.08rem;align-items:center;padding:.3rem .35rem;"
            f"background:{bg};border-radius:6px;margin:.07rem 0'>"

            f"<span style='font-size:.7rem;color:{accent};font-weight:700;"
            f"text-align:center'>{i+1}</span>"

            f"<span style='font-size:.88rem;white-space:nowrap;overflow:hidden;"
            f"text-overflow:ellipsis'>"
            f"<span style='font-size:1.05rem'>{r['flag']}</span> "
            f"<span style='font-weight:600;color:#F1F5F9'>{r['team']}</span></span>"

            f"<span style='text-align:center;font-size:.92rem;font-weight:900;"
            f"color:{accent}'>{r['pts']}</span>"

            f"<span style='text-align:center;font-size:.72rem;color:#CBD5E1;"
            f"letter-spacing:.01em'>{record}</span>"

            f"<span style='text-align:center;font-size:.72rem;color:#94A3B8'>{gd_str}</span>"

            f"<span style='text-align:right'>"
            f"<span style='font-size:.58rem;font-weight:700;color:{status_color};"
            f"background:{status_bg};border-radius:4px;padding:.07rem .28rem;"
            f"white-space:nowrap;display:inline-block'>{status_lbl}</span>"
            f"</span>"

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

# Group stage complete banner
if complete_groups >= 12:
    st.markdown(
        "<div style='background:linear-gradient(135deg,#052e16,#166534);"
        "border:2px solid #4ADE80;border-radius:14px;"
        "padding:1rem 1.3rem;margin:.8rem 0;text-align:center'>"
        "<div style='font-size:1.5rem;font-weight:900;color:#4ADE80'>✅ Group Stage Complete</div>"
        "<div style='font-size:1rem;color:#D1FAE5;margin-top:.3rem'>"
        "All 12 groups are done — the Round of 32 is set below.</div>"
        "</div>",
        unsafe_allow_html=True,
    )

# Legend
st.markdown(
    "<div style='display:flex;gap:.9rem;flex-wrap:wrap;margin:.6rem 0 .8rem;align-items:center'>"
    # Row background legend
    "<span><span style='display:inline-block;width:.65rem;height:.65rem;"
    "background:rgba(16,185,129,.4);border-radius:2px;margin-right:.3rem'></span>"
    "<span style='font-size:.78rem;color:#94A3B8'>Top 2 row</span></span>"
    "<span><span style='display:inline-block;width:.65rem;height:.65rem;"
    "background:rgba(251,191,36,.35);border-radius:2px;margin-right:.3rem'></span>"
    "<span style='font-size:.78rem;color:#94A3B8'>3rd row</span></span>"
    "<span style='color:#334155'>|</span>"
    # Status pill legend
    "<span style='font-size:.7rem;font-weight:700;color:#4ADE80;"
    "background:#4ADE8022;border-radius:4px;padding:.06rem .28rem'>✅ Advanced</span>"
    "<span style='font-size:.7rem;font-weight:700;color:#4ADE80;"
    "background:#4ADE8022;border-radius:4px;padding:.06rem .28rem'>🔒 Locked</span>"
    "<span style='font-size:.7rem;font-weight:700;color:#86EFAC;"
    "background:#86EFAC22;border-radius:4px;padding:.06rem .28rem'>🟢 Good shape</span>"
    "<span style='font-size:.7rem;font-weight:700;color:#FCD34D;"
    "background:#FCD34D22;border-radius:4px;padding:.06rem .28rem'>🟡 Alive</span>"
    "<span style='font-size:.7rem;font-weight:700;color:#FB923C;"
    "background:#FB923C22;border-radius:4px;padding:.06rem .28rem'>🟠 Needs help</span>"
    "<span style='font-size:.7rem;font-weight:700;color:#F87171;"
    "background:#F8717122;border-radius:4px;padding:.06rem .28rem'>❌ Out</span>"
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
                # Convert DataFrame → list of dicts and add status labels
                group_rows = standings[g].to_dict('records')
                classify_group_statuses(group_rows)
                _render_group_card(g, group_rows, played)

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
        "🟡 Best 3rd-place finishers — top 8 advance (in pts order)</div>"
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
