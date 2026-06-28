# components/bracket_board.py
#
# Phase 6A: Knockout bracket visual shell.
# Renders a wall-poster-style HTML/CSS bracket via st.markdown.
#
# Phase 6B TODO: replace _placeholder_data() with _load_knockout_data()
#   that queries the matches table for stage IN ('Round of 32', 'Round of 16',
#   'Quarterfinal', 'Semifinal', 'Final', 'Third Place') and maps to match dicts.
# Phase 6C TODO: wire family picks into cards (avatars under each team row).
# Phase 6D TODO: click-to-expand match detail panel.

import streamlit as st

# ── Constants ─────────────────────────────────────────────────────────────────
_CW   = 155   # card width (px)
_GAP  = 18    # gap between round columns (px); connectors span exactly this
_CONN = '#9C8B6E'   # connector line colour (warm brown)
_BRD  = '#2px solid ' + '#9C8B6E'

# Slot height doubles each round so cards stay centred relative to their feeder pair
_SH = {'r32': 78, 'r16': 156, 'qf': 312, 'sf': 624}


# ── Data helpers ──────────────────────────────────────────────────────────────

def _empty():
    return {'home': '', 'away': '', 'hf': '', 'af': '',
            'hs': None, 'as_': None, 'status': 'scheduled', 'id': None}


def _placeholder_data():
    """Return all-empty bracket dicts for the Phase 6A shell."""
    return {
        'r32_l': [_empty() for _ in range(8)],
        'r16_l': [_empty() for _ in range(4)],
        'qf_l':  [_empty() for _ in range(2)],
        'sf_l':  [_empty()],
        'final': _empty(),
        'third': _empty(),
        'sf_r':  [_empty()],
        'qf_r':  [_empty() for _ in range(2)],
        'r16_r': [_empty() for _ in range(4)],
        'r32_r': [_empty() for _ in range(8)],
    }


# ── HTML builders ─────────────────────────────────────────────────────────────

def _team_row(flag: str, name: str, score, extra_cls: str = '') -> str:
    flag_h  = f'<span class="bk-fl">{flag}</span>' if flag \
              else '<span class="bk-fl bk-fl-empty">·</span>'
    name_h  = f'<span class="bk-nm">{name}</span>' if name \
              else '<span class="bk-nm bk-nm-tbd">TBD</span>'
    score_h = f'<span class="bk-sc">{score}</span>' if score is not None \
              else '<span class="bk-sc bk-sc-empty"></span>'
    return f'<div class="bk-tr {extra_cls}">{flag_h}{name_h}{score_h}</div>'


def _card(m: dict, extra_cls: str = '') -> str:
    h, a   = m.get('home', ''), m.get('away', '')
    hf, af = m.get('hf', ''), m.get('af', '')
    hs, as_ = m.get('hs'), m.get('as_')
    done   = m.get('status') == 'completed' and hs is not None and as_ is not None

    if done:
        hs_i, as_i = int(hs), int(as_)
        h_cls = 'bk-win' if hs_i > as_i else ('bk-lose' if hs_i < as_i else '')
        a_cls = 'bk-win' if as_i > hs_i else ('bk-lose' if as_i < hs_i else '')
        card_cls = 'bk-card bk-done'
    else:
        h_cls = a_cls = ''
        card_cls = 'bk-card' + (' bk-empty-card' if not h and not a else '')

    mid = m.get('id', '')
    return (f'<div class="{card_cls} {extra_cls}" data-mid="{mid}">'
            f'{_team_row(hf, h, hs if done else None, h_cls)}'
            f'<div class="bk-sep"></div>'
            f'{_team_row(af, a, as_ if done else None, a_cls)}'
            f'</div>')


def _slot(m: dict, rnd: str, side: str) -> str:
    h = _SH[rnd]
    return (f'<div class="bk-slot bk-slot-{side}" style="height:{h}px">'
            f'{_card(m)}'
            f'</div>')


def _pair(m1: dict, m2: dict, rnd: str, side: str) -> str:
    return (f'<div class="bk-pair bk-pair-{side}">'
            f'{_slot(m1, rnd, side)}'
            f'{_slot(m2, rnd, side)}'
            f'</div>')


def _col_left(matches: list, rnd: str) -> str:
    ms = list(matches)
    if rnd == 'sf':
        inner = _slot(ms[0], 'sf', 'left')
    else:
        inner = ''.join(_pair(ms[i], ms[i+1], rnd, 'left')
                        for i in range(0, len(ms), 2))
    return f'<div class="bk-col bk-{rnd}-left">{inner}</div>'


def _col_right(matches: list, rnd: str) -> str:
    ms = list(matches)
    if rnd == 'sf':
        inner = _slot(ms[0], 'sf', 'right')
    else:
        inner = ''.join(_pair(ms[i], ms[i+1], rnd, 'right')
                        for i in range(0, len(ms), 2))
    return f'<div class="bk-col bk-{rnd}-right">{inner}</div>'


def _final_col(final: dict, third: dict) -> str:
    return (f'<div class="bk-col bk-final-col">'
            f'<div class="bk-trophy">🏆</div>'
            f'<div class="bk-final-lbl">FINAL</div>'
            f'{_card(final, "bk-final-card")}'
            f'<div class="bk-third-lbl">3rd Place</div>'
            f'{_card(third, "bk-third-card")}'
            f'</div>')


# ── CSS ───────────────────────────────────────────────────────────────────────

def _css() -> str:
    cw, gap, conn = _CW, _GAP, _CONN
    # stub extends (gap+2)px so it visually crosses the gap even with border-box rounding
    stub = gap + 2
    return f"""
<style>
/* ── scroll wrapper ── */
#bk-outer {{
    width: 100%;
    overflow-x: auto;
    padding: 24px 0 36px;
    -webkit-overflow-scrolling: touch;
}}

/* ── board (parchment poster) ── */
#bk-board {{
    position: relative;
    min-width: 1640px;
    background: #F6F0E4;
    background-image:
        repeating-linear-gradient(0deg, transparent, transparent 29px, rgba(160,140,110,.06) 30px),
        repeating-linear-gradient(90deg, transparent, transparent 29px, rgba(160,140,110,.04) 30px);
    border-radius: 10px;
    border: 1px solid #C8B89A;
    box-shadow: 0 8px 36px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.7);
    padding: 44px 36px 52px;
    margin: 0 auto;
    font-family: Georgia, 'Times New Roman', serif;
    color: #241608;
    box-sizing: border-box;
}}

/* ── tape corners ── */
.bk-tape {{
    position: absolute;
    width: 58px;
    height: 19px;
    background: rgba(255,234,160,.72);
    border: 1px solid rgba(220,196,110,.5);
    box-shadow: 0 1px 5px rgba(0,0,0,.18);
    z-index: 10;
}}
.bk-tape-tl {{ top:-9px;  left:40px;  transform:rotate(-8deg); }}
.bk-tape-tr {{ top:-9px;  right:40px; transform:rotate(8deg);  }}
.bk-tape-bl {{ bottom:-9px; left:40px;  transform:rotate(8deg);  }}
.bk-tape-br {{ bottom:-9px; right:40px; transform:rotate(-8deg); }}

/* ── sticky note ── */
.bk-sticky {{
    position: absolute;
    top: 36px;
    right: 60px;
    background: #FEFCB8;
    border: 1px solid #DDD060;
    padding: 8px 11px;
    font-size: .71rem;
    line-height: 1.55;
    color: #5A3E0A;
    transform: rotate(2.8deg);
    box-shadow: 2px 3px 9px rgba(0,0,0,.16);
    max-width: 128px;
    z-index: 20;
}}

/* ── title ── */
#bk-heading {{ text-align: center; margin-bottom: 20px; }}
#bk-title {{
    font-size: 1.75rem;
    font-weight: 700;
    letter-spacing: .14em;
    color: #1A0E04;
    text-transform: uppercase;
    line-height: 1.2;
}}
#bk-subtitle {{
    font-size: .83rem;
    color: #7A6B50;
    letter-spacing: .07em;
    margin-top: 3px;
}}

/* ── round labels ── */
#bk-labels {{
    display: flex;
    align-items: center;
    gap: {gap}px;
    margin-bottom: 10px;
    overflow: visible;
}}
.bk-lbl {{
    font-size: .68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .1em;
    color: #8A7A60;
    text-align: center;
    white-space: nowrap;
    flex-shrink: 0;
}}
.bk-lbl-rnd  {{ width: {cw}px; }}
.bk-lbl-fin  {{ flex: 1; }}

/* ── bracket row ── */
#bk-rounds {{
    display: flex;
    align-items: center;
    gap: {gap}px;
    overflow: visible;
}}

/* ── round columns ── */
.bk-col {{
    display: flex;
    flex-direction: column;
    overflow: visible;
    flex-shrink: 0;
}}

/* ── pairs: vertical bracket line + outgoing stub ── */
.bk-pair {{
    display: flex;
    flex-direction: column;
    position: relative;
    overflow: visible;
}}
.bk-pair-left  {{ border-right: 2px solid {conn}; }}
.bk-pair-right {{ border-left:  2px solid {conn}; }}

/* outgoing horizontal stub from pair midpoint → next column */
.bk-pair-left::after {{
    content: '';
    position: absolute;
    top: 50%;
    right: -{stub}px;
    width: {stub}px;
    height: 2px;
    background: {conn};
    transform: translateY(-1px);
}}
.bk-pair-right::before {{
    content: '';
    position: absolute;
    top: 50%;
    left: -{stub}px;
    width: {stub}px;
    height: 2px;
    background: {conn};
    transform: translateY(-1px);
}}

/* ── slots: fixed-height cell centring the card ── */
.bk-slot {{
    display: flex;
    align-items: center;
    overflow: visible;
    position: relative;
    flex-shrink: 0;
}}

/* SF → Final connectors (only SF slots need explicit stubs; all others use pair ::after/::before) */
.bk-sf-left  .bk-slot::after {{
    content: '';
    position: absolute;
    top: 50%;
    right: -{stub}px;
    width: {stub}px;
    height: 2px;
    background: {conn};
    transform: translateY(-1px);
}}
.bk-sf-right .bk-slot::before {{
    content: '';
    position: absolute;
    top: 50%;
    left: -{stub}px;
    width: {stub}px;
    height: 2px;
    background: {conn};
    transform: translateY(-1px);
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
}}
.bk-card:hover {{
    box-shadow: 0 4px 14px rgba(0,0,0,.2);
    transform: translateY(-1px);
}}
.bk-empty-card {{
    background: #F3EDE3;
    border-style: dashed;
    border-color: #C0AA88;
    opacity: .75;
}}
.bk-done  {{ border-color: #9EBC98; }}

/* Final & Third Place cards are slightly wider */
.bk-final-card {{ width: 168px; border-width: 2px; border-color: #B8963A; }}
.bk-third-card {{ width: 168px; }}

/* ── team rows ── */
.bk-tr {{
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 5px 7px;
    font-size: .77rem;
}}
.bk-fl       {{ font-size: 1.05rem; flex-shrink: 0; }}
.bk-fl-empty {{ color: #C0AA88; font-size: .75rem; }}
.bk-nm {{
    flex: 1;
    font-weight: 600;
    color: #241608;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 88px;
}}
.bk-nm-tbd {{ color: #B0A080; font-weight: 400; font-style: italic; font-size:.72rem; }}
.bk-sc       {{ font-weight: 700; font-size: .88rem; color: #241608; min-width: 14px; text-align: right; flex-shrink: 0; }}
.bk-sc-empty {{ min-width: 14px; }}
.bk-sep      {{ height: 1px; background: #E6DDD0; margin: 0 6px; }}

/* winner/loser row styling */
.bk-win          {{ background: rgba(180,230,180,.25); }}
.bk-win .bk-nm   {{ color: #1A5218; font-weight: 700; }}
.bk-lose         {{ }}
.bk-lose .bk-fl  {{ opacity: .45; }}
.bk-lose .bk-nm  {{ color: #A09080; font-weight: 400; text-decoration: line-through; }}
.bk-lose .bk-sc  {{ color: #A09080; }}

/* ── final column ── */
.bk-final-col {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: {8 * _SH['r32']}px;
    padding: 0 18px;
    gap: 7px;
    overflow: visible;
}}
.bk-trophy     {{ font-size: 2.6rem; line-height: 1; }}
.bk-final-lbl  {{
    font-size: .78rem;
    font-weight: 700;
    letter-spacing: .18em;
    color: #B8883A;
    text-transform: uppercase;
}}
.bk-third-lbl  {{
    font-size: .68rem;
    font-weight: 700;
    letter-spacing: .14em;
    color: #8A7A60;
    text-transform: uppercase;
    margin-top: 18px;
}}
</style>
"""


# ── Public entry point ────────────────────────────────────────────────────────

def render_knockout_bracket_shell() -> None:
    """Render the full knockout bracket shell via st.markdown.

    Phase 6A: all slots are placeholder/empty — no scoring or pick logic.
    """
    data = _placeholder_data()

    bracket = (
        _col_left(data['r32_l'], 'r32')
        + _col_left(data['r16_l'], 'r16')
        + _col_left(data['qf_l'],  'qf')
        + _col_left(data['sf_l'],  'sf')
        + _final_col(data['final'], data['third'])
        + _col_right(data['sf_r'],  'sf')
        + _col_right(data['qf_r'],  'qf')
        + _col_right(data['r16_r'], 'r16')
        + _col_right(data['r32_r'], 'r32')
    )

    labels = (
        '<div class="bk-lbl bk-lbl-rnd">Round of 32</div>'
        '<div class="bk-lbl bk-lbl-rnd">Round of 16</div>'
        '<div class="bk-lbl bk-lbl-rnd">Quarterfinals</div>'
        '<div class="bk-lbl bk-lbl-rnd">Semifinals</div>'
        '<div class="bk-lbl bk-lbl-fin">🏆 Final</div>'
        '<div class="bk-lbl bk-lbl-rnd">Semifinals</div>'
        '<div class="bk-lbl bk-lbl-rnd">Quarterfinals</div>'
        '<div class="bk-lbl bk-lbl-rnd">Round of 16</div>'
        '<div class="bk-lbl bk-lbl-rnd">Round of 32</div>'
    )

    html = f"""
{_css()}
<div id="bk-outer">
  <div id="bk-board">
    <div class="bk-tape bk-tape-tl"></div>
    <div class="bk-tape bk-tape-tr"></div>
    <div class="bk-tape bk-tape-bl"></div>
    <div class="bk-tape bk-tape-br"></div>
    <div class="bk-sticky">Every pick.<br/>Every match.<br/>One champion. 🏆</div>
    <div id="bk-heading">
      <div id="bk-title">🏆 Road to the Final</div>
      <div id="bk-subtitle">2026 FIFA World Cup · Knockout Stage</div>
    </div>
    <div id="bk-labels">{labels}</div>
    <div id="bk-rounds">{bracket}</div>
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)
