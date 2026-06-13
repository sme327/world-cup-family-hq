import streamlit as st
import pandas as pd
from datetime import date
from services.passport import (
    get_country_metadata, get_stamp,
    get_discoveries, get_cheered_for, get_won_with,
    get_top_favorites, get_continent_progress,
    get_picks_per_country, get_points_per_country,
)
from services.achievements import get_user_achievements, get_all_achievements
from services.teams import get_flag
from services.matches import get_all_matches
from services.images import get_country_image_html

CONTINENT_ORDER = ["North America", "South America", "Europe", "Africa", "Asia", "Oceania"]
CONTINENT_EMOJI = {
    "North America": "🌎", "South America": "🌎",
    "Europe": "🌍", "Africa": "🌍", "Asia": "🌏", "Oceania": "🌏",
}

# ── Larger stamps for passport pages ─────────────────────────────────────────
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
.achievement-badge {
    background: linear-gradient(135deg,#1E293B,#0F172A);
    border-radius: 12px; padding: .7rem .5rem; text-align: center;
    border: 2px solid #FCD34D;
    box-shadow: 0 0 10px rgba(252,211,77,.25);
}
.locked-badge {
    background: rgba(255,255,255,.03);
    border-radius: 12px; padding: .7rem .5rem; text-align: center;
    border: 2px solid rgba(255,255,255,.08); opacity:.45;
}
.continent-card {
    background: linear-gradient(160deg,#1E293B,#0F172A);
    border-radius: 14px; padding: .9rem 1rem;
    border: 1px solid rgba(148,163,184,.15);
}
.suggest-card {
    background: linear-gradient(135deg,#0F172A,#1E293B);
    border-radius: 12px; padding: .8rem; text-align: center;
    border: 1px solid rgba(96,165,250,.3); cursor: pointer;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _explorer_rank(disc_count: int, continent_prog: dict) -> tuple[str, str]:
    for continent in CONTINENT_ORDER:
        prog = continent_prog.get(continent, {})
        if prog.get('total', 0) > 2 and prog.get('discovered', 0) == prog.get('total', 0):
            return "🏆", f"{continent} Specialist"
    if disc_count == 48: return "🌍", "World Citizen"
    if disc_count >= 40: return "⭐", "Legend"
    if disc_count >= 30: return "🗺️", "Globe Trotter"
    if disc_count >= 20: return "✈️", "World Traveler"
    if disc_count >= 10: return "🧭", "Explorer"
    if disc_count >= 3:  return "🌱", "Scout"
    if disc_count >= 1:  return "🔍", "Rookie Explorer"
    return "🥚", "Just Starting"


def _country_hero_img(country: str, stamp: dict, height: str = "110px") -> str:
    img = get_country_image_html(country, height=height, border_radius='12px 12px 0 0')
    if img:
        return img
    return (
        f"<div style='height:{height};background:linear-gradient(135deg,#1E293B,#0F172A);"
        f"display:flex;align-items:center;justify-content:center;"
        f"font-size:3rem;border-radius:12px 12px 0 0'>{stamp['stamp_emoji']}</div>"
    )


def _continent_dots(disc: int, won: int, total: int) -> str:
    dots = []
    for i in range(total):
        if i < won:
            dots.append("<span style='background:#10B981;width:13px;height:13px;border-radius:50%;display:inline-block;margin:.1rem'></span>")
        elif i < disc:
            dots.append("<span style='background:#2563EB;width:13px;height:13px;border-radius:50%;display:inline-block;margin:.1rem'></span>")
        else:
            dots.append("<span style='background:rgba(255,255,255,.12);width:13px;height:13px;border-radius:50%;display:inline-block;margin:.1rem'></span>")
    return "".join(dots)


def _mini_card(country, stamp, flag, is_disc, is_cheered, is_won,
               is_fav, top_favs, disc_df, picks_per, points_per):
    st.markdown(f"## {flag} {country}")
    st.markdown(f"**{stamp['stamp_emoji']} {stamp['stamp_label']}** · {stamp['continent']}")
    st.divider()
    badges = []
    if is_disc:   badges.append("✅ Discovered")
    if is_cheered: badges.append("⚽ Cheered For")
    if is_won:    badges.append("🏆 Won With")
    if is_fav:
        rank = top_favs.index(country) + 1
        badges.append(f"⭐ #{rank} Favorite")
    if badges:
        st.markdown("  ".join(badges))
    if not disc_df.empty and country in disc_df['country_name'].values:
        row = disc_df[disc_df['country_name'] == country].iloc[0]
        st.caption(f"First visited: {str(row['first_visited_at'])[:10]} · {int(row['visit_count'])} visit(s)")
    picks = picks_per.get(country, 0)
    pts   = points_per.get(country, 0.0)
    if picks > 0:
        st.caption(f"Picks: {picks} · Points: {pts:.1f}")
    from services.teams import get_team_by_name
    team = get_team_by_name(country)
    if team is not None:
        st.divider()
        coach = team.get('coach', '—')
        rank_ = team.get('fifa_ranking', '—')
        best  = team.get('best_finish', '—')
        st.caption(f"Coach: {coach} · FIFA #{rank_} · Best: {best}")
    if st.button("🌍 Open Country Profile", key=f"cp_pp_{country}"):
        st.session_state["_nav_country"] = country
        st.switch_page("pages/country_profile.py")


# ── Active user from global selector ──────────────────────────────────────────
active_user    = st.session_state.get("active_user_name",      "Shawn")
active_user_id = st.session_state.get("active_user_id",        1)
avatar         = st.session_state.get("active_user_avatar",    "🐘")
theme_color    = st.session_state.get("active_user_color",     "#F97316")
picks_only     = st.session_state.get("active_user_picks_only", False)

# ── Load all data ─────────────────────────────────────────────────────────────
meta       = get_country_metadata()
total      = len(meta)
disc_df    = get_discoveries(active_user_id)
disc_set   = set(disc_df['country_name'].tolist()) if not disc_df.empty else set()
cheered    = set(get_cheered_for(active_user_id))
won        = set(get_won_with(active_user_id))
top_favs   = get_top_favorites(active_user_id, 3)
cont_prog  = get_continent_progress(active_user_id)
picks_per  = get_picks_per_country(active_user_id)
points_per = get_points_per_country(active_user_id)
disc_count = len(disc_set)

rank_emoji, rank_label = _explorer_rank(disc_count, cont_prog)

# ── 1. HERO — Passport card ───────────────────────────────────────────────────
pct_collected = disc_count / total
bar_filled    = int(pct_collected * 30)
bar_empty     = 30 - bar_filled
progress_bar  = "█" * bar_filled + "░" * bar_empty

st.markdown(
    f"<div style='background:linear-gradient(135deg,{theme_color}33,{theme_color}11);"
    f"border:2px solid {theme_color};border-radius:18px;padding:1.8rem;text-align:center;margin-bottom:1rem'>"
    f"<div style='font-size:4rem;line-height:1;margin-bottom:.4rem'>{avatar}</div>"
    f"<div style='font-size:1.8rem;font-weight:900;color:#F1F5F9'>{active_user}'s Passport</div>"
    f"<div style='font-size:1rem;color:{theme_color};font-weight:700;margin:.3rem 0'>"
    f"{rank_emoji} {rank_label}</div>"
    f"<div style='font-size:.88rem;color:#94A3B8;margin:.5rem 0'>"
    f"Countries Collected: <b style='color:#F1F5F9;font-size:1.1rem'>{disc_count}</b> / {total}</div>"
    f"<div style='font-family:monospace;font-size:.75rem;color:{theme_color};letter-spacing:.05rem'>"
    f"{progress_bar} {pct_collected:.0%}</div>"
    f"</div>",
    unsafe_allow_html=True
)

# ── 2. ACHIEVEMENT SHOWCASE ───────────────────────────────────────────────────
all_ach      = get_all_achievements()
user_ach_df  = get_user_achievements(active_user_id)
unlocked_ids = set(user_ach_df['achievement_id'].tolist()) if not user_ach_df.empty else set()

unlocked_ach = all_ach[
    (all_ach['achievement_id'].astype(str).isin(unlocked_ids)) &
    (all_ach['scope'] == 'individual')
].head(9)

if not unlocked_ach.empty:
    st.markdown("### 🏅 Earned Badges")
    badge_cols = st.columns(min(len(unlocked_ach), 6))
    for col, (_, ach) in zip(badge_cols, unlocked_ach.iterrows()):
        col.markdown(
            f"<div class='achievement-badge'>"
            f"<div style='font-size:1.8rem'>{ach['emoji']}</div>"
            f"<div style='font-size:.65rem;font-weight:700;color:#FCD34D;margin-top:.2rem;line-height:1.2'>{ach['name']}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    remaining = len(all_ach[all_ach['scope']=='individual']) - len(unlocked_ach)
    if remaining > 0:
        st.caption(f"🔒 {remaining} more badges to unlock. Keep exploring!")

# ── 3. FAVORITE COUNTRIES — Collectible cards ─────────────────────────────────
if top_favs:
    st.markdown("### ❤️ Favorite Countries")
    fav_cols = st.columns(min(len(top_favs), 3))
    labels = ["❤️ Favorite", "💛 #2 Favorite", "💙 #3 Favorite"]
    for i, country in enumerate(top_favs):
        stamp = get_stamp(country)
        flag  = get_flag(country)
        img_html = _country_hero_img(country, stamp, "110px")
        picks = picks_per.get(country, 0)
        pts   = points_per.get(country, 0.0)
        stats = f"⚽ {picks} picks · 🏆 {pts:.1f} pts" if picks > 0 else "Newly discovered!"
        with fav_cols[i]:
            st.markdown(
                f"<div style='background:white;border:2px solid #E2E8F0;border-radius:14px;"
                f"overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.07)'>"
                f"{img_html}"
                f"<div style='padding:.65rem .7rem'>"
                f"<div style='font-size:1.8rem;line-height:1'>{flag}</div>"
                f"<div style='font-size:.92rem;font-weight:900;color:#0F172A;margin:.15rem 0'>{country}</div>"
                f"<div style='font-size:.75rem;color:#64748B'>{stamp['stamp_emoji']} {stamp['stamp_label']}</div>"
                f"<div style='font-size:.72rem;color:#DC2626;font-weight:700;margin-top:.3rem'>{labels[i] if i < len(labels) else ''}</div>"
                f"<div style='font-size:.7rem;color:#94A3B8;margin-top:.1rem'>{stats}</div>"
                f"</div></div>",
                unsafe_allow_html=True
            )
            if st.button(f"🌍 Explore", key=f"fav_cp_{i}_{country}", use_container_width=True):
                st.session_state["_nav_country"] = country
                st.switch_page("pages/country_profile.py")
else:
    st.markdown("### ❤️ Favorite Countries")
    st.info("Visit Country Profiles and make picks to earn your favorites!")

# ── 4. STAMP COLLECTION — The centrepiece ────────────────────────────────────
st.divider()
st.markdown("### 🏷️ Stamp Collection")
st.caption(f"Collected: {disc_count}/{total} · Cheered: {len(cheered)}/{total} · Won: {len(won)}/{total}")

for continent in CONTINENT_ORDER:
    prog     = cont_prog.get(continent, {})
    teams_in = prog.get('teams', [])
    if not teams_in:
        continue
    emoji = CONTINENT_EMOJI.get(continent, "🌍")
    d, t = prog.get('discovered', 0), prog.get('total', len(teams_in))
    st.markdown(f"**{emoji} {continent}** — {d}/{t}")

    cols = st.columns(8)
    for idx, country in enumerate(teams_in):
        stamp    = get_stamp(country)
        flag     = get_flag(country)
        is_disc  = country in disc_set
        is_cheer = country in cheered
        is_won_  = country in won
        is_fav   = country in top_favs

        # Button label communicates state at a glance
        if is_won_:   btn = f"🏆{flag}"
        elif is_cheer: btn = f"⚽{flag}"
        elif is_disc:  btn = flag
        else:          btn = stamp['stamp_emoji']

        fav_star = "⭐" if is_fav else ""
        label    = f"{btn}{fav_star}"

        with cols[idx % 8]:
            with st.popover(label, use_container_width=True):
                _mini_card(
                    country, stamp, flag,
                    is_disc, is_cheer, is_won_, is_fav,
                    top_favs, disc_df, picks_per, points_per
                )

# ── 5. CONTINENT COLLECTION — Set completion ──────────────────────────────────
st.divider()
st.markdown("### 🗺️ Continent Collection")
st.caption("Fill a continent to become a specialist!")

cont_cols = st.columns(3)
for i, continent in enumerate(CONTINENT_ORDER):
    prog  = cont_prog.get(continent, {})
    d     = prog.get('discovered', 0)
    w     = prog.get('won', 0)
    t     = prog.get('total', 0)
    emoji = CONTINENT_EMOJI.get(continent, "🌍")
    dots  = _continent_dots(d, w, t)
    complete = d == t and t > 0

    badge = (
        "<div style='color:#FCD34D;font-size:.8rem;font-weight:800;margin-top:.4rem'>✨ COMPLETE! Specialist unlocked!</div>"
        if complete else
        f"<div style='font-size:.72rem;color:#64748B;margin-top:.4rem'>{t - d} more to collect</div>"
    )
    border = "2px solid #FCD34D" if complete else "1px solid rgba(148,163,184,.15)"

    with cont_cols[i % 3]:
        st.markdown(
            f"<div class='continent-card' style='border:{border}'>"
            f"<div style='font-size:1.1rem;font-weight:800;color:#F1F5F9'>{emoji} {continent}</div>"
            f"<div style='font-size:.75rem;color:#94A3B8;margin:.2rem 0'>{d}/{t} discovered · {w}/{t} won</div>"
            f"<div style='display:flex;flex-wrap:wrap;gap:.15rem;margin:.4rem 0'>{dots}</div>"
            f"{badge}</div>",
            unsafe_allow_html=True
        )

# ── 6. SUGGESTED NEXT DISCOVERIES ─────────────────────────────────────────────
undiscovered = [c for c in meta['country'].tolist() if c not in disc_set]
if undiscovered:
    st.divider()
    st.markdown("### 🌟 Suggested Next Discoveries")
    st.caption("Countries you haven't explored yet — click to visit!")

    # Prioritize teams playing today
    today_str   = date.today().isoformat()
    all_matches = get_all_matches()
    today_teams = set()
    if not all_matches.empty:
        today_m = all_matches[all_matches['match_date'] == today_str]
        today_teams = set(today_m['home_team'].tolist() + today_m['away_team'].tolist())

    priority   = [c for c in undiscovered if c in today_teams]
    rest       = [c for c in undiscovered if c not in today_teams]
    seed       = date.today().toordinal()
    rest_order = rest[seed % max(1, len(rest)):] + rest[:seed % max(1, len(rest))]
    suggestions = (priority + rest_order)[:3]

    sug_cols = st.columns(3)
    for col, country in zip(sug_cols, suggestions):
        stamp = get_stamp(country)
        flag  = get_flag(country)
        is_today_match = country in today_teams
        badge_html = "<div style='font-size:.68rem;background:#DC2626;color:white;border-radius:4px;padding:.08rem .3rem;margin-top:.2rem;display:inline-block'>🔥 Playing Today</div>" if is_today_match else ""
        with col:
            st.markdown(
                f"<div class='suggest-card'>"
                f"<div style='font-size:3rem;line-height:1'>{flag}</div>"
                f"<div style='font-size:.9rem;font-weight:800;color:#F1F5F9;margin:.3rem 0'>{country}</div>"
                f"<div style='font-size:.78rem;color:#64748B'>{stamp['stamp_emoji']} {stamp['stamp_label']}</div>"
                f"{badge_html}"
                f"</div>",
                unsafe_allow_html=True
            )
            if st.button(f"🌍 Discover", key=f"sug_{country}", use_container_width=True):
                st.session_state["_nav_country"] = country
                st.switch_page("pages/country_profile.py")

# ── 7. STATS (minimal, at bottom) ────────────────────────────────────────────
st.divider()
with st.expander("📊 Full Stats", expanded=False):
    s1, s2, s3 = st.columns(3)
    s1.metric("🌍 Discovered",  f"{disc_count}/{total}")
    s2.metric("⚽ Cheered For", f"{len(cheered)}/{total}")
    s3.metric("🏆 Won With",   f"{len(won)}/{total}")
    st.caption(f"Explorer Rank: {rank_emoji} {rank_label}")
