"""Briques de génération Watch Face Format, avec aperçu SVG en miroir.

Extraites du générateur de Race (race/tools/generate.py), validées sur émulateur Wear OS 6.
Chaque primitive émet l'élément WFF dans O.xml et son équivalent SVG dans O.svg, pour
contrôler la mise en page sans montre. Les coordonnées sont absolues dans la toile W x W ;
rel() / _rel() les convertissent pour les Group et PartDraw englobants.

Règles apprises sur l'émulateur (cf. race/README.md) :
  - pas de Fill + gradient (non rendu) : aplats + PNG translucides ;
  - pas de dashIntervals (dérive) : une Line par graduation ;
  - pas d'Outline sur le texte (non rendu) ;
  - x / y des PartDraw et ComplicationSlot : entiers.

Le générateur appelant renseigne : RES (dossier res/), DEFAULT_COLORS (aperçu des
[CONFIGURATION.*]) et FONTS (nom de ressource -> famille CSS de l'aperçu).
"""

import math
import os
import struct
import zlib
from xml.sax.saxutils import escape

W = 438
C = W / 2
RES = "."
DEFAULT_COLORS = {}
FONTS = {}

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


def _box(x, y, w, h):
    """x / y / width / height entiers (exigés par le schéma pour les Part* et Group)."""
    x0, y0 = round(x), round(y)
    return f'x="{x0}" y="{y0}" width="{round(x + w) - x0}" height="{round(y + h) - y0}"'


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
              angle=None, render_mode=None, alpha=None):
    """alpha : opacité 0-255 du PartDraw entier. pivot : normalisé (0-1) dans la boîte du PartDraw ; angle : rotation fixe."""
    rx, ry = rel(x, y)
    attrs = f'x="{f(rx)}" y="{f(ry)}" width="{f(w)}" height="{f(h)}"'
    if pivot:
        attrs += f' pivotX="{pivot[0]:.4f}" pivotY="{pivot[1]:.4f}"'
    if angle is not None:
        attrs += f' angle="{f(angle)}"'
        svg_angle = angle
    if render_mode:
        attrs += f' renderMode="{render_mode}"'
    O.open(f"<PartDraw {attrs}{alpha_attr(show, alpha)}>")
    if angle_expr:
        O.x(f'<Transform target="angle" value="{angle_expr}" />')
    O._draw = (x, y)
    op = f' opacity="{alpha / 255:.3f}"' if alpha is not None else ""
    if svg_angle:
        px = x + w * (pivot[0] if pivot else 0.5)
        py = y + h * (pivot[1] if pivot else 0.5)
        O.s(f'<g transform="rotate({f(svg_angle)} {f(px)} {f(py)})"{op}>', show)
    else:
        O.s(f"<g{op}>", show)
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
    """Graduations régulières, une Line par trait.

    Pas d'arc en pointillés (dashIntervals) : sur la montre, l'espacement des pointillés
    dérive le long de l'arc (constaté sur émulateur, ~10° d'écart après un demi-tour)."""
    n = count if closed else count - 1
    for i in range(count):
        a = a0 + sweep * i / n
        x1, y1 = polar(cx, cy, r - length / 2, a)
        x2, y2 = polar(cx, cy, r + length / 2, a)
        line(x1, y1, x2, y2, color, th, cap="BUTT")


def line(x1, y1, x2, y2, color, th, cap="ROUND"):
    a, b = _rel(x1, y1)
    c_, d = _rel(x2, y2)
    O.open(f'<Line startX="{f(a)}" startY="{f(b)}" endX="{f(c_)}" endY="{f(d)}">')
    O.x(stroke_xml(color, th, cap))
    O.close("</Line>")
    O.s(f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" {svg_stroke(color, th, cap)} />')


def rect(x, y, w, h, fill, gradient=None, width_expr=None, svg_w=None):
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
    if width_expr:
        O.x(f'<Transform target="width" value="{escape(width_expr)}" />')
    O.close("</Rectangle>")
    sw = w if svg_w is None else svg_w
    O.s(f'<rect x="{f(x)}" y="{f(y)}" width="{f(sw)}" height="{f(h)}" fill="{svg_fill}" />')


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
         align="CENTER", spacing=None, angle=None, pivot=None, upper=False, outline=None,
         slant=False, svg_slant=12, fmt="%s"):
    """PartText. content : texte fixe, ou ('expr', expression) pour un Template (fmt : gabarit).
    slant : Font slant="ITALIC" (oblique synthétique de la montre ; aperçu : skewX)."""
    rx, ry = rel(x, y)
    attrs = _box(rx, ry, w, h)
    if angle is not None:
        attrs += f' angle="{f(angle)}"'
    if pivot:
        attrs += f' pivotX="{pivot[0]:.4f}" pivotY="{pivot[1]:.4f}"'
    O.open(f"<PartText {attrs}{alpha_attr(show, alpha)}>")
    O.open(f'<Text align="{align}" ellipsis="TRUE" maxLines="1">')
    sp = f' letterSpacing="{spacing}"' if spacing else ""
    if isinstance(content, tuple):
        inner = (f'<Template><![CDATA[{fmt}]]><Parameter expression="{escape(content[1])}" />'
                 f"</Template>")
        if upper:
            inner = f"<Upper>{inner}</Upper>"
    else:
        inner = escape(content)
    if outline:  # (épaisseur, couleur) : contour seul, intérieur noir
        inner += f'<Outline width="{f(outline[0])}" color="{outline[1]}" />'
    sl = ' slant="ITALIC"' if slant else ""
    O.x(f'<Font family="{font}" size="{f(size)}" color="{color}"{sp}{sl}>{inner}</Font>')
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
    fam = FONTS.get(font, font)
    if slant:
        cy = y + h / 2
        tr += f' transform="translate({f(tx)} {f(cy)}) skewX(-{svg_slant}) translate({f(-tx)} {f(-cy)})"' \
            if not tr else ""
    if outline:
        ls += f' stroke="{col(outline[1])}" stroke-width="{f(outline[0])}" paint-order="stroke"'
    O.s(f'<text x="{f(tx)}" y="{f(y + h / 2)}" font-family="{fam}" font-size="{f(size)}" '
        f'fill="{col(color)}"{op}{ls} text-anchor="{anchor}" dominant-baseline="central"{tr}>'
        f"{escape(str(sample))}</text>", show)


def group_open(name, x=0, y=0, w=W, h=W, angle=None, angle_expr=None, svg_angle=None,
               show="both", launch=None, pivot=None, scale=None, render_mode=None):
    """pivot : point de rotation / d'échelle en coordonnées absolues (défaut : centre).
    scale : facteur scaleX = scaleY ; render_mode : SOURCE / MASK / ALL (XML seulement)."""
    rx, ry = rel(x, y)
    attrs = f'name="{name}" x="{f(rx)}" y="{f(ry)}" width="{f(w)}" height="{f(h)}"'
    px, py = pivot if pivot else (x + w / 2, y + h / 2)
    if pivot:
        attrs += f' pivotX="{(px - x) / w:.4f}" pivotY="{(py - y) / h:.4f}"'
    if angle is not None:
        attrs += f' angle="{f(angle)}"'
    if scale:
        attrs += f' scaleX="{scale}" scaleY="{scale}"'
    if render_mode:
        attrs += f' renderMode="{render_mode}"'
    O.open(f"<Group {attrs}{alpha_attr(show)}>")
    if launch:
        O.x(f'<Launch target="{launch}" />')
    if angle_expr:
        O.x(f'<Transform target="angle" value="{escape(angle_expr)}" />')
    a = svg_angle if svg_angle is not None else angle
    tr = []
    if a:
        tr.append(f"rotate({f(a)} {f(px)} {f(py)})")
    if scale:
        tr.append(f"translate({f(px)} {f(py)}) scale({scale}) translate({f(-px)} {f(-py)})")
    O.s(f'<g transform="{" ".join(tr)}">' if tr else "<g>", show)
    O.mode_stack.append((show, None))
    O.origin.append((x, y))


def group_close(show="both"):
    variant(show)
    ambient_on(show)
    O.origin.pop()
    O.mode_stack.pop()
    O.s("</g>", show)
    O.close("</Group>")


def image(x, y, w, h, resource, show="both", svg_href=None, tint=None, alpha=None):
    """tint : tintColor (image blanche recolorée, ex. pictogramme dans la couleur de palette)."""
    rx, ry = rel(x, y)
    ta = f' tintColor="{tint}"' if tint else ""
    O.open(f'<PartImage {_box(rx, ry, w, h)}{ta}{alpha_attr(show, alpha)}>')
    O.x(f'<Image resource="{resource}" />')
    variant(show)
    ambient_on(show)
    O.close("</PartImage>")
    href = svg_href or "file://" + os.path.join(os.path.abspath(RES), "drawable-nodpi", resource + ".png")
    op = f' opacity="{alpha / 255:.3f}"' if alpha is not None and show != "ambient" else ""
    if tint:
        mid = O.gid("m")
        O.defs.append(f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}">'
                      f'<image x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" href="{href}" /></mask>')
        O.s(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{col(tint)}" mask="url(#{mid})"{op} />', show)
    else:
        O.s(f'<image x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" href="{href}"{op} />', show)


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
