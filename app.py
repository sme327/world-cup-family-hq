import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from services.database import init_db
from services.picks import get_all_users

# ── localStorage support (optional dep; graceful fallback) ────────────────────
try:
    from streamlit_javascript import st_javascript as _st_js
    _LS_OK = True
except ImportError:
    _LS_OK = False

_LS_KEY = "wc_hq_user_id"

# ── Init ──────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Espinosa World Cup Family HQ",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "db_ready" not in st.session_state:
    init_db()
    st.session_state["db_ready"] = True

# ── Global CSS ────────────────────────────────────────────────────────────────
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

    /* ── Hide Admin from main nav (accessible below Playing As) ── */
    [data-testid="stSidebarNav"] a[href*="admin"],
    [data-testid="stSidebarNav"] a[href*="Admin"] { display: none !important; }
    [data-testid="stSidebarNav"] > ul > li:last-child,
    [data-testid="stSidebarNav"] > div > ul > li:last-child { display: none !important; }
    [data-testid="stSidebarNav"] > ul > *:has(a[href*="admin"]),
    [data-testid="stSidebarNav"] > div > ul > *:has(a[href*="admin"]) { display: none !important; }

    /* ── First-visit player card styling ─────────── */
    div[data-testid="stVerticalBlockBorderWrapper"].fp-card {
        cursor: pointer;
        transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"].fp-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 18px rgba(0,0,0,.35) !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Load users ────────────────────────────────────────────────────────────────
_users  = get_all_users()
_by_id  = {str(int(r["id"])): r for _, r in _users.iterrows()}
_names  = _users["name"].tolist()
_avs    = dict(zip(_users["name"], _users["avatar"]))
_clrs   = dict(zip(_users["name"], _users["theme_color"]))
_ids    = dict(zip(_users["name"], _users["id"]))
_po     = dict(zip(_users["name"], _users["picks_only"].fillna(0).astype(int)))


# ── First-visit player selection screen ───────────────────────────────────────
def _render_first_visit() -> None:
    st.markdown("""
    <div style='max-width:760px;margin:3rem auto 0;text-align:center;'>
        <div style='font-size:4rem;margin-bottom:0.5rem'>🏆⚽🌍</div>
        <h1 style='font-size:2.4rem;margin:0.3rem 0 0.2rem;'>
            Welcome to<br>Espinosa Family World Cup HQ!
        </h1>
        <p style='font-size:1.25rem;opacity:0.72;margin:0.75rem 0 2rem;'>
            Who are you today?
        </p>
    </div>
    """, unsafe_allow_html=True)

    ul = _users.to_dict("records")
    # Two rows: 4 per row max
    for row_items in [ul[:4], ul[4:]] if len(ul) > 4 else [ul]:
        cols = st.columns(len(row_items), gap="medium")
        for col, u in zip(cols, row_items):
            with col:
                with st.container(border=True):
                    st.markdown(
                        f"<div style='text-align:center;font-size:3.2rem;"
                        f"padding:0.75rem 0 0.2rem'>{u['avatar']}</div>"
                        f"<div style='text-align:center;font-weight:600;"
                        f"font-size:1.1rem;padding-bottom:0.5rem'>{u['name']}</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button("That's me!", key=f"fp_{u['id']}", use_container_width=True):
                        uid_str = str(int(u["id"]))
                        st.session_state.update({
                            "active_user_id":         int(u["id"]),
                            "active_user_name":       u["name"],
                            "active_user_avatar":     u["avatar"],
                            "active_user_color":      u["theme_color"],
                            "active_user_picks_only": bool(int(u.get("picks_only", 0))),
                            "ls_pending_uid":         uid_str,
                        })
                        st.rerun()

    st.markdown(
        "<div style='text-align:center;opacity:0.4;margin-top:2rem;font-size:0.9rem;'>"
        "Your browser will remember your choice — you can always switch in the sidebar.</div>",
        unsafe_allow_html=True,
    )


# ── localStorage: write any pending save (from previous selection or switch) ──
if _LS_OK and "ls_pending_uid" in st.session_state:
    _uid_to_write = st.session_state["ls_pending_uid"]
    # Key encodes the UID so a different UID forces a new component instance + JS re-run
    _st_js(
        f"localStorage.setItem('{_LS_KEY}', '{_uid_to_write}')",
        key=f"__ls_w{_uid_to_write}",
    )
    del st.session_state["ls_pending_uid"]

# ── localStorage: read saved user (only needed once per session) ───────────────
_has_session = "active_user_id" in st.session_state

if not _has_session:
    if _LS_OK:
        # Returns None while component loads (first render), then the string value
        _saved_uid: str | None = _st_js(
            f"localStorage.getItem('{_LS_KEY}') || ''",
            key="__ls_r",
        )
    else:
        _saved_uid = ""  # No JS support → treat as no saved user

    # Auto-initialize session from a valid saved UID
    if _saved_uid and _saved_uid in _by_id:
        r = _by_id[_saved_uid]
        st.session_state.update({
            "active_user_id":         int(r["id"]),
            "active_user_name":       str(r["name"]),
            "active_user_avatar":     str(r["avatar"]),
            "active_user_color":      str(r["theme_color"]),
            "active_user_picks_only": bool(int(r.get("picks_only", 0))),
        })
        _has_session = True
else:
    _saved_uid = "ok"  # Session already live; skip localStorage read

# ── Navigation ────────────────────────────────────────────────────────────────
pg = st.navigation(
    {
        "": [
            st.Page("pages/home.py", title="Home", icon="🏠", default=True),
        ],
        "⚽ Play": [
            st.Page("pages/schedule.py",     title="Schedule",     icon="📅"),
            st.Page("pages/matchup.py",      title="Matchups",     icon="🏟️"),
            st.Page("pages/pick_tracker.py", title="Family Picks", icon="📊"),
        ],
        "🌎 Explore": [
            st.Page("pages/country_profile.py",     title="Countries",       icon="🗺️"),
            st.Page("pages/host_cities.py",          title="Host Cities",     icon="🏙️"),
            st.Page("pages/passport_individual.py",  title="My Passport",     icon="🛂"),
            st.Page("pages/passport_family.py",      title="Family Passport", icon="👨‍👩‍👧‍👦"),
            st.Page("pages/achievements.py",         title="Achievements",    icon="🏅"),
            st.Page("pages/leaderboard.py",          title="Leaderboard",     icon="🏆"),
        ],
        # Admin hidden from sidebar nav via CSS; must stay here for Streamlit routing.
        "⚙️": [
            st.Page("pages/admin.py", title="Admin", icon="🔧"),
        ],
    },
    position="sidebar",
    expanded=True,
)

# ── Route ─────────────────────────────────────────────────────────────────────
_js_ready = not _LS_OK or _saved_uid is not None  # True once the read component reports

if not _js_ready:
    # st_javascript component still initializing — Streamlit auto-reruns when it fires
    st.stop()

elif not _has_session:
    # First visit on this browser / device
    _render_first_visit()
    # (pg.run() intentionally not called; nav links visible but inactive until selected)

else:
    # ── Sidebar: Playing As selector ──────────────────────────────────────────
    with st.sidebar:
        _current = st.session_state.get("active_user_name", _names[0])
        _idx     = _names.index(_current) if _current in _names else 0
        _chosen  = st.selectbox(
            "⚽ Playing As",
            _names,
            index=_idx,
            format_func=lambda n: f"{_avs[n]} {n}",
            key="global_user_selector",
        )

        # Manual switch → queue localStorage update for next render
        if _chosen != st.session_state.get("active_user_name"):
            st.session_state["ls_pending_uid"] = str(int(_ids[_chosen]))

        st.session_state.update({
            "active_user_name":       _chosen,
            "active_user_id":         int(_ids[_chosen]),
            "active_user_avatar":     _avs[_chosen],
            "active_user_color":      _clrs[_chosen],
            "active_user_picks_only": bool(_po.get(_chosen, 0)),
        })

        st.divider()
        st.page_link("pages/admin.py", label="Admin", icon="🔧")

    pg.run()
