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
    initial_sidebar_state="collapsed",
)

if "db_ready" not in st.session_state:
    init_db()
    st.session_state["db_ready"] = True

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Global spacing — tight top so nav sits high ── */
    section.main > div.block-container {
        padding-top: .4rem !important;
        padding-bottom: 1rem !important;
        overflow: visible !important;
    }
    section.main { overflow: visible !important; }
    .element-container { overflow: visible !important; }

    /* ── Sidebar (user switcher only) ───────────────── */
    [data-testid="stSidebar"] { background-color: #1E3A5F; }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span:not([data-baseweb]),
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

    /* ── First-visit player card styling ─────────── */
    div[data-testid="stVerticalBlockBorderWrapper"].fp-card {
        cursor: pointer;
        transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"].fp-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 18px rgba(0,0,0,.35) !important;
    }

    /* ═══════════════════════════════════════════════
       TOP NAV BAR
    ═══════════════════════════════════════════════ */
    .tnav-wrap { position: relative; z-index: 9000; margin-bottom: .6rem; }
    .tnav {
        display: flex;
        align-items: center;
        background: linear-gradient(135deg,#1E293B,#0F172A);
        border-radius: 12px;
        padding: .3rem .55rem;
        gap: .05rem;
        border: 1px solid rgba(148,163,184,.15);
        box-shadow: 0 3px 14px rgba(0,0,0,.35);
    }
    .tnav a { text-decoration: none !important; }

    /* Nav items */
    .tnav-item {
        color: #94A3B8;
        padding: .42rem .82rem;
        border-radius: 8px;
        font-size: .92rem;
        font-weight: 600;
        cursor: pointer;
        transition: background .13s, color .13s;
        white-space: nowrap;
        display: inline-flex;
        align-items: center;
        gap: .3rem;
        user-select: none;
        text-decoration: none !important;
        line-height: 1.4;
    }
    .tnav-item:hover { background: rgba(255,255,255,.09); color: #F1F5F9; }
    .tnav-item.tnav-active { background: #2563EB; color: white !important; font-weight: 800; }
    .tnav-caret { font-size: .65rem; opacity: .65; margin-left: .1rem; }
    .tnav-sep { width: 1px; height: 1.1rem; background: rgba(148,163,184,.2); margin: 0 .1rem; flex-shrink: 0; }

    /* Dropdown */
    .tnav-drop { position: relative; display: inline-block; }
    .tnav-menu {
        display: none;
        position: absolute;
        top: calc(100% + .35rem);
        left: 0;
        background: linear-gradient(160deg,#1E293B,#0F172A);
        border: 1px solid rgba(148,163,184,.22);
        border-radius: 10px;
        padding: .3rem;
        min-width: 205px;
        z-index: 99999;
        box-shadow: 0 14px 40px rgba(0,0,0,.55);
    }
    .tnav-drop:hover .tnav-menu { display: block; }
    .tnav-menu a {
        display: flex;
        align-items: center;
        gap: .55rem;
        padding: .44rem .78rem;
        color: #CBD5E1;
        text-decoration: none !important;
        border-radius: 7px;
        font-size: .88rem;
        font-weight: 500;
        transition: background .11s, color .11s;
        white-space: nowrap;
    }
    .tnav-menu a:hover { background: rgba(37,99,235,.28); color: white; }
    .tnav-menu a.tnav-page-active {
        background: rgba(37,99,235,.38);
        color: #93C5FD;
        font-weight: 700;
    }

    /* User chip — right side */
    .tnav-user {
        margin-left: auto;
        display: flex;
        align-items: center;
        gap: .5rem;
        background: rgba(255,255,255,.07);
        border: 1px solid rgba(148,163,184,.15);
        border-radius: 8px;
        padding: .3rem .7rem;
        color: #F1F5F9;
        font-size: .88rem;
        font-weight: 700;
        white-space: nowrap;
    }
    .tnav-avatar { font-size: 1.4rem; line-height: 1; }
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
        "Your browser will remember your choice — open the ☰ menu to switch users.</div>",
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
            st.Page("pages/pick_tracker.py", title="Family Picks", icon="🎯"),
            st.Page("pages/standings.py",    title="Standings",    icon="📊"),
            st.Page("pages/leaderboard.py",  title="Leaderboard",  icon="🏆"),
        ],
        "🌎 Explore": [
            st.Page("pages/country_profile.py",   title="Countries",        icon="🗺️"),
            st.Page("pages/map.py",               title="World Atlas",      icon="🌎"),
            st.Page("pages/host_cities.py",       title="Host Cities",      icon="🏙️"),
            st.Page("pages/world_cup_history.py", title="World Cup History",icon="📖"),
        ],
        "🛂 Passport": [
            st.Page("pages/passport_individual.py", title="My Passport",     icon="🛂"),
            st.Page("pages/passport_family.py",     title="Family Passport", icon="👨‍👩‍👧‍👦"),
        ],
        # Hidden from sidebar nav via CSS; kept for routing (redirects to passport pages).
        "⚙️": [
            st.Page("pages/admin.py",         title="Admin",         icon="🔧"),
            st.Page("pages/achievements.py",  title="Achievements",  icon="🏅"),
            st.Page("pages/discovery_race.py",title="Discovery Race",icon="🌎"),
        ],
    },
    position="hidden",
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
    # ── Callback: fires at start of rerun so pg.run() sees the updated user ──
    def _apply_user_selection():
        _sel = st.session_state.get("global_user_selector", _names[0])
        if _sel != st.session_state.get("active_user_name"):
            st.session_state["ls_pending_uid"] = str(int(_ids[_sel]))
        st.session_state.update({
            "active_user_name":       _sel,
            "active_user_id":         int(_ids[_sel]),
            "active_user_avatar":     _avs[_sel],
            "active_user_color":      _clrs[_sel],
            "active_user_picks_only": bool(_po.get(_sel, 0)),
        })

    # ── Horizontal top nav bar ─────────────────────────────────────────────────
    _SECTION_MAP = {
        "": "home", "home": "home",
        "schedule": "play", "matchup": "play", "pick_tracker": "play",
        "standings": "play", "leaderboard": "play",
        "country_profile": "explore", "map": "explore",
        "host_cities": "explore", "world_cup_history": "explore",
        "passport_individual": "passport", "passport_family": "passport",
        "achievements": "passport", "discovery_race": "passport",
        "admin": "admin",
    }
    _url  = pg.url_path
    _sec  = _SECTION_MAP.get(_url, "home")
    _nav_av   = st.session_state.get("active_user_avatar", "🐘")
    _nav_name = st.session_state.get("active_user_name", "")

    def _ni(section: str) -> str:
        return "tnav-item tnav-active" if _sec == section else "tnav-item"

    def _pi(page: str) -> str:
        return "tnav-page-active" if _url == page else ""

    st.markdown(f"""
<div class='tnav-wrap'>
  <nav class='tnav'>
    <a href='/home' class='{_ni("home")}'>🏠 Home</a>
    <span class='tnav-sep'></span>
    <div class='tnav-drop'>
      <span class='{_ni("play")}'>⚽ Play <span class='tnav-caret'>▾</span></span>
      <div class='tnav-menu'>
        <a href='/schedule' class='{_pi("schedule")}'>📅 Schedule</a>
        <a href='/matchup' class='{_pi("matchup")}'>🏟️ Matchups</a>
        <a href='/pick_tracker' class='{_pi("pick_tracker")}'>🎯 Family Picks</a>
        <a href='/standings' class='{_pi("standings")}'>📊 Standings</a>
        <a href='/leaderboard' class='{_pi("leaderboard")}'>🏆 Leaderboard</a>
      </div>
    </div>
    <div class='tnav-drop'>
      <span class='{_ni("explore")}'>🌎 Explore <span class='tnav-caret'>▾</span></span>
      <div class='tnav-menu'>
        <a href='/country_profile' class='{_pi("country_profile")}'>🗺️ Countries</a>
        <a href='/map' class='{_pi("map")}'>🌍 World Atlas</a>
        <a href='/host_cities' class='{_pi("host_cities")}'>🏙️ Host Cities</a>
        <a href='/world_cup_history' class='{_pi("world_cup_history")}'>📖 World Cup History</a>
      </div>
    </div>
    <div class='tnav-drop'>
      <span class='{_ni("passport")}'>🛂 Passport <span class='tnav-caret'>▾</span></span>
      <div class='tnav-menu'>
        <a href='/passport_individual' class='{_pi("passport_individual")}'>🛂 My Passport</a>
        <a href='/passport_family' class='{_pi("passport_family")}'>👨‍👩‍👧‍👦 Family Passport</a>
      </div>
    </div>
    <div class='tnav-user'>
      <span class='tnav-avatar'>{_nav_av}</span>
      {_nav_name}
    </div>
  </nav>
</div>
""", unsafe_allow_html=True)

    # Run current page — sidebar filters added by pages appear above user selector
    pg.run()

    # ── Sidebar: Playing As + Admin (below page filters) ──────────────────────
    with st.sidebar:
        _current = st.session_state.get("active_user_name", _names[0])
        _idx     = _names.index(_current) if _current in _names else 0
        _chosen  = st.selectbox(
            "⚽ Playing As",
            _names,
            index=_idx,
            format_func=lambda n: f"{_avs[n]} {n}",
            key="global_user_selector",
            on_change=_apply_user_selection,
        )
        # Sync every render (handles first load and edge cases)
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
