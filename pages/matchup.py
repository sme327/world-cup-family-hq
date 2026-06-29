import streamlit as st
import pandas as pd
from services.matches import get_match_by_id, get_all_matches
from services.teams import get_team_by_name, get_flag
from services.picks import get_picks_for_match, save_pick, get_all_users
from services.time_utils import fmt_match_time
from services.images import get_country_image_html
from services.roster import get_featured_players, get_team_summary, get_mls_players, get_team_roster, get_player_slug
from services.player_cards import render_player_modal_content
from services.ko_picks import (
    get_all_ko_matches_display, get_ko_picks_for_match, save_ko_pick,
    get_ko_pick, KO_ROUND_LABELS, KO_ROUND_POINTS,
)
from services.espn import get_match_recap
from services.scoring import get_team_group_status


@st.dialog("⭐ Player Profile", width="large")
def _show_player_modal(slug: str) -> None:
    uid = st.session_state.get('active_user_id', 1)
    render_player_modal_content(slug, uid)


# ── Pure helpers ───────────────────────────────────────────────────────────────

def _parse_pipe(val) -> list[str]:
    if not val or pd.isna(val):
        return []
    return [s.strip() for s in str(val).split('|') if s.strip()]


def _safe(val, default="—"):
    return val if val and not pd.isna(val) else default


def _pick_result(picked, home_team, away_team, home_score, away_score):
    if pd.isna(home_score) or pd.isna(away_score):
        return None
    hs, as_ = int(home_score), int(away_score)
    if hs == as_:
        return 0.5
    return 1.0 if picked == (home_team if hs > as_ else away_team) else 0.0


def _role_color(role: str) -> str:
    if "Captain" in role:     return "#7C3AED"
    if "Youngest" in role:    return "#16A34A"
    if "Oldest" in role:      return "#D97706"
    if "MLS" in role:         return "#0369A1"
    return "#475569"


# ── Param-based render helpers (shared between tabs) ──────────────────────────

def _player_trading_card(p: dict) -> str:
    role_color = _role_color(p['role'])
    return (
        "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);"
        "border-radius:12px;padding:.9rem .7rem;text-align:center;color:white;"
        "border:1px solid rgba(148,163,184,.15);min-width:110px;flex:1'>"
        f"<div style='background:{role_color};color:white;border-radius:4px;"
        f"font-size:.62rem;font-weight:800;padding:.1rem .4rem;"
        f"display:inline-block;letter-spacing:.04em;margin-bottom:.4rem'>{p['role']}</div>"
        f"<div style='font-size:2rem;font-weight:900;color:#FCD34D;line-height:1'>#{p['shirt_number']}</div>"
        f"<div style='font-size:.9rem;font-weight:900;line-height:1.2;margin:.2rem 0'>{p['name']}</div>"
        f"<div style='font-size:.75rem;color:#94A3B8'>{p['position']}</div>"
        f"<div style='font-size:.72rem;color:#64748B;margin-top:.15rem'>{p['club_short']}</div>"
        f"<div style='font-size:.7rem;color:#475569'>Age {p['age']}</div>"
        "</div>"
    )


def _country_card(team, flag, data, pfx=""):
    if data is None:
        st.caption("Data unavailable.")
        return
    st.markdown(
        "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);"
        "border-radius:14px;padding:1.2rem;color:white;height:100%'>"
        f"<div style='font-size:3rem;margin-bottom:.35rem'>{flag}</div>"
        f"<div style='font-size:1.4rem;font-weight:900;margin-bottom:.7rem'>{team}</div>"
        "<div style='font-size:1rem;line-height:2;color:#CBD5E1'>"
        f"🏙️ <b>Capital:</b> {_safe(data.get('capital'))}<br>"
        f"👥 <b>Population:</b> {_safe(data.get('population'))}<br>"
        f"🗣️ <b>Languages:</b> {_safe(data.get('languages'))}<br>"
        f"💰 <b>Currency:</b> {_safe(data.get('currency'))}<br>"
        f"🏆 <b>FIFA Rank:</b> #{_safe(data.get('fifa_ranking'))}<br>"
        f"🎽 <b>Coach:</b> {_safe(data.get('coach'))}"
        "</div></div>",
        unsafe_allow_html=True,
    )
    if st.button(f"🌍 Open {team} Profile", key=f"{pfx}cp_{team}", use_container_width=True):
        st.session_state["_nav_country"] = team
        st.switch_page("pages/country_profile.py")


def _roster_snapshot_card(team, flag, featured, team_sum) -> str:
    captain  = next((p for p in featured if "Captain"  in p['role']), None) if featured else None
    youngest = next((p for p in featured if "Youngest" in p['role']), None) if featured else None
    oldest   = next((p for p in featured if "Oldest"   in p['role']), None) if featured else None
    avg_age  = float(team_sum.get('average_age', 0)) if team_sum else 0
    try:
        roster_df = get_team_roster(team)
        if not roster_df.empty:
            club_counts  = roster_df['club'].value_counts()
            tc_short     = club_counts.index[0].split('(')[0].strip()[:22]
            top_club_str = f"{tc_short} ({int(club_counts.iloc[0])} players)"
        else:
            top_club_str = "—"
    except Exception:
        top_club_str = "—"
    rows = []
    if youngest:          rows.append(f"👶 <b>Youngest:</b> {youngest['name']}, age {youngest['age']}")
    if oldest:            rows.append(f"👴 <b>Oldest:</b> {oldest['name']}, age {oldest['age']}")
    if captain:           rows.append(f"⭐ <b>Captain:</b> {captain['name']}")
    if top_club_str != "—": rows.append(f"🏟️ <b>Top club:</b> {top_club_str}")
    if avg_age > 0:       rows.append(f"📅 <b>Avg age:</b> {avg_age:.1f}")
    rows_html = "<br>".join(rows) if rows else "Roster data unavailable."
    return (
        "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);"
        "border-radius:12px;padding:1rem 1.1rem;color:white;flex:1'>"
        f"<div style='font-size:1.5rem;margin-bottom:.25rem'>{flag}</div>"
        f"<div style='font-size:1rem;font-weight:900;margin-bottom:.5rem'>{team}</div>"
        f"<div style='font-size:.95rem;line-height:2;color:#CBD5E1'>{rows_html}</div>"
        "</div>"
    )


# ── Smart default for group stage ──────────────────────────────────────────────
def _smart_default_match_id() -> int:
    from datetime import datetime, timedelta
    now_pt = datetime.utcnow() - timedelta(hours=7)
    all_m  = get_all_matches()
    if all_m.empty:
        return 1
    for _, m in all_m.iterrows():
        if str(m['status']) != 'scheduled':
            continue
        try:
            ko = datetime.strptime(
                f"{m['match_date']} {m['kickoff_time_et']}", "%Y-%m-%d %H:%M"
            ) - timedelta(hours=3)
            if 0 < (now_pt - ko).total_seconds() / 60 < 115:
                return int(m['id'])
        except Exception:
            pass
    upcoming = []
    for _, m in all_m.iterrows():
        if str(m['status']) != 'scheduled':
            continue
        try:
            ko = datetime.strptime(
                f"{m['match_date']} {m['kickoff_time_et']}", "%Y-%m-%d %H:%M"
            ) - timedelta(hours=3)
            if ko > now_pt:
                upcoming.append((ko, int(m['id'])))
        except Exception:
            pass
    if upcoming:
        upcoming.sort(key=lambda x: x[0])
        return upcoming[0][1]
    done = all_m[all_m['status'] == 'completed']
    if not done.empty:
        return int(done.iloc[-1]['id'])
    return int(all_m.iloc[0]['id'])


# ── Shared page state ──────────────────────────────────────────────────────────
active_user    = st.session_state.get("active_user_name", "Shawn")
active_user_id = st.session_state.get("active_user_id", 1)
users          = get_all_users()

# ── Host city facts (shared) ───────────────────────────────────────────────────
CITY_FACTS = {
    "Mexico City":    ("🇲🇽", "One of Earth's largest cities at 2,240m altitude — players tire faster here! The Azteca has hosted two World Cup finals."),
    "Guadalajara":    ("🇲🇽", "Birthplace of mariachi music and home to tequila country! Mexico's second-largest city."),
    "Monterrey":      ("🇲🇽", "Mexico's industrial powerhouse nestled in the Sierra Madre mountains."),
    "East Rutherford":("🇺🇸", "Right outside New York City — the World Cup FINAL will be played here on July 19!"),
    "Arlington":      ("🇺🇸", "Home of AT&T Stadium (Dallas Cowboys), famous for the world's largest HD screen."),
    "Los Angeles":    ("🇺🇸", "Hollywood, sunshine, and SoFi Stadium — home of the Rams and Chargers."),
    "Santa Clara":    ("🇺🇸", "Silicon Valley! Levi's Stadium near the Golden Gate Bridge."),
    "Philadelphia":   ("🇺🇸", "The City of Brotherly Love — where the Declaration of Independence was signed."),
    "Miami Gardens":  ("🇺🇸", "South Florida energy! Lionel Messi's Inter Miami plays just nearby."),
    "Kansas City":    ("🇺🇸", "Home of legendary BBQ and Arrowhead — one of the loudest stadiums on Earth."),
    "Foxborough":     ("🇺🇸", "Near Boston! Gillette Stadium, home of the Patriots and New England history."),
    "Atlanta":        ("🇺🇸", "The ATL! Mercedes-Benz Stadium has a retractable roof over Atlanta United's home."),
    "Seattle":        ("🇺🇸", "🏠 The Espinosa family home city! Lumen Field — Sounders FC territory."),
    "Houston":        ("🇺🇸", "Space City! NRG Stadium is near NASA Mission Control."),
    "Vancouver":      ("🇨🇦", "Mountains meet ocean — BC Place is one of the most beautiful settings of the tournament."),
    "Toronto":        ("🇨🇦", "Canada's biggest city! BMO Field, home of Toronto FC and the CN Tower skyline."),
}

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_ko, tab_group = st.tabs(["🏆 Knockout", "🌍 Group Stage"])

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.mu-section {
    font-size:1.25rem; font-weight:900; margin:.95rem 0 .4rem;
    color:#F8FAFC; letter-spacing:-.01em;
    padding-bottom:.28rem;
    border-bottom:2px solid rgba(148,163,184,.18);
}
.pick-card  {
    border-radius:14px; padding:.75rem .8rem; text-align:center; color:white;
    transition:all .15s; cursor:pointer;
}
a.mu-chip {
    display:inline-block; padding:.26rem .72rem; border-radius:20px;
    background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.15);
    color:#CBD5E1; font-size:.8rem; font-weight:700; text-decoration:none;
    white-space:nowrap; transition:background .12s;
}
a.mu-chip:hover { background:rgba(255,255,255,.18); color:white; }
.cheer-card {
    background:linear-gradient(160deg,#1E293B,#0F172A);
    border-radius:12px; padding:.8rem .5rem;
    text-align:center; border:1px solid rgba(148,163,184,.15); margin:.2rem;
    color:#F1F5F9;
}
.mls-card {
    background:linear-gradient(135deg,#064E3B,#065F46);
    border-radius:12px; padding:.9rem 1.1rem; color:white; margin:.3rem 0;
}
.city-card {
    background:linear-gradient(135deg,#1E293B,#0F172A);
    border-radius:14px; padding:1.1rem 1.3rem; color:white;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# KNOCKOUT TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_ko:
    all_ko = get_all_ko_matches_display()
    nav_ko = [m for m in all_ko if m["id"] != 131]  # 131 = 3rd place, shown separately

    if not nav_ko:
        st.info("Knockout matches begin June 29, 2026. Check back soon!")
        st.stop()

    # ── Resolve target match ──────────────────────────────────────────────────
    try:
        _ko_qp_id = int(st.query_params.get("match_id") or 0)
    except (ValueError, TypeError):
        _ko_qp_id = 0

    _ko_ids = [m["id"] for m in nav_ko]
    if _ko_qp_id in _ko_ids:
        _ko_target = _ko_qp_id
    else:
        _sched = [m for m in nav_ko if m["status"] == "scheduled"]
        _ko_target = _sched[0]["id"] if _sched else nav_ko[-1]["id"]

    km = next((m for m in nav_ko if m["id"] == _ko_target), nav_ko[0])

    # ── Match selector ────────────────────────────────────────────────────────
    _ko_opts = {
        m["id"]: (
            f"{KO_ROUND_LABELS.get(m['round'], m['round'])} — "
            f"{m.get('home_flag','')} {m.get('home_name') or 'TBD'} vs "
            f"{m.get('away_name') or 'TBD'} {m.get('away_flag','')}"
        )
        for m in nav_ko
    }
    _ms_ko_col, _ = st.columns([4, 4])
    with _ms_ko_col:
        _ko_chosen = st.selectbox(
            "KO Match",
            list(_ko_opts.keys()),
            format_func=lambda k: _ko_opts[k],
            index=list(_ko_opts.keys()).index(km["id"]),
            label_visibility="collapsed",
            key="ko_mu_sel",
        )
    if _ko_chosen != km["id"]:
        st.query_params["match_id"] = str(_ko_chosen)
        st.rerun()

    # ── KO match variables ────────────────────────────────────────────────────
    ko_mid      = km["id"]
    ko_rnd      = km["round"]
    h_name      = km.get("home_name") or "TBD"
    a_name      = km.get("away_name") or "TBD"
    h_flag      = km.get("home_flag") or "⬜"
    a_flag      = km.get("away_flag") or "⬜"
    h_tid       = km.get("home_team_id")
    a_tid       = km.get("away_team_id")
    ko_done     = km["status"] == "completed"
    ko_pts      = KO_ROUND_POINTS.get(ko_rnd, 0)
    rnd_lbl     = KO_ROUND_LABELS.get(ko_rnd, ko_rnd)
    ko_time_str = fmt_match_time(km["match_date"], km.get("kickoff_time_et", ""))
    ko_picks    = get_ko_picks_for_match(ko_mid)
    ko_my_pick  = get_ko_pick(active_user_id, ko_mid) if h_tid and a_tid else None
    ko_winner_id = km.get("winner_team_id")

    if ko_done and km.get("home_score") is not None:
        _hs_str = f"{int(km['home_score'])}–{int(km['away_score'])}"
        _pens   = km.get("pens_str", "")
        if _pens:
            _hs_str += f" ({_pens})"
        ko_score_str = _hs_str
    else:
        ko_score_str = "vs"

    # ── 1. Hero Header ────────────────────────────────────────────────────────
    _hdr_l, _hdr_r = st.columns([6, 1])
    with _hdr_l:
        st.markdown(
            "<div style='background:linear-gradient(135deg,#1E3A5F,#1E293B);"
            "border-radius:16px;padding:1.1rem 1.4rem .9rem;margin-bottom:.5rem'>"
            "<div style='text-align:center'>"
            f"<div style='margin-bottom:.3rem'>"
            f"<span style='background:rgba(255,255,255,.1);color:#93C5FD;border-radius:4px;"
            f"padding:.08rem .4rem;font-size:.7rem;font-weight:800;"
            f"letter-spacing:.04em'>{rnd_lbl}</span>"
            f"<span style='background:rgba(252,211,77,.15);color:#FCD34D;border-radius:4px;"
            f"padding:.08rem .35rem;font-size:.68rem;font-weight:800;margin-left:.3rem'>"
            f"+{ko_pts} pts</span></div>"
            f"<div style='font-size:3rem;margin:.1rem 0'>{h_flag}&nbsp;&nbsp;{a_flag}</div>"
            f"<div style='font-size:1.4rem;font-weight:900;color:#F1F5F9'>"
            f"{h_name} "
            f"<span style='color:#FCD34D;font-size:1.2rem'>{ko_score_str}</span>"
            f" {a_name}</div>"
            f"<div style='font-size:.78rem;color:#94A3B8;margin-top:.2rem'>"
            f"🕒 {ko_time_str} · 🏟️ {km.get('venue', '')} · 📍 {km.get('city', '')}</div>"
            "</div></div>",
            unsafe_allow_html=True,
        )
    with _hdr_r:
        _uid_qp = st.session_state.get("active_user_id", 1)
        st.markdown(
            f"<div style='padding-top:2.8rem;text-align:right'>"
            f"<a href='/bracket?u={_uid_qp}' style='color:#93C5FD;font-size:.78rem;"
            f"font-weight:700;text-decoration:none;white-space:nowrap'>"
            f"🗂️&nbsp;Bracket&nbsp;→</a></div>",
            unsafe_allow_html=True,
        )

    # ── 2. Explore Countries ──────────────────────────────────────────────────
    _xc1, _xc2 = st.columns(2)
    with _xc1:
        if h_name != "TBD" and st.button(f"🌎 Explore {h_name}", key="ko_xp_h", use_container_width=True):
            st.session_state["_nav_country"] = h_name
            st.switch_page("pages/country_profile.py")
    with _xc2:
        if a_name != "TBD" and st.button(f"🌎 Explore {a_name}", key="ko_xp_a", use_container_width=True):
            st.session_state["_nav_country"] = a_name
            st.switch_page("pages/country_profile.py")

    # ── 3. Family Picks ───────────────────────────────────────────────────────
    st.markdown('<div class="mu-section">🏷️ Family Picks</div>', unsafe_allow_html=True)

    h_pickers = [p for p in ko_picks if p["picked_team_id"] == h_tid]
    a_pickers = [p for p in ko_picks if p["picked_team_id"] == a_tid]

    def _ko_pick_card(team, flag, tid, pickers, is_home):
        is_win   = ko_done and ko_winner_id == tid
        is_lose  = ko_done and ko_winner_id and ko_winner_id != tid
        my_pick  = ko_my_pick == tid
        bg       = "linear-gradient(135deg,#1E3A5F,#2563EB)" if is_home else "linear-gradient(135deg,#064E3B,#059669)"
        def_bdr  = "#3B82F6" if is_home else "#10B981"
        border   = "#FCD34D" if (ko_done and is_win) else def_bdr
        opacity  = 1.0 if not ko_done or is_win else 0.6

        result_html = ""
        if ko_done and ko_winner_id:
            if is_win:
                result_html = "<div style='color:#FCD34D;font-size:.9rem;font-weight:800;margin:.2rem 0'>🏆 Advanced!</div>"
                if pickers:
                    result_html += f"<div style='color:#4ADE80;font-size:.78rem'>+{ko_pts} pts each</div>"
            else:
                result_html = "<div style='color:#F87171;font-size:.85rem;margin:.2rem 0'>Eliminated</div>"
                if pickers:
                    result_html += "<div style='color:#F87171;font-size:.78rem'>+0 pts</div>"

        if pickers:
            cells = "".join(
                f"<div style='display:flex;align-items:center;gap:.25rem;padding:.1rem 0'>"
                f"<span style='font-size:1.5rem;line-height:1'>{p['avatar']}</span>"
                f"<span style='font-size:.72rem;font-weight:700;color:rgba(255,255,255,.9)'>{p['name']}</span>"
                f"</div>"
                for p in pickers
            )
            pickers_html = (
                f"<div style='display:grid;grid-template-columns:1fr 1fr;"
                f"gap:.05rem .3rem;margin:.35rem 0;text-align:left'>{cells}</div>"
            )
        else:
            pickers_html = "<div style='color:rgba(255,255,255,.4);font-size:.8rem;margin:.35rem 0'>No picks yet</div>"

        if not ko_done:
            if my_pick:
                status_lbl = "<div style='color:#FCD34D;font-size:.78rem;font-weight:700;margin-top:.25rem'>✅ You picked this</div>"
            elif ko_my_pick:
                status_lbl = "<div style='color:rgba(255,255,255,.4);font-size:.75rem;margin-top:.25rem'>You picked the other team</div>"
            else:
                status_lbl = "<div style='color:rgba(255,255,255,.6);font-size:.78rem;margin-top:.25rem'>👆 Tap to pick</div>"
        else:
            status_lbl = ""

        st.markdown(
            f"<div class='pick-card' style='background:{bg};border:3px solid {border};opacity:{opacity}'>"
            f"<div style='font-size:2.8rem;line-height:1;margin-bottom:.15rem'>{flag}</div>"
            f"<div style='font-size:1.2rem;font-weight:900;color:white'>{team}</div>"
            f"{result_html}{pickers_html}{status_lbl}"
            f"</div>",
            unsafe_allow_html=True,
        )
        pfx = "h" if is_home else "a"
        if h_tid and a_tid and not ko_done:
            btn_lbl = f"✅ Picked {team}" if my_pick else f"Pick {team}"
            if st.button(btn_lbl, key=f"ko_pk_{pfx}_{ko_mid}", use_container_width=True):
                save_ko_pick(active_user_id, ko_mid, tid)
                st.rerun()

    _fpc1, _fpc2 = st.columns(2)
    with _fpc1:
        _ko_pick_card(h_name, h_flag, h_tid, h_pickers, is_home=True)
    with _fpc2:
        _ko_pick_card(a_name, a_flag, a_tid, a_pickers, is_home=False)

    if ko_done and km.get("winner_name"):
        st.success(f"🏆 {km['winner_name']} advances to the next round!")
    elif not ko_done and h_tid and a_tid:
        st.caption(f"Pick your winner — worth {ko_pts} points! You can change your pick any time.")

    # ── 4. How They Got Here ──────────────────────────────────────────────────
    if h_name != "TBD" or a_name != "TBD":
        st.divider()
        st.markdown('<div class="mu-section">🛤️ How They Got Here</div>', unsafe_allow_html=True)
        st.caption("Each team's group stage journey that earned them this spot.")
        _path_c1, _path_c2 = st.columns(2)

        for _pcol, _team, _flag in [(_path_c1, h_name, h_flag), (_path_c2, a_name, a_flag)]:
            with _pcol:
                if _team == "TBD":
                    st.caption("Team TBD")
                    continue
                _td  = get_team_by_name(_team)
                _gl  = str(_td.get('group_letter', '') or '') if _td is not None else ''
                _gst = get_team_group_status(_team, _gl) if _gl else {}

                _pos    = _gst.get('position', 0)
                _pos_s  = {1:"1st",2:"2nd",3:"3rd",4:"4th"}.get(_pos, "—")
                _gpts   = _gst.get('pts', '—')
                _rec    = _gst.get('record', '—')
                _status = _gst.get('status', '')
                _sc     = _gst.get('status_color', '#94A3B8')
                _gf     = _gst.get('gf', 0)
                _ga     = _gst.get('ga', 0)
                _gd     = _gst.get('gd', 0)

                st.markdown(
                    f"<div style='background:rgba(15,23,42,.6);border-radius:12px;"
                    f"padding:.8rem 1rem;border:1px solid rgba(148,163,184,.12);margin-bottom:.5rem'>"
                    f"<div style='font-size:1.5rem;margin-bottom:.1rem'>{_flag}</div>"
                    f"<div style='font-size:1rem;font-weight:900;color:#F1F5F9;margin-bottom:.1rem'>{_team}</div>"
                    f"<div style='font-size:.8rem;color:#94A3B8'>Group {_gl} · {_pos_s} place</div>"
                    f"<div style='font-size:.88rem;color:#CBD5E1;margin:.15rem 0'>{_gpts} pts · {_rec}</div>"
                    f"<div style='font-size:.78rem;color:#CBD5E1'>GF {_gf} · GA {_ga} · GD {_gd:+d}</div>"
                    f"<div style='font-size:.82rem;font-weight:800;color:{_sc};margin-top:.25rem'>{_status}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                if _gl:
                    _all_gm = get_all_matches()
                    _tmatch = _all_gm[
                        ((_all_gm['home_team'] == _team) | (_all_gm['away_team'] == _team))
                        & (_all_gm['group_letter'] == _gl)
                    ].sort_values('match_date')

                    for _, _gm in _tmatch.iterrows():
                        _is_h  = _gm['home_team'] == _team
                        _opp   = _gm['away_team'] if _is_h else _gm['home_team']
                        _opp_f = get_flag(_opp)
                        _done  = _gm['status'] == 'completed'
                        if _done and not pd.isna(_gm.get('home_score')):
                            _hs2 = int(_gm['home_score'])
                            _as2 = int(_gm['away_score'])
                            _sc_str = f"{_hs2}–{_as2}"
                            if _is_h:
                                _res = ("W","#4ADE80") if _hs2>_as2 else (("D","#FCD34D") if _hs2==_as2 else ("L","#F87171"))
                            else:
                                _res = ("W","#4ADE80") if _as2>_hs2 else (("D","#FCD34D") if _as2==_hs2 else ("L","#F87171"))
                            _rbadge = (
                                f"<span style='font-size:.7rem;font-weight:800;color:{_res[1]};"
                                f"background:rgba(0,0,0,.3);border-radius:4px;"
                                f"padding:.05rem .28rem;min-width:1.2rem;display:inline-block;"
                                f"text-align:center'>{_res[0]}</span>"
                            )
                        else:
                            _sc_str = "TBD"
                            _rbadge = ""
                        _gm_date = str(_gm['match_date'])[5:]
                        st.markdown(
                            f"<div style='display:flex;align-items:center;gap:.5rem;"
                            f"padding:.28rem 0;border-bottom:1px solid rgba(148,163,184,.08);"
                            f"font-size:.82rem'>"
                            f"<span style='color:#64748B;min-width:2.2rem'>{_gm_date}</span>"
                            f"{_rbadge}"
                            f"<span style='color:#CBD5E1;flex:1'>vs {_opp_f} {_opp}</span>"
                            f"<span style='color:#94A3B8'>{_sc_str}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

    # ── 5. Players to Watch ───────────────────────────────────────────────────
    if h_name != "TBD" or a_name != "TBD":
        st.divider()
        st.markdown('<div class="mu-section">⭐ Players to Watch</div>', unsafe_allow_html=True)
        st.caption("Key players representing each country. Tap any player to learn more.")
        _pw1, _pw2 = st.columns(2)
        for _pwcol, _team, _flag in [(_pw1, h_name, h_flag), (_pw2, a_name, a_flag)]:
            with _pwcol:
                if _team == "TBD":
                    st.caption("Team TBD")
                    continue
                _td3  = get_team_by_name(_team)
                _cap3 = _safe(_td3.get('captain') if _td3 is not None else None, '')
                _feat = get_featured_players(_team, _cap3)
                st.markdown(
                    f"<div style='font-size:1rem;font-weight:800;margin-bottom:.4rem'>{_flag} {_team}</div>",
                    unsafe_allow_html=True,
                )
                if _feat:
                    _n3 = min(3, len(_feat))
                    _pcols3 = st.columns(_n3)
                    for _pc3, _p3 in zip(_pcols3, _feat[:_n3]):
                        _slug3 = get_player_slug(_team, _p3['name'])
                        with _pc3:
                            st.markdown(_player_trading_card(_p3), unsafe_allow_html=True)
                            if _slug3 and st.button(
                                "👤 Learn More",
                                key=f"ko_pl_{_slug3}",
                                use_container_width=True,
                            ):
                                _show_player_modal(_slug3)
                else:
                    st.caption("Roster data unavailable.")

    # ── 6. Country Comparison ─────────────────────────────────────────────────
    if h_name != "TBD" or a_name != "TBD":
        st.divider()
        st.markdown('<div class="mu-section">🌍 Country Comparison</div>', unsafe_allow_html=True)
        _cc1, _cc2 = st.columns(2)
        with _cc1:
            if h_name != "TBD":
                _country_card(h_name, h_flag, get_team_by_name(h_name), pfx="ko_")
        with _cc2:
            if a_name != "TBD":
                _country_card(a_name, a_flag, get_team_by_name(a_name), pfx="ko_")

    # ── 7. Who Should I Cheer For? ────────────────────────────────────────────
    if h_name != "TBD" or a_name != "TBD":
        st.divider()
        st.markdown('<div class="mu-section">🤔 Who Should I Cheer For?</div>', unsafe_allow_html=True)
        st.caption("Pick your side! Here's why you might love each team…")
        _ch1, _ch2 = st.columns(2)
        for _chcol, _team, _flag in [(_ch1, h_name, h_flag), (_ch2, a_name, a_flag)]:
            with _chcol:
                if _team == "TBD":
                    st.caption("Team TBD")
                    continue
                _chdata = get_team_by_name(_team)
                _img = get_country_image_html(_team, height='120px', border_radius='12px')
                if _img:
                    st.markdown(_img, unsafe_allow_html=True)
                st.markdown(
                    f"<div style='font-size:1.1rem;font-weight:800;margin:.4rem 0'>{_flag} {_team}</div>",
                    unsafe_allow_html=True,
                )
                _reasons = _parse_pipe(_chdata.get('cheer_reasons') if _chdata is not None else None)
                if _reasons:
                    _rcols = st.columns(min(len(_reasons), 4))
                    for _ri, _r in enumerate(_reasons[:4]):
                        _rparts = _r.rsplit(' ', 1)
                        _rlbl, _remoji = (_rparts[0].strip(), _rparts[1].strip()) if len(_rparts) == 2 else (_r, "⭐")
                        with _rcols[_ri % len(_rcols)]:
                            st.markdown(
                                f"<div class='cheer-card'>"
                                f"<div style='font-size:2.2rem;line-height:1.1'>{_remoji}</div>"
                                f"<div style='font-size:.82rem;font-weight:700;color:#F1F5F9;"
                                f"margin-top:.35rem;line-height:1.3'>{_rlbl}</div>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                else:
                    st.caption("They're still awesome!")

    # ── 8. Host City ──────────────────────────────────────────────────────────
    _ko_city = km.get("city", "")
    if _ko_city:
        st.divider()
        st.markdown('<div class="mu-section">🏙️ Host City</div>', unsafe_allow_html=True)
        _ko_cf, _ko_cfact = CITY_FACTS.get(_ko_city, ("📍", "One of the 16 host cities for the 2026 World Cup."))
        _koc_l, _koc_r = st.columns([3, 2])
        with _koc_l:
            st.markdown(
                "<div class='city-card'>"
                f"<div style='font-size:1.6rem;font-weight:900;margin-bottom:.1rem'>{_ko_cf} {_ko_city}</div>"
                f"<div style='color:#94A3B8;font-size:.82rem;margin-bottom:.6rem'>"
                f"🏟️ {km.get('venue', '')} · {km.get('host_country', '')}</div>"
                f"<div style='font-size:.95rem;color:#CBD5E1;line-height:1.6'>{_ko_cfact}</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            if st.button("🏙️ Full City Guide", key="ko_city_btn"):
                st.session_state["_nav_city"] = _ko_city
                st.switch_page("pages/host_cities.py")
        with _koc_r:
            _ko_host_ctry = km.get("host_country", "")
            if _ko_host_ctry:
                _koc_img = get_country_image_html(_ko_host_ctry, height='160px', border_radius='12px')
                if _koc_img:
                    st.markdown(_koc_img, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# GROUP STAGE TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_group:
    # ── Resolve active match ──────────────────────────────────────────────────
    if "_nav_match_id" in st.session_state:
        match_id = int(st.session_state.pop("_nav_match_id"))
        st.query_params["match_id"] = str(match_id)
    else:
        try:
            _qp = st.query_params.get("match_id")
            _qp_int = int(_qp) if _qp else 0
            # Only use QP if it's a group match ID (< 100)
            match_id = _qp_int if 0 < _qp_int < 100 else _smart_default_match_id()
        except (ValueError, TypeError):
            match_id = _smart_default_match_id()

    match = get_match_by_id(match_id)
    if match is None:
        st.error("Match not found.")
        st.stop()

    home_team = match['home_team']
    away_team = match['away_team']
    home_flag = get_flag(home_team)
    away_flag = get_flag(away_team)
    home_data = get_team_by_name(home_team)
    away_data = get_team_by_name(away_team)
    is_completed = match['status'] == 'completed'

    # ── Match selector ────────────────────────────────────────────────────────
    all_matches  = get_all_matches()
    match_labels = [
        f"{r['group_letter']}{r['match_number']}: {r['home_team']} vs {r['away_team']} ({r['match_date']})"
        for _, r in all_matches.iterrows()
    ]
    match_ids   = all_matches['id'].tolist()
    current_idx = match_ids.index(match_id) if match_id in match_ids else 0
    _ms_col, _ = st.columns([3, 5])
    with _ms_col:
        selected_label = st.selectbox(
            "🔍 Jump to match", match_labels,
            index=current_idx,
            key="gs_match_sel",
        )
    selected_id = match_ids[match_labels.index(selected_label)]
    if selected_id != match_id:
        st.query_params["match_id"] = str(selected_id)
        st.rerun()

    # ── 1. Match Hero Header ──────────────────────────────────────────────────
    if is_completed:
        hs, as_ = int(match['home_score']), int(match['away_score'])
        if hs > as_:   status_badge = f"FINAL · {home_team} wins {hs}–{as_}"
        elif as_ > hs: status_badge = f"FINAL · {away_team} wins {hs}–{as_}"
        else:          status_badge = f"FINAL · Draw {hs}–{as_}"
        score_html = f"<span style='font-size:2.2rem;font-weight:900;color:#FCD34D'>{hs} – {as_}</span>"
    else:
        time_str = fmt_match_time(match['match_date'], match['kickoff_time_et'])
        status_badge = f"Group {match['group_letter']} · {time_str}"
        score_html   = "<span style='font-size:2rem;font-weight:900;color:#FCD34D'>VS</span>"

    st.markdown(
        '<div style="background:linear-gradient(135deg,#1E3A5F,#2563EB,#1E3A5F);'
        'padding:1.1rem 1.4rem;border-radius:16px;text-align:center;color:white;margin-bottom:.6rem">'
        f'<div style="font-size:3.2rem;line-height:1">{home_flag} {score_html} {away_flag}</div>'
        f'<div style="font-size:1.5rem;font-weight:900;margin:.25rem 0">{home_team} &nbsp;vs&nbsp; {away_team}</div>'
        f'<div style="font-size:.88rem;color:#CBD5E1">{status_badge}</div>'
        f'<div style="font-size:.8rem;color:#94A3B8;margin-top:.1rem">📍 {match["venue"]}, {match["city"]}</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # ── Upfront data ──────────────────────────────────────────────────────────
    picks_df     = get_picks_for_match(match_id)
    pick_by_user = {
        pk['user_name']: pk['picked_team']
        for _, pk in picks_df.iterrows()
    } if not picks_df.empty else {}

    h_captain  = _safe(home_data.get('captain') if home_data is not None else None, '')
    a_captain  = _safe(away_data.get('captain') if away_data is not None else None, '')
    h_featured = get_featured_players(home_team, h_captain)
    a_featured = get_featured_players(away_team, a_captain)
    h_sum      = get_team_summary(home_team)
    a_sum      = get_team_summary(away_team)
    h_mls      = get_mls_players(home_team)
    a_mls      = get_mls_players(away_team)

    home_picks_info = [
        (u['name'], u['avatar']) for _, u in users.iterrows()
        if pick_by_user.get(u['name']) == home_team
    ]
    away_picks_info = [
        (u['name'], u['avatar']) for _, u in users.iterrows()
        if pick_by_user.get(u['name']) == away_team
    ]

    h_rank = home_data.get('fifa_ranking') if home_data is not None else None
    a_rank = away_data.get('fifa_ranking') if away_data is not None else None
    h_best = _safe(home_data.get('best_finish') if home_data is not None else None)
    a_best = _safe(away_data.get('best_finish') if away_data is not None else None)
    h_apps = home_data.get('wc_appearances') if home_data is not None else None
    a_apps = away_data.get('wc_appearances') if away_data is not None else None

    debate_cards = []
    if h_rank and a_rank:
        diff = abs(int(h_rank) - int(a_rank))
        if diff > 30:
            underdog = away_team if int(h_rank) < int(a_rank) else home_team
            fav      = home_team if int(h_rank) < int(a_rank) else away_team
            debate_cards.append({
                'icon': '🏆', 'color': '#7C3AED',
                'title': 'Favorite vs Underdog',
                'body': f"FIFA #{min(int(h_rank),int(a_rank))} {fav} vs #{max(int(h_rank),int(a_rank))} {underdog}.",
                'question': f"Can {underdog} pull off the upset today?",
            })
        else:
            debate_cards.append({
                'icon': '⚖️', 'color': '#3B82F6',
                'title': 'Well-Matched Teams',
                'body': f"FIFA #{h_rank} {home_team} vs #{a_rank} {away_team} — very close in the rankings.",
                'question': "Which team wants it more today?",
            })
    h_capital = _safe(home_data.get('capital') if home_data is not None else None)
    a_capital = _safe(away_data.get('capital') if away_data is not None else None)
    if h_capital != "—" and a_capital != "—":
        debate_cards.append({
            'icon': '✈️', 'color': '#0369A1',
            'title': 'Which country would you rather visit?',
            'body': f"{home_team}'s capital {h_capital} or {away_team}'s capital {a_capital}?",
            'question': "Pack your bags — where are you going?",
        })
    h_foods = _parse_pipe(home_data.get('foods') if home_data is not None else None)
    a_foods = _parse_pipe(away_data.get('foods') if away_data is not None else None)
    if h_foods and a_foods:
        debate_cards.append({
            'icon': '🍽️', 'color': '#D97706',
            'title': 'Better food?',
            'body': f"{h_foods[0]} from {home_team} vs {a_foods[0]} from {away_team}.",
            'question': "Which dish sounds tastier right now?",
        })
    h_animals = _parse_pipe(home_data.get('animals') if home_data is not None else None)
    a_animals = _parse_pipe(away_data.get('animals') if away_data is not None else None)
    if h_animals and a_animals and len(debate_cards) < 4:
        debate_cards.append({
            'icon': '🦁', 'color': '#16A34A',
            'title': 'Animal Showdown',
            'body': f"{h_animals[0]} ({home_team}) vs {a_animals[0]} ({away_team}).",
            'question': "Which animal would you want to see in the wild?",
        })
    if h_apps and a_apps and abs(int(h_apps) - int(a_apps)) > 5 and len(debate_cards) < 4:
        more_team = home_team if int(h_apps) > int(a_apps) else away_team
        less_team = away_team if int(h_apps) > int(a_apps) else home_team
        debate_cards.append({
            'icon': '📜', 'color': '#D97706',
            'title': 'Experience Gap',
            'body': f"{more_team} has {max(int(h_apps),int(a_apps))} World Cup appearances; {less_team} has {min(int(h_apps),int(a_apps))}.",
            'question': "Does experience matter more than hunger?",
        })
    if ("Winner" in str(h_best) or "Winner" in str(a_best)) and len(debate_cards) < 4:
        champ = home_team if "Winner" in str(h_best) else away_team
        debate_cards.append({
            'icon': '🥇', 'color': '#16A34A',
            'title': 'Former Champions',
            'body': f"{champ} has won the World Cup before!",
            'question': "Does that history give them an edge, or extra pressure?",
        })
    if not debate_cards:
        debate_cards.append({
            'icon': '🔥', 'color': '#DC2626',
            'title': f"Group {match['group_letter']} Battle",
            'body': f"Both {home_team} and {away_team} need points to advance.",
            'question': "Who do you think needs this win more?",
        })

    city        = match['city']
    city_flag, city_fact = CITY_FACTS.get(city, ("📍", "One of the 16 host cities for the 2026 World Cup."))

    # ── Section helper functions (closures over group-stage vars above) ────────

    def _pick_card(team: str, flag: str, is_home: bool):
        pickers      = [(u['name'], u['avatar']) for _, u in users.iterrows() if pick_by_user.get(u['name']) == team]
        user_pick    = pick_by_user.get(active_user)
        picked_by_me = user_pick == team

        bg             = "linear-gradient(135deg,#1E3A5F,#2563EB)" if is_home else "linear-gradient(135deg,#064E3B,#059669)"
        default_border = "#3B82F6" if is_home else "#10B981"

        opacity = 1.0
        result_badge = pts_badge = ""
        if is_completed:
            r = _pick_result(team, home_team, away_team, match['home_score'], match['away_score'])
            if r == 1.0:
                border       = "#FCD34D"
                result_badge = "<div style='font-size:1.1rem;margin:.1rem 0'>🏆 <span style='color:#FCD34D;font-weight:800;font-size:.9rem'>Winner!</span></div>"
                if pickers: pts_badge = "<div style='color:#4ADE80;font-weight:700;font-size:.8rem'>🟢 +1 pt each</div>"
            elif r == 0.5:
                border       = "#FCD34D"
                result_badge = "<div style='color:#FCD34D;font-weight:700;font-size:.82rem;margin:.1rem 0'>🤝 Draw</div>"
                if pickers: pts_badge = "<div style='color:#FCD34D;font-weight:700;font-size:.8rem'>🟡 +0.5 pts each</div>"
            else:
                border, opacity = "rgba(148,163,184,.25)", 0.6
                if pickers: pts_badge = "<div style='color:#F87171;font-weight:700;font-size:.8rem'>🔴 +0 pts</div>"
        else:
            border = "#FCD34D" if picked_by_me else default_border

        if pickers:
            cells = "".join(
                f"<div style='display:flex;align-items:center;gap:.25rem;padding:.1rem 0'>"
                f"<span style='font-size:1.5rem;line-height:1'>{a}</span>"
                f"<span style='font-size:.72rem;font-weight:700;color:rgba(255,255,255,.9)'>{n}</span>"
                f"</div>"
                for n, a in pickers
            )
            avatars_html = (
                f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:.05rem .3rem;"
                f"margin:.35rem 0;text-align:left'>{cells}</div>"
            )
        else:
            avatars_html = "<div style='color:rgba(255,255,255,.4);font-size:.8rem;margin:.35rem 0'>No picks yet</div>"

        if not is_completed:
            if picked_by_me:
                status_label = "<div style='color:#FCD34D;font-size:.78rem;font-weight:700;margin-top:.25rem'>✅ You picked this</div>"
            elif user_pick:
                status_label = "<div style='color:rgba(255,255,255,.4);font-size:.75rem;margin-top:.25rem'>You picked the other team</div>"
            else:
                status_label = "<div style='color:rgba(255,255,255,.6);font-size:.78rem;margin-top:.25rem'>👆 Tap to pick</div>"
        else:
            status_label = ""

        st.markdown(
            f"<div class='pick-card' style='background:{bg};border:3px solid {border};opacity:{opacity}'>"
            f"<div style='font-size:2.8rem;line-height:1;margin-bottom:.15rem'>{flag}</div>"
            f"<div style='font-size:1.2rem;font-weight:900;color:white'>{team}</div>"
            f"{result_badge}"
            f"{avatars_html}"
            f"{pts_badge}{status_label}"
            f"</div>",
            unsafe_allow_html=True,
        )
        if not is_completed:
            btn = f"✅ Picked {team}" if picked_by_me else f"Pick {team}"
            if st.button(btn, key=f"pick_{match_id}_{team}", use_container_width=True):
                save_pick(active_user_id, match_id, team)
                st.rerun()


    def _sec_explore():
        xp_c1, xp_c2 = st.columns(2)
        with xp_c1:
            if st.button(f"🌎 Explore {home_team}", key="xp_home", use_container_width=True):
                st.session_state["_nav_country"] = home_team
                st.switch_page("pages/country_profile.py")
        with xp_c2:
            if st.button(f"🌎 Explore {away_team}", key="xp_away", use_container_width=True):
                st.session_state["_nav_country"] = away_team
                st.switch_page("pages/country_profile.py")


    def _sec_picks():
        st.divider()
        st.markdown('<div id="mu-picks" class="mu-section">🏷️ Family Picks</div>', unsafe_allow_html=True)
        home_col, away_col = st.columns(2)
        with home_col:
            _pick_card(home_team, home_flag, is_home=True)
        with away_col:
            _pick_card(away_team, away_flag, is_home=False)
        if is_completed:
            hs2, as2 = int(match['home_score']), int(match['away_score'])
            if hs2 > as2:   result_msg = f"**{home_team}** won {hs2}–{as2}. Points have been awarded."
            elif as2 > hs2: result_msg = f"**{away_team}** won {hs2}–{as2}. Points have been awarded."
            else:           result_msg = f"It finished {hs2}–{as2} — a draw! Everyone who picked earns 0.5 pts."
            st.caption(f"Final result — {result_msg}")
        else:
            st.caption("Tap your team to register your pick. No locking — you can change it any time.")


    def _sec_recap():
        st.divider()
        st.markdown('<div id="mu-recap" class="mu-section">📋 Match Recap</div>', unsafe_allow_html=True)
        recap = get_match_recap(home_team, away_team, match['match_date'])
        if recap["found"] and recap["key_events"]:
            events_html = ""
            for ev in recap["key_events"]:
                clock_str  = f"{ev['clock']}" if ev['clock'] else ""
                player_str = f"<span style='font-weight:700;color:white'>{ev['player']}</span>" if ev['player'] else ""
                team_str   = f"<span style='color:#94A3B8;font-size:.78rem'>· {ev['team']}</span>" if ev['team'] else ""
                events_html += (
                    f"<div style='display:flex;align-items:center;gap:.75rem;padding:.4rem 0;"
                    f"border-bottom:1px solid rgba(148,163,184,.1)'>"
                    f"<span style='font-size:.82rem;color:#64748B;min-width:2.8rem;text-align:right'>{clock_str}</span>"
                    f"<span style='font-size:1.3rem'>{ev['icon']}</span>"
                    f"{player_str} {team_str}"
                    f"</div>"
                )
            st.markdown(
                "<div style='background:linear-gradient(160deg,#0F172A,#1E293B);border-radius:14px;"
                "padding:1rem 1.2rem;border:1px solid rgba(148,163,184,.12);margin-bottom:.8rem'>"
                f"<div style='font-size:.72rem;color:#64748B;font-weight:700;text-transform:uppercase;"
                f"letter-spacing:.07em;margin-bottom:.5rem'>Scoring Events</div>"
                f"{events_html}"
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.caption("Match recap coming soon.")
        lnk1, lnk2, lnk3 = st.columns(3)
        with lnk1:
            st.link_button("🎥 Watch Highlights", recap["youtube_url"], use_container_width=True)
        with lnk2:
            st.link_button("📰 Match Coverage", recap["news_url"], use_container_width=True)
        with lnk3:
            st.link_button("⚽ FIFA Match Centre", recap["fifa_url"], use_container_width=True)


    def _sec_split():
        if home_picks_info and away_picks_info:
            h_avs = " ".join(
                f"<span style='font-size:1.6rem' title='{n}'>{av}</span>"
                for n, av in home_picks_info
            )
            a_avs = " ".join(
                f"<span style='font-size:1.6rem' title='{n}'>{av}</span>"
                for n, av in away_picks_info
            )
            st.markdown(
                f"<div style='background:rgba(30,58,95,.45);border:1px solid rgba(147,197,253,.15);"
                f"border-radius:12px;padding:.85rem 1.1rem;margin:.5rem 0'>"
                f"<div style='font-size:.8rem;font-weight:800;color:#93C5FD;margin-bottom:.55rem'>⚖️ Family Split</div>"
                f"<div style='display:flex;gap:2rem;flex-wrap:wrap'>"
                f"<div><div style='font-size:.85rem;font-weight:700;color:#F1F5F9'>{home_flag} {home_team}</div>"
                f"<div style='margin-top:.25rem'>{h_avs}</div></div>"
                f"<div><div style='font-size:.85rem;font-weight:700;color:#F1F5F9'>{away_flag} {away_team}</div>"
                f"<div style='margin-top:.25rem'>{a_avs}</div></div>"
                f"</div>"
                f"<div style='font-size:.72rem;color:#64748B;margin-top:.4rem'>"
                f"{len(home_picks_info)} vs {len(away_picks_info)}</div></div>",
                unsafe_allow_html=True,
            )
        elif home_picks_info or away_picks_info:
            winning_team = home_team if home_picks_info else away_team
            winning_flag = home_flag if home_picks_info else away_flag
            all_avs = " ".join(
                f"<span style='font-size:1.6rem' title='{n}'>{av}</span>"
                for n, av in (home_picks_info or away_picks_info)
            )
            st.markdown(
                f"<div style='background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.25);"
                f"border-radius:12px;padding:.85rem 1.1rem;margin:.5rem 0'>"
                f"<div style='font-size:.8rem;font-weight:800;color:#4ADE80;margin-bottom:.35rem'>👨‍👩‍👧‍👦 Family Consensus!</div>"
                f"<div style='font-size:1rem;color:#F1F5F9;font-weight:700'>Everyone picked {winning_flag} {winning_team}!</div>"
                f"<div style='margin-top:.35rem'>{all_avs}</div></div>",
                unsafe_allow_html=True,
            )


    def _sec_cheer(title: str, subtitle: str):
        st.divider()
        st.markdown(f'<div id="mu-cheer" class="mu-section">{title}</div>', unsafe_allow_html=True)
        st.caption(subtitle)

        def _cheer_col(team, flag, data):
            if data is None:
                return
            img = get_country_image_html(team, height='120px', border_radius='12px')
            if img:
                st.markdown(img, unsafe_allow_html=True)
            st.markdown(
                f"<div style='font-size:1.1rem;font-weight:800;margin:.4rem 0'>{flag} {team}</div>",
                unsafe_allow_html=True,
            )
            reasons = _parse_pipe(data.get('cheer_reasons'))
            if not reasons:
                st.caption("They're still awesome!")
                return
            cols = st.columns(min(len(reasons), 4))
            for i, reason in enumerate(reasons[:4]):
                parts = reason.rsplit(' ', 1)
                label, emoji = (parts[0].strip(), parts[1].strip()) if len(parts) == 2 else (reason, "⭐")
                with cols[i % len(cols)]:
                    st.markdown(
                        f"<div class='cheer-card'>"
                        f"<div style='font-size:2.2rem;line-height:1.1'>{emoji}</div>"
                        f"<div style='font-size:.82rem;font-weight:700;color:#F1F5F9;"
                        f"margin-top:.35rem;line-height:1.3'>{label}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        cheer_c1, cheer_c2 = st.columns(2)
        with cheer_c1:
            _cheer_col(home_team, home_flag, home_data)
        with cheer_c2:
            _cheer_col(away_team, away_flag, away_data)


    def _sec_comparison():
        st.divider()
        st.markdown('<div id="mu-compare" class="mu-section">🌍 Country Comparison</div>', unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        with cc1:
            _country_card(home_team, home_flag, home_data, pfx="gs_")
        with cc2:
            _country_card(away_team, away_flag, away_data, pfx="gs_")


    def _sec_roster():
        if not (h_featured or a_featured):
            return
        st.divider()
        st.markdown('<div class="mu-section">📋 Roster Snapshot</div>', unsafe_allow_html=True)
        h_rsc  = _roster_snapshot_card(home_team, home_flag, h_featured, h_sum)
        a_rsc  = _roster_snapshot_card(away_team, away_flag, a_featured, a_sum)
        vs_div = "<div style='display:flex;align-items:center;justify-content:center;color:#94A3B8;font-size:1.4rem;padding:0 .5rem'>🆚</div>"
        st.markdown(
            f"<div style='display:flex;gap:.5rem;align-items:stretch'>{h_rsc}{vs_div}{a_rsc}</div>",
            unsafe_allow_html=True,
        )


    def _sec_key_players():
        st.divider()
        st.markdown('<div id="mu-players" class="mu-section">⭐ Key Players</div>', unsafe_allow_html=True)
        st.caption("Tap any player to learn more.")
        kp_c1, kp_c2 = st.columns(2)
        for col, team, flag, featured in [
            (kp_c1, home_team, home_flag, h_featured),
            (kp_c2, away_team, away_flag, a_featured),
        ]:
            with col:
                st.markdown(
                    f"<div style='font-size:1rem;font-weight:800;margin-bottom:.4rem'>{flag} {team}</div>",
                    unsafe_allow_html=True,
                )
                if featured:
                    n = min(3, len(featured))
                    p_sub_cols = st.columns(n)
                    for pcol, p in zip(p_sub_cols, featured[:n]):
                        slug = get_player_slug(team, p['name'])
                        with pcol:
                            st.markdown(_player_trading_card(p), unsafe_allow_html=True)
                            if slug and st.button(
                                "👤 Learn More", key=f"mup_{slug}",
                                use_container_width=True,
                            ):
                                _show_player_modal(slug)
                else:
                    st.caption("Roster data unavailable.")


    def _sec_mls():
        if h_mls.empty and a_mls.empty:
            return
        st.divider()
        st.markdown('<div class="mu-section">🏟️ MLS & US Connections</div>', unsafe_allow_html=True)
        st.caption("Tap any player to learn more.")

        def _mls_callout(team, flag, mls_df):
            if mls_df.empty:
                return
            st.markdown(
                f"<div style='font-size:1rem;font-weight:800;margin-bottom:.4rem'>"
                f"{flag} {team} · {len(mls_df)} MLS Player{'s' if len(mls_df)!=1 else ''}</div>",
                unsafe_allow_html=True,
            )
            mls_sub = st.columns(min(len(mls_df), 3))
            for mcol, (_, p) in zip(mls_sub, mls_df.head(3).iterrows()):
                mls_slug = get_player_slug(team, p['player_name'])
                with mcol:
                    st.markdown(
                        "<div style='background:linear-gradient(135deg,#064E3B,#065F46);"
                        "border-radius:10px;padding:.65rem .9rem;color:white'>"
                        f"<div style='font-size:.95rem;font-weight:800'>#{int(p['shirt_number'])} {p['player_name']}</div>"
                        f"<div style='font-size:.78rem;color:#6EE7B7'>{p['position']}</div>"
                        f"<div style='font-size:.75rem;color:#A7F3D0'>🏟️ {p['club_short']} · Age {int(p['age'])}</div>"
                        "</div>",
                        unsafe_allow_html=True,
                    )
                    if mls_slug and st.button(
                        "👤 Learn More", key=f"mls_{mls_slug}",
                        use_container_width=True,
                    ):
                        _show_player_modal(mls_slug)

        mls_c1, mls_c2 = st.columns(2)
        with mls_c1:
            _mls_callout(home_team, home_flag, h_mls)
            if h_mls.empty:
                st.caption(f"No MLS players on {home_team}'s squad.")
        with mls_c2:
            _mls_callout(away_team, away_flag, a_mls)
            if a_mls.empty:
                st.caption(f"No MLS players on {away_team}'s squad.")


    def _sec_debate():
        st.divider()
        st.markdown('<div id="mu-debate" class="mu-section">💬 Family Debate Corner</div>', unsafe_allow_html=True)
        for card in debate_cards[:4]:
            c_color = card['color']
            st.markdown(
                f"<div style='background:var(--secondary-background-color);"
                f"border:1px solid rgba(148,163,184,.12);border-left:4px solid {c_color};"
                f"border-radius:12px;padding:1rem 1.1rem;margin:.4rem 0'>"
                f"<div style='font-size:1.1rem;font-weight:900;margin-bottom:.3rem'>{card['icon']} {card['title']}</div>"
                f"<div style='font-size:1rem;opacity:.85;margin:.2rem 0;line-height:1.45'>{card['body']}</div>"
                f"<div style='font-size:.95rem;font-weight:700;color:{c_color};margin-top:.4rem'>"
                f"💬 {card['question']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


    def _sec_host_city():
        st.divider()
        st.markdown('<div id="mu-city" class="mu-section">🏙️ Host City</div>', unsafe_allow_html=True)
        city_left, city_right = st.columns([3, 2])
        with city_left:
            st.markdown(
                "<div class='city-card'>"
                f"<div style='font-size:1.6rem;font-weight:900;margin-bottom:.1rem'>{city_flag} {city}</div>"
                f"<div style='color:#94A3B8;font-size:.82rem;margin-bottom:.6rem'>"
                f"🏟️ {match['venue']} · {match['host_country']}</div>"
                f"<div style='font-size:.95rem;color:#CBD5E1;line-height:1.6'>{city_fact}</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            if st.button("🏙️ Full City Guide", key="host_city_btn"):
                st.session_state["_nav_city"] = city
                st.switch_page("pages/host_cities.py")
        with city_right:
            city_img = get_country_image_html(match['host_country'], height='160px', border_radius='12px')
            if city_img:
                st.markdown(city_img, unsafe_allow_html=True)


    def _sec_result_moment():
        if not is_completed:
            return
        hs, as_ = int(match['home_score']), int(match['away_score'])

        pick_results: list[tuple] = []
        for _, pk in picks_df.iterrows():
            pts = _pick_result(pk['picked_team'], home_team, away_team,
                               match['home_score'], match['away_score'])
            pick_results.append((pk['user_name'], pk['avatar'], pk['picked_team'], pts))

        n_family  = len(pick_results)
        n_correct = sum(1 for _, _, _, pts in pick_results if pts == 1.0)

        user_pts  = None
        user_pick = None
        if not picks_df.empty:
            ur = picks_df[picks_df['user_name'] == active_user]
            if not ur.empty:
                user_pick = ur.iloc[0]['picked_team']
                user_pts  = _pick_result(user_pick, home_team, away_team,
                                         match['home_score'], match['away_score'])

        if hs > as_:
            result_label = f"🏆 {home_flag} {home_team} wins {hs}–{as_}"
            result_color = "#4ADE80"
        elif as_ > hs:
            result_label = f"🏆 {away_flag} {away_team} wins {hs}–{as_}"
            result_color = "#4ADE80"
        else:
            result_label = f"🤝 It's a Draw — {hs}–{as_}"
            result_color = "#FCD34D"

        if n_family == 0:
            family_msg = "No family picks were made."
            family_color = "#64748B"
        elif n_correct == n_family and hs != as_:
            family_msg = "🎉 Everyone got it right!"
            family_color = "#4ADE80"
        elif n_correct == 0 and hs != as_:
            family_msg = "😬 Tough one — no one predicted the winner."
            family_color = "#F87171"
        elif n_correct == 1:
            winner_name = next((n for n, _, _, pts in pick_results if pts == 1.0), "")
            family_msg  = f"⭐ Only {winner_name} got it right!"
            family_color = "#FCD34D"
        elif n_correct > 0:
            family_msg  = f"✅ {n_correct} / {n_family} family members got it right."
            family_color = "#86EFAC"
        else:
            all_draw = all(pts == 0.5 for _, _, _, pts in pick_results if pts is not None)
            family_msg = "🤝 Draw — everyone earns half a point!" if all_draw else "Check results below."
            family_color = "#FCD34D"

        if user_pts is None:
            user_line  = "You didn't make a pick for this match."
            user_color = "#64748B"
        elif user_pts == 1.0:
            user_pf    = get_flag(user_pick)
            user_line  = f"You picked {user_pf} {user_pick} and earned <b style='color:#4ADE80'>1 point</b>! 🎉"
            user_color = "#4ADE80"
        elif user_pts == 0.5:
            user_pf    = get_flag(user_pick)
            user_line  = f"You picked {user_pf} {user_pick} — draw! You earned <b style='color:#FCD34D'>0.5 points</b>."
            user_color = "#FCD34D"
        else:
            user_pf    = get_flag(user_pick) if user_pick else "❓"
            user_line  = f"You picked {user_pf} {user_pick} — they lost. No points this time."
            user_color = "#F87171"

        bg = "linear-gradient(135deg,#052e16,#14532d)" if hs != as_ else "linear-gradient(135deg,#1c1917,#292524)"
        st.markdown(
            f"<div style='background:{bg};border:2px solid {result_color};"
            f"border-radius:16px;padding:1.1rem 1.4rem;margin:.5rem 0'>"
            f"<div style='font-size:1.35rem;font-weight:900;color:{result_color};text-align:center;"
            f"margin-bottom:.5rem'>{result_label}</div>"
            f"<div style='border-top:1px solid rgba(255,255,255,.1);margin:.5rem 0'></div>"
            f"<div style='display:flex;gap:1.5rem;flex-wrap:wrap'>"
            f"<div style='flex:1;min-width:180px'>"
            f"<div style='font-size:.68rem;font-weight:800;color:#64748B;text-transform:uppercase;"
            f"letter-spacing:.06em;margin-bottom:.3rem'>Family Result</div>"
            f"<div style='font-size:.92rem;font-weight:700;color:{family_color}'>{family_msg}</div>"
            f"</div>"
            f"<div style='flex:1;min-width:180px'>"
            f"<div style='font-size:.68rem;font-weight:800;color:#64748B;text-transform:uppercase;"
            f"letter-spacing:.06em;margin-bottom:.3rem'>Your Result</div>"
            f"<div style='font-size:.92rem;color:{user_color}'>{user_line}</div>"
            f"</div>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


    def _sec_stakes():
        if is_completed:
            return
        group_letter = str(match.get('group_letter', '') or '')
        if not group_letter:
            return

        h_stat = get_team_group_status(home_team, group_letter)
        a_stat = get_team_group_status(away_team, group_letter)

        h_played = h_stat.get('played', 0)
        a_played = a_stat.get('played', 0)
        max_played = max(h_played, a_played)

        h_status = h_stat.get('status', '')
        a_status = a_stat.get('status', '')
        h_pts    = h_stat.get('pts', 0)
        a_pts    = a_stat.get('pts', 0)
        h_w      = h_stat.get('w', 0)
        a_w      = a_stat.get('w', 0)
        h_d      = h_stat.get('d', 0)
        a_d      = a_stat.get('d', 0)

        def _is_advanced(s):   return "Advanced" in s or "Locked" in s
        def _is_eliminated(s): return "Eliminated" in s or s.startswith("❌")
        def _is_good(s):       return "good shape" in s
        def _needs_help(s):    return "Needs help" in s

        if h_played == 0 and a_played == 0:
            stake_line = f"First match of Group {group_letter} — everything is still possible."
        elif max_played >= 2:
            if _is_advanced(h_status) and _is_advanced(a_status):
                stake_line = "Both teams have already advanced! This match determines group seeding."
            elif _is_eliminated(h_status) and _is_eliminated(a_status):
                stake_line = "Both teams have been eliminated. Pride is still on the line."
            elif _is_advanced(h_status):
                stake_line = f"{home_team} is already through. {away_team} needs a result to advance."
            elif _is_advanced(a_status):
                stake_line = f"{away_team} is already through. {home_team} needs a result to advance."
            elif _is_eliminated(h_status):
                stake_line = f"{home_team} is out. {away_team} plays to secure their last-chance result."
            elif _is_eliminated(a_status):
                stake_line = f"{away_team} is out. {home_team} plays to secure their last-chance result."
            else:
                stake_line = "This is the last group game — every single point matters."
        else:
            if _is_advanced(h_status) and _is_advanced(a_status):
                stake_line = "Both teams have already advanced! This match determines group seeding."
            elif _is_advanced(h_status):
                stake_line = f"{home_team} has already advanced. {away_team} is still fighting for their spot."
            elif _is_advanced(a_status):
                stake_line = f"{away_team} has already advanced. {home_team} is still fighting for their spot."
            elif _is_eliminated(h_status) and _is_eliminated(a_status):
                stake_line = "Both teams have been eliminated. Pride is still on the line."
            elif _is_eliminated(h_status):
                stake_line = f"{home_team} has been eliminated. {away_team} still has something to play for."
            elif _is_eliminated(a_status):
                stake_line = f"{away_team} has been eliminated. {home_team} still has something to play for."
            elif h_pts == 3 and a_pts == 3:
                stake_line = f"Both teams won their opening match — a battle for the top of Group {group_letter}."
            elif h_w == 1 and a_w == 1:
                stake_line = "Both teams are 1 win and 1 loss — this match could decide who advances."
            elif h_d == 1 and a_d == 1:
                stake_line = f"Both teams are unbeaten — the winner could take control of Group {group_letter}."
            elif h_pts == 0 and a_pts == 0:
                stake_line = "Both teams are still looking for their first win — a must-win match."
            elif _is_good(h_status) and _is_good(a_status):
                stake_line = "Both teams are in good shape — a win here cements their place in the Round of 32."
            elif _needs_help(h_status) and _needs_help(a_status):
                stake_line = "Both teams are in trouble — they need a result to stay alive."
            elif _needs_help(h_status):
                stake_line = f"{home_team} needs help to stay alive — a loss here could end their tournament."
            elif _needs_help(a_status):
                stake_line = f"{away_team} needs help to stay alive — a loss here could end their tournament."
            else:
                stake_line = f"Both teams are trying to set themselves up for the final group game."

        def _team_stake_card(team, flag, stat):
            pos     = stat.get('position', 0)
            pts     = stat.get('pts', 0)
            record  = stat.get('record', '—')
            status  = stat.get('status', '—')
            s_color = stat.get('status_color', '#94A3B8')
            pos_ord = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(pos, "—")
            return (
                f"<div style='flex:1;min-width:160px;background:rgba(15,23,42,.5);"
                f"border-radius:12px;padding:.75rem .9rem;border:1px solid rgba(148,163,184,.12)'>"
                f"<div style='font-size:1.5rem;line-height:1;margin-bottom:.2rem'>{flag}</div>"
                f"<div style='font-size:.88rem;font-weight:900;color:#F1F5F9;margin-bottom:.2rem'>{team}</div>"
                f"<div style='font-size:.78rem;color:#94A3B8'>{pos_ord} · {pts} pts · {record}</div>"
                f"<div style='font-size:.82rem;font-weight:800;color:{s_color};margin-top:.3rem'>{status}</div>"
                f"</div>"
            )

        h_card = _team_stake_card(home_team, home_flag, h_stat)
        a_card = _team_stake_card(away_team, away_flag, a_stat)

        st.markdown(
            f"<div style='background:linear-gradient(135deg,#1E293B,#0F172A);"
            f"border:1px solid rgba(251,191,36,.2);border-left:4px solid #F59E0B;"
            f"border-radius:14px;padding:.9rem 1.1rem;margin:.5rem 0'>"
            f"<div style='font-size:.68rem;font-weight:800;color:#D97706;text-transform:uppercase;"
            f"letter-spacing:.07em;margin-bottom:.5rem'>⚡ What's at Stake — Group {group_letter}</div>"
            f"<div style='font-size:.92rem;color:#CBD5E1;margin-bottom:.6rem;line-height:1.45'>{stake_line}</div>"
            f"<div style='display:flex;gap:.6rem;flex-wrap:wrap'>{h_card}{a_card}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Explore buttons ───────────────────────────────────────────────────────
    _sec_explore()

    # ── Quick nav chips ───────────────────────────────────────────────────────
    if is_completed:
        _nav_chips = [
            ("#mu-result",  "📊 Result"),
            ("#mu-picks",   "🏷️ Picks"),
            ("#mu-recap",   "📋 Recap"),
            ("#mu-players", "⭐ Players"),
            ("#mu-compare", "🌍 Compare"),
            ("#mu-city",    "🏙️ City"),
        ]
    else:
        _nav_chips = [
            ("#mu-stakes",  "⚡ Stakes"),
            ("#mu-picks",   "🏷️ Picks"),
            ("#mu-cheer",   "🤔 Cheer For"),
            ("#mu-players", "⭐ Players"),
            ("#mu-compare", "🌍 Compare"),
            ("#mu-debate",  "💬 Debate"),
            ("#mu-city",    "🏙️ City"),
        ]
    st.markdown(
        "<div style='display:flex;flex-wrap:wrap;gap:.3rem;margin:.4rem 0 .2rem'>"
        + "".join(f"<a href='{h}' class='mu-chip'>{l}</a>" for h, l in _nav_chips)
        + "</div>",
        unsafe_allow_html=True,
    )

    # ── Status-aware section order ────────────────────────────────────────────
    if is_completed:
        st.markdown('<div id="mu-result"></div>', unsafe_allow_html=True)
        _sec_result_moment()
        _sec_picks()
        _sec_recap()
        _sec_split()
        _sec_comparison()
        _sec_roster()
        _sec_key_players()
        _sec_mls()
        _sec_host_city()
        _sec_cheer(
            "🌎 Learn More About These Countries",
            "The match is over, but these countries are still fun to explore.",
        )
    else:
        st.markdown('<div id="mu-stakes"></div>', unsafe_allow_html=True)
        _sec_stakes()
        _sec_picks()
        _sec_cheer(
            "🤔 Who Should I Cheer For?",
            "Pick your side! Here's why you might love each team…",
        )
        _sec_split()
        _sec_comparison()
        _sec_roster()
        _sec_key_players()
        _sec_mls()
        _sec_debate()
        _sec_host_city()
