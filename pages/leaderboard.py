import streamlit as st
import pandas as pd
from datetime import date
from services.scoring import get_leaderboard, get_combined_leaderboard, pick_result
from services.picks import get_all_picks
from services.teams import get_flag
from services.passport import get_top_favorites, get_discoveries
from services.achievements import get_user_achievements

st.markdown("## 🏆 Leaderboard")
st.caption("FIFA World Cup 2026 · Family standings")

_tab_ko, _tab_total, _tab_group = st.tabs(["🏆 Knockout", "📊 Total Score", "⚽ Group Stage"])

# ══════════════════════════════════════════════════════════════════════════════
# 🏆 KNOCKOUT TAB (default)
# ══════════════════════════════════════════════════════════════════════════════

with _tab_ko:
    _ko_active_uid = st.session_state.get("active_user_id", 1)
    _ko_combined = get_combined_leaderboard()

    if not _ko_combined:
        st.info("No knockout picks scored yet — picks open for each round as teams advance.")
    else:
        _ko_sorted = sorted(_ko_combined, key=lambda e: (-e["ko_live_pts"], e["name"]))
        _ko_any_pts = any(e["ko_live_pts"] > 0 for e in _ko_sorted)
        if not _ko_any_pts:
            st.info("No knockout matches scored yet — Knockout picks earn points when results are entered.")

        _ko_medals = ["🥇", "🥈", "🥉"]
        _ko_rank = 1
        for _ki, _ke in enumerate(_ko_sorted):
            if _ki > 0 and _ke["ko_live_pts"] < _ko_sorted[_ki - 1]["ko_live_pts"]:
                _ko_rank = _ki + 1
            _ko_medal = _ko_medals[_ko_rank - 1] if _ko_rank <= 3 else f"#{_ko_rank}"
            _ko_uid   = _ke["user_id"]
            _ko_is_me = _ko_uid == _ko_active_uid
            _ko_glow  = ";box-shadow:0 0 0 2px rgba(147,197,253,.5)" if _ko_is_me else ""

            if _ko_rank == 1:
                _ko_bg, _ko_border, _ko_ptc = (
                    "linear-gradient(135deg,#78350F,#92400E)", "#F59E0B", "#FCD34D"
                )
            elif _ko_rank == 2:
                _ko_bg, _ko_border, _ko_ptc = (
                    "linear-gradient(135deg,#1E293B,#334155)", "#94A3B8", "#E2E8F0"
                )
            elif _ko_rank == 3:
                _ko_bg, _ko_border, _ko_ptc = (
                    "linear-gradient(135deg,#1C1917,#292524)", "#CD7F32", "#E2E8F0"
                )
            else:
                _ko_bg, _ko_border, _ko_ptc = (
                    "linear-gradient(160deg,#1E293B,#0F172A)",
                    "rgba(148,163,184,.18)", "#E2E8F0"
                )

            st.markdown(
                f"<div style='background:{_ko_bg};border:2px solid {_ko_border};"
                f"border-radius:14px;padding:.75rem 1.1rem;margin:.35rem 0{_ko_glow}'>"
                f"<div style='display:flex;align-items:center;gap:.9rem'>"
                f"<div style='font-size:1.5rem;font-weight:900;color:{_ko_ptc};"
                f"min-width:2rem;text-align:center;flex-shrink:0'>{_ko_medal}</div>"
                f"<div style='font-size:2.4rem;line-height:1;flex-shrink:0'>{_ke['avatar']}</div>"
                f"<div style='flex:1;min-width:0'>"
                f"<div style='font-size:1.05rem;font-weight:900;color:#F1F5F9'>{_ke['name']}</div>"
                f"<div style='font-size:.75rem;color:#94A3B8;margin-top:.15rem'>"
                f"Group: {_ke['group_pts']:.1f} pts</div>"
                f"</div>"
                f"<div style='text-align:center;flex-shrink:0'>"
                f"<div style='font-size:2rem;font-weight:900;color:{_ko_ptc};line-height:1'>"
                f"{_ke['ko_live_pts']:.0f}</div>"
                f"<div style='font-size:.65rem;color:#94A3B8;text-transform:uppercase;"
                f"letter-spacing:.05em'>KO pts</div>"
                f"</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

        # Scoring legend
        st.markdown(
            "<div style='margin-top:1.2rem;padding:.7rem 1rem;"
            "background:rgba(255,255,255,.04);border-radius:10px;"
            "border:1px solid rgba(148,163,184,.12)'>"
            "<div style='font-size:.75rem;color:#64748B;font-weight:700;"
            "text-transform:uppercase;letter-spacing:.05em;margin-bottom:.25rem'>Knockout scoring</div>"
            "<div style='font-size:.8rem;color:#94A3B8;display:flex;gap:1.2rem;flex-wrap:wrap'>"
            "<span>R32 = <b style='color:#F1F5F9'>2 pts</b></span>"
            "<span>R16 = <b style='color:#F1F5F9'>3 pts</b></span>"
            "<span>QF = <b style='color:#F1F5F9'>4 pts</b></span>"
            "<span>SF = <b style='color:#F1F5F9'>5 pts</b></span>"
            "<span>Final = <b style='color:#F1F5F9'>8 pts</b></span>"
            "</div></div>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# ⚽ GROUP STAGE TAB
# ══════════════════════════════════════════════════════════════════════════════

with _tab_group:
    board          = get_leaderboard()
    all_picks      = get_all_picks()
    today_str      = date.today().isoformat()
    active_user_id = st.session_state.get("active_user_id", 1)

    # Dense (competition-style) rank with tie support
    board = board.sort_values(['total_points', 'name'], ascending=[False, True]).reset_index(drop=True)
    board['rank'] = board['total_points'].rank(method='min', ascending=False).astype(int)

    no_scored = int(board['total_picks'].sum()) == 0
    if no_scored:
        st.info("No matches have been scored yet — check back after the first kick-off!", icon="⏳")

    # Previous rank (before today's matches) for movement arrows
    _prev_rank: dict[int, int] = {}
    if not all_picks.empty:
        _prev = all_picks[
            (all_picks['status'] == 'completed') &
            (all_picks['match_date'] < today_str)
        ].copy()
        if not _prev.empty:
            _prev['_p'] = _prev.apply(
                lambda r: pick_result(r['picked_team'], r['home_team'], r['away_team'],
                                      r['home_score'], r['away_score']) or 0.0,
                axis=1,
            )
            _prev_agg  = _prev.groupby('user_id')['_p'].sum().to_dict()
            _prev_pts  = {int(uid): float(_prev_agg.get(int(uid), 0.0)) for uid in board['id']}
        else:
            _prev_pts  = {int(uid): 0.0 for uid in board['id']}

        _uniq = sorted(set(_prev_pts.values()), reverse=True)
        for uid, p in _prev_pts.items():
            _prev_rank[uid] = _uniq.index(p) + 1
    else:
        for _, r in board.iterrows():
            _prev_rank[int(r['id'])] = int(r['rank'])

    # Per-user rich extras
    def _extras(uid: int, row) -> dict:
        upicks = (
            all_picks[all_picks['user_id'] == uid]
            if not all_picks.empty
            else pd.DataFrame()
        )
        done = (
            upicks[upicks['status'] == 'completed']
            .sort_values('match_date', ascending=False)
            if not upicks.empty
            else pd.DataFrame()
        )

        # Win streak
        streak = 0
        if not done.empty:
            for _, pk in done.iterrows():
                pts = pick_result(
                    pk['picked_team'], pk['home_team'], pk['away_team'],
                    pk['home_score'], pk['away_score'],
                )
                if pts is not None and pts > 0:
                    streak += 1
                else:
                    break

        # Perfect: no losses among completed picks
        n_done   = len(done)
        n_losses = n_done - int(row['correct_picks']) - int(row['draw_points'])
        perfect  = n_done > 0 and n_losses == 0

        # Best picks: top 4 teams by total points earned in group stage
        from collections import defaultdict
        _team_pts: dict[str, float] = defaultdict(float)
        for _, pk in done.iterrows():
            pts = pick_result(
                pk['picked_team'], pk['home_team'], pk['away_team'],
                pk['home_score'], pk['away_score'],
            )
            if pts is not None and pts > 0:
                _team_pts[pk['picked_team']] += pts
        best_picks = [t for t, _ in sorted(_team_pts.items(), key=lambda x: -x[1])[:4]]

        # Favorite country
        favs    = get_top_favorites(uid, 1)
        fav_str = f"{get_flag(favs[0])} {favs[0]}" if favs else ""

        # Discovery count
        disc_df      = get_discoveries(uid)
        n_discovered = len(disc_df) if not disc_df.empty else 0

        # Achievement count
        uach  = get_user_achievements(uid)
        n_ach = len(uach) if not uach.empty else 0

        return {
            'streak': streak,
            'perfect': perfect,
            'best_picks': best_picks,
            'fav_str': fav_str,
            'n_done': n_done,
            'n_discovered': n_discovered,
            'n_ach': n_ach,
        }

    # Render each player card
    for _, row in board.iterrows():
        uid  = int(row['id'])
        rank = int(row['rank'])
        pts  = float(row['total_points'])
        ex   = _extras(uid, row)

        if rank == 1:
            medal, bg, border, pts_color = (
                "🥇",
                "linear-gradient(135deg,#78350F,#92400E)",
                "#F59E0B",
                "#FCD34D",
            )
            crown = "👑"
        elif rank == 2:
            medal, bg, border, pts_color = (
                "🥈",
                "linear-gradient(135deg,#1E293B,#334155)",
                "#94A3B8",
                "#E2E8F0",
            )
            crown = ""
        elif rank == 3:
            medal, bg, border, pts_color = (
                "🥉",
                "linear-gradient(135deg,#1C1917,#292524)",
                "#CD7F32",
                "#E2E8F0",
            )
            crown = ""
        else:
            medal, bg, border, pts_color = (
                f"#{rank}",
                "linear-gradient(160deg,#1E293B,#0F172A)",
                "rgba(148,163,184,.18)",
                "#E2E8F0",
            )
            crown = ""

        prev_r    = _prev_rank.get(uid, rank)
        move_diff = prev_r - rank
        if move_diff > 0:
            movement   = f"⬆️ +{move_diff}"
            move_color = "#4ADE80"
        elif move_diff < 0:
            movement   = f"⬇️ {move_diff}"
            move_color = "#F87171"
        else:
            movement   = "➖"
            move_color = "#475569"

        if ex['n_done'] == 0:
            streak_html = "<span style='color:#475569'>No picks scored yet</span>"
        elif ex['streak'] == 0:
            streak_html = "<span style='color:#94A3B8'>❄️ Looking for a win</span>"
        elif ex['streak'] >= 3:
            s = ex['streak']
            streak_html = f"<span style='color:#F97316'>🔥 {s} in a row!</span>"
        else:
            s = ex['streak']
            streak_html = f"<span style='color:#FCD34D'>🔥 {s} in a row</span>"

        perfect_badge = (
            " <span style='font-size:.7rem;color:#4ADE80;font-weight:700;"
            "background:rgba(74,222,128,.15);border-radius:6px;"
            "padding:.1rem .3rem'>🏅 Perfect</span>"
            if ex['perfect'] else ""
        )

        fav_str  = ex['fav_str']
        fav_line = (
            f"<div style='font-size:.78rem;color:#94A3B8;margin-top:.04rem'>❤️ {fav_str}</div>"
            if fav_str else ""
        )

        n_correct = int(row['correct_picks'])
        n_draws   = int(row['draw_points'])
        stats_row = (
            f"<div style='display:flex;gap:.55rem;margin-top:.3rem;flex-wrap:wrap'>"
            f"<span style='font-size:.72rem;color:#4ADE80'>✅ {n_correct} wins</span>"
            f"<span style='font-size:.72rem;color:#FCD34D'>🤝 {n_draws} draws</span>"
            f"<span style='font-size:.72rem;color:#60A5FA'>🗺️ {ex['n_discovered']} explored</span>"
            f"<span style='font-size:.72rem;color:#A78BFA'>🏅 {ex['n_ach']} badges</span>"
            f"</div>"
        )

        if ex['best_picks']:
            best_items = " · ".join(
                f"{get_flag(t)}&thinsp;{t}" for t in ex['best_picks']
            )
            recent_row = (
                f"<div style='margin-top:.4rem;padding-top:.35rem;"
                f"border-top:1px solid rgba(148,163,184,.12);font-size:.78rem;color:#94A3B8'>"
                f"<span style='font-size:.6rem;font-weight:800;color:#475569;"
                f"text-transform:uppercase;letter-spacing:.05em'>Best picks: </span>"
                f"{best_items}</div>"
            )
        else:
            recent_row = ""

        is_active   = uid == active_user_id
        active_glow = (
            ";box-shadow:0 0 0 2px rgba(147,197,253,.5),0 0 18px rgba(147,197,253,.12)"
            if is_active else ""
        )
        tied_count = int((board['rank'] == rank).sum())
        tie_badge  = (
            "<div style='font-size:.52rem;color:#94A3B8;text-transform:uppercase;"
            "letter-spacing:.04em;margin-top:.1rem'>TIE</div>"
            if tied_count > 1 else ""
        )

        p_name   = str(row['name'])
        p_avatar = str(row['avatar'])
        pts_fmt  = f"{pts:.1f}"

        st.markdown(
            f"<div style='background:{bg};border:2px solid {border};"
            f"border-radius:16px;padding:.9rem 1.2rem;margin:.45rem 0{active_glow}'>"
            f"<div style='display:flex;align-items:center;gap:1rem'>"
            f"<div style='text-align:center;min-width:2.6rem;flex-shrink:0'>"
            f"<div style='font-size:.95rem;line-height:1.1'>{crown}</div>"
            f"<div style='font-size:1.5rem;font-weight:900;color:{pts_color};line-height:1'>{medal}</div>"
            f"<div style='font-size:.66rem;color:{move_color};margin-top:.1rem'>{movement}</div>"
            f"{tie_badge}"
            f"</div>"
            f"<div style='font-size:3rem;line-height:1;flex-shrink:0'>{p_avatar}</div>"
            f"<div style='flex:1;min-width:0'>"
            f"<div style='font-size:1.15rem;font-weight:900;color:#F1F5F9'>{p_name}{perfect_badge}</div>"
            f"<div style='margin:.08rem 0;font-size:.82rem'>{streak_html}</div>"
            f"{fav_line}"
            f"{stats_row}"
            f"</div>"
            f"<div style='text-align:center;flex-shrink:0'>"
            f"<div style='font-size:2.3rem;font-weight:900;color:{pts_color};line-height:1'>{pts_fmt}</div>"
            f"<div style='font-size:.68rem;color:#94A3B8;text-transform:uppercase;"
            f"letter-spacing:.05em'>pts</div>"
            f"</div>"
            f"</div>"
            + recent_row
            + "</div>",
            unsafe_allow_html=True,
        )

    # Scoring footer
    st.markdown(
        "<div style='margin-top:1.5rem;padding:.75rem 1rem;"
        "background:rgba(255,255,255,.04);border-radius:10px;"
        "border:1px solid rgba(148,163,184,.12)'>"
        "<div style='font-size:.75rem;color:#64748B;font-weight:700;"
        "text-transform:uppercase;letter-spacing:.05em;margin-bottom:.3rem'>Scoring</div>"
        "<div style='font-size:.82rem;color:#94A3B8;display:flex;gap:1.5rem;flex-wrap:wrap'>"
        "<span>✅ Correct Winner = <b style='color:#F1F5F9'>1 point</b></span>"
        "<span>🤝 Draw = <b style='color:#F1F5F9'>½ point</b></span>"
        "<span>❌ Wrong Pick = <b style='color:#F1F5F9'>0 points</b></span>"
        "</div></div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 📊 TOTAL SCORE TAB
# ══════════════════════════════════════════════════════════════════════════════

with _tab_total:
    active_user_id_cb = st.session_state.get("active_user_id", 1)

    combined = get_combined_leaderboard()
    if not combined:
        st.info("No scores yet.")
    else:
        # Header blurb
        st.markdown(
            "<div style='font-size:.85rem;color:#94A3B8;margin-bottom:.75rem'>"
            "Total = Group Stage picks + Knockout picks"
            "</div>",
            unsafe_allow_html=True,
        )

        medals = ["🥇", "🥈", "🥉"]

        for entry in combined:
            uid   = entry["user_id"]
            rank  = entry["rank"]
            medal = medals[rank - 1] if rank <= 3 else f"#{rank}"
            grp   = entry["group_pts"]
            ko    = entry["ko_live_pts"]
            total = entry["total_pts"]

            is_active   = uid == active_user_id_cb
            active_glow = (
                ";box-shadow:0 0 0 2px rgba(147,197,253,.5)"
                if is_active else ""
            )

            if rank == 1:
                bg, border, pts_color = (
                    "linear-gradient(135deg,#78350F,#92400E)",
                    "#F59E0B", "#FCD34D",
                )
            elif rank == 2:
                bg, border, pts_color = (
                    "linear-gradient(135deg,#1E293B,#334155)",
                    "#94A3B8", "#E2E8F0",
                )
            elif rank == 3:
                bg, border, pts_color = (
                    "linear-gradient(135deg,#1C1917,#292524)",
                    "#CD7F32", "#E2E8F0",
                )
            else:
                bg, border, pts_color = (
                    "linear-gradient(160deg,#1E293B,#0F172A)",
                    "rgba(148,163,184,.18)", "#E2E8F0",
                )

            p_name   = str(entry["name"])
            p_avatar = str(entry["avatar"])

            st.markdown(
                f"<div style='background:{bg};border:2px solid {border};"
                f"border-radius:14px;padding:.75rem 1.1rem;margin:.35rem 0{active_glow}'>"
                f"<div style='display:flex;align-items:center;gap:.9rem'>"

                # Rank
                f"<div style='font-size:1.5rem;font-weight:900;color:{pts_color};"
                f"min-width:2rem;text-align:center;flex-shrink:0'>{medal}</div>"

                # Avatar
                f"<div style='font-size:2.4rem;line-height:1;flex-shrink:0'>{p_avatar}</div>"

                # Name + breakdown chips
                f"<div style='flex:1;min-width:0'>"
                f"<div style='font-size:1.05rem;font-weight:900;color:#F1F5F9'>{p_name}</div>"
                f"<div style='display:flex;gap:.6rem;margin-top:.25rem;flex-wrap:wrap'>"
                f"<span style='font-size:.75rem;color:#86EFAC'>⚽ Group: <b>{grp:.1f}</b></span>"
                f"<span style='font-size:.75rem;color:#7DD3FC'>🏆 Knockout: <b>{ko:.0f}</b></span>"
                f"</div>"
                f"</div>"

                # Total
                f"<div style='text-align:center;flex-shrink:0'>"
                f"<div style='font-size:2rem;font-weight:900;color:{pts_color};line-height:1'>"
                f"{total:.1f}</div>"
                f"<div style='font-size:.65rem;color:#94A3B8;text-transform:uppercase;"
                f"letter-spacing:.05em'>total</div>"
                f"</div>"

                f"</div></div>",
                unsafe_allow_html=True,
            )

        # Scoring legend
        st.markdown(
            "<div style='margin-top:1.2rem;padding:.7rem 1rem;"
            "background:rgba(255,255,255,.04);border-radius:10px;"
            "border:1px solid rgba(148,163,184,.12)'>"
            "<div style='font-size:.75rem;color:#64748B;font-weight:700;"
            "text-transform:uppercase;letter-spacing:.05em;margin-bottom:.3rem'>Scoring breakdown</div>"
            "<div style='font-size:.8rem;color:#94A3B8;display:flex;gap:1.2rem;flex-wrap:wrap'>"
            "<span>⚽ <b style='color:#86EFAC'>Group</b>: 1 pt/win, ½ draw</span>"
            "<span>🎯 <b style='color:#7DD3FC'>Knockout</b>: R32=2 · R16=3 · QF=4 · SF=5 · Final=8</span>"
            "</div></div>",
            unsafe_allow_html=True,
        )
