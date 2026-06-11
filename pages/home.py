import streamlit as st
import pandas as pd
from datetime import date, timedelta
from services.matches import get_all_matches
from services.scoring import get_leaderboard
from services.teams import get_flag
from services.activity import (
    get_meaningful_activity, format_activity_message,
    get_recent_family_discoveries, get_best_activity_per_user,
)
from services.passport import (
    get_country_of_the_day, get_family_stamp_statuses,
    get_family_top_favorites, get_stamp, get_top_favorites,
)
from services.images import get_country_image_html
from services.achievements import get_recent_achievement_unlocks
from services.time_utils import fmt_match_time, pt_date_str

st.markdown("""
<style>
/* ── Match cards ─────────────────────────────── */
.match-card {
    background: linear-gradient(135deg, #1E3A5F 0%, #2563EB 100%);
    border-radius: 16px; padding: 1.1rem 1rem .7rem; color: white; margin-bottom: .5rem;
}
.match-card-tomorrow {
    background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
    border-radius: 16px; padding: 1.1rem 1rem .7rem; color: white; margin-bottom: .5rem;
    border: 1px solid rgba(148,163,184,.25);
}
.match-flags   { text-align:center; font-size:5.5rem; line-height:1; margin-bottom:.2rem; }
.match-teams   { text-align:center; font-size:1.3rem; font-weight:900; margin-bottom:.3rem; letter-spacing:-.01em; }
.match-meta    { text-align:center; font-size:.73rem; color:#94A3B8; margin:.08rem 0; }

/* ── COTD card (height reduced ~18%) ─────────── */
.cotd-card {
    background: linear-gradient(160deg, #064E3B 0%, #059669 60%, #10B981 100%);
    border-radius: 18px; overflow:hidden; color: white;
}
.cotd-body     { padding: .9rem 1rem 1rem; }
.cotd-flag     { text-align:center; font-size:2.4rem; margin:.2rem 0; }
.cotd-country  { text-align:center; font-size:1.7rem; font-weight:900; margin:.1rem 0; }
.cotd-stamp    { text-align:center; font-size:.88rem; color:#A7F3D0; margin-bottom:.35rem; }
.cotd-context  { text-align:center; font-size:.85rem; color:#6EE7B7; font-weight:700; margin:.3rem 0; }
.cotd-why      { font-size:.9rem; font-weight:800; color:#D1FAE5; margin:.35rem 0 .2rem; }
.cotd-reason   { display:inline-block; background:rgba(255,255,255,.18);
                 border-radius:8px; padding:.15rem .5rem; font-size:.8rem; margin:.1rem; color:white; }
.cotd-fact     { font-size:.8rem; color:#ECFDF5; line-height:1.45; margin-top:.35rem; }

/* ── Story cards ─────────────────────────────── */
.story-card {
    display:flex; align-items:center; gap:.7rem;
    background:rgba(248,250,252,.06); border:1px solid rgba(255,255,255,.06);
    border-radius:12px; padding:.55rem .8rem; margin:.25rem 0;
    min-height:3.6rem;
}
/* ── Favorites ───────────────────────────────── */
.fav-card {
    border-radius:12px; padding:.55rem .8rem; margin:.25rem 0;
    display:flex; align-items:center; gap:.6rem;
    min-height:3.6rem;
}
/* ── Leaderboard ─────────────────────────────── */
.lb-row { padding:.55rem .7rem; border-radius:8px; margin:.25rem 0; min-height:3.6rem; }
/* ── Section titles ──────────────────────────── */
.section-head { font-size:1.25rem; font-weight:800; margin:.7rem 0 .35rem; }
/* ── Achievement strip ───────────────────────── */
.ach-chip { display:inline-block; background:rgba(251,191,36,.13);
            border:1px solid rgba(251,191,36,.3); border-radius:20px;
            padding:.18rem .65rem; font-size:.88rem; margin:.12rem; }
/* ── Passport preview ────────────────────────── */
.disc-chip { display:inline-flex; align-items:center; gap:.3rem;
             background:rgba(16,185,129,.12); border:1px solid rgba(16,185,129,.25);
             border-radius:8px; padding:.2rem .5rem; margin:.15rem; font-size:.85rem; }
</style>
""", unsafe_allow_html=True)



def _cotd_image_block(country: str) -> str:
    """Returns HTML for the image at top of the COTD card."""
    H = "175px"
    img = get_country_image_html(country, height=H, border_radius='0')
    if img:
        return img
    return (
        f"<div style='height:{H};display:flex;flex-direction:column;"
        "align-items:center;justify-content:center;"
        "background:rgba(0,0,0,.25);color:rgba(255,255,255,.45);gap:.3rem'>"
        "<span style='font-size:1.6rem'>📷</span>"
        "<span style='font-size:.78rem'>Photo coming soon</span>"
        "</div>"
    )


# ── Shared match-card renderer ────────────────────────────────────────────────
def _match_card(m, card_class="match-card"):
    hf = get_flag(m['home_team'])
    af = get_flag(m['away_team'])
    mid = int(m['id'])
    time_str = fmt_match_time(m['match_date'], m['kickoff_time_et'])

    if m['status'] == 'completed':
        hs, as_ = int(m['home_score']), int(m['away_score'])
        flags_html = (
            f"<div class='match-flags'>{hf}"
            f"<span style='font-size:1.8rem;font-weight:900;color:#FCD34D;vertical-align:middle'>"
            f"&nbsp;{hs}–{as_}&nbsp;</span>{af}</div>"
        )
        btn_label, btn_icon = "View Result", "📊"
    else:
        flags_html = (
            f"<div class='match-flags'>{hf}"
            f"<span style='font-size:1.4rem;color:#64748B;vertical-align:middle'>&nbsp;vs&nbsp;</span>"
            f"{af}</div>"
        )
        btn_label, btn_icon = "Make Your Pick", "⚽"

    st.markdown(f"""
<div class="{card_class}">
    {flags_html}
    <div class="match-teams">{m['home_team']} <span style='opacity:.5;font-weight:300'>vs</span> {m['away_team']}</div>
    <div class="match-meta">🕒 {time_str} · Group {m['group_letter']} · 📍 {m['city']}</div>
</div>""", unsafe_allow_html=True)

    if st.button(f"{btn_icon} {btn_label}", key=f"home_go_{mid}", use_container_width=True):
        st.session_state["_nav_match_id"] = mid
        st.switch_page("pages/matchup.py")


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding:.15rem 0 .15rem'>
    <div style='font-size:2.2rem;font-weight:900;color:#1E40AF;line-height:1.15'>
        ⚽ Espinosa World Cup Family HQ
    </div>
    <div style='color:#64748B;font-size:.85rem;margin-top:.15rem'>
        FIFA World Cup 2026 · Group Stage · June 11–27
    </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Pre-compute PT match windows
# ─────────────────────────────────────────────────────────────────────────────
today = date.today()
tomorrow = today + timedelta(days=1)
today_str = today.isoformat()
tomorrow_str = tomorrow.isoformat()

all_matches = get_all_matches()
all_matches['pt_date'] = all_matches.apply(
    lambda r: pt_date_str(r['match_date'], r['kickoff_time_et']), axis=1
)
today_matches   = all_matches[all_matches['pt_date'] == today_str].sort_values('kickoff_time_et')
tomorrow_matches = all_matches[all_matches['pt_date'] == tomorrow_str].sort_values('kickoff_time_et')

# ─────────────────────────────────────────────────────────────────────────────
# 1. Today's Matches
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-head">🗓️ Today\'s Matches</div>', unsafe_allow_html=True)

if today_matches.empty:
    st.info("No matches today — check tomorrow's line-up below!")
else:
    cols = st.columns(min(len(today_matches), 4))
    for col, (_, m) in zip(cols, today_matches.iterrows()):
        with col:
            _match_card(m)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 2. Country of the Day  +  3. Family Passport Progress
# ─────────────────────────────────────────────────────────────────────────────
cotd_col, _, passport_col = st.columns([5, 1, 4])

with cotd_col:
    st.markdown('<div class="section-head">🌍 Country of the Day</div>', unsafe_allow_html=True)
    try:
        cotd = get_country_of_the_day()

        img_html = _cotd_image_block(cotd['country'])

        reasons_html = " ".join(
            f"<span class='cotd-reason'>{r}</span>"
            for r in cotd['cheer_reasons'][:3]
        )
        if cotd['reason_detail']:
            context_line = f"🏟️ Playing today{cotd['reason_detail']}"
        elif "discovered" in cotd['reason'].lower():
            context_line = "🌍 Hidden gem — explore this country!"
        else:
            context_line = "🌟 Featured country of the day"

        credit = cotd.get('hero_image_credit', '').strip()
        credit_html = f"<div style='font-size:.7rem;color:rgba(255,255,255,.4);text-align:right;margin-top:.2rem'>📷 {credit}</div>" if credit else ""

        # Build complete card HTML as a pre-concatenated string to avoid
        # Streamlit's markdown parser misinterpreting injected </div> fragments.
        card_html = (
            '<div class="cotd-card">'
            + img_html
            + '<div class="cotd-body">'
            + f'<div class="cotd-flag">{cotd["flag"]}</div>'
            + f'<div class="cotd-country">{cotd["country"]}</div>'
            + f'<div class="cotd-stamp">{cotd["stamp_emoji"]} {cotd["stamp_label"]} · {cotd["continent"]}</div>'
            + '<hr style="border-color:rgba(255,255,255,.18);margin:.4rem 0">'
            + f'<div class="cotd-context">{context_line}</div>'
            + f'<div class="cotd-why">Why learn about {cotd["country"]}?</div>'
            + f'<div>{reasons_html}</div>'
            + '<hr style="border-color:rgba(255,255,255,.12);margin:.5rem 0">'
            + f'<div class="cotd-fact">💡 {cotd["fun_fact"]}</div>'
            + f'<div class="cotd-fact">🏴 {cotd["flag_fact"]}</div>'
            + credit_html
            + '</div>'
            + '</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

        if st.button(f"🌍 Explore {cotd['country']}", use_container_width=True, key="cotd_btn"):
            st.session_state["_nav_country"] = cotd['country']
            st.switch_page("pages/country_profile.py")
    except Exception as e:
        st.info(f"Country of the Day loading… ({e})")

with passport_col:
    st.markdown('<div class="section-head">🛂 Family Passport</div>', unsafe_allow_html=True)
    try:
        statuses = get_family_stamp_statuses()
        total = len(statuses)
        fam_disc  = sum(1 for s in statuses.values() if s['discovered'])
        fam_cheer = sum(1 for s in statuses.values() if s['cheered'])
        fam_won   = sum(1 for s in statuses.values() if s['won'])

        for label, count in [
            ("🌍 Discovered",  fam_disc),
            ("⚽ Cheered For", fam_cheer),
            ("🏆 Won With",    fam_won),
        ]:
            st.markdown(f"**{label}:** {count} / {total}")
            st.progress(count / total)

        # Recently discovered preview
        recent_disc = get_recent_family_discoveries(4)
        if not recent_disc.empty:
            st.markdown(
                "<div style='font-size:.8rem;font-weight:700;color:#475569;margin:.7rem 0 .2rem'>"
                "Recently Discovered</div>",
                unsafe_allow_html=True
            )
            chips = "".join(
                f"<span class='disc-chip'>"
                f"<span style='font-size:1rem'>{row['avatar']}</span> "
                f"{get_stamp(row['country_name'])['stamp_emoji']} {row['country_name']}"
                f"</span>"
                for _, row in recent_disc.iterrows()
            )
            st.markdown(f"<div>{chips}</div>", unsafe_allow_html=True)

        if st.button("📖 Open Family Passport", use_container_width=True):
            st.switch_page("pages/passport_family.py")
    except Exception:
        st.info("Passport loading...")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 4–6.  Leaderboard | Family Favorites | Family Story
# (reordered: LB first as competitive anchor, then Favorites, then Story)
# ─────────────────────────────────────────────────────────────────────────────
board = get_leaderboard()                          # used by all three columns
lb_order = board['id'].tolist()                    # user IDs in rank order

lb_col, fav_col, feed_col = st.columns([3, 5, 5])

# ── Leaderboard ───────────────────────────────────────────────────────────────
with lb_col:
    st.markdown('<div class="section-head">🏆 Leaderboard</div>', unsafe_allow_html=True)
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, (_, row) in enumerate(board.iterrows()):
        medal = medals[i] if i < len(medals) else " "
        pts   = float(row['total_points'])
        wins  = int(row['correct_picks'])
        cw    = int(row.get('countries_won', 0))
        color = row.get('theme_color', '#E2E8F0')
        st.markdown(
            f"<div class='lb-row' style='background:{color}22;border-left:3px solid {color};display:flex;align-items:center;gap:.5rem'>"
            f"<span style='font-size:2rem;flex-shrink:0'>{row['avatar']}</span>"
            f"<div><div style='font-size:1.05rem;font-weight:800'>{medal} {row['name']}</div>"
            f"<div style='color:#475569;font-size:.92rem'>"
            f"<b>{pts:.1f}</b> pts · {wins} wins · {cw} 🌍"
            f"</div></div></div>",
            unsafe_allow_html=True
        )

# ── Family Favorites — one per person, leaderboard order ──────────────────────
with fav_col:
    st.markdown('<div class="section-head">⭐ Family Favorites</div>', unsafe_allow_html=True)
    MEDALS      = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    MEDAL_BORDER = ["#D97706", "#3B82F6", "#DC2626", "#94A3B8", "#94A3B8"]

    try:
        for i, (_, row) in enumerate(board.iterrows()):
            uid    = int(row['id'])
            medal  = MEDALS[i] if i < len(MEDALS) else " "
            border = MEDAL_BORDER[i] if i < len(MEDAL_BORDER) else "#E2E8F0"
            favs   = get_top_favorites(uid, 1)

            if favs:
                country = favs[0]
                stamp   = get_stamp(country)
                flag    = get_flag(country)
                img_html = (
                    get_country_image_html(country, height='72px', border_radius='10px 10px 0 0')
                    or f"<div style='height:72px;background:linear-gradient(135deg,#1E293B,#334155);"
                       f"display:flex;align-items:center;justify-content:center;"
                       f"font-size:2.5rem;border-radius:10px 10px 0 0'>{flag}</div>"
                )
                st.markdown(
                    f"<div style='background:white;border:2px solid {border};border-radius:12px;"
                    f"overflow:hidden;margin:.25rem 0;box-shadow:0 1px 4px rgba(0,0,0,.06)'>"
                    f"{img_html}"
                    f"<div style='padding:.4rem .6rem'>"
                    f"<div style='display:flex;align-items:center;gap:.35rem'>"
                    f"<span style='font-size:1.4rem;line-height:1'>{flag}</span>"
                    f"<span style='font-size:.92rem;font-weight:900;color:#0F172A;"
                    f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{medal} {country}</span>"
                    f"</div>"
                    f"<div style='font-size:.72rem;color:#64748B;margin:.1rem 0'>{stamp['stamp_emoji']} {stamp['stamp_label']}</div>"
                    f"<div style='font-size:.68rem;color:#94A3B8'>{row['avatar']} {row['name']}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;"
                    f"padding:.55rem .7rem;margin:.25rem 0;opacity:.45;display:flex;align-items:center;gap:.5rem'>"
                    f"<span style='font-size:1.2rem'>{medal}</span>"
                    f"<span style='font-size:1.6rem'>{row['avatar']}</span>"
                    f"<span style='font-size:.8rem;color:#94A3B8;font-style:italic'>"
                    f"{row['name']} — keep exploring!</span></div>",
                    unsafe_allow_html=True
                )
    except Exception:
        st.info("Favorites loading...")

# ── Family Story — one card per person, leaderboard order ─────────────────────
with feed_col:
    st.markdown('<div class="section-head">📖 Family Story</div>', unsafe_allow_html=True)

    best_per_user = get_best_activity_per_user(lb_order)

    any_activity = any(v is not None for v in best_per_user.values())
    if not any_activity:
        st.markdown("""
<div style='background:rgba(248,250,252,.05);border:1px solid rgba(255,255,255,.08);
     border-radius:12px;padding:1.5rem;text-align:center;color:#64748B'>
    <div style='font-size:2.8rem'>🗺️</div>
    <div style='font-weight:700;margin:.4rem 0'>The adventure begins here.</div>
    <div style='font-size:.88rem'>Explore Country Profiles and make picks to write the family story.</div>
</div>""", unsafe_allow_html=True)
    else:
        for lb_user_id in lb_order:
            # Get user info from board
            user_row = board[board['id'] == lb_user_id]
            if user_row.empty:
                continue
            u = user_row.iloc[0]
            activity = best_per_user.get(lb_user_id)

            if activity is None:
                # User exists but has no activity yet
                st.markdown(f"""
<div class="story-card" style="opacity:.45">
    <span style='font-size:2.2rem;flex-shrink:0;line-height:1'>{u['avatar']}</span>
    <div style='min-width:0;flex:1'>
        <div style='font-weight:800;font-size:.9rem'>{u['name']}</div>
        <div style='font-size:.85rem;color:#94A3B8;font-style:italic'>Adventure hasn't started yet…</div>
    </div>
</div>""", unsafe_allow_html=True)
            else:
                icon, narrative = format_activity_message(activity)
                ts = str(activity.get('timestamp', ''))[:10]
                avatar = activity.get('avatar', u['avatar'])
                name   = activity.get('user_name', u['name'])
                st.markdown(f"""
<div class="story-card">
    <span style='font-size:2.2rem;flex-shrink:0;line-height:1'>{avatar}</span>
    <div style='min-width:0;flex:1'>
        <div style='font-weight:800;font-size:.9rem;line-height:1.2'>{name}</div>
        <div style='font-size:.9rem;margin:.15rem 0'>{icon} {narrative}</div>
        <div style='font-size:.75rem;color:#94A3B8'>{ts}</div>
    </div>
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Recent Achievement Unlocks — compact strip
# ─────────────────────────────────────────────────────────────────────────────
try:
    recent_ach = get_recent_achievement_unlocks(5)
    if not recent_ach.empty:
        st.divider()
        st.markdown('<div class="section-head">🏅 Recent Unlocks</div>', unsafe_allow_html=True)
        chips = " ".join(
            f"<span class='ach-chip'>"
            f"<span style='font-size:1.1rem'>{r['avatar']}</span> "
            f"<strong>{r['name']}</strong> unlocked "
            f"{r['ach_emoji']} <strong>{r['ach_name']}</strong>"
            f"</span>"
            for _, r in recent_ach.iterrows()
        )
        st.markdown(chips, unsafe_allow_html=True)
except Exception:
    pass

# ─────────────────────────────────────────────────────────────────────────────
# 7. Tomorrow's Matches — full width
# ─────────────────────────────────────────────────────────────────────────────
if not tomorrow_matches.empty:
    st.divider()
    st.markdown('<div class="section-head">📅 Tomorrow\'s Matches</div>', unsafe_allow_html=True)
    cols = st.columns(min(len(tomorrow_matches), 4))
    for col, (_, m) in zip(cols, tomorrow_matches.iterrows()):
        with col:
            _match_card(m, card_class="match-card-tomorrow")
