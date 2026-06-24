import streamlit as st
import pandas as pd
from services.images import get_country_image_html
from services.passport import (
    get_country_metadata, get_stamp,
    get_all_users_summary, get_family_continent_progress,
    get_family_top_favorites, get_family_stamp_statuses,
    get_family_country_card, get_discoveries, get_cheered_for, get_won_with,
    get_continent_progress, get_top_favorites,
)
from services.teams import get_flag
from services.picks import get_all_users
from services.scoring import get_leaderboard
from services.achievements import get_recent_achievement_unlocks, get_all_achievements
from services.explorer import (
    get_explorer_leaderboard,
    get_discovery_momentum,
    get_discovery_streak,
    get_weekly_explorer,
    get_continent_progress_all_users,
    get_badge_progress,
    MILESTONES,
)

CONTINENT_ORDER = ["North America", "South America", "Europe", "Africa", "Asia", "Oceania"]
CONTINENT_EMOJI = {
    "North America": "🌎", "South America": "🌎",
    "Europe": "🌍", "Africa": "🌍", "Asia": "🌏", "Oceania": "🌏",
}

st.markdown("""
<style>
[data-testid="stPopover"] > button {
    font-size: 2.4rem !important;
    min-height: 4rem !important;
    min-width: 4rem !important;
    border-radius: 10px !important;
    line-height: 1 !important;
    padding: .2rem !important;
}
.rank-card {
    border-radius: 16px; padding: 1.1rem;
    text-align: center; color: white;
}
.profile-card {
    background: linear-gradient(160deg,#1E293B,#0F172A);
    border-radius: 14px; padding: 1rem;
    border: 1px solid rgba(148,163,184,.15); color: white;
}
.milestone-row {
    display: flex; align-items: center; gap: .8rem;
    background: rgba(248,250,252,.05); border-radius: 10px;
    padding: .5rem .8rem; margin: .25rem 0;
    border: 1px solid rgba(255,255,255,.06);
}
</style>
""", unsafe_allow_html=True)


# ── Helpers (Family Passport) ─────────────────────────────────────────────────
def _explorer_rank(disc_count: int) -> tuple[str, str]:
    if disc_count == 48: return "🌍", "World Citizen"
    if disc_count >= 40: return "⭐", "Legend"
    if disc_count >= 30: return "🗺️", "Globe Trotter"
    if disc_count >= 20: return "✈️", "World Traveler"
    if disc_count >= 10: return "🧭", "Explorer"
    if disc_count >= 3:  return "🌱", "Scout"
    if disc_count >= 1:  return "🔍", "Rookie"
    return "🥚", "Just Starting"


def _country_hero_img(country: str, stamp: dict, height: str = "90px") -> str:
    img = get_country_image_html(country, height=height, border_radius='10px 10px 0 0')
    if img:
        return img
    return (
        f"<div style='height:{height};background:linear-gradient(135deg,#1E293B,#0F172A);"
        f"display:flex;align-items:center;justify-content:center;"
        f"font-size:2.5rem;border-radius:10px 10px 0 0'>{stamp['stamp_emoji']}</div>"
    )


def _continent_dots(disc: int, total: int) -> str:
    dots = []
    for i in range(total):
        c = "#2563EB" if i < disc else "rgba(255,255,255,.1)"
        dots.append(f"<span style='background:{c};width:11px;height:11px;border-radius:50%;display:inline-block;margin:.08rem'></span>")
    return "".join(dots)


def _family_popover(country, stamp_statuses):
    card  = get_family_country_card(country)
    stamp = card['stamp']
    flag  = get_flag(country)
    st.markdown(f"## {flag} {country}")
    st.markdown(f"**{stamp['stamp_emoji']} {stamp['stamp_label']}** · {stamp['continent']}")
    st.divider()
    if card['discoverers']:
        st.markdown(f"**✅ Discovered by:** {', '.join(card['discoverers'])}")
    else:
        st.caption("Not yet discovered by anyone.")
    if card['cheerleaders']:
        st.markdown(f"**⚽ Cheered by:** {', '.join(card['cheerleaders'])}")
    if card['winners']:
        st.markdown(f"**🏆 Won with:** {', '.join(card['winners'])}")
    from services.teams import get_team_by_name
    team = get_team_by_name(country)
    if team is not None:
        st.divider()
        st.caption(f"FIFA #{team.get('fifa_ranking','—')} · Coach: {team.get('coach','—')}")
    if st.button("🌍 Open Country Profile", key=f"fcp_{country}"):
        st.session_state["_nav_country"] = country
        st.switch_page("pages/country_profile.py")


def _safe_int(val, default: int = 0) -> int:
    try:
        if pd.isna(val):
            return default
    except (TypeError, ValueError):
        pass
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


# ── Helpers (Discovery Race) ──────────────────────────────────────────────────
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
meta    = get_country_metadata()
total   = len(meta)
users   = get_all_users()
board   = get_leaderboard()
summary = get_all_users_summary()
stamp_statuses = get_family_stamp_statuses()

family_disc  = sum(1 for s in stamp_statuses.values() if s['discovered'])
family_cheer = sum(1 for s in stamp_statuses.values() if s['cheered'])
family_won   = sum(1 for s in stamp_statuses.values() if s['won'])

ranking = board.merge(summary[['id','discovered_count','fav1']], on='id', how='left')
ranking = ranking[ranking['picks_only'] != 1].reset_index(drop=True)
ranking['discovered_count'] = ranking['discovered_count'].fillna(0).astype(int)

# Discovery Race data
active_uid     = st.session_state.get("active_user_id", 1)
explorer_board = get_explorer_leaderboard()
momentum       = get_discovery_momentum(days=7)
weekly         = get_weekly_explorer()
cont_map       = get_continent_progress_all_users()

_MILESTONE_LABELS = {
    5:  ("First Adventure", "🌱"),
    10: ("Double Digits",   "🌿"),
    20: ("Globetrotter",    "🌎"),
    30: ("World Explorer",  "🌍"),
    40: ("Almost There",    "🌟"),
    48: ("Complete! 🎉",    "👑"),
}

# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding:.4rem 0 .2rem'>
    <div style='font-size:1.9rem;font-weight:900;color:#F1F5F9'>👨‍👩‍👧‍👦 Family Passport</div>
    <div style='color:#64748B;font-size:.85rem'>FIFA World Cup 2026 · Shared Collection</div>
</div>
""", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────────────
tab_family, tab_race, tab_favs, tab_progress = st.tabs([
    "👨‍👩‍👧‍👦 Family View",
    "🌎 Discovery Race",
    "⭐ Favorites",
    "🗺️ Progress",
])

# ════════════════════════════════════════════════════════════════════════════
# FAMILY VIEW TAB
# ════════════════════════════════════════════════════════════════════════════
with tab_family:
    rank_bgs = [
        "linear-gradient(135deg,#78350F,#B45309)",
        "linear-gradient(135deg,#1E3A5F,#374151)",
        "linear-gradient(135deg,#7C2D12,#9A3412)",
        "linear-gradient(160deg,#1E293B,#0F172A)",
        "linear-gradient(160deg,#1E293B,#0F172A)",
    ]
    rank_medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

    st.markdown("### 🏆 Family Rankings")
    rank_cols = st.columns(len(ranking))
    for col, (_, row), medal, bg in zip(rank_cols, ranking.iterrows(), rank_medals, rank_bgs):
        disc  = _safe_int(row.get('discovered_count'))
        pts   = float(row['total_points'])
        color = row.get('theme_color', '#2563EB')
        re, rl = _explorer_rank(disc)
        with col:
            st.markdown(
                f"<div class='rank-card' style='background:{bg};border:2px solid {color}'>"
                f"<div style='font-size:.9rem;font-weight:900'>{medal}</div>"
                f"<div style='font-size:2.5rem;line-height:1;margin:.2rem 0'>{row['avatar']}</div>"
                f"<div style='font-size:1rem;font-weight:800'>{row['name']}</div>"
                f"<div style='font-size:.75rem;color:rgba(255,255,255,.65);margin:.2rem 0'>{re} {rl}</div>"
                f"<div style='font-size:.9rem;font-weight:800;color:#FCD34D'>{pts:.1f} pts</div>"
                f"<div style='font-size:.72rem;color:rgba(255,255,255,.55)'>🌍 {disc} countries</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.divider()
    st.markdown("### 🛂 Member Passports")
    prof_cols = st.columns(len(summary))
    for col, (_, row) in zip(prof_cols, summary.iterrows()):
        disc  = _safe_int(row.get('discovered_count'))
        cheer = _safe_int(row.get('cheered_count'))
        won_c = _safe_int(row.get('won_count'))
        fav1  = row.get('fav1')
        color = row.get('theme_color', '#2563EB')
        re, rl = _explorer_rank(disc)
        pct = disc / total

        fav_html = ""
        if fav1 and not (isinstance(fav1, float) and pd.isna(fav1)):
            fav_stamp = get_stamp(str(fav1))
            fav_flag  = get_flag(str(fav1))
            fav_html  = (
                f"<div style='margin-top:.5rem;border-top:1px solid rgba(255,255,255,.1);padding-top:.5rem'>"
                f"<div style='font-size:.65rem;color:#94A3B8'>❤️ Favorite</div>"
                f"<div style='font-size:1.5rem'>{fav_flag}</div>"
                f"<div style='font-size:.72rem;color:#CBD5E1'>{fav1}</div>"
                f"</div>"
            )

        bar = "█" * int(pct * 10) + "░" * (10 - int(pct * 10))
        with col:
            st.markdown(
                f"<div class='profile-card'>"
                f"<div style='font-size:2.5rem;line-height:1'>{row['avatar']}</div>"
                f"<div style='font-weight:800;font-size:.95rem;margin:.2rem 0'>{row['name']}</div>"
                f"<div style='font-size:.7rem;color:{color};font-weight:700'>{re} {rl}</div>"
                f"<div style='font-family:monospace;font-size:.65rem;color:{color};margin:.3rem 0'>{bar} {pct:.0%}</div>"
                f"<div style='font-size:.72rem;color:#94A3B8'>🌍 {disc} · ⚽ {cheer} · 🏆 {won_c}</div>"
                f"{fav_html}"
                f"</div>",
                unsafe_allow_html=True
            )

    st.divider()
    st.markdown("### 🎉 Recent Family Milestones")
    recent_ach = get_recent_achievement_unlocks(8)

    if recent_ach.empty:
        st.caption("No milestones yet — start exploring to write the family story!")
    else:
        for _, row in recent_ach.iterrows():
            emoji = row.get('ach_emoji', '🏅')
            name  = row.get('ach_name', '')
            ts    = str(row.get('unlocked_at', ''))[:10]
            st.markdown(
                f"<div class='milestone-row'>"
                f"<span style='font-size:2rem;flex-shrink:0'>{row['avatar']}</span>"
                f"<div><div style='font-weight:800;font-size:.9rem;color:#F1F5F9'>{row['name']}</div>"
                f"<div style='font-size:.85rem'>{emoji} {name}</div>"
                f"<div style='font-size:.72rem;color:#64748B'>{ts}</div></div>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.divider()
    with st.expander("📊 Full Family Stats", expanded=False):
        p1, p2, p3 = st.columns(3)
        p1.metric("🌍 Family Discovered",  f"{family_disc}/{total}")
        p2.metric("⚽ Family Cheered",     f"{family_cheer}/{total}")
        p3.metric("🏆 Family Won",        f"{family_won}/{total}")
        if st.button("📖 My Personal Passport"):
            st.switch_page("pages/passport_individual.py")

# ════════════════════════════════════════════════════════════════════════════
# DISCOVERY RACE TAB
# ════════════════════════════════════════════════════════════════════════════
with tab_race:
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
        f"<div style='padding:.4rem 0 .2rem'>"
        f"<div style='font-size:1.5rem;font-weight:900;letter-spacing:-.01em;color:#F1F5F9'>"
        f"🌎 Discovery Race</div>"
        f"<div style='font-size:.88rem;color:#94A3B8;margin-top:.15rem'>"
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

    # Explorer Leaderboard
    st.markdown(
        "<div style='font-size:1.1rem;font-weight:900;color:#F8FAFC;margin-bottom:.6rem'>"
        "🏅 Explorer Leaderboard</div>",
        unsafe_allow_html=True,
    )

    race_cols = st.columns(len(explorer_board), gap="small")
    for col, (pos, data) in zip(race_cols, enumerate(explorer_board, 1)):
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

        if pos == 1:
            bg = "linear-gradient(160deg,#3B1F0D,#78350F)"
            border = "2px solid #F59E0B"
            rank_color = "#FCD34D"
        elif pos == 2:
            bg = "linear-gradient(160deg,#0F2437,#1E3A5F)"
            border = "2px solid #60A5FA"
            rank_color = "#93C5FD"
        elif pos == 3:
            bg = "linear-gradient(160deg,#1C1917,#292524)"
            border = "2px solid #CD7F32"
            rank_color = "#D4A57A"
        else:
            bg         = "linear-gradient(160deg,#0F172A,#1E293B)"
            border     = "1px solid rgba(148,163,184,.2)"
            rank_color = "#94A3B8"

        active_ring = ";box-shadow:0 0 0 3px rgba(147,197,253,.5)" if is_active else ""
        streak_html = (
            f"<div style='font-size:.68rem;color:#FB923C;margin-top:.15rem'>🔥 {streak}-day streak</div>"
            if streak > 0 else ""
        )

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
                + bar_html + streak_html + "</div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # Discovery Momentum
    st.markdown(
        "<div style='font-size:1.1rem;font-weight:900;color:#F8FAFC;margin-bottom:.5rem'>"
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
                row_color = "#475569"; bar_w = "0%"; label = "No new discoveries this week"; icon = "💤"; c_text = ""
            else:
                max_count = max(x['count'] for x in momentum)
                pct_w     = int(m['count'] / max(max_count, 1) * 100)
                bar_w     = f"{pct_w}%"
                row_color = m['theme_color']
                icon      = "🌍"
                word      = "country" if m['count'] == 1 else "countries"
                label     = f"{m['count']} new {word}"
                flags     = " ".join(get_flag(c) for c in m['countries'][:3])
                c_text    = f"<span style='font-size:.82rem;opacity:.7'>{flags}</span>" if flags else ""

            st.markdown(
                f"<div style='display:flex;align-items:center;gap:.7rem;"
                f"padding:.35rem 0;border-bottom:1px solid rgba(148,163,184,.08)'>"
                f"<span style='font-size:1.6rem;flex-shrink:0'>{m['avatar']}</span>"
                f"<div style='min-width:5rem;font-size:.88rem;font-weight:700;color:#F1F5F9'>{m['name']}</div>"
                f"<div style='flex:1'>"
                f"<div style='display:flex;align-items:center;gap:.5rem'>"
                f"<div style='flex:1;background:rgba(255,255,255,.07);border-radius:6px;height:.6rem;overflow:hidden'>"
                f"<div style='width:{bar_w};background:{row_color};height:100%;border-radius:6px'></div></div>"
                f"<span style='font-size:.8rem;font-weight:800;color:{row_color};min-width:3.5rem'>{icon} {label[:20]}</span>"
                f"{c_text}"
                f"</div></div></div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # Continent Explorer
    st.markdown(
        "<div style='font-size:1.1rem;font-weight:900;color:#F8FAFC;margin-bottom:.6rem'>"
        "🗺️ Continent Explorer</div>",
        unsafe_allow_html=True,
    )

    ordered    = [c for c in CONTINENT_ORDER if c in cont_map]
    cont_pairs = [ordered[i:i+2] for i in range(0, len(ordered), 2)]

    for pair in cont_pairs:
        pair_cols = st.columns(len(pair), gap="medium")
        for col, cont in zip(pair_cols, pair):
            user_data   = cont_map.get(cont, {})
            cont_total  = next((v['total'] for v in user_data.values()), 0)
            c_emoji     = CONTINENT_EMOJI.get(cont, "🌍")
            sorted_users = sorted(user_data.values(), key=lambda x: -x['discovered'])

            with col:
                with st.container(border=True):
                    st.markdown(
                        f"<div style='font-size:.95rem;font-weight:900;color:#F8FAFC;margin-bottom:.4rem'>"
                        f"{c_emoji} {cont}</div>"
                        f"<div style='font-size:.68rem;color:#64748B;margin-bottom:.5rem'>{cont_total} teams</div>",
                        unsafe_allow_html=True,
                    )
                    for ud in sorted_users:
                        disc_n = ud['discovered']
                        pct    = disc_n / cont_total if cont_total > 0 else 0
                        tc     = ud['theme_color']
                        done   = disc_n == cont_total and cont_total > 0
                        label_extra = " ✅" if done else ""
                        st.markdown(
                            f"<div style='display:flex;align-items:center;gap:.4rem;margin:.18rem 0'>"
                            f"<span style='font-size:1.15rem;flex-shrink:0'>{ud['avatar']}</span>"
                            f"<div style='flex:1'>" + _pct_bar(pct, tc, ".38rem") + "</div>"
                            f"<span style='font-size:.7rem;font-weight:700;color:{tc};"
                            f"min-width:2.2rem;text-align:right'>{disc_n}/{cont_total}{label_extra}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

    st.divider()

    # Discovery Streaks
    st.markdown(
        "<div style='font-size:1.1rem;font-weight:900;color:#F8FAFC;margin-bottom:.5rem'>"
        "🔥 Discovery Streaks</div>",
        unsafe_allow_html=True,
    )

    streak_rows = [(d['user_id'], d['name'], d['avatar'], d['theme_color']) for d in explorer_board]
    streak_data = [(name, av, tc, get_discovery_streak(uid)) for uid, name, av, tc in streak_rows]
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
        for col, (name, av, tc, streak) in zip(streak_cols, streak_data):
            if streak == 0:
                fire = "💤"; slbl = "No streak"; sc = "#475569"; sbg = "rgba(71,85,105,.15)"
            elif streak >= 7:
                fire = "🔥🔥"; slbl = f"{streak} days"; sc = "#F97316"; sbg = "rgba(249,115,22,.15)"
            elif streak >= 3:
                fire = "🔥"; slbl = f"{streak} days"; sc = "#FB923C"; sbg = "rgba(251,146,60,.12)"
            else:
                fire = "🔥"; slbl = f"{streak} day{'s' if streak > 1 else ''}"; sc = "#FCD34D"; sbg = "rgba(252,211,77,.1)"

            with col:
                st.markdown(
                    f"<div style='background:{sbg};border:1px solid {sc}44;"
                    f"border-radius:12px;padding:.7rem;text-align:center'>"
                    f"<div style='font-size:2rem;line-height:1'>{av}</div>"
                    f"<div style='font-size:.78rem;font-weight:700;color:#F1F5F9;margin:.2rem 0'>{name}</div>"
                    f"<div style='font-size:1.4rem;line-height:1'>{fire}</div>"
                    f"<div style='font-size:.88rem;font-weight:900;color:{sc}'>{slbl}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.divider()

    # Country Collector Milestones
    st.markdown(
        "<div style='font-size:1.1rem;font-weight:900;color:#F8FAFC;margin-bottom:.6rem'>"
        "🏁 Country Collector Milestones</div>",
        unsafe_allow_html=True,
    )

    for data in explorer_board:
        disc  = data['discovered']
        color = data['theme_color']
        milestone_cells = []
        for m in MILESTONES:
            reached  = disc >= m
            lbl, emo = _MILESTONE_LABELS.get(m, (str(m), "🏁"))
            cell_bg  = f"{color}30" if reached else "rgba(255,255,255,.04)"
            cell_brd = color if reached else "rgba(148,163,184,.15)"
            txt_col  = "#F1F5F9" if reached else "#475569"
            milestone_cells.append(
                f"<div style='background:{cell_bg};border:1px solid {cell_brd};"
                f"border-radius:8px;padding:.35rem .4rem;text-align:center;flex:1;min-width:70px'>"
                f"<div style='font-size:.85rem'>{emo if reached else '○'}</div>"
                f"<div style='font-size:.62rem;font-weight:700;color:{txt_col}'>"
                f"{'✅' if reached else str(m)} {lbl}</div>"
                f"</div>"
            )
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:.5rem;margin:.35rem 0;flex-wrap:wrap'>"
            f"<span style='font-size:1.5rem;flex-shrink:0'>{data['avatar']}</span>"
            f"<span style='font-size:.85rem;font-weight:700;color:#F1F5F9;min-width:4.5rem;flex-shrink:0'>{data['name']}</span>"
            f"<div style='display:flex;gap:.3rem;flex:1;flex-wrap:wrap'>"
            + "".join(milestone_cells) + "</div></div>",
            unsafe_allow_html=True,
        )

    st.divider()
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

# ════════════════════════════════════════════════════════════════════════════
# FAVORITES TAB
# ════════════════════════════════════════════════════════════════════════════
with tab_favs:
    top5 = get_family_top_favorites(5)
    if top5:
        fav_cols = st.columns(min(len(top5), 5))
        medals   = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for i, country in enumerate(top5):
            stamp = get_stamp(country)
            flag  = get_flag(country)
            img_h = _country_hero_img(country, stamp, "90px")
            with fav_cols[i]:
                st.markdown(
                    f"<div style='background:white;border:2px solid #E2E8F0;border-radius:12px;"
                    f"overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.07)'>"
                    f"{img_h}"
                    f"<div style='padding:.5rem .6rem'>"
                    f"<div style='font-size:1.5rem;line-height:1'>{flag}</div>"
                    f"<div style='font-size:.85rem;font-weight:900;color:#0F172A'>{medals[i]} {country}</div>"
                    f"<div style='font-size:.7rem;color:#64748B'>{stamp['stamp_emoji']} {stamp['stamp_label']}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True
                )
                if st.button("🌍", key=f"ffav_{i}_{country}", use_container_width=True):
                    st.session_state["_nav_country"] = country
                    st.switch_page("pages/country_profile.py")
    else:
        st.info("No family favorites yet — start exploring countries to build your collection!")

# ════════════════════════════════════════════════════════════════════════════
# PROGRESS TAB
# ════════════════════════════════════════════════════════════════════════════
with tab_progress:
    st.markdown(
        f"<div style='font-size:.85rem;color:#94A3B8;margin-bottom:.5rem'>"
        f"🌍 {family_disc} discovered · ⚽ {family_cheer} cheered · 🏆 {family_won} won · "
        f"Total: {total} countries</div>",
        unsafe_allow_html=True
    )
    st.caption("Click any stamp to see which family members collected it.")

    for continent in CONTINENT_ORDER:
        continent_teams = [c for c, s in stamp_statuses.items()
                           if get_stamp(c)['continent'] == continent]
        if not continent_teams:
            continue
        disc_in = sum(1 for c in continent_teams if stamp_statuses[c]['discovered'])
        emoji   = CONTINENT_EMOJI.get(continent, "🌍")
        st.markdown(f"**{emoji} {continent}** — {disc_in}/{len(continent_teams)}")

        cols = st.columns(8)
        for idx, country in enumerate(continent_teams):
            stamp = get_stamp(country)
            flag  = get_flag(country)
            s     = stamp_statuses.get(country, {})
            is_d  = s.get('discovered', False)
            is_c  = s.get('cheered', False)
            is_w  = s.get('won', False)

            if is_w:   btn = f"🏆{flag}"
            elif is_c: btn = f"⚽{flag}"
            elif is_d: btn = flag
            else:      btn = stamp['stamp_emoji']

            with cols[idx % 8]:
                with st.popover(btn, use_container_width=True):
                    _family_popover(country, stamp_statuses)

    st.divider()
    st.markdown("### 🗺️ Continent Race")
    st.caption("How close is the family to completing each continent?")

    cont_prog_fam = get_family_continent_progress()
    cont_cols     = st.columns(3)
    sorted_conts  = sorted(
        CONTINENT_ORDER,
        key=lambda c: cont_prog_fam.get(c, {}).get('discovered', 0) / max(1, cont_prog_fam.get(c, {}).get('total', 1)),
        reverse=True
    )

    for i, continent in enumerate(sorted_conts):
        prog  = cont_prog_fam.get(continent, {})
        d, t  = prog.get('discovered', 0), prog.get('total', 0)
        emoji = CONTINENT_EMOJI.get(continent, "🌍")
        dots  = _continent_dots(d, t)
        pct   = d / t if t > 0 else 0
        complete = d == t and t > 0

        best_uid, best_count = None, 0
        for _, u in users.iterrows():
            uid     = int(u['id'])
            u_cont  = get_continent_progress(uid).get(continent, {})
            u_count = u_cont.get('discovered', 0)
            if u_count > best_count:
                best_count, best_uid = u_count, uid

        leader_html = ""
        if best_uid is not None and best_count > 0:
            leader_row  = users[users['id'] == best_uid].iloc[0]
            leader_html = f"<div style='font-size:.68rem;color:#94A3B8'>Leader: {leader_row['avatar']} {leader_row['name']} ({best_count})</div>"

        border = "2px solid #FCD34D" if complete else "1px solid rgba(148,163,184,.12)"
        badge  = "<div style='color:#FCD34D;font-size:.78rem;font-weight:800;margin-top:.3rem'>✨ COMPLETE!</div>" if complete else ""

        with cont_cols[i % 3]:
            st.markdown(
                f"<div style='background:linear-gradient(160deg,#1E293B,#0F172A);border-radius:12px;"
                f"padding:.8rem;border:{border};margin-bottom:.5rem'>"
                f"<div style='font-size:1rem;font-weight:800;color:#F1F5F9'>{emoji} {continent}</div>"
                f"<div style='font-size:.72rem;color:#94A3B8;margin:.15rem 0'>{d}/{t} · {pct:.0%}</div>"
                f"<div style='display:flex;flex-wrap:wrap;gap:.12rem;margin:.35rem 0'>{dots}</div>"
                f"{leader_html}{badge}"
                f"</div>",
                unsafe_allow_html=True
            )
