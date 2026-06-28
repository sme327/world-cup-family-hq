"""Bracket Picks page — each user fills out a complete knockout bracket.

Three tabs:
  🎯 My Bracket     — interactive picker (round-by-round subtabs)
  👀 Family Brackets — read-only view of others' brackets (locked only)
  📊 Family Comparison — champion / finalist / semifinalists grid
"""
import streamlit as st

from services.bracket_picks import (
    EXCLUDED_MATCHES,
    FINAL_MATCH_ID,
    QF_MATCH_IDS,
    REQUIRED_PICKS,
    ROUND_LABELS,
    ROUND_ORDER,
    SF_MATCH_IDS,
    clear_bracket_picks,
    compute_pick_bracket,
    get_actual_results,
    get_bracket_leaderboard,
    get_bracket_lock,
    get_bracket_picks,
    get_bracket_status_all_users,
    get_team_map,
    is_bracket_complete,
    is_bracket_submitted,
    save_bracket_pick,
    score_bracket,
    submit_bracket,
    unsubmit_bracket,
)
from services.database import get_connection

# ── Page setup ─────────────────────────────────────────────────────────────────

st.set_page_config(layout="wide")

user_id   = st.session_state.get("active_user_id", 1)
user_name = st.session_state.get("active_user_name", "You")
user_avatar = st.session_state.get("active_user_avatar", "⚽")

lock      = get_bracket_lock()
is_locked = lock["is_locked"]

# ── Shared helpers ─────────────────────────────────────────────────────────────

def _all_users() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, avatar, theme_color FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "avatar": r[2], "color": r[3]} for r in rows]


def _bonus_label(mid: int) -> str:
    if mid == FINAL_MATCH_ID:
        return " 🏆 +5 champion bonus"
    if mid in QF_MATCH_IDS:
        return " ⭐ +2 semifinalist bonus"
    return ""


def _result_indicator(mid: int, picked_id: int | None, actual_results: dict) -> str:
    """Return ✅ / ❌ / 🔵 based on actual results."""
    if mid not in actual_results:
        return "🔵"  # Not yet played
    actual = actual_results[mid]
    if picked_id is None:
        return "—"
    return "✅" if picked_id == actual else "❌"


# ── Match card ─────────────────────────────────────────────────────────────────

def _match_card(
    uid: int,
    m: dict,
    allow_edit: bool,
    actual_results: dict | None = None,
    show_result: bool = False,
) -> None:
    """Render one match pick card."""
    mid       = m["match_id"]
    home_id   = m["home_team_id"]
    away_id   = m["away_team_id"]
    home_name = m["home_name"] or "TBD"
    away_name = m["away_name"] or "TBD"
    home_flag = m["home_flag"] or "⬜"
    away_flag = m["away_flag"] or "⬜"
    picked_id = m["picked_team_id"]

    home_picked = picked_id is not None and picked_id == home_id
    away_picked = picked_id is not None and picked_id == away_id
    can_edit    = allow_edit and bool(home_id and away_id)

    # Result overlay (when viewing completed results)
    result_badge = ""
    if show_result and actual_results is not None:
        result_badge = _result_indicator(mid, picked_id, actual_results)

    with st.container(border=True):
        bonus = _bonus_label(mid)
        label = f"Match {m['match_number']}{bonus}"
        if result_badge:
            label = f"{result_badge} {label}"
        st.caption(label)

        # Home team button
        h_label = f"{home_flag} {home_name}"
        h_type  = "primary" if home_picked else "secondary"
        h_disabled = (not can_edit) or (not home_id)
        if st.button(
            h_label,
            key=f"bp_{uid}_{mid}_h",
            type=h_type,
            use_container_width=True,
            disabled=h_disabled,
        ):
            if not home_picked and can_edit:
                try:
                    save_bracket_pick(uid, mid, home_id)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

        # Away team button
        a_label = f"{away_flag} {away_name}"
        a_type  = "primary" if away_picked else "secondary"
        a_disabled = (not can_edit) or (not away_id)
        if st.button(
            a_label,
            key=f"bp_{uid}_{mid}_a",
            type=a_type,
            use_container_width=True,
            disabled=a_disabled,
        ):
            if not away_picked and can_edit:
                try:
                    save_bracket_pick(uid, mid, away_id)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))


# ── Round section ──────────────────────────────────────────────────────────────

def _render_round(uid: int, pick_bracket: dict, rnd: str, allow_edit: bool) -> None:
    """Render all matches for one round in a responsive grid."""
    matches = sorted(
        [m for m in pick_bracket.values() if m["round"] == rnd],
        key=lambda m: m["bracket_slot"],
    )
    if not matches:
        st.info("No matches for this round.")
        return

    # Determine column count based on round
    ncols = min(4, max(1, len(matches) // 2)) if rnd != "final" else 1
    if rnd == "sf":
        ncols = 2

    cols = st.columns(ncols)
    for i, m in enumerate(matches):
        with cols[i % ncols]:
            _match_card(uid, m, allow_edit)


# ── My Bracket tab ─────────────────────────────────────────────────────────────

def _my_bracket() -> None:
    pick_count = len(get_bracket_picks(user_id))
    complete   = pick_count >= REQUIRED_PICKS
    submitted  = is_bracket_submitted(user_id)

    # Status bar
    progress = pick_count / REQUIRED_PICKS
    st.progress(progress, text=f"{pick_count} / {REQUIRED_PICKS} picks made")

    # Action buttons
    btn_cols = st.columns([2, 2, 2, 2])

    if is_locked:
        btn_cols[0].info("🔒 Brackets locked — picks are frozen.")
    elif submitted:
        if btn_cols[0].button("✏️ Edit Bracket", use_container_width=True):
            try:
                unsubmit_bracket(user_id)
                st.success("Bracket reopened for editing.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
        btn_cols[1].success("✅ Submitted!")
    else:
        if complete:
            if btn_cols[0].button(
                "✅ Submit Bracket",
                type="primary",
                use_container_width=True,
            ):
                ok, msg = submit_bracket(user_id)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        else:
            btn_cols[0].warning(f"⏳ {REQUIRED_PICKS - pick_count} picks remaining")

        if pick_count > 0:
            if btn_cols[3].button(
                "🗑️ Clear All",
                use_container_width=True,
                help="Remove all your bracket picks and start over.",
            ):
                try:
                    clear_bracket_picks(user_id)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    # Scoring blurb
    with st.expander("📖 How scoring works", expanded=False):
        st.markdown("""
| What | Points |
|------|--------|
| Correct pick (any round) | **+1 pt** |
| Correct Quarterfinal winner (reaches Semis) | **+3 pts total** (1 + 2 bonus) |
| Correct Champion (Final winner) | **+6 pts total** (1 + 5 bonus) |
| **Maximum possible** | **44 pts** |
        """)

    st.divider()

    # Round-by-round subtabs
    allow_edit = not is_locked

    pick_bracket = compute_pick_bracket(user_id)
    actual_results = get_actual_results()

    tab_labels = [f"{ROUND_LABELS[r]}" for r in ROUND_ORDER]
    subtabs = st.tabs(tab_labels)

    for i, rnd in enumerate(ROUND_ORDER):
        with subtabs[i]:
            matches = sorted(
                [m for m in pick_bracket.values() if m["round"] == rnd],
                key=lambda m: m["bracket_slot"],
            )
            if not matches:
                st.info("No matches for this round.")
                continue

            if rnd == "final":
                # Center the final match
                _, fc, _ = st.columns([1, 2, 1])
                with fc:
                    _match_card(user_id, matches[0], allow_edit, actual_results, show_result=True)
                continue

            if rnd == "sf":
                ncols = 2
            elif rnd == "qf":
                ncols = 4
            elif rnd == "r16":
                ncols = 4
            else:  # r32
                ncols = 4

            cols = st.columns(ncols)
            for j, m in enumerate(matches):
                with cols[j % ncols]:
                    _match_card(user_id, m, allow_edit, actual_results, show_result=True)


# ── Family Brackets tab ────────────────────────────────────────────────────────

def _family_brackets() -> None:
    if not is_locked:
        st.info(
            "🔒 Family brackets are revealed after Admin locks picks.\n\n"
            "This keeps things fair — no peeking at each other's brackets before the deadline!"
        )

        # Show who has submitted (without revealing picks)
        statuses = get_bracket_status_all_users()
        st.markdown("### Who's ready?")
        for s in statuses:
            icon = "✅" if s["is_submitted"] else ("📋" if s["is_complete"] else "⏳")
            label = "Submitted" if s["is_submitted"] else (
                "Complete — not submitted" if s["is_complete"] else
                f"{s['pick_count']}/{REQUIRED_PICKS} picks"
            )
            st.markdown(
                f"<span style='font-size:1.6rem'>{s['avatar']}</span> "
                f"**{s['name']}** — {icon} {label}",
                unsafe_allow_html=True,
            )
        return

    # Locked: show each user's bracket
    users = _all_users()
    actual_results = get_actual_results()
    team_map = get_team_map()

    user_opts = [u["name"] for u in users]
    selected_name = st.selectbox("View bracket for:", user_opts)
    selected_user = next(u for u in users if u["name"] == selected_name)
    su_id = selected_user["id"]

    pick_bracket = compute_pick_bracket(su_id)
    su_score     = score_bracket(su_id)

    # Score summary
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Score", f"{su_score['total']:.0f} pts")
    c2.metric("Correct Picks", f"{su_score['correct']} / {su_score['picks_total']}")
    c3.metric("Semifinalist Bonus", f"+{su_score['semifinalist_bonus']}")
    c4.metric("Champion Bonus", f"+{su_score['champion_bonus']}")

    st.divider()

    tab_labels = [ROUND_LABELS[r] for r in ROUND_ORDER]
    subtabs = st.tabs(tab_labels)
    for i, rnd in enumerate(ROUND_ORDER):
        with subtabs[i]:
            matches = sorted(
                [m for m in pick_bracket.values() if m["round"] == rnd],
                key=lambda m: m["bracket_slot"],
            )
            if not matches:
                st.info("No matches for this round.")
                continue

            if rnd == "final":
                _, fc, _ = st.columns([1, 2, 1])
                with fc:
                    _match_card(su_id, matches[0], allow_edit=False, actual_results=actual_results, show_result=True)
                continue

            ncols = 4 if rnd in ("r32", "r16") else (4 if rnd == "qf" else 2)
            cols = st.columns(ncols)
            for j, m in enumerate(matches):
                with cols[j % ncols]:
                    _match_card(su_id, m, allow_edit=False, actual_results=actual_results, show_result=True)


# ── Family Comparison tab ──────────────────────────────────────────────────────

def _family_comparison() -> None:
    if not is_locked:
        st.info("📊 Family comparison will appear after brackets are locked.")
        return

    users = _all_users()
    actual_results = get_actual_results()
    team_map = get_team_map()

    # Leaderboard summary
    st.markdown("### 🏆 Bracket Leaderboard")
    lb = get_bracket_leaderboard()
    if lb:
        for s in lb:
            medal = ["🥇", "🥈", "🥉"][s["rank"] - 1] if s["rank"] <= 3 else f"#{s['rank']}"
            st.markdown(
                f"{medal} <span style='font-size:1.4rem'>{s['avatar']}</span> "
                f"**{s['name']}** — {s['total']:.0f} pts "
                f"({s['correct']} correct, +{s['semifinalist_bonus']} semis, +{s['champion_bonus']} champ)",
                unsafe_allow_html=True,
            )
    else:
        st.info("No scores yet.")

    st.divider()

    # Per-round comparison grid
    def _team_cell(team_id: int | None, mid: int) -> str:
        if team_id is None:
            return "—"
        t = team_map.get(team_id, {})
        name  = t.get("name", "?")
        flag  = t.get("flag", "")
        actual = actual_results.get(mid)
        if actual is None:
            indicator = "🔵"
        elif team_id == actual:
            indicator = "✅"
        else:
            indicator = "❌"
        return f"{indicator} {flag} {name}"

    comparison_rounds = [
        ("🏆 Champion", [FINAL_MATCH_ID]),
        ("🥈 Runner-Up", list(SF_MATCH_IDS)),
        ("⚡ Semifinalists (QF picks)", list(sorted(QF_MATCH_IDS))),
    ]

    for section_label, match_ids in comparison_rounds:
        st.markdown(f"### {section_label}")
        header = ["Person"] + [f"Match {mid}" for mid in match_ids]
        rows = []
        for u in users:
            uid = u["id"]
            upicks = get_bracket_picks(uid)
            row = [f"{u['avatar']} {u['name']}"]
            for mid in match_ids:
                row.append(_team_cell(upicks.get(mid), mid))
            rows.append(row)

        # Render as a simple markdown table
        md_rows = ["| " + " | ".join(header) + " |"]
        md_rows.append("| " + " | ".join(["---"] * len(header)) + " |")
        for row in rows:
            md_rows.append("| " + " | ".join(row) + " |")
        st.markdown("\n".join(md_rows))
        st.markdown("")


# ── Page header & tabs ─────────────────────────────────────────────────────────

st.markdown(
    f"<h1 style='margin-bottom:0'>🎯 Bracket Picks</h1>",
    unsafe_allow_html=True,
)

lock_status = "🔒 **Locked**" if is_locked else "🔓 Open for picks"
st.markdown(
    f"<span style='color:#888;font-size:.95rem'>"
    f"Playing as: <strong>{user_avatar} {user_name}</strong> · {lock_status}"
    f"</span>",
    unsafe_allow_html=True,
)
st.markdown("")

tab1, tab2, tab3 = st.tabs(["🎯 My Bracket", "👀 Family Brackets", "📊 Family Comparison"])

with tab1:
    _my_bracket()

with tab2:
    _family_brackets()

with tab3:
    _family_comparison()
