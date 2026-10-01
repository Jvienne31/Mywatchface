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


def dim(hex_color, k=0.66):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % (round(r * k), round(g * k), round(b * k))


# Couleur secondaire (jauges des compteurs) : les 10 précédentes + 3.
# Variante sombre = partie non remplie des jauges : même teinte, à mi-luminosité.
SECOND = [(n, a, dim(a)) for n, a, _ in MAIN] + [
    ("col_turquoise", "#2CE6B4", dim("#2CE6B4")),
    ("col_or", "#E8C063", dim("#E8C063")),
    ("col_gris", "#A3AEBA", dim("#A3AEBA")),
]

# Jours, lundi en premier
DAYS = [
    ("lang_fr", ["LUN", "MAR", "MER", "JEU", "VEN", "SAM", "DIM"]),
    ("lang_en", ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]),
    ("lang_de", ["MO", "DI", "MI", "DO", "FR", "SA", "SO"]),
    ("lang_es", ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]),
    ("lang_it", ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]),
]

# main : [vive, vive, sombre] — triplet utilisé tel quel par le dégradé radial du fond
M0, M2 = "[CONFIGURATION.main.0]", "[CONFIGURATION.main.2]"
S0, S1 = "[CONFIGURATION.second.0]", "[CONFIGURATION.second.1]"

OSWALD = "oswald_semibold"
CHAKRA = "chakrapetch_semibold"

# ---------------------------------------------------------------------------
# Données d'exemple pour l'aperçu SVG (l'heure de PREVIEW_TIME)
# ---------------------------------------------------------------------------

SAMPLE = {
    "hour": 11, "minute": 18, "second": 38, "ampm": "AM",
    "hr": 85, "battery": 86, "steps": 6420, "step_pct": 64,
    "dow_idx": 0,  # lundi
    "day": 21, "month": "JUIN", "slot1": "18:49",
}
DEFAULT_COLORS = {M0: MAIN[0][1], "[CONFIGURATION.main.1]": MAIN[0][1], M2: MAIN[0][2], S0: SECOND[0][1], S1: SECOND[0][2]}

# ---------------------------------------------------------------------------
# Géométrie
# ---------------------------------------------------------------------------

# Mesures relevées sur la capture de référence, ramenée à 438 x 438.
# Le disque des heures et l'anneau des secondes ne tournent PAS autour du centre de l'écran :
# leurs centres sont bas, on n'en voit que le sommet.
HOURS_C = (C, 335)     # centre du disque des heures
R_HOURS = 245          # rayon du centre des chiffres (un chiffre tous les 30°)
HOUR_SIZE = 146        # chiffres d'environ 120 px de haut
SEC_C = (C, 396)       # centre de l'anneau des secondes (6° par seconde)
R_SEC_LINE = 301       # filet de l'anneau
R_SEC_LABEL = 268      # étiquettes 00, 05… sous le filet
COCKPIT_C = (C, 421)   # le cockpit est un grand disque dont on ne voit que le haut
COCKPIT_R = 253
ROOF_TIP = (C, 148)    # pointe de la bosse sous l'index
ROOF_SLOPE = 33        # pente des deux pans (degrés)
BATT_C = (C, 228)      # jauge de batterie, demi-anneau au-dessus du pourcentage
BATT_R = 27
PILL_C = (313, 148)    # pastille des minutes, inclinée
PILL_W, PILL_H, PILL_ANGLE = 60, 118, 15
LEFT_C = (116, 296)    # compteur cardio
RIGHT_C = (322, 296)   # compteur date
DIAL_R = 86            # lunette des deux compteurs
BAND_R, BAND_TH = 70, 22
STEP_C = (C, 365)      # petit compteur des pas, posé sur les deux autres
STEP_R = 50

HR_START, HR_SWEEP, HR_MIN, HR_MAX = 176, 240, 40, 220   # 40 en bas, 220 en haut à droite
HR_BAND_START = HR_START - 12                             # marge pour l'étiquette « 40 »
HR_BAND_END = HR_START + 264                              # la bande s'arrête vers 80°
DAY_SEG = 360 / 7
DAY_BASE = -30 - DAY_SEG / 2  # lundi centré à -30°
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

def draw_open(show="both", x=0, y=0, w=W, h=W, angle_expr=None, svg_angle=0, pivot=None,
              angle=None):
    """pivot : normalisé (0-1) dans la boîte du PartDraw ; angle : rotation fixe."""
    rx, ry = rel(x, y)
    attrs = f'x="{f(rx)}" y="{f(ry)}" width="{f(w)}" height="{f(h)}"'
    if pivot:
        attrs += f' pivotX="{pivot[0]:.4f}" pivotY="{pivot[1]:.4f}"'
    if angle is not None:
        attrs += f' angle="{f(angle)}"'
        svg_angle = angle
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
        n = len(g["pos"].split())
        colors = [f"[CONFIGURATION.{name}.{i}]" for i in range(n)]
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


def rect(x, y, w, h, fill, gradient=None):
    a, b = _rel(x, y)
    O.open(f'<Rectangle x="{f(a)}" y="{f(b)}" width="{f(w)}" height="{f(h)}">')
    svg_fill = col(fill)
    if gradient:
        g = gradient
        x1, y1 = _rel(g["x1"], g["y1"])
        x2, y2 = _rel(g["x2"], g["y2"])
        O.open(f'<Fill color="{fill}">')
        O.x(f'<LinearGradient startX="{f(x1)}" startY="{f(y1)}" endX="{f(x2)}" endY="{f(y2)}" '
            f'colors="{g["colors"]}" positions="{g["pos"]}" />')
        O.close("</Fill>")
        gid = O.gid("g")
        O.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                      f'x1="{f(g["x1"])}" y1="{f(g["y1"])}" x2="{f(g["x2"])}" y2="{f(g["y2"])}">'
                      f'{_stops(g)}</linearGradient>')
        svg_fill = f"url(#{gid})"
    else:
        O.x(f'<Fill color="{fill}" />')
    O.close("</Rectangle>")
    O.s(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{svg_fill}" />')


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
         align="CENTER", spacing=None, angle=None, pivot=None, upper=False, outline=None):
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
    if outline:  # (épaisseur, couleur) : contour seul, intérieur noir
        inner += f'<Outline width="{f(outline[0])}" color="{outline[1]}" />'
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
    if outline:
        ls += f' stroke="{col(outline[1])}" stroke-width="{f(outline[0])}" paint-order="stroke"'
    O.s(f'<text x="{f(tx)}" y="{f(y + h / 2)}" font-family="{fam}" font-size="{f(size)}" '
        f'fill="{col(color)}"{op}{ls} text-anchor="{anchor}" dominant-baseline="central"{tr}>'
        f"{escape(str(sample))}</text>", show)


def group_open(name, x=0, y=0, w=W, h=W, angle=None, angle_expr=None, svg_angle=None,
               show="both", launch=None, pivot=None):
    """pivot : point de rotation en coordonnées absolues (défaut : centre du groupe)."""
    rx, ry = rel(x, y)
    attrs = f'name="{name}" x="{f(rx)}" y="{f(ry)}" width="{f(w)}" height="{f(h)}"'
    px, py = pivot if pivot else (x + w / 2, y + h / 2)
    if pivot:
        attrs += f' pivotX="{(px - x) / w:.4f}" pivotY="{(py - y) / h:.4f}"'
    if angle is not None:
        attrs += f' angle="{f(angle)}"'
    O.open(f"<Group {attrs}{alpha_attr(show)}>")
    if launch:
        O.x(f'<Launch target="{launch}" />')
    if angle_expr:
        O.x(f'<Transform target="angle" value="{escape(angle_expr)}" />')
    a = svg_angle if svg_angle is not None else angle
    if a:
        O.s(f'<g transform="rotate({f(a)} {f(px)} {f(py)})">', show)
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
    href = svg_href or "file://" + os.path.join(os.path.abspath(RES), "drawable-nodpi", resource + ".png")
    O.s(f'<image x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" href="{href}" />', show)


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
    ty = gy + (gs - 1.5 * h if flip else h / 2)   # centre du texte sur le rayon r
    text(gx + gs / 2 - w / 2, ty, w, h, label, sample, font, size, color, alpha=alpha)
    group_close(show)


def layer_dial():
    # Les remplissages en dégradé (Fill + RadialGradient) ne s'affichent pas sur la montre
    # (constaté sur l'émulateur Wear OS 6) : aplat de couleur + ombrage en PNG noir translucide.
    O.comment("Fond du cadran : aplat de la couleur principale, assombri vers les bords par un PNG")
    draw_open("normal")
    circle(C, C, C, fill=M0)
    draw_close("normal")
    image(0, 0, W, W, "dial_shade", show="normal")

    O.comment("Motif sur le cadran")
    list_config("motif", [
        lambda: None,
        lambda: image(0, 0, W, W, "pattern_dots", show="normal"),
        lambda: image(0, 0, W, W, "pattern_stripes", show="normal"),
    ])


def layer_hours():
    O.comment("Disque des heures : centré bas (y 335), tourne d'un cran de 30° par heure ; "
              "l'heure courante se lit sous l'index")
    group_open("hour_disk", angle_expr="-30 * [HOUR_0_11]",
               svg_angle=-30 * (SAMPLE["hour"] % 12), pivot=HOURS_C)
    w, h = 180, 150
    y = HOURS_C[1] - R_HOURS - h / 2
    for k in range(1, 13):
        group_open(f"hour_{k}", angle=30 * k if k != 12 else None, pivot=HOURS_C)
        text(C - w / 2, y, w, h, str(k), k, OSWALD, HOUR_SIZE, "#000000", show="normal", alpha=135)
        text(C - w / 2, y, w, h, str(k), k, OSWALD, HOUR_SIZE, "#000000", show="ambient",
             outline=(2, M0))
        group_close()
    group_close()


def layer_seconds():
    O.comment("Anneau des secondes : grand cercle centré bas (y 396), 6° par seconde")
    sx, sy = SEC_C
    group_open("seconds_ring", angle_expr="-6 * [SECOND]", svg_angle=-6 * SAMPLE["second"],
               show="normal", pivot=SEC_C)
    # 12 secteurs de 5 s, chacun dessiné en haut puis tourné : tout reste dans la toile
    for i in range(12):
        group_open(f"sec_{i * 5}", angle=30 * i if i else None, pivot=SEC_C)
        draw_open()
        arc(sx, sy, R_SEC_LINE, -15, 15, "#8C000000", 1.5)
        for j in range(5):
            a = 6 * j
            half = 9 if j == 0 else 4
            x1, y1 = polar(sx, sy, R_SEC_LINE - half, a)
            x2, y2 = polar(sx, sy, R_SEC_LINE + half, a)
            line(x1, y1, x2, y2, "#B4000000", 3 if j == 0 else 1.5, cap="BUTT")
        draw_close()
        lx, ly = polar(sx, sy, R_SEC_LABEL, 0)
        text(lx - 22, ly - 14, 44, 28, f"{i * 5:02d}", f"{i * 5:02d}", OSWALD, 23, "#000000",
             alpha=190)
        group_close()
    group_close("normal")


def layer_index():
    O.comment("Index vertical, jusqu'à la pointe du cockpit")
    tx, ty = ROOF_TIP
    draw_open("normal")
    line(tx, 0, tx, ty, "#8C000000", 1.5, cap="BUTT")
    draw_close("normal")
    draw_open("ambient")
    line(tx, 0, tx, ty, M0, 1.5, cap="BUTT")
    draw_close("ambient")


def layer_pill():
    O.comment("Minutes : pastille inclinée à droite de l'index (son pied passe sous le cockpit)")
    cx, cy = PILL_C
    x, y = cx - PILL_W / 2, cy - PILL_H / 2
    group_open("minute_pill", x, y, PILL_W, PILL_H, angle=PILL_ANGLE)
    draw_open("normal", x, y, PILL_W, PILL_H)
    rrect(x, y, PILL_W, PILL_H, PILL_W / 2, "#121417")
    draw_close("normal")
    draw_open("ambient", x, y, PILL_W, PILL_H)
    rrect(x + 1, y + 1, PILL_W - 2, PILL_H - 2, PILL_W / 2 - 1, "#000000", stroke=M0, th=1.5)
    draw_close("ambient")
    text(x, y + 10, PILL_W, 52, ("expr", "[MINUTE_Z]"), f"{SAMPLE['minute']:02d}",
         OSWALD, 46, "#F2F5F8")
    text(x, y + 60, PILL_W, 18, ("expr", "[AMPM_STRING]"), SAMPLE["ampm"], OSWALD, 15,
         "#8E99A5")
    group_close()


def roof_join():
    """Écart horizontal où un pan de la bosse rejoint le cercle du cockpit."""
    tx, ty = ROOF_TIP
    cx, cy = COCKPIT_C
    k = math.tan(math.radians(ROOF_SLOPE))
    lo, hi = 0.0, COCKPIT_R
    for _ in range(60):
        dx = (lo + hi) / 2
        if ty + dx * k < cy - math.sqrt(COCKPIT_R ** 2 - dx ** 2):
            lo = dx
        else:
            hi = dx
    return lo


ROOF_L, ROOF_H = 90, 60


def roof(fill, grad=None):
    """Les deux pans de la bosse : rectangles pivotés autour de la pointe."""
    tx, ty = ROOF_TIP
    for side in (-1, 1):
        x = tx - ROOF_L if side < 0 else tx
        draw_open("both", x, ty, ROOF_L, ROOF_H, pivot=(1 if side < 0 else 0, 0),
                  angle=side * ROOF_SLOPE)
        rect(x, ty, ROOF_L, ROOF_H, fill, gradient=grad)
        draw_close()


def layer_cockpit():
    cx, cy = COCKPIT_C
    tx, ty = ROOF_TIP

    O.comment("Ombre portée du cockpit")

    list_config("ombre", [
        lambda: image(0, SHADE_Y, W, W - SHADE_Y, "cockpit_shadow", show="normal"),
        lambda: image(0, SHADE_Y, W, W - SHADE_Y, "cockpit_shadow_less", show="normal"),
    ])

    O.comment("Cockpit : grand disque sombre + bosse en pointe sous l'index")

    def cockpit(top):
        def fn():
            group_open("cockpit_fill", show="normal")
            roof(top)   # les pans d'abord : le disque recouvre leur bas
            draw_open()
            circle(cx, cy, COCKPIT_R, fill=top)
            draw_close()
            group_close("normal")
        return fn
    list_config("cockpit", [cockpit("#22262B"), cockpit("#121417")])
    image(0, SHADE_Y, W, W - SHADE_Y, "cockpit_shade", show="normal")  # assombri vers le bas
    group_open("cockpit_ambient", show="ambient")  # AOD : noir pur, masque le bas du cadran
    roof("#000000")
    draw_open()
    circle(cx, cy, COCKPIT_R, fill="#000000")
    draw_close()
    group_close("ambient")

    O.comment("Arêtes du cockpit (aussi en AOD)")
    dx = roof_join()
    jy = ty + dx * math.tan(math.radians(ROOF_SLOPE))
    a_join = math.degrees(math.asin(dx / COCKPIT_R))
    draw_open()
    arc(cx, cy, COCKPIT_R, -80, -a_join, "#454C54", 1.5)
    arc(cx, cy, COCKPIT_R, a_join, 80, "#454C54", 1.5)
    line(tx - dx, jy, tx, ty, "#454C54", 1.5)
    line(tx, ty, tx + dx, jy, "#454C54", 1.5)
    draw_close()

    O.comment("Vis")
    draw_open("normal")
    for sx, sy in [(C, 288), (143, 392), (295, 392)]:
        circle(sx, sy, 4.5, fill="#0B0C0E", stroke="#30363C", th=1.2)
    draw_close("normal")


def layer_battery():
    bx, by = BATT_C
    O.comment("Batterie, dans la bosse — un appui ouvre l'état de la batterie")
    group_open("battery", bx - 32, 160, 64, 86, launch="BATTERY_STATUS")
    draw_open()
    line(222, 166, 215, 177, "#8E99A5", 2)   # éclair
    line(215, 177, 223, 177, "#8E99A5", 2)
    line(223, 177, 216, 188, "#8E99A5", 2)
    draw_close()
    draw_open("normal")
    arc(bx, by, BATT_R, -90, 90, "#2B3036", 6)
    draw_close("normal")
    pct = SAMPLE["battery"]
    draw_open()
    arc(bx, by, BATT_R, -90, 90, S0, 6,
        end_expr="-90 + 180 * [BATTERY_PERCENT] / 100", svg_a1=-90 + 180 * pct / 100)
    draw_close()
    text(bx - 24, by - 11, 48, 26, ("expr", "[BATTERY_PERCENT]"), pct, OSWALD, 22, "#C9D1D9")
    group_close()


def dial_base(cx, cy, r, inner=None):
    """Lunette du compteur (mode normal) + filet (aussi en AOD, sur noir pur)."""
    draw_open("normal")
    circle(cx, cy, r, fill="#101214")
    draw_close("normal")
    draw_open()
    circle(cx, cy, r - 1.5, stroke="#30363C", th=3)
    draw_close()


def inner_disc(cx, cy, r):
    draw_open("normal")
    circle(cx, cy, r, fill="#0E1012")
    draw_close("normal")


def hr_angle(v):
    return HR_START + HR_SWEEP * (v - HR_MIN) / (HR_MAX - HR_MIN)


def layer_heart():
    cx, cy = LEFT_C
    O.comment("Compteur gauche : fréquence cardiaque, échelle 40 (en bas) à 220 (en haut à droite)")
    dial_base(cx, cy, DIAL_R)
    draw_open("normal")
    arc(cx, cy, BAND_R, HR_BAND_START, HR_BAND_END, S1, BAND_TH)
    hr = SAMPLE["hr"]
    arc(cx, cy, BAND_R, HR_BAND_START, HR_START + HR_SWEEP, S0, BAND_TH,
        end_expr=(f"{HR_START} + {HR_SWEEP} * clamp(([HEART_RATE] - {HR_MIN}) / "
                  f"{HR_MAX - HR_MIN}, 0, 1)"),
        svg_a1=hr_angle(hr))
    arc(cx, cy, BAND_R, hr_angle(200), HR_BAND_END, S0, BAND_TH)  # zone rouge 200+
    ticks(cx, cy, BAND_R, 10, HR_START, HR_SWEEP, BAND_TH, 1.4, "#C8000000", closed=False)
    ticks(cx, cy, BAND_R + BAND_TH / 2 - 3, 19, HR_START, HR_SWEEP, 6, 1, "#A0000000",
          closed=False)
    draw_close("normal")
    draw_open("ambient")
    arc(cx, cy, BAND_R + BAND_TH / 2, HR_BAND_START, HR_BAND_END, S0, 1.5)
    draw_close("ambient")
    for v in (40, 60, 80, 120, 140, 160, 180, 220):
        tangential_label(cx, cy, BAND_R, hr_angle(v), str(v), v, OSWALD, 15, "#000000",
                         w=34, h=20, show="normal", alpha=225)
    inner_disc(cx, cy, BAND_R - BAND_TH / 2 - 2)

    draw_open()
    line(cx - 38, cy - 5, cx + 34, cy - 5, "#5D666F", 1.2, cap="BUTT")
    line(cx + 34, cy - 5, cx + 56, cy + 30, "#5D666F", 1.2, cap="BUTT")
    draw_close()

    O.comment("Petit cœur dessiné (deux disques + un carré à 45°)")
    hx, hy = cx + 36, cy + 42
    draw_open()
    circle(hx - 3.6, hy - 2.5, 3.8, fill="#7D8893")
    circle(hx + 3.6, hy - 2.5, 3.8, fill="#7D8893")
    draw_close()
    draw_open(x=hx - 6, y=hy - 5, w=12, h=12, angle=45)   # PartDraw : coordonnées entières
    rect(hx - 5.2, hy - 4.2, 10.4, 10.4, "#7D8893")
    draw_close()

    group_open("heart_rate", cx - 40, cy, 80, 40, launch="HEALTH_HEART_RATE")
    condition("hr_ok", "[HEART_RATE] > 0",
              lambda: _hr_value(cx, cy, ("expr", "round([HEART_RATE])"), hr),
              lambda: _hr_value(cx, cy, "--", "--"), True)
    group_close()


def _hr_value(cx, cy, content, sample):
    group_open(f"hr_{O.gid('v')}", cx - 40, cy, 80, 40)
    text(cx - 40, cy, 80, 40, content, sample, OSWALD, 36, "#E8EDF2")
    group_close()


def layer_date():
    cx, cy = RIGHT_C
    O.comment("Compteur droit : couronne des jours (jour courant en couleur) + mois et jour")
    dial_base(cx, cy, DIAL_R)
    idx_expr = "(([DAY_OF_WEEK] + 5) % 7)"   # [DAY_OF_WEEK] : 1 = dimanche ; idx : 0 = lundi
    i = SAMPLE["dow_idx"]
    seg = dict(start_expr=f"{DAY_BASE:.4f} + {DAY_SEG:.4f} * {idx_expr}",
               end_expr=f"{DAY_BASE + DAY_SEG:.4f} + {DAY_SEG:.4f} * {idx_expr}",
               svg_a0=DAY_BASE + DAY_SEG * i, svg_a1=DAY_BASE + DAY_SEG * (i + 1))
    draw_open("normal")
    arc(cx, cy, BAND_R, DAY_BASE, DAY_BASE + 360, S1, BAND_TH)
    arc(cx, cy, BAND_R, DAY_BASE, DAY_BASE + DAY_SEG, S0, BAND_TH, **seg)
    ticks(cx, cy, BAND_R, 7, DAY_BASE, 360, BAND_TH, 2.5, "#15181B")
    draw_close("normal")
    draw_open("ambient")
    arc(cx, cy, BAND_R + BAND_TH / 2, DAY_BASE, DAY_BASE + DAY_SEG, S0, 2, **seg)
    draw_close("ambient")

    def labels(names):
        def fn():
            for d, name in enumerate(names):
                a = DAY_BASE + DAY_SEG * (d + 0.5)
                tangential_label(cx, cy, BAND_R, a, name, name, OSWALD, 19, "#000000",
                                 w=50, h=22, show="normal", alpha=230)
        return fn
    O.comment("Noms des jours, selon la langue choisie")
    list_config("langue", [labels(names) for _, names in DAYS])
    inner_disc(cx, cy, BAND_R - BAND_TH / 2 - 2)

    text(cx - 40, cy - 42, 80, 32, ("expr", "[MONTH_S]"), SAMPLE["month"], OSWALD, 25,
         "#C9D1D9", upper=True)
    draw_open()
    line(cx - 34, cy - 5, cx + 34, cy - 5, "#5D666F", 1.2, cap="BUTT")
    draw_close()
    text(cx - 40, cy, 80, 40, ("expr", "[DAY]"), SAMPLE["day"], OSWALD, 36, "#E8EDF2")


def layer_steps():
    cx, cy = STEP_C
    O.comment("Petit compteur bas, posé sur les deux autres : progression vers l'objectif de pas")
    dial_base(cx, cy, STEP_R)
    inner_disc(cx, cy, STEP_R - 14)
    pct = SAMPLE["step_pct"]
    draw_open()
    ticks(cx, cy, STEP_R - 8, 10, STEP_START, STEP_SWEEP, 5, 2.4, S0, closed=False)
    draw_close()
    draw_open("normal")
    arc(cx, cy, 28, STEP_START, STEP_START + STEP_SWEEP, "#2B3036", 3)
    arc(cx, cy, 28, STEP_START, STEP_START + STEP_SWEEP, S0, 3,
        end_expr=f"{STEP_START} + {STEP_SWEEP} * [STEP_PERCENT] / 100",
        svg_a1=STEP_START + STEP_SWEEP * pct / 100)
    draw_close("normal")
    text(cx - 26, cy + 10, 20, 16, "0", "0", OSWALD, 12, "#4F5A64")
    text(cx + 6, cy + 10, 20, 16, "%", "%", OSWALD, 12, "#4F5A64")
    text(cx - 24, cy + 25, 48, 14, ("expr", "[STEP_COUNT]"), SAMPLE["steps"], OSWALD, 11,
         "#6B757F")
    O.comment("Aiguille des pas")
    size = 70
    draw_open(x=cx - size / 2, y=cy - size / 2, w=size, h=size,
              angle_expr=f"{STEP_START} + {STEP_SWEEP} * [STEP_PERCENT] / 100",
              svg_angle=STEP_START + STEP_SWEEP * pct / 100)
    line(cx, cy + 7, cx, cy - 30, S0, 3.5)
    draw_close()
    draw_open()
    circle(cx, cy, 5, fill="#0E1012", stroke=S0, th=2)
    draw_close()


SLOT_TYPES_DATA = "SHORT_TEXT RANGED_VALUE GOAL_PROGRESS LONG_TEXT EMPTY"
SLOT_TYPES_SHORTCUT = "SMALL_IMAGE MONOCHROMATIC_IMAGE SHORT_TEXT EMPTY"


def layer_complications():
    cx, cy = LEFT_C
    O.comment("Complication 1 — conteneur de données, en haut du compteur cardio")
    x, y, w, h = 70, 252, 120, 48   # texte à gauche, icône du fournisseur à droite
    O.open(f'<ComplicationSlot slotId="1" x="{f(x)}" y="{f(y)}" width="{w}" height="{h}" '
           f'supportedTypes="{SLOT_TYPES_DATA}" displayName="slot_data">')
    O.x('<DefaultProviderPolicy defaultSystemProvider="SUNRISE_SUNSET" '
        'defaultSystemProviderType="SHORT_TEXT" />')
    O.x(f'<BoundingBox x="0" y="0" width="{w}" height="{h}" />')
    O.mode_stack.append(("none", None))  # l'aperçu dessine la donnée d'exemple ci-dessous
    O.origin.append((x, y))
    for t in SLOT_TYPES_DATA.split()[:-1]:
        O.open(f'<Complication type="{t}">')
        text(x, y, 92, 36, ("expr", "[COMPLICATION.TEXT]"), "", OSWALD, 25, "#C9D1D9")
        O.open('<PartImage x="100" y="30" width="18" height="18" tintColor="#8E99A5">')
        O.x('<Image resource="[COMPLICATION.MONOCHROMATIC_IMAGE]" />')
        O.close("</PartImage>")
        O.close("</Complication>")
    O.origin.pop()
    O.mode_stack.pop()
    O.close("</ComplicationSlot>")
    O.s(f'<text x="{f(x + 46)}" y="{f(y + 18)}" font-family="Oswald" font-size="25" '
        f'fill="#C9D1D9" text-anchor="middle" dominant-baseline="central">'
        f'{SAMPLE["slot1"]}</text>', "normal")
    sun_x, sun_y = x + 109, y + 39   # icône d'exemple : soleil levant
    O.s(f'<g stroke="#8E99A5" stroke-width="1.6" fill="none">'
        f'<path d="M {f(sun_x - 7)} {f(sun_y + 2)} A 7 7 0 0 1 {f(sun_x + 7)} {f(sun_y + 2)}" />'
        f'<line x1="{f(sun_x - 9)}" y1="{f(sun_y + 5)}" x2="{f(sun_x + 9)}" y2="{f(sun_y + 5)}" />'
        f'</g>', "normal")

    O.comment("Complications 2 à 6 — raccourcis invisibles (choisir « Raccourci d'appli »)")
    zones = [
        ("slot_sc_tl", 40, 110, 84, 84),
        ("slot_sc_tr", 356, 150, 56, 56),
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
    layer_pill()
    layer_cockpit()
    layer_battery()
    layer_heart()
    layer_date()
    layer_steps()
    layer_complications()


def config_xml():
    lines = ['  <UserConfigurations>',
             '    <ColorConfiguration id="main" displayName="cfg_main" defaultValue="0">']
    for i, (name, a, b) in enumerate(MAIN):
        lines.append(f'      <ColorOption id="{i}" displayName="{name}" colors="{a} {a} {b}" />')
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


SHADE_Y = 120   # les PNG d'ombrage du cockpit commencent ici (inutile de couvrir le haut)


def cockpit_distance(x, y):
    """Distance signée au cockpit (disque + bosse en pointe) : < 0 dedans, > 0 dehors."""
    cx, cy = COCKPIT_C
    tx, ty = ROOF_TIP
    d_disc = math.hypot(x - cx, y - cy) - COCKPIT_R
    k = math.tan(math.radians(ROOF_SLOPE))
    dx = abs(x - tx)
    if dx <= roof_join():
        d_roof = ((ty + dx * k) - y) * math.cos(math.radians(ROOF_SLOPE))
        return min(d_disc, d_roof)
    return d_disc


def write_shading():
    out = os.path.join(RES, "drawable-nodpi")
    h = W - SHADE_Y

    def dial_shade(x, y):  # vignette : clair en haut au centre, sombre vers le bord
        r = math.hypot(x - C, y - 150)
        t = max(0.0, min(1.0, (r - 110) / 230))
        return int(200 * t ** 1.6)
    png(os.path.join(out, "dial_shade.png"), W, W, dial_shade)

    def shadow(alpha, spread):
        def fn(x, y):
            d = cockpit_distance(x, y + SHADE_Y)
            if d <= 0 or d >= spread:
                return 0
            return int(alpha * (1 - d / spread) ** 1.5)
        return fn
    png(os.path.join(out, "cockpit_shadow.png"), W, h, shadow(150, 26))
    png(os.path.join(out, "cockpit_shadow_less.png"), W, h, shadow(80, 14))

    def cockpit_shade(x, y):  # dégradé vertical, uniquement dans le cockpit
        yy = y + SHADE_Y
        if cockpit_distance(x, yy) > -0.5:
            return 0
        return int(185 * max(0.0, (yy - ROOF_TIP[1]) / (W - ROOF_TIP[1])))
    png(os.path.join(out, "cockpit_shade.png"), W, h, cockpit_shade)


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
    write_shading()
    head = ['<?xml version="1.0" encoding="utf-8"?>',
            "<!-- Race — cadran Watch Face Format, 438 x 438, Galaxy Watch8 Classic 46 mm.",
            "     FICHIER GÉNÉRÉ par race/tools/generate.py : ne pas éditer à la main. -->",
            f'<WatchFace width="{W}" height="{W}" clipShape="CIRCLE">',
            '  <Metadata key="CLOCK_TYPE" value="DIGITAL" />',
            '  <Metadata key="PREVIEW_TIME" value="11:18:38" />',
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
