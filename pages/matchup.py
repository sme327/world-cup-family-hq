import streamlit as st
import pandas as pd
from services.matches import get_match_by_id, get_all_matches
from services.teams import get_team_by_name, get_flag
from services.picks import get_picks_for_match, save_pick, get_all_users
from services.time_utils import fmt_match_time
from services.images import get_country_image_html
from services.roster import get_featured_players, get_team_summary, get_mls_players


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_pipe(val) -> list[str]:
    if not val or pd.isna(val):
        return []
    return [s.strip() for s in str(val).split('|') if s.strip()]


def _safe(val, default="—"):
    return val if val and not pd.isna(val) else default


def _pick_result(picked, home_team, away_team, home_score, away_score):
    if pd.isna(home_score) or pd.isna(away_score):
        return None
    hs, as_ = int(home_score), int(away_score)
    if hs == as_:
        return 0.5
    return 1.0 if picked == (home_team if hs > as_ else away_team) else 0.0


def _role_color(role: str) -> str:
    if "Captain" in role:     return "#7C3AED"
    if "Youngest" in role:    return "#16A34A"
    if "Oldest" in role:      return "#D97706"
    if "MLS" in role:         return "#0369A1"
    return "#475569"


# ── Resolve active match ──────────────────────────────────────────────────────
if "_nav_match_id" in st.session_state:
    match_id = int(st.session_state.pop("_nav_match_id"))
    st.query_params["match_id"] = str(match_id)
else:
    try:
        match_id = int(st.query_params.get("match_id", 1))
    except (ValueError, TypeError):
        match_id = 1

match = get_match_by_id(match_id)
if match is None:
    st.error("Match not found.")
    st.stop()

home_team = match['home_team']
away_team = match['away_team']
home_flag = get_flag(home_team)
away_flag = get_flag(away_team)
home_data = get_team_by_name(home_team)
away_data = get_team_by_name(away_team)
is_completed = match['status'] == 'completed'

# ── Resolve active user ───────────────────────────────────────────────────────
active_user    = st.session_state.get("active_user_name",   "Shawn")
active_user_id = st.session_state.get("active_user_id",     1)

# ── Sidebar ───────────────────────────────────────────────────────────────────
users = get_all_users()
with st.sidebar:
    st.markdown("### 🔍 Jump to Match")
    all_matches = get_all_matches()
    match_labels = [
        f"{r['group_letter']}{r['match_number']}: {r['home_team']} vs {r['away_team']} ({r['match_date']})"
        for _, r in all_matches.iterrows()
    ]
    match_ids = all_matches['id'].tolist()
    current_idx = match_ids.index(match_id) if match_id in match_ids else 0
    selected_label = st.selectbox("Match", match_labels, index=current_idx)
    selected_id = match_ids[match_labels.index(selected_label)]
    if selected_id != match_id:
        st.query_params["match_id"] = str(selected_id)
        st.rerun()

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.mu-section { font-size:1.25rem; font-weight:800; margin:1.2rem 0 .5rem; }
.pick-card  {
    border-radius:14px; padding:1.3rem 1rem; text-align:center; color:white;
    transition:all .15s; cursor:pointer;
}
.cheer-card {
    background:#F8FAFC; border-radius:12px; padding:.7rem .5rem;
    text-align:center; border:1px solid #E2E8F0; margin:.2rem;
}
.squad-card {
    background:linear-gradient(160deg,#1E293B,#0F172A); border-radius:12px;
    padding:.9rem 1rem; color:white; flex:1;
}
.mls-card {
    background:linear-gradient(135deg,#064E3B,#065F46);
    border-radius:12px; padding:.9rem 1.1rem; color:white; margin:.3rem 0;
}
.debate-card {
    background:#F1F5F9; border-radius:12px; padding:.75rem 1rem;
    border-left:4px solid #3B82F6; margin:.35rem 0;
}
.city-card {
    background:linear-gradient(135deg,#1E293B,#0F172A);
    border-radius:14px; padding:1.1rem 1.3rem; color:white;
}
</style>
""", unsafe_allow_html=True)

# ── 1. Match Hero Header ──────────────────────────────────────────────────────
if is_completed:
    hs, as_ = int(match['home_score']), int(match['away_score'])
    if hs > as_:   status_badge = f"FINAL · {home_team} wins {hs}–{as_}"
    elif as_ > hs: status_badge = f"FINAL · {away_team} wins {hs}–{as_}"
    else:          status_badge = f"FINAL · Draw {hs}–{as_}"
    score_html = f"<span style='font-size:2.2rem;font-weight:900;color:#FCD34D'>{hs} – {as_}</span>"
else:
    time_str = fmt_match_time(match['match_date'], match['kickoff_time_et'])
    status_badge = f"Group {match['group_letter']} · {time_str}"
    score_html   = "<span style='font-size:2rem;font-weight:900;color:#FCD34D'>VS</span>"

st.markdown(
    '<div style="background:linear-gradient(135deg,#1E3A5F,#2563EB,#1E3A5F);'
    'padding:1.8rem;border-radius:16px;text-align:center;color:white;margin-bottom:1rem">'
    f'<div style="font-size:4rem;line-height:1">{home_flag} {score_html} {away_flag}</div>'
    f'<div style="font-size:1.7rem;font-weight:900;margin:.4rem 0">{home_team} &nbsp;vs&nbsp; {away_team}</div>'
    f'<div style="font-size:.9rem;color:#CBD5E1">{status_badge}</div>'
    f'<div style="font-size:.85rem;color:#94A3B8;margin-top:.2rem">📍 {match["venue"]}, {match["city"]}</div>'
    '</div>',
    unsafe_allow_html=True
)

# ── 2. Family Picks ───────────────────────────────────────────────────────────
st.markdown('<div class="mu-section">🏷️ Family Picks</div>', unsafe_allow_html=True)

picks_df = get_picks_for_match(match_id)
pick_by_user = {pk['user_name']: pk['picked_team'] for _, pk in picks_df.iterrows()} if not picks_df.empty else {}

def _pick_card(team: str, flag: str, is_home: bool):
    pickers      = [(u['name'], u['avatar']) for _, u in users.iterrows() if pick_by_user.get(u['name']) == team]
    user_pick    = pick_by_user.get(active_user)
    picked_by_me = user_pick == team

    # Card gradient colors
    bg = "linear-gradient(135deg,#1E3A5F,#2563EB)" if is_home else "linear-gradient(135deg,#064E3B,#059669)"
    default_border = "#3B82F6" if is_home else "#10B981"

    # Result state for completed matches
    opacity = 1.0
    result_badge = pts_badge = ""
    if is_completed:
        r = _pick_result(team, home_team, away_team, match['home_score'], match['away_score'])
        if r == 1.0:
            border = "#FCD34D"
            result_badge = "<div style='font-size:1.3rem;margin:.2rem 0'>🏆</div><div style='color:#FCD34D;font-weight:800;font-size:.95rem'>Winner!</div>"
            if pickers: pts_badge = "<div style='color:#4ADE80;font-weight:700;font-size:.88rem;margin-top:.3rem'>🟢 +1 pt each</div>"
        elif r == 0.5:
            border = "#FCD34D"
            result_badge = "<div style='color:#FCD34D;font-weight:700;font-size:.9rem;margin:.2rem 0'>🤝 Draw</div>"
            if pickers: pts_badge = "<div style='color:#FCD34D;font-weight:700;font-size:.88rem;margin-top:.3rem'>🟡 +0.5 pts each</div>"
        else:
            border, opacity = "rgba(148,163,184,.25)", 0.6
            if pickers: pts_badge = "<div style='color:#F87171;font-weight:700;font-size:.88rem;margin-top:.3rem'>🔴 +0 pts</div>"
    else:
        border = "#FCD34D" if picked_by_me else default_border

    avatars_html = " ".join(
        f"<span title='{n}' style='font-size:2.8rem;display:inline-block;margin:.05rem'>{a}</span>"
        for n, a in pickers
    ) or "<span style='color:rgba(255,255,255,.4);font-size:.85rem'>No picks yet</span>"

    # Status label
    if not is_completed:
        if picked_by_me:
            status_label = f"<div style='color:#FCD34D;font-size:.82rem;font-weight:700;margin-top:.4rem'>✅ You picked this</div>"
        elif user_pick:
            status_label = "<div style='color:rgba(255,255,255,.4);font-size:.8rem;margin-top:.4rem'>You picked the other team</div>"
        else:
            status_label = "<div style='color:rgba(255,255,255,.6);font-size:.82rem;margin-top:.4rem'>👆 Tap to pick</div>"
    else:
        status_label = ""

    st.markdown(
        f"<div class='pick-card' style='background:{bg};border:3px solid {border};opacity:{opacity}'>"
        f"<div style='font-size:4rem;line-height:1;margin-bottom:.25rem'>{flag}</div>"
        f"<div style='font-size:1.4rem;font-weight:900;color:white'>{team}</div>"
        f"{result_badge}"
        f"<div style='margin:.5rem 0'>{avatars_html}</div>"
        f"{pts_badge}{status_label}"
        f"</div>",
        unsafe_allow_html=True
    )

    if not is_completed:
        btn = f"✅ Picked {team}" if picked_by_me else f"Pick {team}"
        if st.button(btn, key=f"pick_{match_id}_{team}", use_container_width=True):
            save_pick(active_user_id, match_id, team)
            st.rerun()

home_col, away_col = st.columns(2)
with home_col:
    _pick_card(home_team, home_flag, is_home=True)
with away_col:
    _pick_card(away_team, away_flag, is_home=False)

if is_completed:
    hs2, as2 = int(match['home_score']), int(match['away_score'])
    if hs2 > as2:   result_msg = f"**{home_team}** won {hs2}–{as2}. Points have been awarded."
    elif as2 > hs2: result_msg = f"**{away_team}** won {hs2}–{as2}. Points have been awarded."
    else:           result_msg = f"It finished {hs2}–{as2} — a draw! Everyone who picked earns 0.5 pts."
    st.caption(f"Final result — {result_msg}")
else:
    st.caption("Tap your team to register your pick. No locking — you can change it any time.")

# ── 3. Who Should I Cheer For? ────────────────────────────────────────────────
st.divider()
st.markdown('<div class="mu-section">🤔 Who Should I Cheer For?</div>', unsafe_allow_html=True)
st.caption("Pick your side! Here's why you might love each team…")

def _cheer_col(team, flag, data):
    if data is None:
        return
    # Country image header
    img = get_country_image_html(team, height='120px', border_radius='12px')
    if img:
        st.markdown(img, unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:1.1rem;font-weight:800;margin:.4rem 0'>{flag} {team}</div>",
        unsafe_allow_html=True
    )
    reasons = _parse_pipe(data.get('cheer_reasons'))
    if not reasons:
        st.caption("They're still awesome!")
        return
    cols = st.columns(min(len(reasons), 4))
    for i, reason in enumerate(reasons[:4]):
        # Format: "Text Label 🎯" — emoji at end, text before it
        parts = reason.rsplit(' ', 1)
        if len(parts) == 2:
            label, emoji = parts[0].strip(), parts[1].strip()
        else:
            label, emoji = reason, "⭐"
        with cols[i % len(cols)]:
            st.markdown(
                f"<div class='cheer-card'>"
                f"<div style='font-size:2.2rem;line-height:1.1'>{emoji}</div>"
                f"<div style='font-size:.82rem;font-weight:700;color:#0F172A;margin-top:.35rem;line-height:1.3'>{label}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

cheer_c1, cheer_c2 = st.columns(2)
with cheer_c1:
    _cheer_col(home_team, home_flag, home_data)
with cheer_c2:
    _cheer_col(away_team, away_flag, away_data)

# ── 4. Key Players ────────────────────────────────────────────────────────────
st.divider()
st.markdown('<div class="mu-section">⭐ Key Players</div>', unsafe_allow_html=True)

h_captain  = _safe(home_data.get('captain') if home_data is not None else None, '')
a_captain  = _safe(away_data.get('captain') if away_data is not None else None, '')
h_featured = get_featured_players(home_team, h_captain)
a_featured = get_featured_players(away_team, a_captain)

def _player_trading_card(p: dict) -> str:
    role_color = _role_color(p['role'])
    return (
        "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);"
        "border-radius:12px;padding:.9rem .7rem;text-align:center;color:white;"
        "border:1px solid rgba(148,163,184,.15);min-width:110px;flex:1'>"
        f"<div style='background:{role_color};color:white;border-radius:4px;"
        f"font-size:.62rem;font-weight:800;padding:.1rem .4rem;"
        f"display:inline-block;letter-spacing:.04em;margin-bottom:.4rem'>{p['role']}</div>"
        f"<div style='font-size:2rem;font-weight:900;color:#FCD34D;line-height:1'>#{p['shirt_number']}</div>"
        f"<div style='font-size:.9rem;font-weight:900;line-height:1.2;margin:.2rem 0'>{p['name']}</div>"
        f"<div style='font-size:.75rem;color:#94A3B8'>{p['position']}</div>"
        f"<div style='font-size:.72rem;color:#64748B;margin-top:.15rem'>{p['club_short']}</div>"
        f"<div style='font-size:.7rem;color:#475569'>Age {p['age']}</div>"
        "</div>"
    )

kp_c1, kp_c2 = st.columns(2)
for col, team, flag, featured in [
    (kp_c1, home_team, home_flag, h_featured),
    (kp_c2, away_team, away_flag, a_featured),
]:
    with col:
        st.markdown(
            f"<div style='font-size:1rem;font-weight:800;margin-bottom:.4rem'>{flag} {team}</div>",
            unsafe_allow_html=True
        )
        if featured:
            cards = "".join(_player_trading_card(p) for p in featured[:3])
            st.markdown(
                f"<div style='display:flex;gap:.4rem;flex-wrap:wrap'>{cards}</div>",
                unsafe_allow_html=True
            )
        else:
            st.caption("Roster data unavailable.")

# ── 5. Country Comparison ─────────────────────────────────────────────────────
st.divider()
st.markdown('<div class="mu-section">🌍 Country Comparison</div>', unsafe_allow_html=True)

def _country_card(team, flag, data):
    if data is None:
        st.caption("Data unavailable.")
        return
    card = (
        "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);"
        "border-radius:14px;padding:1.1rem;color:white;height:100%'>"
        f"<div style='font-size:3rem;margin-bottom:.3rem'>{flag}</div>"
        f"<div style='font-size:1.3rem;font-weight:900;margin-bottom:.6rem'>{team}</div>"
        "<div style='font-size:.82rem;line-height:1.8;color:#CBD5E1'>"
        f"🏙️ <b>Capital:</b> {_safe(data.get('capital'))}<br>"
        f"👥 <b>Population:</b> {_safe(data.get('population'))}<br>"
        f"🗣️ <b>Languages:</b> {_safe(data.get('languages'))}<br>"
        f"💰 <b>Currency:</b> {_safe(data.get('currency'))}<br>"
        f"🏆 <b>FIFA Rank:</b> #{_safe(data.get('fifa_ranking'))}<br>"
        f"🎽 <b>Coach:</b> {_safe(data.get('coach'))}"
        "</div>"
        "</div>"
    )
    st.markdown(card, unsafe_allow_html=True)
    if st.button(f"🌍 Open {team} Profile", key=f"cp_{team}", use_container_width=True):
        st.session_state["_nav_country"] = team
        st.switch_page("pages/country_profile.py")

cc1, cc2 = st.columns(2)
with cc1:
    _country_card(home_team, home_flag, home_data)
with cc2:
    _country_card(away_team, away_flag, away_data)

# ── 6. Squad Comparison ───────────────────────────────────────────────────────
h_sum = get_team_summary(home_team)
a_sum = get_team_summary(away_team)

if h_sum and a_sum:
    st.divider()
    st.markdown('<div class="mu-section">📊 Squad Comparison</div>', unsafe_allow_html=True)

    def _squad_card_html(team, flag, s) -> str:
        return (
            "<div class='squad-card'>"
            f"<div style='font-size:2rem;margin-bottom:.2rem'>{flag}</div>"
            f"<div style='font-size:.95rem;font-weight:800;margin-bottom:.5rem'>{team}</div>"
            f"<div style='font-size:.82rem;line-height:1.9;color:#CBD5E1'>"
            f"📅 Avg Age: <b>{float(s.get('average_age',0)):.1f}</b><br>"
            f"🧤 GK:  <b>{int(s.get('goalkeepers',0))}</b><br>"
            f"🛡️ DEF: <b>{int(s.get('defenders',0))}</b><br>"
            f"⚙️ MID: <b>{int(s.get('midfielders',0))}</b><br>"
            f"⚽ FWD: <b>{int(s.get('forwards',0))}</b>"
            f"</div></div>"
        )

    h_card = _squad_card_html(home_team, home_flag, h_sum)
    a_card = _squad_card_html(away_team, away_flag, a_sum)
    vs_div = "<div style='display:flex;align-items:center;justify-content:center;color:#94A3B8;font-size:1.4rem;padding:0 .5rem'>🆚</div>"
    st.markdown(
        f"<div style='display:flex;gap:.5rem;align-items:stretch'>{h_card}{vs_div}{a_card}</div>",
        unsafe_allow_html=True
    )

# ── 7. MLS & US Connections ───────────────────────────────────────────────────
h_mls = get_mls_players(home_team)
a_mls = get_mls_players(away_team)

if not h_mls.empty or not a_mls.empty:
    st.divider()
    st.markdown('<div class="mu-section">🏟️ MLS & US Connections</div>', unsafe_allow_html=True)

    def _mls_callout(team, flag, mls_df):
        if mls_df.empty:
            return
        rows = "".join(
            f"<div style='font-size:.85rem;margin:.3rem 0;color:#A7F3D0'>"
            f"#{int(p['shirt_number'])} <b>{p['player_name']}</b> — {p['club_short']}</div>"
            for _, p in mls_df.iterrows()
        )
        st.markdown(
            "<div class='mls-card'>"
            f"<div style='font-size:1rem;font-weight:800;margin-bottom:.3rem'>"
            f"{flag} {team} · {len(mls_df)} MLS Player{'s' if len(mls_df)!=1 else ''}</div>"
            f"<div style='border-top:1px solid rgba(255,255,255,.15);margin:.4rem 0'></div>"
            f"{rows}</div>",
            unsafe_allow_html=True
        )

    mls_c1, mls_c2 = st.columns(2)
    with mls_c1:
        _mls_callout(home_team, home_flag, h_mls)
        if h_mls.empty:
            st.caption(f"No MLS players on {home_team}'s squad.")
    with mls_c2:
        _mls_callout(away_team, away_flag, a_mls)
        if a_mls.empty:
            st.caption(f"No MLS players on {away_team}'s squad.")

# ── 8. Family Debate Corner ───────────────────────────────────────────────────
st.divider()
st.markdown('<div class="mu-section">💬 Family Debate Corner</div>', unsafe_allow_html=True)

h_rank = home_data.get('fifa_ranking') if home_data is not None else None
a_rank = away_data.get('fifa_ranking') if away_data is not None else None
h_best = _safe(home_data.get('best_finish') if home_data is not None else None)
a_best = _safe(away_data.get('best_finish') if away_data is not None else None)
h_apps = home_data.get('wc_appearances') if home_data is not None else None
a_apps = away_data.get('wc_appearances') if away_data is not None else None

debate_cards = []

if h_rank and a_rank:
    diff = abs(int(h_rank) - int(a_rank))
    if diff > 30:
        underdog = away_team if int(h_rank) < int(a_rank) else home_team
        fav      = home_team if int(h_rank) < int(a_rank) else away_team
        debate_cards.append({
            'icon': '🏆', 'color': '#7C3AED',
            'title': 'Favorite vs Underdog',
            'body': f"FIFA #{min(int(h_rank),int(a_rank))} {fav} vs #{max(int(h_rank),int(a_rank))} {underdog}.",
            'question': f"Can {underdog} pull off the upset today?",
        })
    else:
        debate_cards.append({
            'icon': '⚖️', 'color': '#3B82F6',
            'title': 'Well-Matched Teams',
            'body': f"FIFA #{h_rank} {home_team} vs #{a_rank} {away_team} — very close in the rankings.",
            'question': "Which team wants it more today?",
        })

if h_apps and a_apps and int(h_apps) > int(a_apps) + 5:
    debate_cards.append({
        'icon': '📜', 'color': '#D97706',
        'title': 'Experience Gap',
        'body': f"{home_team} has {h_apps} World Cup appearances; {away_team} has {a_apps}.",
        'question': "Does experience matter more than hunger?",
    })

if "Winner" in str(h_best) or "Winner" in str(a_best):
    champ = home_team if "Winner" in str(h_best) else away_team
    debate_cards.append({
        'icon': '🥇', 'color': '#16A34A',
        'title': 'Former Champions',
        'body': f"{champ} has won the World Cup before!",
        'question': "Does that history give them an edge, or extra pressure?",
    })

if not debate_cards:
    debate_cards.append({
        'icon': '🔥', 'color': '#DC2626',
        'title': f"Group {match['group_letter']} Battle",
        'body': f"Both {home_team} and {away_team} need points to advance.",
        'question': "Who do you think needs this win more?",
    })

for card in debate_cards:
    c_color = card['color']
    st.markdown(
        f"<div class='debate-card' style='border-left-color:{c_color}'>"
        f"<div style='font-size:.95rem;font-weight:800;color:#0F172A'>{card['icon']} {card['title']}</div>"
        f"<div style='font-size:.85rem;color:#475569;margin:.2rem 0'>{card['body']}</div>"
        f"<div style='font-size:.82rem;color:{c_color};font-style:italic;margin-top:.3rem'>"
        f"💬 {card['question']}</div>"
        f"</div>",
        unsafe_allow_html=True
    )

# ── 9. Host City Explorer ─────────────────────────────────────────────────────
st.divider()
st.markdown('<div class="mu-section">🏙️ Host City</div>', unsafe_allow_html=True)

CITY_FACTS = {
    "Mexico City":   ("🇲🇽", "One of Earth's largest cities at 2,240m altitude — players tire faster here! The Azteca has hosted two World Cup finals."),
    "Guadalajara":   ("🇲🇽", "Birthplace of mariachi music and home to tequila country! Mexico's second-largest city."),
    "Monterrey":     ("🇲🇽", "Mexico's industrial powerhouse nestled in the Sierra Madre mountains."),
    "East Rutherford": ("🇺🇸", "Right outside New York City — the World Cup FINAL will be played here on July 19!"),
    "Arlington":     ("🇺🇸", "Home of AT&T Stadium (Dallas Cowboys), famous for the world's largest HD screen."),
    "Los Angeles":   ("🇺🇸", "Hollywood, sunshine, and SoFi Stadium — home of the Rams and Chargers."),
    "Santa Clara":   ("🇺🇸", "Silicon Valley! Levi's Stadium near the Golden Gate Bridge."),
    "Philadelphia":  ("🇺🇸", "The City of Brotherly Love — where the Declaration of Independence was signed."),
    "Miami Gardens": ("🇺🇸", "South Florida energy! Lionel Messi's Inter Miami plays just nearby."),
    "Kansas City":   ("🇺🇸", "Home of legendary BBQ and Arrowhead — one of the loudest stadiums on Earth."),
    "Foxborough":    ("🇺🇸", "Near Boston! Gillette Stadium, home of the Patriots and New England history."),
    "Atlanta":       ("🇺🇸", "The ATL! Mercedes-Benz Stadium has a retractable roof over Atlanta United's home."),
    "Seattle":       ("🇺🇸", "🏠 The Espinosa family home city! Lumen Field — Sounders FC territory."),
    "Houston":       ("🇺🇸", "Space City! NRG Stadium is near NASA Mission Control."),
    "Vancouver":     ("🇨🇦", "Mountains meet ocean — BC Place is one of the most beautiful settings of the tournament."),
    "Toronto":       ("🇨🇦", "Canada's biggest city! BMO Field, home of Toronto FC and the CN Tower skyline."),
}

city = match['city']
city_flag, city_fact = CITY_FACTS.get(city, ("📍", f"One of the 16 host cities for the 2026 World Cup."))

st.markdown(
    "<div class='city-card'>"
    f"<div style='font-size:1.6rem;font-weight:900;margin-bottom:.1rem'>{city_flag} {city}</div>"
    f"<div style='color:#94A3B8;font-size:.82rem;margin-bottom:.6rem'>🏟️ {match['venue']} · {match['host_country']}</div>"
    f"<div style='font-size:.88rem;color:#CBD5E1;line-height:1.55'>{city_fact}</div>"
    "</div>",
    unsafe_allow_html=True
)

if st.button("🏙️ Full City Guide", key="host_city_btn"):
    st.switch_page("pages/host_cities.py")
