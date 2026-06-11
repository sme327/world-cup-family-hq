import streamlit as st
import pandas as pd
from services.achievements import get_all_achievements, get_user_achievements, get_family_achievements
# ── Active user from global selector ──────────────────────────────────────────
active_user    = st.session_state.get("active_user_name",   "Shawn")
active_user_id = st.session_state.get("active_user_id",     1)
avatar         = st.session_state.get("active_user_avatar", "🐘")

# ── Load data ─────────────────────────────────────────────────────────────────
all_ach = get_all_achievements()
user_ach = get_user_achievements(active_user_id)
family_ach = get_family_achievements()

unlocked_ids = set(user_ach['achievement_id'].tolist()) if not user_ach.empty else set()
family_unlocked_ids = set(family_ach['achievement_id'].tolist()) if not family_ach.empty else set()

individual_ach = all_ach[all_ach['scope'] == 'individual']
family_only_ach = all_ach[all_ach['scope'] == 'family']

# ── Header ────────────────────────────────────────────────────────────────────
unlocked_count = len(unlocked_ids)
total_individual = len(individual_ach[individual_ach['hidden'] == False])

st.markdown(f"""
<div style='background:linear-gradient(135deg,#7C3AED,#2563EB);
padding:2rem;border-radius:16px;color:white;text-align:center;margin-bottom:1.5rem'>
    <div style='font-size:3.5rem'>{avatar} 🏅</div>
    <div style='font-size:1.8rem;font-weight:800'>{active_user}'s Achievements</div>
    <div style='font-size:1.2rem;color:#DDD6FE;margin-top:.3rem'>
        {unlocked_count} unlocked · FIFA World Cup 2026
    </div>
</div>
""", unsafe_allow_html=True)

# ── Category tabs ─────────────────────────────────────────────────────────────
categories = sorted(individual_ach['category'].unique().tolist())
tab_labels = categories + ["👨‍👩‍👧‍👦 Family"]
tabs = st.tabs(tab_labels)

def _ach_card(ach, is_unlocked: bool, is_hidden: bool, unlocked_at: str = ""):
    emoji = str(ach.get('emoji', '🏅'))
    name = str(ach.get('name', ''))
    desc = str(ach.get('description', ''))

    if is_hidden and not is_unlocked:
        st.markdown(f"""
<div style='background:#F1F5F9;border:2px solid #CBD5E1;border-radius:12px;
padding:.8rem 1rem;margin:.3rem 0;opacity:0.6'>
    <span style='font-size:1.8rem'>🔒</span>
    <strong style='font-size:1rem'> ???</strong><br>
    <span style='color:#94A3B8;font-size:.85rem'>Hidden achievement — keep exploring!</span>
</div>""", unsafe_allow_html=True)
    elif is_unlocked:
        date_str = str(unlocked_at)[:10] if unlocked_at else ""
        st.markdown(f"""
<div style='background:linear-gradient(135deg,#FFFBEB,#FEF3C7);
border:2px solid #FCD34D;border-radius:12px;padding:.8rem 1rem;margin:.3rem 0'>
    <span style='font-size:2rem'>{emoji}</span>
    <strong style='font-size:1rem'> {name}</strong>
    <span style='float:right;color:#92400E;font-size:.8rem'>✅ {date_str}</span><br>
    <span style='color:#78350F;font-size:.85rem'>{desc}</span>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div style='background:#F8FAFC;border:2px solid #E2E8F0;border-radius:12px;
padding:.8rem 1rem;margin:.3rem 0;opacity:0.75'>
    <span style='font-size:2rem;filter:grayscale(100%)'>{emoji}</span>
    <strong style='font-size:1rem;color:#475569'> {name}</strong><br>
    <span style='color:#94A3B8;font-size:.85rem'>{desc}</span>
</div>""", unsafe_allow_html=True)


# Individual by category
for tab, cat in zip(tabs[:-1], categories):
    with tab:
        cat_ach = individual_ach[individual_ach['category'] == cat]
        visible = cat_ach[cat_ach['hidden'] == False]
        hidden = cat_ach[cat_ach['hidden'] == True]

        unlocked_in_cat = [a for _, a in visible.iterrows() if str(a['achievement_id']) in unlocked_ids]
        locked_in_cat = [a for _, a in visible.iterrows() if str(a['achievement_id']) not in unlocked_ids]

        if unlocked_in_cat:
            st.markdown("**🏆 Unlocked**")
            for ach in unlocked_in_cat:
                aid = str(ach['achievement_id'])
                row = user_ach[user_ach['achievement_id'] == aid]
                ua = row['unlocked_at'].iloc[0] if not row.empty else ""
                _ach_card(ach, True, False, ua)

        if locked_in_cat:
            st.markdown("**🔓 Available**")
            for ach in locked_in_cat:
                _ach_card(ach, False, False)

        if not hidden.empty:
            st.markdown("**🔒 Hidden**")
            for _, ach in hidden.iterrows():
                aid = str(ach['achievement_id'])
                is_unlocked = aid in unlocked_ids
                row = user_ach[user_ach['achievement_id'] == aid] if is_unlocked else pd.DataFrame()
                ua = row['unlocked_at'].iloc[0] if not row.empty else ""
                _ach_card(ach, is_unlocked, not is_unlocked, ua)

# Family tab
with tabs[-1]:
    st.markdown("### 👨‍👩‍👧‍👦 Family Achievements")
    st.caption("These count when the whole family works together!")
    for _, ach in family_only_ach.iterrows():
        aid = str(ach['achievement_id'])
        is_unlocked = aid in family_unlocked_ids
        row = family_ach[family_ach['achievement_id'] == aid] if is_unlocked else pd.DataFrame()
        ua = row['unlocked_at'].iloc[0] if not row.empty else ""
        _ach_card(ach, is_unlocked, False, ua)

# ── Check for new achievements ────────────────────────────────────────────────
from services.achievements import check_individual_achievements, check_family_achievements
newly = check_individual_achievements(active_user_id)
check_family_achievements()
if newly:
    st.success(f"🎉 You just unlocked {len(newly)} new achievement(s)! Refresh to see them.")
