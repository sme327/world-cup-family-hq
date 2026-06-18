import streamlit as st
from datetime import date
import pandas as pd
from services.teams import get_all_teams
from services.matches import get_all_matches
from services.passport import (
    get_discoveries, get_cheered_for, get_won_with, get_family_top_favorites,
    get_continent_progress,
)
from services.map_utils import build_atlas_figure, get_iso3_maps, HOST_CITIES

# ── Active user ───────────────────────────────────────────────────────────────
active_user_id = st.session_state.get("active_user_id", 1)
active_name    = st.session_state.get("active_user_name", "Shawn")
avatar         = st.session_state.get("active_user_avatar", "🐘")

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def _load_base():
    return get_all_teams(), get_all_matches()

teams_df, matches_df = _load_base()
iso3_to_name, _      = get_iso3_maps(teams_df)
all_countries        = sorted(teams_df["name"].tolist())

# Today's matches (PT date: subtract 7h from UTC)
from datetime import datetime as _dt, timezone as _tz, timedelta as _td
_today_str = (_dt.now(_tz.utc) - _td(hours=7)).date().isoformat()
_today_df  = matches_df[matches_df["match_date"] == _today_str]
today_countries = set(
    _today_df["home_team"].tolist() + _today_df["away_team"].tolist()
)

# Per-user passport data
disc_df     = get_discoveries(active_user_id)
discoveries = set(disc_df["country_name"].tolist()) if not disc_df.empty else set()
cheered     = set(get_cheered_for(active_user_id))
won         = set(get_won_with(active_user_id))
family_favs = get_family_top_favorites(n=5)

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    "<div style='display:flex;align-items:center;gap:.8rem;margin-bottom:.4rem'>"
    "<span style='font-size:3rem;line-height:1'>🌎</span>"
    "<div>"
    "<div style='font-size:1.9rem;font-weight:900;color:#F8FAFC;line-height:1.1'>World Atlas</div>"
    "<div style='font-size:.92rem;color:#64748B'>Click any country to explore it · 48 World Cup nations</div>"
    "</div></div>",
    unsafe_allow_html=True,
)

# Quick stats strip
_n_disc = len(discoveries)
_n_cheer = len(cheered)
_n_won = len(won)
st.markdown(
    f"<div style='display:flex;gap:1.4rem;flex-wrap:wrap;margin:.2rem 0 .7rem;"
    f"font-size:.83rem;color:#94A3B8'>"
    f"<span>🗺️ {avatar} {active_name}: "
    f"<b style='color:#0F766E'>{_n_disc} discovered</b> · "
    f"<b style='color:#2563EB'>{_n_cheer} cheered</b> · "
    f"<b style='color:#10B981'>{_n_won} won with</b></span>"
    f"<span>⭐ Family favs: "
    + " ".join(
        f"{teams_df.loc[teams_df['name']==n,'flag_emoji'].values[0] if not teams_df.loc[teams_df['name']==n,'flag_emoji'].empty else '🏳️'} {n}"
        for n in family_favs[:3]
    ) +
    f"</span></div>",
    unsafe_allow_html=True,
)

# ── Layer tabs ────────────────────────────────────────────────────────────────
_LAYERS = [
    ("today",    f"⚡ Today's Matches"),
    ("passport", f"🛂 {active_name}'s Passport"),
    ("all",      "🌍 All 48 Countries"),
    ("favorites","⭐ Family Favorites"),
]

tabs = st.tabs([label for _, label in _LAYERS])

for tab, (layer, _) in zip(tabs, _LAYERS):
    with tab:
        # ── Build + show figure ───────────────────────────────────────────────
        fig = build_atlas_figure(
            layer=layer,
            teams_df=teams_df,
            discoveries=discoveries,
            cheered=cheered,
            won=won,
            family_favs=family_favs,
            today_countries=today_countries,
            height=520,
        )

        event = st.plotly_chart(
            fig,
            on_select="rerun",
            use_container_width=True,
            key=f"atlas_{layer}",
        )

        # ── Handle country click ──────────────────────────────────────────────
        if event and event.selection and event.selection.points:
            pt = event.selection.points[0]
            iso3 = pt.get("location")
            if iso3:
                team = iso3_to_name.get(iso3)
                if team:
                    st.session_state["_nav_country"] = team
                    st.switch_page("pages/country_profile.py")

        # ── Layer legend ──────────────────────────────────────────────────────
        if layer == "today":
            _playing = [
                f"{teams_df.loc[teams_df['name']==n,'flag_emoji'].values[0] if not teams_df.loc[teams_df['name']==n,'flag_emoji'].empty else '🏳️'} {n}"
                for n in sorted(today_countries)
            ]
            if _playing:
                st.markdown(
                    "<div style='display:flex;flex-wrap:wrap;gap:.5rem;margin:.4rem 0'>"
                    "<span style='font-size:.75rem;font-weight:700;color:#F59E0B;"
                    "text-transform:uppercase;letter-spacing:.05em;align-self:center'>⚡ Playing today:</span>"
                    + "".join(
                        f"<span style='background:rgba(245,158,11,.15);border:1px solid rgba(245,158,11,.3);"
                        f"border-radius:20px;padding:.15rem .6rem;font-size:.82rem'>{c}</span>"
                        for c in _playing
                    ) +
                    "</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("No matches scheduled today.")

        elif layer == "passport":
            _legend_items = [
                ("#10B981", "Won with",    f"{_n_won} countries"),
                ("#2563EB", "Cheered for", f"{_n_cheer} countries"),
                ("#0F766E", "Discovered",  f"{_n_disc} countries"),
                ("#1A2A3D", "Not yet",     f"{48 - _n_disc} remaining"),
            ]
            st.markdown(
                "<div style='display:flex;gap:1.2rem;flex-wrap:wrap;margin:.4rem 0'>"
                + "".join(
                    f"<span style='display:flex;align-items:center;gap:.35rem'>"
                    f"<span style='display:inline-block;width:.7rem;height:.7rem;"
                    f"background:{c};border-radius:2px;flex-shrink:0'></span>"
                    f"<span style='font-size:.82rem;color:#94A3B8'>{lbl}: <b style='color:#CBD5E1'>{val}</b></span>"
                    f"</span>"
                    for c, lbl, val in _legend_items
                ) +
                "</div>",
                unsafe_allow_html=True,
            )
            # Continent progress bars
            cont_prog = get_continent_progress(active_user_id)
            if cont_prog:
                st.markdown(
                    "<div style='display:flex;flex-wrap:wrap;gap:.5rem;margin:.3rem 0'>",
                    unsafe_allow_html=True,
                )
                cols = st.columns(len(cont_prog))
                for col, (continent, data) in zip(cols, cont_prog.items()):
                    disc_c = data.get("discovered", 0)
                    total_c = data.get("total", 1)
                    pct = int(disc_c / total_c * 100)
                    col.markdown(
                        f"<div style='font-size:.72rem;color:#94A3B8;text-align:center'>"
                        f"<b style='color:#CBD5E1'>{continent}</b><br>"
                        f"{disc_c}/{total_c}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    col.progress(pct / 100)

        elif layer == "favorites":
            if family_favs:
                medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
                items = []
                for i, name in enumerate(family_favs[:5]):
                    flag_row = teams_df.loc[teams_df["name"] == name, "flag_emoji"]
                    flag = flag_row.values[0] if not flag_row.empty else "🏳️"
                    items.append(
                        f"<span style='background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.25);"
                        f"border-radius:20px;padding:.15rem .6rem;font-size:.85rem'>"
                        f"{medals[i]} {flag} {name}</span>"
                    )
                st.markdown(
                    "<div style='display:flex;flex-wrap:wrap;gap:.4rem;margin:.4rem 0'>"
                    + "".join(items) +
                    "</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("No family favorites yet — start picking and exploring to build them up!")

        else:  # "all"
            st.caption(
                "🔵 All 48 World Cup nations · 🔵 USA  🔴 Canada  🟢 Mexico host city pins"
            )

        # ── Host city pin legend ──────────────────────────────────────────────
        st.markdown(
            "<div style='display:flex;gap:1rem;flex-wrap:wrap;margin:.2rem 0 .4rem'>"
            "<span style='font-size:.75rem;color:#64748B;font-weight:600;text-transform:uppercase;"
            "letter-spacing:.04em;align-self:center'>📍 Host cities:</span>"
            "<span style='font-size:.78rem;color:#60A5FA'>● USA (11)</span>"
            "<span style='font-size:.78rem;color:#F87171'>● Canada (2)</span>"
            "<span style='font-size:.78rem;color:#34D399'>● Mexico (3)</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        # ── Quick navigate ────────────────────────────────────────────────────
        st.markdown("---")
        _nc1, _nc2 = st.columns([4, 1])
        with _nc1:
            _chosen = st.selectbox(
                "Or choose a country to explore:",
                ["— select a country —"] + all_countries,
                key=f"nav_sel_{layer}",
                label_visibility="collapsed",
            )
        with _nc2:
            if st.button("Explore →", key=f"nav_go_{layer}", use_container_width=True,
                         disabled=_chosen == "— select a country —"):
                st.session_state["_nav_country"] = _chosen
                st.switch_page("pages/country_profile.py")

        if _chosen != "— select a country —":
            _row = teams_df[teams_df["name"] == _chosen]
            if not _row.empty:
                _r = _row.iloc[0]
                disc_status = (
                    "🟢 Won with" if _chosen in won else
                    "🔵 Cheered for" if _chosen in cheered else
                    "🩵 Discovered" if _chosen in discoveries else
                    "⚪ Not yet explored"
                )
                st.markdown(
                    f"<div style='background:rgba(30,41,59,.6);border:1px solid rgba(99,102,241,.2);"
                    f"border-radius:12px;padding:.7rem 1.1rem;margin:.3rem 0;display:flex;"
                    f"align-items:center;gap:1rem'>"
                    f"<span style='font-size:3rem;line-height:1'>{_r['flag_emoji']}</span>"
                    f"<div>"
                    f"<div style='font-weight:800;font-size:1.05rem;color:#F1F5F9'>{_chosen}</div>"
                    f"<div style='font-size:.82rem;color:#94A3B8'>"
                    f"Group {_r['group_letter']} · {_r.get('confederation','?')} · {disc_status}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
