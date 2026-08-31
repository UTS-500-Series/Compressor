#!/usr/bin/env python3
"""Front panel for the OPN-500 / CMP-01 compressor.

Emits three files from one definition, so the mockup and the machining data cannot drift:

    faceplate-mockup.svg    how it looks - finish, knobs, silkscreen, lit meters
    faceplate-drawing.svg   1:1 technical drawing, dimensioned
    faceplate.dxf           outline and holes only, for a panel shop or CNC

Geometry is the API 500 mechanical spec: 1.500 x 5.250 x 0.125 inch, two 0.125 inch
mounting holes on the vertical centreline 4.938 inch apart, countersunk 82 degrees.

Run: python3 make_panel.py
"""
import math, os

# ---------------------------------------------------------------- panel (mm)
W, H, THK  = 38.10, 133.35, 3.18
CL         = W / 2
HOLE_D     = 3.18
CSINK_D    = 5.72
HOLE_PITCH = 125.43
HOLE_Y     = [(H - HOLE_PITCH) / 2, (H - HOLE_PITCH) / 2 + HOLE_PITCH]

# ---------------------------------------------------------------- hardware
BUSH_CONC = 9.5      # dual-concentric pot, 3/8" bushing
BUSH_POT  = 7.0      # 9 mm pot
BUSH_TOG  = 6.0      # mini toggle
BUSH_BTN  = 8.0      # illuminated latching pushbutton
LED_HOLE  = 2.2      # 2 mm meter LED
KNOB_OUT  = 15.0     # concentric outer skirt
KNOB_IN   = 8.5      # concentric inner cap
KNOB_SGL  = 12.0

# ---------------------------------------------------------------- controls
# Two dual-concentric pots carry the four controls that pair naturally, which is what
# buys the room for the meters, the bypass button and two toggles. MAKEUP keeps a pull
# switch for LINK - it is the one function you set per pair and then leave.
CONCENTRIC = [
    # outer label, outer ref, inner label, inner ref, x, y
    ('THRESHOLD', 'RV3', 'RATIO',   'RV4', CL, 56.0),
    ('ATTACK',    'RV5', 'RELEASE', 'RV6', CL, 79.0),
]
SINGLES = [
    # ref, label, pull legend, x, y, knob dia, hole dia
    ('RV2', 'MAKEUP', 'PULL LINK', CL, 106.0, KNOB_SGL, BUSH_POT),
]
# BYPASS is a latching button legended on its own face - there is no room for a legend
# beside it, and the bottom screw owns the centreline down there.
BUTTONS = [
    ('SW1', 'BYP', 8.5, 126.0, BUSH_BTN),
]
# the two sidechain toggles flank MAKEUP rather than fighting the bottom screw
TOGGLES = [
    ('SW3', 'HPF', 5.6,  105.0, BUSH_TOG),
    ('SW2', 'KEY', 32.5, 105.0, BUSH_TOG),
]

METER_PITCH, METER_TOP, METER_N = 3.5, 14.0, 7
METERS = [('GR', 'D20', 13.6, 'gr'), ('LVL', 'D30', 24.5, 'lvl')]

def meter_leds():
    out = []
    for label, base, x, kind in METERS:
        for i in range(METER_N):
            out.append(('%s%d' % (base, i + 1), label, x,
                        METER_TOP + i * METER_PITCH, kind, i))
    return out

# ---------------------------------------------------------------- palette
# Warm bone panel with sage and terracotta, flat rather than metallic. A light panel
# in a rack of black modules is the whole point - it should not look like everything
# else in the frame.
BONE    = '#E9E3D6'
BONE_HI = '#F2EDE3'
INK     = '#2B2F2A'
MUTED   = '#8A8D80'
SAGE    = '#7F9B7E'
SAGE_LT = '#B9C9B4'
TERRA   = '#C4785A'
DARKSET = '#22262A'
KNOB    = '#2E332E'
CREAM   = '#DCD3C0'


def all_holes():
    """(ref, x, y, dia) for everything that gets drilled."""
    h  = [(o_ref, x, y, BUSH_CONC) for ol, o_ref, il, i_ref, x, y in CONCENTRIC]
    h += [(r, x, y, hd) for r, l, p, x, y, kd, hd in SINGLES]
    h += [(r, x, y, d) for r, l, x, y, d in BUTTONS]
    h += [(r, x, y, d) for r, l, x, y, d in TOGGLES]
    h += [(r, x, y, LED_HOLE) for r, l, x, y, k, i in meter_leds()]
    h += [('MTG%d' % (i + 1), CL, hy, HOLE_D) for i, hy in enumerate(HOLE_Y)]
    return h


def visuals():
    """(x, y, radius) of everything a finger touches, for skirt clearance."""
    v  = [(x, y, KNOB_OUT / 2) for ol, orf, il, irf, x, y in CONCENTRIC]
    v += [(x, y, kd / 2) for r, l, p, x, y, kd, hd in SINGLES]
    v += [(x, y, d / 2 + 1.0) for r, l, x, y, d in BUTTONS]
    v += [(x, y, d / 2) for r, l, x, y, d in TOGGLES]
    return v


def clearance_report():
    issues, holes = [], all_holes()
    for ref, x, y, d in holes:
        r = d / 2
        if x - r < 2.0 or x + r > W - 2.0:
            issues.append('%s too close to a side edge' % ref)
        if y - r < 2.0 or y + r > H - 2.0:
            issues.append('%s too close to an end' % ref)
    for i, a in enumerate(holes):
        for b in holes[i + 1:]:
            dist = math.hypot(a[1] - b[1], a[2] - b[2])
            need = a[3] / 2 + b[3] / 2 + 1.0
            if dist < need:
                issues.append('%s and %s only %.2f mm apart, need %.2f'
                              % (a[0], b[0], dist, need))
    for x, y, r in visuals():                       # knobs and caps must clear the screws
        for hy in HOLE_Y:
            dist = math.hypot(x - CL, y - hy)
            if dist < r + CSINK_D / 2 + 0.5:
                issues.append('a control at (%.1f, %.1f) fouls the mounting hole at y=%.2f'
                              % (x, y, hy))
    vs = visuals()
    for i, a in enumerate(vs):
        for b in vs[i + 1:]:
            dist = math.hypot(a[0] - b[0], a[1] - b[1])
            if dist < a[2] + b[2] + 1.5:
                issues.append('controls at (%.1f, %.1f) and (%.1f, %.1f) only %.2f mm apart'
                              % (a[0], a[1], b[0], b[1], dist))
    return issues


# ---------------------------------------------------------------- mockup
def _arc(cx, cy, r, a0, a1):
    """SVG arc path between two angles in degrees, drawn clockwise."""
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return 'M %.2f %.2f A %.2f %.2f 0 %d 1 %.2f %.2f' % (x0, y0, r, r, large, x1, y1)


def _numbers(cx, cy, r, marks, a0=135, sweep=270, size=1.55):
    """Printed numerals outside the dot scale.

    Nothing is placed at 12 o'clock: on a panel this tight the top of one knob's scale
    lands in the label of the control above it. Ends and quarters only.

    Only the outer of a concentric pair can carry a scale - there is nowhere to print one
    for the inner shaft, so RATIO and RELEASE are unnumbered."""
    out = []
    for frac, txt in marks:
        a = math.radians(a0 + frac * sweep)
        out.append('<text x="%.2f" y="%.2f" text-anchor="middle" '
                   'font-family="Helvetica Neue,Helvetica,Arial,sans-serif" font-size="%.2f" '
                   'font-weight="500" fill="%s" fill-opacity="0.75">%s</text>'
                   % (cx + r * math.cos(a), cy + r * math.sin(a) + size * 0.35, size,
                      MUTED, txt))
    return out


def _scale(cx, cy, r, n=11, a0=135, sweep=270, col=None, dot=0.30):
    """Printed dot scale round a knob. Dots read cleaner than ticks at this size, and
    they are what gives the panel its software-UI feel while staying printable."""
    out = []
    for i in range(n):
        a = math.radians(a0 + i * sweep / (n - 1))
        big = i in (0, (n - 1) // 2, n - 1)
        out.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" fill-opacity="%.2f"/>'
                   % (cx + r * math.cos(a), cy + r * math.sin(a),
                      dot * (1.5 if big else 1.0), col or MUTED, 0.9 if big else 0.55))
    return out


def _flatknob(x, y, r, face, pointer, pdeg):
    """Flat disc, single bright pointer, soft contact shadow. No metal, no knurling."""
    o = ['<path d="%s" fill="none" stroke="%s" stroke-width="0.42" stroke-linecap="round" '
         'stroke-opacity="0.8"/>' % (_arc(x, y, r + 3.0, 135, 45), SAGE_LT),
         '<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" fill-opacity="0.13"/>'
         % (x, y + 0.35, r, INK),
         '<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s"/>' % (x, y, r, face)]
    a = math.radians(pdeg)
    o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.85" '
             'stroke-linecap="round"/>'
             % (x + r * 0.34 * math.cos(a), y + r * 0.34 * math.sin(a),
                x + (r - 1.15) * math.cos(a), y + (r - 1.15) * math.sin(a), pointer))
    return o


def _label(x, y, txt, size=2.4, col=None, track=0.55, anchor='middle', weight='500'):
    return ('<text x="%.2f" y="%.2f" text-anchor="%s" font-family="Helvetica Neue,Helvetica,'
            'Arial,sans-serif" font-size="%.2f" font-weight="%s" letter-spacing="%.2f" '
            'fill="%s">%s</text>' % (x, y, anchor, size, weight, track, col or INK, txt))


DEFS = (
 '<defs>'
 '<linearGradient id="pan" x1="0" y1="0" x2="0.35" y2="1">'
 '<stop offset="0" stop-color="%s"/><stop offset="0.55" stop-color="%s"/>'
 '<stop offset="1" stop-color="#E2DBCC"/></linearGradient>'
 '<linearGradient id="set" x1="0" y1="0" x2="0" y2="1">'
 '<stop offset="0" stop-color="#262B30"/><stop offset="1" stop-color="#1A1E22"/>'
 '</linearGradient>'
 '<linearGradient id="bat" x1="0" y1="0" x2="1" y2="0">'
 '<stop offset="0" stop-color="#8C887C"/><stop offset="0.38" stop-color="#E6E2D6"/>'
 '<stop offset="0.62" stop-color="#C8C3B6"/><stop offset="1" stop-color="#7E7A6F"/>'
 '</linearGradient></defs>')


def mockup():
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
         'viewBox="0 0 %.2f %.2f">' % (W, H, W, H), DEFS % (BONE_HI, BONE)]
    o.append('<rect width="%.2f" height="%.2f" rx="1.4" fill="url(#pan)"/>' % (W, H))
    o.append('<rect x="2.2" y="2.2" width="%.2f" height="%.2f" rx="1.0" fill="none" '
             'stroke="%s" stroke-width="0.22" stroke-opacity="0.5"/>' % (W - 4.4, H - 4.4, SAGE))

    o.append(_label(4.4, 8.4, 'OPN-500', 2.1, MUTED, 0.62, 'start', '600'))
    o.append(_label(W - 4.4, 8.4, 'CMP-01', 2.1, MUTED, 0.62, 'end', '600'))

    # meters sit in a dark inset - LEDs need something to read against on a light panel
    wx, wy, ww, wh = 5.0, 11.4, W - 10.0, 31.6
    o.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="1.6" fill="url(#set)"/>'
             % (wx, wy, ww, wh))
    lit = {'gr': 3, 'lvl': 5}
    for ref, label, x, y, kind, i in meter_leds():
        if kind == 'gr':
            base, on = TERRA, i < lit['gr']
        else:
            n = METER_N - 1 - i
            base = TERRA if n >= 6 else ('#D9A85C' if n >= 4 else SAGE)
            on = n < lit['lvl']
        o.append('<rect x="%.2f" y="%.2f" width="3.4" height="1.5" rx="0.75" fill="%s" '
                 'fill-opacity="%.2f"/>'
                 % (x - 1.7, y - 0.75, base if on else '#FFFFFF', 1.0 if on else 0.09))
        if on:
            o.append('<rect x="%.2f" y="%.2f" width="5.0" height="3.1" rx="1.4" fill="%s" '
                     'fill-opacity="0.18"/>' % (x - 2.5, y - 1.55, base))
    for label, base, x, kind in METERS:
        o.append(_label(x, METER_TOP + (METER_N - 1) * METER_PITCH + 3.9, label,
                        1.85, '#9AA29B', 0.7))

    def rule(y, text):
        o.append(_label(CL, y, text, 1.75, SAGE, 1.35, 'middle', '600'))
        o.append('<line x1="4.4" y1="%.2f" x2="12.2" y2="%.2f" stroke="%s" stroke-width="0.2" '
                 'stroke-opacity="0.42"/>' % (y - 0.6, y - 0.6, SAGE))
        o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="0.2" '
                 'stroke-opacity="0.42"/>' % (W - 12.2, y - 0.6, W - 4.4, y - 0.6, SAGE))

    # The DYNAMICS / OUTPUT section rules used to sit here. The numbered scales need that
    # room, and a legend you read beats a divider you do not - so they are gone.

    for ol, orf, il, irf, x, y in CONCENTRIC:
        R, r = KNOB_OUT / 2, KNOB_IN / 2
        o += _scale(x, y, R + 3.0)
        o += _numbers(x, y, R + 5.7, [(0.0, '0'), (0.25, '2'), (0.75, '8'), (1.0, '10')])
        o += _flatknob(x, y, R, KNOB, SAGE_LT, 205)
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="#000" fill-opacity="0.18"/>'
                 % (x, y + 0.3, r))
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s"/>' % (x, y, r, CREAM))
        a = math.radians(335)
        o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                 'stroke-width="0.75" stroke-linecap="round"/>'
                 % (x + r * 0.30 * math.cos(a), y + r * 0.30 * math.sin(a),
                    x + (r - 0.9) * math.cos(a), y + (r - 0.9) * math.sin(a), TERRA))
        o.append(_label(x, y + R + 5.0, ol, 2.45, INK, 0.62, 'middle', '600'))
        o.append(_label(x, y + R + 7.4, il, 1.85, TERRA, 0.55))

    for ref, label, pull, x, y, kd, hd in SINGLES:
        R = kd / 2
        o += _scale(x, y, R + 3.0)
        # only the endpoints here: the toggles either side leave no room for a full scale
        o += _numbers(x, y, R + 5.0, [(0.0, '0'), (1.0, '10')])
        o += _flatknob(x, y, R, KNOB, SAGE_LT, 205)
        o.append(_label(x, y + R + 5.0, label, 2.45, INK, 0.62, 'middle', '600'))
        if pull:
            o.append(_label(x, y + R + 7.4, pull, 1.7, SAGE, 0.5))

    for ref, label, x, y, d in BUTTONS:
        R = d / 2
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" fill-opacity="0.14"/>'
                 % (x, y + 0.35, R + 1.1, INK))
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="none" stroke="%s" '
                 'stroke-width="0.45" stroke-opacity="0.9"/>' % (x, y, R + 1.1, SAGE))
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s"/>' % (x, y, R, KNOB))
        o.append(_label(x, y + 0.68, label, 1.85, SAGE_LT, 0.35, 'middle', '600'))

    # ---- thin metal bat toggles: hex nut, tapered chrome lever, ball tip
    for ref, label, x, y, d in TOGGLES:
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" fill-opacity="0.13"/>'
                 % (x, y + 0.3, d / 2 + 0.5, INK))
        nut = []
        for k in range(6):                       # hex bushing nut
            a = math.radians(90 + k * 60)
            nut.append('%.2f,%.2f' % (x + (d / 2 + 0.5) * math.cos(a),
                                      y + (d / 2 + 0.5) * math.sin(a)))
        o.append('<polygon points="%s" fill="#B9B4A6" stroke="#8E8A7E" '
                 'stroke-width="0.18"/>' % ' '.join(nut))
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="#6E6A60"/>' % (x, y, d / 2 - 1.1))
        lean = math.radians(-74)                 # flicked up, slightly off vertical
        tipx, tipy = x + 4.4 * math.cos(lean), y + 4.4 * math.sin(lean)
        px, py = -math.sin(lean), math.cos(lean)
        o.append('<polygon points="%.2f,%.2f %.2f,%.2f %.2f,%.2f %.2f,%.2f" fill="url(#bat)"/>'
                 % (x + px * 0.62, y + py * 0.62, x - px * 0.62, y - py * 0.62,
                    tipx - px * 0.40, tipy - py * 0.40, tipx + px * 0.40, tipy + py * 0.40))
        o.append('<circle cx="%.2f" cy="%.2f" r="0.62" fill="url(#bat)"/>' % (tipx, tipy))
        o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#FFFFFF" '
                 'stroke-width="0.16" stroke-opacity="0.55"/>'
                 % (x + px * 0.22, y + py * 0.22, tipx + px * 0.14, tipy + py * 0.14))
        o.append(_label(x, y - d / 2 - 4.4, label, 1.9, INK, 0.5, 'middle', '600'))

    # the one flourish: concentric arcs tucked into the bottom corner
    for i, rr in enumerate((3.4, 5.2, 7.0)):
        o.append('<path d="%s" fill="none" stroke="%s" stroke-width="0.22" '
                 'stroke-opacity="%.2f"/>'
                 % (_arc(W - 3.2, H - 3.2, rr, 180, 270), SAGE, 0.5 - i * 0.13))
    o.append(_label(27.0, 125.5, 'REV A', 1.6, MUTED, 0.5, 'middle', '500'))

    for hy in HOLE_Y:
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" fill-opacity="0.28"/>'
                 % (CL, hy, CSINK_D / 2, INK))
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="#1A1D1A"/>' % (CL, hy, HOLE_D / 2))
    o.append('<rect width="%.2f" height="%.2f" rx="1.4" fill="none" stroke="#C7BFAE" '
             'stroke-width="0.4"/>' % (W, H))
    o.append('</svg>')
    return '\n'.join(o)


# ---------------------------------------------------------------- drawing
def drawing():
    M = 24.0
    ww, hh = W + M * 2, H + M * 2
    ln   = 'stroke="#111" fill="none"'
    thin = 'stroke="#111" stroke-width="0.12" fill="none"'
    dash = 'stroke="#c22" stroke-width="0.12" stroke-dasharray="3 1 0.6 1" fill="none"'
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
         'viewBox="0 0 %.2f %.2f">' % (ww, hh, ww, hh),
         '<rect width="%.2f" height="%.2f" fill="#fff"/>' % (ww, hh),
         '<g transform="translate(%.2f %.2f)">' % (M, M),
         '<rect width="%.2f" height="%.2f" rx="1.2" %s stroke-width="0.35"/>' % (W, H, ln),
         '<line x1="%.2f" y1="-7" x2="%.2f" y2="%.2f" %s/>' % (CL, CL, H + 7, dash)]

    for hy in HOLE_Y:
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" %s stroke-width="0.3"/>'
                 % (CL, hy, HOLE_D / 2, ln))
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" %s/>' % (CL, hy, CSINK_D / 2, thin))
        o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" %s/>'
                 % (CL - 5, hy, CL + 5, hy, dash))

    for ref, x, y, d in all_holes():
        if ref.startswith('MTG'):
            continue
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" %s stroke-width="0.3"/>'
                 % (x, y, d / 2, ln))
        o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" %s/>'
                 % (x - d / 2 - 1.5, y, x + d / 2 + 1.5, y, dash))
        o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" %s/>'
                 % (x, y - d / 2 - 1.5, x, y + d / 2 + 1.5, dash))

    def callout(x, y, r, ref, txt, dy=0.0, force=None):
        left = (x < CL - 0.5) if force is None else force
        tx = x - r - 1.5 if left else x + r + 1.5
        anc = 'end' if left else 'start'
        o.append('<text x="%.2f" y="%.2f" text-anchor="%s" font-family="Helvetica,Arial" '
                 'font-size="2.0" fill="#111">%s</text>' % (tx, y - 0.8 + dy, anc, ref))
        o.append('<text x="%.2f" y="%.2f" text-anchor="%s" font-family="Helvetica,Arial" '
                 'font-size="1.7" fill="#555">%s</text>' % (tx, y + 1.7 + dy, anc, txt))

    for ol, orf, il, irf, x, y in CONCENTRIC:
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" %s stroke-dasharray="1 1"/>'
                 % (x, y, KNOB_OUT / 2, thin))
        callout(x, y, KNOB_OUT / 2, '%s / %s' % (orf, irf),
                '%s + %s &#216;%.1f' % (ol, il, BUSH_CONC))
    for ref, label, pull, x, y, kd, hd in SINGLES:
        o.append('<circle cx="%.2f" cy="%.2f" r="%.2f" %s stroke-dasharray="1 1"/>'
                 % (x, y, kd / 2, thin))
        callout(x, y, kd / 2, ref, '%s &#216;%.1f' % (label, hd))
    # these share rows with a knob, so push the labels clear of it
    for i, (ref, label, x, y, d) in enumerate(TOGGLES):
        callout(x, y, d / 2, ref, '%s &#216;%.1f' % (label, d), dy=-8.0 - i * 5.0)
    for ref, label, x, y, d in BUTTONS:
        callout(x, y, d / 2, ref, '%s &#216;%.1f' % (label, d), dy=-6.0, force=True)
    o.append('<text x="%.2f" y="%.2f" font-family="Helvetica,Arial" font-size="1.6" '
             'fill="#555" text-anchor="middle">2 &#215; %d holes &#216;%.1f, %.1f pitch</text>'
             % (CL, METER_TOP + (METER_N - 1) * METER_PITCH + 3.6, METER_N, LED_HOLE,
                METER_PITCH))
    for label, base, x, kind in METERS:
        o.append('<text x="%.2f" y="%.2f" font-family="Helvetica,Arial" font-size="1.7" '
                 'fill="#555" text-anchor="middle">%s</text>' % (x, METER_TOP - 2.6, label))

    def dim_v(x, y1, y2, txt, off):
        o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" %s/>' % (x+off,y1,x+off,y2,thin))
        for yy in (y1, y2):
            o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" %s/>' % (x,yy,x+off,yy,thin))
        o.append('<text x="%.2f" y="%.2f" font-family="Helvetica,Arial" font-size="2.1" '
                 'fill="#111" transform="rotate(-90 %.2f %.2f)" text-anchor="middle">%s</text>'
                 % (x+off-1.0, (y1+y2)/2, x+off-1.0, (y1+y2)/2, txt))

    def dim_h(y, x1, x2, txt, off):
        o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" %s/>' % (x1,y+off,x2,y+off,thin))
        for xx in (x1, x2):
            o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" %s/>' % (xx,y,xx,y+off,thin))
        o.append('<text x="%.2f" y="%.2f" font-family="Helvetica,Arial" font-size="2.1" '
                 'fill="#111" text-anchor="middle">%s</text>' % ((x1+x2)/2, y+off-1.0, txt))

    dim_h(0, 0, W, '38.10 (1.500")', -7)
    dim_v(W, 0, H, '133.35 (5.250")', 11)
    dim_v(CL, HOLE_Y[0], HOLE_Y[1], '125.43 (4.938")', -15)
    dim_h(H, 0, CL, '19.05', 9)
    o.append('<text x="0" y="%.2f" font-family="Helvetica,Arial" font-size="2.3" fill="#111">'
             'OPN-500 / CMP-01 compressor : front panel</text>' % (H + 15))
    o.append('<text x="0" y="%.2f" font-family="Helvetica,Arial" font-size="1.8" fill="#555">'
             "Material 3.18 mm (0.125&quot;) aluminium. Mounting holes &#216;3.18, c'sink 82&#176; "
             'to &#216;5.72. All dimensions mm.</text>' % (H + 18.4))
    o.append('</g></svg>')
    return '\n'.join(o)


# ---------------------------------------------------------------- DXF (R12 ASCII)
def dxf():
    e = []
    def line(x1, y1, x2, y2):
        e.append('0\nLINE\n8\nPANEL\n10\n%.4f\n20\n%.4f\n11\n%.4f\n21\n%.4f' % (x1,y1,x2,y2))
    def circle(x, y, r, layer):
        e.append('0\nCIRCLE\n8\n%s\n10\n%.4f\n20\n%.4f\n40\n%.4f' % (layer, x, y, r))
    def fy(y): return H - y
    line(0,0,W,0); line(W,0,W,H); line(W,H,0,H); line(0,H,0,0)
    for ref, x, y, d in all_holes():
        circle(x, fy(y), d / 2, 'MOUNT' if ref.startswith('MTG') else 'CUTOUT')
    return '0\nSECTION\n2\nENTITIES\n' + '\n'.join(e) + '\n0\nENDSEC\n0\nEOF\n'


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    issues = clearance_report()
    for i in issues:
        print('CLEARANCE: ' + i)
    if not issues:
        print('clearance check: no fouling, %d holes (%d knob positions, %d meter LEDs, '
              '%d switches, 2 mounting)'
              % (len(all_holes()), len(CONCENTRIC) + len(SINGLES), len(meter_leds()),
                 len(BUTTONS) + len(TOGGLES)))
    for name, data in [('faceplate-mockup.svg', mockup()),
                       ('faceplate-drawing.svg', drawing()),
                       ('faceplate.dxf', dxf())]:
        open(os.path.join(here, name), 'w').write(data)
        print('wrote %-24s %6.1f KB' % (name, len(data) / 1024))
