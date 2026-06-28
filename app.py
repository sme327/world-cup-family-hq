import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from services.database import init_db
from services.picks import get_all_users

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
    /* ── Eliminate Streamlit header bar (dead space + hamburger) ── */
    [data-testid="stHeader"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        visibility: hidden !important;
    }

    /* ── Remove sidebar entirely ─────────────────────────────────── */
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"] { display: none !important; }

    /* ── Kill every layer of top spacing so nav sits flush ────────── */
    [data-testid="stAppViewContainer"] { padding-top: 0 !important; margin-top: 0 !important; }
    [data-testid="stMain"]             { padding-top: 0 !important; margin-top: 0 !important; }
    section.main                       { padding-top: 0 !important; margin-top: 0 !important; overflow: visible !important; }
    [data-testid="stMainBlockContainer"],
    section.main > div.block-container {
        padding-top: 0 !important;
        margin-top: 0 !important;
        padding-bottom: 1rem !important;
        overflow: visible !important;
    }
    /* stVerticalBlock is a newer Streamlit wrapper inside stMainBlockContainer */
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }

    .element-container { overflow: visible !important; }

    /* ── Global emoji / text size ────────────────── */
    .stMarkdown p, .stMarkdown li { font-size: 1.08rem; line-height: 1.65; }
    .stButton > button { font-size: 1rem !important; padding: 0.45rem 0.9rem !important; }
    /* Large stamp popovers defined per-page in passport_individual / passport_family */
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
    .tnav-wrap { position: relative; z-index: 9000; margin-bottom: .55rem; }
    .tnav {
        display: flex;
        align-items: center;
        background: linear-gradient(135deg,#1E293B,#0F172A);
        border-radius: 10px;
        padding: .28rem .5rem;
        gap: .05rem;
        border: 1px solid rgba(148,163,184,.15);
        box-shadow: 0 3px 14px rgba(0,0,0,.35);
    }
    .tnav a { text-decoration: none !important; }

    /* Nav items */
    .tnav-item {
        color: #94A3B8;
        padding: .4rem .8rem;
        border-radius: 7px;
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
        top: 100%;          /* no gap — hover zone is continuous from trigger into menu */
        left: 0;
        background: linear-gradient(160deg,#1E293B,#0F172A);
        border: 1px solid rgba(148,163,184,.22);
        border-radius: 10px;
        padding: .5rem .3rem .3rem;   /* top padding replaces the old visual gap */
        min-width: 205px;
        z-index: 99999;
        box-shadow: 0 14px 40px rgba(0,0,0,.55);
    }
    .tnav-drop:hover .tnav-menu { display: block; }

    /* Allow dropdowns to overflow Streamlit column containers */
    [data-testid="stColumn"],
    [data-testid="stHorizontalBlock"] { overflow: visible !important; }
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
    .tnav-menu a.tnav-page-active { background: rgba(37,99,235,.38); color: #93C5FD; font-weight: 700; }

    /* Nav row: stretch so both columns are the same height */
    [data-testid="stHorizontalBlock"]:first-of-type {
        margin-top: 0 !important;
        gap: .4rem !important;
        align-items: stretch !important;
    }
    /* User selector popover container fills the column height */
    [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:last-child
        [data-testid="stPopover"] {
        height: 100% !important;
        display: flex !important;
        flex-direction: column !important;
    }
    /* User selector button fills the popover container */
    [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:last-child
        [data-testid="stPopover"] > button {
        flex: 1 !important;
        height: 100% !important;
        min-height: 2.4rem !important;
        font-size: .9rem !important;
        padding: .25rem .7rem !important;
        background: rgba(255,255,255,.08) !important;
        border: 1px solid rgba(148,163,184,.2) !important;
        border-radius: 8px !important;
        color: #F1F5F9 !important;
        font-weight: 700 !important;
        line-height: 1.4 !important;
        width: 100% !important;
    }

    /* Tighten up user-switcher popover: kill excess padding and gaps */
    [data-testid="stPopoverBody"] {
        padding: .5rem .5rem .3rem !important;
    }
    [data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] {
        gap: .15rem !important;
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
                        st.session_state.update({
                            "active_user_id":         int(u["id"]),
                            "active_user_name":       u["name"],
                            "active_user_avatar":     u["avatar"],
                            "active_user_color":      u["theme_color"],
                            "active_user_picks_only": bool(int(u.get("picks_only", 0))),
                        })
                        st.query_params["u"] = str(int(u["id"]))
                        st.rerun()

    st.markdown(
        "<div style='text-align:center;opacity:0.4;margin-top:2rem;font-size:0.9rem;'>"
        "Your browser will remember your choice — tap your name in the top-right corner to switch users.</div>",
        unsafe_allow_html=True,
    )


# ── Restore session from URL query param ?u=<user_id> ────────────────────────
_has_session = "active_user_id" in st.session_state

if not _has_session:
    _uid_from_url = st.query_params.get("u", "")
    if _uid_from_url and _uid_from_url in _by_id:
        r = _by_id[_uid_from_url]
        st.session_state.update({
            "active_user_id":         int(r["id"]),
            "active_user_name":       str(r["name"]),
            "active_user_avatar":     str(r["avatar"]),
            "active_user_color":      str(r["theme_color"]),
            "active_user_picks_only": bool(int(r.get("picks_only", 0))),
        })
        _has_session = True

# ── Navigation ────────────────────────────────────────────────────────────────
pg = st.navigation(
    {
        "": [
            st.Page("pages/home.py", title="Home", icon="🏠", default=True),
        ],
        "⚽ Play": [
            st.Page("pages/schedule.py",     title="Schedule",     icon="📅"),
            st.Page("pages/matchup.py",      title="Matchups",     icon="🏟️"),
            st.Page("pages/bracket.py",        title="Bracket",        icon="🗂️"),
            st.Page("pages/bracket_picks.py", title="Bracket Picks",  icon="🎯"),
            st.Page("pages/pick_tracker.py",  title="Family Picks",   icon="🃏"),
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
if not _has_session:
    # First visit on this browser / device
    _render_first_visit()
    # (pg.run() intentionally not called; nav links visible but inactive until selected)

else:
    # ── Top nav: nav bar (left) + user selector (right) ───────────────────────
    _SECTION_MAP = {
        "": "home", "home": "home",
        "schedule": "play", "matchup": "play", "bracket": "play",
        "bracket_picks": "play", "pick_tracker": "play",
        "standings": "play", "leaderboard": "play",
        "country_profile": "explore", "map": "explore",
        "host_cities": "explore", "world_cup_history": "explore",
        "passport_individual": "passport", "passport_family": "passport",
        "achievements": "passport", "discovery_race": "passport",
        "admin": "admin",
    }
    _url = pg.url_path
    _sec = _SECTION_MAP.get(_url, "home")

    def _ni(section: str) -> str:
        return "tnav-item tnav-active" if _sec == section else "tnav-item"

    def _pi(page: str) -> str:
        return "tnav-page-active" if _url == page else ""

    _uid_qp = str(st.session_state.get("active_user_id", ""))
    _nav_col, _usr_col = st.columns([9, 2], gap="small")

    with _nav_col:
        st.markdown(f"""
<div class='tnav-wrap'>
  <nav class='tnav'>
    <a href='/?u={_uid_qp}' class='{_ni("home")}' target='_self'>🏠 Home</a>
    <span class='tnav-sep'></span>
    <div class='tnav-drop'>
      <span class='{_ni("play")}'>⚽ Play <span class='tnav-caret'>▾</span></span>
      <div class='tnav-menu'>
        <a href='/schedule?u={_uid_qp}' class='{_pi("schedule")}' target='_self'>📅 Schedule</a>
        <a href='/matchup?u={_uid_qp}' class='{_pi("matchup")}' target='_self'>🏟️ Matchups</a>
        <a href='/bracket?u={_uid_qp}' class='{_pi("bracket")}' target='_self'>🗂️ Bracket</a>
        <a href='/bracket_picks?u={_uid_qp}' class='{_pi("bracket_picks")}' target='_self'>🎯 Bracket Picks</a>
        <a href='/pick_tracker?u={_uid_qp}' class='{_pi("pick_tracker")}' target='_self'>🃏 Family Picks</a>
        <a href='/standings?u={_uid_qp}' class='{_pi("standings")}' target='_self'>📊 Standings</a>
        <a href='/leaderboard?u={_uid_qp}' class='{_pi("leaderboard")}' target='_self'>🏆 Leaderboard</a>
      </div>
    </div>
    <div class='tnav-drop'>
      <span class='{_ni("explore")}'>🌎 Explore <span class='tnav-caret'>▾</span></span>
      <div class='tnav-menu'>
        <a href='/country_profile?u={_uid_qp}' class='{_pi("country_profile")}' target='_self'>🗺️ Countries</a>
        <a href='/map?u={_uid_qp}' class='{_pi("map")}' target='_self'>🌍 World Atlas</a>
        <a href='/host_cities?u={_uid_qp}' class='{_pi("host_cities")}' target='_self'>🏙️ Host Cities</a>
        <a href='/world_cup_history?u={_uid_qp}' class='{_pi("world_cup_history")}' target='_self'>📖 World Cup History</a>
      </div>
    </div>
    <div class='tnav-drop'>
      <span class='{_ni("passport")}'>🛂 Passport <span class='tnav-caret'>▾</span></span>
      <div class='tnav-menu'>
        <a href='/passport_individual?u={_uid_qp}' class='{_pi("passport_individual")}' target='_self'>🛂 My Passport</a>
        <a href='/passport_family?u={_uid_qp}' class='{_pi("passport_family")}' target='_self'>👨‍👩‍👧‍👦 Family Passport</a>
      </div>
    </div>
  </nav>
</div>
""", unsafe_allow_html=True)

    with _usr_col:
        _current  = st.session_state.get("active_user_name", _names[0])
        _curr_av  = _avs.get(_current, "🐘")
        with st.popover(f"{_curr_av} {_current} ▾", use_container_width=True):
            st.caption("Switch user")
            for _n in _names:
                _is_me = (_n == _current)
                if st.button(
                    f"{_avs.get(_n, '🐘')} {_n}{'  ✓' if _is_me else ''}",
                    key=f"_uswitch_{_n}",
                    use_container_width=True,
                    type="primary" if _is_me else "secondary",
                ):
                    if not _is_me:
                        st.session_state.update({
                            "active_user_name":       _n,
                            "active_user_id":         int(_ids[_n]),
                            "active_user_avatar":     _avs[_n],
                            "active_user_color":      _clrs[_n],
                            "active_user_picks_only": bool(_po.get(_n, 0)),
                        })
                        st.query_params["u"] = str(int(_ids[_n]))
                        st.rerun()
            st.page_link("pages/admin.py", label="⚙️ Admin", icon="🔧")

    pg.run()
