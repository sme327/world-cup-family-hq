import re
import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime as _dt
from services.matches import get_all_matches
from services.scoring import get_leaderboard, get_combined_leaderboard
from services.teams import get_flag, get_all_teams
from services.activity import format_activity_message, get_tiered_family_activity
from services.picks import get_picks_for_match
from services.passport import (
    get_country_of_the_day, get_stamp, get_top_favorites,
    get_discoveries, get_cheered_for, get_won_with, get_family_top_favorites,
)
from services.images import get_country_image_data_uri
from services.time_utils import fmt_match_time, pt_date_str
from services.database import get_connection
from services.map_utils import build_atlas_figure, get_iso3_maps
from services.explorer import get_explorer_leaderboard, get_weekly_explorer, get_badge
from services.player_cards import get_featured_player_of_day, render_player_modal_content
from services.ko_picks import (
    get_all_ko_matches_display, get_ko_picks_for_match, KO_ROUND_POINTS,
)


@st.dialog("⭐ Player Profile", width="large")
def _show_player_modal_home(slug: str) -> None:
    uid = st.session_state.get('active_user_id', 1)
    render_player_modal_content(slug, uid)


st.markdown("""
<style>
/* ── Match card ──────────────────────────────────── */
.match-flags { text-align:center; font-size:4.6rem; line-height:1; margin-bottom:.15rem; }
.match-teams { text-align:center; font-size:1.2rem; font-weight:900; margin-bottom:.2rem; letter-spacing:-.01em; }
.match-meta  { text-align:center; font-size:.73rem; color:#94A3B8; margin:.05rem 0; }

/* ── Leaderboard row ─────────────────────────────── */
.lb-row {
    padding:.55rem .75rem; border-radius:10px; margin:.2rem 0;
    box-shadow:0 2px 6px rgba(0,0,0,.2);
}

/* ── Section titles ──────────────────────────────── */
.section-head {
    font-size:1.35rem; font-weight:900; margin:.5rem 0 .3rem;
    color:#F8FAFC; letter-spacing:-.01em;
}

/* ── Compact picks strip ─────────────────────────── */
.picks-strip {
    background:rgba(30,41,59,.6); border:1px solid rgba(148,163,184,.15);
    border-radius:10px; padding:.42rem .9rem; margin:.25rem 0 .5rem;
    display:flex; align-items:center; gap:.55rem; flex-wrap:wrap;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _country_sq_img(country: str, size: str = "80px") -> str:
    """Square background-image div for compact cards."""
    uri  = get_country_image_data_uri(country) or ''
    flag = get_flag(country)
    if uri:
        return (
            f"<div style='width:{size};height:{size};flex-shrink:0;"
            f"background:url(\"{uri}\") center/cover no-repeat;"
            f"border-radius:7px'></div>"
        )
    return (
        f"<div style='width:{size};height:{size};flex-shrink:0;"
        f"background:linear-gradient(135deg,#1E293B,#334155);"
        f"display:flex;align-items:center;justify-content:center;"
        f"font-size:2rem;border-radius:7px'>{flag}</div>"
    )


def _country_total_picks(country: str) -> int:
    conn = get_connection()
    df   = pd.read_sql("SELECT count(*) as cnt FROM picks WHERE picked_team = ?",
                       conn, params=(country,))
    conn.close()
    return int(df['cnt'].iloc[0]) if not df.empty else 0


def _today_match_card(m):
    """Cinematic image-background match card for today's grid."""
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
            f"<div style='position:absolute;top:0;left:0;width:50%;height:100%;{left_bg}'></div>"
            f"<div style='position:absolute;top:0;right:0;width:50%;height:100%;{right_bg}'></div>"
            "<div style='position:absolute;inset:0;"
            "background:linear-gradient(135deg,rgba(30,58,95,.55) 0%,rgba(15,23,42,.45) 100%)'></div>"
            "<div style='position:relative;z-index:1;padding:1.1rem 1rem .7rem;color:white'>"
            + flags_html
            + f"<div class='match-teams'>{m['home_team']} <span style='opacity:.5;font-weight:300'>vs</span> {m['away_team']}</div>"
            + f"<div class='match-meta'>🕒 {time_str} · Group {m['group_letter']} · 📍 {m['city']}</div>"
            + "</div></div>"
        )
    else:
        card_html = (
            "<div style='background:linear-gradient(135deg,#1E3A5F,#2563EB);"
            "border-radius:16px;padding:1.1rem 1rem .7rem;color:white;margin-bottom:.5rem'>"
            + flags_html
            + f"<div class='match-teams'>{m['home_team']} <span style='opacity:.5;font-weight:300'>vs</span> {m['away_team']}</div>"
            + f"<div class='match-meta'>🕒 {time_str} · Group {m['group_letter']} · 📍 {m['city']}</div>"
            + "</div>"
        )

    st.markdown(card_html, unsafe_allow_html=True)
    if st.button(f"{btn_icon} {btn_label}", key=f"home_go_{mid}", use_container_width=True):
        st.session_state["_nav_match_id"] = mid
        st.switch_page("pages/matchup.py")


def _dedup_story(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse same-event / same-country / same-day rows from different users into one."""
    if df.empty:
        return df
    rows: list[dict] = []
    seen: dict       = {}
    for _, row in df.iterrows():
        ev  = str(row.get('event_type', '') or '')
        cn  = str(row.get('country_name', '') or '')
        day = str(row.get('timestamp', ''))[:10]
        if ev in ('points_earned', 'country_discovered') and cn:
            key = (ev, cn, day)
            if key in seen:
                idx = seen[key]
                rows[idx]['_grp_avs']   = (rows[idx].get('_grp_avs')   or str(rows[idx].get('avatar','')))   + '|' + str(row.get('avatar',''))
                rows[idx]['_grp_names'] = (rows[idx].get('_grp_names') or str(rows[idx].get('user_name',''))) + '|' + str(row.get('user_name',''))
                continue
            seen[key] = len(rows)
        rows.append(dict(row))
    return pd.DataFrame(rows) if rows else pd.DataFrame()


_KO_RND_COLORS = {
    "r32": ("#1E3A5F", "#BAE6FD"), "r16": ("#14532D", "#BBF7D0"),
    "qf":  ("#3B1A6B", "#DDD6FE"), "sf":  ("#7C2D12", "#FED7AA"),
    "final": ("#78350F", "#FDE68A"),
}
_KO_RND_LABELS = {
    "r32": "Round of 32", "r16": "Round of 16", "qf": "Quarterfinals",
    "sf": "Semifinals", "final": "Final",
}


def _today_ko_card(km: dict) -> None:
    """Cinematic home-page card for one knockout match.

    Layout — TOP: round/pts badges | MIDDLE: team blocks flanking a gold vs badge
    (or score) | BOTTOM: venue/kickoff. Supporters live inside each team block
    so they visually belong to their side.
    """
    mid        = km["id"]
    rnd        = km["round"]
    home_id    = km["home_team_id"]
    away_id    = km["away_team_id"]
    home_name  = km["home_name"] or "TBD"
    away_name  = km["away_name"] or "TBD"
    home_flag  = km["home_flag"] or "⬜"
    away_flag  = km["away_flag"] or "⬜"
    pts_val    = KO_ROUND_POINTS.get(rnd, 0)
    rnd_lbl    = _KO_RND_LABELS.get(rnd, rnd)
    bg_c, tx_c = _KO_RND_COLORS.get(rnd, ("#374151", "#E2E8F0"))
    time_str   = fmt_match_time(km["match_date"], km["kickoff_time_et"])
    is_done    = km["status"] == "completed"
    active_uid = st.session_state.get("active_user_id", 1)

    # ── Picks ───────────────────────────────────────────────────────────────
    home_pickers: list[dict] = []
    away_pickers: list[dict] = []
    active_pick_id: int | None = None
    if home_id and away_id:
        ko_picks     = get_ko_picks_for_match(mid)
        home_pickers = [p for p in ko_picks if p["picked_team_id"] == home_id]
        away_pickers = [p for p in ko_picks if p["picked_team_id"] == away_id]
        for p in ko_picks:
            if p["user_id"] == active_uid:
                active_pick_id = p["picked_team_id"]
                break

    def _avatars(pickers: list[dict]) -> str:
        parts = []
        for p in pickers:
            if p["user_id"] == active_uid:
                # Larger + gold ring for the active user
                style = (
                    "font-size:1.55rem;line-height:1;"
                    "display:inline-flex;align-items:center;justify-content:center;"
                    "border-radius:50%;padding:.12rem;"
                    "box-shadow:0 0 0 2.5px #F59E0B,0 0 8px rgba(245,158,11,.35);"
                )
            else:
                style = "font-size:1.35rem;line-height:1;"
            parts.append(f"<span style='{style}'>{p['avatar']}</span>")
        return (
            "<div style='display:flex;flex-wrap:wrap;justify-content:center;gap:.25rem'>"
            + "".join(parts)
            + "</div>"
        )

    def _team_block(flag: str, name: str, pickers: list[dict], team_id: int | None) -> str:
        # Subtle gold underline on name if this is the active user's pick
        is_my_pick = bool(team_id and active_pick_id and team_id == active_pick_id)
        if is_my_pick:
            name_inner = (
                f"<span style='border-bottom:2px solid rgba(245,158,11,.6);"
                f"padding-bottom:.12rem'>{name}</span>"
            )
        else:
            name_inner = name

        supporter_html = ""
        if pickers:
            supporter_html = (
                # Slightly more space between name and label, label more muted (no uppercase)
                "<div style='font-size:.6rem;color:#6B7280;margin:.5rem 0 .15rem;"
                "letter-spacing:.02em;font-weight:500'>Supporters</div>"
                + _avatars(pickers)
            )
        return (
            "<div style='flex:1;min-width:0;text-align:center;padding:.05rem .2rem'>"
            f"<div style='font-size:2.8rem;line-height:1.05'>{flag}</div>"
            f"<div style='font-size:.95rem;font-weight:800;color:#F1F5F9;"
            f"margin:.2rem 0 0;line-height:1.2'>{name_inner}</div>"
            + supporter_html
            + "</div>"
        )

    # ── Center badge ────────────────────────────────────────────────────────
    if is_done and km.get("home_score") is not None:
        hs, as_ = int(km["home_score"]), int(km["away_score"])
        center_html = (
            "<div style='flex-shrink:0;align-self:center;padding:0 .4rem;text-align:center'>"
            f"<div style='color:#FCD34D;font-size:1.25rem;font-weight:900;"
            f"line-height:1'>{hs}–{as_}</div>"
            "</div>"
        )
        btn_label = "📊 View Result"
    else:
        center_html = (
            "<div style='flex-shrink:0;align-self:center;padding:0 .4rem;text-align:center'>"
            "<span style='background:rgba(245,158,11,.12);color:#F59E0B;"
            "border:1px solid rgba(245,158,11,.28);border-radius:20px;"
            "padding:.17rem .48rem;font-size:.63rem;font-weight:900;"
            "letter-spacing:.06em'>vs</span>"
            "</div>"
        )
        btn_label = "⚽ Make Your Pick"

    # ── Card wrapper ────────────────────────────────────────────────────────
    home_uri = get_country_image_data_uri(home_name) or ""
    away_uri = get_country_image_data_uri(away_name) or ""
    if home_uri and away_uri:
        card_html = (
            "<div style='position:relative;border-radius:16px;overflow:hidden;margin-bottom:.5rem'>"
            f"<div style='position:absolute;top:0;left:0;width:50%;height:100%;"
            f"background:url('{home_uri}') center/cover no-repeat;"
            f"filter:brightness(.18) blur(2px)'></div>"
            f"<div style='position:absolute;top:0;right:0;width:50%;height:100%;"
            f"background:url('{away_uri}') center/cover no-repeat;"
            f"filter:brightness(.18) blur(2px)'></div>"
            "<div style='position:absolute;inset:0;"
            "background:linear-gradient(135deg,rgba(30,58,95,.5),rgba(15,23,42,.4))'></div>"
            "<div style='position:relative;z-index:1;padding:.85rem .75rem .65rem'>"
        )
    else:
        card_html = (
            f"<div style='background:linear-gradient(135deg,{bg_c},{bg_c}cc);"
            f"border-radius:16px;padding:.85rem .75rem .65rem;margin-bottom:.5rem'>"
            "<div>"
        )

    card_html += (
        # TOP: badges (centered)
        "<div style='text-align:center;margin-bottom:.5rem'>"
        f"<span style='background:{bg_c};color:{tx_c};border-radius:4px;"
        f"padding:.08rem .4rem;font-size:.7rem;font-weight:800;"
        f"letter-spacing:.04em'>{rnd_lbl}</span>"
        f"<span style='background:rgba(255,255,255,.12);color:#FCD34D;border-radius:4px;"
        f"padding:.08rem .35rem;font-size:.68rem;font-weight:800;"
        f"margin-left:.3rem'>+{pts_val} pts</span>"
        "</div>"
        # MIDDLE: Team A block | vs badge | Team B block
        "<div style='display:flex;align-items:flex-start'>"
        + _team_block(home_flag, home_name, home_pickers, home_id)
        + center_html
        + _team_block(away_flag, away_name, away_pickers, away_id)
        + "</div>"
        # BOTTOM: kickoff + venue
        "<div style='text-align:center;margin-top:.5rem'>"
        f"<div style='font-size:.72rem;color:#94A3B8'>🕒 {time_str} · 🏟️ {km['venue']}</div>"
        f"<div style='font-size:.68rem;color:#64748B'>📍 {km['city']}, {km['host_country']}</div>"
        "</div>"
        "</div></div>"
    )
    st.markdown(card_html, unsafe_allow_html=True)
    if st.button(btn_label, key=f"home_ko_{mid}", use_container_width=True):
        st.switch_page("pages/schedule.py")


def _build_storylines(combined: list[dict], active_uid: int) -> list[str]:
    """Generate up to 4 narrative storyline strings for the current standings."""
    stories: list[str] = []

    # 1. Leader gap
    if len(combined) >= 2:
        leader = combined[0]
        second = combined[1]
        gap = leader["total_pts"] - second["total_pts"]
        if gap == 0:
            stories.append(f"⚖️ **{leader['name']}** and **{second['name']}** are tied at the top!")
        else:
            stories.append(
                f"🏆 **{leader['avatar']} {leader['name']}** leads by "
                f"**{gap:.1f} pt{'s' if gap != 1.0 else ''}**"
            )

    # 2. Most recent scored KO live pick
    try:
        conn = get_connection()
        row = conn.execute("""
            SELECT u.name, u.avatar, t.name, t.flag_emoji, km.round
            FROM knockout_live_picks klp
            JOIN knockout_matches km ON klp.knockout_match_id = km.id
            JOIN users u ON klp.user_id = u.id
            JOIN teams t ON klp.picked_team_id = t.id
            WHERE km.status = 'completed'
              AND km.winner_team_id = klp.picked_team_id
            ORDER BY km.match_date DESC, km.kickoff_time_et DESC
            LIMIT 1
        """).fetchone()
        conn.close()
        if row:
            p_name, p_av, t_name, t_flag, rnd = row
            pts_earned = KO_ROUND_POINTS.get(rnd, 0)
            stories.append(
                f"{p_av} **{p_name}** earned **+{pts_earned} pt{'s' if pts_earned != 1 else ''}** "
                f"picking {t_flag} {t_name}"
            )
    except Exception:
        pass

    # 3. Closest chaser (last place's gap to leader)
    if len(combined) >= 3:
        leader = combined[0]
        chaser = combined[-1]
        gap = leader["total_pts"] - chaser["total_pts"]
        if 0 < gap <= 15:
            stories.append(
                f"{chaser['avatar']} **{chaser['name']}** is **{gap:.1f} pts** behind — "
                f"still in reach!"
            )

    return stories[:4]


# ─────────────────────────────────────────────────────────────────────────────
# Pre-compute dates + matches
# ─────────────────────────────────────────────────────────────────────────────
today     = (_dt.utcnow() - timedelta(hours=7)).date()   # PDT
today_str = today.isoformat()

all_matches = get_all_matches()
all_matches['pt_date'] = all_matches.apply(
    lambda r: pt_date_str(r['match_date'], r['kickoff_time_et']), axis=1
)

def _pt_sort_key(et_time: str) -> int:
    try:
        h, m   = str(et_time).split(":")
        pt_min = int(h) * 60 + int(m) - 180
        return pt_min + 1440 if pt_min < 0 else pt_min
    except Exception:
        return 9999

today_matches = all_matches[all_matches['pt_date'] == today_str].copy()
today_matches['_sk'] = today_matches['kickoff_time_et'].apply(_pt_sort_key)
today_matches = today_matches.sort_values('_sk').drop(columns=['_sk'])

board    = get_leaderboard()
combined = get_combined_leaderboard()

# Knockout matches scheduled for today (exclude 3rd-place match 131)
try:
    _ko_all        = get_all_ko_matches_display()
    today_ko       = [m for m in _ko_all if m["match_date"] == today_str and m["id"] != 131]
except Exception:
    today_ko = []

try:
    cotd_hero = get_country_of_the_day()
except Exception:
    cotd_hero = None


# ─────────────────────────────────────────────────────────────────────────────
# 1. HERO — Dynamic World Cup Day banner
# ─────────────────────────────────────────────────────────────────────────────
wc_start      = date(2026, 6, 11)
wc_end        = date(2026, 7, 19)
in_tournament = wc_start <= today <= wc_end
day_num       = (today - wc_start).days + 1 if in_tournament else None
n_today       = len(today_matches)

completed_all = all_matches[all_matches['status'] == 'completed'].sort_values(
    ['match_date', 'kickoff_time_et'], ascending=False
)
last_result_html = ""
if not completed_all.empty:
    lm = completed_all.iloc[0]
    lhf, laf = get_flag(lm['home_team']), get_flag(lm['away_team'])
    hs, as_  = int(lm['home_score']), int(lm['away_score'])
    last_result_html = (
        f"<div style='font-size:.85rem;color:#CBD5E1;margin:.2rem 0'>"
        f"📊 Latest: {lhf} {lm['home_team']} <b style='color:#FCD34D'>{hs}–{as_}</b> {lm['away_team']} {laf}"
        f"</div>"
    )

leader_html = ""
if combined:
    lr = combined[0]
    leader_html = (
        f"<div style='font-size:.85rem;color:#CBD5E1;margin:.2rem 0'>"
        f"🏆 Leader: {lr['avatar']} <b>{lr['name']}</b> "
        f"<span style='color:#FCD34D'>{lr['total_pts']:.1f} pts</span>"
        f"</div>"
    )

cotd_hero_html = ""
if cotd_hero:
    cotd_hero_html = (
        f"<div style='font-size:.85rem;color:#CBD5E1;margin:.2rem 0'>"
        f"🌍 Country of the Day: {cotd_hero['flag']} <b>{cotd_hero['country']}</b>"
        f"</div>"
    )

day_label   = f"⚽ Day {day_num}" if in_tournament and day_num else "⚽ FIFA World Cup 2026"
if n_today > 0:
    match_label = f"🗓 {n_today} Match{'es' if n_today != 1 else ''} Today"
elif today_ko:
    _nko = len(today_ko)
    match_label = f"🏆 {_nko} Knockout Match{'es' if _nko != 1 else ''} Today"
else:
    match_label = "🗓 No matches today"

st.markdown(
    "<div style='background:linear-gradient(135deg,#1E3A5F 0%,#1e40af 60%,#1E293B 100%);"
    "border-radius:20px;padding:1.2rem 1.6rem 1rem;color:white;margin-bottom:.5rem'>"
    "<div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:.5rem'>"
    "<div>"
    "<div style='font-size:1rem;font-weight:900;color:#93C5FD;letter-spacing:.04em;text-transform:uppercase'>"
    "Espinosa World Cup Family HQ</div>"
    f"<div style='font-size:2rem;font-weight:900;color:white;margin:.1rem 0;line-height:1.1'>{day_label}</div>"
    f"<div style='font-size:1rem;color:#93C5FD'>{match_label}</div>"
    "</div>"
    "<div style='text-align:right'>"
    + last_result_html + leader_html + cotd_hero_html
    + "</div></div></div>",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# 2. NEXT KICKOFF COUNTDOWN
# ─────────────────────────────────────────────────────────────────────────────
now_pt = _dt.utcnow() - timedelta(hours=7)

upcoming = []
for _, m in all_matches[all_matches['status'] == 'scheduled'].iterrows():
    try:
        ko_pt = _dt.strptime(f"{m['match_date']} {m['kickoff_time_et']}", "%Y-%m-%d %H:%M") - timedelta(hours=3)
        upcoming.append((ko_pt, m))
    except Exception:
        pass

if upcoming:
    upcoming.sort(key=lambda x: x[0])
    next_ko_pt, next_m = upcoming[0]
    secs = (next_ko_pt - now_pt).total_seconds()
    nhf  = get_flag(next_m['home_team'])
    naf  = get_flag(next_m['away_team'])

    if -9000 < secs < 0:
        label, color = "🟢 Live now!", "#4ADE80"
    elif secs <= 0:
        label, color = "Final", "#94A3B8"
    elif secs < 3600:
        label, color = f"Starts in {int(secs//60)}m", "#FBBF24"
    else:
        label, color = f"Starts in {int(secs//3600)}h {int((secs%3600)//60)}m", "#93C5FD"

    st.markdown(
        f"<div style='background:rgba(30,58,95,.55);border:1px solid rgba(147,197,253,.25);"
        f"border-radius:12px;padding:.55rem 1rem;margin-bottom:.6rem;"
        f"display:flex;align-items:center;gap:.8rem;flex-wrap:wrap'>"
        f"<span style='font-size:1.1rem;color:#93C5FD;font-weight:700;white-space:nowrap'>⏰ Next Kickoff</span>"
        f"<span style='font-size:1.1rem;color:#F1F5F9'>{nhf} {next_m['home_team']} vs {next_m['away_team']} {naf}</span>"
        f"<span style='margin-left:auto;font-size:1.13rem;font-weight:800;color:{color}'>{label}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# 2b. TODAY'S KNOCKOUT MATCHES
# ─────────────────────────────────────────────────────────────────────────────
if today_ko:
    st.markdown(
        '<div class="section-head">⚽ Today\'s Knockout Matches</div>',
        unsafe_allow_html=True,
    )
    _nko   = len(today_ko)
    _nkcols = min(_nko, 4)
    _kocols = st.columns(_nkcols)
    for _ki, _km in enumerate(today_ko):
        with _kocols[_ki % _nkcols]:
            _today_ko_card(_km)

# ─────────────────────────────────────────────────────────────────────────────
# 3. TODAY'S GROUP MATCHES (only rendered when group matches exist today)
# ─────────────────────────────────────────────────────────────────────────────
if not today_matches.empty:
    st.markdown('<div class="section-head">🗓️ Today\'s Matches</div>', unsafe_allow_html=True)
    _n = len(today_matches)
    n_cols = 3 if _n >= 5 else min(_n, 4)
    _cols  = st.columns(n_cols)
    for _i, (_, _m) in enumerate(today_matches.iterrows()):
        with _cols[_i % n_cols]:
            _today_match_card(_m)

# ─────────────────────────────────────────────────────────────────────────────
# 4. COMPACT PICKS STRIP — single horizontal line
# ─────────────────────────────────────────────────────────────────────────────
_uid   = st.session_state.get("active_user_id", 1)
_uname = st.session_state.get("active_user_name", "You")
_uav   = st.session_state.get("active_user_avatar", "🐘")

if not today_matches.empty:
    _pick_parts: list[str] = []
    _n_unpicked = 0
    for _, _m in today_matches.iterrows():
        _mid  = int(_m['id'])
        _pdf  = get_picks_for_match(_mid)
        _urow = _pdf[_pdf['user_id'] == _uid] if not _pdf.empty else pd.DataFrame()
        _pick = _urow.iloc[0]['picked_team'] if not _urow.empty else None

        if _m['status'] == 'completed':
            if _pick:
                _pf = get_flag(_pick)
                hs, as_ = int(_m['home_score']), int(_m['away_score'])
                if (_pick == _m['home_team'] and hs > as_) or (_pick == _m['away_team'] and as_ > hs):
                    _res = "✅"
                elif hs == as_:
                    _res = "🟡"
                else:
                    _res = "❌"
                _pick_parts.append(
                    f"<span style='display:inline-flex;flex-direction:column;align-items:center;"
                    f"gap:0;line-height:1' title='{_pick}'>"
                    f"<span style='font-size:1.3rem'>{_pf}</span>"
                    f"<span style='font-size:.6rem'>{_res}</span></span>"
                )
            else:
                _pick_parts.append("<span style='font-size:.85rem;color:#475569'>—</span>")
        elif _pick:
            _pick_parts.append(f"<span style='font-size:1.4rem' title='{_pick}'>{get_flag(_pick)}</span>")
        else:
            _n_unpicked += 1
            _pick_parts.append(
                "<span style='font-size:.75rem;color:#475569;border:1px solid #334155;"
                "border-radius:50%;width:1.1rem;height:1.1rem;"
                "display:inline-flex;align-items:center;justify-content:center'>?</span>"
            )

    _tail = (
        f"<span style='margin-left:auto;font-size:.8rem;color:#FBBF24;font-weight:700'>⏳ {_n_unpicked} not picked</span>"
        if _n_unpicked else
        "<span style='margin-left:auto;font-size:.8rem;color:#4ADE80;font-weight:700'>✅ All picked!</span>"
    )
    st.markdown(
        f"<div class='picks-strip'>"
        f"<span style='font-size:1.2rem'>{_uav}</span>"
        f"<span style='font-size:.88rem;font-weight:800;color:#94A3B8;white-space:nowrap'>{_uname}'s Picks:</span>"
        f"<span style='display:flex;align-items:center;gap:.45rem'>{''.join(_pick_parts)}</span>"
        f"{_tail}</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 5. THREE-COLUMN: Leaderboard | Family Favorites | Discovery Race
# ─────────────────────────────────────────────────────────────────────────────
lb_col, fav_col, disc_col = st.columns([3, 4, 4])

# ── Race to the Cup ────────────────────────────────────────────────────────────
with lb_col:
    st.markdown('<div class="section-head">🏆 Race to the Cup</div>', unsafe_allow_html=True)
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣"]
    for i, entry in enumerate(combined):
        color = entry.get("theme_color") or "#E2E8F0"
        grp   = entry["group_pts"]
        ko    = entry["ko_live_pts"]
        tot   = entry["total_pts"]
        chips = (
            f"<span style='font-size:.65rem;color:#86EFAC'>⚽{grp:.1f}</span>"
            f"<span style='font-size:.65rem;color:#7DD3FC'>🎯{ko:.0f}</span>"
        )
        st.markdown(
            f"<div class='lb-row' style='background:{color}22;border-left:3px solid {color};"
            f"display:flex;align-items:center;gap:.5rem'>"
            f"<span style='font-size:2rem;flex-shrink:0'>{entry['avatar']}</span>"
            f"<div style='flex:1;min-width:0'>"
            f"<div style='font-size:1.05rem;font-weight:800'>{medals[i] if i < len(medals) else ''} {entry['name']}</div>"
            f"<div style='display:flex;gap:.4rem;flex-wrap:wrap;margin-top:.05rem'>"
            f"<span style='color:#FCD34D;font-size:.88rem;font-weight:700'>{tot:.1f} pts</span>"
            f"&nbsp;{chips}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
    st.page_link("pages/leaderboard.py", label="→ Full Breakdown", icon="📊")

# ── Family Favorites — compact [square image] + [text] media cards ─────────────
with fav_col:
    st.markdown('<div class="section-head">⭐ Family Favorites</div>', unsafe_allow_html=True)
    try:
        country_owners: dict[str, list] = {}
        no_fav_rows = []
        for i, (_, row) in enumerate(board.iterrows()):
            uid  = int(row['id'])
            favs = get_top_favorites(uid, 1)
            if favs:
                country_owners.setdefault(favs[0], []).append((i, row))
            else:
                no_fav_rows.append(row)

        sorted_countries = sorted(
            country_owners.items(),
            key=lambda item: (-len(item[1]), min(r for r, _ in item[1])),
        )

        for country, owners in sorted_countries:
            n_fans   = len(owners)
            border   = "#9333EA" if n_fans >= 4 else "#3B82F6" if n_fans >= 2 else "#D97706"
            stamp    = get_stamp(country)
            flag     = get_flag(country)
            landmark = stamp.get('stamp_label', '')
            pick_count = _country_total_picks(country)

            if n_fans == 1:
                ctx, ctx_color = f"❤️ {owners[0][1]['name']}'s #1 pick", "#94A3B8"
            elif n_fans == 2:
                ctx, ctx_color = "👨‍👩‍👧 Shared by 2 family members", "#60A5FA"
            else:
                ctx, ctx_color = f"👨‍👩‍👧 Shared by {n_fans} family members", "#A78BFA"

            av_html = "".join(
                "<span title='" + str(r["name"]) + "' style='font-size:1.2rem'>" + str(r["avatar"]) + "</span>"
                for _, r in owners
            )

            st.markdown(
                f"<div style='display:flex;align-items:flex-start;gap:.55rem;"
                f"border:2px solid {border};border-radius:10px;"
                f"padding:.4rem .55rem .4rem .4rem;margin:.18rem 0'>"
                + _country_sq_img(country, "78px")
                + f"<div style='min-width:0;flex:1'>"
                f"<div style='font-size:.93rem;font-weight:900'>{flag} {country}</div>"
                f"<div style='font-size:.7rem;color:#64748B;margin:.04rem 0'>{landmark}</div>"
                f"<div style='font-size:.72rem;font-weight:700;color:{ctx_color}'>{ctx}</div>"
                f"<div style='display:flex;gap:.15rem;margin:.06rem 0'>{av_html}</div>"
                f"<div style='font-size:.68rem;color:#475569'>⚽ {pick_count} pick{'s' if pick_count != 1 else ''}</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

        for row in no_fav_rows:
            st.markdown(
                f"<div style='border:1px solid rgba(255,255,255,.07);border-radius:10px;"
                f"padding:.38rem .65rem;margin:.18rem 0;opacity:.4;"
                f"display:flex;align-items:center;gap:.5rem'>"
                f"<span style='font-size:1.4rem'>{row['avatar']}</span>"
                f"<span style='font-size:.8rem;color:#94A3B8;font-style:italic'>"
                f"{row['name']} — keep exploring!</span></div>",
                unsafe_allow_html=True,
            )
    except Exception:
        st.caption("Favorites loading...")

# ── Discovery Race — promoted to first-class column ───────────────────────────
with disc_col:
    st.markdown('<div class="section-head">🌎 Discovery Race</div>', unsafe_allow_html=True)
    try:
        _exp_board  = get_explorer_leaderboard()
        _exp_weekly = get_weekly_explorer()

        if _exp_weekly and _exp_weekly.get('count', 0) > 0:
            _ew_word = "country" if _exp_weekly['count'] == 1 else "countries"
            st.markdown(
                f"<div style='background:rgba(168,85,247,.12);border-left:3px solid #A855F7;"
                f"border-radius:0 8px 8px 0;padding:.38rem .6rem;margin:.25rem 0 .45rem;"
                f"font-size:.8rem'>"
                f"<span style='color:#A855F7;font-weight:800'>🌟 This Week's Explorer</span><br>"
                f"<span style='color:#F1F5F9'>{_exp_weekly['avatar']} {_exp_weekly['name']}"
                f" — {_exp_weekly['count']} new {_ew_word}</span></div>",
                unsafe_allow_html=True,
            )

        medals_exp = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣"]
        for i, _erow in enumerate(_exp_board):
            _escore        = _erow['score']
            _etitle, _eemoji = get_badge(_escore)
            _ecolor        = _erow['theme_color']
            st.markdown(
                f"<div class='lb-row' style='background:{_ecolor}22;border-left:3px solid {_ecolor};"
                f"display:flex;align-items:center;gap:.5rem'>"
                f"<span style='font-size:2rem;flex-shrink:0'>{_erow['avatar']}</span>"
                f"<div><div style='font-size:1.05rem;font-weight:800'>"
                f"{medals_exp[i] if i < len(medals_exp) else ''} {_erow['name']}</div>"
                f"<div style='color:#475569;font-size:.82rem'><b>{_escore}</b> pts · {_eemoji} {_etitle}"
                f"</div></div></div>",
                unsafe_allow_html=True,
            )
        st.page_link("pages/discovery_race.py", label="→ Full Discovery Race", icon="🌎")
    except Exception:
        st.caption("Discovery Race loading...")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 5b. STORYLINES STRIP
# ─────────────────────────────────────────────────────────────────────────────
_uid_for_stories = st.session_state.get("active_user_id", 1)
try:
    _stories = _build_storylines(combined, _uid_for_stories)
except Exception:
    _stories = []

def _md_bold(s: str) -> str:
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)

if _stories:
    _s_cols = st.columns(len(_stories))
    for _si, (_scol, _story) in enumerate(zip(_s_cols, _stories)):
        with _scol:
            st.markdown(
                f"<div style='background:rgba(255,255,255,.04);"
                f"border:1px solid rgba(255,255,255,.1);border-radius:10px;"
                f"padding:.55rem .75rem;font-size:.85rem;color:#CBD5E1;line-height:1.45'>"
                f"{_md_bold(_story)}</div>",
                unsafe_allow_html=True,
            )
    st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 6. FAMILY STORY — full-width compact 2-column feed, deduplicated
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-head">📖 Family Story</div>', unsafe_allow_html=True)

_TIER_STYLE = {
    1: ("rgba(251,191,36,.07)",  "rgba(217,119,6,.55)"),
    2: ("rgba(16,185,129,.06)",  "rgba(16,185,129,.4)"),
    3: ("rgba(248,250,252,.03)", "rgba(255,255,255,.07)"),
}

story_items = _dedup_story(get_tiered_family_activity(limit=20))

if story_items.empty:
    st.markdown(
        "<div style='background:rgba(248,250,252,.05);border:1px solid rgba(255,255,255,.08);"
        "border-radius:12px;padding:1.2rem;text-align:center;color:#64748B'>"
        "<div style='font-size:2.5rem'>🗺️</div>"
        "<div style='font-weight:700;margin:.3rem 0'>The adventure begins here.</div>"
        "<div style='font-size:.88rem'>Explore countries and make picks to write the family story.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
else:
    _scols = st.columns(2)
    for _i, (_, _act) in enumerate(story_items.head(12).iterrows()):
        _icon, _narr = format_activity_message(_act)
        _tier  = int(_act.get('_tier', 3))
        _ts    = str(_act.get('timestamp', ''))[:10]
        _av    = str(_act.get('avatar', '⚽'))
        _name  = str(_act.get('user_name', ''))
        _bg, _border = _TIER_STYLE.get(_tier, _TIER_STYLE[3])

        # Merge grouped users
        _grp_avs = str(_act.get('_grp_avs') or '')
        if '|' in _grp_avs:
            _av = " ".join(a for a in _grp_avs.split('|')[:4] if a)
            _grp_names = str(_act.get('_grp_names') or '').split('|')
            _grp_names = [n for n in _grp_names if n]
            if len(_grp_names) <= 3:
                _name = " & ".join(_grp_names)
            else:
                _name = f"{len(_grp_names)} family members"

        with _scols[_i % 2]:
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:.45rem;padding:.28rem .55rem;"
                f"border-radius:8px;margin:.08rem 0;background:{_bg};border:1px solid {_border}'>"
                f"<span style='font-size:1.1rem;flex-shrink:0'>{_icon}</span>"
                f"<span style='font-size:.95rem;flex-shrink:0'>{_av}</span>"
                f"<span style='font-size:.84rem;font-weight:700;flex-shrink:0;color:#F1F5F9;"
                f"max-width:5.5rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>{_name}</span>"
                f"<span style='font-size:.83rem;flex:1;color:#CBD5E1;min-width:0;"
                f"overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>{_narr}</span>"
                f"<span style='font-size:.68rem;color:#475569;flex-shrink:0;white-space:nowrap'>{_ts}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 7. FEATURED PLAYER OF THE DAY
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-head">⭐ Featured Player of the Day</div>', unsafe_allow_html=True)
try:
    _fp = get_featured_player_of_day()
    if _fp:
        _fp_c1, _fp_c2 = st.columns([1, 3])
        with _fp_c1:
            st.markdown(
                f"<div style='text-align:center;padding:.5rem 0'>"
                f"<div style='font-size:4rem;line-height:1'>{_fp['flag']}</div>"
                f"<div style='font-size:2.2rem;font-weight:900;color:#FCD34D;margin:.1rem 0'>#{_fp['shirt_number']}</div>"
                f"<div style='font-size:1rem;font-weight:900;color:#F1F5F9;line-height:1.2'>{_fp['name']}</div>"
                f"<div style='font-size:.82rem;color:#94A3B8;margin-top:.1rem'>{_fp['team']}</div>"
                f"<div style='font-size:.78rem;color:#64748B'>{_fp['position']} · {_fp['club_short']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if st.button("👤 Learn More", key=f"home_fp_{_fp['player_slug']}", use_container_width=True):
                _show_player_modal_home(_fp['player_slug'])
        with _fp_c2:
            st.markdown(
                f"<div style='background:linear-gradient(160deg,#1E293B,#0F172A);"
                f"border-left:4px solid #F59E0B;border-radius:0 14px 14px 0;"
                f"padding:1rem 1.2rem;height:100%;color:white;"
                f"border:1px solid rgba(148,163,184,.12)'>"
                f"<div style='font-size:.65rem;font-weight:800;color:#D97706;"
                f"text-transform:uppercase;letter-spacing:.07em;margin-bottom:.4rem'>"
                f"⭐ One Thing To Remember</div>"
                f"<div style='font-size:1.05rem;color:#F1F5F9;line-height:1.6;font-weight:500'>"
                f"{_fp['one_thing']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("Roster data loading...")
except Exception:
    st.caption("Featured player loading...")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 8. WORLD ATLAS PREVIEW
# ─────────────────────────────────────────────────────────────────────────────
_map_head, _map_btn = st.columns([5, 1])
with _map_head:
    st.markdown('<div class="section-head">🌎 World Atlas</div>', unsafe_allow_html=True)
with _map_btn:
    st.markdown("&nbsp;", unsafe_allow_html=True)
    if st.button("Open Full Atlas →", use_container_width=True, key="home_open_atlas"):
        st.switch_page("pages/map.py")

try:
    _map_teams   = get_all_teams()
    _map_iso3, _ = get_iso3_maps(_map_teams)
    _active_uid  = st.session_state.get("active_user_id", 1)
    _map_disc_df = get_discoveries(_active_uid)
    _map_disc    = set(_map_disc_df["country_name"].tolist()) if not _map_disc_df.empty else set()
    _map_cheered = set(get_cheered_for(_active_uid))
    _map_won     = set(get_won_with(_active_uid))
    _map_favs    = get_family_top_favorites(n=5)
    # Include both group-stage and KO match teams in the "playing today" highlight
    _map_today = set(today_matches["home_team"].tolist() + today_matches["away_team"].tolist())
    for _ktm in today_ko:
        if _ktm.get("home_name"):
            _map_today.add(_ktm["home_name"])
        if _ktm.get("away_name"):
            _map_today.add(_ktm["away_name"])

    _mini_fig = build_atlas_figure(
        layer="today", teams_df=_map_teams,
        discoveries=_map_disc, cheered=_map_cheered, won=_map_won,
        family_favs=_map_favs, today_countries=_map_today, height=300,
    )
    _mini_event = st.plotly_chart(_mini_fig, on_select="rerun",
                                  use_container_width=True, key="home_mini_atlas")
    if _mini_event and _mini_event.selection and _mini_event.selection.points:
        _pt   = _mini_event.selection.points[0]
        _iso3 = _pt.get("location")
        if _iso3 and _iso3 in _map_iso3:
            st.session_state["_nav_country"] = _map_iso3[_iso3]
            st.switch_page("pages/country_profile.py")

    if _map_today:
        _today_flags = " ".join(
            str(_map_teams.loc[_map_teams["name"] == n, "flag_emoji"].values[0])
            for n in sorted(_map_today)
            if not _map_teams.loc[_map_teams["name"] == n, "flag_emoji"].empty
        )
        _today_lbl = "⚽ Playing today" if today_ko else "🗓 Playing today"
        st.caption(f"{_today_lbl}: {_today_flags}  ·  📍 Blue = USA · Red = Canada · Green = Mexico")
    else:
        st.caption("📍 Blue = USA · Red = Canada · Green = Mexico")
except Exception:
    st.info("🌎 Map loading...")
