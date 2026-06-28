"""Knockout match page — game-day program for a single KO match."""
import streamlit as st
from services.ko_picks import (
    get_all_ko_matches_display,
    get_ko_picks_for_match,
    save_ko_pick,
    get_ko_pick,
    KO_ROUND_LABELS,
    KO_ROUND_POINTS,
)
from services.teams import get_flag
from services.time_utils import fmt_match_time
from services.images import get_country_image_html

st.set_page_config(layout="wide")

active_user_id   = st.session_state.get("active_user_id", 1)
active_user_name = st.session_state.get("active_user_name", "You")
active_avatar    = st.session_state.get("active_user_avatar", "⚽")

# ── Resolve match ─────────────────────────────────────────────────────────────

try:
    qp = st.query_params.get("match_id")
    target_id = int(qp) if qp else None
except (ValueError, TypeError):
    target_id = None

all_ko = get_all_ko_matches_display()
# exclude 3rd place from navigation
nav_ko = [km for km in all_ko if km["id"] != 131]

if not nav_ko:
    st.info("No knockout matches available yet.")
    st.stop()

# Default to first scheduled or last completed
if target_id is None:
    scheduled = [km for km in nav_ko if km["status"] == "scheduled"]
    target_id = scheduled[0]["id"] if scheduled else nav_ko[-1]["id"]

km = next((m for m in nav_ko if m["id"] == target_id), nav_ko[0])

# ── Match selector ────────────────────────────────────────────────────────────

_sel_options = {
    m["id"]: (
        f"{KO_ROUND_LABELS.get(m['round'], m['round'])} — "
        f"{m.get('home_flag','')} {m.get('home_name') or 'TBD'} vs "
        f"{m.get('away_name') or 'TBD'} {m.get('away_flag','')}"
    )
    for m in nav_ko
}
_sel_val = st.selectbox(
    "Match",
    options=list(_sel_options.keys()),
    format_func=lambda k: _sel_options[k],
    index=list(_sel_options.keys()).index(km["id"]),
    label_visibility="collapsed",
    key="ko_matchup_sel",
)
if _sel_val != km["id"]:
    st.query_params["match_id"] = str(_sel_val)
    st.rerun()

# ── Data ──────────────────────────────────────────────────────────────────────

mid        = km["id"]
rnd        = km["round"]
home_name  = km.get("home_name") or "TBD"
away_name  = km.get("away_name") or "TBD"
home_flag  = km.get("home_flag") or "⬜"
away_flag  = km.get("away_flag") or "⬜"
home_id    = km.get("home_team_id")
away_id    = km.get("away_team_id")
is_done    = km["status"] == "completed"
pts_val    = KO_ROUND_POINTS.get(rnd, 0)
rnd_lbl    = KO_ROUND_LABELS.get(rnd, rnd)
time_str   = fmt_match_time(km["match_date"], km.get("kickoff_time_et", ""))
ko_picks   = get_ko_picks_for_match(mid)
my_pick_id = get_ko_pick(active_user_id, mid) if home_id and away_id else None

# ── Hero header ───────────────────────────────────────────────────────────────

hs_str = f"{int(km['home_score'])}–{int(km['away_score'])}" if is_done and km.get("home_score") is not None else "vs"

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
    f"+{pts_val} pts</span></div>"
    f"<div style='font-size:3rem;margin:.1rem 0'>{home_flag}&nbsp;&nbsp;{away_flag}</div>"
    f"<div style='font-size:1.4rem;font-weight:900;color:#F1F5F9'>"
    f"{home_name} "
    f"<span style='color:#FCD34D;font-size:1.2rem'>{hs_str}</span>"
    f" {away_name}</div>"
    f"<div style='font-size:.78rem;color:#94A3B8;margin-top:.2rem'>"
    f"🕒 {time_str} · 🏟️ {km.get('venue', '')} · 📍 {km.get('city', '')}</div>"
    "</div></div>",
    unsafe_allow_html=True,
)

# ── Family picks ──────────────────────────────────────────────────────────────

st.markdown(
    "<div style='font-size:1rem;font-weight:800;color:#F1F5F9;margin:.6rem 0 .25rem'>"
    "🏟️ Family Picks</div>",
    unsafe_allow_html=True,
)

home_pickers = [p for p in ko_picks if p["picked_team_id"] == home_id]
away_pickers = [p for p in ko_picks if p["picked_team_id"] == away_id]
winner_id    = km.get("winner_team_id")


def _av_pills(pickers: list[dict]) -> str:
    if not pickers:
        return "<span style='color:#4B5563;font-size:.78rem'>No picks yet</span>"
    parts = []
    for p in pickers:
        tc = p.get("theme_color") or "#94A3B8"
        is_winner = is_done and winner_id and p["picked_team_id"] == winner_id
        suffix = f"+{pts_val}" if is_winner else ("+0" if is_done else "")
        sc = "#4ADE80" if is_winner else ("#F87171" if is_done else tc)
        if not isinstance(tc, str) or not tc.startswith("#"):
            tc = "#94A3B8"
        parts.append(
            f"<span style='background:rgba(128,128,128,.12);color:{sc};"
            f"border-radius:20px;padding:.07rem .5rem;font-size:.85rem;"
            f"font-weight:700;display:inline-block;margin:.04rem'>"
            f"{p['avatar']}&nbsp;{p['name']}"
            + (f"&nbsp;<b>{suffix}</b>" if suffix else "")
            + "</span>"
        )
    return "".join(parts)


picks_col_l, picks_col_r = st.columns(2)
with picks_col_l:
    st.markdown(
        f"<div style='border-radius:10px;padding:.5rem .7rem;"
        f"background:rgba(148,163,184,.07);min-height:60px'>"
        f"<div style='font-size:.75rem;font-weight:700;color:#94A3B8;margin-bottom:.2rem'>"
        f"{home_flag} {home_name}</div>"
        f"<div style='display:flex;flex-wrap:wrap'>{_av_pills(home_pickers)}</div></div>",
        unsafe_allow_html=True,
    )
with picks_col_r:
    st.markdown(
        f"<div style='border-radius:10px;padding:.5rem .7rem;"
        f"background:rgba(148,163,184,.07);min-height:60px'>"
        f"<div style='font-size:.75rem;font-weight:700;color:#94A3B8;margin-bottom:.2rem'>"
        f"{away_flag} {away_name}</div>"
        f"<div style='display:flex;flex-wrap:wrap'>{_av_pills(away_pickers)}</div></div>",
        unsafe_allow_html=True,
    )

# ── Pick buttons ─────────────────────────────────────────────────────────────

if home_id and away_id and not is_done:
    st.markdown(
        f"<div style='font-size:.78rem;color:#94A3B8;margin:.5rem 0 .15rem'>"
        f"Pick as {active_avatar} {active_user_name}</div>",
        unsafe_allow_html=True,
    )
    _pc1, _pc2 = st.columns(2)
    with _pc1:
        _h_type = "primary" if my_pick_id == home_id else "secondary"
        if st.button(f"{home_flag} {home_name}", type=_h_type,
                     key=f"kmp_h_{mid}", use_container_width=True):
            try:
                save_ko_pick(active_user_id, mid, home_id)
                st.rerun()
            except Exception as e:
                st.error(str(e))
    with _pc2:
        _a_type = "primary" if my_pick_id == away_id else "secondary"
        if st.button(f"{away_flag} {away_name}", type=_a_type,
                     key=f"kmp_a_{mid}", use_container_width=True):
            try:
                save_ko_pick(active_user_id, mid, away_id)
                st.rerun()
            except Exception as e:
                st.error(str(e))

elif is_done and km.get("winner_name"):
    st.success(f"🏆 {km['winner_name']} advances!")

st.divider()

# ── Country exploration links ─────────────────────────────────────────────────

st.markdown(
    "<div style='font-size:1rem;font-weight:800;color:#F1F5F9;margin-bottom:.35rem'>"
    "🌍 Explore These Countries</div>",
    unsafe_allow_html=True,
)
_exp_c1, _exp_c2 = st.columns(2)
with _exp_c1:
    if home_name != "TBD":
        st.page_link(
            "pages/country_profile.py",
            label=f"{home_flag} {home_name}",
            icon="🗺️",
        )
with _exp_c2:
    if away_name != "TBD":
        st.page_link(
            "pages/country_profile.py",
            label=f"{away_flag} {away_name}",
            icon="🗺️",
        )
