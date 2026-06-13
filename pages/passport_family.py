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

CONTINENT_ORDER = ["North America", "South America", "Europe", "Africa", "Asia", "Oceania"]
CONTINENT_EMOJI = {
    "North America": "🌎", "South America": "🌎",
    "Europe": "🌍", "Africa": "🌍", "Asia": "🌏", "Oceania": "🌏",
}

# ── Larger stamps ─────────────────────────────────────────────────────────────
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


# ── Helpers ───────────────────────────────────────────────────────────────────
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

# Merge board with summary for combined ranking
ranking = board.merge(summary[['id','discovered_count','fav1']], on='id', how='left')
ranking = ranking[ranking['picks_only'] != 1].reset_index(drop=True)
ranking['discovered_count'] = ranking['discovered_count'].fillna(0).astype(int)


def _safe_int(val, default: int = 0) -> int:
    """int(val) with fallback for NaN/None — guards against left-merge NaN."""
    try:
        if pd.isna(val):
            return default
    except (TypeError, ValueError):
        pass
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


# ── PAGE HEADER ───────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding:.4rem 0 .2rem'>
    <div style='font-size:1.9rem;font-weight:900;color:#F1F5F9'>👨‍👩‍👧‍👦 Family Passport</div>
    <div style='color:#64748B;font-size:.85rem'>FIFA World Cup 2026 · Shared Collection</div>
</div>
""", unsafe_allow_html=True)

# ── 1. FAMILY RANKINGS — Who's winning? ───────────────────────────────────────
st.markdown("### 🏆 Family Rankings")
rank_bgs = [
    "linear-gradient(135deg,#78350F,#B45309)",  # gold
    "linear-gradient(135deg,#1E3A5F,#374151)",  # silver
    "linear-gradient(135deg,#7C2D12,#9A3412)",  # bronze
    "linear-gradient(160deg,#1E293B,#0F172A)",  # 4th
    "linear-gradient(160deg,#1E293B,#0F172A)",  # 5th
]
rank_medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

rank_cols = st.columns(len(ranking))
for col, (_, row), medal, bg in zip(rank_cols, ranking.iterrows(), rank_medals, rank_bgs):
    uid   = int(row['id'])
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

# ── 2. FAMILY MEMBER PROFILE CARDS ───────────────────────────────────────────
st.divider()
st.markdown("### 🛂 Member Passports")

prof_cols = st.columns(len(summary))
for col, (_, row) in zip(prof_cols, summary.iterrows()):
    uid   = int(row['id'])
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

# ── 3. FAMILY STAMP WALL — The Panini album ───────────────────────────────────
st.divider()
st.markdown("### 🏷️ Family Stamp Wall")
st.markdown(
    f"<div style='font-size:.85rem;color:#94A3B8;margin-bottom:.5rem'>"
    f"🌍 {family_disc} discovered · ⚽ {family_cheer} cheered · 🏆 {family_won} won · "
    f"Total: {total} countries</div>",
    unsafe_allow_html=True
)
st.caption("Click any stamp to see which family members collected it.")

for continent in CONTINENT_ORDER:
    # Find teams in this continent
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

# ── 4. CONTINENT RACE ─────────────────────────────────────────────────────────
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

    # Leading explorer for this continent
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

# ── 5. FAMILY FAVORITES — with hero images ────────────────────────────────────
top5 = get_family_top_favorites(5)
if top5:
    st.divider()
    st.markdown("### ⭐ Family Favorites")
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

# ── 6. FAMILY MILESTONES ─────────────────────────────────────────────────────
st.divider()
st.markdown("### 🎉 Recent Family Milestones")
recent_ach = get_recent_achievement_unlocks(8)

if recent_ach.empty:
    st.caption("No milestones yet — start exploring to write the family story!")
else:
    all_ach    = get_all_achievements()
    ach_dict   = {str(r['achievement_id']): r for _, r in all_ach.iterrows()}
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

# ── Compact family stats ──────────────────────────────────────────────────────
st.divider()
with st.expander("📊 Full Family Stats", expanded=False):
    p1, p2, p3 = st.columns(3)
    p1.metric("🌍 Family Discovered",  f"{family_disc}/{total}")
    p2.metric("⚽ Family Cheered",     f"{family_cheer}/{total}")
    p3.metric("🏆 Family Won",        f"{family_won}/{total}")
    if st.button("📖 My Personal Passport"):
        st.switch_page("pages/passport_individual.py")
