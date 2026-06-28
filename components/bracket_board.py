# components/bracket_board.py
#
# Phase 6B: Knockout bracket — renders real data from knockout_matches table.
# Layout: R32 (16) → R16 (8) → QF (4) → SF (2) → Final + 3rd Place
#
# Phase 6C hook: add family pick avatars to match cards / final column
# Phase 6D hook: add click-to-expand match detail panel

import streamlit as st
from services.knockout import get_knockout_rounds

# ── Dimensions ────────────────────────────────────────────────────────────────
_BS   = 88    # base slot height for R32 (px) — generous to give match cards clear breathing room
_GAP  = 22    # gap between columns (px)
_STUB = _GAP + 2   # outgoing connector stub — crosses the gap by 2px into next col
_CONN = '#9C8B6E'  # connector colour (warm brown)
_TOTAL_H = 16 * _BS  # total bracket height = 1408px

# Slot heights double each round so a pair in round N
# occupies the same vertical space as one slot in round N+1
_SH = {
    'r32': _BS,
    'r16': _BS * 2,
    'qf':  _BS * 4,
    'sf':  _BS * 8,
}


# ── Match data model ──────────────────────────────────────────────────────────

def _make_match(match_id: str,
                team1=None, team2=None,
                flag1=None, flag2=None,
                score1=None, score2=None,
                winner=None) -> dict:
    """Create a single match record.

    Fields:
        match_id  — stable identifier used as a data- attribute on the card HTML
        team1/2   — display name (str) or None for TBD
        flag1/2   — flag emoji (str) or None
        score1/2  — integer score or None (None = match not yet played)
        winner    — "team1" | "team2" | "draw" | None

    Phase 6B: populate team, flag, score, and winner from the knockout matches
              table in worldcup.db (queried via services/matches.py).
    """
    return {
        "match_id": match_id,
        "team1":    team1,
        "team2":    team2,
        "flag1":    flag1,
        "flag2":    flag2,
        "score1":   score1,
        "score2":   score2,
        "winner":   winner,   # explicit — set at DB load time after scores entered
        "pens_str": "",
    }


def _placeholder_rounds() -> dict:
    """Fallback all-TBD data used if knockout_matches table is unavailable."""
    return {
        "r32":         [_make_match(f"r32_{i+1}")  for i in range(16)],
        "r16":         [_make_match(f"r16_{i+1}")  for i in range(8)],
        "qf":          [_make_match(f"qf_{i+1}")   for i in range(4)],
        "sf":          [_make_match(f"sf_{i+1}")   for i in range(2)],
        "final":       [_make_match("final_1")],
        "third_place": [_make_match("third_1")],
    }


# ── Rendering helpers ─────────────────────────────────────────────────────────

def render_team_row(team, flag, score, is_winner=False, is_loser=False) -> str:
    """Render one team row (flag + name + score) inside a match card.

    Phase 6B: is_winner/is_loser are derived from completed match scores.
    Phase 6C: add a small pick indicator (avatar dot) when a family member
              picked this team — insert after score_h.
    """
    row_cls = "bk-win" if is_winner else ("bk-lose" if is_loser else "")
    flag_h  = f'<span class="bk-fl">{flag}</span>' if flag \
              else '<span class="bk-fl bk-fl-e">·</span>'
    name_h  = f'<span class="bk-nm">{team}</span>' if team \
              else '<span class="bk-nm bk-nm-tbd">TBD</span>'
    score_h = f'<span class="bk-sc">{score}</span>' if score is not None \
              else '<span class="bk-sc bk-sc-e"></span>'
    return f'<div class="bk-tr {row_cls}">{flag_h}{name_h}{score_h}</div>'


def render_match_card(match: dict, extra_class: str = "") -> str:
    """Render a match card from a match dict.

    Handles three display states:
      - Empty/TBD:   both teams None, dashed border, muted styling
      - Scheduled:   teams known, no scores yet
      - Completed:   scores present, winner/loser rows highlighted

    Phase 6B: completed-state styling activates automatically when
              score1/score2 are populated (or winner field is set).
    Phase 6C: add family pick avatar strip below the two team rows.
              Insert a <div class="bk-picks">...</div> before the closing </div>.
    Phase 6D: wire data-mid attribute to a click handler that opens
              a match detail panel via st.session_state.
    """
    team1  = match.get("team1")
    team2  = match.get("team2")
    flag1  = match.get("flag1")
    flag2  = match.get("flag2")
    score1 = match.get("score1")
    score2 = match.get("score2")
    winner = match.get("winner")   # explicit winner field from DB

    is_complete = score1 is not None and score2 is not None

    # Resolve winner/loser booleans
    # Phase 6B: winner field is set by admin score entry; fallback to score comparison
    if winner == "team1":
        w1, l1, w2, l2 = True, False, False, True
    elif winner == "team2":
        w1, l1, w2, l2 = False, True, True, False
    elif winner == "draw":
        w1, l1, w2, l2 = False, False, False, False
    elif is_complete:
        if score1 > score2:
            w1, l1, w2, l2 = True, False, False, True
        elif score2 > score1:
            w1, l1, w2, l2 = False, True, True, False
        else:
            w1, l1, w2, l2 = False, False, False, False
    else:
        w1, l1, w2, l2 = False, False, False, False

    # Card CSS class
    is_empty = not team1 and not team2
    base_cls = "bk-card"
    if is_empty:
        base_cls += " bk-empty-card"
    elif is_complete:
        base_cls += " bk-done"
    if extra_class:
        base_cls += f" {extra_class}"

    displayed_score1 = score1 if is_complete else None
    displayed_score2 = score2 if is_complete else None

    row1 = render_team_row(team1, flag1, displayed_score1, w1, l1)
    row2 = render_team_row(team2, flag2, displayed_score2, w2, l2)

    # Penalty line (only for completed tied-score matches)
    pens_str = match.get("pens_str", "")
    pens_html = (
        f'<div class="bk-pens">{pens_str}</div>'
        if pens_str else ""
    )

    return (
        f'<div class="{base_cls}" data-mid="{match.get("match_id", "")}">'
        f'{row1}'
        f'<div class="bk-sep"></div>'
        f'{row2}'
        f'{pens_html}'
        f'</div>'
    )


def render_round_column(round_id: str, matches: list) -> str:
    """Render one bracket column (r32, r16, qf, sf).

    Matches are processed as consecutive pairs: matches[0]+[1] feed
    into r16[0], matches[2]+[3] feed into r16[1], etc.

    Phase 6B: advancement logic populates team/flag in the next round's
              match records at data-load time (not here in the renderer).
    Phase 6D: add id to each .bk-slot for connector-line positioning if
              switching to SVG-based connectors.
    """
    sh = _SH[round_id]
    pairs = ""
    for i in range(0, len(matches), 2):
        m1 = matches[i]
        m2 = matches[i + 1] if i + 1 < len(matches) else _make_match(f"bye_{i}")
        pairs += (
            f'<div class="bk-pair">'
            f'  <div class="bk-slot" style="height:{sh}px">{render_match_card(m1)}</div>'
            f'  <div class="bk-slot" style="height:{sh}px">{render_match_card(m2)}</div>'
            f'</div>'
        )
    return f'<div class="bk-col" id="bk-{round_id}">{pairs}</div>'


def render_final_column(final_match: dict, third_match: dict) -> str:
    """Render the rightmost column: Final card + 3rd Place card.

    The Final card centre is anchored at 50% of the bracket height so it
    aligns with the SF outgoing connector stub (which also fires at 50%).

    Vertical math for #bk-champ-area top:
        trophy  ≈ 38px  (font-size 2.4rem, line-height 1)
        gap          7px
        FINAL label ≈ 14px  (font-size 0.72rem)
        gap          7px
        card centre ≈ 25px  (card ~50px tall)
        ─────────────────
        total above card centre ≈ 91px
    → top = calc(50% − 91px) places card centre at bracket midpoint.

    Phase 6B: final_match and third_match come from _placeholder_rounds()["final"][0]
              and ["third_place"][0], swapped for real DB records.
    Phase 6C: family pick avatars for the Final appear inside render_match_card().
    Phase 6D: click handler on bk-final-card opens match detail panel.
    """
    total_h = _TOTAL_H
    return (
        f'<div class="bk-col" id="bk-final-col" style="height:{total_h}px">'

        # ── Champion block ─────────────────────────────────────────────────────
        f'  <div id="bk-champ-area">'
        f'    <div class="bk-trophy">🏆</div>'
        f'    <div class="bk-final-lbl">FINAL</div>'
        f'    {render_match_card(final_match, "bk-final-card")}'
        f'  </div>'

        # ── 3rd Place block ────────────────────────────────────────────────────
        # Anchored well below the Final so it reads as secondary/bonus.
        # top: calc(50% + 175px) gives ~84px of clear space below the Final card bottom.
        f'  <div id="bk-third-area">'
        f'    <div class="bk-third-sep"></div>'
        f'    <div class="bk-third-lbl">🥉 3rd Place</div>'
        f'    {render_match_card(third_match, "bk-third-card")}'
        f'  </div>'

        f'</div>'
    )


# ── CSS ───────────────────────────────────────────────────────────────────────

def _css() -> str:
    gap, stub, conn = _GAP, _STUB, _CONN
    total_h = _TOTAL_H
    return f"""
<style>
/* ── scroll wrapper — horizontal scroll fallback for narrow screens ── */
#bk-outer {{
    width: 100%;
    overflow-x: auto;
    padding: 20px 0 36px;
    -webkit-overflow-scrolling: touch;
}}

/* ── board (parchment poster) ── */
#bk-board {{
    position: relative;
    width: 100%;
    max-width: 1400px;
    box-sizing: border-box;
    background: #F6F0E4;
    background-image:
        repeating-linear-gradient(0deg, transparent, transparent 29px, rgba(160,140,110,.055) 30px),
        repeating-linear-gradient(90deg, transparent, transparent 29px, rgba(160,140,110,.04) 30px);
    border-radius: 10px;
    border: 1px solid #C8B89A;
    box-shadow: 0 8px 36px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.7);
    padding: 42px 28px 50px;
    margin: 0 auto;
    font-family: Georgia, 'Times New Roman', serif;
    color: #241608;
}}

/* ── tape corners ── */
.bk-tape {{
    position: absolute;
    width: 54px; height: 17px;
    background: rgba(255,234,150,.72);
    border: 1px solid rgba(210,190,100,.5);
    box-shadow: 0 1px 5px rgba(0,0,0,.16);
    z-index: 10;
}}
.bk-tape-tl {{ top:-8px;  left:36px;  transform:rotate(-8deg); }}
.bk-tape-tr {{ top:-8px;  right:36px; transform:rotate(8deg);  }}
.bk-tape-bl {{ bottom:-8px; left:36px;  transform:rotate(8deg);  }}
.bk-tape-br {{ bottom:-8px; right:36px; transform:rotate(-8deg); }}

/* ── sticky note ── */
#bk-sticky {{
    position: absolute;
    top: 52px;
    left: 50px;
    background: #FEFCB2;
    border: 1px solid #DACC5A;
    padding: 7px 10px;
    font-size: .67rem;
    line-height: 1.55;
    color: #5A3E08;
    transform: rotate(-2.2deg);
    box-shadow: 2px 3px 9px rgba(0,0,0,.15);
    max-width: 110px;
    z-index: 20;
}}

/* ── title ── */
#bk-heading {{ text-align: center; margin-bottom: 18px; }}
#bk-title {{
    font-size: 1.55rem;
    font-weight: 700;
    letter-spacing: .13em;
    color: #1A0E04;
    text-transform: uppercase;
    line-height: 1.2;
}}
#bk-subtitle {{
    font-size: .8rem;
    color: #7A6B50;
    letter-spacing: .07em;
    margin-top: 3px;
}}

/* ── round labels: same flex structure as the columns below ── */
#bk-labels {{
    display: flex;
    gap: {gap}px;
    margin-bottom: 10px;
    overflow: visible;
}}
.bk-lbl {{
    flex: 1;
    min-width: 80px;
    font-size: .65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .1em;
    color: #8A7A60;
    text-align: center;
    white-space: nowrap;
}}

/* ── bracket row ── */
#bk-rounds {{
    display: flex;
    align-items: flex-start;
    gap: {gap}px;
    overflow: visible;
}}

/* ── columns: flex:1 distributes board width equally across all 5 columns.
   Cards are width:100% so connector right edges always land at card edges. ── */
.bk-col {{
    flex: 1;
    min-width: 90px;
    display: flex;
    flex-direction: column;
    overflow: visible;
}}

/* ── pairs: LOCAL connector lines only ──────────────────────────────────────
   ::before  — vertical line spanning only card-centre to card-centre (25%→75%)
   ::after   — short outgoing stub pointing toward the next column
   ── */
.bk-pair {{
    position: relative;
    display: flex;
    flex-direction: column;
    overflow: visible;
}}
.bk-pair::before {{
    content: '';
    position: absolute;
    top: 25%;       /* = centre of first slot */
    height: 50%;    /* = distance between the two card centres */
    right: 0;       /* = right edge of card (pair fills column width) */
    width: 2px;
    background: {conn};
}}
.bk-pair::after {{
    content: '';
    position: absolute;
    top: 50%;
    right: -{stub}px;
    width: {stub}px;
    height: 2px;
    background: {conn};
    transform: translateY(-1px);
}}

/* ── slots ── */
.bk-slot {{
    display: flex;
    align-items: center;
    overflow: visible;
    position: relative;
    flex-shrink: 0;
}}

/* ── match cards: fill their column ── */
.bk-card {{
    width: 100%;
    box-sizing: border-box;
    background: #F9F4EC;
    border: 1.5px solid #C4AE88;
    border-radius: 5px;
    overflow: hidden;
    cursor: pointer;
    box-shadow: 0 1px 4px rgba(0,0,0,.09);
    transition: box-shadow .15s, transform .12s;
}}
.bk-card:hover {{
    box-shadow: 0 4px 14px rgba(0,0,0,.18);
    transform: translateY(-1px);
}}
.bk-empty-card  {{ background: transparent; border-style: dashed; border-color: #BCA882; opacity: .6; }}
.bk-done        {{ border-color: #9EBC98; background: #F5F9F4; }}
.bk-final-card  {{ border-width: 2px; border-color: #B08030; box-shadow: 0 3px 12px rgba(0,0,0,.18); background: #FDF7EC; }}
.bk-third-card  {{ opacity: .85; }}

/* ── team rows — transparent inside the card, no individual boxes ── */
.bk-tr     {{ display: flex; align-items: center; gap: 5px; padding: 5px 8px; font-size: .75rem; background: transparent; }}
.bk-fl     {{ font-size: 1rem; flex-shrink: 0; }}
.bk-fl-e   {{ color: #C0AA88; font-size: .7rem; }}
.bk-nm     {{ flex: 1; font-weight: 600; color: #241608; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.bk-nm-tbd {{ color: #B0A080; font-weight: 400; font-style: italic; font-size: .69rem; }}
.bk-sc     {{ font-weight: 700; font-size: .84rem; color: #241608; min-width: 14px; text-align: right; flex-shrink: 0; }}
.bk-sc-e   {{ min-width: 14px; }}
.bk-pens   {{ font-size: .6rem; color: #8B7D6B; text-align: center; padding: 2px 6px 3px;
              border-top: 1px solid #E4DBCE; font-style: italic; }}
/* separator between the two teams within one match card — clear enough to read "two teams, one match" */
.bk-sep    {{ height: 1px; background: #C8B48A; margin: 0; }}

/* ── winner / loser row highlights ── */
.bk-win          {{ background: rgba(175,228,175,.22); }}
.bk-win .bk-nm   {{ color: #185018; font-weight: 700; }}
.bk-lose .bk-fl  {{ opacity: .4; }}
.bk-lose .bk-nm  {{ color: #A09080; font-weight: 400; text-decoration: line-through; }}
.bk-lose .bk-sc  {{ color: #A09080; }}

/* ── final column: block layout for absolute-positioned inner sections ── */
#bk-final-col {{
    position: relative;
    display: block !important;   /* override .bk-col flex layout so absolute children work */
    overflow: visible;
    /* inherits flex:1 + min-width:90px from .bk-col */
}}

/* Champion block: top = 50% − 91px → Final card centre lands at bracket midpoint
   (the SF pair's ::after stub fires at top:50% of the pair, which equals 50%
   of the total bracket height since there is only one SF pair) */
#bk-champ-area {{
    position: absolute;
    top: calc(50% - 91px);
    left: 0;
    right: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 7px;
    padding: 0 6px;
    box-sizing: border-box;
}}
.bk-trophy    {{ font-size: 2.4rem; line-height: 1; }}
.bk-final-lbl {{
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .18em;
    color: #B07828;
    text-transform: uppercase;
}}

/* 3rd Place: top = 50% + 175px → ~84px of clear space below the Final card bottom
   (Final card bottom ≈ 50% + 25px card-half + 7px gap = ~50% + 91px) */
#bk-third-area {{
    position: absolute;
    top: calc(50% + 175px);
    left: 0;
    right: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    padding: 0 6px;
    box-sizing: border-box;
}}
.bk-third-sep {{
    width: 55%;
    height: 1px;
    background: rgba(160,140,110,.45);
    margin-bottom: 6px;
}}
.bk-third-lbl {{
    font-size: .64rem;
    font-weight: 700;
    letter-spacing: .12em;
    color: #8A7A60;
    text-transform: uppercase;
}}

/* Phase 6C: family pick avatar strip (hidden until 6C wires it) */
.bk-picks {{
    display: flex;
    gap: 2px;
    justify-content: center;
    padding: 3px 6px 2px;
    border-top: 1px solid #E4DBCE;
    font-size: .85rem;
}}
</style>
"""


# ── Public entry point ────────────────────────────────────────────────────────

def render_knockout_bracket_shell() -> None:
    """Render the full knockout bracket via st.markdown.

    Phase 6C hook: render_match_card() has a commented pick-avatar hook.
    Phase 6D hook: wire data-mid attribute to Streamlit component click handler.
    """
    try:
        rounds = get_knockout_rounds()
    except Exception:
        rounds = _placeholder_rounds()

    round_cols = (
        render_round_column("r32", rounds["r32"])
        + render_round_column("r16", rounds["r16"])
        + render_round_column("qf",  rounds["qf"])
        + render_round_column("sf",  rounds["sf"])
        + render_final_column(rounds["final"][0], rounds["third_place"][0])
    )

    labels = (
        '<div class="bk-lbl">Round of 32</div>'
        '<div class="bk-lbl">Round of 16</div>'
        '<div class="bk-lbl">Quarterfinals</div>'
        '<div class="bk-lbl">Semifinals</div>'
        '<div class="bk-lbl">Final</div>'
    )

    html = f"""
{_css()}
<div id="bk-outer">
  <div id="bk-board">
    <div class="bk-tape bk-tape-tl"></div>
    <div class="bk-tape bk-tape-tr"></div>
    <div class="bk-tape bk-tape-bl"></div>
    <div class="bk-tape bk-tape-br"></div>
    <div id="bk-sticky">Every pick.<br/>Every match.<br/>One champion. 🏆</div>
    <div id="bk-heading">
      <div id="bk-title">🏆 Road to the Final</div>
      <div id="bk-subtitle">2026 FIFA World Cup · Knockout Stage</div>
    </div>
    <div id="bk-labels">{labels}</div>
    <div id="bk-rounds">{round_cols}</div>
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)
