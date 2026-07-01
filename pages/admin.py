import streamlit as st
import pandas as pd
from services.matches import get_all_matches, update_match_score, reset_match
from services.teams import get_all_teams
from services.picks import get_all_users, get_all_picks
from services.passport import get_country_metadata
from services.database import get_connection
from services.knockout import get_knockout_admin_data, save_knockout_result, reset_knockout_result

st.markdown("## 🔧 Admin — Data Review & Score Entry")
st.caption("Shawn's tools for entering scores and reviewing data.")

# ── Waiting On Picks ──────────────────────────────────────────────────────────
_adm_matches  = get_all_matches()
_adm_picks    = get_all_picks()
_adm_users    = get_all_users()
_adm_upcoming = _adm_matches[_adm_matches['status'] == 'scheduled']

if not _adm_upcoming.empty:
    _adm_upcoming_ids = set(_adm_upcoming['id'].astype(int).tolist())
    _adm_missing: list[dict] = []
    for _, _u in _adm_users.iterrows():
        _uid = int(_u['id'])
        _picked_ids = (
            set(_adm_picks[_adm_picks['user_id'] == _uid]['match_id'].astype(int).tolist())
            if not _adm_picks.empty else set()
        )
        _n = len(_adm_upcoming_ids - _picked_ids)
        if _n > 0:
            _adm_missing.append({'name': str(_u['name']), 'avatar': str(_u['avatar']), 'count': _n})

    _adm_total_missing = sum(v['count'] for v in _adm_missing)

    if not _adm_missing:
        st.markdown(
            "<div style='background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.3);"
            "border-radius:12px;padding:.6rem 1.1rem;margin:.3rem 0 .8rem;"
            "display:flex;align-items:center;gap:.7rem'>"
            "<span style='font-size:1.4rem'>✅</span>"
            "<div>"
            "<div style='font-weight:800;color:#4ADE80;font-size:.92rem'>Everyone is ready!</div>"
            "<div style='font-size:.75rem;color:#6EE7B7'>"
            "All family picks submitted for upcoming matches.</div>"
            "</div></div>",
            unsafe_allow_html=True,
        )
    else:
        _adm_pills = " ".join(
            f"<span style='display:inline-flex;align-items:center;gap:.28rem;"
            f"background:rgba(251,191,36,.11);border:1px solid rgba(251,191,36,.28);"
            f"border-radius:20px;padding:.2rem .65rem;font-size:.84rem;font-weight:700'>"
            f"<span style='font-size:1.08rem'>{v['avatar']}</span>"
            f"<span style='color:#F1F5F9'>{v['name']}</span>"
            f"<span style='background:rgba(0,0,0,.28);border-radius:10px;"
            f"padding:.02rem .26rem;font-size:.71rem;color:#FCD34D;margin-left:.08rem'>"
            f"{v['count']}</span></span>"
            for v in sorted(_adm_missing, key=lambda x: -x['count'])
        )
        _adm_rem = "1 pick" if _adm_total_missing == 1 else f"{_adm_total_missing} picks"
        st.markdown(
            f"<div style='background:rgba(30,41,59,.7);border:1px solid rgba(251,191,36,.2);"
            f"border-radius:12px;padding:.6rem 1.1rem;margin:.3rem 0 .8rem'>"
            f"<div style='font-size:.7rem;font-weight:800;color:#F59E0B;letter-spacing:.05em;"
            f"text-transform:uppercase;margin-bottom:.38rem'>⏳ Waiting On Picks</div>"
            f"<div style='display:flex;flex-wrap:wrap;gap:.3rem;margin:.1rem 0'>{_adm_pills}</div>"
            f"<div style='font-size:.71rem;color:#94A3B8;margin-top:.28rem'>"
            f"{_adm_rem} remaining across all upcoming matches</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

tabs = st.tabs(["⚽ Knockout", "📥 Group Scores", "📋 Matches", "🌍 Teams", "👤 Users", "🏷️ Stamps", "🖼️ Card Images", "🛠️ Database", "💾 Backup"])

# ── Enter Scores ──────────────────────────────────────────────────────────────
with tabs[1]:
    st.markdown("### Enter Final Scores")
    matches = get_all_matches()

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        status_filter = st.selectbox("Filter by status", ["scheduled", "completed", "all"])
    with filter_col2:
        group_filter = st.selectbox("Filter by group", ["All"] + sorted(matches['group_letter'].unique().tolist()))

    filtered = matches.copy()
    if status_filter != "all":
        filtered = filtered[filtered['status'] == status_filter]
    if group_filter != "All":
        filtered = filtered[filtered['group_letter'] == group_filter]

    for _, m in filtered.iterrows():
        mid = int(m['id'])
        with st.expander(
            f"Group {m['group_letter']} | {m['match_date']} | "
            f"{m['home_team']} vs {m['away_team']} [{m['status']}]"
        ):
            score_col1, score_col2, btn_col = st.columns([2, 2, 3])
            with score_col1:
                home_score = st.number_input(
                    f"{m['home_team']} score",
                    min_value=0, max_value=30,
                    value=int(m['home_score']) if pd.notna(m.get('home_score')) else 0,
                    key=f"hs_{mid}"
                )
            with score_col2:
                away_score = st.number_input(
                    f"{m['away_team']} score",
                    min_value=0, max_value=30,
                    value=int(m['away_score']) if pd.notna(m.get('away_score')) else 0,
                    key=f"as_{mid}"
                )
            with btn_col:
                st.markdown("&nbsp;", unsafe_allow_html=True)
                if st.button("✅ Save Score", key=f"save_{mid}"):
                    update_match_score(mid, int(home_score), int(away_score))
                    st.success(f"Saved: {m['home_team']} {int(home_score)}–{int(away_score)} {m['away_team']}")
                    st.rerun()
                if m['status'] == 'completed':
                    if st.button("↩️ Reset to Scheduled", key=f"reset_{mid}"):
                        reset_match(mid)
                        st.rerun()

# ── Knockout Score Entry ──────────────────────────────────────────────────────
with tabs[0]:
    st.markdown("### ⚽ Knockout Stage Score Entry")
    st.caption("Enter scores for each knockout match. The winner advances automatically.")

    _KO_ROUND_LABELS = {
        "r32": "Round of 32", "r16": "Round of 16",
        "qf": "Quarterfinals", "sf": "Semifinals",
        "final": "Final", "third_place": "3rd Place",
    }
    ko_round = st.radio(
        "Round",
        options=["r32", "r16", "qf", "sf", "final", "third_place"],
        format_func=lambda r: _KO_ROUND_LABELS[r],
        horizontal=True,
        key="ko_round_sel",
    )

    try:
        ko_matches = get_knockout_admin_data(ko_round)
    except Exception as e:
        st.error(f"Could not load knockout data: {e}. Run `python scripts/reset_db.py` to initialize the table.")
        ko_matches = []

    if not ko_matches:
        st.info("No knockout matches found. Make sure the database has been reset/initialized after today's update.")
    else:
        _SELECT_SENTINEL = "— select winner —"
        for m in ko_matches:
            mid    = int(m["id"])
            h_name = m.get("home_name") or m.get("home_source") or "TBD"
            a_name = m.get("away_name") or m.get("away_source") or "TBD"
            h_flag = m.get("home_flag") or ""
            a_flag = m.get("away_flag") or ""
            status = m.get("status", "scheduled")
            h_src  = m.get("home_source", "")
            a_src  = m.get("away_source", "")
            mdate  = m.get("match_date", "")
            venue  = m.get("venue", "")
            mnum   = m.get("match_number", "")

            label  = f"M{mnum} | {mdate} | {h_flag}{h_name} vs {a_flag}{a_name} [{status}]"

            with st.expander(label):
                teams_known = m.get("home_team_id") is not None and m.get("away_team_id") is not None
                if not teams_known:
                    st.caption(f"⏳ Teams TBD — {h_src} vs {a_src}")
                else:
                    st.caption(f"📍 {venue}")

                sc1, sc2, btn_col = st.columns([2, 2, 2])

                with sc1:
                    ko_hs = st.number_input(
                        f"{h_flag} {h_name}",
                        min_value=0, max_value=30,
                        value=int(m["home_score"]) if m.get("home_score") is not None else 0,
                        disabled=not teams_known,
                        key=f"ko_hs_{mid}",
                    )
                with sc2:
                    ko_as = st.number_input(
                        f"{a_flag} {a_name}",
                        min_value=0, max_value=30,
                        value=int(m["away_score"]) if m.get("away_score") is not None else 0,
                        disabled=not teams_known,
                        key=f"ko_as_{mid}",
                    )

                # Penalty inputs — only visible when scores are tied
                is_tied = teams_known and (ko_hs == ko_as)
                ko_hp = ko_ap = None
                if is_tied:
                    st.caption("🏆 Penalty shootout scores (if applicable):")
                    pn1, pn2 = st.columns(2)
                    with pn1:
                        _hp_val = int(m.get("home_penalties") or 0)
                        ko_hp = st.number_input(
                            f"{h_flag} {h_name} pens",
                            min_value=0, max_value=30, value=_hp_val,
                            disabled=not teams_known, key=f"ko_hp_{mid}",
                        )
                    with pn2:
                        _ap_val = int(m.get("away_penalties") or 0)
                        ko_ap = st.number_input(
                            f"{a_flag} {a_name} pens",
                            min_value=0, max_value=30, value=_ap_val,
                            disabled=not teams_known, key=f"ko_ap_{mid}",
                        )

                # Winner selectbox — auto-suggest from scores/pens before rendering
                winner_options = []
                if m.get("home_name"):
                    winner_options.append(m["home_name"])
                if m.get("away_name"):
                    winner_options.append(m["away_name"])

                cur_winner_name = m.get("winner_name")
                _win_key = f"ko_win_{mid}"

                if winner_options:
                    if cur_winner_name and cur_winner_name in winner_options:
                        # Saved match — ensure session state matches saved winner
                        _opts = winner_options
                        if st.session_state.get(_win_key) not in winner_options:
                            st.session_state[_win_key] = cur_winner_name
                    else:
                        # Unsaved — auto-select from scores (or penalties if tied)
                        _opts = [_SELECT_SENTINEL] + winner_options
                        _cur_sel = st.session_state.get(_win_key, _SELECT_SENTINEL)
                        if _cur_sel == _SELECT_SENTINEL:
                            if not is_tied and ko_hs > ko_as and m.get("home_name"):
                                st.session_state[_win_key] = m["home_name"]
                            elif not is_tied and ko_as > ko_hs and m.get("away_name"):
                                st.session_state[_win_key] = m["away_name"]
                            elif is_tied and ko_hp is not None and ko_ap is not None:
                                if ko_hp > ko_ap and m.get("home_name"):
                                    st.session_state[_win_key] = m["home_name"]
                                elif ko_ap > ko_hp and m.get("away_name"):
                                    st.session_state[_win_key] = m["away_name"]

                    ko_winner = st.selectbox(
                        "Winner",
                        options=_opts,
                        key=_win_key,
                        disabled=not teams_known,
                    )
                    # Tied-score message
                    if ko_winner == _SELECT_SENTINEL and is_tied:
                        st.caption("Score is tied — select the team that advanced, likely after penalties.")
                else:
                    ko_winner = None
                    st.caption("Winner TBD")

                # Save / Reset buttons
                _winner_chosen = (
                    teams_known
                    and ko_winner
                    and ko_winner != _SELECT_SENTINEL
                )
                with btn_col:
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                    if _winner_chosen:
                        if st.button("✅ Save", key=f"ko_save_{mid}"):
                            _wconn = get_connection()
                            _wrow = _wconn.execute(
                                "SELECT id FROM teams WHERE name=?", (ko_winner,)
                            ).fetchone()
                            _wconn.close()
                            if _wrow:
                                # Only save penalties when scores are tied and values entered
                                _save_hp = int(ko_hp) if is_tied and ko_hp else None
                                _save_ap = int(ko_ap) if is_tied and ko_ap else None
                                save_knockout_result(
                                    mid, int(ko_hs), int(ko_as), _wrow[0],
                                    _save_hp, _save_ap,
                                )
                                st.success(f"Saved! {ko_winner} advances.")
                                st.rerun()
                            else:
                                st.error(f"Team '{ko_winner}' not found in DB.")

                if status == "completed":
                    if st.button("↩️ Reset", key=f"ko_reset_{mid}"):
                        ok, msg = reset_knockout_result(mid)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.warning(msg)

# ── All Matches ───────────────────────────────────────────────────────────────
with tabs[2]:
    st.markdown("### All 72 Group Stage Matches")
    matches = get_all_matches()
    st.dataframe(
        matches[['id', 'group_letter', 'match_date', 'kickoff_time_et',
                 'home_team', 'away_team', 'venue', 'city',
                 'home_score', 'away_score', 'status']],
        use_container_width=True, hide_index=True
    )
    st.caption(f"Total matches: {len(matches)} | Completed: {(matches['status']=='completed').sum()}")

# ── Teams ─────────────────────────────────────────────────────────────────────
with tabs[3]:
    st.markdown("### All 48 Teams")
    teams = get_all_teams()
    view_cols = ['name', 'flag_emoji', 'group_letter', 'confederation',
                 'fifa_ranking', 'coach', 'captain', 'capital', 'population']
    st.dataframe(teams[view_cols], use_container_width=True, hide_index=True)
    st.caption(f"Total teams: {len(teams)} | Groups: {teams['group_letter'].nunique()}")

# ── Users ─────────────────────────────────────────────────────────────────────
with tabs[4]:
    st.markdown("### Family Members")
    users = get_all_users()
    for _, u in users.iterrows():
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([1, 2, 2, 2])
            c1.markdown(f"<span style='font-size:2.5rem'>{u['avatar']}</span>", unsafe_allow_html=True)
            c2.markdown(f"**{u['name']}**  \nID: {u['id']}")
            c3.markdown(f"Theme: `{u['theme_color']}`")
            c4.markdown(f"<div style='background:{u['theme_color']};height:24px;border-radius:4px'></div>",
                        unsafe_allow_html=True)

# ── Country Metadata ──────────────────────────────────────────────────────────
with tabs[5]:
    st.markdown("### Country Stamps & Metadata")
    meta = get_country_metadata()
    st.dataframe(meta, use_container_width=True, hide_index=True)
    st.caption(f"Total countries: {len(meta)} | Continents: {meta['continent'].nunique()}")

# ── Card Images Review ────────────────────────────────────────────────────────
with tabs[6]:
    st.markdown("### 🖼️ Country Card Images")
    st.caption(
        "Images are downloaded by `scripts/download_country_card_images.py`. "
        "Run it to populate images for the Country Profile cards."
    )

    import os
    targets_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'country_card_image_targets.csv')
    targets_path = os.path.normpath(targets_path)

    if not os.path.exists(targets_path):
        st.warning("No targets CSV found. Run `python scripts/build_country_card_image_targets.py` first.")
    else:
        card_df = pd.read_csv(targets_path)

        # Summary metrics
        total     = len(card_df[card_df['is_duplicate'] == 'no'])
        downloaded = (card_df[card_df['is_duplicate'] == 'no']['status'] == 'downloaded').sum()
        missing    = (card_df[card_df['is_duplicate'] == 'no']['status'] == 'missing').sum()
        pending    = total - downloaded - missing

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Unique Images", total)
        m2.metric("Downloaded ✅", downloaded)
        m3.metric("Missing ❌", missing)
        m4.metric("Pending ⏳", pending)

        if total > 0:
            pct = int(downloaded / total * 100)
            st.progress(pct / 100, text=f"{pct}% complete ({downloaded}/{total})")

        # Filters
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            country_filter = st.selectbox("Country", ["All"] + sorted(card_df['country'].unique().tolist()))
        with fc2:
            section_filter = st.selectbox("Section", ["All", "landmarks", "animals", "foods", "cheer_reasons"])
        with fc3:
            status_filter = st.selectbox("Status", ["All", "downloaded", "missing", "pending", "duplicate"])

        view = card_df.copy()
        if country_filter != "All":
            view = view[view['country'] == country_filter]
        if section_filter != "All":
            view = view[view['section'] == section_filter]
        if status_filter == "duplicate":
            view = view[view['is_duplicate'] == 'yes']
        elif status_filter != "All":
            view = view[view['status'] == status_filter]

        show_cols = ['country', 'section', 'item_name', 'item_slug', 'search_query',
                     'image_path', 'is_duplicate', 'status']
        st.dataframe(view[show_cols], use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(view)} rows. To re-download: `python scripts/download_country_card_images.py`")

        with st.expander("📥 Download command examples"):
            st.code("# Download everything (skip already-downloaded)\npython scripts/download_country_card_images.py")
            st.code("# Landmarks only\npython scripts/download_country_card_images.py --section landmarks")
            st.code("# One country\npython scripts/download_country_card_images.py --country mexico")
            st.code("# Re-download everything from scratch\npython scripts/download_country_card_images.py --overwrite")

# ── Database ──────────────────────────────────────────────────────────────────
with tabs[7]:
    import os as _os
    from services.database import _restore_from_backup, DATA_DIR

    # ── Restore status check ──────────────────────────────────────────────────
    _bak_path = _os.path.join(DATA_DIR, 'picks_backup.csv')
    _conn_check = get_connection()
    _live_picks = _conn_check.execute("SELECT COUNT(*) FROM picks").fetchone()[0]
    _live_scores = _conn_check.execute("SELECT COUNT(*) FROM matches WHERE status='completed'").fetchone()[0]
    _conn_check.close()

    if _os.path.exists(_bak_path):
        import pandas as _pd2
        _bak_df = _pd2.read_csv(_bak_path)
        _bak_picks = len(_bak_df)
    else:
        _bak_picks = None

    if _live_picks == 0:
        st.error(
            f"⚠️ **Database has 0 picks** — the backup file has {_bak_picks} picks. "
            "Press the button below to restore immediately."
        )
    elif _bak_picks and _live_picks < _bak_picks:
        st.warning(
            f"⚠️ Live DB has **{_live_picks} picks** but backup has **{_bak_picks}**. "
            "Some picks may be missing."
        )
    else:
        st.success(f"✅ DB looks healthy — {_live_picks} picks, {_live_scores} completed matches.")

    if st.button("🔄 Restore from picks_backup.csv now", type="primary"):
        _rconn = get_connection()
        _rcur  = _rconn.cursor()
        _rp, _rs = _restore_from_backup(_rcur)
        _rconn.commit()
        _rconn.close()
        st.success(f"✅ Restored {_rp} picks and {_rs} scores from backup.")
        st.rerun()

    st.divider()
    st.markdown("### Database Stats")
    conn = get_connection()
    tables = ['teams', 'matches', 'users', 'picks', 'discoveries',
              'activity_log', 'user_achievements', 'family_achievements']
    for t in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            st.metric(t, count)
        except Exception:
            st.metric(t, "table missing")
    conn.close()

    st.divider()
    st.markdown("### Reset Database")
    st.warning(
        "To completely reset and reseed the database from CSV files, run this command "
        "in your terminal from the `world-cup-family-hq/` folder:"
    )
    st.code("python scripts/reset_db.py", language="bash")
    st.caption("⚠️ reset_db.py now auto-backs up picks before wiping. Use --wipe to skip.")

# ── Backup & Restore ──────────────────────────────────────────────────────────
with tabs[8]:
    st.markdown("### 💾 Backup Picks")
    st.markdown(
        "Download the current picks and scores so they survive code deployments. "
        "**Do this before pushing any code changes to GitHub.**"
    )

    _bconn = get_connection()

    # Picks CSV
    _picks_rows = _bconn.execute(
        """SELECT u.name AS user_name, p.user_id, p.match_id,
                  m.home_team, m.away_team, m.match_date, p.picked_team
           FROM picks p
           JOIN users u ON p.user_id = u.id
           JOIN matches m ON p.match_id = m.id
           ORDER BY m.match_date, m.id, u.id"""
    ).fetchall()

    # Scores CSV
    _scores_rows = _bconn.execute(
        """SELECT home_team, away_team, match_date, home_score, away_score, status
           FROM matches WHERE status='completed' ORDER BY match_date"""
    ).fetchall()

    # KO Results CSV
    _ko_results_rows = _bconn.execute(
        """SELECT km.id, km.round, km.bracket_slot, km.match_number,
                  km.home_team_id, km.away_team_id,
                  ht.name AS home_name, at2.name AS away_name,
                  km.match_date, km.home_score, km.away_score,
                  km.winner_team_id, km.status, km.home_penalties, km.away_penalties
           FROM knockout_matches km
           LEFT JOIN teams ht  ON km.home_team_id  = ht.id
           LEFT JOIN teams at2 ON km.away_team_id = at2.id
           WHERE km.home_score IS NOT NULL OR km.winner_team_id IS NOT NULL
           ORDER BY km.match_date, km.id"""
    ).fetchall()

    # KO Live Picks CSV
    _ko_picks_rows = _bconn.execute(
        """SELECT u.name AS user_name, u.id AS user_id,
                  klp.knockout_match_id, klp.picked_team_id,
                  t.name AS picked_team_name,
                  km.round, km.bracket_slot, km.match_date,
                  klp.created_at, klp.updated_at
           FROM knockout_live_picks klp
           JOIN users u ON klp.user_id = u.id
           JOIN teams t ON klp.picked_team_id = t.id
           JOIN knockout_matches km ON klp.knockout_match_id = km.id
           ORDER BY km.match_date, km.id, u.id"""
    ).fetchall()

    _bconn.close()

    import csv, io
    from datetime import datetime as _dtnow

    def _to_csv(rows, headers):
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(headers)
        w.writerows(rows)
        return buf.getvalue().encode()

    _ts = _dtnow.now().strftime("%Y%m%d_%H%M")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Group picks to backup", len(_picks_rows))
        st.download_button(
            "⬇️ Download picks_backup.csv",
            data=_to_csv(_picks_rows, ["user_name","user_id","match_id","home_team","away_team","match_date","picked_team"]),
            file_name=f"picks_backup_{_ts}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        st.metric("Group scores to backup", len(_scores_rows))
        st.download_button(
            "⬇️ Download scores_backup.csv",
            data=_to_csv(_scores_rows, ["home_team","away_team","match_date","home_score","away_score","status"]),
            file_name=f"scores_backup_{_ts}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    col3, col4 = st.columns(2)
    with col3:
        st.metric("KO results to backup", len(_ko_results_rows))
        st.download_button(
            "⬇️ Download ko_results_backup.csv",
            data=_to_csv(_ko_results_rows, ["id","round","bracket_slot","match_number","home_team_id","away_team_id","home_name","away_name","match_date","home_score","away_score","winner_team_id","status","home_penalties","away_penalties"]),
            file_name=f"ko_results_backup_{_ts}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col4:
        st.metric("KO picks to backup", len(_ko_picks_rows))
        st.download_button(
            "⬇️ Download ko_live_picks_backup.csv",
            data=_to_csv(_ko_picks_rows, ["user_name","user_id","knockout_match_id","picked_team_id","picked_team_name","round","bracket_slot","match_date","created_at","updated_at"]),
            file_name=f"ko_live_picks_backup_{_ts}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.divider()
    st.markdown("### 🔄 How to preserve picks across deployments")
    st.markdown(
        "**Option A (fastest):** Download all 4 CSVs above, save to `data/` in your local repo "
        "with the exact filenames shown, then commit and push.\n\n"
        "**Option B (automatic):** From your terminal:\n"
    )
    st.code(
        "python scripts/backup_picks.py    # exports all 4 CSVs to data/\n"
        "git add data/picks_backup.csv data/scores_backup.csv\n"
        "git add data/ko_results_backup.csv data/ko_live_picks_backup.csv\n"
        "git commit -m 'backup picks'\n"
        "git push",
        language="bash"
    )
    st.info(
        "💡 `reset_db.py` automatically backs up and restores all picks and scores. "
        "Run `python scripts/reset_db.py` instead of deleting the database directly."
    )
