import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from services.database import init_db
from services.picks import get_all_users

st.set_page_config(
    page_title="Espinosa World Cup Family HQ",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "db_ready" not in st.session_state:
    init_db()
    st.session_state["db_ready"] = True

st.markdown("""
<style>
    /* ── Sidebar ─────────────────────────────────── */
    [data-testid="stSidebar"] { background-color: #1E3A5F; }
    /* Target sidebar nav + labels without leaking into dropdown popups */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span:not([data-baseweb]),
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] *,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * { color: white !important; }

    /* ── Global emoji / text size ────────────────── */
    .stMarkdown p, .stMarkdown li { font-size: 1.08rem; line-height: 1.65; }
    .stButton > button { font-size: 1rem !important; padding: 0.45rem 0.9rem !important; }
    [data-testid="stPopover"] > button {
        font-size: 2rem !important;
        min-height: 3.2rem !important;
        line-height: 1 !important;
        padding: 0.2rem 0.3rem !important;
    }
    [data-testid="metric-container"] [data-testid="metric-value"] { font-size: 1.9rem !important; }
    [data-testid="metric-container"] [data-testid="metric-label"] { font-size: 1rem !important; }

    /* ── Global emoji helper classes ─────────────── */
    .emoji-xl { font-size: 3.5rem; display: inline-block; }
    .emoji-lg { font-size: 2.5rem; display: inline-block; }
    .emoji-md { font-size: 1.8rem; display: inline-block; }

    /* ── Bordered containers — theme-adaptive ──────── */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--secondary-background-color) !important;
        border: 1px solid rgba(128,128,128,.2) !important;
        border-radius: 14px !important;
        padding: 0.4rem !important;
        box-shadow: 0 2px 8px rgba(0,0,0,.18) !important;
    }

    /* ── Typography ──────────────────────────────── */
    h1, h2, h3 { font-family: 'Georgia', serif; }
</style>
""", unsafe_allow_html=True)

# ── Grouped navigation ────────────────────────────────────────────────────────
pg = st.navigation(
    {
        "": [
            st.Page("pages/home.py", title="Home", icon="🏠", default=True),
        ],
        "Tournament": [
            st.Page("pages/schedule.py",    title="Schedule",     icon="📅"),
            st.Page("pages/matchup.py",     title="Matchup",      icon="🏟️"),
            st.Page("pages/pick_tracker.py", title="Pick Tracker", icon="🎯"),
        ],
        "Explore": [
            st.Page("pages/country_profile.py", title="Countries",   icon="🌍"),
            st.Page("pages/host_cities.py",      title="Host Cities", icon="🏙️"),
        ],
        "Passports": [
            st.Page("pages/passport_individual.py", title="My Passport",     icon="🛂"),
            st.Page("pages/passport_family.py",     title="Family Passport", icon="👨‍👩‍👧‍👦"),
        ],
        "Progress": [
            st.Page("pages/leaderboard.py",  title="Leaderboard",  icon="🏆"),
            st.Page("pages/achievements.py", title="Achievements",  icon="🏅"),
            st.Page("pages/admin.py",        title="Admin",         icon="🔧"),
        ],
    },
    position="sidebar",
    expanded=True,
)

# ── Global user selector ──────────────────────────────────────────────────────
_users  = get_all_users()
_names  = _users['name'].tolist()
_avs    = dict(zip(_users['name'], _users['avatar']))
_clrs   = dict(zip(_users['name'], _users['theme_color']))
_ids    = dict(zip(_users['name'], _users['id']))
_po     = dict(zip(_users['name'], _users.get('picks_only', [0]*len(_users))))

with st.sidebar:
    _current = st.session_state.get("active_user_name", _names[0])
    _idx     = _names.index(_current) if _current in _names else 0
    _chosen  = st.selectbox(
        "👤 Playing as",
        _names,
        index=_idx,
        format_func=lambda n: f"{_avs[n]} {n}",
        key="global_user_selector",
    )
    st.session_state["active_user_name"]      = _chosen
    st.session_state["active_user_id"]        = int(_ids[_chosen])
    st.session_state["active_user_avatar"]    = _avs[_chosen]
    st.session_state["active_user_color"]     = _clrs[_chosen]
    st.session_state["active_user_picks_only"] = bool(_po.get(_chosen, 0))

pg.run()
