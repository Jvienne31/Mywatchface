#!/usr/bin/env python3
"""Génère le cadran Race : watchface.xml (Watch Face Format v4) + aperçus SVG.

Le XML contient beaucoup de motifs répétitifs (12 chiffres d'heure, 60 graduations,
7 jours x 5 langues...) : on le décrit ici une seule fois. Chaque primitive émet à la fois
l'élément WFF et son équivalent SVG, rendu avec une heure et des données d'exemple, pour
contrôler la mise en page sans montre.

    python3 race/tools/generate.py          # écrit watchface.xml + tools/preview*.svg
    node race/tools/render-preview.mjs      # SVG -> PNG (preview.png du paquet)

Ne pas éditer watchface.xml à la main : modifier ce script puis le relancer.
"""

import math
import os
import struct
import zlib
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "src", "main", "res")

W = 438
C = W / 2

# ---------------------------------------------------------------------------
# Personnalisation
# ---------------------------------------------------------------------------

# Couleur principale (cadran) : [vive, sombre]
MAIN = [
    ("col_cyan", "#22D8EE", "#06535E"),
    ("col_vert", "#4DF07A", "#0D5C26"),
    ("col_orange", "#FF9C1A", "#6E3200"),
    ("col_jaune", "#F2E01E", "#5E5200"),
    ("col_rouge", "#FF4040", "#6A0808"),
    ("col_bleu", "#3F8CFF", "#0B2A66"),
    ("col_violet", "#B270FF", "#3C1470"),
    ("col_rose", "#FF5FB4", "#6A1046"),
    ("col_lime", "#C8FF3A", "#456600"),
    ("col_blanc", "#E6ECF2", "#4A535C"),
]
# Couleur secondaire (jauges des compteurs) : les 10 précédentes + 3
SECOND = MAIN + [
    ("col_turquoise", "#2CE6B4", "#0B5A45"),
    ("col_or", "#E8C063", "#5C4415"),
    ("col_gris", "#A3AEBA", "#353C44"),
]

# Jours, lundi en premier
DAYS = [
    ("lang_fr", ["LUN", "MAR", "MER", "JEU", "VEN", "SAM", "DIM"]),
    ("lang_en", ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]),
    ("lang_de", ["MO", "DI", "MI", "DO", "FR", "SA", "SO"]),
    ("lang_es", ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]),
    ("lang_it", ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]),
]

M0, M1 = "[CONFIGURATION.main.0]", "[CONFIGURATION.main.1]"
S0, S1 = "[CONFIGURATION.second.0]", "[CONFIGURATION.second.1]"

OSWALD = "oswald_semibold"
CHAKRA = "chakrapetch_semibold"

# ---------------------------------------------------------------------------
# Données d'exemple pour l'aperçu SVG (l'heure de PREVIEW_TIME)
# ---------------------------------------------------------------------------

SAMPLE = {
    "hour": 10, "minute": 8, "second": 37, "ampm": "AM",
    "hr": 72, "battery": 86, "steps": 6420, "step_pct": 64,
    "dow_idx": 1,  # mardi (lundi = 0)
    "day": 23, "month": "SEPT", "slot1": "07:24",
}
DEFAULT_COLORS = {M0: MAIN[0][1], M1: MAIN[0][2], S0: SECOND[0][1], S1: SECOND[0][2]}

# ---------------------------------------------------------------------------
# Géométrie
# ---------------------------------------------------------------------------

R_HOURS = 166          # rayon du centre des chiffres d'heure
R_SECONDS = 112        # anneau des secondes
COCKPIT_C = (C, 522)   # le cockpit est un grand disque dont on ne voit que le haut
COCKPIT_R = 326
HUMP_C = (C, 212)      # bosse de la batterie
HUMP_R = 38
LEFT_C = (124, 312)    # compteur cardio
RIGHT_C = (314, 312)   # compteur date
DIAL_R = 70
STEP_C = (C, 386)      # compteur des pas
STEP_R = 40

HR_START, HR_SWEEP, HR_MIN, HR_MAX = 200, 250, 40, 220
DAY_SEG = 360 / 7
DAY_BASE = -1.5 * DAY_SEG     # lundi centré à -51°, mardi en haut
STEP_START, STEP_SWEEP = 225, 270


def polar(cx, cy, r, a):
    t = math.radians(a)
    return cx + r * math.sin(t), cy - r * math.cos(t)


def f(v):
    """Nombre compact pour le XML/SVG."""
    v = round(v, 2)
    return str(int(v)) if v == int(v) else str(v)


# ---------------------------------------------------------------------------
# Émetteur double XML / SVG
# ---------------------------------------------------------------------------

class Out:
    def __init__(self):
        self.xml = []
        self.svg = {"normal": [], "ambient": []}
        self.defs = []
        self.depth = 2
        self.mode_stack = [("both", None)]  # visibilité courante dans l'aperçu
        self.origin = [(0, 0)]  # les enfants d'un Group sont relatifs à son coin
        self._gid = 0

    # --- XML -----------------------------------------------------------
    def x(self, line):
        self.xml.append("  " * self.depth + line)

    def open(self, line):
        self.x(line)
        self.depth += 1

    def close(self, line):
        self.depth -= 1
        self.x(line)

    def comment(self, text):
        self.xml.append("")
        self.x(f"<!-- {text} -->")

    # --- SVG -----------------------------------------------------------
    def s(self, frag, show="both"):
        """show : both / normal / ambient — dans quel(s) aperçu(s) dessiner."""
        eff = show
        for m, _ in self.mode_stack:
            if m != "both":
                if eff == "both":
                    eff = m
                elif eff != m:
                    return
        if eff in ("both", "normal"):
            self.svg["normal"].append(frag)
        if eff in ("both", "ambient"):
            self.svg["ambient"].append(frag)

    def gid(self, prefix):
        self._gid += 1
        return f"{prefix}{self._gid}"


O = Out()


def col(c):
    """Couleur WFF -> couleur SVG (valeurs par défaut des réglages)."""
    c = DEFAULT_COLORS.get(c, c)
    if len(c) == 9:  # #AARRGGBB
        a = int(c[1:3], 16) / 255
        return f"rgba({int(c[3:5], 16)},{int(c[5:7], 16)},{int(c[7:9], 16)},{a:.3f})"
    return c


def rel(x, y):
    """Coordonnées absolues -> relatives au Group (ou à l'emplacement) englobant."""
    ox, oy = O.origin[-1]
    return x - ox, y - oy


def variant(show):
    """Éléments visibles seulement en mode normal ou seulement en AOD."""
    if show == "normal":
        O.x('<Variant mode="AMBIENT" target="alpha" value="0" />')


def alpha_attr(show, alpha=None):
    if show == "ambient":
        return ' alpha="0"'
    if alpha is not None:
        return f' alpha="{alpha}"'
    return ""


def ambient_on(show, alpha=255):
    if show == "ambient":
        O.x(f'<Variant mode="AMBIENT" target="alpha" value="{alpha}" />')


# ---------------------------------------------------------------------------
# Primitives de dessin (coordonnées absolues dans la toile 438 x 438)
# ---------------------------------------------------------------------------

def draw_open(show="both", x=0, y=0, w=W, h=W, angle_expr=None, svg_angle=0, pivot=None):
    rx, ry = rel(x, y)
    attrs = f'x="{f(rx)}" y="{f(ry)}" width="{f(w)}" height="{f(h)}"'
    if pivot:
        attrs += f' pivotX="{pivot[0]:.4f}" pivotY="{pivot[1]:.4f}"'
    O.open(f"<PartDraw {attrs}{alpha_attr(show)}>")
    if angle_expr:
        O.x(f'<Transform target="angle" value="{angle_expr}" />')
    O._draw = (x, y)
    if svg_angle:
        px = x + w * (pivot[0] if pivot else 0.5)
        py = y + h * (pivot[1] if pivot else 0.5)
        O.s(f'<g transform="rotate({f(svg_angle)} {f(px)} {f(py)})">', show)
    else:
        O.s("<g>", show)
    O.mode_stack.append((show, None))


def draw_close(show="both"):
    variant(show)
    ambient_on(show)
    O.mode_stack.pop()
    O.s("</g>", show)
    O.close("</PartDraw>")


def _rel(px, py):
    ox, oy = O._draw
    return px - ox, py - oy


def stroke_xml(color, th, cap="BUTT", dash=None, phase=None):
    extra = f' cap="{cap}"' if cap != "BUTT" else ""
    if dash:
        extra += f' dashIntervals="{dash}"'
    if phase is not None:
        extra += f' dashPhase="{f(phase)}"'
    return f'<Stroke color="{color}" thickness="{f(th)}"{extra} />'


def svg_stroke(color, th, cap="BUTT", dash=None, phase=None):
    s = f'fill="none" stroke="{col(color)}" stroke-width="{f(th)}"'
    if cap == "ROUND":
        s += ' stroke-linecap="round"'
    if dash:
        s += f' stroke-dasharray="{dash}"'
    if phase is not None:
        s += f' stroke-dashoffset="{f(phase)}"'
    return s


def circle(cx, cy, r, fill=None, stroke=None, th=1, gradient=None):
    """Disque (Ellipse) avec remplissage uni ou dégradé, et/ou contour."""
    rx, ry = _rel(cx - r, cy - r)
    O.open(f'<Ellipse x="{f(rx)}" y="{f(ry)}" width="{f(2 * r)}" height="{f(2 * r)}">')
    svg_fill = "none"
    if fill:
        if gradient:
            kind, g = gradient
            O.open(f'<Fill color="{fill}">')
            gid = O.gid("g")
            if kind == "radial":
                gx, gy = _rel(g["cx"], g["cy"])
                O.x(f'<RadialGradient centerX="{f(gx)}" centerY="{f(gy)}" radius="{f(g["r"])}" '
                    f'colors="{g["colors"]}" positions="{g["pos"]}" />')
                stops = _stops(g)
                O.defs.append(f'<radialGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                              f'cx="{f(g["cx"])}" cy="{f(g["cy"])}" r="{f(g["r"])}">{stops}</radialGradient>')
            else:
                x1, y1 = _rel(g["x1"], g["y1"])
                x2, y2 = _rel(g["x2"], g["y2"])
                O.x(f'<LinearGradient startX="{f(x1)}" startY="{f(y1)}" endX="{f(x2)}" endY="{f(y2)}" '
                    f'colors="{g["colors"]}" positions="{g["pos"]}" />')
                stops = _stops(g)
                O.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                              f'x1="{f(g["x1"])}" y1="{f(g["y1"])}" x2="{f(g["x2"])}" y2="{f(g["y2"])}">'
                              f'{stops}</linearGradient>')
            O.close("</Fill>")
            svg_fill = f"url(#{gid})"
        else:
            O.x(f'<Fill color="{fill}" />')
            svg_fill = col(fill)
    if stroke:
        O.x(stroke_xml(stroke, th))
    O.close("</Ellipse>")
    st = f' stroke="{col(stroke)}" stroke-width="{f(th)}"' if stroke else ""
    O.s(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{svg_fill}"{st} />')


def _stops(g):
    colors = g["colors"].split()
    if len(colors) == 1:  # référence à une configuration entière : [CONFIGURATION.main]
        name = colors[0].strip("[]").split(".")[1]
        colors = [f"[CONFIGURATION.{name}.0]", f"[CONFIGURATION.{name}.1]"]
    return "".join(f'<stop offset="{p}" stop-color="{col(c)}" />'
                   for c, p in zip(colors, g["pos"].split()))


def arc(cx, cy, r, a0, a1, color, th, cap="BUTT", dash=None, phase=None,
        end_expr=None, start_expr=None, svg_a0=None, svg_a1=None):
    rx, ry = _rel(cx, cy)
    O.open(f'<Arc centerX="{f(rx)}" centerY="{f(ry)}" width="{f(2 * r)}" height="{f(2 * r)}" '
           f'startAngle="{f(a0)}" endAngle="{f(a1)}" direction="CLOCKWISE">')
    O.x(stroke_xml(color, th, cap, dash, phase))
    if start_expr:
        O.x(f'<Transform target="startAngle" value="{escape(start_expr)}" />')
    if end_expr:
        O.x(f'<Transform target="endAngle" value="{escape(end_expr)}" />')
    O.close("</Arc>")
    s0 = a0 if svg_a0 is None else svg_a0
    s1 = a1 if svg_a1 is None else svg_a1
    if s1 - s0 <= 0.01:
        return
    O.s(f'<path d="{_arc_path(cx, cy, r, s0, s1)}" {svg_stroke(color, th, cap, dash, phase)} />')


def _arc_path(cx, cy, r, a0, a1):
    if a1 - a0 >= 359.99:
        x0, y0 = polar(cx, cy, r, a0)
        xm, ym = polar(cx, cy, r, a0 + 180)
        return (f"M {f(x0)} {f(y0)} A {f(r)} {f(r)} 0 1 1 {f(xm)} {f(ym)} "
                f"A {f(r)} {f(r)} 0 1 1 {f(x0)} {f(y0)}")
    x0, y0 = polar(cx, cy, r, a0)
    x1, y1 = polar(cx, cy, r, a1)
    large = 1 if a1 - a0 > 180 else 0
    return f"M {f(x0)} {f(y0)} A {f(r)} {f(r)} 0 {large} 1 {f(x1)} {f(y1)}"


def ticks(cx, cy, r, count, a0, sweep, length, th, color, closed=True):
    """Graduations régulières : un arc en pointillés (une seule primitive au lieu de N lignes)."""
    circ = 2 * math.pi * r
    step = circ * (sweep / 360) / (count if closed else count - 1)
    half = th / 2 / circ * 360  # recentre le premier trait sur a0
    end = a0 + sweep + (0 if closed else half * 2)
    arc(cx, cy, r, a0 - half, end - half, color, length,
        dash=f"{f(th)} {f(step - th)}")


def line(x1, y1, x2, y2, color, th, cap="ROUND"):
    a, b = _rel(x1, y1)
    c_, d = _rel(x2, y2)
    O.open(f'<Line startX="{f(a)}" startY="{f(b)}" endX="{f(c_)}" endY="{f(d)}">')
    O.x(stroke_xml(color, th, cap))
    O.close("</Line>")
    O.s(f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" {svg_stroke(color, th, cap)} />')


def rrect(x, y, w, h, r, fill, stroke=None, th=1):
    a, b = _rel(x, y)
    O.open(f'<RoundRectangle x="{f(a)}" y="{f(b)}" width="{f(w)}" height="{f(h)}" '
           f'cornerRadiusX="{f(r)}" cornerRadiusY="{f(r)}">')
    O.x(f'<Fill color="{fill}" />')
    if stroke:
        O.x(stroke_xml(stroke, th))
    O.close("</RoundRectangle>")
    st = f' stroke="{col(stroke)}" stroke-width="{f(th)}"' if stroke else ""
    O.s(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(r)}" '
        f'fill="{col(fill)}"{st} />')


def text(x, y, w, h, content, sample, font, size, color, show="both", alpha=None,
         align="CENTER", spacing=None, angle=None, pivot=None, upper=False):
    """PartText. content : texte fixe, ou ('expr', expression) pour un Template."""
    rx, ry = rel(x, y)
    attrs = f'x="{f(rx)}" y="{f(ry)}" width="{f(w)}" height="{f(h)}"'
    if angle is not None:
        attrs += f' angle="{f(angle)}"'
    if pivot:
        attrs += f' pivotX="{pivot[0]:.4f}" pivotY="{pivot[1]:.4f}"'
    O.open(f"<PartText {attrs}{alpha_attr(show, alpha)}>")
    O.open(f'<Text align="{align}" ellipsis="TRUE" maxLines="1">')
    sp = f' letterSpacing="{spacing}"' if spacing else ""
    if isinstance(content, tuple):
        inner = (f'<Template><![CDATA[%s]]><Parameter expression="{escape(content[1])}" />'
                 f"</Template>")
        if upper:
            inner = f"<Upper>{inner}</Upper>"
    else:
        inner = escape(content)
    O.x(f'<Font family="{font}" size="{f(size)}" color="{color}"{sp}>{inner}</Font>')
    O.close("</Text>")
    variant(show)
    ambient_on(show, 255 if alpha is None else alpha)
    O.close("</PartText>")

    anchor = {"CENTER": "middle", "START": "start", "END": "end"}[align]
    tx = {"CENTER": x + w / 2, "START": x, "END": x + w}[align]
    op = f' fill-opacity="{alpha / 255:.3f}"' if alpha is not None else ""
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    tr = ""
    if angle is not None:
        px = x + w * (pivot[0] if pivot else 0.5)
        py = y + h * (pivot[1] if pivot else 0.5)
        tr = f' transform="rotate({f(angle)} {f(px)} {f(py)})"'
    fam = "Oswald" if font == OSWALD else "ChakraPetch"
    O.s(f'<text x="{f(tx)}" y="{f(y + h / 2)}" font-family="{fam}" font-size="{f(size)}" '
        f'fill="{col(color)}"{op}{ls} text-anchor="{anchor}" dominant-baseline="central"{tr}>'
        f"{escape(str(sample))}</text>", show)


def group_open(name, x=0, y=0, w=W, h=W, angle=None, angle_expr=None, svg_angle=None,
               show="both", launch=None):
    rx, ry = rel(x, y)
    attrs = f'name="{name}" x="{f(rx)}" y="{f(ry)}" width="{f(w)}" height="{f(h)}"'
    if angle is not None:
        attrs += f' angle="{f(angle)}"'
    O.open(f"<Group {attrs}{alpha_attr(show)}>")
    if launch:
        O.x(f'<Launch target="{launch}" />')
    if angle_expr:
        O.x(f'<Transform target="angle" value="{escape(angle_expr)}" />')
    a = svg_angle if svg_angle is not None else angle
    if a:
        O.s(f'<g transform="rotate({f(a)} {f(x + w / 2)} {f(y + h / 2)})">', show)
    else:
        O.s("<g>", show)
    O.mode_stack.append((show, None))
    O.origin.append((x, y))


def group_close(show="both"):
    variant(show)
    ambient_on(show)
    O.origin.pop()
    O.mode_stack.pop()
    O.s("</g>", show)
    O.close("</Group>")


def image(x, y, w, h, resource, show="both", svg_href=None):
    rx, ry = rel(x, y)
    O.open(f'<PartImage x="{f(rx)}" y="{f(ry)}" width="{f(w)}" height="{f(h)}"{alpha_attr(show)}>')
    O.x(f'<Image resource="{resource}" />')
    variant(show)
    ambient_on(show)
    O.close("</PartImage>")
    if svg_href:
        O.s(f'<image x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" href="{svg_href}" />', show)


def list_config(cid, options):
    """options : liste de callables ; seule l'option 0 est rendue dans l'aperçu."""
    O.open(f'<ListConfiguration id="{cid}">')
    for i, fn in enumerate(options):
        O.open(f'<ListOption id="{i}">')  # un seul enfant autorisé : on enveloppe
        O.mode_stack.append(("both", None) if i == 0 else ("none", None))
        ox, oy = O.origin[-1]
        group_open(f"{cid}_{i}", ox, oy)
        fn()
        group_close()
        O.mode_stack.pop()
        O.close("</ListOption>")
    O.close("</ListConfiguration>")


def condition(expr_name, expr, then_fn, else_fn, sample_true):
    O.open("<Condition>")
    O.open("<Expressions>")
    O.x(f'<Expression name="{expr_name}"><![CDATA[{expr}]]></Expression>')
    O.close("</Expressions>")
    O.open(f'<Compare expression="{expr_name}">')
    O.mode_stack.append(("both", None) if sample_true else ("none", None))
    then_fn()
    O.mode_stack.pop()
    O.close("</Compare>")
    O.open("<Default>")
    O.mode_stack.append(("none", None) if sample_true else ("both", None))
    else_fn()
    O.mode_stack.pop()
    O.close("</Default>")
    O.close("</Condition>")


# ---------------------------------------------------------------------------
# Couches du cadran
# ---------------------------------------------------------------------------

def tangential_label(cx, cy, r, a, label, sample, font, size, color, w=40, h=16,
                     show="both", alpha=None):
    """Étiquette posée sur un cercle, tangente, toujours lisible (retournée en bas)."""
    flip = 90 < (a % 360) < 270
    gx, gy, gs = cx - r - h, cy - r - h, 2 * (r + h)
    group_open(f"lbl_{O.gid('l')}", gx, gy, gs, gs, angle=(a - 180 if flip else a), show=show)
    ty = gy + (gs - h if flip else 0)
    text(gx + gs / 2 - w / 2, ty, w, h, label, sample, font, size, color, alpha=alpha)
    group_close(show)


def layer_dial():
    O.comment("Fond du cadran : dégradé radial de la couleur principale + vignette")
    draw_open("normal")
    circle(C, C, C, fill=M0, gradient=("radial", {"cx": C, "cy": 140, "r": 300,
                                                  "colors": "[CONFIGURATION.main]", "pos": "0 1"}))
    circle(C, C, C, fill="#00000000", gradient=("radial", {
        "cx": C, "cy": C, "r": C, "colors": "#00000000 #00000000 #B0000000", "pos": "0 0.72 1"}))
    draw_close("normal")

    O.comment("Motif sur le cadran")
    list_config("motif", [
        lambda: None,
        lambda: image(0, 0, W, W, "pattern_dots", show="normal"),
        lambda: image(0, 0, W, W, "pattern_stripes", show="normal"),
    ])


def layer_hours():
    O.comment("Disque des heures : tourne pour amener l'heure courante sous l'index")
    expr = "-30 * ([HOUR_0_11] + [MINUTE] / 60)"
    svg_a = -30 * (SAMPLE["hour"] % 12 + SAMPLE["minute"] / 60)
    group_open("hour_disk", angle_expr=expr, svg_angle=svg_a)
    w, h = 130, 104
    for k in range(1, 13):
        group_open(f"hour_{k}", angle=30 * k if k != 12 else None)
        y = C - R_HOURS - h / 2
        text(C - w / 2, y, w, h, str(k), k, OSWALD, 104, "#000000", show="normal", alpha=92)
        text(C - w / 2, y, w, h, str(k), k, OSWALD, 104, M0, show="ambient", alpha=110)
        group_close()
    group_close()


def layer_seconds():
    O.comment("Anneau des secondes (mode normal)")
    expr = "-6 * [SECOND]"
    group_open("seconds_ring", angle_expr=expr, svg_angle=-6 * SAMPLE["second"], show="normal")
    draw_open()
    arc(C, C, R_SECONDS + 4, 0, 360, "#73000000", 1.5)
    ticks(C, C, R_SECONDS, 60, 0, 360, 7, 1.4, "#8C000000")
    ticks(C, C, R_SECONDS - 1, 12, 0, 360, 10, 2.6, "#B4000000")
    draw_close()
    for i in range(12):
        group_open(f"sec_{i * 5}", angle=30 * i if i else None)
        text(C - 15, C - R_SECONDS + 9, 30, 16, f"{i * 5:02d}", f"{i * 5:02d}", CHAKRA, 13,
             "#000000", alpha=170)
        group_close()
    group_close("normal")


def layer_index():
    O.comment("Index vertical")
    draw_open()
    line(C, 6, C, HUMP_C[1] - HUMP_R, "#B4000000", 2.5, cap="BUTT")
    draw_close()
    draw_open("ambient")
    line(C, 6, C, HUMP_C[1] - HUMP_R, M0, 2, cap="BUTT")
    draw_close("ambient")


def layer_minutes():
    O.comment("Minutes : pastille à droite de l'index")
    px, py, pw, ph = 248, 70, 58, 86
    draw_open("normal")
    rrect(px, py, pw, ph, 29, "#E6101317", stroke="#3A4149", th=1.5)
    draw_close("normal")
    draw_open("ambient")
    rrect(px, py, pw, ph, 29, "#000000", stroke=M0, th=1.5)
    draw_close("ambient")
    text(px, py + 8, pw, 48, ("expr", "[MINUTE_Z]"), f"{SAMPLE['minute']:02d}",
         OSWALD, 42, "#F2F5F8")
    text(px, py + 56, pw, 18, ("expr", "[AMPM_STRING]"), SAMPLE["ampm"], CHAKRA, 12, "#8E99A5",
         spacing=1)


def layer_cockpit():
    cx, cy = COCKPIT_C
    hx, hy = HUMP_C

    O.comment("Ombre portée du cockpit")

    def shadow(a, extra):
        def fn():
            draw_open("normal")
            for (sx, sy), r0 in ((COCKPIT_C, COCKPIT_R), (HUMP_C, HUMP_R)):
                r = r0 + extra
                circle(sx, sy, r, fill="#00000000", gradient=("radial", {
                    "cx": sx, "cy": sy, "r": r,
                    "colors": f"#{a}000000 #{a}000000 #00000000", "pos": f"0 {r0 / r:.4f} 1"}))
            draw_close("normal")
        return fn
    list_config("ombre", [shadow("A6", 26), shadow("60", 14)])

    O.comment("Cockpit : grand disque sombre + bosse de la batterie")

    def cockpit(top, bottom):
        def fn():
            grad = ("linear", {"x1": 0, "y1": cy - COCKPIT_R, "x2": 0, "y2": W,
                               "colors": f"{top} {bottom}", "pos": "0 1"})
            draw_open("normal")
            circle(cx, cy, COCKPIT_R, fill=top, gradient=grad)
            circle(hx, hy, HUMP_R, fill=top, gradient=grad)
            draw_close("normal")
        return fn
    list_config("cockpit", [cockpit("#2C3137", "#0D0F12"), cockpit("#17191C", "#050607")])
    draw_open("ambient")  # en AOD : noir pur, masque le bas du disque des heures
    circle(cx, cy, COCKPIT_R, fill="#000000")
    circle(hx, hy, HUMP_R, fill="#000000")
    draw_close("ambient")

    O.comment("Arête du cockpit (aussi en AOD, où elle remplace l'aplat)")
    draw_open()
    # intersection bosse / cockpit : angle t sur la bosse, puis angle sur le cockpit
    d = cy - hy
    t = math.degrees(math.acos((COCKPIT_R ** 2 - HUMP_R ** 2 - d ** 2) / (2 * HUMP_R * d)))
    a_join = math.degrees(math.asin(HUMP_R * math.sin(math.radians(t)) / COCKPIT_R))
    arc(cx, cy, COCKPIT_R, -60, -a_join, "#4A525B", 2)
    arc(cx, cy, COCKPIT_R, a_join, 60, "#4A525B", 2)
    arc(hx, hy, HUMP_R, -t, t, "#4A525B", 2)
    draw_close()

    O.comment("Vis")
    draw_open("normal")
    for sx, sy in [(191, 262), (247, 262), (174, 412), (264, 412)]:
        circle(sx, sy, 5, fill="#15181B", stroke="#3E454D", th=1.2)
        line(sx - 3, sy + 2, sx + 3, sy - 2, "#3E454D", 1.2)
    draw_close("normal")


def layer_battery():
    hx, hy = HUMP_C
    O.comment("Batterie, dans la bosse du cockpit — un appui ouvre l'état de la batterie")
    group_open("battery", hx - HUMP_R, hy - HUMP_R, 2 * HUMP_R, 2 * HUMP_R, launch="BATTERY_STATUS")
    draw_open()
    # éclair
    line(222, 181, 215, 191, "#9AA4AF", 2)
    line(215, 191, 223, 191, "#9AA4AF", 2)
    line(223, 191, 216, 201, "#9AA4AF", 2)
    arc(hx, hy + 8, 24, -125, 125, "#2B3036", 5, cap="ROUND")
    pct = SAMPLE["battery"]
    arc(hx, hy + 8, 24, -125, 125, S0, 5, cap="ROUND",
        end_expr="-125 + 250 * [BATTERY_PERCENT] / 100", svg_a1=-125 + 250 * pct / 100)
    draw_close()
    text(hx - 20, hy + 2, 40, 22, ("expr", "[BATTERY_PERCENT]"), pct, CHAKRA, 15, "#E8EDF2")
    group_close()


def dial_base(cx, cy, r):
    """Fond du compteur (mode normal) + filet (aussi en AOD, sur noir pur)."""
    draw_open("normal")
    circle(cx, cy, r, fill="#0D0F12")
    draw_close("normal")
    draw_open()
    circle(cx, cy, r, stroke="#3E454D", th=2)
    draw_close()


def gauge_band(cx, cy, r, th, a0, sweep):
    arc(cx, cy, r, a0, a0 + sweep, S1, th)


def layer_heart():
    cx, cy = LEFT_C
    rb = 58
    O.comment("Compteur gauche : fréquence cardiaque (40-220) + conteneur de données")
    dial_base(cx, cy, DIAL_R)
    draw_open("normal")
    gauge_band(cx, cy, rb, 16, HR_START, HR_SWEEP)
    hr = SAMPLE["hr"]
    frac = (hr - HR_MIN) / (HR_MAX - HR_MIN)
    arc(cx, cy, rb, HR_START, HR_START + HR_SWEEP, S0, 16,
        end_expr=(f"{HR_START} + {HR_SWEEP} * clamp(([HEART_RATE] - {HR_MIN}) / "
                  f"{HR_MAX - HR_MIN}, 0, 1)"),
        svg_a1=HR_START + HR_SWEEP * frac)
    ticks(cx, cy, rb, 10, HR_START, HR_SWEEP, 16, 1.2, "#C8000000", closed=False)
    draw_close("normal")
    draw_open("ambient")
    arc(cx, cy, rb, HR_START, HR_START + HR_SWEEP, S0, 1.5)
    draw_close("ambient")
    n = (HR_MAX - HR_MIN) // 20
    for i in range(n + 1):
        a = HR_START + HR_SWEEP * i / n
        if i in (0, n):
            continue  # extrémités : les traits suffisent
        v = HR_MIN + 20 * i
        tangential_label(cx, cy, rb, a, str(v), v, CHAKRA, 10, "#000000", w=30, h=14,
                         show="normal", alpha=200)
    draw_open()
    line(cx - 30, cy - 6, cx + 30, cy - 6, "#3E454D", 1.2)
    draw_close()

    group_open("heart_rate", cx - 36, cy - 4, 72, 52, launch="HEALTH_HEART_RATE")
    condition("hr_ok", "[HEART_RATE] > 0",
              lambda: _hr_value(cx, cy, ("expr", "round([HEART_RATE])"), hr),
              lambda: _hr_value(cx, cy, "--", "--"), True)
    text(cx - 30, cy + 30, 60, 12, "BPM", "BPM", CHAKRA, 9, "#7D8893", spacing=1.5)
    group_close()


def _hr_value(cx, cy, content, sample):
    group_open(f"hr_{O.gid('v')}", cx - 36, cy - 4, 72, 36)
    text(cx - 36, cy - 4, 72, 36, content, sample, OSWALD, 30, "#F2F5F8")
    group_close()


def layer_date():
    cx, cy = RIGHT_C
    rb = 58
    O.comment("Compteur droit : jours de la semaine + mois et jour")
    dial_base(cx, cy, DIAL_R)
    draw_open("normal")
    gauge_band(cx, cy, rb, 18, DAY_BASE, 360)
    # Segment du jour courant. [DAY_OF_WEEK] : 1 = dimanche ; idx : 0 = lundi.
    idx_expr = "(([DAY_OF_WEEK] + 5) % 7)"
    i = SAMPLE["dow_idx"]
    arc(cx, cy, rb, DAY_BASE, DAY_BASE + DAY_SEG, S0, 18,
        start_expr=f"{DAY_BASE:.4f} + {DAY_SEG:.4f} * {idx_expr}",
        end_expr=f"{DAY_BASE + DAY_SEG:.4f} + {DAY_SEG:.4f} * {idx_expr}",
        svg_a0=DAY_BASE + DAY_SEG * i, svg_a1=DAY_BASE + DAY_SEG * (i + 1))
    ticks(cx, cy, rb, 7, DAY_BASE, 360, 18, 1.6, "#0D0F12")
    draw_close("normal")
    draw_open("ambient")
    arc(cx, cy, rb, DAY_BASE, DAY_BASE + DAY_SEG, S0, 2,
        start_expr=f"{DAY_BASE:.4f} + {DAY_SEG:.4f} * {idx_expr}",
        end_expr=f"{DAY_BASE + DAY_SEG:.4f} + {DAY_SEG:.4f} * {idx_expr}",
        svg_a0=DAY_BASE + DAY_SEG * i, svg_a1=DAY_BASE + DAY_SEG * (i + 1))
    draw_close("ambient")

    def labels(names):
        def fn():
            for d, name in enumerate(names):
                a = DAY_BASE + DAY_SEG * (d + 0.5)
                tangential_label(cx, cy, rb, a, name, name, CHAKRA, 11, "#000000", w=34, h=14,
                                 show="normal", alpha=210)
        return fn
    O.comment("Noms des jours, selon la langue choisie")
    list_config("langue", [labels(names) for _, names in DAYS])

    text(cx - 36, cy - 34, 72, 24, ("expr", "[MONTH_S]"), SAMPLE["month"], CHAKRA, 15,
         "#C9D1D9", spacing=1, upper=True)
    draw_open()
    line(cx - 30, cy - 6, cx + 30, cy - 6, "#3E454D", 1.2)
    draw_close()
    text(cx - 36, cy - 4, 72, 36, ("expr", "[DAY]"), SAMPLE["day"], OSWALD, 30, "#F2F5F8")


def layer_steps():
    cx, cy = STEP_C
    O.comment("Petit compteur bas : progression des pas vers l'objectif")
    dial_base(cx, cy, STEP_R)
    draw_open("normal")
    ticks(cx, cy, 31, 10, STEP_START, STEP_SWEEP, 6, 1.4, "#5A636D", closed=False)
    pct = SAMPLE["step_pct"]
    arc(cx, cy, 25, STEP_START, STEP_START + STEP_SWEEP, S0, 3,
        end_expr=f"{STEP_START} + {STEP_SWEEP} * [STEP_PERCENT] / 100",
        svg_a1=STEP_START + STEP_SWEEP * pct / 100)
    draw_close("normal")
    text(cx - 24, cy + 12, 48, 14, ("expr", "[STEP_COUNT]"), SAMPLE["steps"], CHAKRA, 10,
         "#8E99A5")
    O.comment("Aiguille des pas")
    size = 64
    draw_open(x=cx - size / 2, y=cy - size / 2, w=size, h=size,
              angle_expr=f"{STEP_START} + {STEP_SWEEP} * [STEP_PERCENT] / 100",
              svg_angle=STEP_START + STEP_SWEEP * pct / 100)
    line(cx, cy + 6, cx, cy - 27, S0, 3)
    draw_close()
    draw_open()
    circle(cx, cy, 5, fill="#2B3036", stroke=S0, th=1.5)
    draw_close()


SLOT_TYPES_DATA = "SHORT_TEXT RANGED_VALUE GOAL_PROGRESS LONG_TEXT EMPTY"
SLOT_TYPES_SHORTCUT = "SMALL_IMAGE MONOCHROMATIC_IMAGE SHORT_TEXT EMPTY"


def layer_complications():
    cx, cy = LEFT_C
    O.comment("Complication 1 — conteneur de données, en haut du compteur cardio")
    x, y, w, h = cx - 38, cy - 36, 76, 28
    O.open(f'<ComplicationSlot slotId="1" x="{f(x)}" y="{f(y)}" width="{w}" height="{h}" '
           f'supportedTypes="{SLOT_TYPES_DATA}" displayName="slot_data">')
    O.x('<DefaultProviderPolicy defaultSystemProvider="SUNRISE_SUNSET" '
        'defaultSystemProviderType="SHORT_TEXT" />')
    O.x(f'<BoundingBox x="0" y="0" width="{w}" height="{h}" />')
    O.mode_stack.append(("none", None))  # l'aperçu dessine la donnée d'exemple ci-dessous
    O.origin.append((x, y))
    for t in SLOT_TYPES_DATA.split()[:-1]:
        O.open(f'<Complication type="{t}">')
        text(x, y, w, h, ("expr", "[COMPLICATION.TEXT]"), "", CHAKRA, 15, "#C9D1D9")
        O.close("</Complication>")
    O.origin.pop()
    O.mode_stack.pop()
    O.close("</ComplicationSlot>")
    O.s(f'<text x="{f(cx)}" y="{f(cy - 22)}" font-family="ChakraPetch" font-size="15" '
        f'fill="#C9D1D9" text-anchor="middle" dominant-baseline="central">'
        f'{SAMPLE["slot1"]}</text>', "normal")

    O.comment("Complications 2 à 6 — raccourcis invisibles (choisir « Raccourci d'appli »)")
    zones = [
        ("slot_sc_tl", 40, 116, 84, 84),
        ("slot_sc_tr", 316, 168, 84, 70),
        ("slot_sc_top", 184, 10, 54, 54),
        ("slot_sc_date", RIGHT_C[0] - 36, RIGHT_C[1] - 36, 72, 72),
        ("slot_sc_steps", STEP_C[0] - 30, STEP_C[1] - 30, 60, 60),
    ]
    for n, (name, x, y, w, h) in enumerate(zones, start=2):
        O.open(f'<ComplicationSlot slotId="{n}" x="{f(x)}" y="{f(y)}" width="{w}" height="{h}" '
               f'supportedTypes="{SLOT_TYPES_SHORTCUT}" displayName="{name}">')
        O.x(f'<BoundingOval x="0" y="0" width="{w}" height="{h}" />')
        for t in SLOT_TYPES_SHORTCUT.split():
            O.x(f'<Complication type="{t}" />')
        O.close("</ComplicationSlot>")


# ---------------------------------------------------------------------------
# Assemblage
# ---------------------------------------------------------------------------

def build():
    layer_dial()
    layer_hours()
    layer_seconds()
    layer_index()
    layer_cockpit()
    layer_minutes()
    layer_battery()
    layer_heart()
    layer_date()
    layer_steps()
    layer_complications()


def config_xml():
    lines = ['  <UserConfigurations>',
             '    <ColorConfiguration id="main" displayName="cfg_main" defaultValue="0">']
    for i, (name, a, b) in enumerate(MAIN):
        lines.append(f'      <ColorOption id="{i}" displayName="{name}" colors="{a} {b}" />')
    lines += ['    </ColorConfiguration>',
              '    <ColorConfiguration id="second" displayName="cfg_second" defaultValue="0">']
    for i, (name, a, b) in enumerate(SECOND):
        lines.append(f'      <ColorOption id="{i}" displayName="{name}" colors="{a} {b}" />')
    lines.append('    </ColorConfiguration>')
    for cid, opts in [("cockpit", ["opt_default", "opt_darker"]),
                      ("motif", ["opt_none", "opt_dots", "opt_stripes"]),
                      ("ombre", ["opt_default", "opt_less_shadow"]),
                      ("langue", [n for n, _ in DAYS])]:
        lines.append(f'    <ListConfiguration id="{cid}" displayName="cfg_{cid}" defaultValue="0">')
        for i, n in enumerate(opts):
            lines.append(f'      <ListOption id="{i}" displayName="{n}" />')
        lines.append('    </ListConfiguration>')
    lines.append('  </UserConfigurations>')
    return lines


def png(path, w, h, alpha_at):
    """PNG RGBA noir, alpha donné par alpha_at(x, y) -> 0..255 (stdlib uniquement)."""
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw += bytes((0, 0, 0, alpha_at(x, y)))

    def chunk(kind, data):
        c = struct.pack(">I", len(data)) + kind + data
        return c + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def write_patterns():
    out = os.path.join(RES, "drawable-nodpi")

    def dots(x, y):  # grille de points de 7 px, bord adouci
        d = math.hypot(x % 7 - 3, y % 7 - 3)
        return int(110 * max(0.0, min(1.0, 1.9 - d)))

    def stripes(x, y):  # diagonales de 8 px
        d = (x + y) % 8
        return 100 if d < 2 else (45 if d == 2 else 0)
    png(os.path.join(out, "pattern_dots.png"), W, W, dots)
    png(os.path.join(out, "pattern_stripes.png"), W, W, stripes)


def write():
    build()
    write_patterns()
    head = ['<?xml version="1.0" encoding="utf-8"?>',
            "<!-- Race — cadran Watch Face Format, 438 x 438, Galaxy Watch8 Classic 46 mm.",
            "     FICHIER GÉNÉRÉ par race/tools/generate.py : ne pas éditer à la main. -->",
            f'<WatchFace width="{W}" height="{W}" clipShape="CIRCLE">',
            '  <Metadata key="CLOCK_TYPE" value="DIGITAL" />',
            '  <Metadata key="PREVIEW_TIME" value="10:08:37" />',
            ""]
    body = head + config_xml() + ["", "  <Scene>"] + O.xml + ["", "  </Scene>", "</WatchFace>", ""]
    with open(os.path.join(RES, "raw", "watchface.xml"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(body))

    fonts = os.path.join(RES, "font")
    for mode, frags in O.svg.items():
        bg = "#000000"
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{W}" '
               f'viewBox="0 0 {W} {W}">',
               "<style>",
               f"@font-face {{ font-family: Oswald; src: url('file://{fonts}/{OSWALD}.ttf'); }}",
               f"@font-face {{ font-family: ChakraPetch; src: url('file://{fonts}/{CHAKRA}.ttf'); }}",
               "</style>",
               f"<defs>{''.join(O.defs)}<clipPath id='face'><circle cx='{C}' cy='{C}' r='{C}' />"
               "</clipPath></defs>",
               f'<g clip-path="url(#face)"><rect width="{W}" height="{W}" fill="{bg}" />']
        svg += frags + ["</g></svg>", ""]
        name = "preview.svg" if mode == "normal" else "preview_ambient.svg"
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as fh:
            fh.write("\n".join(svg))


if __name__ == "__main__":
    write()
