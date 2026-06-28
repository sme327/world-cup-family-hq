# components/bracket_board.py
#
# Phase 6A: Knockout bracket visual shell — left-to-right compact layout.
#
# Layout: R32 (16 matches) → R16 (8) → QF (4) → SF (2) → Final + 3rd Place
#
# Phase 6B TODO: replace _placeholder_data() with _load_knockout_data()
#   querying matches WHERE stage IN ('Round of 32','Round of 16',
#   'Quarterfinal','Semifinal','Final','Third Place')
# Phase 6C TODO: wire family picks (avatars under each team row)
# Phase 6D TODO: click-to-expand match detail panel

import streamlit as st

# ── Dimensions ────────────────────────────────────────────────────────────────
_CW   = 138   # card width (px)
_BS   = 52    # base slot height for R32; doubles each round
_GAP  = 16    # gap between columns (px); connector stubs span exactly this
_STUB = _GAP + 2   # stub length is slightly longer than gap for clean overlap
_CONN = '#9C8B6E'  # connector line colour (warm brown)
_TOTAL_H = 16 * _BS  # total bracket height = 832 px (16 R32 slots)

# Slot height per round
_SH = {
    'r32': _BS,
    'r16': _BS * 2,
    'qf':  _BS * 4,
    'sf':  _BS * 8,
}


# ── Data helpers ──────────────────────────────────────────────────────────────

def _empty():
    return {'home': '', 'away': '', 'hf': '', 'af': '',
            'hs': None, 'as_': None, 'status': 'scheduled', 'id': None}


def _placeholder_data():
    """All-empty bracket dicts for the Phase 6A shell.
    Phase 6B: replace this with a real DB query.
    """
    return {
        'r32':   [_empty() for _ in range(16)],
        'r16':   [_empty() for _ in range(8)],
        'qf':    [_empty() for _ in range(4)],
        'sf':    [_empty() for _ in range(2)],
        'final': _empty(),
        'third': _empty(),
    }


# ── HTML card builders ────────────────────────────────────────────────────────

def _team_row(flag: str, name: str, score, cls: str = '') -> str:
    flag_h  = f'<span class="bk-fl">{flag}</span>' if flag \
              else '<span class="bk-fl bk-fl-e">·</span>'
    name_h  = f'<span class="bk-nm">{name}</span>' if name \
              else '<span class="bk-nm bk-nm-tbd">TBD</span>'
    score_h = f'<span class="bk-sc">{score}</span>' if score is not None \
              else '<span class="bk-sc bk-sc-e"></span>'
    return f'<div class="bk-tr {cls}">{flag_h}{name_h}{score_h}</div>'


def _card(m: dict, extra: str = '') -> str:
    h,  a   = m.get('home', ''),  m.get('away', '')
    hf, af  = m.get('hf', ''),   m.get('af', '')
    hs, as_ = m.get('hs'),        m.get('as_')
    done    = m.get('status') == 'completed' and hs is not None and as_ is not None

    if done:
        hi, ai = int(hs), int(as_)
        hc = 'bk-win' if hi > ai else ('bk-lose' if hi < ai else '')
        ac = 'bk-win' if ai > hi else ('bk-lose' if ai < hi else '')
        cc = 'bk-card bk-done'
    else:
        hc = ac = ''
        cc = 'bk-card' + (' bk-empty-card' if not h and not a else '')

    return (f'<div class="{cc} {extra}" data-mid="{m.get("id","")}">'
            f'{_team_row(hf, h, hs if done else None, hc)}'
            f'<div class="bk-sep"></div>'
            f'{_team_row(af, a, as_ if done else None, ac)}'
            f'</div>')


# ── Column builders ───────────────────────────────────────────────────────────

def _round_col(matches: list, rnd: str) -> str:
    """One bracket column: pairs of match slots with connector bracket lines."""
    sh = _SH[rnd]
    pairs = ''
    for i in range(0, len(matches), 2):
        m1 = matches[i]
        m2 = matches[i + 1] if i + 1 < len(matches) else _empty()
        pairs += (
            f'<div class="bk-pair">'
            f'<div class="bk-slot" style="height:{sh}px">{_card(m1)}</div>'
            f'<div class="bk-slot" style="height:{sh}px">{_card(m2)}</div>'
            f'</div>'
        )
    return f'<div class="bk-col" id="bk-{rnd}">{pairs}</div>'


def _final_col(final: dict, third: dict) -> str:
    """Final column: trophy icon, Final card, 3rd Place card — vertically centred."""
    return (
        f'<div class="bk-col" id="bk-final-col" style="min-height:{_TOTAL_H}px">'
        f'  <div id="bk-final-inner">'
        f'    <div class="bk-trophy">🏆</div>'
        f'    <div class="bk-final-lbl">FINAL</div>'
        f'    {_card(final, "bk-final-card")}'
        f'    <div class="bk-third-lbl">3rd Place</div>'
        f'    {_card(third, "bk-third-card")}'
        f'  </div>'
        f'</div>'
    )


# ── CSS ───────────────────────────────────────────────────────────────────────

def _css() -> str:
    cw, gap, stub, conn = _CW, _GAP, _STUB, _CONN
    total_h = _TOTAL_H
    return f"""
<style>
/* ── scroll wrapper ── */
#bk-outer {{
    width: 100%;
    overflow-x: auto;
    padding: 20px 0 32px;
    -webkit-overflow-scrolling: touch;
}}

/* ── board (parchment poster) ── */
#bk-board {{
    position: relative;
    /* min-width keeps bracket from collapsing; allow growth */
    min-width: 820px;
    max-width: 960px;
    background: #F6F0E4;
    background-image:
        repeating-linear-gradient(0deg, transparent, transparent 29px, rgba(160,140,110,.055) 30px),
        repeating-linear-gradient(90deg, transparent, transparent 29px, rgba(160,140,110,.04) 30px);
    border-radius: 10px;
    border: 1px solid #C8B89A;
    box-shadow: 0 8px 36px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.7);
    padding: 42px 34px 50px;
    margin: 0 auto;
    font-family: Georgia, 'Times New Roman', serif;
    color: #241608;
    box-sizing: border-box;
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
    bottom: 28px;
    right: 50px;
    background: #FEFCB2;
    border: 1px solid #DACC5A;
    padding: 7px 10px;
    font-size: .69rem;
    line-height: 1.55;
    color: #5A3E08;
    transform: rotate(2.5deg);
    box-shadow: 2px 3px 9px rgba(0,0,0,.15);
    max-width: 120px;
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

/* ── round labels row ── */
#bk-labels {{
    display: flex;
    gap: {gap}px;
    align-items: flex-end;
    margin-bottom: 8px;
    overflow: visible;
}}
.bk-lbl {{
    font-size: .65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .1em;
    color: #8A7A60;
    text-align: center;
    white-space: nowrap;
    flex-shrink: 0;
    width: {cw}px;
}}
.bk-lbl-final {{ flex: 1; min-width: {cw}px; }}

/* ── bracket row ── */
#bk-rounds {{
    display: flex;
    align-items: flex-start;
    gap: {gap}px;
    overflow: visible;
}}

/* ── columns ── */
.bk-col {{
    display: flex;
    flex-direction: column;
    overflow: visible;
    flex-shrink: 0;
    width: {cw}px;
}}

/* ── pairs: bracket vertical line + outgoing stub ── */
.bk-pair {{
    position: relative;
    display: flex;
    flex-direction: column;
    overflow: visible;
    border-right: 2px solid {conn};
}}
/* Outgoing horizontal stub from pair midpoint → next column */
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

/* ── slots: fixed-height cell, centres the card vertically ── */
.bk-slot {{
    display: flex;
    align-items: center;
    overflow: visible;
    position: relative;
    flex-shrink: 0;
}}

/* ── match cards ── */
.bk-card {{
    width: {cw}px;
    background: #FFFDF6;
    border: 1.5px solid #C8B890;
    border-radius: 5px;
    overflow: hidden;
    cursor: pointer;
    box-shadow: 0 1px 4px rgba(0,0,0,.1);
    transition: box-shadow .15s, transform .12s;
    flex-shrink: 0;
    box-sizing: border-box;
}}
.bk-card:hover {{
    box-shadow: 0 4px 14px rgba(0,0,0,.2);
    transform: translateY(-1px);
}}
.bk-empty-card {{
    background: #F2EBE0;
    border-style: dashed;
    border-color: #BCA882;
    opacity: .72;
}}
.bk-done {{ border-color: #9EBC98; }}
.bk-final-card {{ border-width: 2px; border-color: #B08030; box-shadow: 0 2px 8px rgba(0,0,0,.15); }}
.bk-third-card {{ opacity: .88; }}

/* ── team rows ── */
.bk-tr {{
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 6px;
    font-size: .74rem;
}}
.bk-fl       {{ font-size: 1rem; flex-shrink: 0; }}
.bk-fl-e     {{ color: #C0AA88; font-size: .7rem; }}
.bk-nm       {{ flex: 1; font-weight: 600; color: #241608; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 82px; }}
.bk-nm-tbd   {{ color: #B0A080; font-weight: 400; font-style: italic; font-size: .69rem; }}
.bk-sc       {{ font-weight: 700; font-size: .84rem; color: #241608; min-width: 13px; text-align: right; flex-shrink: 0; }}
.bk-sc-e     {{ min-width: 13px; }}
.bk-sep      {{ height: 1px; background: #E4DBCE; margin: 0 5px; }}

/* winner / loser styling */
.bk-win          {{ background: rgba(175,228,175,.22); }}
.bk-win .bk-nm   {{ color: #185018; font-weight: 700; }}
.bk-lose .bk-fl  {{ opacity: .4; }}
.bk-lose .bk-nm  {{ color: #A09080; font-weight: 400; text-decoration: line-through; }}
.bk-lose .bk-sc  {{ color: #A09080; }}

/* ── final column ── */
#bk-final-col {{
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    flex: 1 !important;
    width: auto !important;
}}
#bk-final-inner {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 7px;
    padding: 0 8px;
}}
.bk-trophy     {{ font-size: 2.2rem; line-height: 1; }}
.bk-final-lbl  {{
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .18em;
    color: #B07828;
    text-transform: uppercase;
}}
.bk-third-lbl  {{
    font-size: .65rem;
    font-weight: 700;
    letter-spacing: .13em;
    color: #8A7A60;
    text-transform: uppercase;
    margin-top: 16px;
}}
</style>
"""


# ── Public entry point ────────────────────────────────────────────────────────

def render_knockout_bracket_shell() -> None:
    """Render the full knockout bracket shell via st.markdown.

    Layout: R32 → R16 → QF → SF → Final (left-to-right, compact).
    Phase 6A: all slots are placeholder/empty — no scoring or pick logic.
    """
    data = _placeholder_data()

    round_cols = (
        _round_col(data['r32'], 'r32')
        + _round_col(data['r16'], 'r16')
        + _round_col(data['qf'],  'qf')
        + _round_col(data['sf'],  'sf')
        + _final_col(data['final'], data['third'])
    )

    labels = (
        f'<div class="bk-lbl">Round of 32</div>'
        f'<div class="bk-lbl">Round of 16</div>'
        f'<div class="bk-lbl">Quarterfinals</div>'
        f'<div class="bk-lbl">Semifinals</div>'
        f'<div class="bk-lbl bk-lbl-final">🏆 Final</div>'
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
