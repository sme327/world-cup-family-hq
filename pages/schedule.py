import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from services.matches import get_all_matches
from services.teams import get_all_teams, get_all_group_letters, get_flag
from services.picks import get_all_picks, get_all_users, save_pick
from services.time_utils import fmt_match_time, fmt_date, pt_date_str, et_to_pt
from services.ko_picks import (
    get_all_ko_matches_display,
    get_ko_pick,
    get_ko_picks_for_match,
    save_ko_pick,
    KO_ROUND_LABELS,
    KO_ROUND_POINTS,
)

# ── Page CSS ───────────────────────────────────────────────────────────────────
st.markdown("""<style>
.sect-hdr {
    font-size:1rem;font-weight:900;letter-spacing:.07em;text-transform:uppercase;
    padding:.38rem .9rem;border-radius:8px;margin:1.2rem 0 .4rem;display:inline-block;
    box-shadow:0 1px 4px rgba(0,0,0,.25);
}
.sect-live     { background:linear-gradient(90deg,#7F1D1D,#991B1B);color:#FCA5A5; }
.sect-upcoming { background:linear-gradient(90deg,#1E3A5F,#1E40AF);color:#BAE6FD; }
.sect-final    { background:rgba(255,255,255,.05);color:#64748B;border:1px solid rgba(255,255,255,.07); }
.live-badge {
    background:#DC2626;color:white;border-radius:20px;padding:.1rem .5rem;
    font-size:.7rem;font-weight:800;letter-spacing:.06em;animation:pulse 1.4s infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.6} }
/* ── Quick nav chips ──────────────────────────────── */
a.nav-chip {
    display:inline-block;padding:.28rem .78rem;border-radius:20px;
    background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);
    color:#CBD5E1;font-size:.83rem;font-weight:700;text-decoration:none;
    white-space:nowrap;
}
a.nav-chip:hover { background:rgba(255,255,255,.15);color:white; }
</style>""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
_GRP_COLORS = {
    'A': '#1D4ED8', 'B': '#15803D', 'C': '#B45309', 'D': '#7C3AED',
    'E': '#BE123C', 'F': '#0F766E', 'G': '#9A3412', 'H': '#1E40AF',
    'I': '#4D7C0F', 'J': '#6D28D9', 'K': '#0E7490', 'L': '#92400E',
}

now_pt       = datetime.utcnow() - timedelta(hours=7)
today_pt     = now_pt.date().isoformat()
tomorrow_pt  = (now_pt.date() + timedelta(days=1)).isoformat()


# ── Group-stage helpers ────────────────────────────────────────────────────────

def _grp_badge(letter: str) -> str:
    c = _GRP_COLORS.get(letter, '#374151')
    return (f"<span style='background:{c};color:white;border-radius:4px;"
            f"padding:.07rem .3rem;font-size:.68rem;font-weight:800;"
            f"letter-spacing:.04em'>Group {letter}</span>")

def _pick_pts(picked: str, m) -> float | None:
    if str(m['status']) != 'completed':
        return None
    hs, as_ = int(m['home_score']), int(m['away_score'])
    if hs == as_:
        return 0.5
    return 1.0 if picked == (m['home_team'] if hs > as_ else m['away_team']) else 0.0

def _is_live(m) -> bool:
    if str(m['status']) != 'scheduled':
        return False
    kickoff = et_to_pt(str(m['match_date']), str(m['kickoff_time_et']))
    elapsed = (now_pt - kickoff).total_seconds() / 60
    return 0 < elapsed < 115

def _picks_for(mid: int, picks_df: pd.DataFrame) -> pd.DataFrame:
    if picks_df.empty:
        return pd.DataFrame()
    return picks_df[picks_df['match_id'] == mid]

def _sticker_block(team: str, match_picks: pd.DataFrame, flag: str) -> str:
    pickers = match_picks[match_picks['picked_team'] == team]
    avs = "".join(
        f"<span style='font-size:1.4rem'>{pk['avatar']}</span>"
        for _, pk in pickers.iterrows()
    )
    if not avs:
        avs = "<span style='color:#374151;font-size:.8rem'>—</span>"
    short = team[:12] + ("…" if len(team) > 12 else "")
    return (
        f"<div style='text-align:center;min-width:80px'>"
        f"<div style='font-size:.7rem;color:#64748B;margin-bottom:.15rem'>{flag} {short}</div>"
        f"<div style='line-height:1.3'>{avs}</div>"
        f"</div>"
    )

def _consensus_html(m, match_picks: pd.DataFrame) -> str:
    if match_picks.empty:
        return ""
    h_cnt = int((match_picks['picked_team'] == m['home_team']).sum())
    a_cnt = int((match_picks['picked_team'] == m['away_team']).sum())
    total = int(len(match_picks))
    if total == 0:
        return ""
    if h_cnt == a_cnt:
        verdict = f"⚖️ <b>Split decision</b> &nbsp;{h_cnt}–{a_cnt}"
        vc = "#FCD34D"
    elif h_cnt > a_cnt:
        verdict = f"👨‍👩‍👧‍👦 <b>{m['home_team']}</b> ({h_cnt}/{total})"
        vc = "#93C5FD"
    else:
        verdict = f"👨‍👩‍👧‍👦 <b>{m['away_team']}</b> ({a_cnt}/{total})"
        vc = "#93C5FD"
    upset = ""
    if total > 1:
        if h_cnt == 1:
            solo = match_picks[match_picks['picked_team'] == m['home_team']]['user_name'].iloc[0]
            upset = f"<div style='font-size:.72rem;color:#FB923C;margin-top:.1rem'>⚠️ Only {solo} picked {m['home_team']}</div>"
        elif a_cnt == 1:
            solo = match_picks[match_picks['picked_team'] == m['away_team']]['user_name'].iloc[0]
            upset = f"<div style='font-size:.72rem;color:#FB923C;margin-top:.1rem'>⚠️ Only {solo} picked {m['away_team']}</div>"
    return (
        f"<div style='text-align:center;margin-top:.25rem'>"
        f"<div style='font-size:.78rem;color:{vc}'>{verdict}</div>"
        f"{upset}</div>"
    )

def _family_accuracy_html(m, match_picks: pd.DataFrame) -> str:
    if match_picks.empty or str(m['status']) != 'completed':
        return ""
    correct = sum(
        1 for _, pk in match_picks.iterrows()
        if (_pick_pts(pk['picked_team'], m) or 0) > 0
    )
    total = len(match_picks)
    if total == 0:
        return ""
    pct = int(100 * correct / total)
    color = "#4ADE80" if pct >= 60 else "#FCD34D" if pct >= 34 else "#F87171"
    return f"<span style='color:{color};font-size:.72rem'>🎯 {correct}/{total} correct</span>"

def _compact_picks_row(m, match_picks: pd.DataFrame) -> str:
    if match_picks.empty:
        return ""
    hf = get_flag(m['home_team'])
    af = get_flag(m['away_team'])
    home_pks = match_picks[match_picks['picked_team'] == m['home_team']]
    away_pks = match_picks[match_picks['picked_team'] == m['away_team']]
    h_avs = "".join(f"<span style='font-size:1.05rem'>{pk['avatar']}</span>" for _, pk in home_pks.iterrows())
    a_avs = "".join(f"<span style='font-size:1.05rem'>{pk['avatar']}</span>" for _, pk in away_pks.iterrows())
    parts = []
    if h_avs:
        parts.append(f"{h_avs}&thinsp;{hf}")
    if a_avs:
        parts.append(f"{a_avs}&thinsp;{af}")
    return " &nbsp;·&nbsp; ".join(parts)


# ── Knockout helpers ───────────────────────────────────────────────────────────

_KO_ROUND_COLOR = {
    "r32":         "#1E3A5F",
    "r16":         "#14532D",
    "qf":          "#3B1A6B",
    "sf":          "#7C2D12",
    "third_place": "#374151",
    "final":       "#78350F",
}
_KO_ROUND_TEXT = {
    "r32":         "#BAE6FD",
    "r16":         "#BBF7D0",
    "qf":          "#DDD6FE",
    "sf":          "#FED7AA",
    "third_place": "#CBD5E1",
    "final":       "#FDE68A",
}


def _ko_round_badge(rnd: str) -> str:
    bg  = _KO_ROUND_COLOR.get(rnd, "#374151")
    col = _KO_ROUND_TEXT.get(rnd, "#E2E8F0")
    lbl = KO_ROUND_LABELS.get(rnd, rnd)
    pts = KO_ROUND_POINTS.get(rnd, 0)
    return (
        f"<span style='background:{bg};color:{col};border-radius:4px;"
        f"padding:.07rem .35rem;font-size:.68rem;font-weight:800;"
        f"letter-spacing:.04em'>{lbl}</span>"
        f"<span style='font-size:.65rem;color:#64748B;margin-left:.35rem'>+{pts} pts</span>"
    )


def _ko_sticker_block(team_id: int | None, team_name: str, team_flag: str, picks: list[dict]) -> str:
    pickers = [p for p in picks if p["picked_team_id"] == team_id] if team_id else []
    avs = "".join(
        f"<span style='font-size:1.3rem'>{p['avatar']}</span>"
        for p in pickers
    )
    if not avs:
        avs = "<span style='color:#374151;font-size:.8rem'>—</span>"
    short = (team_name or "TBD")[:12] + ("…" if len(team_name or "TBD") > 12 else "")
    flag  = team_flag or "⬜"
    return (
        f"<div style='text-align:center;min-width:80px'>"
        f"<div style='font-size:.7rem;color:#64748B;margin-bottom:.15rem'>{flag} {short}</div>"
        f"<div style='line-height:1.3'>{avs}</div>"
        f"</div>"
    )


def _render_ko_card(km: dict) -> None:
    mid       = km["id"]
    rnd       = km["round"]
    home_id   = km["home_team_id"]
    away_id   = km["away_team_id"]
    home_name = km["home_name"] or "TBD"
    away_name = km["away_name"] or "TBD"
    home_flag = km["home_flag"] or "⬜"
    away_flag = km["away_flag"] or "⬜"
    status    = km["status"]
    time_str  = fmt_match_time(km["match_date"], km["kickoff_time_et"])

    user_ko_pick    = get_ko_pick(active_user_id, mid) if (home_id and away_id) else None
    ko_family_picks = get_ko_picks_for_match(mid) if (home_id and away_id) else []

    both_known = bool(home_id and away_id)
    is_done    = (status == "completed")
    can_pick   = both_known and not is_done

    sticker = (
        f"<div style='display:flex;justify-content:center;gap:1.5rem;margin:.2rem 0'>"
        f"{_ko_sticker_block(home_id, home_name, home_flag, ko_family_picks)}"
        f"{_ko_sticker_block(away_id, away_name, away_flag, ko_family_picks)}"
        f"</div>"
        if ko_family_picks else
        f"<div style='text-align:center;margin:.2rem 0;font-size:.72rem;color:#374151'>"
        + ("🗳️ Picks Open" if can_pick else ("⏳ Teams TBD" if not both_known else ""))
        + "</div>"
    )

    score_line = ""
    if is_done and km.get("home_score") is not None:
        score_line = (
            f"<div style='font-size:.82rem;color:#FCD34D;font-weight:700;margin:.1rem 0'>"
            f"{int(km['home_score'])} – {int(km['away_score'])}"
            f"{'  🏆 ' + (km.get('winner_name') or '') if km.get('winner_name') else ''}"
            f"</div>"
        )

    with st.container(border=True):
        st.markdown(
            f"<div style='text-align:center;padding:.1rem 0'>"
            f"<div style='margin-bottom:.15rem'>{_ko_round_badge(rnd)}</div>"
            f"<div style='font-size:2.6rem;line-height:1.05'>{home_flag}&nbsp;&nbsp;{away_flag}</div>"
            f"<div style='font-size:1rem;font-weight:900;color:#F1F5F9;margin:.15rem 0'>"
            f"{home_name} &nbsp;<span style='opacity:.4;font-weight:300'>vs</span>&nbsp; {away_name}"
            f"</div>"
            f"{score_line}"
            f"<div style='font-size:.73rem;color:#94A3B8'>🕒 {time_str} &nbsp;·&nbsp; 🏟️ {km['venue']}</div>"
            f"<div style='font-size:.68rem;color:#64748B'>📍 {km['city']}, {km['host_country']}</div>"
            f"</div>"
            f"{sticker}"
            f"<hr style='border:none;border-top:1px solid rgba(148,163,184,.15);margin:.35rem 0'>",
            unsafe_allow_html=True,
        )
        b1, b2 = st.columns(2)
        with b1:
            h_picked = user_ko_pick == home_id
            h_label  = f"✅ {home_name}" if h_picked else home_name
            if st.button(h_label, key=f"ko_{mid}_h", use_container_width=True, disabled=not can_pick):
                if can_pick and not h_picked:
                    try:
                        save_ko_pick(active_user_id, mid, home_id)
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
        with b2:
            a_picked = user_ko_pick == away_id
            a_label  = f"✅ {away_name}" if a_picked else away_name
            if st.button(a_label, key=f"ko_{mid}_a", use_container_width=True, disabled=not can_pick):
                if can_pick and not a_picked:
                    try:
                        save_ko_pick(active_user_id, mid, away_id)
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))


# ── Upcoming card (group stage) ────────────────────────────────────────────────

def _render_upcoming_card(m, picks_df: pd.DataFrame) -> None:
    mid      = int(m['id'])
    hf       = get_flag(m['home_team'])
    af       = get_flag(m['away_team'])
    time_str = fmt_match_time(m['match_date'], m['kickoff_time_et'])
    mp       = _picks_for(mid, picks_df)
    user_pick_row = mp[mp['user_name'] == active_user] if not mp.empty else pd.DataFrame()
    user_pick     = user_pick_row['picked_team'].iloc[0] if not user_pick_row.empty else None

    sticker = (
        f"<div style='display:flex;justify-content:center;gap:1.5rem;margin:.2rem 0'>"
        f"{_sticker_block(m['home_team'], mp, hf)}"
        f"{_sticker_block(m['away_team'], mp, af)}"
        f"</div>"
        if not mp.empty else
        f"<div style='text-align:center;margin:.2rem 0;"
        f"font-size:.72rem;color:#374151'>🗳️ Picks Open</div>"
    )
    consensus = _consensus_html(m, mp)

    with st.container(border=True):
        st.markdown(
            f"<div style='text-align:center;padding:.1rem 0'>"
            f"<div style='margin-bottom:.15rem'>{_grp_badge(m['group_letter'])}"
            f"<span style='font-size:.65rem;color:#64748B'>⏰ Upcoming</span></div>"
            f"<div style='font-size:2.8rem;line-height:1.05'>{hf}&nbsp;&nbsp;{af}</div>"
            f"<div style='font-size:1rem;font-weight:900;color:#F1F5F9;margin:.15rem 0'>"
            f"{m['home_team']} &nbsp;<span style='opacity:.4;font-weight:300'>vs</span>&nbsp; {m['away_team']}"
            f"</div>"
            f"<div style='font-size:.73rem;color:#94A3B8'>🕒 {time_str} &nbsp;·&nbsp; 🏟️ {m['venue']}</div>"
            f"<div style='font-size:.68rem;color:#64748B'>📍 {m['city']}, {m['host_country']}</div>"
            f"</div>"
            f"{sticker}{consensus}"
            f"<hr style='border:none;border-top:1px solid rgba(148,163,184,.15);margin:.35rem 0'>",
            unsafe_allow_html=True,
        )
        b1, b2, b3 = st.columns([2, 2, 3])
        with b1:
            lbl = f"✅ {m['home_team']}" if user_pick == m['home_team'] else m['home_team']
            if st.button(lbl, key=f"up_{mid}_h", use_container_width=True):
                save_pick(active_user_id, mid, m['home_team'])
                st.rerun()
        with b2:
            lbl = f"✅ {m['away_team']}" if user_pick == m['away_team'] else m['away_team']
            if st.button(lbl, key=f"up_{mid}_a", use_container_width=True):
                save_pick(active_user_id, mid, m['away_team'])
                st.rerun()
        with b3:
            if st.button("📖 Match Preview", key=f"up_mc_{mid}", use_container_width=True):
                st.session_state["_nav_match_id"] = mid
                st.switch_page("pages/matchup.py")


# ── Session state (must be before helper calls that read active_user_id) ───────
active_user    = st.session_state.get("active_user_name",   "Shawn")
active_user_id = st.session_state.get("active_user_id",     1)
active_avatar  = st.session_state.get("active_user_avatar", "🐘")
users          = get_all_users()
n_fam          = len(users)

# ── Shared data (used by both tabs) ───────────────────────────────────────────
all_matches = get_all_matches()
picks_df    = get_all_picks()

all_matches['pt_date'] = all_matches.apply(
    lambda r: pt_date_str(r['match_date'], r['kickoff_time_et']), axis=1
)

# KO data
try:
    _ko_all     = get_all_ko_matches_display()
    _ko_matches = [km for km in _ko_all if km["id"] != 131]
    _has_ko     = bool(_ko_matches)
except Exception:
    _ko_matches = []
    _has_ko     = False

# ── Page header ────────────────────────────────────────────────────────────────
st.markdown("## 📅 Match Schedule")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_ko, tab_grp = st.tabs(["⚽ Knockout", "🌍 Group Stage"])


# ══════════════════════════════════════════════════════════════════════════════
# ⚽ KNOCKOUT TAB
# ══════════════════════════════════════════════════════════════════════════════

with tab_ko:
    if not _has_ko:
        st.info("The knockout stage begins June 28 — check back soon! 🏆")
    else:
        st.caption("Round of 32 → Final · June 28 – July 19, 2026 · All times Pacific")

        _ko_round_order = ["r32", "r16", "qf", "sf", "final"]
        for _rnd in _ko_round_order:
            _rnd_matches = [km for km in _ko_matches if km["round"] == _rnd]
            if not _rnd_matches:
                continue

            _rnd_lbl = KO_ROUND_LABELS.get(_rnd, _rnd)
            st.markdown(
                f"<div id='ko-{_rnd}' style='font-size:.9rem;font-weight:800;color:#94A3B8;"
                f"letter-spacing:.03em;margin:.8rem 0 .2rem'>🏆 {_rnd_lbl}</div>",
                unsafe_allow_html=True,
            )

            for _i in range(0, len(_rnd_matches), 2):
                if _i + 1 < len(_rnd_matches):
                    _ka, _kb = st.columns(2, gap="medium")
                    with _ka:
                        _render_ko_card(_rnd_matches[_i])
                    with _kb:
                        _render_ko_card(_rnd_matches[_i + 1])
                else:
                    if _rnd == "final":
                        _, _fc, _ = st.columns([1, 2, 1])
                        with _fc:
                            _render_ko_card(_rnd_matches[_i])
                    else:
                        _render_ko_card(_rnd_matches[_i])


# ══════════════════════════════════════════════════════════════════════════════
# 🌍 GROUP STAGE TAB
# ══════════════════════════════════════════════════════════════════════════════

with tab_grp:
    st.caption("Group Stage · June 11–27, 2026 · All times Pacific")

    # ── Filters ───────────────────────────────────────────────────────────────
    teams_df  = get_all_teams()
    _f1, _f2, _f3 = st.columns([1, 2, 5])
    with _f1:
        groups = ["All Groups"] + get_all_group_letters()
        selected_group = st.selectbox("Group", groups, label_visibility="collapsed")
    with _f2:
        team_list = ["All Teams"] + sorted(teams_df['name'].tolist())
        selected_team = st.selectbox("Team", team_list, label_visibility="collapsed")

    # ── Apply filters ─────────────────────────────────────────────────────────
    matches = all_matches.copy()
    if selected_group != "All Groups":
        matches = matches[matches['group_letter'] == selected_group]
    if selected_team != "All Teams":
        matches = matches[
            (matches['home_team'] == selected_team) |
            (matches['away_team'] == selected_team)
        ]

    live_df      = matches[matches.apply(_is_live, axis=1)].copy()
    completed_df = matches[matches['status'] == 'completed'].copy()
    upcoming_df  = matches[
        (matches['status'] == 'scheduled') & ~matches.apply(_is_live, axis=1)
    ].copy()

    if matches.empty:
        st.info("No matches found with those filters.")
        st.stop()

    # ── Next Kickoff Banner ───────────────────────────────────────────────────
    def _et_to_sort_key(row) -> int:
        try:
            h, m = str(row['kickoff_time_et']).split(":")
            et_min = int(h) * 60 + int(m)
            pt_min = et_min - 180
            if pt_min < 0:
                pt_min += 1440
            return int(row.get('match_date', '').replace('-', '') or 0) * 10000 + pt_min
        except Exception:
            return 99999999

    _sched = all_matches[all_matches['status'] == 'scheduled'].copy()
    _sched = _sched[~_sched.apply(_is_live, axis=1)]
    _sched['_sk'] = _sched.apply(_et_to_sort_key, axis=1)
    _sched = _sched.sort_values('_sk').drop(columns=['_sk'])

    if not _sched.empty:
        nm     = _sched.iloc[0]
        nm_id  = int(nm['id'])
        hf     = get_flag(nm['home_team'])
        af     = get_flag(nm['away_team'])
        nm_picks = _picks_for(nm_id, picks_df)
        n_picked = len(nm_picks)

        kickoff_pt  = et_to_pt(str(nm['match_date']), str(nm['kickoff_time_et']))
        time_until  = kickoff_pt - now_pt
        total_secs  = max(0, int(time_until.total_seconds()))
        h_until     = total_secs // 3600
        m_until     = (total_secs % 3600) // 60

        if total_secs <= 0:
            countdown = "Starting now!"
            cd_color  = "#F87171"
        elif h_until > 0:
            countdown = f"Starts in {h_until}h {m_until}m"
            cd_color  = "#93C5FD"
        else:
            countdown = f"Starts in {m_until}m"
            cd_color  = "#FCD34D"

        picks_note = (
            f"👨‍👩‍👧‍👦 {n_picked}/{n_fam} picks submitted"
            if n_picked > 0 else "👨‍👩‍👧‍👦 No picks yet"
        )
        grp = nm['group_letter']
        time_str = fmt_match_time(nm['match_date'], nm['kickoff_time_et'])

        st.markdown(
            f"<div style='background:linear-gradient(135deg,#0F172A,#1E293B);"
            f"border:1px solid rgba(147,197,253,.25);border-radius:14px;"
            f"padding:.9rem 1.2rem;margin:.3rem 0 .8rem;display:flex;align-items:center;gap:1rem'>"
            f"<div style='font-size:1.2rem;opacity:.7'>⏰</div>"
            f"<div style='flex:1'>"
            f"<div style='font-size:.72rem;color:#64748B;font-weight:700;letter-spacing:.05em;text-transform:uppercase'>Next Kickoff · Group {grp}</div>"
            f"<div style='font-size:1.1rem;font-weight:900;color:#F1F5F9;margin:.1rem 0'>"
            f"{hf} {nm['home_team']} &nbsp;vs&nbsp; {af} {nm['away_team']}</div>"
            f"<div style='font-size:.78rem;color:#94A3B8'>🕒 {time_str}</div>"
            f"</div>"
            f"<div style='text-align:right'>"
            f"<div style='font-size:1.15rem;font-weight:900;color:{cd_color}'>{countdown}</div>"
            f"<div style='font-size:.72rem;color:#64748B;margin-top:.1rem'>{picks_note}</div>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Quick Navigation Chips ────────────────────────────────────────────────
    _chip_defs: list[tuple[str, str]] = []
    if not live_df.empty:
        _chip_defs.append(("🔴 Live", "#sched-live"))
    if not upcoming_df.empty:
        if today_pt in upcoming_df['pt_date'].values:
            _chip_defs.append(("📅 Today", "#sched-today"))
        if tomorrow_pt in upcoming_df['pt_date'].values:
            _chip_defs.append(("⏭ Tomorrow", "#sched-tomorrow"))
        _chip_defs.append(("🔥 Upcoming", "#sched-upcoming"))
    if not completed_df.empty:
        _chip_defs.append(("🏆 Results", "#sched-results"))

    if _chip_defs:
        st.markdown(
            "<div style='display:flex;flex-wrap:wrap;gap:.35rem;margin:.15rem 0 .9rem'>"
            + " ".join(f"<a href='{h}' class='nav-chip'>{l}</a>" for l, h in _chip_defs)
            + "</div>",
            unsafe_allow_html=True,
        )

    # ── LIVE NOW ──────────────────────────────────────────────────────────────
    if not live_df.empty:
        st.markdown("<div id='sched-live' class='sect-hdr sect-live'>🔥 Live Now</div>",
                    unsafe_allow_html=True)

        for _, m in live_df.iterrows():
            mid      = int(m['id'])
            hf       = get_flag(m['home_team'])
            af       = get_flag(m['away_team'])
            time_str = fmt_match_time(m['match_date'], m['kickoff_time_et'])
            mp       = _picks_for(mid, picks_df)
            user_pick_row = mp[mp['user_name'] == active_user] if not mp.empty else pd.DataFrame()
            user_pick     = user_pick_row['picked_team'].iloc[0] if not user_pick_row.empty else None

            sticker = (
                f"<div style='display:flex;justify-content:center;gap:2rem;margin:.3rem 0'>"
                f"{_sticker_block(m['home_team'], mp, hf)}"
                f"{_sticker_block(m['away_team'], mp, af)}"
                f"</div>"
                if not mp.empty else ""
            )
            consensus = _consensus_html(m, mp)

            with st.container(border=True):
                st.markdown(
                    f"<div style='text-align:center;padding:.2rem 0'>"
                    f"<div style='display:flex;justify-content:center;align-items:center;gap:.5rem;margin-bottom:.2rem'>"
                    f"{_grp_badge(m['group_letter'])}"
                    f"<span class='live-badge'>🔴 LIVE</span>"
                    f"</div>"
                    f"<div style='font-size:3.8rem;line-height:1.05'>{hf}&nbsp;&nbsp;{af}</div>"
                    f"<div style='font-size:1.2rem;font-weight:900;color:#F1F5F9;margin:.2rem 0'>"
                    f"{m['home_team']} &nbsp;<span style='opacity:.4;font-weight:300'>vs</span>&nbsp; {m['away_team']}"
                    f"</div>"
                    f"<div style='font-size:.78rem;color:#94A3B8'>🕒 {time_str} &nbsp;·&nbsp; 🏟️ {m['venue']}</div>"
                    f"<div style='font-size:.72rem;color:#64748B'>📍 {m['city']}, {m['host_country']}</div>"
                    f"</div>"
                    f"{sticker}{consensus}"
                    f"<hr style='border:none;border-top:1px solid rgba(148,163,184,.15);margin:.45rem 0'>",
                    unsafe_allow_html=True,
                )
                b1, b2, b3 = st.columns([2, 2, 3])
                with b1:
                    lbl = f"✅ {m['home_team']}" if user_pick == m['home_team'] else m['home_team']
                    if st.button(lbl, key=f"live_{mid}_h", use_container_width=True):
                        save_pick(active_user_id, mid, m['home_team'])
                        st.rerun()
                with b2:
                    lbl = f"✅ {m['away_team']}" if user_pick == m['away_team'] else m['away_team']
                    if st.button(lbl, key=f"live_{mid}_a", use_container_width=True):
                        save_pick(active_user_id, mid, m['away_team'])
                        st.rerun()
                with b3:
                    if st.button("🔥 Match Center", key=f"live_mc_{mid}", use_container_width=True):
                        st.session_state["_nav_match_id"] = mid
                        st.switch_page("pages/matchup.py")

    # ── UPCOMING ──────────────────────────────────────────────────────────────
    if not upcoming_df.empty:
        st.markdown(
            "<div id='sched-upcoming' class='sect-hdr sect-upcoming'>⏰ Upcoming</div>",
            unsafe_allow_html=True,
        )

        for pt_date_val, day_grp in upcoming_df.groupby('pt_date'):
            is_today    = (pt_date_val == today_pt)
            is_tomorrow = (pt_date_val == tomorrow_pt)
            if is_today:
                date_label   = "Today"
                _date_anchor = " id='sched-today'"
            elif is_tomorrow:
                date_label   = "Tomorrow"
                _date_anchor = " id='sched-tomorrow'"
            else:
                date_label   = fmt_date(pt_date_val)
                _date_anchor = ""
            st.markdown(
                f"<div{_date_anchor} style='font-size:.82rem;color:#64748B;font-weight:700;"
                f"letter-spacing:.03em;margin:.5rem 0 .15rem'>📆 {date_label}</div>",
                unsafe_allow_html=True,
            )

            _day_rows = list(day_grp.iterrows())
            for _i in range(0, len(_day_rows), 2):
                if _i + 1 < len(_day_rows):
                    _ca, _cb = st.columns(2, gap="medium")
                    with _ca:
                        _render_upcoming_card(_day_rows[_i][1], picks_df)
                    with _cb:
                        _render_upcoming_card(_day_rows[_i + 1][1], picks_df)
                else:
                    _render_upcoming_card(_day_rows[_i][1], picks_df)

    # ── FINAL RESULTS (compact) ────────────────────────────────────────────────
    if not completed_df.empty:
        n_done = len(completed_df)
        st.markdown(
            f"<div id='sched-results' class='sect-hdr sect-final'>🏆 Final Results &nbsp;"
            f"<span style='font-weight:400;font-size:.8rem'>({n_done} matches)</span></div>",
            unsafe_allow_html=True,
        )

        for pt_date_val, day_grp in completed_df.sort_values(
            ['pt_date', 'kickoff_time_et'], ascending=[False, False]
        ).groupby('pt_date', sort=False):
            st.markdown(
                f"<div style='font-size:.78rem;color:#475569;font-weight:700;"
                f"margin:.5rem 0 .15rem'>📆 {fmt_date(pt_date_val)}</div>",
                unsafe_allow_html=True,
            )

            for _, m in day_grp.iterrows():
                mid      = int(m['id'])
                hf       = get_flag(m['home_team'])
                af       = get_flag(m['away_team'])
                hs, as_  = int(m['home_score']), int(m['away_score'])
                mp       = _picks_for(mid, picks_df)
                user_pick_row = mp[mp['user_name'] == active_user] if not mp.empty else pd.DataFrame()
                user_pick     = user_pick_row['picked_team'].iloc[0] if not user_pick_row.empty else None

                if hs > as_:
                    winner     = m['home_team']
                    result_txt = f"🏆 {winner} wins"
                    result_clr = "#4ADE80"
                elif as_ > hs:
                    winner     = m['away_team']
                    result_txt = f"🏆 {winner} wins"
                    result_clr = "#4ADE80"
                else:
                    winner     = None
                    result_txt = "🤝 Draw"
                    result_clr = "#FCD34D"

                if user_pick:
                    pts = _pick_pts(user_pick, m)
                    u_badge = (
                        f"&nbsp;<span style='font-size:.68rem;"
                        f"color:{'#4ADE80' if (pts or 0)>0 else '#F87171'}'>"
                        f"{'✅' if (pts or 0)==1.0 else '🤝' if (pts or 0)==0.5 else '❌'}"
                        f"&thinsp;{active_avatar}</span>"
                    )
                else:
                    u_badge = ""

                picks_row  = _compact_picks_row(m, mp)
                family_acc = _family_accuracy_html(m, mp)
                family_line = ""
                if picks_row or family_acc:
                    sep = " &nbsp;·&nbsp; " if picks_row and family_acc else ""
                    family_line = (
                        f"<div style='font-size:.75rem;color:#94A3B8;margin-top:.1rem'>"
                        f"👨‍👩‍👧‍👦 {picks_row}{sep}{family_acc}</div>"
                    )

                ht_full = m['home_team']
                at_full = m['away_team']

                col_card, col_btn = st.columns([5, 1])
                with col_card:
                    st.markdown(
                        f"<div style='background:linear-gradient(160deg,#0F172A,#1E293B);"
                        f"border:1px solid rgba(148,163,184,.12);border-radius:10px;"
                        f"padding:.5rem .85rem;margin:.18rem 0'>"
                        f"<div style='display:flex;align-items:center;gap:.6rem'>"
                        f"<span style='font-size:1.5rem;line-height:1'>{hf}&thinsp;{af}</span>"
                        f"<div style='flex:1'>"
                        f"<div style='font-size:.92rem;font-weight:700;color:#E2E8F0;line-height:1.2'>"
                        f"{ht_full} <span style='color:#FCD34D;font-weight:900'>{hs}–{as_}</span> {at_full}{u_badge}"
                        f"</div>"
                        f"<div style='font-size:.72rem;color:{result_clr};margin-top:.05rem'>{result_txt}"
                        f"&nbsp;·&nbsp;{_grp_badge(m['group_letter'])}</div>"
                        f"</div>"
                        f"</div>"
                        + family_line
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    st.markdown("<div style='height:.35rem'></div>", unsafe_allow_html=True)
                    if st.button("📊", key=f"done_{mid}", help="Match Summary",
                                 use_container_width=True):
                        st.session_state["_nav_match_id"] = mid
                        st.switch_page("pages/matchup.py")
