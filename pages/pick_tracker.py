import streamlit as st
import pandas as pd
from services.picks import get_all_picks, get_picks_for_user
from services.matches import get_all_matches
from services.teams import get_flag, get_all_group_letters
from services.time_utils import fmt_date, fmt_match_time, pt_date_str
from services.scoring import pick_result

active_user    = st.session_state.get("active_user_name", "Shawn")
active_user_id = st.session_state.get("active_user_id", 1)
active_avatar  = st.session_state.get("active_user_avatar", "🐘")

st.markdown("## 🎯 Pick Tracker")

with st.sidebar:
    st.markdown("### 🔍 Filters")
    status_filter = st.selectbox("Show", ["All Matches", "Has Picks", "Completed", "Scheduled"])
    group_filter  = st.selectbox("Group", ["All Groups"] + get_all_group_letters())

all_matches = get_all_matches()
all_picks   = get_all_picks()

all_matches['pt_date'] = all_matches.apply(
    lambda r: pt_date_str(r['match_date'], r['kickoff_time_et']), axis=1
)

tab_match, tab_person = st.tabs(["📋 By Match", "👤 By Person"])

# ── TAB 1: BY MATCH ───────────────────────────────────────────────────────────
with tab_match:
    matches = all_matches.copy()
    if group_filter != "All Groups":
        matches = matches[matches['group_letter'] == group_filter]
    if status_filter == "Completed":
        matches = matches[matches['status'] == 'completed']
    elif status_filter == "Scheduled":
        matches = matches[matches['status'] == 'scheduled']
    elif status_filter == "Has Picks":
        picked_mids = set(all_picks['match_id'].unique()) if not all_picks.empty else set()
        matches = matches[matches['id'].isin(picked_mids)]

    if matches.empty:
        st.info("No matches to show with those filters.")
    else:
        for pt_date_val, day_matches in matches.groupby('pt_date'):
            st.markdown(f"### 📅 {fmt_date(pt_date_val)}")
            for _, m in day_matches.iterrows():
                mid      = int(m['id'])
                hf       = get_flag(m['home_team'])
                af       = get_flag(m['away_team'])
                time_str = fmt_match_time(m['match_date'], m['kickoff_time_et'])
                mpicks   = all_picks[all_picks['match_id'] == mid] if not all_picks.empty else pd.DataFrame()

                if m['status'] == 'completed':
                    hs, as_      = int(m['home_score']), int(m['away_score'])
                    score_str    = f"{hs} – {as_}"
                    result_label = (
                        f"🏆 {m['home_team']} wins" if hs > as_
                        else f"🏆 {m['away_team']} wins" if as_ > hs
                        else "🤝 Draw"
                    )
                    result_color = "#4ADE80"
                else:
                    score_str    = "vs"
                    result_label = ""
                    result_color = "#64748B"

                def _avatar_row(rows):
                    if rows.empty:
                        return "<span style='opacity:.3;font-size:1.4rem'>—</span>"
                    parts = []
                    for _, r in rows.iterrows():
                        name, av = r['user_name'], r['avatar']
                        parts.append(f"<span style='font-size:1.9rem' title='{name}'>{av}</span>")
                    return " ".join(parts)

                if not mpicks.empty:
                    home_rows = mpicks[mpicks['picked_team'] == m['home_team']]
                    away_rows = mpicks[mpicks['picked_team'] == m['away_team']]

                    sticker_board = (
                        "<div style='display:flex;justify-content:space-around;padding:.5rem 0'>"
                        f"<div style='text-align:center'>"
                        f"<div style='font-size:.72rem;color:#94A3B8;margin-bottom:.2rem'>{hf} {m['home_team']}</div>"
                        f"<div>{_avatar_row(home_rows)}</div>"
                        f"</div>"
                        f"<div style='text-align:center'>"
                        f"<div style='font-size:.72rem;color:#94A3B8;margin-bottom:.2rem'>{af} {m['away_team']}</div>"
                        f"<div>{_avatar_row(away_rows)}</div>"
                        f"</div>"
                        "</div>"
                    )

                    if m['status'] == 'completed':
                        pts_parts = []
                        for _, pk in mpicks.iterrows():
                            pts = pick_result(
                                pk['picked_team'], m['home_team'], m['away_team'],
                                m['home_score'], m['away_score']
                            )
                            clr = "#4ADE80" if pts == 1.0 else "#FCD34D" if pts == 0.5 else "#F87171"
                            lbl = "+1" if pts == 1.0 else "+½" if pts == 0.5 else "+0"
                            pts_parts.append(
                                f"<span style='color:{clr};font-size:.88rem'>"
                                f"{pk['avatar']} {lbl}</span>"
                            )
                        pts_row = (
                            "<div style='text-align:center;padding:.3rem 0;"
                            "border-top:1px solid rgba(148,163,184,.15);margin-top:.2rem'>"
                            + " &nbsp;·&nbsp; ".join(pts_parts)
                            + "</div>"
                        )
                    else:
                        pts_row = ""
                else:
                    sticker_board = (
                        "<div style='text-align:center;color:#475569;font-size:.82rem;"
                        "padding:.6rem 0'>No picks yet</div>"
                    )
                    pts_row = ""

                with st.container(border=True):
                    st.markdown(
                        f"<div style='text-align:center;padding:.25rem 0'>"
                        f"<div style='font-size:3rem;line-height:1.05'>{hf} &nbsp; {af}</div>"
                        f"<div style='font-size:1rem;font-weight:900;color:#F1F5F9;margin:.15rem 0'>"
                        f"{m['home_team']} &nbsp;"
                        f"<span style='color:#FCD34D'>{score_str}</span>"
                        f"&nbsp; {m['away_team']}</div>"
                        f"<div style='font-size:.7rem;color:#64748B'>"
                        f"Group {m['group_letter']} · {time_str} · {m['city']}</div>"
                        + (
                            f"<div style='font-size:.82rem;color:{result_color};"
                            f"font-weight:700;margin:.1rem 0'>{result_label}</div>"
                            if result_label else ""
                        )
                        + "</div>"
                        "<hr style='border:none;border-top:1px solid rgba(148,163,184,.15);margin:.3rem 0'>"
                        + sticker_board + pts_row,
                        unsafe_allow_html=True
                    )

# ── TAB 2: BY PERSON ──────────────────────────────────────────────────────────
with tab_person:
    user_picks = get_picks_for_user(active_user_id)

    if not user_picks.empty:
        completed = user_picks[user_picks['status'] == 'completed'].copy()
        if not completed.empty:
            completed['pts'] = completed.apply(
                lambda r: pick_result(
                    r['picked_team'], r['home_team'], r['away_team'],
                    r['home_score'], r['away_score']
                ),
                axis=1
            )
            total_pts = float(completed['pts'].sum())
            wins      = int((completed['pts'] == 1.0).sum())
            draws     = int((completed['pts'] == 0.5).sum())
        else:
            total_pts, wins, draws = 0.0, 0, 0
        n_picks = len(user_picks)
    else:
        total_pts, wins, draws, n_picks = 0.0, 0, 0, 0

    st.markdown(
        f"<div style='background:linear-gradient(135deg,#1E3A5F,#2563EB);border-radius:16px;"
        f"padding:1.2rem;text-align:center;color:white;margin-bottom:1.2rem'>"
        f"<div style='font-size:3.2rem;line-height:1'>{active_avatar}</div>"
        f"<div style='font-size:1.5rem;font-weight:900;margin:.25rem 0'>{active_user}'s Picks</div>"
        f"<div style='display:flex;justify-content:center;gap:2.5rem;margin-top:.6rem'>"
        f"<div><div style='font-size:1.6rem;font-weight:900;color:#FCD34D'>{total_pts:.1f}</div>"
        f"<div style='font-size:.75rem;color:#CBD5E1'>Points</div></div>"
        f"<div><div style='font-size:1.6rem;font-weight:900;color:#4ADE80'>{wins}</div>"
        f"<div style='font-size:.75rem;color:#CBD5E1'>Wins</div></div>"
        f"<div><div style='font-size:1.6rem;font-weight:900;color:#FCD34D'>{draws}</div>"
        f"<div style='font-size:.75rem;color:#CBD5E1'>Draws</div></div>"
        f"<div><div style='font-size:1.6rem;font-weight:900'>{n_picks}</div>"
        f"<div style='font-size:.75rem;color:#CBD5E1'>Picks Made</div></div>"
        f"</div></div>",
        unsafe_allow_html=True
    )

    if user_picks.empty:
        st.info(f"{active_user} hasn't made any picks yet — head to the Schedule page to get started!")
    else:
        user_picks = user_picks.copy()
        user_picks['pt_date'] = user_picks.apply(
            lambda r: pt_date_str(r['match_date'], r['kickoff_time_et']), axis=1
        )

        for pt_date_val, day_picks in user_picks.groupby('pt_date'):
            st.markdown(f"#### 📅 {fmt_date(pt_date_val)}")
            for _, pk in day_picks.iterrows():
                hf          = get_flag(pk['home_team'])
                af          = get_flag(pk['away_team'])
                picked_home = pk['picked_team'] == pk['home_team']
                time_str    = fmt_match_time(pk['match_date'], pk['kickoff_time_et'])

                if pk['status'] == 'completed':
                    pts = pick_result(
                        pk['picked_team'], pk['home_team'], pk['away_team'],
                        pk['home_score'], pk['away_score']
                    )
                    hs, as_   = int(pk['home_score']), int(pk['away_score'])
                    score_str = f"{hs}–{as_}"
                    if pts == 1.0:
                        badge, badge_color = "🟢 +1 pt",  "#4ADE80"
                    elif pts == 0.5:
                        badge, badge_color = "🟡 +½ pt",  "#FCD34D"
                    else:
                        badge, badge_color = "🔴 +0 pts", "#F87171"
                else:
                    score_str             = "vs"
                    badge, badge_color    = "⏳ Pending", "#94A3B8"

                home_style = "font-weight:900;color:#FCD34D" if picked_home else "color:#94A3B8"
                away_style = "font-weight:900;color:#FCD34D" if not picked_home else "color:#94A3B8"
                check_h    = " ✓" if picked_home else ""
                check_a    = " ✓" if not picked_home else ""

                st.markdown(
                    f"<div style='background:linear-gradient(160deg,#1E293B,#0F172A);border-radius:12px;"
                    f"padding:.75rem 1.1rem;margin:.3rem 0;border:1px solid rgba(148,163,184,.15)'>"
                    f"<div style='display:flex;align-items:center;gap:.5rem'>"
                    f"<div style='flex:1;{home_style}'>{hf} {pk['home_team']}{check_h}</div>"
                    f"<div style='color:#64748B;font-size:.85rem;padding:0 .5rem'>{score_str}</div>"
                    f"<div style='flex:1;text-align:right;{away_style}'>{check_a}{pk['away_team']} {af}</div>"
                    f"</div>"
                    f"<div style='display:flex;justify-content:space-between;margin-top:.3rem'>"
                    f"<div style='font-size:.7rem;color:#64748B'>Group {pk['group_letter']} · {time_str}</div>"
                    f"<div style='font-size:.8rem;color:{badge_color};font-weight:700'>{badge}</div>"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
