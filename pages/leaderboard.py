import streamlit as st
import pandas as pd
from datetime import date
from services.scoring import get_leaderboard, pick_result
from services.picks import get_all_picks
from services.teams import get_flag
from services.passport import get_top_favorites, get_discoveries
from services.achievements import get_user_achievements

st.markdown("## 🏆 Leaderboard")
st.caption("FIFA World Cup 2026 · Family standings")

board          = get_leaderboard()
all_picks      = get_all_picks()
today_str      = date.today().isoformat()
active_user_id = st.session_state.get("active_user_id", 1)

# ── Dense (competition-style) rank with tie support ───────────────────────────
board = board.sort_values(['total_points', 'name'], ascending=[False, True]).reset_index(drop=True)
board['rank'] = board['total_points'].rank(method='min', ascending=False).astype(int)

no_scored = int(board['total_picks'].sum()) == 0
if no_scored:
    st.info("No matches have been scored yet — check back after the first kick-off!", icon="⏳")

# ── Previous rank (before today's matches) for movement arrows ────────────────
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


# ── Per-user rich extras ──────────────────────────────────────────────────────
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

    # Win streak — consecutive correct picks from most recent backwards
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

    # Recent picks (last 8, newest first)
    recent: list[str] = []
    for _, pk in done.head(8).iterrows():
        pts  = pick_result(
            pk['picked_team'], pk['home_team'], pk['away_team'],
            pk['home_score'], pk['away_score'],
        )
        flag = get_flag(pk['picked_team'])
        icon = "✅" if pts == 1.0 else "🤝" if pts == 0.5 else "❌"
        recent.append(f"{flag}&thinsp;{icon}")

    # Favorite country
    favs    = get_top_favorites(uid, 1)
    fav_str = f"{get_flag(favs[0])} {favs[0]}" if favs else ""

    # Discovery count
    disc_df      = get_discoveries(uid)
    n_discovered = len(disc_df) if not disc_df.empty else 0

    # Achievement count
    uach         = get_user_achievements(uid)
    n_ach        = len(uach) if not uach.empty else 0

    return {
        'streak': streak,
        'perfect': perfect,
        'recent': recent,
        'fav_str': fav_str,
        'n_done': n_done,
        'n_discovered': n_discovered,
        'n_ach': n_ach,
    }


# ── Render each player card ───────────────────────────────────────────────────
for _, row in board.iterrows():
    uid  = int(row['id'])
    rank = int(row['rank'])
    pts  = float(row['total_points'])
    ex   = _extras(uid, row)

    # Rank-based styling
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

    # Movement vs. yesterday's standing
    prev_r    = _prev_rank.get(uid, rank)
    move_diff = prev_r - rank          # positive = climbed, negative = dropped
    if move_diff > 0:
        movement   = f"⬆️ +{move_diff}"
        move_color = "#4ADE80"
    elif move_diff < 0:
        movement   = f"⬇️ {move_diff}"
        move_color = "#F87171"
    else:
        movement   = "➖"
        move_color = "#475569"

    # Streak line
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

    # Perfect badge — extracted string to avoid nested-quote issues
    perfect_badge = (
        " <span style='font-size:.7rem;color:#4ADE80;font-weight:700;"
        "background:rgba(74,222,128,.15);border-radius:6px;"
        "padding:.1rem .3rem'>🏅 Perfect</span>"
        if ex['perfect'] else ""
    )

    # Favorite country line
    fav_str  = ex['fav_str']
    fav_line = (
        f"<div style='font-size:.78rem;color:#94A3B8;margin-top:.04rem'>❤️ {fav_str}</div>"
        if fav_str else ""
    )

    # Stats chips: two rows for readability
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

    # Recent picks row (up to 8, compact)
    if ex['recent']:
        picks_items = " ".join(
            f"<span style='display:inline-block;font-size:.82rem'>{p}</span>"
            for p in ex['recent']
        )
        recent_row = (
            f"<div style='margin-top:.4rem;padding-top:.35rem;"
            f"border-top:1px solid rgba(148,163,184,.12);"
            f"display:flex;align-items:center;gap:.4rem;flex-wrap:wrap'>"
            f"<span style='font-size:.6rem;font-weight:800;color:#475569;text-transform:uppercase;"
            f"letter-spacing:.05em'>Recent:</span>{picks_items}</div>"
        )
    else:
        recent_row = ""

    # Active user highlight + tie indicator
    is_active  = uid == active_user_id
    active_glow = (
        ";box-shadow:0 0 0 2px rgba(147,197,253,.5),0 0 18px rgba(147,197,253,.12)"
        if is_active else ""
    )
    tied_count  = int((board['rank'] == rank).sum())
    tie_badge   = (
        "<div style='font-size:.52rem;color:#94A3B8;text-transform:uppercase;"
        "letter-spacing:.04em;margin-top:.1rem'>TIE</div>"
        if tied_count > 1 else ""
    )

    # Extract plain strings for safe f-string embedding
    p_name   = str(row['name'])
    p_avatar = str(row['avatar'])
    pts_fmt  = f"{pts:.1f}"

    st.markdown(
        f"<div style='background:{bg};border:2px solid {border};"
        f"border-radius:16px;padding:.9rem 1.2rem;margin:.45rem 0{active_glow}'>"

        # Main row
        f"<div style='display:flex;align-items:center;gap:1rem'>"

        # Rank column: crown · medal · movement · tie
        f"<div style='text-align:center;min-width:2.6rem;flex-shrink:0'>"
        f"<div style='font-size:.95rem;line-height:1.1'>{crown}</div>"
        f"<div style='font-size:1.5rem;font-weight:900;color:{pts_color};line-height:1'>{medal}</div>"
        f"<div style='font-size:.66rem;color:{move_color};margin-top:.1rem'>{movement}</div>"
        f"{tie_badge}"
        f"</div>"

        # Avatar
        f"<div style='font-size:3rem;line-height:1;flex-shrink:0'>{p_avatar}</div>"

        # Name · streak · favorite
        f"<div style='flex:1;min-width:0'>"
        f"<div style='font-size:1.15rem;font-weight:900;color:#F1F5F9'>{p_name}{perfect_badge}</div>"
        f"<div style='margin:.08rem 0;font-size:.82rem'>{streak_html}</div>"
        f"{fav_line}"
        f"{stats_row}"
        f"</div>"

        # Points
        f"<div style='text-align:center;flex-shrink:0'>"
        f"<div style='font-size:2.3rem;font-weight:900;color:{pts_color};line-height:1'>{pts_fmt}</div>"
        f"<div style='font-size:.68rem;color:#94A3B8;text-transform:uppercase;"
        f"letter-spacing:.05em'>pts</div>"
        f"</div>"

        f"</div>"  # end main row
        + recent_row
        + "</div>",
        unsafe_allow_html=True,
    )

# ── Scoring footer ────────────────────────────────────────────────────────────
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
