import streamlit as st
from services.explorer import (
    get_explorer_leaderboard,
    get_discovery_momentum,
    get_discovery_streak,
    get_weekly_explorer,
    get_continent_progress_all_users,
    get_badge_progress,
    BADGES, CONTINENT_ORDER, CONTINENT_EMOJI, MILESTONES,
)
from services.teams import get_flag

# ── Helpers ───────────────────────────────────────────────────────────────────

def _pct_bar(pct: float, color: str, height: str = ".42rem") -> str:
    filled = max(0.0, min(1.0, pct))
    return (
        f"<div style='background:rgba(255,255,255,.1);border-radius:4px;"
        f"height:{height};overflow:hidden;margin:.15rem 0'>"
        f"<div style='width:{filled*100:.0f}%;background:{color};"
        f"height:100%;border-radius:4px;transition:width .4s'></div>"
        f"</div>"
    )


def _badge_color(title: str) -> str:
    return {
        "Scout":          "#94A3B8",
        "Explorer":       "#60A5FA",
        "World Traveler": "#34D399",
        "Globe Trotter":  "#F59E0B",
        "Master Explorer":"#A855F7",
    }.get(title, "#94A3B8")


def _rank_title(pos: int) -> str:
    return {1: "🥇 Lead Explorer", 2: "🥈 2nd", 3: "🥉 3rd"}.get(pos, f"#{pos}")


# ── Load data ─────────────────────────────────────────────────────────────────

board    = get_explorer_leaderboard()
momentum = get_discovery_momentum(days=7)
weekly   = get_weekly_explorer()
cont_map = get_continent_progress_all_users()

# ── Page header ───────────────────────────────────────────────────────────────

weekly_html = ""
if weekly and weekly['count'] > 0:
    c_word = "country" if weekly['count'] == 1 else "countries"
    weekly_html = (
        f"<div style='display:inline-flex;align-items:center;gap:.6rem;"
        f"background:linear-gradient(135deg,rgba(168,85,247,.18),rgba(99,102,241,.12));"
        f"border:1px solid rgba(168,85,247,.35);border-radius:12px;"
        f"padding:.45rem 1rem;margin-top:.5rem'>"
        f"<span style='font-size:1.6rem'>{weekly['avatar']}</span>"
        f"<div>"
        f"<div style='font-size:.65rem;font-weight:800;color:#A855F7;"
        f"text-transform:uppercase;letter-spacing:.07em'>Explorer of the Week</div>"
        f"<div style='font-size:.95rem;font-weight:900;color:#F1F5F9'>"
        f"{weekly['name']} — {weekly['count']} new {c_word} this week</div>"
        f"</div></div>"
    )

st.markdown(
    f"<div style='padding:.6rem 0 .4rem'>"
    f"<div style='font-size:2.2rem;font-weight:900;letter-spacing:-.01em;color:#F1F5F9'>"
    f"🌎 Discovery Race</div>"
    f"<div style='font-size:.95rem;color:#94A3B8;margin-top:.2rem'>"
    f"World Cup 2026 · Family Explorer Competition</div>"
    f"{weekly_html}"
    f"</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div style='background:rgba(99,102,241,.12);border-left:3px solid #818CF8;"
    "border-radius:0 10px 10px 0;padding:.55rem .9rem;margin:.3rem 0 .5rem;"
    "font-size:.88rem;color:#C7D2FE;line-height:1.5'>"
    "Explorer Score rewards <b>discovering countries</b>, <b>cheering for teams</b>, "
    "<b>winning with countries</b>, <b>earning achievements</b>, and <b>completing continents</b> — "
    "completely separate from the pick'em leaderboard."
    "</div>",
    unsafe_allow_html=True,
)
st.divider()

# ── Section 1: Explorer Leaderboard ──────────────────────────────────────────

st.markdown(
    "<div style='font-size:1.15rem;font-weight:900;color:#F8FAFC;margin-bottom:.6rem'>"
    "🏅 Explorer Leaderboard</div>",
    unsafe_allow_html=True,
)

active_uid = st.session_state.get("active_user_id", 1)

# Cards in a row (wrap naturally via Streamlit columns)
cols = st.columns(len(board), gap="small")
for col, (pos, data) in zip(cols, enumerate(board, 1)):
    uid       = data['user_id']
    score     = data['score']
    color     = data['theme_color']
    badge     = data['badge_title']
    b_emoji   = data['badge_emoji']
    b_color   = _badge_color(badge)
    bp        = get_badge_progress(score)
    is_active = uid == active_uid
    disc      = data['discovered']
    cheer     = data['cheered']
    won_c     = data['won']
    ach       = data['achievements']
    streak    = get_discovery_streak(uid)

    # Background gradient varies by rank
    if pos == 1:
        bg = "linear-gradient(160deg,#3B1F0D,#78350F)"
        border = f"2px solid #F59E0B"
        rank_color = "#FCD34D"
    elif pos == 2:
        bg = "linear-gradient(160deg,#0F2437,#1E3A5F)"
        border = f"2px solid #60A5FA"
        rank_color = "#93C5FD"
    elif pos == 3:
        bg = "linear-gradient(160deg,#1C1917,#292524)"
        border = f"2px solid #CD7F32"
        rank_color = "#D4A57A"
    else:
        bg     = "linear-gradient(160deg,#0F172A,#1E293B)"
        border = f"1px solid rgba(148,163,184,.2)"
        rank_color = "#94A3B8"

    active_ring = ";box-shadow:0 0 0 3px rgba(147,197,253,.5)" if is_active else ""

    streak_html = (
        f"<div style='font-size:.68rem;color:#FB923C;margin-top:.15rem'>🔥 {streak}-day streak</div>"
        if streak > 0 else ""
    )

    # Badge progress bar
    if bp['next_title']:
        bar_html = (
            _pct_bar(bp['progress'], b_color)
            + f"<div style='font-size:.58rem;color:#64748B;margin-top:.05rem'>"
            + f"{bp['pts_to_next']} pts to {bp['next_emoji']} {bp['next_title']}"
            + f"</div>"
        )
    else:
        bar_html = f"<div style='font-size:.62rem;color:{b_color}'>✨ Max rank achieved!</div>"

    with col:
        st.markdown(
            f"<div style='background:{bg};border:{border};"
            f"border-radius:16px;padding:1rem .85rem;text-align:center{active_ring}'>"

            f"<div style='font-size:3rem;line-height:1;margin-bottom:.3rem'>{data['avatar']}</div>"

            f"<div style='font-size:.65rem;font-weight:800;color:{rank_color};"
            f"letter-spacing:.06em;text-transform:uppercase'>{_rank_title(pos)}</div>"

            f"<div style='font-size:.78rem;font-weight:800;color:{b_color};"
            f"margin:.2rem 0 .05rem'>{b_emoji} {badge}</div>"

            f"<div style='font-size:2.4rem;font-weight:900;color:#F1F5F9;"
            f"line-height:1.05'>{score}</div>"
            f"<div style='font-size:.6rem;color:#64748B;text-transform:uppercase;"
            f"letter-spacing:.04em;margin-bottom:.3rem'>explorer pts</div>"

            f"<div style='font-size:.7rem;color:#CBD5E1;margin:.25rem 0;"
            f"display:flex;flex-direction:column;gap:.1rem;text-align:left'>"
            f"<span>🗺️ <b>{disc}</b>/48 discovered</span>"
            f"<span>📣 <b>{cheer}</b> cheered for</span>"
            f"<span>🏆 <b>{won_c}</b> won with</span>"
            f"<span>🏅 <b>{ach}</b> badges</span>"
            f"</div>"

            + bar_html
            + streak_html
            + "</div>",
            unsafe_allow_html=True,
        )

st.divider()

# ── Section 2: Discovery Momentum ────────────────────────────────────────────

st.markdown(
    "<div style='font-size:1.15rem;font-weight:900;color:#F8FAFC;margin-bottom:.5rem'>"
    "⚡ Discovery Momentum — Last 7 Days</div>",
    unsafe_allow_html=True,
)

has_any_momentum = any(m['count'] > 0 for m in momentum)

if not has_any_momentum:
    st.markdown(
        "<div style='font-size:.9rem;color:#64748B;padding:.5rem 0'>"
        "🌱 No new discoveries this week yet — open a country profile to get started!</div>",
        unsafe_allow_html=True,
    )
else:
    for m in momentum:
        if m['count'] == 0:
            row_color = "#475569"
            bar_w     = "0%"
            label     = "No new discoveries this week"
            icon      = "💤"
            c_text    = ""
        else:
            max_count = max(x['count'] for x in momentum)
            pct_w     = int(m['count'] / max(max_count, 1) * 100)
            bar_w     = f"{pct_w}%"
            row_color = m['theme_color']
            icon      = "🌍"
            word      = "country" if m['count'] == 1 else "countries"
            label     = f"{m['count']} new {word}"

            # show last 3 discovered flags
            flags = " ".join(get_flag(c) for c in m['countries'][:3])
            c_text = (
                f"<span style='font-size:.82rem;opacity:.7'>{flags}</span>"
                if flags else ""
            )

        st.markdown(
            f"<div style='display:flex;align-items:center;gap:.7rem;"
            f"padding:.35rem 0;border-bottom:1px solid rgba(148,163,184,.08)'>"
            f"<span style='font-size:1.6rem;flex-shrink:0'>{m['avatar']}</span>"
            f"<div style='min-width:5rem;font-size:.88rem;font-weight:700;color:#F1F5F9'>"
            f"{m['name']}</div>"
            f"<div style='flex:1'>"
            f"<div style='display:flex;align-items:center;gap:.5rem'>"
            f"<div style='flex:1;background:rgba(255,255,255,.07);border-radius:6px;"
            f"height:.6rem;overflow:hidden'>"
            f"<div style='width:{bar_w};background:{row_color};height:100%;border-radius:6px'></div>"
            f"</div>"
            f"<span style='font-size:.8rem;font-weight:800;color:{row_color};"
            f"min-width:3.5rem'>{icon} {label[:20]}</span>"
            f"{c_text}"
            f"</div></div></div>",
            unsafe_allow_html=True,
        )

st.divider()

# ── Section 3: Continent Explorer ────────────────────────────────────────────

st.markdown(
    "<div style='font-size:1.15rem;font-weight:900;color:#F8FAFC;margin-bottom:.6rem'>"
    "🗺️ Continent Explorer</div>",
    unsafe_allow_html=True,
)

# Two-column continent grid
cont_pairs = []
ordered    = [c for c in CONTINENT_ORDER if c in cont_map]
for i in range(0, len(ordered), 2):
    cont_pairs.append(ordered[i:i+2])

for pair in cont_pairs:
    pair_cols = st.columns(len(pair), gap="medium")
    for col, cont in zip(pair_cols, pair):
        user_data = cont_map.get(cont, {})
        total     = next((v['total'] for v in user_data.values()), 0)
        # Family total (any user discovered)
        fam_total = sum(1 for teams_data in user_data.values() for _ in range(0))  # computed below
        c_emoji   = CONTINENT_EMOJI.get(cont, "🌍")

        # Sort users by discovered count desc
        sorted_users = sorted(user_data.values(), key=lambda x: -x['discovered'])

        with col:
            with st.container(border=True):
                st.markdown(
                    f"<div style='font-size:.95rem;font-weight:900;color:#F8FAFC;"
                    f"margin-bottom:.4rem'>{c_emoji} {cont}</div>"
                    f"<div style='font-size:.68rem;color:#64748B;margin-bottom:.5rem'>"
                    f"{total} teams</div>",
                    unsafe_allow_html=True,
                )
                for ud in sorted_users:
                    disc_n  = ud['discovered']
                    pct     = disc_n / total if total > 0 else 0
                    tc      = ud['theme_color']
                    done    = disc_n == total and total > 0

                    label_extra = " ✅" if done else ""
                    st.markdown(
                        f"<div style='display:flex;align-items:center;gap:.4rem;"
                        f"margin:.18rem 0'>"
                        f"<span style='font-size:1.15rem;flex-shrink:0'>{ud['avatar']}</span>"
                        f"<div style='flex:1'>"
                        + _pct_bar(pct, tc, ".38rem") +
                        f"</div>"
                        f"<span style='font-size:.7rem;font-weight:700;color:{tc};"
                        f"min-width:2.2rem;text-align:right'>{disc_n}/{total}{label_extra}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

st.divider()

# ── Section 4: Discovery Streaks ─────────────────────────────────────────────

st.markdown(
    "<div style='font-size:1.15rem;font-weight:900;color:#F8FAFC;margin-bottom:.5rem'>"
    "🔥 Discovery Streaks</div>",
    unsafe_allow_html=True,
)

streak_rows = [(d['user_id'], d['name'], d['avatar'], d['theme_color'])
               for d in board]
streak_data = [(name, avatar, tc, get_discovery_streak(uid))
               for uid, name, avatar, tc in streak_rows]
streak_data.sort(key=lambda x: -x[3])

has_streaks = any(s > 0 for _, _, _, s in streak_data)
if not has_streaks:
    st.markdown(
        "<div style='font-size:.9rem;color:#64748B'>"
        "🌱 No active streaks yet — visit a country profile every day to build one!</div>",
        unsafe_allow_html=True,
    )
else:
    streak_cols = st.columns(len(streak_data), gap="small")
    for col, (name, avatar, tc, streak) in zip(streak_cols, streak_data):
        if streak == 0:
            fire = "💤"
            streak_label = "No streak"
            streak_color = "#475569"
            streak_bg    = "rgba(71,85,105,.15)"
        elif streak >= 7:
            fire = "🔥🔥"
            streak_label = f"{streak} days"
            streak_color = "#F97316"
            streak_bg    = "rgba(249,115,22,.15)"
        elif streak >= 3:
            fire = "🔥"
            streak_label = f"{streak} days"
            streak_color = "#FB923C"
            streak_bg    = "rgba(251,146,60,.12)"
        else:
            fire = "🔥"
            streak_label = f"{streak} day{'s' if streak > 1 else ''}"
            streak_color = "#FCD34D"
            streak_bg    = "rgba(252,211,77,.1)"

        with col:
            st.markdown(
                f"<div style='background:{streak_bg};border:1px solid {streak_color}44;"
                f"border-radius:12px;padding:.7rem;text-align:center'>"
                f"<div style='font-size:2rem;line-height:1'>{avatar}</div>"
                f"<div style='font-size:.78rem;font-weight:700;color:#F1F5F9;"
                f"margin:.2rem 0'>{name}</div>"
                f"<div style='font-size:1.4rem;line-height:1'>{fire}</div>"
                f"<div style='font-size:.88rem;font-weight:900;color:{streak_color}'>"
                f"{streak_label}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

st.divider()

# ── Section 5: Country Collector Milestones ───────────────────────────────────

st.markdown(
    "<div style='font-size:1.15rem;font-weight:900;color:#F8FAFC;margin-bottom:.6rem'>"
    "🏁 Country Collector Milestones</div>",
    unsafe_allow_html=True,
)

_MILESTONE_LABELS = {
    5:  ("First Adventure", "🌱"),
    10: ("Double Digits",   "🌿"),
    20: ("Globetrotter",    "🌎"),
    30: ("World Explorer",  "🌍"),
    40: ("Almost There",    "🌟"),
    48: ("Complete! 🎉",    "👑"),
}

for data in board:
    uid   = data['user_id']
    disc  = data['discovered']
    color = data['theme_color']

    milestone_cells = []
    for m in MILESTONES:
        reached = disc >= m
        lbl, emo = _MILESTONE_LABELS.get(m, (str(m), "🏁"))
        cell_bg  = f"{color}30" if reached else "rgba(255,255,255,.04)"
        cell_brd = color if reached else "rgba(148,163,184,.15)"
        txt_col  = "#F1F5F9" if reached else "#475569"
        check    = "✅" if reached else f"<span style='color:#475569'>{m}🌍</span>"
        milestone_cells.append(
            f"<div style='background:{cell_bg};border:1px solid {cell_brd};"
            f"border-radius:8px;padding:.35rem .4rem;text-align:center;flex:1;"
            f"min-width:70px'>"
            f"<div style='font-size:.85rem'>{emo if reached else '○'}</div>"
            f"<div style='font-size:.62rem;font-weight:700;color:{txt_col}'>"
            f"{'✅' if reached else str(m)} {lbl}</div>"
            f"</div>"
        )

    st.markdown(
        f"<div style='display:flex;align-items:center;gap:.5rem;margin:.35rem 0;flex-wrap:wrap'>"
        f"<span style='font-size:1.5rem;flex-shrink:0'>{data['avatar']}</span>"
        f"<span style='font-size:.85rem;font-weight:700;color:#F1F5F9;"
        f"min-width:4.5rem;flex-shrink:0'>{data['name']}</span>"
        f"<div style='display:flex;gap:.3rem;flex:1;flex-wrap:wrap'>"
        + "".join(milestone_cells) +
        f"</div></div>",
        unsafe_allow_html=True,
    )

st.divider()

# ── Section 6: How Explorer Score Works ──────────────────────────────────────

with st.expander("ℹ️ How Explorer Score Works"):
    st.markdown("""
**Explorer Score = the points you earn by exploring the World Cup.**

| Action | Points |
|--------|--------|
| 🗺️ Open a country profile (discover) | +1 |
| 📣 Make a pick for a country (cheer) | +2 |
| 🏆 Earn points with a pick (win/draw) | +3 |
| 🏅 Unlock an achievement | +3 |
| 🌍 Discover every country in a continent | +10 |

**Explorer Badges:**
| Score | Badge |
|-------|-------|
| 0–9   | 🗺️ Scout |
| 10–24 | 🧭 Explorer |
| 25–39 | ✈️ World Traveler |
| 40–59 | 🌍 Globe Trotter |
| 60+   | 👑 Master Explorer |

*The Discovery Race runs alongside the Pick Competition — two ways to win!*
""")
