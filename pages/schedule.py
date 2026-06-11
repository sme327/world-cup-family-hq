import streamlit as st
import pandas as pd
from datetime import date
from services.matches import get_all_matches
from services.teams import get_all_teams, get_all_group_letters, get_flag
from services.picks import get_all_picks, get_all_users, save_pick
from services.passport import get_discoveries
from services.time_utils import fmt_match_time, fmt_date, pt_date_str

st.markdown("""
<style>
/* Pick-badge chips */
.pick-badge {
    display: inline-block;
    background: rgba(255,255,255,.1);
    border-radius: 20px;
    padding: .12rem .5rem;
    font-size: .82rem;
    margin: .1rem;
    color: #CBD5E1;
}
/* Group letter badge */
.grp-badge {
    display: inline-block;
    background: #1E40AF;
    color: white;
    border-radius: 5px;
    padding: .06rem .32rem;
    font-size: .7rem;
    font-weight: 800;
    margin-right: .3rem;
    letter-spacing: .03em;
}
/* Winner / loser row in completed card */
.winner-accent { color: #4ADE80; font-weight: 700; font-size: .8rem; }
.loser-accent  { color: #F87171; font-size: .8rem; }
</style>
""", unsafe_allow_html=True)


def _pick_pts(picked, m):
    if m['status'] != 'completed':
        return None
    hs, as_ = int(m['home_score']), int(m['away_score'])
    if hs == as_:
        return 0.5
    return 1.0 if picked == (m['home_team'] if hs > as_ else m['away_team']) else 0.0


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Filter Matches")
    groups = ["All Groups"] + get_all_group_letters()
    selected_group = st.selectbox("Group", groups)

    teams_df = get_all_teams()
    team_names = ["All Teams"] + sorted(teams_df['name'].tolist())
    selected_team = st.selectbox("Team", team_names)

    status_opts = ["All", "Scheduled", "Completed"]
    selected_status = st.selectbox("Status", status_opts)


active_user    = st.session_state.get("active_user_name",   "Shawn")
active_user_id = st.session_state.get("active_user_id",     1)
active_avatar  = st.session_state.get("active_user_avatar", "🐘")
users          = get_all_users()

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("## 📅 Match Schedule")
st.caption("Group Stage · June 11–27, 2026 · All times Pacific")

# ── Load + filter ─────────────────────────────────────────────────────────────
matches  = get_all_matches()
picks_df = get_all_picks()

# PT dates for correct grouping
matches['pt_date'] = matches.apply(
    lambda r: pt_date_str(r['match_date'], r['kickoff_time_et']), axis=1
)

if selected_group != "All Groups":
    matches = matches[matches['group_letter'] == selected_group]
if selected_team != "All Teams":
    matches = matches[(matches['home_team'] == selected_team) |
                      (matches['away_team'] == selected_team)]
if selected_status == "Scheduled":
    matches = matches[matches['status'] == 'scheduled']
elif selected_status == "Completed":
    matches = matches[matches['status'] == 'completed']

# ── Load active user's passport discoveries (for passport indicators) ─────────
user_disc: set[str] = set()
try:
    disc_df = get_discoveries(active_user_id)
    if not disc_df.empty:
        user_disc = set(disc_df['country_name'].tolist())
except Exception:
    pass

today_pt = date.today().isoformat()

# ── Match cards ───────────────────────────────────────────────────────────────
if matches.empty:
    st.info("No matches found with those filters.")
else:
    for pt_date_val, day_matches in matches.groupby('pt_date'):
        is_today = (pt_date_val == today_pt)

        if is_today:
            st.markdown(
                "<div style='background:linear-gradient(135deg,#DC2626,#EF4444);"
                "color:white;border-radius:10px;padding:.5rem 1.1rem;"
                "font-size:1.2rem;font-weight:900;margin:.6rem 0 .3rem'>"
                "🔥 TODAY — Live Matches</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"### 📆 {fmt_date(pt_date_val)}")

        for _, m in day_matches.iterrows():
            mid  = int(m['id'])
            hf   = get_flag(m['home_team'])
            af   = get_flag(m['away_team'])
            time_str = fmt_match_time(m['match_date'], m['kickoff_time_et'])

            match_picks   = picks_df[picks_df['match_id'] == mid] if not picks_df.empty else pd.DataFrame()
            user_pick_row = match_picks[match_picks['user_name'] == active_user] if not match_picks.empty else pd.DataFrame()
            user_pick     = user_pick_row['picked_team'].iloc[0] if not user_pick_row.empty else None

            # Passport discovery icons
            h_disc = " 🌍" if m['home_team'] in user_disc else " ❓"
            a_disc = " 🌍" if m['away_team'] in user_disc else " ❓"

            # Group badge
            grp_badge = f"<span class='grp-badge'>{m['group_letter']}</span>"

            # Score / result block
            if m['status'] == 'completed':
                hs, as_ = int(m['home_score']), int(m['away_score'])
                score_html = (
                    f"<div style='font-size:2rem;font-weight:900;color:#FCD34D;text-align:center'>"
                    f"{hs} – {as_}</div>"
                )
                if hs > as_:
                    result_html = (
                        f"<div class='winner-accent' style='text-align:center'>🏆 {m['home_team']} wins</div>"
                    )
                elif as_ > hs:
                    result_html = (
                        f"<div class='winner-accent' style='text-align:center'>🏆 {m['away_team']} wins</div>"
                    )
                else:
                    result_html = "<div style='text-align:center;color:#FCD34D;font-size:.85rem'>🤝 Draw</div>"
            else:
                score_html = "<div style='text-align:center;font-size:1.2rem;color:#64748B'>vs</div>"
                result_html = ""

            # ── Sticker board (replaces text chips) ───────────────────────────
            if not match_picks.empty:
                home_avs = " ".join(
                    f"<span style='font-size:1.5rem'>{pk['avatar']}</span>"
                    for _, pk in match_picks.iterrows() if pk['picked_team'] == m['home_team']
                )
                away_avs = " ".join(
                    f"<span style='font-size:1.5rem'>{pk['avatar']}</span>"
                    for _, pk in match_picks.iterrows() if pk['picked_team'] == m['away_team']
                )
                sticker_board = (
                    "<div style='display:flex;justify-content:center;gap:2rem;"
                    "margin:.3rem 0;font-size:.75rem;color:#94A3B8'>"
                    f"<div style='text-align:center'>"
                    f"<div style='font-size:.75rem;color:#94A3B8'>{hf} {m['home_team']}</div>"
                    f"<div>{home_avs if home_avs else '<span style=\"opacity:.35\">—</span>'}</div>"
                    f"</div>"
                    f"<div style='text-align:center'>"
                    f"<div style='font-size:.75rem;color:#94A3B8'>{af} {m['away_team']}</div>"
                    f"<div>{away_avs if away_avs else '<span style=\"opacity:.35\">—</span>'}</div>"
                    f"</div>"
                    "</div>"
                )

                # Family consensus summary
                h_cnt = sum(1 for _, pk in match_picks.iterrows() if pk['picked_team'] == m['home_team'])
                a_cnt = sum(1 for _, pk in match_picks.iterrows() if pk['picked_team'] == m['away_team'])
                n_fam = len(users)
                total = len(match_picks)
                if total == n_fam:
                    if h_cnt > a_cnt:
                        consensus = f"👨‍👩‍👧‍👦 {m['home_team']} ({h_cnt}/{n_fam})"
                    elif a_cnt > h_cnt:
                        consensus = f"👨‍👩‍👧‍👦 {m['away_team']} ({a_cnt}/{n_fam})"
                    else:
                        consensus = f"👨‍👩‍👧‍👦 Split! {h_cnt}–{a_cnt}"
                elif total > 0:
                    consensus = f"👨‍👩‍👧‍👦 So far: {m['home_team']} {h_cnt} · {m['away_team']} {a_cnt}"
                else:
                    consensus = ""
                consensus_html = (
                    f"<div style='text-align:center;font-size:.75rem;color:#94A3B8;margin-top:.1rem'>{consensus}</div>"
                    if consensus else ""
                )
            else:
                sticker_board  = ""
                consensus_html = ""

            # ── Render card ───────────────────────────────────────────────────
            with st.container(border=True):
                st.markdown(
                    f"<div style='text-align:center;padding:.15rem 0'>"
                    f"<div style='font-size:3.5rem;line-height:1.05'>{hf}&nbsp;&nbsp;{af}</div>"
                    f"<div style='font-size:1.1rem;font-weight:900;color:#F1F5F9;margin:.2rem 0'>"
                    f"{m['home_team']}{h_disc} "
                    f"<span style='opacity:.4;font-weight:300'>vs</span> "
                    f"{m['away_team']}{a_disc}</div>"
                    f"{score_html}{result_html}"
                    f"</div>"
                    f"<div style='text-align:center;margin:.2rem 0'>"
                    f"<div style='color:#94A3B8;font-size:.78rem'>"
                    f"{grp_badge}🕒 {time_str} &nbsp;·&nbsp; 🏟️ {m['venue']}</div>"
                    f"<div style='color:#64748B;font-size:.75rem'>📍 {m['city']}, {m['host_country']}</div>"
                    f"</div>"
                    f"{sticker_board}{consensus_html}"
                    f"<hr style='border:none;border-top:1px solid rgba(148,163,184,.15);margin:.45rem 0'>",
                    unsafe_allow_html=True
                )

                # Action buttons — inside container, at bottom
                if m['status'] == 'scheduled':
                    b1, b2, b3 = st.columns([2, 2, 3])
                    with b1:
                        lbl = f"✅ {m['home_team']}" if user_pick == m['home_team'] else m['home_team']
                        if st.button(lbl, key=f"pick_{mid}_h", use_container_width=True):
                            save_pick(active_user_id, mid, m['home_team'])
                            st.rerun()
                    with b2:
                        lbl = f"✅ {m['away_team']}" if user_pick == m['away_team'] else m['away_team']
                        if st.button(lbl, key=f"pick_{mid}_a", use_container_width=True):
                            save_pick(active_user_id, mid, m['away_team'])
                            st.rerun()
                    with b3:
                        if st.button("⚽ Game Day Program", key=f"matchup_{mid}", use_container_width=True):
                            st.session_state["_nav_match_id"] = mid
                            st.switch_page("pages/matchup.py")
                else:
                    res_col, link_col = st.columns([3, 2])
                    with res_col:
                        if user_pick:
                            pts = _pick_pts(user_pick, m)
                            badge = "🟢 +1 pt" if pts == 1.0 else "🟡 +0.5 pts" if pts == 0.5 else "🔴 +0 pts"
                            st.markdown(
                                f"<span style='color:#CBD5E1;font-size:.88rem'>"
                                f"{active_avatar} Picked **{user_pick}** &nbsp;{badge}</span>",
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                f"<span style='color:#64748B;font-size:.85rem'>"
                                f"{active_avatar} No pick made</span>",
                                unsafe_allow_html=True
                            )
                    with link_col:
                        if st.button("⚽ Game Day Program", key=f"matchup_{mid}", use_container_width=True):
                            st.session_state["_nav_match_id"] = mid
                            st.switch_page("pages/matchup.py")
