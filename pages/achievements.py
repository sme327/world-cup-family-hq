import streamlit as st
import pandas as pd
from services.achievements import (
    get_all_achievements, get_user_achievements, get_family_achievements,
    check_individual_achievements, check_family_achievements,
)
from services.passport import get_discoveries, get_cheered_for, get_won_with
from services.picks import get_all_picks
from services.scoring import get_leaderboard

# ── Active user ───────────────────────────────────────────────────────────────
active_user    = st.session_state.get("active_user_name",   "Shawn")
active_user_id = st.session_state.get("active_user_id",     1)
avatar         = st.session_state.get("active_user_avatar", "🐘")

# ── Load data ─────────────────────────────────────────────────────────────────
all_ach    = get_all_achievements()
user_ach   = get_user_achievements(active_user_id)
family_ach = get_family_achievements()

unlocked_ids        = set(user_ach['achievement_id'].tolist()) if not user_ach.empty else set()
family_unlocked_ids = set(family_ach['achievement_id'].tolist()) if not family_ach.empty else set()

individual_ach = all_ach[all_ach['scope'] == 'individual']
family_only_ach = all_ach[all_ach['scope'] == 'family']

# ── Current user metrics for progress tracking ────────────────────────────────
disc_df      = get_discoveries(active_user_id)
n_discovered = len(disc_df) if not disc_df.empty else 0
n_cheered    = len(get_cheered_for(active_user_id))
n_won        = len(get_won_with(active_user_id))

all_picks  = get_all_picks()
user_picks = all_picks[all_picks['user_id'] == active_user_id] if not all_picks.empty else pd.DataFrame()
n_picks    = len(user_picks)

board    = get_leaderboard()
user_row = board[board['id'] == active_user_id]
n_points = float(user_row['total_points'].iloc[0]) if not user_row.empty else 0.0

_METRIC = {
    'countries_discovered': n_discovered,
    'picks_made': n_picks,
    'countries_cheered': n_cheered,
    'countries_won': n_won,
    'points_earned': n_points,
}

# ── Header ────────────────────────────────────────────────────────────────────
unlocked_count   = len(unlocked_ids)
total_individual = len(individual_ach[individual_ach['hidden'] == False])

st.markdown(
    f"<div style='background:linear-gradient(135deg,#7C3AED,#2563EB);"
    f"padding:1.4rem 1.8rem;border-radius:16px;color:white;text-align:center;margin-bottom:1rem'>"
    f"<div style='font-size:2.8rem;line-height:1'>{avatar} 🏅</div>"
    f"<div style='font-size:1.6rem;font-weight:800;margin:.2rem 0'>{active_user}'s Achievements</div>"
    f"<div style='font-size:1rem;color:#DDD6FE'>"
    f"{unlocked_count} of {total_individual} unlocked · FIFA World Cup 2026</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# ── Recently Unlocked ─────────────────────────────────────────────────────────
if not user_ach.empty:
    recent_ach = user_ach.sort_values('unlocked_at', ascending=False).head(3)
    st.markdown("### 🎉 Recently Unlocked")
    r_cols = st.columns(min(len(recent_ach), 3))
    for col, (_, ua) in zip(r_cols, recent_ach.iterrows()):
        aid = str(ua['achievement_id'])
        arow = all_ach[all_ach['achievement_id'] == aid]
        if arow.empty:
            continue
        a = arow.iloc[0]
        date_str = str(ua.get('unlocked_at', ''))[:10]
        with col:
            st.markdown(
                f"<div style='background:linear-gradient(135deg,#78350F,#92400E);"
                f"border:2px solid #FCD34D;border-radius:14px;padding:1rem;text-align:center'>"
                f"<div style='font-size:2.4rem;line-height:1;margin-bottom:.3rem'>{a.get('emoji','🏅')}</div>"
                f"<div style='font-size:.95rem;font-weight:900;color:#FEF3C7;line-height:1.2'>{a.get('name','')}</div>"
                f"<div style='font-size:.76rem;color:#FDE68A;margin:.3rem 0;line-height:1.35'>{a.get('description','')}</div>"
                f"<div style='font-size:.68rem;color:#D97706'>✅ {date_str}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    st.markdown("")

# ── Closest to Unlocking ──────────────────────────────────────────────────────
_closest: list[tuple] = []
for _, ach in individual_ach[individual_ach['hidden'] == False].iterrows():
    aid = str(ach['achievement_id'])
    if aid in unlocked_ids:
        continue
    rt  = str(ach.get('rule_type', ''))
    thr = ach.get('threshold')
    if rt in _METRIC and pd.notna(thr) and float(thr) > 0:
        current = _METRIC[rt]
        pct     = min(current / float(thr), 1.0)
        if pct > 0:
            _closest.append((pct, current, float(thr), ach))

_closest.sort(key=lambda x: -x[0])

if _closest:
    st.markdown("### 🎯 Closest to Unlocking")
    for pct, current, thr, ach in _closest[:5]:
        bar_pct  = int(pct * 100)
        thr_int  = int(thr)
        cur_int  = int(current)
        st.markdown(
            f"<div style='background:linear-gradient(160deg,#1E293B,#0F172A);"
            f"border:1px solid rgba(148,163,184,.15);border-radius:12px;"
            f"padding:.7rem 1rem;margin:.3rem 0'>"
            f"<div style='display:flex;align-items:center;gap:.75rem;margin-bottom:.4rem'>"
            f"<span style='font-size:1.6rem;line-height:1'>{ach.get('emoji','🏅')}</span>"
            f"<div style='flex:1'>"
            f"<div style='font-size:.9rem;font-weight:800;color:#F1F5F9'>{ach.get('name','')}</div>"
            f"<div style='font-size:.74rem;color:#94A3B8'>{ach.get('description','')}</div>"
            f"</div>"
            f"<div style='font-size:.85rem;font-weight:800;color:#FCD34D;flex-shrink:0'>"
            f"{cur_int} / {thr_int}</div>"
            f"</div>"
            f"<div style='background:rgba(148,163,184,.15);border-radius:4px;height:6px'>"
            f"<div style='background:linear-gradient(90deg,#3B82F6,#8B5CF6);border-radius:4px;"
            f"height:6px;width:{bar_pct}%'></div></div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("")

# ── Category tabs ─────────────────────────────────────────────────────────────
st.markdown("### 🗂️ All Achievements")
categories  = sorted(individual_ach['category'].unique().tolist())
tab_labels  = categories + ["👨‍👩‍👧‍👦 Family"]
tabs        = st.tabs(tab_labels)


def _ach_card(ach, is_unlocked: bool, is_hidden: bool, unlocked_at: str = ""):
    emoji = str(ach.get('emoji', '🏅'))
    name  = str(ach.get('name', ''))
    desc  = str(ach.get('description', ''))

    if is_hidden and not is_unlocked:
        st.markdown(
            "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);"
            "border:2px solid rgba(148,163,184,.2);border-radius:12px;"
            "padding:.8rem 1rem;margin:.25rem 0;opacity:0.7'>"
            "<div style='display:flex;align-items:center;gap:.7rem'>"
            "<span style='font-size:1.8rem'>❓</span>"
            "<div><div style='font-size:.9rem;font-weight:800;color:#475569'>???</div>"
            "<div style='font-size:.78rem;color:#334155'>Hidden achievement — keep exploring!</div>"
            "</div></div></div>",
            unsafe_allow_html=True,
        )
    elif is_unlocked:
        date_str = str(unlocked_at)[:10] if unlocked_at else ""
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#FFFBEB,#FEF3C7);"
            f"border:2px solid #FCD34D;border-radius:12px;padding:.75rem 1rem;margin:.25rem 0'>"
            f"<div style='display:flex;align-items:center;gap:.7rem'>"
            f"<span style='font-size:2rem'>{emoji}</span>"
            f"<div style='flex:1'>"
            f"<div style='font-size:.9rem;font-weight:900;color:#78350F'>{name}</div>"
            f"<div style='font-size:.78rem;color:#92400E'>{desc}</div>"
            f"</div>"
            f"<span style='font-size:.75rem;color:#92400E;flex-shrink:0'>✅ {date_str}</span>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='background:linear-gradient(160deg,#1E293B,#0F172A);"
            f"border:1px solid rgba(148,163,184,.12);border-radius:12px;"
            f"padding:.75rem 1rem;margin:.25rem 0;opacity:0.75'>"
            f"<div style='display:flex;align-items:center;gap:.7rem'>"
            f"<span style='font-size:2rem;filter:grayscale(100%)'>{emoji}</span>"
            f"<div>"
            f"<div style='font-size:.9rem;font-weight:800;color:#475569'>{name}</div>"
            f"<div style='font-size:.78rem;color:#334155'>{desc}</div>"
            f"</div></div></div>",
            unsafe_allow_html=True,
        )


# Individual by category
for tab, cat in zip(tabs[:-1], categories):
    with tab:
        cat_ach = individual_ach[individual_ach['category'] == cat]
        visible = cat_ach[cat_ach['hidden'] == False]
        hidden  = cat_ach[cat_ach['hidden'] == True]

        unlocked_in_cat = [a for _, a in visible.iterrows() if str(a['achievement_id']) in unlocked_ids]
        locked_in_cat   = [a for _, a in visible.iterrows() if str(a['achievement_id']) not in unlocked_ids]

        if unlocked_in_cat:
            st.markdown("**🏆 Unlocked**")
            for ach in unlocked_in_cat:
                aid = str(ach['achievement_id'])
                row = user_ach[user_ach['achievement_id'] == aid]
                ua  = row['unlocked_at'].iloc[0] if not row.empty else ""
                _ach_card(ach, True, False, ua)

        if locked_in_cat:
            st.markdown("**🔓 Available**")
            for ach in locked_in_cat:
                _ach_card(ach, False, False)

        if not hidden.empty:
            st.markdown("**🔒 Secret**")
            for _, ach in hidden.iterrows():
                aid        = str(ach['achievement_id'])
                is_unlocked = aid in unlocked_ids
                row        = user_ach[user_ach['achievement_id'] == aid] if is_unlocked else pd.DataFrame()
                ua         = row['unlocked_at'].iloc[0] if not row.empty else ""
                _ach_card(ach, is_unlocked, not is_unlocked, ua)

# Family tab
with tabs[-1]:
    st.markdown("### 👨‍👩‍👧‍👦 Family Achievements")
    st.caption("These count when the whole family works together!")
    for _, ach in family_only_ach.iterrows():
        aid        = str(ach['achievement_id'])
        is_unlocked = aid in family_unlocked_ids
        row        = family_ach[family_ach['achievement_id'] == aid] if is_unlocked else pd.DataFrame()
        ua         = row['unlocked_at'].iloc[0] if not row.empty else ""
        _ach_card(ach, is_unlocked, False, ua)

# ── Check for new achievements ────────────────────────────────────────────────
newly = check_individual_achievements(active_user_id)
check_family_achievements()
if newly:
    st.success(f"🎉 You just unlocked {len(newly)} new achievement(s)! Refresh to see them.")
