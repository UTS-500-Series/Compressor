#!/usr/bin/env python3
"""Generates the documentation HTML. The output is plain static HTML - edit either
this script and re-run it, or the .html files directly. Run: python3 _build.py"""
import os, html

PROJECT = "UTS Mini Mixing Desk &mdash; Compressor"
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
         'family=Archivo:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&'
         'family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">')

NAV = [
    ("Start here", [("index.html", "01", "Overview")]),
    ("Signal path", [("connector.html", "02", "500-series interface"),
                     ("input.html",     "03", "Balanced input &amp; pad"),
                     ("vca.html",       "04", "The gain cell"),
                     ("output.html",    "05", "Makeup &amp; output")]),
    ("Control path", [("sidechain.html", "06", "The sidechain")]),
    ("Support", [("power.html", "07", "Power &amp; references"),
                 ("meters.html", "08", "The LED meters")]),
    ("Practical", [("panel.html", "09", "The front panel"),
                   ("using.html", "10", "Setting up &amp; using it")]),
]
ORDER = [p for _, g in NAV for p, _, _ in g]
TITLES = {p: t for _, g in NAV for p, _, t in g}


def shell(fname, title, body):
    nav = []
    for head, group in NAV:
        nav.append('<h4>%s</h4>' % head)
        for href, num, label in group:
            on = ' class="on"' if href == fname else ''
            nav.append('<a href="%s"%s><i>%s</i><span>%s</span></a>' % (href, on, num, label))
    i = ORDER.index(fname)
    prev = ('<a href="%s">&larr; %s</a>' % (ORDER[i-1], TITLES[ORDER[i-1]])) if i > 0 else '<span></span>'
    nxt = ('<a href="%s">%s &rarr;</a>' % (ORDER[i+1], TITLES[ORDER[i+1]])) if i < len(ORDER)-1 else '<span></span>'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} &middot; {PROJECT}</title>
<meta name="description" content="How the UTS Mini Mixing Desk compressor module works, section by section.">
{FONTS}
<link rel="stylesheet" href="style.css">
<script>
/* Runs before paint so a stored preference does not flash narrow first. */
try {{
  if (localStorage.getItem('uts-width') === 'wide')
    document.documentElement.dataset.width = 'wide';
}} catch (e) {{}}
</script>
<script src="vendor/cytoscape.min.js" defer></script>
<script src="viewer.js" defer></script>
</head><body>
<div class="shell">
<aside class="side">
  <a class="brand" href="index.html"><b>UTS Mini Mixing Desk</b><span>Compressor module</span></a>
  <button class="menu" onclick="document.querySelector('nav').classList.toggle('open')">Contents</button>
  <nav>{''.join(nav)}</nav>
  <div class="side-foot">
    <button class="wbtn" id="wbtn" type="button" aria-pressed="false">
      <span class="wbtn-ico" aria-hidden="true"></span><span class="wbtn-txt">Wide layout</span>
    </button>
  </div>
</aside>
<main class="main"><div class="wrap">
{body}
<div class="next">{prev}{nxt}</div>
<footer>
  UTS Mini Mixing Desk &mdash; Compressor &middot; documentation generated from the KiCad project<br>
  Schematics are exported from the project in this repository. Figures update when you re-run <code>_build.py</code>.<br>
  Performance figures are calculated from the design, not measured on hardware.
</footer>
</div></main>
</div></body></html>
"""


def fig(name, caption, note=""):
    """Interactive viewer: the real schematic with clickable parts, plus the same sheet
    as a netlist graph. Sheet data is inlined so it works from file:// too."""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, 'data', '%s.json' % name)) as f:
        payload = f.read()
    return f"""<div class="iv" id="iv-{name}">
  <div class="iv-bar">
    <button class="iv-tab on" data-view="schematic">Schematic</button>
    <button class="iv-tab" data-view="graph">Connections</button>
    <span class="iv-sp"></span>
    <input class="iv-find" type="search" placeholder="find R14, VBIAS…" aria-label="Find part or net">
    <button class="iv-btn iv-zout" title="Zoom out">&minus;</button>
    <button class="iv-btn iv-zin" title="Zoom in">+</button>
    <button class="iv-btn iv-lay" title="Change graph layout">Flow</button>
    <button class="iv-btn iv-zres" title="Fit">Fit</button>
  </div>
  <div class="iv-body"></div>
  <div class="iv-key">
    <span class="iv-trace"></span>
    <span class="iv-sp"></span>
    <span class="k sig">audio</span><span class="k ctl">control</span>
    <span class="k pwr">supply</span><span class="k gnd">ground</span>
    <span class="k dot">junction</span>
  </div>
  <div class="iv-foot">
    <span>{caption}</span>
    <a href="img/{name}.svg" target="_blank" rel="noopener">Open the plain schematic &rarr;</a>
  </div>
  <script type="application/json">{payload}</script>
</div>{note}"""


def pic(name, caption, note=""):
    """Static figure. The panel drawings are not schematic sheets, so they get a plain
    image rather than the interactive viewer."""
    return f"""<figure>
  <div class="pane tall"><img src="img/{name}" alt="{caption}" loading="lazy"></div>
  <figcaption><span>{caption}</span><a href="img/{name}" target="_blank" rel="noopener">Open full size &rarr;</a></figcaption>
</figure>{note}"""


def table(headers, rows, cls=None):
    cls = cls or [''] * len(headers)
    h = ''.join('<th class="%s">%s</th>' % (c, x) for x, c in zip(headers, cls))
    b = ''.join('<tr>%s</tr>' % ''.join('<td class="%s">%s</td>' % (c, x)
                for x, c in zip(r, cls)) for r in rows)
    return '<div class="tw"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (h, b)


PAGES = {}

# ============================================================ 01 OVERVIEW
PAGES['index.html'] = ("Overview", """
<p class="eyebrow">Compressor module</p>
<h1>How this compressor works</h1>
<p class="lede">A 500-series dynamics module built from ordinary parts &mdash; nine BC549
transistors, seven NE5532 op amps and a pair of LED bargraph drivers. This site walks through every section of the
schematic: what it does, how it does it, and why it was built that way.</p>
<div class="note">
  <h4>The schematics are interactive</h4>
  <p>Every sheet on this site is live. Scroll to zoom and drag to pan, click any part to see
  its value, footprint and every net it touches, and click a net to light up everything else
  connected to it. The <strong>Connections</strong> tab shows the same sheet as a graph &mdash;
  parts and nets are both nodes, because a net joins any number of pins, not just two. There is
  a search box for jumping straight to a designator like <code>R14</code> or a net like
  <code>VBIAS</code>.</p>
</div>

<dl class="spec">
  <div><dt>Format</dt><dd>500 series</dd></div>
  <div><dt>Supply</dt><dd>&plusmn;16 V</dd></div>
  <div><dt>Gain reduction</dt><dd>~40 dB max</dd></div>
  <div><dt>Components</dt><dd>128</dd></div>
  <div><dt>Nets</dt><dd>83</dd></div>
  <div><dt>Sheets</dt><dd>6</dd></div>
</dl>

<h2>What a compressor actually does</h2>
<p>A compressor makes loud sounds quieter, automatically. You set a <strong>threshold</strong>;
anything louder gets turned down. The result is a signal with a smaller gap between its
quietest and loudest parts, which is easier to mix, easier to broadcast, and harder to
accidentally clip.</p>
<p>To do that, a compressor needs two things: a way to <em>change its own gain</em> under
electrical control, and a way to <em>measure how loud the signal is</em> so it knows how much
to change it by. Those two jobs split this design cleanly in half:</p>

<div class="flow">
  <b class="a">IN</b><i>&rarr;</i><b class="a">Input receiver</b><i>&rarr;</i><b class="a">Pad</b>
  <i>&rarr;</i><b class="a">Gain cell</b><i>&rarr;</i><b class="a">Recovery amp</b>
  <i>&rarr;</i><b class="a">Makeup gain</b><i>&rarr;</i><b class="a">OUT</b>
</div>
<div class="flow">
  <b class="c">Detector</b><i>&larr;</i><b class="c">Rectifier</b><i>&larr;</i><b class="c">Threshold</b>
  <i>&larr;</i><i>listens to the output</i>
</div>

<p>The <span class="sig">amber path</span> is audio. The <span class="ctl">teal path</span> is
control &mdash; it carries a slow DC voltage that represents "how loud is it right now", and
that voltage is what turns the gain cell down.</p>

<h2>Feedback, not feedforward</h2>
<p>Notice that the detector listens to the <strong>output</strong>, not the input. That makes
this a <strong>feedback</strong> compressor, and it is the single decision that gives the
module its character.</p>
<p>In a feedforward design the detector measures the input and calculates exactly how much
gain reduction to apply, so you can dial in a precise ratio like 4:1. In a feedback design the
detector measures the result and keeps pushing until the output stops getting louder. You
cannot label the ratio precisely, because it emerges from the loop gain rather than being set
directly &mdash; but the knee comes out soft and program-dependent on its own, and the circuit
is far more forgiving of component tolerance. Most classic bus compressors work this way.</p>

<h2>The sections</h2>
<div class="cards">
  <a class="card" href="connector.html"><b>500-series interface</b><span>How the module gets audio and power from the rack, and the one pin that is not standard.</span></a>
  <a class="card" href="input.html"><b>Balanced input &amp; pad</b><span>Turning a balanced line signal into something the gain cell can handle without distorting.</span></a>
  <a class="card" href="vca.html"><b>The gain cell</b><span>Nine transistors that steer current to set gain. The heart of the module.</span></a>
  <a class="card" href="output.html"><b>Makeup &amp; output</b><span>Getting the level back and driving the outside world.</span></a>
  <a class="card" href="sidechain.html"><b>The sidechain</b><span>Measuring loudness and turning it into a control voltage, with attack and release.</span></a>
  <a class="card" href="power.html"><b>Power &amp; references</b><span>Rails, the &minus;5.1 V reference, and the bias voltages everything else depends on.</span></a>
  <a class="card" href="panel.html"><b>The front panel</b><span>Nine functions in 38 mm, three ways to arrange them, and why each one is a compromise.</span></a>
</div>

<div class="note warn">
  <h4>Read this before building</h4>
  <p>Nothing here has been built or simulated. Every performance figure on this site is
  <strong>calculated from the design</strong>, not measured. The netlist has been verified
  against the schematic automatically, and ERC passes with no errors, but that only proves the
  drawing is self-consistent &mdash; not that the circuit behaves as predicted.</p>
</div>
""")

# ============================================================ 02 CONNECTOR
PAGES['connector.html'] = ("500-series interface", """
<p class="eyebrow">Sheet 1</p>
<h1>The 500-series interface</h1>
<p class="lede">A 500-series module is a card that plugs into a rack. The rack supplies power
and carries audio in and out on a single 15-pin edge connector.</p>

""" + fig("connector", "Sheet 1 &mdash; edge connector J1") + """

<h2>What the rack gives you</h2>
<p>Everything arrives on one card-edge connector: a 15-pin EDAC at 0.156&Prime; pitch. There is
no separate power lead and no separate audio lead &mdash; slide the card in and it is connected.
That is the whole appeal of the format.</p>
<p>The rack provides <strong>&plusmn;16 V</strong> and a ground. It expects the module to
present a balanced input and drive a balanced output. It does not provide a regulated low
voltage, so anything else the module needs it has to make for itself.</p>

<h2>Pin by pin</h2>
""" + table(
    ["Pin", "Standard function", "Used here for", "Notes"],
    [["1", "Chassis ground", "Chassis / shield", "Tied to audio ground through a 100 &Omega; + 10 nF network"],
     ["2", "Output + (+4)", "Main output, hot", "Driven through a 100 &Omega; build-out resistor"],
     ["3", "Output + (&minus;2)", "Aux output, hot", "Chassis-specific &mdash; buffered duplicate of the main output"],
     ["4", "Output &minus;", "Main output, cold", "Driven in antiphase, also through 100 &Omega;"],
     ["5", "Audio ground", "Audio ground (AGND)", "The module's star ground"],
     ["6", "525 stereo link", "Stereo link", "Ties two modules' detectors together"],
     ["7", "Input &minus; (&minus;2)", "Aux output, cold", "Chassis-specific"],
     ["8", "Input &minus; (+4)", "Main input, cold", ""],
     ["9", "Input + (&minus;2)", "Aux input, cold", "Chassis-specific &mdash; external key input"],
     ["10", "Input + (+4)", "Main input, hot", ""],
     ["11", "Gain trim resistor", "Aux input, hot", "<strong>Not standard.</strong> See the warning below"],
     ["12", "+16 V", "+16 V", "Through a 10 &Omega; series resistor into the module"],
     ["13", "PSU ground", "PSU ground (PGND)", "Joined to AGND at exactly one point"],
     ["14", "&minus;16 V", "&minus;16 V", "Through a 10 &Omega; series resistor"],
     ["15", "+48 V", "<em>not connected</em>", "Phantom power has no use on a line-level compressor"]],
    ["r", "", "", ""]) + """

<div class="note warn">
  <h4>Pin 11 is not standards-clean</h4>
  <p>The API 500 specification assigns pin 11 to a <em>gain trim resistor</em> node, not to
  audio. This module uses it as the hot side of an auxiliary input. That is fine in the chassis
  it was designed for, but it means the Aux section is not portable to an arbitrary 500 rack.
  The Aux circuitry is kept as a separable block for exactly this reason &mdash; leave it
  unpopulated and the module is fully standard.</p>
</div>

<h2>Why balanced?</h2>
<p>A balanced connection sends the signal twice: once normally on the hot pin, once inverted on
the cold pin. Any interference the cable picks up along the way lands on <em>both</em> wires
equally. At the far end the receiver subtracts one from the other, so the wanted signal
(which is opposite on the two wires) adds, while the interference (which is identical on both)
cancels. That cancellation is called <strong>common-mode rejection</strong>, and it is why
professional audio runs balanced over long cables.</p>
<p>How well it works depends on how accurately the receiver subtracts &mdash; which comes down
to resistor matching, covered on the next page.</p>

<h2>Grounding</h2>
<p>Three grounds arrive at this connector and they are not the same thing:</p>
<ul>
  <li><strong>Audio ground (pin 5)</strong> is the reference every signal voltage is measured against.</li>
  <li><strong>PSU ground (pin 13)</strong> is the return path for supply current, which is noisy.</li>
  <li><strong>Chassis ground (pin 1)</strong> is metalwork and shielding.</li>
</ul>
<p>They are joined at exactly one point on the module &mdash; a single 0 &Omega; link,
<code>R48</code>, on the power sheet. Joining them at more than one point creates a loop that
supply current can flow around, and any voltage that loop develops appears in series with your
audio. This is the classic cause of hum in otherwise-correct equipment.</p>
""")

# ============================================================ 03 INPUT
PAGES['input.html'] = ("Balanced input &amp; pad", """
<p class="eyebrow">Sheet 2</p>
<h1>Balanced input and pad</h1>
<p class="lede">Two jobs: convert the balanced input into a single-ended signal, then throw
most of it away. The second one sounds wrong, and is the key to the whole design.</p>

""" + fig("input", "Sheet 2 &mdash; input receiver U1A and the pad") + """

<h2>The receiver: U1A</h2>
<p><code>U1A</code> is wired as a <strong>difference amplifier</strong>. Four 22 k&Omega;
resistors surround it: <code>R1</code> and <code>R2</code> feed the two inputs,
<code>R4</code> is the feedback resistor and <code>R3</code> goes to ground. When all four are
equal, the output is simply <em>hot minus cold</em>, at unity gain.</p>
<p>Ahead of them, <code>C1</code> and <code>C2</code> (22 &micro;F bipolar) block any DC the
previous device might be sitting on, and <code>R5</code>/<code>R6</code> with
<code>C3</code>/<code>C4</code> form a small filter that shunts radio frequencies to ground
before they reach the op amp. Op amps rectify RF into audible noise if you let it in.</p>

<div class="note">
  <h4>Why the resistors must be 0.1%</h4>
  <p>Common-mode rejection depends entirely on how well the four 22 k&Omega; resistors match.
  With ordinary 1% parts the worst-case mismatch limits you to roughly <strong>46 dB</strong>
  of rejection. With 0.1% parts it is about <strong>66 dB</strong>. That is a 20 dB
  improvement for no change other than buying better resistors, which is why they are called
  out specially in the BOM.</p>
</div>

<h2>The pad, and why it exists</h2>
<p>After the receiver the signal hits <code>R7</code>, <code>RV1</code> and <code>R8</code>
&mdash; a plain resistive divider that attenuates by roughly <strong>42 dB</strong>. It throws
away over 99% of the signal.</p>
<p>This looks like vandalism. The reason is the gain cell that follows.</p>
<p>The gain cell is built from transistors, and a transistor is only linear over a very small
voltage range &mdash; a few tens of millivolts. Push more than that into it and it distorts
badly. So the signal is deliberately shrunk to a level the transistors can handle cleanly, run
through the cell, and then amplified back up afterwards by the recovery amplifier and the
makeup gain stage.</p>
<p>The cost is noise. Attenuating and re-amplifying means the cell's own noise is amplified
along with the signal, so the noise floor ends up higher than it would be without the pad.
<strong>Every gain cell design is a negotiation between distortion and noise, and the pad is
where that negotiation happens.</strong> Make it bigger and the module gets cleaner but
hissier; make it smaller and it gets quieter but grittier.</p>

<h3>Where the numbers come from</h3>
""" + table(
    ["Stage", "Gain", "Reason"],
    [["Input receiver U1A", "0 dB", "Difference amplifier, unity by design"],
     ["Pad (R7 + RV1 / R8)", "&minus;42 dB", "Shrink the signal to suit the transistors"],
     ["Gain cell (max)", "+26 dB", "4k7 collector load &divide; 237 &Omega; emitter resistance"],
     ["Recovery amp U1B", "+16.5 dB", "22 k &divide; 3k3"],
     ["<strong>Through gain</strong>", "<strong>~0 dB</strong>", "The pad is chosen to cancel the two gain stages"]],
    ["", "n", ""]) + """
<p><code>RV1</code> is the trimmer that lets you land exactly on unity, absorbing the tolerance
of everything upstream and downstream of it. It is the only audio trim in the module.</p>

<h2 id="errata">How R8 was chosen</h2>
<p>The pad has to divide by whatever the cell and recovery amp multiply by, so the two cancel
and the module passes signal at unity. Working it through:</p>
<ul>
  <li>Gain cell at full gain: 4k7 collector load &divide; 237 &Omega; emitter resistance =
      <strong>19.8&times;</strong></li>
  <li>Recovery amp <code>U1B</code>: 22 k &divide; 3k3 = <strong>6.67&times;</strong></li>
  <li>Together: <strong>132&times;</strong>, so the pad must divide by 132</li>
</ul>
<p>The divider ratio is <code>(R7 + RV1 + R8) / R8</code>. With <code>R7</code> = 8k2 and
<code>RV1</code> spanning 0&ndash;2k, that needs <code>R8</code> &asymp; 75 &Omega;, giving a
ratio of 110&ndash;137&times; &mdash; which puts unity comfortably inside the trimmer's range.</p>

<div class="note warn">
  <h4>If you are working from an early copy of this design</h4>
  <p>An earlier revision specified <code>R8</code> = 47 &Omega;. That gives a ratio of
  175&ndash;218&times; &mdash; too much attenuation, leaving the module 2.5 to 4.4 dB below
  unity with the trimmer at either end, so <code>RV1</code> could never reach unity. The
  current schematic and <code>design.py</code> both specify <strong>75 &Omega;</strong>.
  Check your board before assembling.</p>
</div>

<h2>What to check when you build it</h2>
<ul>
  <li>With no signal, U1A's output should sit within a few millivolts of ground.</li>
  <li>Feed +4 dBu in; you should measure roughly 1.2 V RMS at U1A's output and around
      <strong>9 mV RMS</strong> after the pad. That tiny number is correct &mdash; it is the
      whole point.</li>
  <li>To check common-mode rejection, tie hot and cold together and drive them from one source.
      The output should drop into the noise. If it does not, your 22 k&Omega; resistors are not
      matched.</li>
</ul>
""")

# ============================================================ 04 VCA
PAGES['vca.html'] = ("The gain cell", """
<p class="eyebrow">Sheet 3</p>
<h1>The gain cell</h1>
<p class="lede">Nine transistors whose only job is to have a gain you can change with a
voltage. This is the part of a compressor that actually compresses, and the part where the
design decisions matter most.</p>

""" + fig("vca", "Sheet 3 &mdash; the steering cell Q1&ndash;Q9 and recovery amplifier U1B") + """

<h2>The problem</h2>
<p>You need an amplifier whose gain a control voltage can set, over a wide range, without
adding much distortion or noise. Commercially you would buy a THAT2180 or an SSM2018 and be
done. Building one from discrete transistors is harder, and there are two common approaches.</p>

<h3>The simple approach, and why it was rejected</h3>
<p>The obvious method is a <strong>long-tailed pair</strong>: two matched transistors sharing a
current source in their emitters. The gain of such a pair depends on how much current flows
through it, so varying that "tail" current varies the gain. This is how the CA3080 works, and
how classic pedals like the Ross and the MXR Dyna Comp get their compression.</p>
<p>It has a flaw that matters at line level. A transistor's internal emitter resistance is
<em>inversely</em> proportional to its current. Turn the tail current down to reduce gain and
that resistance goes up, which shrinks the voltage range over which the pair stays linear.
In other words <strong>the cell distorts worst exactly when it is working hardest</strong>.
Calculated distortion climbs from about 0.2% at 6 dB of gain reduction to several percent at
18 dB. Fine for a guitar pedal, poor for a mixing desk.</p>

<h3>The approach used here: current steering</h3>
<p>Instead of varying the current, keep it <strong>constant</strong> and vary where it
<em>goes</em>.</p>
<ol>
  <li><code>Q3</code> is a current source holding a fixed <strong>~3 mA</strong> tail current,
      no matter what the control voltage does.</li>
  <li><code>Q1</code> and <code>Q2</code> are the matched pair that turns the input voltage into
      a signal current riding on that fixed tail. Because the tail never changes, their linear
      range never changes either.</li>
  <li>Above them sit four more transistors, <code>Q6</code>&ndash;<code>Q9</code>, arranged in
      two pairs. Each pair can send its share of the current either to the <strong>output</strong>
      load or to the <strong>+16 V rail</strong>, where it is simply thrown away.</li>
</ol>
<p>Gain is then just the <em>fraction</em> of the signal current that reaches the output. Send
all of it and you have full gain; dump 99% of it and you have 40 dB of gain reduction. And
because the transistors doing the amplifying never change their operating point, the distortion
stays flat at every gain setting. That is the whole argument for the extra four transistors.</p>

<div class="note good">
  <h4>The trade in one line</h4>
  <p>Varying current is simpler and distorts more as it compresses. Steering current costs four
  extra transistors and distorts the same amount however hard it compresses.</p>
</div>

<h2>How the steering is controlled</h2>
<p>The four steering transistors have their bases tied to two nets, <code>STA</code> and
<code>STB</code>. What matters is only the <strong>difference</strong> between them:</p>
""" + table(
    ["STB relative to STA", "Where the current goes", "Gain"],
    [["+150 mV (resting)", "Almost entirely to the output", "Full gain, ~0 dB reduction"],
     ["0 mV", "Split evenly", "&minus;6 dB"],
     ["&minus;60 mV", "Mostly dumped to the rail", "&minus;20 dB"],
     ["&minus;120 mV", "Nearly all dumped", "&minus;40 dB"]],
    ["n", "", "n"]) + """
<p>The entire 40 dB range fits inside about a quarter of a volt. That sensitivity is why the
control voltage is scaled down heavily by <code>R68</code>/<code>R69</code> before it reaches
<code>STB</code> &mdash; a 10 V swing on the control line becomes a 270 mV swing here.</p>

<div class="note warn">
  <h4>Why matched transistors are not optional</h4>
  <p><code>Q1</code>/<code>Q2</code> must be a matched pair, and <code>Q6</code>&ndash;<code>Q9</code>
  a matched quad, all glued together so they stay at the same temperature. The steering balance
  is set by base-emitter voltages that differ by only tens of millivolts &mdash; and a transistor's
  base-emitter voltage drifts about &minus;2 mV for every &deg;C. If two transistors in the quad
  sit at different temperatures, the cell's gain drifts with them. Bond them face to face and
  put heatshrink over the group.</p>
</div>

<h2>Recovering the signal</h2>
<p>The steered current becomes a voltage across the collector load resistors <code>R16</code>
and <code>R17</code>, giving a <strong>differential</strong> signal &mdash; the wanted audio is
the difference between the two collectors.</p>
<p><code>Q4</code> and <code>Q5</code> are emitter followers that buffer those collectors so the
next stage does not load them, and <code>U1B</code> is a difference amplifier with a gain of
6.67&times; that converts the difference back into a normal single-ended signal.</p>
<p>Taking the output differentially is what makes gain changes inaudible. When the cell changes
gain, the DC level at <em>both</em> collectors moves together. That common movement is exactly
what a difference amplifier rejects &mdash; so the "thump" you would otherwise hear on a fast
attack largely cancels. How well it cancels depends on <code>R21</code>&ndash;<code>R24</code>
matching, which is why they are 0.1% parts too.</p>

<h2>The honest limitations</h2>
<ul>
  <li><strong>Noise rises with gain reduction.</strong> The dump transistors keep generating
      noise even when carrying no signal. Expect the noise floor to climb roughly 6 dB by the
      time you are 20 dB into gain reduction. Every steering-type cell does this, including the
      commercial ICs.</li>
  <li><strong>The control law drifts with temperature.</strong> Gain reduction per volt scales
      with a quantity proportional to absolute temperature, so the dB-per-volt slope moves about
      0.33% per &deg;C. Over a 20 &deg;C swing a nominal 20 dB of reduction shifts by a few
      tenths of a dB. If that matters, <code>R68</code> can be a +3300 ppm/&deg;C tempco resistor
      mounted against the transistor quad.</li>
</ul>
""")

# ============================================================ 05 OUTPUT
PAGES['output.html'] = ("Makeup &amp; output", """
<p class="eyebrow">Sheet 4</p>
<h1>Makeup gain and the output stage</h1>
<p class="lede">Compression makes things quieter. This section gives you the level back and
drives it out of the module.</p>

""" + fig("output", "Sheet 4 &mdash; makeup gain U2A, output drivers U2A/U2B, bypass, and the aux section") + """

<h2>Makeup gain</h2>
<p>Once the compressor is pulling 10 dB off the peaks, the whole signal is quieter than it was.
<strong>Makeup gain</strong> puts it back so you can compare compressed and uncompressed at the
same loudness &mdash; without which every compressor sounds worse simply because it is
quieter.</p>
<p><code>U2A</code> is a non-inverting amplifier. <code>R26</code> (1 k&Omega;) sits from its
inverting input to ground and <code>RV2</code> (10 k&Omega;) forms the feedback, so the gain is
<code>1 + RV2/R26</code> &mdash; adjustable from <strong>1&times; to 11&times;</strong>, or
0 to about +21 dB.</p>

<div class="note">
  <h4>Why the detector taps before this stage</h4>
  <p>The sidechain listens at <code>SIG-VCA</code>, which is the recovery amplifier's output
  &mdash; <em>before</em> makeup gain. If it listened after, then turning up makeup would raise
  the level the detector sees, which would increase gain reduction, which would lower the
  output... and your threshold setting would change every time you touched the makeup knob.
  Tapping before makeup keeps the two controls independent.</p>
</div>

<h2>Driving the output</h2>
<p>The module has to present a balanced output. It does that with two op amps in antiphase:
<code>U2A</code> drives the hot pin directly, and <code>U2B</code> is a unity-gain inverter
(<code>R29</code>/<code>R30</code>, both 10 k&Omega;) that produces the cold pin. The two
outputs move in opposite directions, which is exactly what a balanced receiver at the other end
wants to see.</p>
<p><code>R28</code> and <code>R32</code>, both 100 &Omega;, sit in series with each output.
They are <strong>build-out resistors</strong>: they isolate the op amp from the capacitance of
whatever cable you plug in. Without them a long cable can make the op amp oscillate.</p>

<div class="note warn">
  <h4>Do not ground the cold output</h4>
  <p>Because both pins are actively driven, shorting pin 4 to ground &mdash; which is what
  happens if you feed an unbalanced input with the wrong cable &mdash; puts an NE5532 output
  into 100 &Omega;. It will survive, but it will run hot and distort. If unbalanced destinations
  are likely, raise <code>R28</code> and <code>R32</code> to 220 &Omega;, or fit an output
  transformer.</p>
</div>

<h2>Hard bypass</h2>
<p><code>SW1</code> is a DPDT switch that transfers output pins 2 and 4 between the module's
own drivers and the input pins 10 and 8. In bypass, the audio goes straight from the rack's
input to the rack's output through nothing but a switch contact &mdash; genuinely out of
circuit, not just "gain set to unity". That is what makes an A/B comparison trustworthy.</p>

<h2>The aux section</h2>
<p>Drawn as a separable block because it uses chassis-specific pins:</p>
<ul>
  <li><strong>Aux in (pins 11, 9)</strong> &rarr; <code>U5A</code>, another difference amplifier,
      producing the <code>KEY</code> net. This is an <em>external key</em> input: it lets the
      compressor respond to a different signal than the one it is processing. Ducking a music bed
      under a voiceover is the classic use.</li>
  <li><strong>Aux out (pins 3, 7)</strong> &rarr; <code>U5B</code> buffers the main output to
      give a duplicate feed. It is <em>impedance balanced</em> rather than actively driven:
      the hot pin carries the signal through 100 &Omega; and the cold pin is 100 &Omega; to
      ground. A balanced receiver still rejects interference properly, at half the level and
      half the parts.</li>
</ul>
<p>Omit <code>U5</code> and its four resistors and the module becomes fully standards-compliant,
and gives back about 16 mA per rail.</p>
""")

# ============================================================ 06 SIDECHAIN
PAGES['sidechain.html'] = ("The sidechain", """
<p class="eyebrow">Sheet 5</p>
<h1>The sidechain</h1>
<p class="lede">The part that decides how much compression to apply. It measures the output,
compares it to a threshold, and produces the DC control voltage that drives the gain cell.</p>

""" + fig("sidechain", "Sheet 5 &mdash; source select, threshold, rectifier, ratio, timing and control buffer") + """

<h2>The chain, stage by stage</h2>
<div class="flow">
  <b class="c">Source select</b><i>&rarr;</i><b class="c">Buffer</b><i>&rarr;</i><b class="c">HPF</b>
  <i>&rarr;</i><b class="c">Threshold</b><i>&rarr;</i><b class="c">Rectifier</b>
  <i>&rarr;</i><b class="c">Ratio</b><i>&rarr;</i><b class="c">Timing</b><i>&rarr;</i><b class="c">To gain cell</b>
</div>

<h3>1. Source select and buffer</h3>
<p><code>SW2</code> chooses between the module's own output (<code>SIG-VCA</code>) and the
external key input. <code>U6B</code> buffers whichever you picked so the following controls do
not load the source.</p>

<h3>2. The sidechain high-pass filter</h3>
<p><code>C14</code> (220 nF) with <code>R38</code> (10 k&Omega;) makes a high-pass filter at
about <strong>72 Hz</strong>, which <code>SW3</code> can short out.</p>
<p>This exists because bass carries most of the energy in music. Without it, every kick drum
hit pulls the whole mix down and the compressor "pumps" to the beat. Rolling the bass out of
the <em>detector only</em> &mdash; the audio path is untouched &mdash; makes the compressor
respond to the overall balance instead of to the low end.</p>

<h3>3. Threshold</h3>
<p><code>RV3</code> (1 M&Omega;) is wired as a <strong>rheostat</strong>: a variable resistor
feeding <code>U3A</code>, whose gain is <code>R36 / (R35 + RV3)</code>. Turning it up increases
the detector's gain, so a quieter signal is enough to start compression &mdash; which is what
lowering a threshold means.</p>
<p>Wiring it this way is deliberate. Because gain is inversely proportional to resistance, a
plain <em>linear</em> pot produces a roughly <em>logarithmic</em> sweep in dB, which is what
feels natural on the knob. The usable range is about &minus;20 dBu to +14 dBu.</p>

<h3>4. The precision rectifier</h3>
<p>To measure loudness you need the size of the signal regardless of sign &mdash; its absolute
value. A plain diode cannot do this at audio levels, because it needs about 0.6 V before it
conducts at all and anything smaller vanishes.</p>
<p>The fix is to put the diodes <em>inside</em> an op amp's feedback loop. <code>U3B</code>
with <code>D5</code> and <code>D6</code> forms a half-wave rectifier whose op amp simply drives
harder to overcome the diode drop, so the law holds down to millivolts. <code>U4A</code> then
sums the half-wave result at twice the weight of the original signal, and the arithmetic works
out to a clean <strong>full-wave</strong> absolute value at <code>RECT</code>.</p>
<p>Full-wave rather than half-wave matters because it doubles the ripple frequency, which makes
the ripple easier to smooth away in the next stage without slowing the compressor down.</p>

<h3>5. Ratio</h3>
<p><code>RV4</code> (100 k&Omega;) is a plain divider on the rectifier output. It sets how much
control voltage reaches the gain cell for a given amount of signal &mdash; in other words, how
many dB of gain reduction you get per dB over threshold. That is what "ratio" means.</p>

<h3>6. Attack and release</h3>
<p>This is where the compressor gets its <em>timing</em>. <code>C15</code> (10 &micro;F) is the
timing capacitor, and its voltage <em>is</em> the control signal.</p>
""" + table(
    ["Control", "Path", "Time constant"],
    [["Attack", "<code>RV5</code> 4k7 + <code>R46</code> 47 &Omega; + <code>R45</code> 220 &Omega;, through <code>D7</code> into C15",
      "2.7 ms &ndash; 50 ms"],
     ["Release", "<code>RV6</code> 220 k&Omega; + <code>R47</code> 4k7 discharging C15 to ground",
      "47 ms &ndash; 2.2 s"]],
    ["", "", "n"]) + """
<p><code>D7</code> is what separates the two. Charging current can only flow into the capacitor
through the diode, so the <em>attack</em> path is the diode plus the attack resistor. Discharge
cannot flow back through the diode, so it has to go through the release resistor instead. One
diode gives you two independent time constants.</p>
<p>Short attack catches transients but sounds aggressive; long attack lets the initial hit
through and sounds punchier. Short release recovers quickly but can pump audibly; long release
is smoother but can leave the signal held down after a loud passage.</p>

<h3>7. Control buffer</h3>
<p><code>U4B</code> buffers the timing capacitor. Its job is to read the capacitor's voltage
without discharging it. <code>R74</code> (220 k&Omega;) in the feedback path is chosen to match
the release network's resistance, so the op amp's small input bias current produces an equal
error on both inputs and cancels rather than shifting the resting point.</p>

<div class="note warn">
  <h4>The one place worth deviating from NE5532</h4>
  <p>An NE5532's inputs draw around 200 nA. On a 220 k&Omega; timing node that can leave enough
  offset to hold the compressor in about a decibel of gain reduction at idle. Fitting a
  <strong>TL072 or OPA2134 for U4 only</strong> &mdash; both pin-compatible &mdash; removes the
  problem entirely, because FET inputs draw essentially no current.</p>
</div>

<h2>Stereo link</h2>
<p><code>SW4</code> connects the detector node to pin 6. With two modules linked, each
detector sees the <em>average</em> of both channels, so they always apply identical gain
reduction. Without linking, a loud sound on one side only would pull that side down and shift
the stereo image sideways.</p>
<p>Set attack and release the same on both modules when linked.</p>
""")

# ============================================================ 07 POWER
PAGES['power.html'] = ("Power &amp; references", """
<p class="eyebrow">Sheet 6</p>
<h1>Power and references</h1>
<p class="lede">Not a signal path &mdash; five small independent circuits plus a block of
decoupling. Everything else in the module depends on getting these voltages right.</p>

""" + fig("power", "Sheet 6 &mdash; rail entry, references, bias, meter, grounding and decoupling") + """

<h2>Rail entry</h2>
<p>The &plusmn;16 V rails arrive from the rack and pass through <code>R50</code> and
<code>R51</code> (10 &Omega; each) into reservoir capacitors <code>C16</code> and
<code>C17</code> (100 &micro;F). The resistors do two things: with the capacitors they form a
low-pass filter that keeps rack-borne noise out, and they limit fault current if something goes
wrong on the card.</p>
<p><code>D8</code> and <code>D9</code> are reverse-polarity clamps. Both sit
<strong>cathode-up</strong>, meaning both are reverse-biased and doing nothing in normal
operation. If a rail ever arrives with the wrong polarity, the corresponding diode conducts and
clamps it near ground while the 10 &Omega; resistor absorbs the current, instead of that
polarity reaching every IC on the board.</p>

<h2>The &minus;5.1 V reference</h2>
<p>The gain cell's current source needs a stable negative reference that is <em>not</em> the
&minus;16 V rail &mdash; using the rail directly would make the tail current, and therefore the
gain, follow every wobble on the supply.</p>
<p><code>R53</code> (1k8) feeds <strong>6.1 mA</strong> from the &minus;16 V rail into
<code>D10</code>, a 5.1 V zener. The cell draws about 3 mA of that, leaving roughly 3 mA
through the zener &mdash; comfortably inside its regulating range.
<code>C19</code> and <code>C20</code> bypass it.</p>

<h2>Cell bias &mdash; VBIAS</h2>
<p><code>R9</code> (68 k&Omega;) and <code>R10</code> (11 k&Omega;) divide +16 V down to
<strong>2.23 V</strong>, heavily bypassed by <code>C6</code> and <code>C7</code>.</p>
<p>This lifts the gain cell's input transistors off ground. Without it, <code>Q3</code>'s
collector would sit too close to its emitter and the current source would not have enough
voltage across it to behave like a current source. Raising the whole cell by 2.23 V buys
<code>Q3</code> about 2 V of headroom at full tail current.</p>

<h2>The steering reference</h2>
<p>This is the most sensitive network in the module, because it sets the gain cell's resting
point.</p>
""" + table(
    ["Net", "Voltage", "Set by", "What it does"],
    [["<code>VREF5</code>", "5.49 V", "R60 / (R61+R62)", "Top of the reference chain"],
     ["<code>VREFA</code>", "5.19 V", "R60+R61 / R62", "Buffered by U6A to become <code>STA</code>"],
     ["<code>STA</code>", "5.19 V", "U6A follower", "Fixed reference for the dump transistors"],
     ["<code>STB</code>", "5.34 V at rest", "R68 / R69 from VREF5 and the control voltage",
      "The controlled side &mdash; moves with compression"]],
    ["r", "n", "r", ""]) + """
<p>At rest <code>STB</code> sits about <strong>150 mV above</strong> <code>STA</code>, which
holds the cell fully on. As the control voltage goes negative, <code>R68</code>/<code>R69</code>
drag <code>STB</code> down; when it passes about 120 mV <em>below</em> <code>STA</code> the cell
is at roughly 40 dB of gain reduction.</p>
<p>That resting offset is set by <code>R61</code> (1k33) and <code>R62</code> (23k2), which is
why both are 0.1% parts. If <code>VREFA</code> comes out too high, <code>STB</code> starts below
<code>STA</code> and the module sits in permanent gain reduction.</p>

<h2>Gain-reduction meter</h2>
<p><code>R77</code> (3k9) and <code>LED1</code> hang off the control voltage. At rest the
control line is at 0 V and the LED is dark; at full compression it is near &minus;10 V and the
LED draws about 2 mA. Brightness tracks gain reduction directly &mdash; crude, but it costs two
components and tells you instantly whether the compressor is working.</p>
<p><strong>This is now superseded.</strong> <a href="meters.html">Sheet 7</a> carries a proper
seven-segment gain-reduction meter, and the panel has no hole for <code>LED1</code>. It is left
on the sheet as a build-time sanity check &mdash; it lights before any of the meter circuitry is
populated &mdash; but it can be omitted.</p>

<h2>Grounding</h2>
<p><code>R48</code> is a <strong>0 &Omega; link</strong> and it is the single most important
component on this sheet. It is the one and only place where PSU ground and audio ground meet.
Fit exactly one.</p>
<p><code>R52</code> (100 &Omega;) and <code>C18</code> (10 nF) connect chassis ground to audio
ground as a <em>hybrid</em>: the capacitor gives radio frequencies a low-impedance path to the
chassis for shielding, while the resistor stops mains-frequency current from circulating and
causing hum.</p>

<h2>Decoupling</h2>
<p>Every NE5532 gets a 100 nF capacitor on each supply pin, close to the package &mdash; twelve
in all. Op amps draw current in fast bursts as their outputs move; the capacitors supply that
locally instead of letting it travel around the board and modulate the rails. This is not
optional garnish, it is what stops one stage from talking to another through the supply.</p>

<div class="note">
  <h4>Current budget</h4>
  <p>About <strong>90 mA on +16 V and 70 mA on &minus;16 V</strong> typical, against the
  130 mA per rail the 500-series specification allows. The asymmetry is the
  <a href="meters.html">meter sheet</a>, whose display drivers and LEDs hang off the positive
  rail only. Worst-case NE5532s with a hard-driven output land near 140 mA on +16 V, which is
  over &mdash; that is a peak, not a steady state, but it is the number to watch. Building a
  stereo pair into a small frame? Omitting the aux section gives back roughly 16 mA per rail
  per module.</p>
</div>
""")

# ============================================================ 08 LED METERS
PAGES['meters.html'] = ("The LED meters", """
<p class="eyebrow">Sheet 7</p>
<h1>The LED meters</h1>
<p class="lede">Two seven-segment bargraphs &mdash; gain reduction and output level &mdash;
driven by one NE5532 and a pair of display drivers. Both light exactly one LED at a time, which
is the only reason they fit the power budget at all.</p>

""" + fig("meters", "Sheet 7 &mdash; detectors, display drivers and the two LED columns") + """

<h2>Why this sheet uses a driver IC</h2>
<p>A seven-segment bargraph needs seven comparators, and there are two of them. Building
fourteen comparators out of NE5532s means seven more packages and roughly <strong>56 mA</strong>
&mdash; on rails that only have about 70 mA of headroom left. It does not fit.</p>
<p>So this is the one place the module steps outside its NE5532-and-BC549 palette.
<code>U8</code> and <code>U9</code> are LM391x display drivers: ten comparators, a reference and
the LED current sinks in one 18-pin package.</p>
<p>They are pin-identical but follow different laws, which is the whole reason there are two
different part numbers. <code>U8</code> is an <strong>LM3914</strong>, whose ten steps are
evenly spaced in volts. <code>U9</code> is an <strong>LM3915</strong>, whose steps are 3 dB
apart. Gain reduction is read off a control voltage; output level is read in dB. Fitting them
the wrong way round gives two meters that both read badly.</p>

<div class="note">
  <h4>Dot mode, not bar mode</h4>
  <p>Pin 9 (<code>MODE</code>) is left open on both drivers, which selects dot mode: one LED lit
  at a time instead of a filled bar. That is a power decision before it is an aesthetic one. In
  bar mode, seven lit LEDs per meter at 4.6 mA is about <strong>64 mA</strong> of extra draw and
  the module no longer fits the 130 mA the rack allows. In dot mode the same meters cost
  <strong>9.2 mA</strong>.</p>
</div>

<h2>The reference and the LED current</h2>
<p>Each driver sets its own full-scale voltage and its own LED current from two resistors, and
both meters use the same pair.</p>
""" + table(
    ["Set by", "Value", "Result", "What it fixes"],
    [["<code>R89</code> / <code>R91</code>", "2k7", "4.6 mA",
      "LED current, <em>12.5&nbsp;/&nbsp;R</em> &mdash; every segment the same brightness"],
     ["<code>R90</code> / <code>R92</code>", "8k2", "5.05 V",
      "Full scale, <em>1.25&nbsp;&times;&nbsp;(1&nbsp;+&nbsp;R90/R89)</em>"]],
    ["r", "n", "n", ""]) + """
<p>The LED current is set by the driver, not by a series resistor per LED, so all fourteen
segments match without sorting parts. <code>RHI</code> ties to <code>REFOUT</code> and
<code>RLO</code> to ground, so each ladder spans 0 V to 5.05 V.</p>

<h2>Gain reduction &mdash; U8</h2>
<p>The control voltage <code>CTRL-B</code> rests at 0 V and swings to about &minus;10 V at full
compression, so it needs inverting before a meter can read it. That much is easy. The problem is
what happens next.</p>
<p><code>Q6</code> and <code>Q7</code> in the gain cell are an <strong>undegenerated</strong>
differential pair, so gain follows control voltage as a sigmoid, not a line. Feed that to a
meter that steps evenly in volts and the scale bunches horribly:</p>
""" + table(
    ["Segment", "Even steps in volts", "With the R93 offset"],
    [["<code>D20</code>", "0.1 dB", "1 dB"], ["<code>D21</code>", "0.5 dB", "2 dB"],
     ["<code>D22</code>", "2.0 dB", "3 dB"],  ["<code>D23</code>", "6.6 dB", "6 dB"],
     ["<code>D24</code>", "15.7 dB", "9 dB"], ["<code>D25</code>", "27.5 dB", "14 dB"],
     ["<code>D26</code>", "40.2 dB", "19 dB"]],
    ["r", "n", "n"]) + """
<p>Three of seven segments inside the first 2 dB, then a jump from 6 dB to 40 dB across the last
three. No trim setting fixes it, because the spacing is wrong, not the span.</p>
<p><code>R93</code> (18 k&Omega;) solves it by making <code>U7B</code> a <em>summing</em>
inverting stage: it subtracts a fixed offset taken from <code>U8</code>'s own reference before
the signal reaches the driver. The seven even voltage steps then land on the useful middle of
the sigmoid, and the scale comes out close to the classic 1/2/3/6/9/14/19 dB progression.</p>
<p>The cost is that <code>U7B</code> now sits at about <strong>&minus;2.1 V</strong> with no
compression happening. <code>R94</code> and <code>D12</code> clamp the driver input at
&minus;0.7 V so that idle offset never reaches <code>U8</code>. <code>RV7</code> trims the
slope, which moves the whole scale together.</p>

<h2>Output level &mdash; U9</h2>
<p>The level meter watches <code>OUT-A</code>, the makeup amplifier's output. That is the last
point in the signal path that is still a low-impedance op-amp output: metering after
<code>R28</code> would put the meter's input divider across the module's balanced output and
unbalance it slightly.</p>
<p><code>U7A</code> is a precision peak detector. <code>D11</code> sits <em>inside</em> the
feedback loop, so the op amp servos out the diode's own forward drop and the detector stays
accurate down to a few millivolts &mdash; a bare diode and capacitor would read about 0.6 V low.
<code>R87</code> limits the surge into <code>C35</code> as it charges.</p>
""" + table(
    ["Set by", "Value", "Result"],
    [["<code>R87</code> &times; <code>C35</code>", "1k &times; 2&micro;2", "2.2 ms attack &mdash; fast enough to catch peaks"],
     ["<code>R88</code> &times; <code>C35</code>", "100k &times; 2&micro;2", "220 ms decay &mdash; slow enough to read"]],
    ["r", "n", ""]) + """
<p>From there <code>U9</code>'s 3 dB steps give a seven-segment scale spanning
<strong>18 dB</strong>. Outputs 4&ndash;10 drive the LEDs, so the top segment is full scale and
the bottom is 18 dB below it; outputs 1&ndash;3 are unused.</p>

<h2>Setting the two trimmers</h2>
<p>Neither meter is calibrated by calculation &mdash; both have a trimmer, and both want a
signal generator and a voltmeter.</p>
<ul>
  <li><strong><code>RV8</code>, level.</strong> Feed the module a steady tone at whatever level
  you want the top LED to mean &mdash; +18 dBu is the usual choice, leaving about 2 dB before
  <code>U2A</code> clips. Adjust <code>RV8</code> until <code>D36</code> just lights. The scale
  below it then reads +15, +12, +9, +6, +3 and 0 dBu.</li>
  <li><strong><code>RV7</code>, gain reduction.</strong> Drive the compressor hard enough to
  produce a known amount of gain reduction, measured as the difference in output level with the
  threshold backed off and applied. Adjust <code>RV7</code> until the segment you want lights.
  Setting it at 19 dB on <code>D26</code> puts the rest of the scale where the table above
  says.</li>
</ul>

<h2>What this costs the supply</h2>
""" + table(
    ["Draw", "+16 V", "&minus;16 V"],
    [["<code>U7</code> NE5532", "8 mA", "8 mA"],
     ["<code>U8</code> + <code>U9</code> quiescent", "~12 mA", "&mdash;"],
     ["Two lit LEDs at 4.6 mA", "9 mA", "&mdash;"],
     ["<strong>Added by this sheet</strong>", "<strong>~29 mA</strong>", "<strong>8 mA</strong>"],
     ["<strong>Module total</strong>", "<strong>~90 mA</strong>", "<strong>~70 mA</strong>"]],
    ["r", "n", "n"]) + """
<p>Against the 130 mA per rail the 500-series specification allows, that still fits &mdash; but
the +16 V margin is now about 40 mA rather than 70 mA. The driver quiescent figures are
datasheet typicals; this is the one number in the project worth measuring on the bench rather
than trusting.</p>

<div class="note warn">
  <h4>Still open</h4>
  <p>Nothing here has been built or simulated. The gain-reduction scale in particular comes from
  a model of the steering pair, not from measurement &mdash; the shape is right, but expect to
  move <code>RV7</code> and to redraw the panel legend once a real one exists. <code>LED1</code>
  on sheet 6 is now superseded by this sheet and has no hole in the panel.</p>
</div>
""")


# ============================================================ 08 PANEL
PAGES['panel.html'] = ("The front panel", """
<p class="eyebrow">Practical</p>
<h1>The front panel</h1>
<p class="lede">Nine functions, two meters and two mounting screws, in a space 38 mm wide.
Almost every decision on this panel is a consequence of that.</p>

""" + pic("panel-mockup.svg", "Front panel &mdash; toggle layout, anodised finish") + """

<h2>What the panel has to fit</h2>
<p>A 500-series module is 1.500&Prime; &times; 5.250&Prime; &mdash; <strong>38.10 &times;
133.35 mm</strong>. Two mounting screws sit on the vertical centreline, 125.43 mm apart, which
puts them 3.96 mm from each end. They are countersunk, so a screw head occupies a 5.72 mm
circle in the middle of the panel top and bottom.</p>
<p>That leaves a usable strip roughly 34 mm wide and 120 mm tall, interrupted at both ends.
Into it go five knobs, four switch functions, fourteen meter LEDs and the legends for all of
it. There is no arrangement where everything is comfortable; every layout below trades one
thing for another.</p>

<h2>The controls</h2>
""" + table(
    ["Control", "Ref", "What it does", "More"],
    [["THRESHOLD", "RV3", "How loud before compression starts", '<a href="sidechain.html">Sidechain</a>'],
     ["RATIO", "RV4", "How much gain reduction per dB over threshold", '<a href="sidechain.html">Sidechain</a>'],
     ["ATTACK", "RV5", "How fast it clamps down, 2.7&ndash;50 ms", '<a href="sidechain.html">Sidechain</a>'],
     ["RELEASE", "RV6", "How fast it lets go, 47 ms&ndash;2.2 s", '<a href="sidechain.html">Sidechain</a>'],
     ["MAKEUP", "RV2", "Level put back after compression, 0 to +21 dB", '<a href="output.html">Output</a>'],
     ["BYPASS", "SW1", "Hard bypass &mdash; rack straight through", '<a href="output.html">Output</a>'],
     ["HPF", "SW3", "Defeats the 72 Hz sidechain filter", '<a href="sidechain.html">Sidechain</a>'],
     ["KEY", "SW2", "Detector listens here, or to the aux input", '<a href="sidechain.html">Sidechain</a>'],
     ["LINK", "SW4", "Ties this detector to the module beside it", '<a href="sidechain.html">Sidechain</a>']],
    ["", "r", "", ""]) + """

<h2>Reading the meters</h2>
<p>Two seven-segment bargraphs sit at the top, in a recessed window so they read against the
panel.</p>
<ul>
  <li><strong>GR</strong> fills <em>downward</em> from the top as the compressor clamps. More
      lit means more gain reduction. Dark means it is not working &mdash; either the threshold
      is above the signal or nothing is getting through.</li>
  <li><strong>LVL</strong> fills <em>upward</em> from the bottom, green through amber to red,
      showing what is leaving the module.</li>
</ul>
<div class="note">
  <h4>The meters have a circuit now</h4>
  <p>The fourteen LEDs are driven by <a href="meters.html">sheet 7</a>: two LM391x display
  drivers in dot mode, fed by a peak detector and a level shifter. They add about 29 mA to the
  +16 V rail, taking the module to roughly 90 mA of the 130 mA the rack allows.</p>
</div>

<h2>Three layouts</h2>
<p>The same nine functions, arranged three ways. The generator builds any of them from one
definition, so choosing is a command-line flag rather than a redraw.</p>
""" + table(
    ["Layout", "Switches", "Holes", "The trade"],
    [["<code>pull</code>", "None &mdash; every switch is a pull on a pot; LINK is an internal jumper",
      "21", "Fewest parts and cheapest to build. Bypass is slow and uncertain, and you cannot bypass without touching the makeup knob."],
     ["<code>toggle</code>", "Four toggles flanking THRESHOLD and RATIO",
      "25", "Every function is one positive movement, nothing hidden, bypass instant. Most parts of the three."],
     ["<code>concentric</code>", "Lit BYPASS button and two toggles; LINK on a pull",
      "22", "Dual-concentric knobs free the space, but they are dearer, harder to source, and their inner shafts cannot carry a printed scale."]],
    ["r", "", "n", ""]) + """

<h3>Why the switches sit where they do</h3>
<p>On the <code>toggle</code> layout they flank the knob they belong to: <strong>HPF</strong>
and <strong>KEY</strong> either side of THRESHOLD, because all three are sidechain controls you
adjust together; <strong>LINK</strong> and <strong>BYPASS</strong> either side of RATIO,
because both are set once and then left.</p>
<p>That grouping is the whole argument for this layout. A switch next to the control it
modifies needs no label to explain the relationship.</p>

<div class="note good">
  <h4>This is the layout the schematic already matches</h4>
  <p>The <code>toggle</code> layout uses four discrete switches &mdash; exactly what
  <code>SW1</code>&ndash;<code>SW4</code> are in <code>design.py</code>. The other two need the
  schematic changing: <code>pull</code> wants pull-switch pots, and <code>concentric</code>
  wants dual-concentric pots plus a latching pushbutton.</p>
</div>

<h2>Small things that took several attempts</h2>
<ul>
  <li><strong>ATTACK and RELEASE share a row</strong>, so they get a smaller legend and no
      printed numerals. Two full scales put their <code>0</code> and <code>10</code> on top of
      each other in the gap between the knobs.</li>
  <li><strong>Nothing is printed at 12 o'clock</strong> on a knob scale. On a panel this tight
      the top of one scale lands in the label of the control above it, every time.</li>
  <li><strong>The countersinks own the centreline</strong> at both ends. Anything near the top
      or bottom has to sit off-centre, which is why BYPASS is where it is on the
      <code>concentric</code> layout.</li>
</ul>

<h2>The other finish</h2>
<p>A second, lighter treatment exists: flat graphic rather than skeuomorphic, printed dot
scales with 0&ndash;10 numerals, thin metal bat toggles. Same holes, same drawing, same DXF
&mdash; only the artwork differs.</p>

""" + pic("panel-bone.svg", "The same layout in the bone finish") + """

<h2>Machining</h2>
<p>The drawing below is 1:1 and dimensioned. A full drill schedule &mdash; every hole with its
coordinates, diameter and the hardware it suits &mdash; is in <code>panel/README.md</code> in
the repository, alongside the DXF.</p>

""" + pic("panel-drawing.svg", "1:1 technical drawing with all hole positions") + """

<div class="note warn">
  <h4>Before you have one made</h4>
  <p>Hole sizes assume a 9 mm pot bushing, a mini toggle and 2 mm LEDs. Check them against the
  parts you actually buy &mdash; bushing diameters vary between manufacturers, and half a
  millimetre is the difference between a push fit and a rattle. Depth clearance between knobs,
  switch bodies and the PCB is not modelled at all: this is a 2D drawing.</p>
</div>
""")

# ============================================================ 09 USING
PAGES['using.html'] = ("Setting up &amp; using it", """
<p class="eyebrow">Practical</p>
<h1>Setting up and using it</h1>
<p class="lede">Bring-up order, what each control does, and what to measure if something is
wrong.</p>

<h2>The controls</h2>
""" + table(
    ["Control", "Ref", "What it does"],
    [["Threshold", "RV3", "How loud the signal must be before compression starts. Clockwise = lower threshold = more compression."],
     ["Ratio", "RV4", "How much gain reduction per dB over threshold. Clockwise = harder."],
     ["Attack", "RV5", "How fast it clamps down. 2.7&ndash;50 ms."],
     ["Release", "RV6", "How fast it lets go. 47 ms&ndash;2.2 s."],
     ["Makeup", "RV2", "Level put back after compression. 0 to +21 dB."],
     ["Unity trim", "RV1", "Set once at bring-up. Not a performance control."],
     ["Bypass", "SW1", "Hard bypass &mdash; audio goes straight through the rack."],
     ["Key int/ext", "SW2", "Detector listens to this channel, or to the aux input."],
     ["HPF defeat", "SW3", "Shorts out the 72 Hz detector filter."],
     ["Link", "SW4", "Ties this detector to the other module on pin 6."]],
    ["", "r", ""]) + """

<div class="note">
  <h4>Threshold and ratio interact &mdash; this is normal</h4>
  <p>Because this is a feedback compressor, ratio also nudges where compression starts, and
  threshold also affects the apparent ratio. That is inherent to the topology, not a fault. If
  you want a dialled, independent 4:1 you want a feedforward design with a log detector, which
  is a different module.</p>
</div>

<h2>Bring-up, in order</h2>
<p>Do steps 1&ndash;5 on the bench with a current-limited supply, no signal, before the card
ever goes near a rack.</p>
<ol>
  <li><strong>Rails.</strong> Confirm pin 12 is +16 V and pin 14 is &minus;16 V at the
      backplane <em>before</em> inserting. Check the drop across <code>R50</code> and
      <code>R51</code> &mdash; more than 1 V (100 mA) with no signal means something is wrong.</li>
  <li><strong>References.</strong> <code>VBIAS</code> = 2.23 V &plusmn;0.05.
      <code>&minus;5V1</code> = &minus;5.1 V &plusmn;0.15. <code>VREF5</code> = 5.49 V,
      <code>VREFA</code> = 5.19 V.</li>
  <li><strong>Tail current.</strong> Measure across <code>R18</code>: about 4.45 V, i.e. ~3 mA.
      Anywhere from 2.7 to 3.2 mA is fine &mdash; gain is set by the steering ratio, not by this
      current.</li>
  <li><strong>Cell operating points.</strong> <code>CP</code> and <code>CN</code> should both
      read about 9.1 V and should be within 100 mV <em>of each other</em>. A large difference
      means the <code>Q6</code>&ndash;<code>Q9</code> quad is not matched.</li>
  <li><strong>Steering at rest.</strong> With no signal, <code>STB</code> should sit roughly
      150 mV <em>above</em> <code>STA</code>. If it sits below, the module is compressing at
      idle &mdash; check <code>R61</code>.</li>
  <li><strong>Unity trim.</strong> Feed +4 dBu at 1 kHz, makeup fully down, threshold fully
      anticlockwise so nothing is compressing. Adjust <code>RV1</code> for +4 dBu out.</li>
  <li><strong>Threshold sweep.</strong> Still at +4 dBu, ratio at maximum, bring threshold up
      until the LED just lights. Raise the input and the output should start to hold. Sweep
      attack and release and watch the LED's decay track.</li>
  <li><strong>Link check.</strong> With two modules and <code>SW4</code> closed on both,
      driving one channel only should pull <em>both</em> down by about half as much as that
      channel alone would move. That halving is the averaging bus working.</li>
</ol>

<h2>If something is wrong</h2>
""" + table(
    ["Symptom", "Likely cause"],
    [["Compressing with no signal", "<code>VREFA</code> too high, or U4 bias current &mdash; see the TL072 note"],
     ["No compression at any setting", "Check <code>STB</code> moves when you feed signal; check <code>D7</code> orientation"],
     ["Audible thump on fast attack", "<code>R21</code>&ndash;<code>R24</code> not matched"],
     ["Poor common-mode rejection", "<code>R1</code>&ndash;<code>R4</code> not matched to 0.1%"],
     ["Hum", "More than one connection between AGND and PGND &mdash; only <code>R48</code> should join them"],
     ["Cannot reach unity gain", "Check <code>R8</code> is 75 &Omega; &mdash; an early revision specified 47 &Omega;"],
     ["Release much shorter than expected", "<code>C15</code> leaky &mdash; it must be film, not electrolytic"],
     ["Gain drifts when warm", "Transistor quad not thermally bonded"]],
    ["", ""]) + """

<h2>Project files</h2>
<ul>
  <li><code>kicad/</code> &mdash; the KiCad project. Open the <code>.kicad_pro</code> in
      KiCad 9; it holds seven sheets.</li>
  <li><code>tools/design.py</code> &mdash; the authoritative netlist as data.
      The schematic is generated and verified against it.</li>
  <li><code>panel/</code> &mdash; the faceplate generator: mockups, a 1:1 drawing and DXF.</li>
  <li><code>docs/</code> &mdash; this site. Rebuild the pages with
      <code>python3 _build.py</code>, and the viewer data with <code>python3 _data.py</code>
      after any schematic change.</li>
</ul>
""")


# ============================================================ write
if __name__ == '__main__':
    import shutil
    here = os.path.dirname(os.path.abspath(__file__))
    # panel artwork is generated next door; copy it rather than keep a second copy by hand
    for src, dst in [('faceplate-mockup.svg', 'panel-mockup.svg'),
                     ('faceplate-mockup-bone.svg', 'panel-bone.svg'),
                     ('faceplate-drawing.svg', 'panel-drawing.svg')]:
        s_path = os.path.join(here, '..', 'panel', src)
        if os.path.exists(s_path):
            shutil.copyfile(s_path, os.path.join(here, 'img', dst))
            print('copied', dst)
    for fname in ORDER:
        title, body = PAGES[fname]
        open(os.path.join(here, fname), 'w').write(shell(fname, title, body))
        print('wrote', fname)
