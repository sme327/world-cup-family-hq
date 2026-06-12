import streamlit as st
import pandas as pd
from services.matches import get_all_matches, update_match_score, reset_match
from services.teams import get_all_teams
from services.picks import get_all_users
from services.passport import get_country_metadata
from services.database import get_connection

st.markdown("## 🔧 Admin — Data Review & Score Entry")
st.caption("Shawn's tools for entering scores and reviewing data.")

tabs = st.tabs(["📥 Enter Scores", "📋 Matches", "🌍 Teams", "👤 Users", "🏷️ Stamps", "🖼️ Card Images", "🛠️ Database"])

# ── Enter Scores ──────────────────────────────────────────────────────────────
with tabs[0]:
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

# ── All Matches ───────────────────────────────────────────────────────────────
with tabs[1]:
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
with tabs[2]:
    st.markdown("### All 48 Teams")
    teams = get_all_teams()
    view_cols = ['name', 'flag_emoji', 'group_letter', 'confederation',
                 'fifa_ranking', 'coach', 'captain', 'capital', 'population']
    st.dataframe(teams[view_cols], use_container_width=True, hide_index=True)
    st.caption(f"Total teams: {len(teams)} | Groups: {teams['group_letter'].nunique()}")

# ── Users ─────────────────────────────────────────────────────────────────────
with tabs[3]:
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
with tabs[4]:
    st.markdown("### Country Stamps & Metadata")
    meta = get_country_metadata()
    st.dataframe(meta, use_container_width=True, hide_index=True)
    st.caption(f"Total countries: {len(meta)} | Continents: {meta['continent'].nunique()}")

# ── Card Images Review ────────────────────────────────────────────────────────
with tabs[5]:
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
with tabs[6]:
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
    st.caption("⚠️ This will delete ALL picks, discoveries, and activity. Cannot be undone.")
