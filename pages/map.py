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

        pass  # end of with tab block

# ── Country Browser (outside tabs — runs once after map) ─────────────────────
import os as _os, pandas as _pd

_meta_path = _os.path.join(_os.path.dirname(__file__), '..', 'data', 'country_metadata.csv')
try:
    _meta_df = _pd.read_csv(_meta_path)
except Exception:
    _meta_df = _pd.DataFrame()

_CONTINENT_ORDER = ['North America', 'South America', 'Europe', 'Africa', 'Asia', 'Oceania']
_CONTINENT_EMOJI = {
    'North America': '🗽', 'South America': '🌎', 'Europe': '🗼',
    'Africa': '🦁', 'Asia': '🗻', 'Oceania': '🥝',
}
_IDENTITY = {
    'Argentina':            'Tango & Messi',
    'Australia':            'Kangaroos & Opera',
    'Belgium':              'Waffles & Chocolate',
    'Bolivia':              "World's Highest Capital",
    'Bosnia and Herzegovina': 'Stari Most Bridge',
    'Brazil':               'Carnival & Samba',
    'Cameroon':             'Indomitable Lions',
    'Canada':               'Maple Syrup & Mountains',
    'Cape Verde':           'Atlantic Island Nation',
    'Chile':                'Atacama Desert',
    'Colombia':             'Coffee & Gold',
    'Costa Rica':           'Pura Vida',
    'Croatia':              'Adriatic Coast',
    'DR Congo':             'Congo River',
    'Ecuador':              'Galápagos Islands',
    'Egypt':                'Pyramids & Nile',
    'England':              'Football Birthplace',
    'France':               'Eiffel Tower & Croissants',
    'Germany':              'Cars & Oktoberfest',
    'Ghana':                'Black Stars',
    'Honduras':             'Maya Ruins',
    'Indonesia':            'Bali & 17,000 Islands',
    'Iran':                 'Ancient Persia',
    'Ivory Coast':          'Elephants & Cacao',
    'Japan':                'Mt Fuji & Sushi',
    'Kenya':                'Safari & Distance Running',
    'Mexico':               'Tacos & Pyramids',
    'Morocco':              'Sahara & Medinas',
    'Netherlands':          'Tulips & Windmills',
    'New Zealand':          'Hobbits & All Blacks',
    'Nigeria':              'Nollywood & Jollof Rice',
    'Panama':               'The Famous Canal',
    'Paraguay':             'Guaraní Culture',
    'Peru':                 'Machu Picchu',
    'Portugal':             'Pastel de Nata',
    'Saudi Arabia':         'Desert Kingdom',
    'Senegal':              'Lions of Teranga',
    'Serbia':               "Djokovic's Home",
    'South Africa':         'Mandela & Safari',
    'South Korea':          'K-pop & Kimchi',
    'Spain':                'Flamenco & Tapas',
    'Switzerland':          'Alps & Chocolate',
    'Tunisia':              'Carthage & Medina',
    'Turkey':               'Istanbul & Kebabs',
    'Ukraine':              'Sunflowers & History',
    'United States':        '🏠 Home Team!',
    'Uruguay':              'Mate & Gaucho',
    'Venezuela':            'Angel Falls',
    'Algeria':              'Sahara & Couscous',
}

st.markdown("---")
st.markdown(
    "<div style='font-size:1.25rem;font-weight:900;color:#F1F5F9;margin-bottom:.3rem'>"
    "🌍 Browse All 48 Countries</div>"
    "<div style='font-size:.83rem;color:#64748B;margin-bottom:.8rem'>"
    "Click any country to explore — tap a continent to expand</div>",
    unsafe_allow_html=True,
)

for _cont in _CONTINENT_ORDER:
    if _meta_df.empty:
        _cont_countries = [n for n in all_countries if True]
    else:
        _cont_row = _meta_df[_meta_df['continent'] == _cont]
        _cont_countries = [n for n in _cont_row['country'].tolist() if n in set(all_countries)]

    if not _cont_countries:
        continue

    _disc_c  = sum(1 for c in _cont_countries if c in discoveries)
    _em      = _CONTINENT_EMOJI.get(_cont, '🌍')
    _total_c = len(_cont_countries)

    with st.expander(
        f"{_em} {_cont} — {_disc_c}/{_total_c} explored",
        expanded=False,
    ):
        # 4-column grid of country cards
        _cc_rows = [_cont_countries[i:i+4] for i in range(0, len(_cont_countries), 4)]
        for _cc_row in _cc_rows:
            _cc_cols = st.columns(4)
            for _cc_col, _cc_name in zip(_cc_cols, _cc_row):
                _cc_team = teams_df[teams_df['name'] == _cc_name]
                if _cc_team.empty:
                    continue
                _cc_t   = _cc_team.iloc[0]
                _cc_flag = str(_cc_t.get('flag_emoji', '🏳️'))

                # Stamp emoji from metadata
                _cc_stamp_row = _meta_df[_meta_df['country'] == _cc_name] if not _meta_df.empty else _pd.DataFrame()
                _cc_stamp = str(_cc_stamp_row['stamp_emoji'].iloc[0]) if not _cc_stamp_row.empty else '🌍'

                # Discovery status
                if _cc_name in won:
                    _cc_badge, _cc_bg = "🏆", "rgba(252,211,77,.12)"
                elif _cc_name in cheered:
                    _cc_badge, _cc_bg = "⚽", "rgba(74,222,128,.10)"
                elif _cc_name in discoveries:
                    _cc_badge, _cc_bg = "🌱", "rgba(96,165,250,.10)"
                else:
                    _cc_badge, _cc_bg = "", "rgba(30,41,59,.5)"

                _cc_id = _IDENTITY.get(_cc_name, '')
                with _cc_col:
                    st.markdown(
                        f"<div style='background:{_cc_bg};"
                        f"border:1px solid rgba(148,163,184,.15);border-radius:10px;"
                        f"padding:.5rem .35rem;text-align:center;margin:.1rem 0'>"
                        f"<div style='font-size:1.7rem;line-height:1'>{_cc_flag}</div>"
                        f"<div style='font-size:.65rem;font-weight:800;color:#F1F5F9;"
                        f"line-height:1.2;margin:.15rem 0 .05rem'>{_cc_name}</div>"
                        + (f"<div style='font-size:.57rem;color:#64748B;font-style:italic;"
                           f"line-height:1.2;margin-bottom:.1rem'>{_cc_id}</div>"
                           if _cc_id else "")
                        + f"<div style='font-size:.78rem'>{_cc_stamp}</div>"
                        f"<div style='font-size:.58rem;color:#94A3B8;margin-top:.05rem'>{_cc_badge}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button("Explore", key=f"cb_{_cc_name}", use_container_width=True):
                        st.session_state["_nav_country"] = _cc_name
                        st.switch_page("pages/country_profile.py")
