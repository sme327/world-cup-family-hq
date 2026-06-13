import streamlit as st
import pandas as pd
from services.picks import get_all_picks, get_picks_for_user, get_all_users
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
    group_filter = st.selectbox("Group", ["All Groups"] + get_all_group_letters())

# ── Load data ──────────────────────────────────────────────────────────────────
all_matches = get_all_matches()
all_picks   = get_all_picks()
all_users   = get_all_users()
n_family    = len(all_users)

all_matches['pt_date'] = all_matches.apply(
    lambda r: pt_date_str(r['match_date'], r['kickoff_time_et']), axis=1
)

# ── Pure helpers ───────────────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> str:
    h = (h or "#888888").lstrip('#')
    if len(h) == 6:
        return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"
    return "128,128,128"


def _pill(av: str, name: str, suffix: str, color: str) -> str:
    rgb = _hex_to_rgb(color)
    return (
        f"<span style='background:rgba({rgb},.15);color:{color};border-radius:20px;"
        f"padding:.07rem .5rem;font-size:.85rem;font-weight:700;display:inline-block;"
        f"margin:.04rem;white-space:nowrap'>{av}&nbsp;{name}"
        + (f"&nbsp;<b>{suffix}</b>" if suffix else "")
        + "</span>"
    )


def _confidence(home_n: int, away_n: int, home_team: str, away_team: str,
                status: str, hs, as_) -> str:
    total = home_n + away_n
    if total == 0:
        return ""
    if status == 'completed' and hs is not None and not pd.isna(hs):
        hs, as_ = int(hs), int(as_)
        if hs == as_:
            return f"🎯 Split — {home_n} picked {home_team} · {away_n} picked {away_team}"
        winner = home_team if hs > as_ else away_team
        wn = home_n if hs > as_ else away_n
        if wn == 0:
            return f"😲 Unanimous upset — nobody picked {winner}!"
        if wn == total:
            return f"🔥 Everyone got it right!"
        if wn == 1:
            return f"😲 Upset Alert — only 1 picked {winner}"
        if wn >= total * 0.67:
            return f"✅ Family got it — {wn}/{total} picked {winner}"
        return f"😲 Surprise — only {wn}/{total} picked {winner}"
    else:
        if home_n == away_n and total > 0:
            return f"🎯 Split — {home_n} vs {away_n}"
        fav = home_team if home_n >= away_n else away_team
        mx = max(home_n, away_n)
        if mx == total:
            return f"🔥 All in on {fav}"
        return f"📊 Leaning {fav} — {mx}/{total}"


def _build_pick_board(mpicks: pd.DataFrame, home_team: str, away_team: str,
                      status: str, hs, as_) -> str:
    if mpicks.empty:
        return ("<div style='text-align:center;font-size:.75rem;color:#64748B;"
                "padding:.25rem 0'>No picks yet</div>")

    home_rows = mpicks[mpicks['picked_team'] == home_team]
    away_rows = mpicks[mpicks['picked_team'] == away_team]
    home_n, away_n = len(home_rows), len(away_rows)
    hf, af = get_flag(home_team), get_flag(away_team)

    is_done  = status == 'completed' and hs is not None and not pd.isna(hs)
    is_draw  = is_done and int(hs) == int(as_)

    def _pills_for(rows: pd.DataFrame, pts_override=None) -> str:
        if rows.empty:
            return "<span style='font-size:.78rem;color:#475569;opacity:.6'>—</span>"
        parts = []
        for _, r in rows.iterrows():
            av   = r['avatar']
            name = r['user_name']
            tc   = r.get('theme_color') or '#94A3B8'
            if not isinstance(tc, str) or not tc.startswith('#'):
                tc = '#94A3B8'
            if pts_override is not None:
                suffix, color = pts_override, "#FCD34D"
            elif is_done:
                pts = pick_result(r['picked_team'], home_team, away_team, hs, as_)
                if pts == 1.0:   suffix, color = "+1",  "#4ADE80"
                elif pts == 0.5: suffix, color = "+½",  "#FCD34D"
                else:            suffix, color = "+0",  "#F87171"
            else:
                suffix, color = "", tc
            parts.append(_pill(av, name, suffix, color))
        return "".join(parts)

    col_style = "flex:1;border-radius:8px;padding:.2rem .4rem"

    if is_draw:
        hp = _pills_for(home_rows, "+½")
        ap = _pills_for(away_rows, "+½")
        return (
            "<div style='text-align:center;font-size:.88rem;font-weight:800;"
            "color:#FCD34D;margin:.15rem 0'>🤝 DRAW — everyone earns +½</div>"
            "<div style='display:flex;gap:.3rem;margin-top:.1rem'>"
            f"<div style='{col_style};background:rgba(252,211,77,.07)'>"
            f"<div style='font-size:.75rem;color:#FCD34D;font-weight:700;margin-bottom:.1rem'>"
            f"{hf} {home_team}</div>"
            f"<div style='display:flex;flex-wrap:wrap'>{hp}</div></div>"
            f"<div style='{col_style};background:rgba(252,211,77,.07)'>"
            f"<div style='font-size:.75rem;color:#FCD34D;font-weight:700;margin-bottom:.1rem'>"
            f"{af} {away_team}</div>"
            f"<div style='display:flex;flex-wrap:wrap'>{ap}</div></div>"
            "</div>"
        )

    if is_done:
        hs_i, as_i = int(hs), int(as_)
        home_wins  = hs_i > as_i
        win_team, lose_team   = (home_team, away_team) if home_wins else (away_team, home_team)
        win_rows,  lose_rows  = (home_rows, away_rows) if home_wins else (away_rows, home_rows)
        win_n,     lose_n     = len(win_rows), len(lose_rows)
        wp = _pills_for(win_rows)
        lp = _pills_for(lose_rows)
        return (
            "<div style='display:flex;gap:.3rem;margin-top:.1rem'>"
            f"<div style='{col_style};background:rgba(74,222,128,.08)'>"
            f"<div style='font-size:.75rem;font-weight:700;color:#4ADE80;margin-bottom:.1rem'>"
            f"✓ {win_team} ({win_n}/{n_family})</div>"
            f"<div style='display:flex;flex-wrap:wrap'>{wp}</div></div>"
            f"<div style='{col_style};background:rgba(248,113,113,.07)'>"
            f"<div style='font-size:.75rem;font-weight:700;color:#F87171;margin-bottom:.1rem'>"
            f"✗ {lose_team} ({lose_n}/{n_family})</div>"
            f"<div style='display:flex;flex-wrap:wrap'>{lp}</div></div>"
            "</div>"
        )

    # Scheduled
    hp = _pills_for(home_rows)
    ap = _pills_for(away_rows)
    return (
        "<div style='display:flex;gap:.3rem;margin-top:.1rem'>"
        f"<div style='{col_style};background:rgba(148,163,184,.07)'>"
        f"<div style='font-size:.75rem;color:#94A3B8;font-weight:700;margin-bottom:.1rem'>"
        f"{hf} {home_team} ({home_n}/{n_family})</div>"
        f"<div style='display:flex;flex-wrap:wrap'>{hp}</div></div>"
        f"<div style='{col_style};background:rgba(148,163,184,.07)'>"
        f"<div style='font-size:.75rem;color:#94A3B8;font-weight:700;margin-bottom:.1rem'>"
        f"{af} {away_team} ({away_n}/{n_family})</div>"
        f"<div style='display:flex;flex-wrap:wrap'>{ap}</div></div>"
        "</div>"
    )


def _match_card_html(m: pd.Series, mpicks: pd.DataFrame) -> str:
    hf  = get_flag(m['home_team'])
    af  = get_flag(m['away_team'])
    time_str = fmt_match_time(m['match_date'], m['kickoff_time_et'])
    hs, as_  = m.get('home_score'), m.get('away_score')

    if m['status'] == 'completed' and hs is not None and not pd.isna(hs):
        hs_i, as_i = int(hs), int(as_)
        score_str = f"{hs_i} – {as_i}"
        if hs_i > as_i:
            result_html = f"<div style='font-size:.9rem;font-weight:700;color:#4ADE80'>🏆 {m['home_team']} wins</div>"
        elif as_i > hs_i:
            result_html = f"<div style='font-size:.9rem;font-weight:700;color:#4ADE80'>🏆 {m['away_team']} wins</div>"
        else:
            result_html = ""  # draw shown in pick board
    else:
        score_str    = "vs"
        result_html  = ""
        hs, as_      = None, None

    # Confidence label
    if not mpicks.empty:
        home_n = int((mpicks['picked_team'] == m['home_team']).sum())
        away_n = int((mpicks['picked_team'] == m['away_team']).sum())
        conf_str = _confidence(home_n, away_n, m['home_team'], m['away_team'],
                               m['status'], hs, as_)
        conf_html = (
            f"<div style='font-size:.72rem;color:#64748B;margin-top:.15rem;"
            f"text-align:center'>{conf_str}</div>"
            if conf_str else ""
        )
    else:
        conf_html = ""

    pick_board = _build_pick_board(mpicks, m['home_team'], m['away_team'],
                                    m['status'], hs, as_)

    # NOTE: score_str / result_html can be extended for extra time / penalties
    # in knockout rounds by checking m.get('extra_time') / m.get('penalties') fields.
    return (
        f"<div style='padding:.3rem .6rem'>"
        # Header row: flags + teams + score inline
        f"<div style='display:flex;align-items:center;justify-content:center;"
        f"gap:.35rem;margin-bottom:.1rem'>"
        f"<span style='font-size:1.9rem;line-height:1'>{hf}</span>"
        f"<span style='font-size:1rem;font-weight:900;color:var(--text-color)'>{m['home_team']}</span>"
        f"<span style='font-size:1.3rem;font-weight:900;color:#FCD34D'>{score_str}</span>"
        f"<span style='font-size:1rem;font-weight:900;color:var(--text-color)'>{m['away_team']}</span>"
        f"<span style='font-size:1.9rem;line-height:1'>{af}</span>"
        f"</div>"
        # Sub-info
        f"<div style='text-align:center;font-size:.72rem;color:#64748B;margin-bottom:.15rem'>"
        f"Group {m['group_letter']} · {time_str} · {m['city']}</div>"
        + result_html
        + "<hr style='border:none;border-top:1px solid rgba(128,128,128,.15);margin:.2rem 0'>"
        + pick_board
        + conf_html
        + "</div>"
    )


def _win_streak(user_picks: pd.DataFrame) -> int:
    done = user_picks[user_picks['status'] == 'completed'].copy()
    if done.empty:
        return 0
    done = done.sort_values(['match_date', 'kickoff_time_et'])
    streak = 0
    for _, row in done.iloc[::-1].iterrows():
        pts = pick_result(row['picked_team'], row['home_team'], row['away_team'],
                          row['home_score'], row['away_score'])
        if pts == 1.0:
            streak += 1
        else:
            break
    return streak


def _best_countries_for_user(completed_picks: pd.DataFrame, all_user_picks: pd.DataFrame,
                             n: int = 5) -> list[tuple[str, float, int]]:
    """Countries ranked by points earned; tiebreak by pick count, then name."""
    if all_user_picks.empty:
        return []
    pick_counts = all_user_picks.groupby('picked_team').size().to_dict()
    if completed_picks.empty or 'pts' not in completed_picks.columns:
        return []
    pts_by = completed_picks.groupby('picked_team')['pts'].sum().to_dict()
    results = [
        (team, float(pts_by.get(team, 0.0)), int(pick_counts[team]))
        for team in pick_counts
        if float(pts_by.get(team, 0.0)) > 0
    ]
    results.sort(key=lambda x: (-x[1], -x[2], x[0]))
    return results[:n]


def _best_and_worst(completed: pd.DataFrame) -> tuple:
    if completed.empty:
        return None, None
    best_pick, best_score = None, -1
    worst_pick, worst_score = None, -1
    for _, pk in completed.iterrows():
        pts = pk['pts']
        mid = pk['match_id']
        mpicks = all_picks[all_picks['match_id'] == mid] if not all_picks.empty else pd.DataFrame()
        n_same  = int((mpicks['picked_team'] == pk['picked_team']).sum()) if not mpicks.empty else 0
        n_total = len(mpicks)
        n_other = n_total - n_same
        if pts == 1.0 and n_other > best_score:
            best_score, best_pick = n_other, pk
        elif pts == 0.0 and n_other > worst_score:
            worst_score, worst_pick = n_other, pk
    return best_pick, worst_pick


def _family_story_insights() -> list[str]:
    if all_picks.empty:
        return []
    stories = []

    # 1. Universal agreement on a pick
    for mid, mp in all_picks.groupby('match_id'):
        if mp['picked_team'].nunique() == 1 and len(mp) >= 3:
            team = mp['picked_team'].iloc[0]
            n    = len(mp)
            stories.append(f"🔥 {n} of {n_family} picked {get_flag(team)} **{team}**")
            break

    # 2. Lone-wolf correct pick among completed matches
    comp_picks = all_picks[all_picks['status'] == 'completed']
    for mid, mp in comp_picks.groupby('match_id'):
        if len(mp) < 3: continue
        r0 = mp.iloc[0]
        hs, as_ = r0.get('home_score'), r0.get('away_score')
        if pd.isna(hs) or pd.isna(as_): continue
        hs, as_ = int(hs), int(as_)
        if hs == as_: continue
        winner    = r0['home_team'] if hs > as_ else r0['away_team']
        win_picks = mp[mp['picked_team'] == winner]
        if len(win_picks) == 1:
            wolf = win_picks.iloc[0]
            stories.append(
                f"😲 **{wolf['avatar']} {wolf['user_name']}** was the only one "
                f"who picked {get_flag(winner)} **{winner}** — and was right!"
            )
            break

    # 3. Hottest current win streak
    best_n, best_name, best_av = 0, None, None
    for uid, upicks in all_picks.groupby('user_id'):
        done = upicks[upicks['status'] == 'completed'].sort_values('match_date')
        if done.empty: continue
        streak = 0
        for _, pk in done.iloc[::-1].iterrows():
            pts = pick_result(pk['picked_team'], pk['home_team'], pk['away_team'],
                              pk['home_score'], pk['away_score'])
            if pts == 1.0: streak += 1
            else:          break
        if streak > best_n:
            best_n, best_name, best_av = streak, upicks.iloc[0]['user_name'], upicks.iloc[0]['avatar']

    if best_name and best_n >= 2:
        stories.append(
            f"🔥 **{best_av} {best_name}** is on a **{best_n}-pick win streak!**"
        )

    return stories[:3]


# ── Tab header: title left, achievement shortcut right ────────────────────────
_tab_hdr_l, _tab_hdr_r = st.columns([5, 2])
with _tab_hdr_r:
    if st.button("🏅 Achievement Progress", key="ach_header_btn", use_container_width=True):
        st.switch_page("pages/achievements.py")

# ── TABS ───────────────────────────────────────────────────────────────────────
tab_match, tab_person = st.tabs(["📋 By Match", "👤 By Person"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: BY MATCH
# ══════════════════════════════════════════════════════════════════════════════
with tab_match:

    # ── Family Pick Story ─────────────────────────────────────────────────────
    insights = _family_story_insights()
    if insights:
        for insight in insights:
            st.markdown(f"> {insight}")

    # ── Family Favorite Countries ─────────────────────────────────────────────
    st.markdown("##### 🌎 Family Favorite Countries")
    if all_picks.empty:
        st.caption("No family picks yet.")
    else:
        _ctry_counts = (
            all_picks.groupby('picked_team').size()
            .sort_values(ascending=False)
            .head(10)
        )
        _max_cnt    = int(_ctry_counts.max())
        _MEDALS     = ["🥇", "🥈", "🥉"]
        _fav_rows   = ""
        for _i, (_team, _cnt) in enumerate(_ctry_counts.items()):
            _cnt        = int(_cnt)
            _flag       = get_flag(_team)
            _rank_label = _MEDALS[_i] if _i < 3 else f"{_i + 1}."
            _bar_w      = max(4, round(_cnt / _max_cnt * 100))
            _fav_rows  += (
                f"<div style='display:flex;align-items:center;gap:.55rem;"
                f"padding:.3rem 0;border-bottom:1px solid rgba(128,128,128,.07)'>"
                f"<span style='font-size:1.05rem;min-width:1.7rem;text-align:center;"
                f"line-height:1'>{_rank_label}</span>"
                f"<span style='font-size:1.15rem;min-width:1.6rem;line-height:1'>{_flag}</span>"
                f"<span style='font-size:.9rem;font-weight:700;flex:1;min-width:0'>{_team}</span>"
                f"<div style='min-width:110px;display:flex;align-items:center;gap:.45rem'>"
                f"<div style='flex:1;background:rgba(148,163,184,.15);border-radius:4px;height:6px'>"
                f"<div style='width:{_bar_w}%;background:#3B82F6;border-radius:4px;height:6px'></div>"
                f"</div>"
                f"<span style='font-size:.8rem;color:#94A3B8;white-space:nowrap;"
                f"min-width:4rem;text-align:right'>"
                f"{_cnt} pick{'s' if _cnt != 1 else ''}</span>"
                f"</div>"
                f"</div>"
            )
        st.markdown(
            f"<div style='border-radius:12px;padding:.3rem .85rem;"
            f"border:1px solid rgba(128,128,128,.12)'>{_fav_rows}</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Quick filters ─────────────────────────────────────────────────────────
    quick_filter = st.radio(
        "Filter",
        ["All", "Completed", "Upcoming", "Draws", "Upsets", "My Picks"],
        horizontal=True,
        label_visibility="collapsed",
    )

    # ── Build filtered match set ──────────────────────────────────────────────
    matches = all_matches.copy()
    if group_filter != "All Groups":
        matches = matches[matches['group_letter'] == group_filter]

    if quick_filter == "Completed":
        matches = matches[matches['status'] == 'completed']
    elif quick_filter == "Upcoming":
        matches = matches[matches['status'] == 'scheduled']
    elif quick_filter == "Draws":
        matches = matches[
            (matches['status'] == 'completed') &
            (matches['home_score'] == matches['away_score'])
        ]
    elif quick_filter == "Upsets":
        # Winner was picked by fewer than half of pickers for that match
        upset_mids = []
        for mid, mp in all_picks.groupby('match_id'):
            m_row = all_matches[all_matches['id'] == mid]
            if m_row.empty: continue
            m_row = m_row.iloc[0]
            if m_row['status'] != 'completed': continue
            hs, as_ = m_row.get('home_score'), m_row.get('away_score')
            if pd.isna(hs) or pd.isna(as_): continue
            hs, as_ = int(hs), int(as_)
            if hs == as_: continue
            winner = m_row['home_team'] if hs > as_ else m_row['away_team']
            wn = int((mp['picked_team'] == winner).sum())
            if wn < len(mp) / 2:
                upset_mids.append(mid)
        matches = matches[matches['id'].isin(upset_mids)]
    elif quick_filter == "My Picks":
        my_mids = set(all_picks[all_picks['user_id'] == active_user_id]['match_id'].unique()) \
                  if not all_picks.empty else set()
        matches = matches[matches['id'].isin(my_mids)]

    if matches.empty:
        st.info("No matches match that filter.")
    else:
        for pt_date_val, day_matches in matches.groupby('pt_date'):
            st.markdown(f"### 📅 {fmt_date(pt_date_val)}")
            for _, m in day_matches.iterrows():
                mid    = int(m['id'])
                mpicks = all_picks[all_picks['match_id'] == mid] if not all_picks.empty else pd.DataFrame()
                with st.container(border=True):
                    st.markdown(_match_card_html(m, mpicks), unsafe_allow_html=True)
                    _mu_status = m['status']
                    if _mu_status == 'live':        _mu_label = "📖 Match Center"
                    elif _mu_status == 'completed': _mu_label = "📊 Match Summary"
                    else:                           _mu_label = "📖 Match Preview"
                    _btn_c1, _btn_c2 = st.columns([5, 2])
                    with _btn_c2:
                        if st.button(_mu_label, key=f"mu_link_{mid}", use_container_width=True):
                            st.session_state["_nav_match_id"] = mid
                            st.switch_page("pages/matchup.py")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: BY PERSON
# ══════════════════════════════════════════════════════════════════════════════
with tab_person:
    user_picks = get_picks_for_user(active_user_id)
    user_color = st.session_state.get("active_user_color", "#2563EB")

    # ── Compute stats ─────────────────────────────────────────────────────────
    if not user_picks.empty:
        completed_up = user_picks[user_picks['status'] == 'completed'].copy()
        if not completed_up.empty:
            completed_up['pts'] = completed_up.apply(
                lambda r: pick_result(r['picked_team'], r['home_team'], r['away_team'],
                                      r['home_score'], r['away_score']),
                axis=1
            )
            total_pts  = float(completed_up['pts'].sum())
            wins       = int((completed_up['pts'] == 1.0).sum())
            draws      = int((completed_up['pts'] == 0.5).sum())
            n_done     = len(completed_up)
            accuracy   = total_pts / n_done * 100 if n_done > 0 else None
        else:
            total_pts, wins, draws, n_done, accuracy = 0.0, 0, 0, 0, None
        n_picks = len(user_picks)
    else:
        total_pts, wins, draws, n_done, n_picks, accuracy = 0.0, 0, 0, 0, 0, None
        completed_up = pd.DataFrame()

    streak  = _win_streak(user_picks)
    best_pk, worst_pk = _best_and_worst(completed_up) if not completed_up.empty else (None, None)

    # ── Header card ───────────────────────────────────────────────────────────
    acc_html = (
        f"<div><div style='font-size:1.6rem;font-weight:900;color:#A78BFA'>"
        f"{accuracy:.0f}%</div>"
        f"<div style='font-size:.75rem;color:#CBD5E1'>Accuracy</div></div>"
        if accuracy is not None else ""
    )
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#1E3A5F,#2563EB);border-radius:16px;"
        f"padding:1rem 1.2rem;text-align:center;color:white;margin-bottom:1rem'>"
        f"<div style='font-size:3rem;line-height:1'>{active_avatar}</div>"
        f"<div style='font-size:1.4rem;font-weight:900;margin:.2rem 0'>{active_user}'s Picks</div>"
        f"<div style='display:flex;justify-content:center;gap:2rem;margin-top:.5rem;flex-wrap:wrap'>"
        f"<div><div style='font-size:1.6rem;font-weight:900;color:#FCD34D'>{total_pts:.1f}</div>"
        f"<div style='font-size:.75rem;color:#CBD5E1'>Points</div></div>"
        f"<div><div style='font-size:1.6rem;font-weight:900;color:#4ADE80'>{wins}</div>"
        f"<div style='font-size:.75rem;color:#CBD5E1'>Wins</div></div>"
        f"<div><div style='font-size:1.6rem;font-weight:900;color:#FCD34D'>{draws}</div>"
        f"<div style='font-size:.75rem;color:#CBD5E1'>Draws</div></div>"
        f"<div><div style='font-size:1.6rem;font-weight:900'>{n_picks}</div>"
        f"<div style='font-size:.75rem;color:#CBD5E1'>Picks</div></div>"
        + acc_html +
        f"</div></div>",
        unsafe_allow_html=True,
    )
    # ── Streak + Best/Worst ───────────────────────────────────────────────────
    if streak >= 2 or best_pk is not None or worst_pk is not None:
        c1, c2, c3 = st.columns(3)

        with c1:
            if streak >= 2:
                st.markdown(
                    f"<div style='background:rgba(74,222,128,.1);border-radius:12px;"
                    f"padding:.6rem;text-align:center;height:100%'>"
                    f"<div style='font-size:1.4rem'>🔥</div>"
                    f"<div style='font-size:.75rem;font-weight:800;color:#4ADE80'>"
                    f"Won last {streak}</div>"
                    f"<div style='font-size:.6rem;color:#64748B'>Current streak</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='background:rgba(148,163,184,.08);border-radius:12px;"
                    "padding:.6rem;text-align:center;height:100%'>"
                    "<div style='font-size:1.4rem'>😴</div>"
                    "<div style='font-size:.75rem;color:#64748B'>No streak</div></div>",
                    unsafe_allow_html=True,
                )

        with c2:
            if best_pk is not None:
                hf = get_flag(best_pk['home_team'])
                af = get_flag(best_pk['away_team'])
                picked_flag = hf if best_pk['picked_team'] == best_pk['home_team'] else af
                st.markdown(
                    f"<div style='background:rgba(74,222,128,.1);border-radius:12px;"
                    f"padding:.6rem;text-align:center;height:100%'>"
                    f"<div style='font-size:1.4rem'>⭐</div>"
                    f"<div style='font-size:.75rem;font-weight:800;color:#4ADE80'>Best Pick</div>"
                    f"<div style='font-size:.7rem;color:var(--text-color);margin:.15rem 0'>"
                    f"{picked_flag} {best_pk['picked_team']}</div>"
                    f"<div style='font-size:.6rem;color:#64748B'>"
                    f"{hf} {best_pk['home_team']} vs {af} {best_pk['away_team']}</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='background:rgba(148,163,184,.08);border-radius:12px;"
                    "padding:.6rem;text-align:center;height:100%'>"
                    "<div style='font-size:1.4rem'>⭐</div>"
                    "<div style='font-size:.75rem;color:#64748B'>Best Pick</div>"
                    "<div style='font-size:.6rem;color:#475569;margin-top:.2rem'>Pending results</div></div>",
                    unsafe_allow_html=True,
                )

        with c3:
            if worst_pk is not None:
                hf = get_flag(worst_pk['home_team'])
                af = get_flag(worst_pk['away_team'])
                picked_flag = hf if worst_pk['picked_team'] == worst_pk['home_team'] else af
                st.markdown(
                    f"<div style='background:rgba(248,113,113,.1);border-radius:12px;"
                    f"padding:.6rem;text-align:center;height:100%'>"
                    f"<div style='font-size:1.4rem'>❌</div>"
                    f"<div style='font-size:.75rem;font-weight:800;color:#F87171'>Biggest Miss</div>"
                    f"<div style='font-size:.7rem;color:var(--text-color);margin:.15rem 0'>"
                    f"{picked_flag} {worst_pk['picked_team']}</div>"
                    f"<div style='font-size:.6rem;color:#64748B'>"
                    f"{hf} {worst_pk['home_team']} vs {af} {worst_pk['away_team']}</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='background:rgba(148,163,184,.08);border-radius:12px;"
                    "padding:.6rem;text-align:center;height:100%'>"
                    "<div style='font-size:1.4rem'>❌</div>"
                    "<div style='font-size:.75rem;color:#64748B'>Biggest Miss</div>"
                    "<div style='font-size:.6rem;color:#475569;margin-top:.2rem'>Pending results</div></div>",
                    unsafe_allow_html=True,
                )

    # ── Best Countries ────────────────────────────────────────────────────────
    best_ctys = _best_countries_for_user(completed_up, user_picks)
    st.markdown(f"#### 🌎 Best Countries for {active_user}")
    if not best_ctys:
        st.caption("No winning countries yet — keep picking!")
    else:
        fc_cols = st.columns(min(len(best_ctys), 5))
        for i, (team, pts, cnt) in enumerate(best_ctys):
            flag = get_flag(team)
            pts_label = f"{pts:.0f}" if pts == int(pts) else f"{pts:.1f}"
            with fc_cols[i]:
                st.markdown(
                    f"<div style='text-align:center;background:rgba(148,163,184,.07);"
                    f"border-radius:10px;padding:.4rem .3rem'>"
                    f"<div style='font-size:1.8rem;line-height:1'>{flag}</div>"
                    f"<div style='font-size:.72rem;font-weight:700;color:var(--text-color)'>{team}</div>"
                    f"<div style='font-size:.65rem;color:#4ADE80;font-weight:700'>"
                    f"{pts_label} pt{'s' if pts != 1.0 else ''}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Match list ────────────────────────────────────────────────────────────
    if user_picks.empty:
        st.info(f"{active_user} hasn't made any picks yet — head to the Schedule to get started!")
    else:
        st.markdown("#### 📋 All Picks")
        user_picks = user_picks.copy()
        user_picks['pt_date'] = user_picks.apply(
            lambda r: pt_date_str(r['match_date'], r['kickoff_time_et']), axis=1
        )
        for pt_date_val, day_picks in user_picks.groupby('pt_date'):
            st.markdown(f"**📅 {fmt_date(pt_date_val)}**")
            for _, pk in day_picks.iterrows():
                hf           = get_flag(pk['home_team'])
                af           = get_flag(pk['away_team'])
                picked_home  = pk['picked_team'] == pk['home_team']
                time_str     = fmt_match_time(pk['match_date'], pk['kickoff_time_et'])

                if pk['status'] == 'completed':
                    pts = pick_result(pk['picked_team'], pk['home_team'], pk['away_team'],
                                      pk['home_score'], pk['away_score'])
                    hs, as_   = int(pk['home_score']), int(pk['away_score'])
                    score_str = f"{hs}–{as_}"
                    if pts == 1.0:   badge, bc = "🟢 +1",   "#4ADE80"
                    elif pts == 0.5: badge, bc = "🟡 +½",   "#FCD34D"
                    else:            badge, bc = "🔴 +0",   "#F87171"
                else:
                    score_str, badge, bc = "vs", "⏳", "#94A3B8"

                hs = "font-weight:900;color:#FCD34D" if picked_home else "color:#64748B"
                as_ = "font-weight:900;color:#FCD34D" if not picked_home else "color:#64748B"

                st.markdown(
                    f"<div style='border-radius:10px;padding:.4rem .9rem;margin:.2rem 0;"
                    f"border:1px solid rgba(128,128,128,.15)'>"
                    f"<div style='display:flex;align-items:center;gap:.4rem'>"
                    f"<div style='flex:1;font-size:.85rem;{hs}'>{hf} {pk['home_team']}</div>"
                    f"<div style='color:#64748B;font-size:.82rem'>{score_str}</div>"
                    f"<div style='flex:1;text-align:right;font-size:.85rem;{as_}'>"
                    f"{pk['away_team']} {af}</div>"
                    f"</div>"
                    f"<div style='display:flex;justify-content:space-between;margin-top:.15rem'>"
                    f"<div style='font-size:.62rem;color:#64748B'>Group {pk['group_letter']} · {time_str}</div>"
                    f"<div style='font-size:.75rem;color:{bc};font-weight:700'>{badge}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
