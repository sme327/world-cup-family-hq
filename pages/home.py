import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime as _dt
from services.matches import get_all_matches
from services.scoring import get_leaderboard
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

board = get_leaderboard()

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
if not board.empty:
    lr = board.iloc[0]
    leader_html = (
        f"<div style='font-size:.85rem;color:#CBD5E1;margin:.2rem 0'>"
        f"🏆 Leader: {lr['avatar']} <b>{lr['name']}</b> "
        f"<span style='color:#FCD34D'>{float(lr['total_points']):.1f} pts</span>"
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
match_label = (
    f"🗓 {n_today} Match{'es' if n_today != 1 else ''} Today"
    if n_today > 0 else "🗓 No matches today"
)

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
# 3. TODAY'S MATCHES — 3-col grid for 5-6, 4-col otherwise
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-head">🗓️ Today\'s Matches</div>', unsafe_allow_html=True)

if today_matches.empty:
    st.info("No matches today — check the Schedule for upcoming matches!")
else:
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

# ── Leaderboard ───────────────────────────────────────────────────────────────
with lb_col:
    st.markdown('<div class="section-head">🏆 Leaderboard</div>', unsafe_allow_html=True)
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣"]
    for i, (_, row) in enumerate(board.iterrows()):
        pts   = float(row['total_points'])
        wins  = int(row['correct_picks'])
        cw    = int(row.get('countries_won', 0))
        color = row.get('theme_color', '#E2E8F0')
        st.markdown(
            f"<div class='lb-row' style='background:{color}22;border-left:3px solid {color};"
            f"display:flex;align-items:center;gap:.5rem'>"
            f"<span style='font-size:2rem;flex-shrink:0'>{row['avatar']}</span>"
            f"<div><div style='font-size:1.05rem;font-weight:800'>{medals[i] if i < len(medals) else ''} {row['name']}</div>"
            f"<div style='color:#475569;font-size:.88rem'><b>{pts:.1f}</b> pts · {wins} wins · {cw} 🌍</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

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
    _map_today   = set(today_matches["home_team"].tolist() + today_matches["away_team"].tolist())

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
        st.caption(f"⚡ Playing today: {_today_flags}  ·  📍 Blue = USA · Red = Canada · Green = Mexico")
    else:
        st.caption("📍 Blue = USA · Red = Canada · Green = Mexico")
except Exception:
    st.info("🌎 Map loading...")
