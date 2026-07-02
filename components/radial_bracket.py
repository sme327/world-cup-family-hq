"""Circular/radial knockout bracket rendered as inline SVG."""
import base64
import math
import os
from datetime import datetime as _dt
import streamlit as st
from services.ko_picks import get_all_ko_matches_display

_ASSETS = os.path.join(os.path.dirname(__file__), '..', 'assets')

def _trophy_data_uri() -> str | None:
    path = os.path.join(_ASSETS, 'trophy_bracket.png')
    try:
        with open(path, 'rb') as fh:
            return 'data:image/png;base64,' + base64.b64encode(fh.read()).decode()
    except Exception:
        return None

# ── Layout ────────────────────────────────────────────────────────────────────
SIZE  = 900
CX = CY = SIZE // 2
N     = 32          # outer team positions
STEP  = 360.0 / N  # 11.25° per position

R_TEAM = 416        # flag emoji radius
R_CODE = 442        # short-code text radius
R_R32  = 353        # R32 match node radius
R_R16  = 266        # R16 match node radius
R_QF   = 179        # QF  match node radius
R_SF   = 96         # SF  match node radius

# ── Palette ───────────────────────────────────────────────────────────────────
BG          = '#111827'
GRAY        = '#374151'
GRAY_LIGHT  = '#4B5563'
GOLD        = '#D2981C'   # sampled from trophy PNG
GOLD_DIM    = '#694C0E'
TXT         = '#6B7280'
TXT_WIN     = '#FCD34D'
NODE_BG     = '#1A2235'
NODE_WIN_BG = '#2A1C00'

# ── 3-letter codes ────────────────────────────────────────────────────────────
_SHORT = {
    'Germany':'GER','Paraguay':'PAR','Norway':'NOR','Sweden':'SWE',
    'South Korea':'KOR','Switzerland':'SUI','Netherlands':'NED','Morocco':'MAR',
    'DR Congo':'COD','Ghana':'GHA','Saudi Arabia':'KSA','Austria':'AUT',
    'USA':'USA','Bosnia and Herzegovina':'BIH','Iran':'IRN','Senegal':'SEN',
    'Brazil':'BRA','Japan':'JPN','Ivory Coast':'CIV','France':'FRA',
    'Mexico':'MEX','Ecuador':'ECU','England':'ENG','Portugal':'POR',
    'Argentina':'ARG','Uruguay':'URU','Australia':'AUS','New Zealand':'NZL',
    'Canada':'CAN','Jordan':'JOR','Colombia':'COL','Panama':'PAN',
}


def _short(name: str) -> str:
    return _SHORT.get(name, name[:3].upper() if name else '---')


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _pt(r: float, deg: float) -> tuple[float, float]:
    """Polar → SVG XY. 0° = top, clockwise."""
    rad = math.radians(deg - 90)
    return CX + r * math.cos(rad), CY + r * math.sin(rad)


def _f(v: float) -> str:
    return f"{v:.1f}"


def _a_team(i: int) -> float:
    return i * STEP

def _a_r32(s0: int) -> float:
    return (2 * s0 + 0.5) * STEP

def _a_r16(s0: int) -> float:
    return (_a_r32(2 * s0) + _a_r32(2 * s0 + 1)) / 2

def _a_qf(s0: int) -> float:
    return (_a_r16(2 * s0) + _a_r16(2 * s0 + 1)) / 2

def _a_sf(s0: int) -> float:
    return (_a_qf(2 * s0) + _a_qf(2 * s0 + 1)) / 2


def _text_anchor(angle: float) -> str:
    a = angle % 360
    if 25 < a < 155:  return "start"
    if 205 < a < 335: return "end"
    return "middle"


# ── SVG element builders ──────────────────────────────────────────────────────

def _line(x1, y1, x2, y2, stroke, width, opacity) -> str:
    return (f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" '
            f'stroke="{stroke}" stroke-width="{width}" opacity="{opacity:.2f}"/>')


def _circ(x, y, r, fill, stroke, sw) -> str:
    return (f'<circle cx="{_f(x)}" cy="{_f(y)}" r="{r}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>')


def _txt(x, y, content, size, fill, anchor, baseline="central", weight="normal", extra="", tooltip="") -> str:
    title = f'<title>{tooltip}</title>' if tooltip else ''
    return (f'<text x="{_f(x)}" y="{_f(y)}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" dominant-baseline="{baseline}" '
            f'font-weight="{weight}" font-family="system-ui,sans-serif"{extra}>{title}{content}</text>')


# ── Match node helper ─────────────────────────────────────────────────────────

def _match_node(svg: list, angle: float, radius: float, m, r_px: int = 9, rnd: str = '', uid: str = '') -> None:
    x, y  = _pt(radius, angle)
    has_w = m and m.get('winner_team_id')
    is_scheduled = m and not has_w and m.get('status', 'scheduled') == 'scheduled'
    illuminate = is_scheduled and rnd == 'r32'   # glow only for unplayed R32

    # Linkable if the match exists and has at least one team assigned
    match_id  = m.get('id') if m else None
    has_teams = m and (m.get('home_name') or m.get('away_name'))
    u_param   = f'&u={uid}' if uid else ''
    link_open  = f'<a href="/matchup?match_id={match_id}{u_param}" target="_parent" style="cursor:pointer">' if (match_id and has_teams) else ''
    link_close = '</a>' if link_open else ''

    # Build node tooltip
    def _fmt_when(date_str, et_time) -> str:
        """'Jul 5 · 3 PM PT' from match_date + kickoff_time_et."""
        try:
            d = _dt.strptime(str(date_str), '%Y-%m-%d')
            if et_time:
                pt = d.replace(hour=int(et_time[:2]), minute=int(et_time[3:5]))
                from datetime import timedelta as _td
                pt = pt - _td(hours=3)
                ap = 'AM' if pt.hour < 12 else 'PM'
                h  = pt.hour % 12 or 12
                t  = f"{h}:{pt.minute:02d} {ap}" if pt.minute else f"{h} {ap}"
                return f"{d.strftime('%b')} {d.day} · {t} PT"
            return f"{d.strftime('%b')} {d.day}"
        except Exception:
            return ''

    if has_w:
        _hn = m.get('home_name', '?')
        _an = m.get('away_name', '?')
        _hs = m.get('home_score')
        _as = m.get('away_score')
        _wn = m.get('winner_name', '')
        _sc = f"{int(_hs)}–{int(_as)}" if _hs is not None and _as is not None else ''
        # PK: tied score with a declared winner (don't rely on pens_str — may be blank)
        _is_pk = bool(_hs is not None and _as is not None
                      and int(_hs) == int(_as) and _wn)
        if _is_pk:
            _tip = f"{_hn} {_sc} {_an} · {_wn} advances on PKs"
        else:
            _tip = f"{_hn} {_sc} {_an}" + (f" · {_wn} advances" if _wn else '')
    elif m:
        # Unplayed — date + time + city for every round
        _hn   = m.get('home_name') or ''
        _an   = m.get('away_name') or ''
        _when = _fmt_when(m.get('match_date', ''), m.get('kickoff_time_et', ''))
        _city = m.get('city', '')
        _loc  = f" · {_city}" if _city else ''
        if _hn and _an:
            _tip = f"{_hn} vs {_an} · {_when}{_loc}"
        else:
            _tip = f"{_when}{_loc}"
    else:
        _tip = ''

    svg.append(f'<g{">" if not _tip else f"><title>{_tip}</title>"}')

    if link_open:
        svg.append(link_open)

    # Larger invisible hit-target so small nodes are easy to tap
    svg.append(_circ(x, y, max(r_px + 6, 14), 'transparent', 'none', 0))

    if has_w:
        # Completed match — warm gold dome, no glow, just depth
        svg.append(_circ(x + 0.6, y + 1.0, r_px, '#000000', 'none', 0).replace('/>', ' opacity="0.50"/>'))
        svg.append(_circ(x, y, r_px, 'url(#peg-gold)', GOLD_DIM, 1.0))
        hx, hy = x - r_px * 0.27, y - r_px * 0.30
        svg.append(_circ(hx, hy, max(1.2, r_px * 0.28), '#FFFFFF', 'none', 0).replace('/>', ' opacity="0.20"/>'))
        svg.append(_circ(x, y, 2.2, GOLD, 'none', 0))

    elif illuminate:
        # Unplayed R32 — full illuminated peg: halo + glow ring + dome + highlight
        svg.append(
            f'<circle cx="{_f(x)}" cy="{_f(y)}" r="{r_px * 1.9}" '
            f'fill="#4A7AB5" filter="url(#peg-halo)" opacity="0.30"/>'
        )
        svg.append(_circ(x, y, r_px * 1.45, '#4A7AB5', 'none', 0).replace('/>', ' opacity="0.12"/>'))
        svg.append(_circ(x + 0.7, y + 1.1, r_px, '#000000', 'none', 0).replace('/>', ' opacity="0.60"/>'))
        svg.append(_circ(x, y, r_px, 'url(#peg-gray)', GRAY, 0.9))
        hx, hy = x - r_px * 0.27, y - r_px * 0.30
        svg.append(_circ(hx, hy, max(1.4, r_px * 0.30), '#FFFFFF', 'none', 0).replace('/>', ' opacity="0.30"/>'))

    else:
        # Future round or TBD — recede into background
        svg.append(_circ(x, y, r_px * 0.85, GRAY, 'none', 0).replace('/>', f' opacity="0.20"/>'))

    if link_close:
        svg.append(link_close)

    svg.append('</g>')


# ── Connector helper ──────────────────────────────────────────────────────────

def _conn(svg: list, x1, y1, x2, y2, winner: bool) -> None:
    stroke  = GOLD if winner else GRAY
    width   = 1.8  if winner else 0.7
    opacity = 0.95 if winner else 0.30
    svg.append(_line(x1, y1, x2, y2, stroke, width, opacity))


# ── Main SVG builder ──────────────────────────────────────────────────────────

def _build_svg(ko: list, uid: str = '') -> str:
    trophy_uri = _trophy_data_uri()

    # Index by round → bracket_slot
    by_slot: dict = {rnd: {} for rnd in ('r32', 'r16', 'qf', 'sf', 'final', 'third_place')}
    for m in ko:
        rnd  = m.get('round', '')
        slot = m.get('bracket_slot')
        if rnd in by_slot and slot is not None:
            by_slot[rnd][slot] = m

    # Build 32 outer team slots from R32 home/away
    # R32 slot s (1-indexed) → home at outer[2(s-1)], away at outer[2(s-1)+1]
    outer = [None] * 32
    for s1 in range(1, 17):
        m = by_slot['r32'].get(s1)
        if m:
            i = 2 * (s1 - 1)
            outer[i]     = {'name': m.get('home_name'), 'flag': m.get('home_flag') or '⬜', 'tid': m.get('home_team_id')}
            outer[i + 1] = {'name': m.get('away_name'), 'flag': m.get('away_flag') or '⬜', 'tid': m.get('away_team_id')}

    svg = []

    # ── SVG header + defs ─────────────────────────────────────────────────────
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {SIZE} {SIZE}" '
        f'style="width:100%;max-width:{SIZE}px;display:block;margin:auto;background:transparent">'
    )
    svg.append(f'''<defs>
  <!-- Center glow: tight inner warmth + wide atmospheric spill -->
  <radialGradient id="cg-inner" cx="50%" cy="50%" r="50%">
    <stop offset="0%"   stop-color="{GOLD}" stop-opacity="0.32"/>
    <stop offset="40%"  stop-color="{GOLD}" stop-opacity="0.10"/>
    <stop offset="100%" stop-color="{GOLD}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="cg-outer" cx="50%" cy="50%" r="50%">
    <stop offset="0%"   stop-color="{GOLD}" stop-opacity="0.10"/>
    <stop offset="50%"  stop-color="{GOLD}" stop-opacity="0.03"/>
    <stop offset="100%" stop-color="{GOLD}" stop-opacity="0"/>
  </radialGradient>
  <!-- Peg body gradients: off-centre highlight → deep shadow gives 3-D dome -->
  <radialGradient id="peg-gray" cx="32%" cy="28%" r="72%">
    <stop offset="0%"   stop-color="#3D5475"/>
    <stop offset="55%"  stop-color="#1C2B42"/>
    <stop offset="100%" stop-color="#0A1018"/>
  </radialGradient>
  <radialGradient id="peg-gold" cx="32%" cy="28%" r="72%">
    <stop offset="0%"   stop-color="#7A5200"/>
    <stop offset="55%"  stop-color="#3E2A00"/>
    <stop offset="100%" stop-color="#180E00"/>
  </radialGradient>
  <!-- Halo glow for illuminated pegs -->
  <filter id="peg-halo" x="-120%" y="-120%" width="340%" height="340%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="3.5" result="blur"/>
  </filter>
  <!-- Flag float: tiny drop shadow gives pinned-to-board depth -->
  <filter id="flag-float" x="-15%" y="-15%" width="130%" height="130%">
    <feDropShadow dx="0" dy="1.5" stdDeviation="1.8"
                  flood-color="#000000" flood-opacity="0.55"/>
  </filter>
  <!-- Trophy image clip paths -->
  <clipPath id="tc-lg">
    <circle cx="{CX}" cy="{CY}" r="100"/>
  </clipPath>
  <clipPath id="tc-sm">
    <circle cx="{CX}" cy="{CY - 22}" r="52"/>
  </clipPath>
</defs>''')

    # ── Background ────────────────────────────────────────────────────────────
    # No background rect — SVG is transparent so it inherits the page color seamlessly

    # ── Center glow: tight warmth + wide atmospheric spill ───────────────────
    svg.append(f'<circle cx="{CX}" cy="{CY}" r="340" fill="url(#cg-outer)"/>')
    svg.append(f'<circle cx="{CX}" cy="{CY}" r="170" fill="url(#cg-inner)"/>')

    # ── Subtle ring guides ────────────────────────────────────────────────────
    for r in (R_R32, R_R16, R_QF, R_SF):
        svg.append(f'<circle cx="{CX}" cy="{CY}" r="{r}" fill="none" stroke="{GRAY}" '
                   f'stroke-width="0.5" stroke-dasharray="3 9" opacity="0.20"/>')

    # ── Outer team ring (faint) ───────────────────────────────────────────────
    svg.append(f'<circle cx="{CX}" cy="{CY}" r="{R_TEAM - 8}" fill="none" stroke="{GRAY}" '
               f'stroke-width="0.4" stroke-dasharray="1 10" opacity="0.15"/>')

    # ── CONNECTORS (drawn before nodes so nodes sit on top) ───────────────────

    # Team → R32
    for s0 in range(16):
        s1   = s0 + 1
        r32m = by_slot['r32'].get(s1)
        for ti in range(2):
            team = outer[2 * s0 + ti]
            t_ang = _a_team(2 * s0 + ti)
            r_ang = _a_r32(s0)
            tx, ty = _pt(R_TEAM - 14, t_ang)
            rx, ry = _pt(R_R32 + 10, r_ang)
            winner = bool(
                team and r32m and
                r32m.get('winner_team_id') and
                r32m.get('winner_team_id') == team.get('tid')
            )
            _conn(svg, tx, ty, rx, ry, winner)

    # R32 → R16
    for r16_s0 in range(8):
        r16m = by_slot['r16'].get(r16_s0 + 1)
        for off in range(2):
            r32_s0 = 2 * r16_s0 + off
            r32m   = by_slot['r32'].get(r32_s0 + 1)
            winner = bool(r32m and r32m.get('winner_team_id'))
            x1, y1 = _pt(R_R32 - 10, _a_r32(r32_s0))
            x2, y2 = _pt(R_R16 + 10, _a_r16(r16_s0))
            _conn(svg, x1, y1, x2, y2, winner)

    # R16 → QF
    for qf_s0 in range(4):
        for off in range(2):
            r16_s0 = 2 * qf_s0 + off
            r16m   = by_slot['r16'].get(r16_s0 + 1)
            winner = bool(r16m and r16m.get('winner_team_id'))
            x1, y1 = _pt(R_R16 - 10, _a_r16(r16_s0))
            x2, y2 = _pt(R_QF + 10, _a_qf(qf_s0))
            _conn(svg, x1, y1, x2, y2, winner)

    # QF → SF
    for sf_s0 in range(2):
        for off in range(2):
            qf_s0  = 2 * sf_s0 + off
            qfm    = by_slot['qf'].get(qf_s0 + 1)
            winner = bool(qfm and qfm.get('winner_team_id'))
            x1, y1 = _pt(R_QF - 10, _a_qf(qf_s0))
            x2, y2 = _pt(R_SF + 10, _a_sf(sf_s0))
            _conn(svg, x1, y1, x2, y2, winner)

    # SF → center
    for sf_s0 in range(2):
        sfm    = by_slot['sf'].get(sf_s0 + 1)
        winner = bool(sfm and sfm.get('winner_team_id'))
        x1, y1 = _pt(R_SF - 12, _a_sf(sf_s0))
        _conn(svg, x1, y1, CX, CY, winner)

    # ── MATCH NODES ───────────────────────────────────────────────────────────
    for s0 in range(16):
        _match_node(svg, _a_r32(s0), R_R32, by_slot['r32'].get(s0 + 1), 8,  'r32', uid)
    for s0 in range(8):
        _match_node(svg, _a_r16(s0), R_R16, by_slot['r16'].get(s0 + 1), 9,  'r16', uid)
    for s0 in range(4):
        _match_node(svg, _a_qf(s0),  R_QF,  by_slot['qf'].get(s0 + 1),  10, 'qf',  uid)
    for s0 in range(2):
        _match_node(svg, _a_sf(s0),  R_SF,  by_slot['sf'].get(s0 + 1),  11, 'sf',  uid)

    # ── OUTER TEAM FLAGS ──────────────────────────────────────────────────────
    for i, team in enumerate(outer):
        angle = _a_team(i)
        fx, fy = _pt(R_TEAM, angle)

        if team and team.get('name'):
            svg.append(_txt(fx, fy, team['flag'], 48, 'inherit', 'middle',
                            extra=' filter="url(#flag-float)"', tooltip=team['name']))
        else:
            svg.append(_circ(fx, fy, 3, GRAY, 'none', 0))

    # ── CENTER: trophy or champion ────────────────────────────────────────────
    final_m    = by_slot['final'].get(1)
    champ_name = final_m.get('winner_name') if final_m else None
    champ_flag = None

    if champ_name:
        for t in outer:
            if t and t.get('name') == champ_name:
                champ_flag = t.get('flag')
                break
        # Smaller trophy above, champion flag + name below
        if trophy_uri:
            svg.append(f'<image href="{trophy_uri}" x="{CX-52}" y="{CY-84}" '
                       f'width="104" height="104" clip-path="url(#tc-sm)"/>')
        else:
            svg.append(_txt(CX, CY - 28, '🏆', 48, 'inherit', 'middle'))
        if champ_flag:
            svg.append(_txt(CX, CY + 16, champ_flag, 32, 'inherit', 'middle'))
        svg.append(_txt(CX, CY + 44, _short(champ_name), 11, TXT_WIN, 'middle', weight='bold'))
    else:
        # No champion yet — full trophy centred
        if trophy_uri:
            svg.append(f'<image href="{trophy_uri}" x="{CX-100}" y="{CY-100}" '
                       f'width="200" height="200" clip-path="url(#tc-lg)"/>')
        else:
            svg.append(_txt(CX, CY + 16, '🏆', 72, 'inherit', 'middle'))

    svg.append('</svg>')
    return '\n'.join(svg)


# ── Public entry point ────────────────────────────────────────────────────────

def render_radial_bracket(show_title: bool = True) -> None:
    """Render the circular knockout bracket inside Streamlit."""
    import streamlit.components.v1 as _components
    try:
        ko = get_all_ko_matches_display()
    except Exception:
        st.caption("Bracket data unavailable.")
        return

    uid  = str(st.session_state.get("active_user_id", ""))
    svg  = _build_svg(ko, uid)
    title_html = (
        "<div style='text-align:center;padding:.75rem 0 .5rem'>"
        "<div style='font-size:1.5rem;font-weight:900;color:#D2981C;letter-spacing:.12em;"
        "text-transform:uppercase;font-family:Georgia,serif'>2026 FIFA World Cup</div>"
        "</div>"
    ) if show_title else ""

    # Use components.html (iframe) so the SVG is not sanitized by Streamlit's
    # markdown renderer. Links use target="_parent" to navigate the outer window.
    html = f"""<!DOCTYPE html>
<html><head><style>
  html,body{{margin:0;padding:0;background:transparent;overflow:hidden}}
</style></head>
<body>
<div style="width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;padding:2px 0">
  <div style="min-width:480px;max-width:{SIZE}px;margin:0 auto">
    {title_html}
    {svg}
  </div>
</div>
</body></html>"""
    height = SIZE + (60 if show_title else 10)
    _components.html(html, height=height, scrolling=False)
