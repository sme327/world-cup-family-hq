import streamlit as st
import pandas as pd
from datetime import date
from services.passport import (
    get_country_metadata, get_stamp,
    get_discoveries, get_cheered_for, get_won_with,
    get_top_favorites, get_continent_progress,
    get_picks_per_country, get_points_per_country,
)
from services.achievements import (
    get_all_achievements, get_user_achievements, get_family_achievements,
    check_individual_achievements, check_family_achievements,
)
from services.teams import get_flag
from services.matches import get_all_matches
from services.images import get_country_image_html
from services.picks import get_all_picks
from services.scoring import get_leaderboard

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
    if is_disc:    badges.append("✅ Discovered")
    if is_cheered: badges.append("⚽ Cheered For")
    if is_won:     badges.append("🏆 Won With")
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


def _ach_card(ach, is_unlocked: bool, is_hidden: bool, unlocked_at: str = ""):
    emoji = str(ach.get('emoji', '🏅'))
    name  = str(ach.get('name', ''))
    desc  = str(ach.get('description', ''))

    if is_hidden and not is_unlocked:
        st.markdown(
            "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);"
            "border:2px solid rgba(148,163,184,.2);border-radius:12px;"
            "padding:.8rem 1rem;margin:.25rem 0;opacity:0.7'>"
            "<div style='display:flex;align-items:center;gap:.7rem'>"
            "<span style='font-size:1.8rem'>❓</span>"
            "<div><div style='font-size:.9rem;font-weight:800;color:#475569'>???</div>"
            "<div style='font-size:.78rem;color:#334155'>Hidden achievement — keep exploring!</div>"
            "</div></div></div>",
            unsafe_allow_html=True,
        )
    elif is_unlocked:
        date_str = str(unlocked_at)[:10] if unlocked_at else ""
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#78350F,#92400E);"
            f"border:2px solid #FCD34D;border-radius:14px;padding:.85rem 1.1rem;margin:.3rem 0;"
            f"box-shadow:0 2px 10px rgba(252,211,77,.2)'>"
            f"<div style='display:flex;align-items:center;gap:.8rem'>"
            f"<span style='font-size:2.4rem;line-height:1;flex-shrink:0'>{emoji}</span>"
            f"<div style='flex:1'>"
            f"<div style='font-size:.95rem;font-weight:900;color:#FEF3C7;line-height:1.2'>{name}</div>"
            f"<div style='font-size:.78rem;color:#FDE68A;margin:.2rem 0;line-height:1.35'>{desc}</div>"
            f"</div>"
            f"<div style='text-align:center;flex-shrink:0'>"
            f"<div style='font-size:.65rem;font-weight:800;color:#FCD34D;text-transform:uppercase;"
            f"letter-spacing:.07em'>UNLOCKED</div>"
            f"<div style='font-size:.65rem;color:#D97706;margin-top:.1rem'>✅ {date_str}</div>"
            f"</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='background:linear-gradient(160deg,#1E293B,#0F172A);"
            f"border:1px solid rgba(148,163,184,.12);border-radius:12px;"
            f"padding:.75rem 1rem;margin:.25rem 0;opacity:0.75'>"
            f"<div style='display:flex;align-items:center;gap:.7rem'>"
            f"<span style='font-size:2rem;filter:grayscale(100%)'>{emoji}</span>"
            f"<div>"
            f"<div style='font-size:.9rem;font-weight:800;color:#475569'>{name}</div>"
            f"<div style='font-size:.78rem;color:#334155'>{desc}</div>"
            f"</div></div></div>",
            unsafe_allow_html=True,
        )


# ── Active user ───────────────────────────────────────────────────────────────
active_user    = st.session_state.get("active_user_name",      "Shawn")
active_user_id = st.session_state.get("active_user_id",        1)
avatar         = st.session_state.get("active_user_avatar",    "🐘")
theme_color    = st.session_state.get("active_user_color",     "#F97316")
picks_only     = st.session_state.get("active_user_picks_only", False)

# ── Passport data ─────────────────────────────────────────────────────────────
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

# ── Achievement data ──────────────────────────────────────────────────────────
all_ach       = get_all_achievements()
user_ach      = get_user_achievements(active_user_id)
family_ach    = get_family_achievements()
unlocked_ids        = set(user_ach['achievement_id'].tolist()) if not user_ach.empty else set()
family_unlocked_ids = set(family_ach['achievement_id'].tolist()) if not family_ach.empty else set()
individual_ach  = all_ach[all_ach['scope'] == 'individual']
family_only_ach = all_ach[all_ach['scope'] == 'family']

n_discovered = disc_count
n_cheered    = len(cheered)
n_won        = len(won)
all_picks_df = get_all_picks()
user_picks   = all_picks_df[all_picks_df['user_id'] == active_user_id] if not all_picks_df.empty else pd.DataFrame()
n_picks      = len(user_picks)
board        = get_leaderboard()
user_row     = board[board['id'] == active_user_id]
n_points     = float(user_row['total_points'].iloc[0]) if not user_row.empty else 0.0

_METRIC = {
    'countries_discovered': n_discovered,
    'picks_made':           n_picks,
    'countries_cheered':    n_cheered,
    'countries_won':        n_won,
    'points_earned':        n_points,
}

# ── 1. HERO — Passport card ───────────────────────────────────────────────────
pct_collected = disc_count / total
bar_filled    = int(pct_collected * 30)
bar_empty     = 30 - bar_filled
progress_bar  = "█" * bar_filled + "░" * bar_empty

st.markdown(
    f"<div style='background:linear-gradient(135deg,{theme_color}33,{theme_color}11);"
    f"border:2px solid {theme_color};border-radius:16px;padding:1rem 1.4rem;text-align:center;margin-bottom:.6rem'>"
    f"<div style='font-size:3rem;line-height:1;margin-bottom:.25rem'>{avatar}</div>"
    f"<div style='font-size:1.4rem;font-weight:900;color:#F1F5F9'>{active_user}'s Passport</div>"
    f"<div style='font-size:.9rem;color:{theme_color};font-weight:700;margin:.2rem 0'>"
    f"{rank_emoji} {rank_label}</div>"
    f"<div style='font-size:.85rem;color:#94A3B8;margin:.3rem 0'>"
    f"Countries Collected: <b style='color:#F1F5F9;font-size:1rem'>{disc_count}</b> / {total}</div>"
    f"<div style='font-family:monospace;font-size:.72rem;color:{theme_color};letter-spacing:.05rem'>"
    f"{progress_bar} {pct_collected:.0%}</div>"
    f"</div>",
    unsafe_allow_html=True
)

# ── 2. TABS ───────────────────────────────────────────────────────────────────
tab_stamps, tab_ach, tab_favs = st.tabs(["🏷️ Stamps", "🏅 Achievements", "❤️ Favorites"])

# ════════════════════════════════════════════════════════════════════════════
# STAMPS TAB
# ════════════════════════════════════════════════════════════════════════════
with tab_stamps:
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

            if is_won_:    btn = f"🏆{flag}"
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

    undiscovered = [c for c in meta['country'].tolist() if c not in disc_set]
    if undiscovered:
        st.divider()
        st.markdown("### 🌟 Suggested Next Discoveries")
        st.caption("Countries you haven't explored yet — click to visit!")

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
            badge_html = (
                "<div style='font-size:.68rem;background:#DC2626;color:white;border-radius:4px;"
                "padding:.08rem .3rem;margin-top:.2rem;display:inline-block'>🔥 Playing Today</div>"
                if is_today_match else ""
            )
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

    st.divider()
    with st.expander("📊 Full Stats", expanded=False):
        s1, s2, s3 = st.columns(3)
        s1.metric("🌍 Discovered",  f"{disc_count}/{total}")
        s2.metric("⚽ Cheered For", f"{len(cheered)}/{total}")
        s3.metric("🏆 Won With",    f"{len(won)}/{total}")
        st.caption(f"Explorer Rank: {rank_emoji} {rank_label}")

# ════════════════════════════════════════════════════════════════════════════
# ACHIEVEMENTS TAB
# ════════════════════════════════════════════════════════════════════════════
with tab_ach:
    unlocked_count   = len(unlocked_ids)
    total_individual = len(individual_ach[individual_ach['hidden'] == False])

    st.markdown(
        f"<div style='text-align:center;padding:.5rem 0 .3rem'>"
        f"<div style='font-size:2rem;line-height:1'>{avatar} 🏅</div>"
        f"<div style='font-size:1.1rem;font-weight:800;color:#F1F5F9;margin:.2rem 0'>"
        f"{unlocked_count} of {total_individual} unlocked</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Recently Unlocked
    if not user_ach.empty:
        recent_ach = user_ach.sort_values('unlocked_at', ascending=False).head(3)
        st.markdown("### 🎉 Recently Unlocked")
        r_cols = st.columns(min(len(recent_ach), 3))
        for col, (_, ua) in zip(r_cols, recent_ach.iterrows()):
            aid  = str(ua['achievement_id'])
            arow = all_ach[all_ach['achievement_id'] == aid]
            if arow.empty:
                continue
            a        = arow.iloc[0]
            date_str = str(ua.get('unlocked_at', ''))[:10]
            with col:
                st.markdown(
                    f"<div style='background:linear-gradient(135deg,#78350F,#92400E);"
                    f"border:2px solid #FCD34D;border-radius:14px;padding:1rem;text-align:center'>"
                    f"<div style='font-size:2.4rem;line-height:1;margin-bottom:.3rem'>{a.get('emoji','🏅')}</div>"
                    f"<div style='font-size:.95rem;font-weight:900;color:#FEF3C7;line-height:1.2'>{a.get('name','')}</div>"
                    f"<div style='font-size:.76rem;color:#FDE68A;margin:.3rem 0;line-height:1.35'>{a.get('description','')}</div>"
                    f"<div style='font-size:.68rem;color:#D97706'>✅ {date_str}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        st.markdown("")

    # Closest to Unlocking
    _closest: list[tuple] = []
    for _, ach in individual_ach[individual_ach['hidden'] == False].iterrows():
        aid = str(ach['achievement_id'])
        if aid in unlocked_ids:
            continue
        rt  = str(ach.get('rule_type', ''))
        thr = ach.get('threshold')
        if rt in _METRIC and pd.notna(thr) and float(thr) > 0:
            current = _METRIC[rt]
            pct     = min(current / float(thr), 1.0)
            if pct > 0:
                _closest.append((pct, current, float(thr), ach))

    _closest.sort(key=lambda x: -x[0])

    if _closest:
        st.markdown("### 🎯 Closest to Unlocking")
        for pct, current, thr, ach in _closest[:5]:
            bar_pct = int(pct * 100)
            thr_int = int(thr)
            cur_int = int(current)
            st.markdown(
                f"<div style='background:linear-gradient(160deg,#1E293B,#0F172A);"
                f"border:1px solid rgba(148,163,184,.15);border-radius:12px;"
                f"padding:.7rem 1rem;margin:.3rem 0'>"
                f"<div style='display:flex;align-items:center;gap:.75rem;margin-bottom:.4rem'>"
                f"<span style='font-size:1.6rem;line-height:1'>{ach.get('emoji','🏅')}</span>"
                f"<div style='flex:1'>"
                f"<div style='font-size:.9rem;font-weight:800;color:#F1F5F9'>{ach.get('name','')}</div>"
                f"<div style='font-size:.74rem;color:#94A3B8'>{ach.get('description','')}</div>"
                f"</div>"
                f"<div style='font-size:.85rem;font-weight:800;color:#FCD34D;flex-shrink:0'>"
                f"{cur_int} / {thr_int}</div>"
                f"</div>"
                f"<div style='background:rgba(148,163,184,.15);border-radius:4px;height:6px'>"
                f"<div style='background:linear-gradient(90deg,#3B82F6,#8B5CF6);border-radius:4px;"
                f"height:6px;width:{bar_pct}%'></div></div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown("")

    # All achievements by category
    st.markdown("### 🗂️ All Achievements")
    categories  = sorted(individual_ach['category'].unique().tolist())
    tab_labels  = categories + ["👨‍👩‍👧‍👦 Family"]
    ach_tabs    = st.tabs(tab_labels)

    for ach_tab, cat in zip(ach_tabs[:-1], categories):
        with ach_tab:
            cat_ach = individual_ach[individual_ach['category'] == cat]
            visible = cat_ach[cat_ach['hidden'] == False]
            hidden  = cat_ach[cat_ach['hidden'] == True]

            unlocked_in_cat = [a for _, a in visible.iterrows() if str(a['achievement_id']) in unlocked_ids]
            locked_in_cat   = [a for _, a in visible.iterrows() if str(a['achievement_id']) not in unlocked_ids]

            if unlocked_in_cat:
                st.markdown("**🏆 Unlocked**")
                for ach in unlocked_in_cat:
                    aid = str(ach['achievement_id'])
                    row = user_ach[user_ach['achievement_id'] == aid]
                    ua  = row['unlocked_at'].iloc[0] if not row.empty else ""
                    _ach_card(ach, True, False, ua)

            if locked_in_cat:
                st.markdown("**🔓 Available**")
                for ach in locked_in_cat:
                    _ach_card(ach, False, False)

            if not hidden.empty:
                st.markdown("**🔒 Secret**")
                for _, ach in hidden.iterrows():
                    aid         = str(ach['achievement_id'])
                    is_unlocked = aid in unlocked_ids
                    row         = user_ach[user_ach['achievement_id'] == aid] if is_unlocked else pd.DataFrame()
                    ua          = row['unlocked_at'].iloc[0] if not row.empty else ""
                    _ach_card(ach, is_unlocked, not is_unlocked, ua)

    with ach_tabs[-1]:
        st.markdown("### 👨‍👩‍👧‍👦 Family Achievements")
        st.caption("These count when the whole family works together!")
        for _, ach in family_only_ach.iterrows():
            aid         = str(ach['achievement_id'])
            is_unlocked = aid in family_unlocked_ids
            row         = family_ach[family_ach['achievement_id'] == aid] if is_unlocked else pd.DataFrame()
            ua          = row['unlocked_at'].iloc[0] if not row.empty else ""
            _ach_card(ach, is_unlocked, False, ua)

    # Check for new achievements
    newly = check_individual_achievements(active_user_id)
    check_family_achievements()
    if newly:
        st.success(f"🎉 You just unlocked {len(newly)} new achievement(s)! Refresh to see them.")

# ════════════════════════════════════════════════════════════════════════════
# FAVORITES TAB
# ════════════════════════════════════════════════════════════════════════════
with tab_favs:
    if top_favs:
        fav_cols = st.columns(min(len(top_favs), 3))
        labels   = ["❤️ Favorite", "💛 #2 Favorite", "💙 #3 Favorite"]
        for i, country in enumerate(top_favs):
            stamp    = get_stamp(country)
            flag     = get_flag(country)
            img_html = _country_hero_img(country, stamp, "110px")
            picks    = picks_per.get(country, 0)
            pts      = points_per.get(country, 0.0)
            stats    = f"⚽ {picks} picks · 🏆 {pts:.1f} pts" if picks > 0 else "Newly discovered!"
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
        st.caption("Your top 3 countries will appear here based on how much you discover and cheer for them.")
