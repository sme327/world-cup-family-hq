"""Circular/radial knockout bracket rendered as inline SVG."""
import math
import streamlit as st
from services.ko_picks import get_all_ko_matches_display

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
GOLD        = '#C9A227'
GOLD_DIM    = '#7A6315'
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


def _txt(x, y, content, size, fill, anchor, baseline="central", weight="normal", extra="") -> str:
    return (f'<text x="{_f(x)}" y="{_f(y)}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" dominant-baseline="{baseline}" '
            f'font-weight="{weight}" font-family="system-ui,sans-serif"{extra}>{content}</text>')


# ── Match node helper ─────────────────────────────────────────────────────────

def _match_node(svg: list, angle: float, radius: float, m, r_px: int = 9) -> None:
    x, y = _pt(radius, angle)
    has_w = m and m.get('winner_team_id')
    fill  = NODE_WIN_BG if has_w else NODE_BG
    sk    = GOLD if has_w else GRAY
    sw    = 1.5 if has_w else 0.8
    svg.append(_circ(x, y, r_px, fill, sk, sw))
    if has_w:
        svg.append(_circ(x, y, 3, GOLD, 'none', 0))


# ── Connector helper ──────────────────────────────────────────────────────────

def _conn(svg: list, x1, y1, x2, y2, winner: bool) -> None:
    stroke  = GOLD if winner else GRAY
    width   = 1.8  if winner else 0.7
    opacity = 0.95 if winner else 0.30
    svg.append(_line(x1, y1, x2, y2, stroke, width, opacity))


# ── Main SVG builder ──────────────────────────────────────────────────────────

def _build_svg(ko: list) -> str:
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
        f'style="width:100%;max-width:{SIZE}px;display:block;margin:auto;background:{BG};border-radius:16px">'
    )
    svg.append(f'''<defs>
  <radialGradient id="cg" cx="50%" cy="50%" r="45%">
    <stop offset="0%"   stop-color="{GOLD}" stop-opacity="0.18"/>
    <stop offset="40%"  stop-color="{GOLD}" stop-opacity="0.05"/>
    <stop offset="100%" stop-color="{BG}"   stop-opacity="0"/>
  </radialGradient>
  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur stdDeviation="3" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>''')

    # ── Background ────────────────────────────────────────────────────────────
    svg.append(f'<rect width="{SIZE}" height="{SIZE}" fill="{BG}" rx="16"/>')

    # ── Center glow ───────────────────────────────────────────────────────────
    svg.append(f'<circle cx="{CX}" cy="{CY}" r="200" fill="url(#cg)"/>')

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
        _match_node(svg, _a_r32(s0), R_R32, by_slot['r32'].get(s0 + 1), 8)
    for s0 in range(8):
        _match_node(svg, _a_r16(s0), R_R16, by_slot['r16'].get(s0 + 1), 9)
    for s0 in range(4):
        _match_node(svg, _a_qf(s0),  R_QF,  by_slot['qf'].get(s0 + 1),  10)
    for s0 in range(2):
        _match_node(svg, _a_sf(s0),  R_SF,  by_slot['sf'].get(s0 + 1),  11)

    # ── ROUND LABELS (at 270° = left side) ───────────────────────────────────
    for r, label in [(R_R32, 'R32'), (R_R16, 'R16'), (R_QF, 'QF'), (R_SF, 'SF')]:
        lx, ly = _pt(r, 270)
        svg.append(_txt(lx - 18, ly, label, 7, GRAY_LIGHT, 'middle'))

    # ── OUTER TEAM LABELS ─────────────────────────────────────────────────────
    for i, team in enumerate(outer):
        angle = _a_team(i)
        fx, fy = _pt(R_TEAM, angle)
        cx2, cy2 = _pt(R_CODE, angle)
        anchor = _text_anchor(angle)

        if team and team.get('name'):
            flag = team['flag']
            code = _short(team['name'])
            svg.append(_txt(fx, fy, flag, 28, 'inherit', 'middle'))
            svg.append(_txt(cx2, cy2, code, 6.5, TXT, anchor))
        else:
            svg.append(_circ(fx, fy, 3, GRAY, 'none', 0))

    # ── CENTER: trophy or champion ────────────────────────────────────────────
    final_m     = by_slot['final'].get(1)
    champ_name  = final_m.get('winner_name') if final_m else None
    champ_flag  = None

    # Extra glow ring around the center focal point
    svg.append(f'<circle cx="{CX}" cy="{CY}" r="54" fill="none" stroke="{GOLD}" '
               f'stroke-width="1" opacity="0.25"/>')

    if champ_name:
        for t in outer:
            if t and t.get('name') == champ_name:
                champ_flag = t.get('flag')
                break
        svg.append(_txt(CX, CY - 32, '🏆', 52, 'inherit', 'middle'))
        if champ_flag:
            svg.append(_txt(CX, CY + 12, champ_flag, 36, 'inherit', 'middle'))
        code = _short(champ_name)
        svg.append(_txt(CX, CY + 46, code, 11, TXT_WIN, 'middle', weight='bold'))
    else:
        svg.append(_txt(CX, CY + 16, '🏆', 72, 'inherit', 'middle'))

    svg.append('</svg>')
    return '\n'.join(svg)


# ── Public entry point ────────────────────────────────────────────────────────

def render_radial_bracket() -> None:
    """Render the circular knockout bracket inside Streamlit."""
    try:
        ko = get_all_ko_matches_display()
    except Exception:
        st.caption("Bracket data unavailable.")
        return

    svg = _build_svg(ko)

    # Wrap in a div that allows horizontal scroll on small screens
    html = f"""
<div style="width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;padding:4px 0">
  <div style="min-width:480px;max-width:{SIZE}px;margin:0 auto">
    {svg}
    <div style="text-align:center;margin-top:.75rem;padding:.5rem 0">
      <div style="font-size:1.35rem;font-weight:900;color:#C9A227;letter-spacing:.12em;
                  text-transform:uppercase;font-family:'Georgia',serif">
        2026 FIFA World Cup
      </div>
      <div style="font-size:1rem;color:#6B7280;letter-spacing:.08em;
                  text-transform:uppercase;margin-top:.2rem">
        Knockout Bracket
      </div>
    </div>
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)
