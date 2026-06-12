import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime as _dt
from services.matches import get_all_matches
from services.scoring import get_leaderboard
from services.teams import get_flag
from services.activity import (
    format_activity_message,
    get_recent_family_discoveries,
    get_best_activity_per_user,
)
from services.passport import (
    get_country_of_the_day, get_family_stamp_statuses,
    get_stamp, get_top_favorites,
)
from services.images import get_country_image_html, get_country_image_data_uri
from services.achievements import get_recent_achievement_unlocks
from services.time_utils import fmt_match_time, pt_date_str
from services.database import get_connection

st.markdown("""
<style>
/* ── Match card shared ───────────────────────────── */
.match-card-tomorrow {
    background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
    border-radius: 16px; padding: 1.1rem 1rem .7rem; color: white; margin-bottom: .5rem;
    border: 1px solid rgba(148,163,184,.25);
}
.match-flags   { text-align:center; font-size:5.5rem; line-height:1; margin-bottom:.2rem; }
.match-teams   { text-align:center; font-size:1.3rem; font-weight:900; margin-bottom:.3rem; letter-spacing:-.01em; }
.match-meta    { text-align:center; font-size:.73rem; color:#94A3B8; margin:.08rem 0; }

/* ── COTD card ───────────────────────────────────── */
.cotd-card {
    background: linear-gradient(160deg, #064E3B 0%, #059669 60%, #10B981 100%);
    border-radius: 18px; overflow:hidden; color: white;
}
.cotd-body     { padding: .45rem .85rem .6rem; }
.cotd-inline   { display:flex; align-items:center; gap:.45rem;
                  justify-content:center; margin:.18rem 0 .08rem; }
.cotd-flag     { font-size:1.9rem; line-height:1; }
.cotd-country  { font-size:1.4rem; font-weight:900; }
.cotd-stamp    { text-align:center; font-size:.82rem; color:#A7F3D0; margin-bottom:.15rem; }
.cotd-context  { font-size:.79rem; color:#6EE7B7; font-weight:700; }
.cotd-why      { font-size:.84rem; font-weight:800; color:#D1FAE5; margin:.18rem 0 .08rem; }
.cotd-reason   { display:inline-block; background:rgba(255,255,255,.18);
                 border-radius:8px; padding:.1rem .4rem; font-size:.75rem; margin:.05rem; color:white; }
.cotd-fact     { font-size:.76rem; color:#ECFDF5; line-height:1.35; margin-top:.15rem; }

/* ── Story cards ─────────────────────────────────── */
.story-card {
    display:flex; align-items:center; gap:.7rem;
    background:rgba(248,250,252,.06); border:1px solid rgba(255,255,255,.06);
    border-radius:12px; padding:.55rem .8rem; margin:.25rem 0;
    min-height:3.6rem;
}
/* ── Leaderboard ─────────────────────────────────── */
.lb-row { padding:.55rem .7rem; border-radius:8px; margin:.25rem 0; min-height:3.6rem; }
/* ── Section titles ──────────────────────────────── */
.section-head { font-size:1.25rem; font-weight:800; margin:.7rem 0 .35rem; }
/* ── Achievement strip ───────────────────────────── */
.ach-chip { display:inline-block; background:rgba(251,191,36,.13);
            border:1px solid rgba(251,191,36,.3); border-radius:20px;
            padding:.18rem .65rem; font-size:.88rem; margin:.12rem; }
/* ── Passport preview ────────────────────────────── */
.disc-chip { display:inline-flex; align-items:center; gap:.3rem;
             background:rgba(16,185,129,.12); border:1px solid rgba(16,185,129,.25);
             border-radius:8px; padding:.2rem .5rem; margin:.15rem; font-size:.85rem; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cotd_image_block(country: str, height: str = "140px") -> str:
    img = get_country_image_html(country, height=height, border_radius='0')
    if img:
        return img
    return (
        f"<div style='height:{height};display:flex;flex-direction:column;"
        "align-items:center;justify-content:center;"
        "background:rgba(0,0,0,.25);color:rgba(255,255,255,.45);gap:.3rem'>"
        "<span style='font-size:1.6rem'>📷</span>"
        "<span style='font-size:.78rem'>Photo coming soon</span>"
        "</div>"
    )


def _cheered_by(country: str) -> list[dict]:
    """Return list of {name, avatar} for users who picked this country in any match."""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT DISTINCT u.name, u.avatar
        FROM picks p JOIN users u ON p.user_id = u.id
        WHERE p.picked_team = ?
        ORDER BY u.id
    """, conn, params=(country,))
    conn.close()
    return df.to_dict('records')


def _today_match_card(m):
    """Match card with subtle country image background for Today's Matches."""
    hf  = get_flag(m['home_team'])
    af  = get_flag(m['away_team'])
    mid = int(m['id'])
    time_str = fmt_match_time(m['match_date'], m['kickoff_time_et'])

    home_uri = get_country_image_data_uri(m['home_team']) or ''
    away_uri = get_country_image_data_uri(m['away_team']) or ''

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

    if home_uri and away_uri:
        left_bg  = f"background:url('{home_uri}') center/cover no-repeat;filter:brightness(.2) blur(2px)"
        right_bg = f"background:url('{away_uri}') center/cover no-repeat;filter:brightness(.2) blur(2px)"
        card_html = (
            "<div style='position:relative;border-radius:16px;overflow:hidden;margin-bottom:.5rem'>"
            # bg halves
            f"<div style='position:absolute;top:0;left:0;width:50%;height:100%;{left_bg}'></div>"
            f"<div style='position:absolute;top:0;right:0;width:50%;height:100%;{right_bg}'></div>"
            # gradient overlay
            "<div style='position:absolute;inset:0;"
            "background:linear-gradient(135deg,rgba(30,58,95,.55) 0%,rgba(15,23,42,.45) 100%)'></div>"
            # content
            "<div style='position:relative;z-index:1;padding:1.1rem 1rem .7rem;color:white'>"
            + flags_html
            + f"<div class='match-teams'>{m['home_team']} <span style='opacity:.5;font-weight:300'>vs</span> {m['away_team']}</div>"
            + f"<div class='match-meta'>🕒 {time_str} · Group {m['group_letter']} · 📍 {m['city']}</div>"
            + "</div></div>"
        )
    else:
        card_html = (
            f"<div style='background:linear-gradient(135deg,#1E3A5F,#2563EB);"
            f"border-radius:16px;padding:1.1rem 1rem .7rem;color:white;margin-bottom:.5rem'>"
            + flags_html
            + f"<div class='match-teams'>{m['home_team']} <span style='opacity:.5;font-weight:300'>vs</span> {m['away_team']}</div>"
            + f"<div class='match-meta'>🕒 {time_str} · Group {m['group_letter']} · 📍 {m['city']}</div>"
            + "</div>"
        )

    st.markdown(card_html, unsafe_allow_html=True)
    if st.button(f"{btn_icon} {btn_label}", key=f"home_go_{mid}", use_container_width=True):
        st.session_state["_nav_match_id"] = mid
        st.switch_page("pages/matchup.py")


def _tomorrow_match_card(m):
    hf  = get_flag(m['home_team'])
    af  = get_flag(m['away_team'])
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
<div class="match-card-tomorrow">
    {flags_html}
    <div class="match-teams">{m['home_team']} <span style='opacity:.5;font-weight:300'>vs</span> {m['away_team']}</div>
    <div class="match-meta">🕒 {time_str} · Group {m['group_letter']} · 📍 {m['city']}</div>
</div>""", unsafe_allow_html=True)

    if st.button(f"{btn_icon} {btn_label}", key=f"home_go_{mid}", use_container_width=True):
        st.session_state["_nav_match_id"] = mid
        st.switch_page("pages/matchup.py")


# ─────────────────────────────────────────────────────────────────────────────
# Pre-compute dates + matches
# ─────────────────────────────────────────────────────────────────────────────
today     = date.today()
tomorrow  = today + timedelta(days=1)
today_str = today.isoformat()

all_matches      = get_all_matches()
all_matches['pt_date'] = all_matches.apply(
    lambda r: pt_date_str(r['match_date'], r['kickoff_time_et']), axis=1
)
today_matches    = all_matches[all_matches['pt_date'] == today_str].sort_values('kickoff_time_et')
tomorrow_matches = all_matches[all_matches['pt_date'] == tomorrow.isoformat()].sort_values('kickoff_time_et')

board = get_leaderboard()


# ─────────────────────────────────────────────────────────────────────────────
# 1. HERO — Dynamic World Cup Day banner
# ─────────────────────────────────────────────────────────────────────────────
wc_start = date(2026, 6, 11)
wc_end   = date(2026, 7, 19)
in_tournament = wc_start <= today <= wc_end
day_num   = (today - wc_start).days + 1 if in_tournament else None

n_today   = len(today_matches)
completed_today = today_matches[today_matches['status'] == 'completed']

# Latest result (most recent completed match overall)
completed_all = all_matches[all_matches['status'] == 'completed'].sort_values(
    ['match_date', 'kickoff_time_et'], ascending=False
)
last_result_html = ""
if not completed_all.empty:
    lm = completed_all.iloc[0]
    lhf, laf = get_flag(lm['home_team']), get_flag(lm['away_team'])
    hs, as_ = int(lm['home_score']), int(lm['away_score'])
    last_result_html = (
        f"<div style='font-size:.85rem;color:#CBD5E1;margin:.2rem 0'>"
        f"📊 Latest: {lhf} {lm['home_team']} <b style='color:#FCD34D'>{hs}–{as_}</b> {lm['away_team']} {laf}"
        f"</div>"
    )

# Leader
leader_html = ""
if not board.empty:
    lr = board.iloc[0]
    leader_html = (
        f"<div style='font-size:.85rem;color:#CBD5E1;margin:.2rem 0'>"
        f"🏆 Leader: {lr['avatar']} <b>{lr['name']}</b> "
        f"<span style='color:#FCD34D'>{float(lr['total_points']):.1f} pts</span>"
        f"</div>"
    )

# COTD for hero
try:
    cotd_hero = get_country_of_the_day()
    cotd_flag = cotd_hero['flag']
    cotd_name = cotd_hero['country']
    cotd_hero_html = (
        f"<div style='font-size:.85rem;color:#CBD5E1;margin:.2rem 0'>"
        f"🌍 Country of the Day: {cotd_flag} <b>{cotd_name}</b>"
        f"</div>"
    )
except Exception:
    cotd_hero_html = ""
    cotd_hero     = None

# Day / matches line
if in_tournament and day_num is not None:
    day_label = f"⚽ Day {day_num}"
else:
    day_label = "⚽ FIFA World Cup 2026"

match_label = (
    f"🗓 {n_today} Match{'es' if n_today != 1 else ''} Today"
    if n_today > 0
    else "🗓 No matches today"
)

st.markdown(
    "<div style='background:linear-gradient(135deg,#1E3A5F 0%,#1e40af 60%,#1E293B 100%);"
    "border-radius:20px;padding:1.2rem 1.6rem 1rem;color:white;margin-bottom:.5rem'>"
    "<div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:.5rem'>"
    "<div>"
    "<div style='font-size:1rem;font-weight:900;color:#93C5FD;letter-spacing:.04em;text-transform:uppercase'>"
    "Espinosa World Cup Family HQ</div>"
    f"<div style='font-size:2rem;font-weight:900;color:white;margin:.1rem 0;line-height:1.1'>"
    f"{day_label}</div>"
    f"<div style='font-size:1rem;color:#93C5FD'>{match_label}</div>"
    "</div>"
    "<div style='text-align:right'>"
    + last_result_html
    + leader_html
    + cotd_hero_html
    + "</div>"
    "</div>"
    "</div>",
    unsafe_allow_html=True
)

# ─────────────────────────────────────────────────────────────────────────────
# 2. NEXT KICKOFF COUNTDOWN
# ─────────────────────────────────────────────────────────────────────────────
now_pt = _dt.utcnow() - timedelta(hours=7)   # UTC → PDT (UTC-7 in June)

upcoming_with_time = []
for _, m in all_matches[all_matches['status'] == 'scheduled'].iterrows():
    try:
        ko_et  = _dt.strptime(f"{m['match_date']} {m['kickoff_time_et']}", "%Y-%m-%d %H:%M")
        ko_pt  = ko_et - timedelta(hours=3)
        upcoming_with_time.append((ko_pt, m))
    except Exception:
        pass

if upcoming_with_time:
    upcoming_with_time.sort(key=lambda x: x[0])
    next_ko_pt, next_m = upcoming_with_time[0]
    delta = next_ko_pt - now_pt
    total_secs = delta.total_seconds()

    nhf = get_flag(next_m['home_team'])
    naf = get_flag(next_m['away_team'])
    matchup_str = f"{nhf} {next_m['home_team']} vs {next_m['away_team']} {naf}"

    if -9000 < total_secs < 0:
        countdown_label = "🟢 Live now!"
        countdown_color = "#4ADE80"
    elif total_secs <= 0:
        countdown_label = "Final"
        countdown_color = "#94A3B8"
    elif total_secs < 3600:
        minutes = int(total_secs // 60)
        countdown_label = f"Starts in {minutes}m"
        countdown_color = "#FBBF24"
    else:
        hours   = int(total_secs // 3600)
        minutes = int((total_secs % 3600) // 60)
        countdown_label = f"Starts in {hours}h {minutes}m"
        countdown_color = "#93C5FD"

    st.markdown(
        f"<div style='background:rgba(30,58,95,.55);border:1px solid rgba(147,197,253,.25);"
        f"border-radius:12px;padding:.55rem 1rem;margin-bottom:.6rem;"
        f"display:flex;align-items:center;gap:.8rem;flex-wrap:wrap'>"
        f"<span style='font-size:1.1rem;color:#93C5FD;font-weight:700;white-space:nowrap'>⏰ Next Kickoff</span>"
        f"<span style='font-size:1.1rem;color:#F1F5F9'>{matchup_str}</span>"
        f"<span style='margin-left:auto;font-size:1.13rem;font-weight:800;color:{countdown_color}'>"
        f"{countdown_label}</span>"
        f"</div>",
        unsafe_allow_html=True
    )

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 3. Today's Matches — cinematic image-background cards
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-head">🗓️ Today\'s Matches</div>', unsafe_allow_html=True)

if today_matches.empty:
    st.info("No matches today — check tomorrow's line-up below!")
else:
    cols = st.columns(min(len(today_matches), 4))
    for col, (_, m) in zip(cols, today_matches.iterrows()):
        with col:
            _today_match_card(m)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 4. Country of the Day  +  5. Family Passport Progress
# ─────────────────────────────────────────────────────────────────────────────
cotd_col, _, passport_col = st.columns([5, 1, 4])

with cotd_col:
    st.markdown('<div class="section-head">🌍 Country of the Day</div>', unsafe_allow_html=True)
    try:
        cotd = cotd_hero if cotd_hero is not None else get_country_of_the_day()

        img_html = _cotd_image_block(cotd['country'], height="115px")

        reasons_html = " ".join(
            f"<span class='cotd-reason'>{r}</span>"
            for r in cotd['cheer_reasons'][:2]
        )
        if cotd['reason_detail']:
            context_line = f"🏟️ Playing today{cotd['reason_detail']}"
        elif "discovered" in cotd['reason'].lower():
            context_line = "🌍 Hidden gem"
        else:
            context_line = "🌟 Featured today"

        credit = cotd.get('hero_image_credit', '').strip()
        credit_html = (
            f"<div style='font-size:.65rem;color:rgba(255,255,255,.35);text-align:right;margin-top:.1rem'>"
            f"📷 {credit}</div>"
            if credit else ""
        )

        # Context + cheered-by on one line
        cheerers = _cheered_by(cotd['country'])
        if cheerers:
            cheer_parts = []
            for u in cheerers:
                name, av = u['name'], u['avatar']
                cheer_parts.append(f"<span style='font-size:1.15rem' title='{name}'>{av}</span>")
            cheer_inline = (
                f" &nbsp;·&nbsp; <span style='font-weight:400;color:#A7F3D0'>Cheered by: "
                + " ".join(cheer_parts)
                + "</span>"
            )
        else:
            cheer_inline = ""

        context_row = (
            f"<div class='cotd-context' style='margin:.15rem 0'>"
            f"{context_line}{cheer_inline}</div>"
        )

        card_html = (
            '<div class="cotd-card">'
            + img_html
            + '<div class="cotd-body">'
            + '<div class="cotd-inline">'
            + f'<span class="cotd-flag">{cotd["flag"]}</span>'
            + f'<span class="cotd-country">{cotd["country"]}</span>'
            + '</div>'
            + f'<div class="cotd-stamp">{cotd["stamp_emoji"]} {cotd["stamp_label"]} · {cotd["continent"]}</div>'
            + '<hr style="border-color:rgba(255,255,255,.18);margin:.25rem 0">'
            + context_row
            + f'<div class="cotd-why">Why learn about {cotd["country"]}?</div>'
            + f'<div style="margin-bottom:.15rem">{reasons_html}</div>'
            + f'<div class="cotd-fact">💡 {cotd["fun_fact"]}</div>'
            + (f'<div class="cotd-fact">🏴 {cotd["flag_fact"]}</div>' if cotd.get("flag_fact") else "")
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
        statuses  = get_family_stamp_statuses()
        total     = len(statuses)
        fam_disc  = sum(1 for s in statuses.values() if s['discovered'])
        fam_cheer = sum(1 for s in statuses.values() if s['cheered'])
        fam_won   = sum(1 for s in statuses.values() if s['won'])

        for label, count in [
            ("🌍 Countries Visited",  fam_disc),
            ("⚽ Teams Cheered For",  fam_cheer),
            ("🏆 Teams Won With",     fam_won),
        ]:
            st.markdown(f"**{label}:** {count} / {total}")
            st.progress(count / total)

        # Recently Collected — deduplicated by country, stamp + name chips
        recent_disc = get_recent_family_discoveries(8)
        if not recent_disc.empty:
            seen    = set()
            chips   = []
            for _, row in recent_disc.iterrows():
                country = row['country_name']
                if country in seen:
                    continue
                seen.add(country)
                stamp_emoji = get_stamp(country).get('stamp_emoji', '🌍')
                chips.append(
                    f"<span class='disc-chip'>"
                    f"<span style='font-size:1rem'>{stamp_emoji}</span> {country}"
                    f"</span>"
                )
                if len(chips) >= 4:
                    break

            st.markdown(
                "<div style='font-size:.8rem;font-weight:700;color:#475569;margin:.7rem 0 .2rem'>"
                "Recently Collected</div>",
                unsafe_allow_html=True
            )
            st.markdown(f"<div>{''.join(chips)}</div>", unsafe_allow_html=True)

        if st.button("📖 Open Family Passport", use_container_width=True):
            st.switch_page("pages/passport_family.py")
    except Exception:
        st.info("Passport loading...")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 6–8. Leaderboard | Family Favorites | Family Story
# ─────────────────────────────────────────────────────────────────────────────
lb_order = board['id'].tolist()

lb_col, fav_col, feed_col = st.columns([3, 5, 5])

# ── Leaderboard ───────────────────────────────────────────────────────────────
with lb_col:
    st.markdown('<div class="section-head">🏆 Leaderboard</div>', unsafe_allow_html=True)
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣"]
    for i, (_, row) in enumerate(board.iterrows()):
        medal = medals[i] if i < len(medals) else " "
        pts   = float(row['total_points'])
        wins  = int(row['correct_picks'])
        cw    = int(row.get('countries_won', 0))
        color = row.get('theme_color', '#E2E8F0')
        st.markdown(
            f"<div class='lb-row' style='background:{color}22;border-left:3px solid {color};"
            f"display:flex;align-items:center;gap:.5rem'>"
            f"<span style='font-size:2rem;flex-shrink:0'>{row['avatar']}</span>"
            f"<div><div style='font-size:1.05rem;font-weight:800'>{medal} {row['name']}</div>"
            f"<div style='color:#475569;font-size:.92rem'>"
            f"<b>{pts:.1f}</b> pts · {wins} wins · {cw} 🌍"
            f"</div></div></div>",
            unsafe_allow_html=True
        )

# ── Family Favorites — one card per country, shared avatars if tied ───────────
with fav_col:
    st.markdown('<div class="section-head">⭐ Family Favorites</div>', unsafe_allow_html=True)
    MEDAL_BORDER = ["#D97706", "#3B82F6", "#DC2626", "#94A3B8", "#94A3B8", "#94A3B8"]

    try:
        # Build country → [(board_rank, user_row), ...] mapping
        country_owners: dict[str, list] = {}
        no_fav_rows = []
        for i, (_, row) in enumerate(board.iterrows()):
            uid  = int(row['id'])
            favs = get_top_favorites(uid, 1)
            if favs:
                c = favs[0]
                country_owners.setdefault(c, []).append((i, row))
            else:
                no_fav_rows.append(row)

        # Emit one card per unique country, in order of the top-ranked fan
        seen_countries: set[str] = set()
        for i, (_, row) in enumerate(board.iterrows()):
            uid  = int(row['id'])
            favs = get_top_favorites(uid, 1)
            if not favs:
                continue
            country = favs[0]
            if country in seen_countries:
                continue
            seen_countries.add(country)

            owners = country_owners[country]       # list of (rank_idx, user_row)
            top_rank = owners[0][0]                # rank of the first (highest) fan
            border = MEDAL_BORDER[top_rank] if top_rank < len(MEDAL_BORDER) else "#E2E8F0"
            stamp  = get_stamp(country)
            flag   = get_flag(country)
            img_html = (
                get_country_image_html(country, height='72px', border_radius='10px 10px 0 0')
                or f"<div style='height:72px;background:linear-gradient(135deg,#1E293B,#334155);"
                   f"display:flex;align-items:center;justify-content:center;"
                   f"font-size:2.5rem;border-radius:10px 10px 0 0'>{flag}</div>"
            )

            # Avatar row — all fans of this country
            av_parts = []
            for _, r in owners:
                nm, av = r['name'], r['avatar']
                av_parts.append(f"<span style='font-size:1.4rem' title='{nm}'>{av}</span>")
            avatar_html = " ".join(av_parts)
            fans_label = (
                f"{owners[0][1]['name']}'s Favorite"
                if len(owners) == 1
                else "Shared Favorite"
            )

            st.markdown(
                f"<div style='background:white;border:2px solid {border};border-radius:12px;"
                f"overflow:hidden;margin:.25rem 0;box-shadow:0 1px 4px rgba(0,0,0,.06)'>"
                f"{img_html}"
                f"<div style='padding:.4rem .65rem'>"
                f"<div style='display:flex;align-items:center;gap:.3rem'>"
                f"<span style='font-size:1.3rem;line-height:1'>{flag}</span>"
                f"<span style='font-size:.95rem;font-weight:900;color:#0F172A'>{country}</span>"
                f"</div>"
                f"<div style='font-size:.7rem;color:#64748B;margin:.1rem 0'>"
                f"{stamp['stamp_emoji']} {stamp['stamp_label']}</div>"
                f"<div style='font-size:.7rem;color:#94A3B8;font-weight:700;text-transform:uppercase;"
                f"letter-spacing:.04em'>{fans_label}</div>"
                f"<div style='margin-top:.2rem'>{avatar_html}</div>"
                f"</div></div>",
                unsafe_allow_html=True
            )

        # Users with no favorite yet
        for row in no_fav_rows:
            st.markdown(
                f"<div style='background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;"
                f"padding:.55rem .7rem;margin:.25rem 0;opacity:.45;"
                f"display:flex;align-items:center;gap:.5rem'>"
                f"<span style='font-size:1.6rem'>{row['avatar']}</span>"
                f"<span style='font-size:.8rem;color:#94A3B8;font-style:italic'>"
                f"{row['name']}'s favorite — keep exploring!</span></div>",
                unsafe_allow_html=True
            )
    except Exception:
        st.info("Favorites loading...")

# ── Family Story — one card per person, leaderboard order ─────────────────────
with feed_col:
    st.markdown('<div class="section-head">📖 Family Story</div>', unsafe_allow_html=True)

    best_per_user = get_best_activity_per_user(lb_order)
    any_activity  = any(v is not None for v in best_per_user.values())

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
            user_row = board[board['id'] == lb_user_id]
            if user_row.empty:
                continue
            u        = user_row.iloc[0]
            activity = best_per_user.get(lb_user_id)

            if activity is None:
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
                ts     = str(activity.get('timestamp', ''))[:10]
                avatar = activity.get('avatar', u['avatar'])
                name   = activity.get('user_name', u['name'])
                st.markdown(f"""
<div class="story-card">
    <span style='font-size:2.2rem;flex-shrink:0;line-height:1'>{avatar}</span>
    <div style='min-width:0;flex:1'>
        <div style='font-weight:800;font-size:.9rem;line-height:1.2'>{name}</div>
        <div style='font-size:.9rem;margin:.1rem 0'>{icon} {narrative}</div>
        <div style='font-size:.75rem;color:#94A3B8'>{ts}</div>
    </div>
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Family Celebrations (was: Recent Unlocks)
# ─────────────────────────────────────────────────────────────────────────────
try:
    recent_ach = get_recent_achievement_unlocks(3)
    if not recent_ach.empty:
        st.divider()
        st.markdown(
            '<div class="section-head">🏆 Family Celebrations</div>',
            unsafe_allow_html=True
        )
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
# Tomorrow's Matches — full width, unchanged
# ─────────────────────────────────────────────────────────────────────────────
if not tomorrow_matches.empty:
    st.divider()
    st.markdown('<div class="section-head">📅 Tomorrow\'s Matches</div>', unsafe_allow_html=True)
    cols = st.columns(min(len(tomorrow_matches), 4))
    for col, (_, m) in zip(cols, tomorrow_matches.iterrows()):
        with col:
            _tomorrow_match_card(m)
