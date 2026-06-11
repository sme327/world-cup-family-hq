import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from services.teams import get_all_teams, get_team_by_name, get_flag
from services.passport import get_stamp, log_discovery, get_country_metadata
from services.matches import get_matches_by_team
from services.images import get_country_image_html
from services.roster import (
    get_team_roster, get_team_summary, get_featured_players,
    get_mls_players, get_roster_by_position, pos_icon
)
from services.time_utils import fmt_date, fmt_match_time

# ── ISO-2 → ISO-3 for Plotly choropleth ──────────────────────────────────────
_ISO3 = {
    'MX':'MEX','ZA':'ZAF','KR':'KOR','CZ':'CZE','CA':'CAN','BA':'BIH',
    'QA':'QAT','CH':'CHE','BR':'BRA','MA':'MAR','HT':'HTI','GB':'GBR',
    'GB-SCT':'GBR','US':'USA','PY':'PRY','AU':'AUS','TR':'TUR','DE':'DEU',
    'CW':'CUW','CI':'CIV','EC':'ECU','NL':'NLD','JP':'JPN','SE':'SWE',
    'TN':'TUN','BE':'BEL','EG':'EGY','IR':'IRN','NZ':'NZL','ES':'ESP',
    'CV':'CPV','SA':'SAU','UY':'URY','FR':'FRA','SN':'SEN','NO':'NOR',
    'IQ':'IRQ','AR':'ARG','DZ':'DZA','AT':'AUT','JO':'JOR','PT':'PRT',
    'CD':'COD','UZ':'UZB','CO':'COL','HR':'HRV','GH':'GHA','PA':'PAN',
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _parse_pipe(val) -> list[str]:
    if not val or pd.isna(val):
        return []
    return [s.strip() for s in str(val).split('|') if s.strip()]


def _safe(val, default="—"):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return val


def _parse_pop_m(pop_str: str) -> float | None:
    s = str(pop_str).lower().replace(',', '')
    try:
        if 'billion' in s:
            return float(s.split('billion')[0].split()[-1]) * 1000
        if 'million' in s:
            return float(s.split('million')[0].split()[-1])
        if 'thousand' in s:
            return float(s.split('thousand')[0].split()[-1]) / 1000
    except Exception:
        pass
    return None


@st.cache_data(ttl=86400)
def _country_map(iso3: str):
    fig = go.Figure(go.Choropleth(
        locations=[iso3], z=[1], locationmode='ISO-3',
        colorscale=[[0, '#2563EB'], [1, '#2563EB']],
        showscale=False,
        marker_line_color='white', marker_line_width=0.8,
    ))
    fig.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True, coastlinecolor='#94A3B8',
            showland=True, landcolor='#E2E8F0',
            showocean=True, oceancolor='#DBEAFE',
            projection_type='natural earth',
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=270,
        paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig



def _stat_card(icon: str, label: str, value: str) -> str:
    return (
        "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);border-radius:12px;"
        "padding:.8rem;text-align:center;color:white;border:1px solid rgba(148,163,184,.15)'>"
        f"<div style='font-size:1.5rem'>{icon}</div>"
        f"<div style='font-size:.75rem;color:#94A3B8;margin:.15rem 0;font-weight:600;text-transform:uppercase;letter-spacing:.04em'>{label}</div>"
        f"<div style='font-size:.92rem;font-weight:800;color:#F1F5F9;line-height:1.2'>{value}</div>"
        "</div>"
    )


def _explore_card(emoji: str, label: str) -> str:
    """Visual card for animals / foods / landmarks."""
    return (
        "<div style='background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;"
        "padding:.7rem .5rem;text-align:center'>"
        f"<div style='font-size:2.2rem;line-height:1.1;margin-bottom:.3rem'>{emoji}</div>"
        f"<div style='font-size:.82rem;font-weight:700;color:#0F172A;line-height:1.2'>{label}</div>"
        "</div>"
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────
teams_df = get_all_teams()

_nav_country = st.session_state.pop("_nav_country", None)

with st.sidebar:
    st.markdown("### 🌍 Explore Countries")
    all_countries = sorted(teams_df['name'].tolist())
    default_idx   = all_countries.index(_nav_country) if _nav_country and _nav_country in all_countries else 0
    selected_country = st.selectbox("Country", all_countries, index=default_idx)

active_user_id = st.session_state.get("active_user_id", 1)

# ── Silent discovery logging ──────────────────────────────────────────────────
log_discovery(active_user_id, selected_country)

# ── Load data ─────────────────────────────────────────────────────────────────
team  = get_team_by_name(selected_country)
stamp = get_stamp(selected_country)
flag  = get_flag(selected_country)

if team is None:
    st.error(f"Country data not found: {selected_country}")
    st.stop()

iso2    = _safe(team.get('country_code'), '')
iso3    = _ISO3.get(iso2, '')
fun     = _safe(team.get('fun_fact'), '')

# ── 1. Hero Image ─────────────────────────────────────────────────────────────
hero_html = get_country_image_html(selected_country, height='320px')
has_hero  = hero_html is not None

if has_hero:
    st.markdown(hero_html, unsafe_allow_html=True)

# ── Country identity banner ───────────────────────────────────────────────────
flag_size    = "2.5rem" if has_hero else "4rem"
header_pad   = "1rem 1.5rem 1.2rem" if has_hero else "2rem"
border_radius = "0 0 16px 16px" if has_hero else "16px"

st.markdown(
    f"<div style='background:linear-gradient(135deg,#1E3A5F,#2563EB);"
    f"padding:{header_pad};border-radius:{border_radius};text-align:center;color:white;margin-bottom:1.2rem'>"
    f"<div style='font-size:{flag_size};margin-bottom:.2rem'>{flag}</div>"
    f"<div style='font-size:2rem;font-weight:900'>{selected_country}</div>"
    f"<div style='font-size:1.1rem;color:#FCD34D;margin:.2rem 0'>{stamp['stamp_emoji']} {stamp['stamp_label']}</div>"
    f"<div style='color:#CBD5E1;font-size:.88rem'>"
    f"{stamp['continent']} · Group {_safe(team.get('group_letter'))} · FIFA #{_safe(team.get('fifa_ranking'))}"
    f"</div></div>",
    unsafe_allow_html=True
)

if not has_hero:
    # Placeholder image card when no real image is available
    st.markdown(
        "<div style='background:linear-gradient(135deg,#1E293B,#0F172A);border-radius:12px;"
        "height:120px;display:flex;align-items:center;justify-content:center;color:rgba(255,255,255,.3);"
        "font-size:.85rem;margin-bottom:1rem;border:1px dashed rgba(148,163,184,.3)'>"
        "<div style='text-align:center'><div style='font-size:1.8rem'>📷</div><div>Country photo coming soon</div></div>"
        "</div>",
        unsafe_allow_html=True
    )

# ── 2. Country Facts Grid (2 rows × 3 cards) ──────────────────────────────────
st.markdown("### 🌍 Country Facts")
row1 = st.columns(3)
row2 = st.columns(3)
facts = [
    ("🏙️", "Capital",       _safe(team.get('capital'))),
    ("👥", "Population",    _safe(team.get('population'))),
    ("🗣️", "Languages",     _safe(team.get('languages'))),
    ("💰", "Currency",      _safe(team.get('currency'))),
    ("🌍", "Continent",     stamp['continent']),
    ("⚽", "Confederation", _safe(team.get('confederation'))),
]
for col, (icon, label, val) in zip(list(row1) + list(row2), facts):
    col.markdown(_stat_card(icon, label, val), unsafe_allow_html=True)

if fun:
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#FEF3C7,#FDE68A);border-radius:12px;"
        f"padding:.75rem 1rem;margin:.7rem 0;border-left:4px solid #FCD34D'>"
        f"<div style='font-size:.88rem;color:#78350F'><b>💡 Did you know?</b> {fun}</div></div>",
        unsafe_allow_html=True
    )

# ── 3. Where Is This Country? Map ─────────────────────────────────────────────
st.markdown("### 🗺️ Where Is This Country?")
if iso3:
    try:
        fig = _country_map(iso3)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    except Exception:
        st.info(f"📍 {selected_country} is located in {stamp['continent']}.")
else:
    st.info(f"📍 {selected_country} is located in {stamp['continent']}.")

# ── 4. Animals & Nature ───────────────────────────────────────────────────────
animals = _parse_pipe(team.get('animals'))
if animals:
    st.markdown("### 🐾 Animals & Nature")
    a_cols = st.columns(min(len(animals), 4))
    for col, a in zip(a_cols, animals[:4]):
        parts = a.rsplit(' ', 1)
        emoji = parts[-1] if len(parts) == 2 and len(parts[-1]) <= 4 else "🐾"
        label = parts[0] if len(parts) == 2 else a
        col.markdown(_explore_card(emoji, label), unsafe_allow_html=True)

# ── 5. Famous Foods ───────────────────────────────────────────────────────────
foods = _parse_pipe(team.get('foods'))
if foods:
    st.markdown("### 🍽️ Famous Foods")
    f_cols = st.columns(min(len(foods), 4))
    for col, food in zip(f_cols, foods[:4]):
        parts = food.rsplit(' ', 1)
        emoji = parts[-1] if len(parts) == 2 and len(parts[-1]) <= 4 else "🍴"
        label = parts[0] if len(parts) == 2 else food
        col.markdown(_explore_card(emoji, label), unsafe_allow_html=True)

# ── 6. Famous Landmarks ───────────────────────────────────────────────────────
landmarks = _parse_pipe(team.get('landmarks'))
if landmarks:
    st.markdown("### 🏛️ Famous Landmarks")
    l_cols = st.columns(min(len(landmarks), 4))
    for col, lm in zip(l_cols, landmarks[:4]):
        col.markdown(_explore_card("📍", lm), unsafe_allow_html=True)

# ── 7. Why Kids Might Cheer ───────────────────────────────────────────────────
reasons = _parse_pipe(team.get('cheer_reasons'))
if reasons:
    st.markdown("### 🎉 Why Kids Might Cheer For This Country")
    r_cols = st.columns(min(len(reasons), 4))
    for col, reason in zip(r_cols, reasons[:4]):
        parts = reason.rsplit(' ', 1)
        if len(parts) == 2:
            label, emoji = parts[0].strip(), parts[1].strip()
        else:
            label, emoji = reason, "⭐"
        blurb = f"{selected_country} is known for {label.lower()}."
        with col:
            st.markdown(
                "<div style='background:white;border:1.5px solid #E2E8F0;border-radius:14px;"
                "padding:.9rem .6rem;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.06)'>"
                f"<div style='font-size:2.5rem;margin-bottom:.3rem'>{emoji}</div>"
                f"<div style='font-size:.88rem;font-weight:800;color:#0F172A;margin-bottom:.2rem'>{label}</div>"
                f"<div style='font-size:.75rem;color:#64748B;line-height:1.35'>{blurb}</div>"
                "</div>",
                unsafe_allow_html=True
            )

# ── 8. Compared to Home ───────────────────────────────────────────────────────
st.markdown("### 🏠 Compared to Home")
comparisons = []
pop_m = _parse_pop_m(team.get('population', ''))
if pop_m:
    usa_m = 335.0
    sea_m = 4.0
    if pop_m >= usa_m:
        comparisons.append(f"👥 **{selected_country}** has **{pop_m/usa_m:.1f}×** as many people as the USA.")
    elif pop_m >= 10:
        pct = int(pop_m / usa_m * 100)
        comparisons.append(f"👥 **{selected_country}** has about **{pct}%** of the USA's population ({pop_m:.0f}M people).")
    else:
        comparisons.append(f"👥 **{selected_country}** has about **{pop_m:.1f}M** people — similar to the Seattle metro area ({sea_m:.0f}M).")

lang = _safe(team.get('languages'), '')
if lang and 'English' not in lang:
    comparisons.append(f"🗣️ People in **{selected_country}** speak **{lang}** — not English!")
elif lang and 'English' in lang:
    comparisons.append(f"🗣️ They speak **English** in {selected_country} — just like us!")

flag_fact = stamp.get('flag_fact', '')
if flag_fact:
    comparisons.append(f"🏴 **Flag fact:** {flag_fact}")

for c in comparisons[:3]:
    st.markdown(c)

# ── 9. Soccer Team Overview ───────────────────────────────────────────────────
st.divider()
st.markdown("## ⚽ Soccer Team")

soc1, soc2, soc3 = st.columns(3)
soc1.metric("FIFA Ranking", f"#{_safe(team.get('fifa_ranking'))}")
soc1.markdown(f"**Coach:** {_safe(team.get('coach'))}")
soc1.markdown(f"**Captain:** {_safe(team.get('captain'))}")
soc2.metric("World Cup Appearances", _safe(team.get('wc_appearances'), "—"))
soc2.markdown(f"**Best Finish:** {_safe(team.get('best_finish'))}")

# ── 10. Upcoming Matches Widget ───────────────────────────────────────────────
matches = get_matches_by_team(selected_country)
if not matches.empty:
    st.markdown("#### ⚽ Group Stage Matches")
    for _, m in matches.iterrows():
        opp       = m['away_team'] if m['home_team'] == selected_country else m['home_team']
        opp_flag  = get_flag(opp)
        mid       = int(m['id'])
        time_str  = fmt_match_time(m['match_date'], m['kickoff_time_et'])

        if m['status'] == 'completed':
            hs, as_ = int(m['home_score']), int(m['away_score'])
            score   = f"**{hs}–{as_}**"
            label   = f"{flag} {selected_country} vs {opp_flag} {opp} · {score}"
        else:
            label   = f"{flag} {selected_country} vs {opp_flag} **{opp}** · {time_str}"

        col_info, col_btn = st.columns([5, 2])
        col_info.markdown(label)
        if col_btn.button("🏟️ Matchup", key=f"match_link_{mid}"):
            st.session_state["_nav_match_id"] = mid
            st.switch_page("pages/matchup.py")

# ── 11. Meet the Team ────────────────────────────────────────────────────────
st.divider()
st.markdown("## 👥 Meet the Team")

summary      = get_team_summary(selected_country)
roster       = get_team_roster(selected_country)
captain_name = _safe(team.get('captain'), '')

if summary:
    st.markdown("#### Squad Snapshot")
    sn_cols = st.columns(5)
    for col, (icon, label, key) in zip(sn_cols, [
        ("🧤", "GK",       "goalkeepers"),
        ("🛡️", "DEF",      "defenders"),
        ("⚙️", "MID",      "midfielders"),
        ("⚽", "FWD",      "forwards"),
        ("📅", "Avg Age",  "average_age"),
    ]):
        val = summary.get(key, 0)
        display = f"{float(val):.1f}" if key == "average_age" else str(int(val))
        col.markdown(
            f"<div style='text-align:center'><div style='font-size:1.6rem'>{icon}</div>"
            f"<div style='font-weight:900;font-size:1.2rem'>{display}</div>"
            f"<div style='font-size:.75rem;color:#64748B'>{label}</div></div>",
            unsafe_allow_html=True
        )

# Players to Know
featured = get_featured_players(selected_country, captain_name)
if featured:
    st.markdown("#### ⭐ Players to Know")
    p_cols = st.columns(min(len(featured), 5))
    for col, p in zip(p_cols, featured):
        with col:
            st.markdown(
                "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);border-radius:12px;"
                "padding:.9rem .7rem;text-align:center;color:white;border:1px solid rgba(148,163,184,.15)'>"
                f"<div style='font-size:.65rem;color:#94A3B8;font-weight:700;text-transform:uppercase'>{p['role']}</div>"
                f"<div style='font-size:1.8rem;font-weight:900;color:#FCD34D'>#{p['shirt_number']}</div>"
                f"<div style='font-size:.88rem;font-weight:800;line-height:1.2;margin:.1rem 0'>{p['name']}</div>"
                f"<div style='font-size:.75rem;color:#94A3B8'>{p['position']}</div>"
                f"<div style='font-size:.72rem;color:#64748B;margin-top:.15rem'>{p['club_short']}</div>"
                f"<div style='font-size:.7rem;color:#475569'>Age {p['age']}</div>"
                "</div>",
                unsafe_allow_html=True
            )

# MLS connections
mls_players = get_mls_players(selected_country)
if not mls_players.empty:
    st.markdown("#### 🏟️ MLS & US Connections")
    mls_cols = st.columns(min(len(mls_players), 3))
    for col, (_, p) in zip(mls_cols, mls_players.iterrows()):
        col.markdown(
            "<div style='background:linear-gradient(135deg,#064E3B,#065F46);border-radius:10px;"
            "padding:.65rem .9rem;color:white'>"
            f"<div style='font-size:.95rem;font-weight:800'>#{int(p['shirt_number'])} {p['player_name']}</div>"
            f"<div style='font-size:.78rem;color:#6EE7B7'>{p['position']}</div>"
            f"<div style='font-size:.75rem;color:#A7F3D0'>🏟️ {p['club_short']} · Age {int(p['age'])}</div>"
            "</div>",
            unsafe_allow_html=True
        )

# Full Squad with expanders
if not roster.empty:
    st.markdown("#### 📋 Full Squad")
    by_pos = get_roster_by_position(selected_country)
    for pos in ['Goalkeeper', 'Defender', 'Midfielder', 'Forward']:
        pos_df = by_pos.get(pos)
        if pos_df is None or pos_df.empty:
            continue
        icon   = pos_icon(pos)
        count  = len(pos_df)
        with st.expander(f"{icon} {pos}s ({count})", expanded=False):
            for _, p in pos_df.iterrows():
                st.markdown(
                    f"**#{int(p['shirt_number'])}** &nbsp; {p['player_name']} "
                    f"<span style='color:#64748B;font-size:.88rem'>· {p['club_short']} · Age {int(p['age'])}</span>",
                    unsafe_allow_html=True
                )
