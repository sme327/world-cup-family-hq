import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime as _dt
from services.matches import get_all_matches
from services.scoring import get_leaderboard
from services.teams import get_flag
from services.activity import (
    format_activity_message,
    get_recent_family_discoveries,
    get_tiered_family_activity,
    STORY_TIERS,
)
from services.picks import get_picks_for_match
from services.passport import (
    get_country_of_the_day, get_family_stamp_statuses,
    get_stamp, get_top_favorites,
)
from services.images import get_country_image_html, get_country_image_data_uri
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
/* ── Story tier variants ─────────────────────────── */
.story-t1 {
    background:rgba(251,191,36,.09) !important;
    border-color:#D97706 !important;
    border-left:3px solid #D97706 !important;
}
.story-t2 {
    background:rgba(16,185,129,.07) !important;
    border-color:#10B981 !important;
    border-left:3px solid #10B981 !important;
}
/* ── Pick participation bar ──────────────────────── */
.pick-bar {
    margin:.45rem 0 .1rem;
    font-size:.72rem;
    font-weight:700;
    text-align:center;
}
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


def _tomorrow_match_card(m, match_picks: dict = None, all_users: list = None):
    """match_picks: {user_id: picked_team}. all_users: list of {id,name,avatar} dicts."""
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

    # ── Pick participation block ──────────────────────────────────────────────
    if match_picks is not None and all_users:
        total      = len(all_users)
        picked_ids = set(match_picks.keys())
        n_picked   = len(picked_ids)
        missing    = [u for u in all_users if int(u['id']) not in picked_ids]

        if n_picked == total:
            part_html = (
                "<div class='pick-bar' style='color:#10B981'>"
                "✅ All picks submitted!</div>"
            )
        elif n_picked == 0:
            part_html = (
                f"<div class='pick-bar' style='color:#64748B'>"
                f"👨‍👩‍👧‍👦 No picks yet — {total} waiting</div>"
            )
        else:
            missing_avs = " ".join(
                f"<span title='{u['name']}' style='font-size:1.1rem'>{u['avatar']}</span>"
                for u in missing
            )
            part_html = (
                f"<div class='pick-bar' style='color:#F59E0B'>"
                f"👨‍👩‍👧‍👦 {n_picked} / {total} picked</div>"
                f"<div style='text-align:center;font-size:.72rem;color:#94A3B8;margin-bottom:.3rem'>"
                f"⏳ Waiting: {missing_avs}</div>"
            )
    else:
        part_html = ""

    st.markdown(f"""
<div class="match-card-tomorrow">
    {flags_html}
    <div class="match-teams">{m['home_team']} <span style='opacity:.5;font-weight:300'>vs</span> {m['away_team']}</div>
    <div class="match-meta">🕒 {time_str} · Group {m['group_letter']} · 📍 {m['city']}</div>
    {part_html}
</div>""", unsafe_allow_html=True)

    if st.button(f"{btn_icon} {btn_label}", key=f"home_go_{mid}", use_container_width=True):
        st.session_state["_nav_match_id"] = mid
        st.switch_page("pages/matchup.py")


# ─────────────────────────────────────────────────────────────────────────────
# Pre-compute dates + matches
# ─────────────────────────────────────────────────────────────────────────────
today     = (_dt.utcnow() - timedelta(hours=7)).date()  # UTC-7 = PDT; keeps correct date on cloud servers
tomorrow  = today + timedelta(days=1)
today_str = today.isoformat()

all_matches      = get_all_matches()
all_matches['pt_date'] = all_matches.apply(
    lambda r: pt_date_str(r['match_date'], r['kickoff_time_et']), axis=1
)
def _time_sort_key(t: str) -> int:
    try:
        h, m = str(t).split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return 9999

today_matches    = all_matches[all_matches['pt_date'] == today_str].copy()
today_matches['_sort_key'] = today_matches['kickoff_time_et'].apply(_time_sort_key)
today_matches    = today_matches.sort_values('_sort_key').drop(columns=['_sort_key'])

tomorrow_matches = all_matches[all_matches['pt_date'] == tomorrow.isoformat()].copy()
tomorrow_matches['_sort_key'] = tomorrow_matches['kickoff_time_et'].apply(_time_sort_key)
tomorrow_matches = tomorrow_matches.sort_values('_sort_key').drop(columns=['_sort_key'])

board = get_leaderboard()

# ── Pre-compute pick participation for tomorrow's matches ──────────────────────
_conn_users = get_connection()
_all_users_for_picks = pd.read_sql(
    "SELECT id, name, avatar FROM users ORDER BY id", _conn_users
).to_dict('records')
_conn_users.close()

_tomorrow_picks: dict[int, dict] = {}
for _, _tm in tomorrow_matches.iterrows():
    _mid = int(_tm['id'])
    _pdf = get_picks_for_match(_mid)
    _tomorrow_picks[_mid] = {
        int(r['user_id']): r['picked_team'] for _, r in _pdf.iterrows()
    }


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

# ── Family Favorites — sorted by most shared, with context line ───────────────
with fav_col:
    st.markdown('<div class="section-head">⭐ Family Favorites</div>', unsafe_allow_html=True)

    try:
        # Build country → [(board_rank, user_row), ...] mapping
        country_owners: dict[str, list] = {}
        no_fav_rows = []
        for i, (_, row) in enumerate(board.iterrows()):
            uid  = int(row['id'])
            favs = get_top_favorites(uid, 1)
            if favs:
                country_owners.setdefault(favs[0], []).append((i, row))
            else:
                no_fav_rows.append(row)

        # Sort: most shared first, then by best-ranking fan within ties
        sorted_countries = sorted(
            country_owners.items(),
            key=lambda item: (-len(item[1]), min(rank for rank, _ in item[1])),
        )

        for country, owners in sorted_countries:
            n_fans    = len(owners)
            top_rank  = owners[0][0]
            # Border color by share level
            if n_fans >= 4:
                border = "#9333EA"   # purple — very popular
            elif n_fans >= 2:
                border = "#3B82F6"   # blue — shared
            else:
                border = "#D97706"   # gold — individual #1 pick

            stamp    = get_stamp(country)
            flag     = get_flag(country)
            img_html = (
                get_country_image_html(country, height='72px', border_radius='10px 10px 0 0')
                or f"<div style='height:72px;background:linear-gradient(135deg,#1E293B,#334155);"
                   f"display:flex;align-items:center;justify-content:center;"
                   f"font-size:2.5rem;border-radius:10px 10px 0 0'>{flag}</div>"
            )

            # Context line — why this country appears
            if n_fans == 1:
                sole = owners[0][1]
                context_line = f"❤️ {sole['name']}'s favorite"
                context_color = "#94A3B8"
            elif n_fans == 2:
                context_line  = f"👨‍👩‍👧‍👦 Shared by 2 family members"
                context_color = "#60A5FA"
            else:
                context_line  = f"👨‍👩‍👧‍👦 Shared by {n_fans} family members"
                context_color = "#A78BFA"

            # Avatar pills for all fans
            av_parts = []
            for _, r in owners:
                av_parts.append(
                    f"<span style='font-size:1.45rem;line-height:1' title='{r['name']}'>"
                    f"{r['avatar']}</span>"
                )
            avatar_row = (
                f"<div style='display:flex;gap:.25rem;flex-wrap:wrap;"
                f"margin-top:.25rem;align-items:center'>"
                + " ".join(av_parts)
                + "</div>"
            )

            st.markdown(
                f"<div style='background:var(--secondary-background-color);"
                f"border:2px solid {border};border-radius:12px;"
                f"overflow:hidden;margin:.25rem 0;box-shadow:0 1px 4px rgba(0,0,0,.08)'>"
                f"{img_html}"
                f"<div style='padding:.4rem .65rem'>"
                f"<div style='display:flex;align-items:center;gap:.3rem'>"
                f"<span style='font-size:1.3rem;line-height:1'>{flag}</span>"
                f"<span style='font-size:.95rem;font-weight:900'>{country}</span>"
                f"</div>"
                f"<div style='font-size:.7rem;color:#64748B;margin:.1rem 0'>"
                f"{stamp['stamp_emoji']} {stamp['stamp_label']}</div>"
                f"<div style='font-size:.72rem;font-weight:700;color:{context_color}'>"
                f"{context_line}</div>"
                f"{avatar_row}"
                f"</div></div>",
                unsafe_allow_html=True,
            )

        # Users with no favorite yet
        for row in no_fav_rows:
            st.markdown(
                f"<div style='background:rgba(248,250,252,.04);border:1px solid rgba(255,255,255,.07);"
                f"border-radius:12px;padding:.55rem .7rem;margin:.25rem 0;opacity:.45;"
                f"display:flex;align-items:center;gap:.5rem'>"
                f"<span style='font-size:1.6rem'>{row['avatar']}</span>"
                f"<span style='font-size:.8rem;color:#94A3B8;font-style:italic'>"
                f"{row['name']}'s favorite — keep exploring!</span></div>",
                unsafe_allow_html=True,
            )
    except Exception:
        st.info("Favorites loading...")

# ── Family Story — tiered (milestones first, then exploration, then routine) ───
with feed_col:
    st.markdown('<div class="section-head">📖 Family Story</div>', unsafe_allow_html=True)

    _TIER_CLASS  = {1: "story-t1", 2: "story-t2", 3: ""}
    _TIER_BADGE  = {1: "<span style='font-size:.65rem;font-weight:800;color:#D97706;"
                       "background:rgba(251,191,36,.15);border-radius:4px;"
                       "padding:.08rem .35rem;margin-left:.4rem'>✨ MILESTONE</span>",
                    2: "", 3: ""}

    story_items = get_tiered_family_activity(limit=8)

    if story_items.empty:
        st.markdown("""
<div style='background:rgba(248,250,252,.05);border:1px solid rgba(255,255,255,.08);
     border-radius:12px;padding:1.5rem;text-align:center;color:#64748B'>
    <div style='font-size:2.8rem'>🗺️</div>
    <div style='font-weight:700;margin:.4rem 0'>The adventure begins here.</div>
    <div style='font-size:.88rem'>Explore Country Profiles and make picks to write the family story.</div>
</div>""", unsafe_allow_html=True)
    else:
        for _, activity in story_items.iterrows():
            icon, narrative = format_activity_message(activity)
            tier   = int(activity.get('_tier', 3))
            ts     = str(activity.get('timestamp', ''))[:10]
            avatar = activity.get('avatar', '⚽')
            name   = activity.get('user_name', '')
            t_cls  = _TIER_CLASS.get(tier, "")
            badge  = _TIER_BADGE.get(tier, "")
            st.markdown(
                f'<div class="story-card {t_cls}">'
                f"<span style='font-size:2.2rem;flex-shrink:0;line-height:1'>{avatar}</span>"
                f"<div style='min-width:0;flex:1'>"
                f"<div style='font-weight:800;font-size:.9rem;line-height:1.2'>"
                f"{name}{badge}</div>"
                f"<div style='font-size:.9rem;margin:.1rem 0'>{icon} {narrative}</div>"
                f"<div style='font-size:.75rem;color:#94A3B8'>{ts}</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

# ─────────────────────────────────────────────────────────────────────────────
# Tomorrow's Matches — full width, unchanged
# ─────────────────────────────────────────────────────────────────────────────
if not tomorrow_matches.empty:
    st.divider()
    st.markdown('<div class="section-head">📅 Tomorrow\'s Matches</div>', unsafe_allow_html=True)
    cols = st.columns(min(len(tomorrow_matches), 4))
    for col, (_, m) in zip(cols, tomorrow_matches.iterrows()):
        with col:
            _tomorrow_match_card(
                m,
                match_picks=_tomorrow_picks.get(int(m['id']), {}),
                all_users=_all_users_for_picks,
            )
