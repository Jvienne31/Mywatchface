#!/usr/bin/env python3
"""Génère le cadran Prisme : watchface.xml (Watch Face Format v2) + PNG + aperçus SVG.

Maquette de référence : concepts/prisme/ (version « 2 dômes », palette Lagune).

    node prisme/tools/icons.mjs            # pictogrammes blancs (PNG), une seule fois
    python3 prisme/tools/generate.py       # watchface.xml, PNG de verre / ombrage, aperçus SVG
    node prisme/tools/render-preview.mjs   # aperçus PNG (preview.png du paquet)

Ne pas éditer watchface.xml à la main.

Principes (règles apprises sur émulateur avec Race, cf. tools/wff.py) :
  - bandes : 4 Rectangle dans un Group tourné de 18° ;
  - inversion des chiffres : les chiffres sont dessinés une fois par bande, dans l'encre de la
    bande, chaque fois découpés par un masque (renderMode="MASK") en forme de bande ;
  - loupes : fond agrandi 1,2x découpé en disque (MASK) + ComplicationSlot agrandi 1,2x
    + verre et ombre en PNG translucides ;
  - 7 emplacements = 7 ComplicationSlot. Tant qu'aucune source n'est choisie (type EMPTY),
    chacun affiche sa donnée intégrée (date, météo, UV, pluie, cardio, batterie, pas).
"""

import math
import os
import sys
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wff  # noqa: E402
from wff import (O, W, C, f, polar, rel, escape, draw_open, draw_close, rect, circle, arc,  # noqa: E402
                 line, rrect, text, group_open, group_close, image, condition)

RES = os.path.join(HERE, "..", "src", "main", "res")
wff.RES = RES

# ---------------------------------------------------------------------------
# Palettes : 4 bandes (sombre -> claire) + accent ; encres calculées par luminance
# ---------------------------------------------------------------------------

def _hex(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def _lum(h):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in _hex(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _mix(a, b, k):
    return "#" + "".join(f"{round(x + (y - x) * k):02X}" for x, y in zip(_hex(a), _hex(b)))


def _contrast(a, b):
    l1, l2 = sorted((_lum(a), _lum(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


PALETTES = [
    ("pal_lagune", ["#0A1729", "#0E4756", "#2A9BA6", "#DDEFF0"], "#7FE3EC"),
    ("pal_volcan", ["#1C1A19", "#5E281B", "#C4562C", "#ECE0CB"], "#FF8A3D"),
    ("pal_ardoise", ["#151719", "#353A40", "#78808A", "#E9EBED"], "#C8F03A"),
    ("pal_moka", ["#2B1D17", "#5A3B2E", "#A47864", "#EADBC8"], "#F0B86E"),
    ("pal_sauge", ["#18221C", "#3F5A4A", "#8FA98F", "#E6ECDF"], "#F2C14E"),
    ("pal_lavande", ["#1C1830", "#45386B", "#9C8FD0", "#ECE8F8"], "#FFB3C7"),
    ("pal_cerise", ["#1A0E12", "#5B1424", "#C8364F", "#F5E1DF"], "#FFC9A3"),
    ("pal_cobalt", ["#0A1330", "#1E3A8A", "#4C7BF3", "#E4EAFB"], "#FFD23F"),
    ("pal_olive", ["#1C1E12", "#474B26", "#8F9A4E", "#EEEDDA"], "#FF8C42"),
    ("pal_dune", ["#2A2118", "#8C6A47", "#D2B48C", "#F7EFE2"], "#2FB3A8"),
    ("pal_neon", ["#0B0B12", "#22224A", "#FF2E88", "#F4F4F8"], "#00E5FF"),
    ("pal_graphite", ["#101010", "#2F2F2F", "#8A8A8A", "#F2F2F2"], "#FF3B30"),
    ("pal_foret", ["#0E1A14", "#1F3D2E", "#3E7C5A", "#DDEBE2"], "#E6C35C"),
    ("pal_peche", ["#2A1C1A", "#8A4F3D", "#F2A07B", "#FDEDE3"], "#2E6E9E"),
    ("pal_beurre", ["#26231A", "#6B6342", "#E8D27A", "#FBF6E3"], "#D9544D"),
    ("pal_bordeaux", ["#1A0C10", "#4A1621", "#B54A57", "#EBDCCD"], "#D9AE62"),
    ("pal_abysse", ["#05121C", "#0B3954", "#087E8B", "#C4DCEC"], "#FF6B6B"),
    ("pal_aurore", ["#1A1530", "#5A2A6E", "#E0607E", "#FFE6D8"], "#FFC857"),
]


def palette_colors(bands, accent):
    """5 couleurs par option (maximum du format) : bandes 0-3 (sombre -> claire), accent."""
    return bands + [accent]


def P(i):
    return f"[CONFIGURATION.palette.{i}]"


BAND, ACCENT = [P(0), P(1), P(2), P(3)], P(4)
# Encre de chaque bande : claire sur les bandes 0-1, sombre sur 2-3 (vérifié par
# check_contrast() pour les 18 palettes : un ColorOption ne porte que 5 couleurs).
INK = [P(3), P(3), P(0), P(0)]
# Couleurs dérivées par transparence : texte « doux » et pistes des jauges.
SOFT_D, SOFT_L = (P(3), 150), (P(0), 150)       # sur bande sombre / sur bande claire
TRACK_D, TRACK_L = (P(1), 160), (P(2), 95)


def check_contrast():
    for name, b, _ in PALETTES:
        for i, ink in enumerate((b[3], b[3], b[0], b[0])):
            k = _contrast(b[i], ink)
            assert k >= 3.5, f"{name} : contraste {k:.2f} sur la bande {i}"


_PREVIEW = int(os.environ.get("PRISME_PREVIEW_PALETTE", "0"))
wff.DEFAULT_COLORS = {P(i): c for i, c in enumerate(palette_colors(*PALETTES[_PREVIEW][1:]))}

# ---------------------------------------------------------------------------
# Polices, géométrie, données d'exemple
# ---------------------------------------------------------------------------

DIGITS, DIGITS_AOD = "bigshoulders_extrabold", "bigshoulders_light"
DATA, DATA_M = "barlowcondensed_semibold", "barlowcondensed_medium"
wff.FONTS = {DIGITS: "ShouldersXB", DIGITS_AOD: "ShouldersL", DATA: "BarlowSB", DATA_M: "BarlowM"}

ANGLE = 18
EDGES = [0, 128, 206, 286, W]        # bords des bandes dans le repère tourné
HH_C, MM_C = (C - 30, 130), (C + 34, 272)   # centres des deux lignes de chiffres
DIGIT_SIZE = 172
DOME_TR, DOME_BL, DOME_R, DOME_K = (354, 124), (68, 262), 46, 1.2
SAMPLE = {"hh": "10", "mm": "09", "s": 36, "day": "02", "mon": "OCT", "dow": "VENDREDI",
          "temp": 18, "rain": 20, "uv": 3, "hr": 72, "batt": 86, "steps": 6420, "pct": 64}

# ---------------------------------------------------------------------------
# Masques : l'aperçu SVG utilise des clipPath, le XML des Group renderMode="MASK"
# ---------------------------------------------------------------------------

def svg_band_clip(i):
    cid = f"band{i}"
    x0, x1 = EDGES[i], EDGES[i + 1]
    if not any(cid in d for d in O.defs):
        O.defs.append(f'<clipPath id="{cid}"><rect x="{x0}" y="-200" width="{x1 - x0}" height="{W + 400}" '
                      f'transform="rotate({ANGLE} {C} {C})" /></clipPath>')
    return cid


def band_mask(i):
    """Masque XML en forme de bande i (rien dans l'aperçu : il utilise le clipPath)."""
    O.mode_stack.append(("none", None))
    group_open(f"mask_band{i}", angle=ANGLE, render_mode="MASK")
    draw_open()
    x0, x1 = EDGES[i], EDGES[i + 1]
    rect(x0, 0, x1 - x0, W, "#FFFFFF")
    draw_close()
    group_close()
    O.mode_stack.pop()


def bands(show="normal", name="bands"):
    """Les 4 bandes (Group tourné). Le carré tourné contient tout le disque inscrit."""
    group_open(name, angle=ANGLE, show=show)
    draw_open()
    for i in range(4):
        rect(EDGES[i], 0, EDGES[i + 1] - EDGES[i], W, BAND[i])
    draw_close()
    group_close(show)


# ---------------------------------------------------------------------------
# Couches
# ---------------------------------------------------------------------------

def layer_background():
    O.comment("Bandes diagonales + ombrage de volume (PNG)")
    bands()
    image(0, 0, W, W, "bands_shade", show="normal")


def hour_texts(tag, font, color_h, color_m, show):
    """HH (12 ou 24 h selon la montre) et MM."""
    condition(f"h24_{tag}", "[IS_24_HOUR_MODE]",
              lambda: _digits(HH_C, "[HOUR_0_23_Z]", font, color_h, show),
              lambda: _digits(HH_C, "[HOUR_1_12_Z]", font, color_h, show), True)
    _digits(MM_C, "[MINUTE_Z]", font, color_m, show, wrap=False)


def _digits(center, expr, font, color, show, wrap=True):
    w, h = 250, 170
    cx, cy = center
    sample = SAMPLE["hh"] if "HOUR" in expr else SAMPLE["mm"]
    if wrap:   # enfant d'un Compare / Default : un Group est requis
        group_open(O.gid("d"))
    text(cx - w / 2, cy - h / 2, w, h, ("expr", expr), sample, font, DIGIT_SIZE, color,
         show=show, slant=True)
    if wrap:
        group_close()


def layer_digits():
    O.comment("Chiffres : dessinés une fois par bande, dans l'encre de la bande, découpés par la bande")
    for i in range(4):
        group_open(f"ink{i}", show="normal")
        O.s(f'<g clip-path="url(#{svg_band_clip(i)})">', "normal")
        band_mask(i)
        hour_texts(i, DIGITS, INK[i], INK[i], "both")
        O.s("</g>", "normal")
        group_close("normal")
    O.comment("AOD : chiffres fins sur noir, minutes en accent")
    group_open("digits_aod", show="ambient")
    hour_texts("aod", DIGITS_AOD, "#D5DBE1", ACCENT, "both")
    group_close("ambient")


def layer_seconds():
    O.comment("Secondes : arc au bord")
    draw_open("normal")
    arc(C, C, C - 5, 0, 360, ACCENT, 4, cap="ROUND", end_expr="6 * [SECOND]",
        svg_a1=6 * SAMPLE["s"])
    draw_close("normal")


def dome_background(cx, cy, r):
    """Fond agrandi sous la loupe : bandes x1,2 autour du centre du dôme, découpées en disque."""
    group_open(f"dome_bg_{cx}", show="normal")
    cid = O.gid("lens")
    O.defs.append(f'<clipPath id="{cid}"><circle cx="{cx}" cy="{cy}" r="{r}" /></clipPath>')
    O.s(f'<g clip-path="url(#{cid})">', "normal")
    O.mode_stack.append(("none", None))
    draw_open(x=cx - r, y=cy - r, w=2 * r, h=2 * r, render_mode="MASK")
    circle(cx, cy, r, fill="#FFFFFF")
    draw_close()
    O.mode_stack.pop()
    group_open(f"dome_mag_{cx}", scale=DOME_K, pivot=(cx, cy))
    bands("both", f"bands_mag_{cx}")
    group_close()
    O.s("</g>", "normal")
    group_close("normal")





# ---------------------------------------------------------------------------
# Emplacements (ComplicationSlot) : donnée intégrée si vide, sinon source choisie
# ---------------------------------------------------------------------------

TEXT_TYPES = "SHORT_TEXT RANGED_VALUE GOAL_PROGRESS LONG_TEXT MONOCHROMATIC_IMAGE EMPTY"
GAUGE_TYPES = "RANGED_VALUE GOAL_PROGRESS SHORT_TEXT MONOCHROMATIC_IMAGE EMPTY"
FRAC = {
    "RANGED_VALUE": "([COMPLICATION.RANGED_VALUE_VALUE] - [COMPLICATION.RANGED_VALUE_MIN]) / "
                    "([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN])",
    "GOAL_PROGRESS": "[COMPLICATION.GOAL_PROGRESS_VALUE] / [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE]",
}
CTEXT, CTITLE = ("expr", "[COMPLICATION.TEXT]"), ("expr", "[COMPLICATION.TITLE]")


def slot(sid, name, x, y, w, h, types, builtin, render, oval=False, scale=None):
    """ComplicationSlot masqué en AOD. builtin() : contenu du type EMPTY (seul rendu dans
    l'aperçu) ; render(t) : contenu pour une source de type t (XML seulement)."""
    sc = f' scaleX="{scale}" scaleY="{scale}"' if scale else ""
    O.open(f'<ComplicationSlot slotId="{sid}" x="{x}" y="{y}" width="{w}" height="{h}"{sc} '
           f'supportedTypes="{types}" displayName="{name}" isCustomizable="TRUE">')
    O.x(f'<{"BoundingOval" if oval else "BoundingBox"} x="0" y="0" width="{w}" height="{h}" />')
    O.origin.append((x, y))
    O.mode_stack.append(("normal", None))
    if scale:
        px, py = x + w / 2, y + h / 2
        O.s(f'<g transform="translate({f(px)} {f(py)}) scale({scale}) translate({f(-px)} {f(-py)})">')
    for t in types.split():
        O.open(f'<Complication type="{t}">')
        if t == "EMPTY":
            builtin()
        else:
            O.mode_stack.append(("none", None))
            render(t)
            O.mode_stack.pop()
        O.close("</Complication>")
    if scale:
        O.s("</g>")
    O.mode_stack.pop()
    O.origin.pop()
    O.x('<Variant mode="AMBIENT" target="alpha" value="0" />')
    O.close("</ComplicationSlot>")


def box_draw(x, y, w, h, alpha=None):
    """PartDraw local (x / y entiers) couvrant la zone x, y, w, h."""
    x0, y0 = int(math.floor(x)), int(math.floor(y))
    draw_open(x=x0, y=y0, w=int(math.ceil(x + w)) - x0, h=int(math.ceil(y + h)) - y0, alpha=alpha)


def value_unit(cx, y, h, content, sample, unit, size, color, unit_size=None):
    """Valeur centrée suivie d'une petite unité (« % », « ° ») : la valeur s'aligne à droite
    sur cx + d, l'unité à gauche juste après (pas de « %% » dans les gabarits)."""
    us = unit_size or round(size * 0.6)
    d = round(us * 0.3)
    text(cx - 60 + d, y, 60, h, content, sample, DATA, size, color, align="END")
    text(cx + d + 1, y + (h - us) / 2 - size * 0.12, 30, us * 1.3, unit, unit, DATA, us, color, align="START")


def gauge(cx, cy, r, frac_expr, frac_sample, value, label, soft, track, color, icon=None, comp_ic=False):
    """Jauge en arc 270° : piste, valeur au centre, pictogramme au-dessus, libellé dans
    l'ouverture. value : callable(cx, y, h) qui dessine la valeur."""
    a0, a1 = -135, 135
    box_draw(cx - r - 4, cy - r - 4, 2 * r + 8, 2 * r + 8, alpha=track[1])
    arc(cx, cy, r, a0, a1, track[0], 6, cap="ROUND")
    draw_close()
    box_draw(cx - r - 4, cy - r - 4, 2 * r + 8, 2 * r + 8)
    arc(cx, cy, r, a0, a1, color, 6, cap="ROUND",
        end_expr=f"{a0} + {a1 - a0} * clamp({frac_expr}, 0, 1)",
        svg_a1=a0 + (a1 - a0) * frac_sample)
    draw_close()
    if icon:
        icon_img(cx, cy - 13, 15, icon, color)
    elif comp_ic:
        comp_icon(cx, cy - 13, 14, color)
    value(cx, cy - 1, 26)
    text(cx - 30, cy + r - 9, 60, 16, label, label if isinstance(label, str) else "", DATA_M, 11,
         soft[0], alpha=soft[1], spacing="0.12")


def icon_img(cx, cy, size, name, tint):
    image(cx - size / 2, cy - size / 2, size, size, f"ic_{name}", tint=tint)


def comp_icon(cx, cy, size, tint):
    """Icône monochrome fournie par la source de données (XML seulement)."""
    rx, ry = rel(cx - size / 2, cy - size / 2)
    O.open(f'<PartImage {wff._box(rx, ry, size, size)} tintColor="{tint}">')
    O.x('<Image resource="[COMPLICATION.MONOCHROMATIC_IMAGE]" />')
    O.close("</PartImage>")


def dome_slot(sid, name, center, gr, ink, soft, track, color, builtin):
    cx, cy = center
    x, y, s = cx - DOME_R + 4, cy - DOME_R + 4, 2 * DOME_R - 8

    def render(t):
        if t in FRAC:
            gauge(cx, cy - 2, gr, FRAC[t], 0.5,
                  lambda x_, y_, h_: text(x_ - 30, y_, 60, h_, CTEXT, "", DATA, 20, ink),
                  CTITLE, soft, track, color, comp_ic=True)
        elif t == "SHORT_TEXT":
            comp_icon(cx, cy - 16, 16, color)
            text(cx - 32, cy - 4, 64, 26, CTEXT, "", DATA, 20, ink)
            text(cx - 30, cy + 18, 60, 16, CTITLE, "", DATA_M, 11, soft[0], alpha=soft[1])
        elif t == "MONOCHROMATIC_IMAGE":
            comp_icon(cx, cy, 30, color)

    O.comment(f"Dôme {name} : ombre, fond agrandi, emplacement agrandi x{DOME_K}, verre")
    image(cx - DOME_R - 14 + 3, cy - DOME_R - 14 + 5, 2 * DOME_R + 28, 2 * DOME_R + 28, "dome_shadow",
          show="normal")
    dome_background(cx, cy, DOME_R)
    slot(sid, name, x, y, s, s, GAUGE_TYPES, builtin, render, oval=True, scale=DOME_K)
    image(cx - DOME_R - 2, cy - DOME_R - 2, 2 * DOME_R + 4, 2 * DOME_R + 4, "dome_glass", show="normal")


def text_slot(sid, name, x, y, w, h, ink, soft, tint, builtin, big=26, centered=False):
    """Emplacement texte : source au choix = icône + texte + titre."""
    def render(t):
        if t in ("SHORT_TEXT", "LONG_TEXT", "RANGED_VALUE", "GOAL_PROGRESS"):
            if centered:   # colonne droite : icône au-dessus, valeur, titre
                comp_icon(x + w / 2, y + 12, 18, tint)
                text(x, y + 22, w, 36, CTEXT, "", DATA, big, ink)
                text(x, y + h - 16, w, 16, CTITLE, "", DATA_M, 12, soft[0], alpha=soft[1], spacing="0.12")
            else:          # colonne gauche : icône à gauche, valeur, titre dessous
                comp_icon(x + 16, y + h / 2, 22, tint)
                text(x + 32, y, w - 32, h * 0.62, CTEXT, "", DATA, big, ink, align="START")
                text(x + 32, y + h * 0.6, w - 32, h * 0.4, CTITLE, "", DATA_M, 12, soft[0], alpha=soft[1], align="START",
                     spacing="0.1")
        elif t == "MONOCHROMATIC_IMAGE":
            comp_icon(x + w / 2, y + h / 2, min(w, h) - 12, tint)
    slot(sid, name, x, y, w, h, TEXT_TYPES, builtin, render)


# --- Données intégrées --------------------------------------------------------

def builtin_date():
    # « 02 OCT » en gros (jour du mois en accent), jour de la semaine en petit dessous
    text(30, 108, 56, 44, ("expr", "[DAY_Z]"), SAMPLE["day"], DATA, 36, ACCENT, align="END")
    text(90, 116, 56, 34, ("expr", "[MONTH_S]"), SAMPLE["mon"], DATA, 22, INK[0], align="START", upper=True)
    text(30, 145, 116, 20, ("expr", "[DAY_OF_WEEK_F]"), SAMPLE["dow"], DATA_M, 15, SOFT_D[0], alpha=SOFT_D[1], align="START",
         upper=True, spacing="0.13")


WEATHER_ICONS = [  # [WEATHER.CONDITION] -> pictogramme (défaut : nuage)
    ((1, 8), "sun"), ((14,), "partly"), ((4, 6, 12), "rain"), ((5, 7, 10, 11), "snow"),
    ((9,), "storm"), ((3, 13), "fog"),
]


def builtin_weather():
    ix, iy, isz = 46, 185, 26
    O.open("<Condition>")
    O.open("<Expressions>")
    for k, (codes, _) in enumerate(WEATHER_ICONS):
        expr = " || ".join(f"[WEATHER.CONDITION] == {c}" for c in codes)
        O.x(f'<Expression name="w{k}"><![CDATA[{expr}]]></Expression>')
    O.close("</Expressions>")
    for k, (_, ic) in enumerate(WEATHER_ICONS):
        O.open(f'<Compare expression="w{k}">')
        O.mode_stack.append(("both", None) if ic == "sun" else ("none", None))
        group_open(O.gid("wi"))
        icon_img(ix, iy, isz, ic, ACCENT)
        group_close()
        O.mode_stack.pop()
        O.close("</Compare>")
    O.open("<Default>")
    O.mode_stack.append(("none", None))
    group_open(O.gid("wi"))
    icon_img(ix, iy, isz, "cloud", ACCENT)
    group_close()
    O.mode_stack.pop()
    O.close("</Default>")
    O.close("</Condition>")

    condition("w_ok", "[WEATHER.IS_AVAILABLE]",
              lambda: _group(lambda: text(64, 168, 70, 36, ("expr", "[WEATHER.TEMPERATURE]"),
                                          f"{SAMPLE['temp']}°", DATA, 28, INK[0], align="START",
                                          fmt="%s°")),
              lambda: _group(lambda: text(64, 168, 70, 36, "--", "--", DATA, 28, INK[0], align="START")),
              True)


def _group(fn):
    group_open(O.gid("g"))
    fn()
    group_close()


def builtin_uv():
    gauge(DOME_BL[0], DOME_BL[1] - 2, 30, "[WEATHER.UV_INDEX] / 11", SAMPLE["uv"] / 11,
          lambda x, y, h: text(x - 30, y, 60, h, ("expr", "[WEATHER.UV_INDEX]"), SAMPLE["uv"], DATA, 20, INK[0]),
          "UV", SOFT_D, TRACK_D, ACCENT, "uv")


def builtin_rain():
    gauge(DOME_TR[0], DOME_TR[1] - 2, 28, "[WEATHER.CHANCE_OF_PRECIPITATION] / 100", SAMPLE["rain"] / 100,
          lambda x, y, h: value_unit(x, y, h, ("expr", "[WEATHER.CHANCE_OF_PRECIPITATION]"), SAMPLE["rain"],
                                     "%", 20, INK[3], 12),
          "PLUIE", SOFT_L, TRACK_L, BAND[2], "drop")


def builtin_hr():
    icon_img(371, 191, 18, "heart", BAND[2])
    condition("hr_ok", "[HEART_RATE] > 0",
              lambda: _group(lambda: text(338, 202, 66, 40, ("expr", "[HEART_RATE]"), SAMPLE["hr"], DATA, 32,
                                          INK[3])),
              lambda: _group(lambda: text(338, 202, 66, 40, "--", "--", DATA, 32, INK[3])), True)
    text(340, 236, 60, 16, "BPM", "BPM", DATA_M, 12, SOFT_L[0], alpha=SOFT_L[1], spacing="0.17")


def builtin_battery():
    box_draw(356, 268, 30, 16)
    rrect(358, 270, 22, 12, 2.5, "#00000000", stroke=INK[3], th=1.8)
    rect(380.5, 273.5, 2.5, 5, INK[3])
    rect(360.5, 272.5, 17, 7, BAND[2], width_expr="17 * [BATTERY_PERCENT] / 100",
         svg_w=17 * SAMPLE["batt"] / 100)
    draw_close()
    value_unit(370, 288, 34, ("expr", "[BATTERY_PERCENT]"), SAMPLE["batt"], "%", 26, INK[3], 15)


SEG_N, SEG_W, SEG_GAP, SEG_H, SEG_Y = 10, 14, 3.5, 12, 377
SEG_X0 = C - (SEG_N * (SEG_W + SEG_GAP) - SEG_GAP) / 2 - 8


def steps_bar(frac_expr, frac_sample, pct):
    """10 segments penchés comme les bandes (traits épais inclinés) + pourcentage.
    Segment plein : accent ; segment entamé : accent à demi ; reste : noir translucide."""
    dx = SEG_H * math.tan(math.radians(ANGLE))
    x_end = SEG_X0 + SEG_N * (SEG_W + SEG_GAP)

    def seg(i, color):
        # parallélogramme (côtés penchés comme les bandes) : traits horizontaux empilés
        x = SEG_X0 + i * (SEG_W + SEG_GAP)
        n = 12
        for k in range(n):
            yk = SEG_Y + SEG_H * (k + 0.5) / n
            sh = dx * (1 - (k + 0.5) / n) - dx / 2
            line(x + sh, yk, x + sh + SEG_W, yk, color, 2, cap="BUTT")   # traits qui se chevauchent : pas de jour

    box_draw(SEG_X0 - 6, SEG_Y - 2, x_end - SEG_X0 + 12, SEG_H + 4, alpha=72)
    for i in range(SEG_N):
        seg(i, "#000000")   # couleurs opaques : la transparence est celle du PartDraw entier
    draw_close()
    for i in range(SEG_N):
        lit = f"(({frac_expr}) * 10 - {i})"
        level = min(max(frac_sample * 10 - i, 0), 1)
        O.mode_stack.append(("none", None) if level <= 0 else ("both", None))
        box_draw(SEG_X0 + i * (SEG_W + SEG_GAP) - 4, SEG_Y - 2, SEG_W + 8, SEG_H + 4)
        O.x(f'<Transform target="alpha" value="{escape(f"{lit} >= 1 ? 255 : ({lit} > 0 ? 140 : 0)")}" />')
        O.svg["normal"][-1] = O.svg["normal"][-1].replace("<g>", f'<g opacity="{1 if level >= 1 else 0.55}">') \
            if level > 0 else O.svg["normal"][-1]
        seg(i, ACCENT)
        draw_close()
        O.mode_stack.pop()
    pct(x_end + 2, SEG_Y - 5, 22)


def builtin_steps():
    icon_img(C - 66, 352, 22, "steps", ACCENT)
    text(C - 52, 336, 72, 34, ("expr", "[STEP_COUNT]"), SAMPLE["steps"], DATA, 26, INK[1], align="START")
    text(C + 12, 342, 40, 26, "PAS", "PAS", DATA_M, 13, INK[1], align="START", spacing="0.15")
    steps_bar("[STEP_PERCENT] / 100", SAMPLE["pct"] / 100,
              lambda x, y, h: _pct_after(x, y, h, ("expr", "[STEP_PERCENT]"), SAMPLE["pct"]))


def _pct_after(x, y, h, content, sample):
    text(x, y, 28, h, content, sample, DATA, 17, INK[2], align="END")
    text(x + 29, y + 4, 14, h - 6, "%", "%", DATA, 11, INK[2], align="START")


def layer_slots():
    O.comment("Emplacement 1 — date (intégrée) ou source au choix")
    text_slot(1, "slot_date", 30, 104, 118, 62, INK[0], SOFT_D, ACCENT, builtin_date, big=30)
    O.comment("Emplacement 2 — météo (intégrée) ou source au choix")
    text_slot(2, "slot_left", 30, 168, 112, 38, INK[0], SOFT_D, ACCENT, builtin_weather, big=26)
    O.comment("Emplacement 3 — dôme bas gauche : indice UV (intégré) ou source au choix")
    dome_slot(3, "slot_dome_bl", DOME_BL, 30, INK[0], SOFT_D, TRACK_D, ACCENT, builtin_uv)
    O.comment("Emplacement 4 — dôme haut droite : pluie (intégrée) ou source au choix")
    dome_slot(4, "slot_dome_tr", DOME_TR, 28, INK[3], SOFT_L, TRACK_L, BAND[2], builtin_rain)
    O.comment("Emplacement 5 — cardio (intégré) ou source au choix")
    text_slot(5, "slot_right", 336, 178, 70, 76, INK[3], SOFT_L, BAND[2], builtin_hr, big=28, centered=True)
    O.comment("Emplacement 6 — batterie (intégrée) ou source au choix")
    text_slot(6, "slot_right2", 336, 264, 70, 60, INK[3], SOFT_L, BAND[2], builtin_battery, big=24, centered=True)
    O.comment("Emplacement 7 — pas (intégrés) ou source au choix")

    def steps_render(t):
        comp_icon(C - 66, 352, 22, ACCENT)
        text(C - 52, 336, 150, 34, CTEXT, "", DATA, 26, INK[1], align="START")
        if t in FRAC:
            steps_bar(FRAC[t], 0.5,
                      lambda x, y, h: _pct_after(x, y, h, ("expr", f"round(100 * clamp({FRAC[t]}, 0, 1))"), ""))
    slot(7, "slot_bottom", 112, 334, 236, 62,
         "GOAL_PROGRESS RANGED_VALUE SHORT_TEXT LONG_TEXT EMPTY", builtin_steps, steps_render)


def layer_aod():
    O.comment("AOD : date, cardio, batterie, pas en texte simple sur noir")
    group_open("aod_data", show="ambient")
    text(30, 108, 56, 44, ("expr", "[DAY_Z]"), SAMPLE["day"], DATA, 34, ACCENT, align="END")
    text(90, 116, 56, 34, ("expr", "[MONTH_S]"), SAMPLE["mon"], DATA, 20, "#C9D1D9", align="START", upper=True)
    text(30, 145, 116, 20, ("expr", "[DAY_OF_WEEK_F]"), SAMPLE["dow"], DATA_M, 14, "#7D8791", align="START",
         upper=True, spacing="0.13")
    text(338, 196, 66, 40, ("expr", "[HEART_RATE]"), SAMPLE["hr"], DATA, 28, "#C9D1D9")
    text(340, 230, 60, 16, "BPM", "BPM", DATA_M, 11, "#7D8791", spacing="0.17")
    value_unit(370, 280, 34, ("expr", "[BATTERY_PERCENT]"), SAMPLE["batt"], "%", 24, "#C9D1D9", 14)
    text(C - 70, 348, 140, 30, ("expr", "[STEP_COUNT]"), SAMPLE["steps"], DATA, 22, "#C9D1D9")
    group_close("ambient")


def build():
    layer_background()
    layer_digits()
    layer_seconds()
    layer_slots()
    layer_aod()


# ---------------------------------------------------------------------------
# PNG : ombrage des bandes, verre et ombre des dômes (RGBA, stdlib)
# ---------------------------------------------------------------------------

def png_rgba(path, w, h, px):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw += bytes(px(x, y))

    def chunk(kind, data):
        c = struct.pack(">I", len(data)) + kind + data
        return c + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def _over(dst, src):
    """Composition « over » de deux pixels RGBA (0-255)."""
    sa, da = src[3] / 255, dst[3] / 255
    oa = sa + da * (1 - sa)
    if oa <= 0:
        return (0, 0, 0, 0)
    rgb = [round((src[i] * sa + dst[i] * da * (1 - sa)) / oa) for i in range(3)]
    return (*rgb, round(oa * 255))


def _smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def write_pngs():
    out = os.path.join(RES, "drawable-nodpi")
    os.makedirs(out, exist_ok=True)
    ca, sa = math.cos(math.radians(-ANGLE)), math.sin(math.radians(-ANGLE))

    def shade(x, y):
        # repère des bandes : rotation inverse autour du centre
        bx = C + (x - C) * ca - (y - C) * sa
        for i in range(1, 4):
            x0, x1 = EDGES[i], EDGES[i + 1]
            if x0 <= bx < x1:
                t = (bx - x0) / (x1 - x0)
                if t < 0.25:
                    return (0, 0, 0, round(56 * (1 - t / 0.25)))
                return (255, 255, 255, round(13 * (t - 0.25) / 0.75))
        return (0, 0, 0, 0)
    png_rgba(os.path.join(out, "bands_shade.png"), W, W, shade)

    R = DOME_R
    s = 2 * R + 4
    hx, hy = -0.3 * R, -0.42 * R
    cr, sr = math.cos(math.radians(30)), math.sin(math.radians(30))

    def glass(x, y):
        dx, dy = x - s / 2 + 0.5, y - s / 2 + 0.5
        d = math.hypot(dx, dy)
        px = (0, 0, 0, 0)
        if d <= R:
            # bord assombri (réfraction)
            k = _smooth(0.72 * R, 0.93 * R, d) * 0.28 + _smooth(0.93 * R, R, d) * 0.27
            px = _over(px, (0, 0, 0, round(255 * k)))
            # reflet : ellipse floue en haut à gauche, inclinée de -30°
            ex, ey = dx - hx, dy - hy
            u, v = ex * cr + ey * sr, -ex * sr + ey * cr
            q = (u / (0.5 * R)) ** 2 + (v / (0.28 * R)) ** 2
            if q < 1:
                px = _over(px, (255, 255, 255, round(140 * (1 - q) ** 1.5)))
            # croissant de lumière en bas à droite
            ang = math.degrees(math.atan2(dx, -dy)) % 360
            if 100 <= ang <= 170:
                band = max(0.0, 1 - abs(d - 0.9 * R) / 1.3)
                px = _over(px, (255, 255, 255, round(90 * band)))
            # filet intérieur clair
            px = _over(px, (255, 255, 255, round(115 * max(0.0, 1 - abs(d - (R - 0.6)) / 0.8))))
        # filet extérieur sombre
        px = _over(px, (0, 0, 0, round(90 * max(0.0, 1 - abs(d - (R + 0.8)) / 0.9))))
        return px
    png_rgba(os.path.join(out, "dome_glass.png"), s, s, glass)

    sw = 2 * R + 28

    def shadow(x, y):
        d = math.hypot(x - sw / 2 + 0.5, y - sw / 2 + 0.5)
        return (0, 0, 0, round(97 * (1 - _smooth(R - 6, R + 9, d))))
    png_rgba(os.path.join(out, "dome_shadow.png"), sw, sw, shadow)


# ---------------------------------------------------------------------------
# Écriture
# ---------------------------------------------------------------------------

def config_xml():
    lines = ['  <UserConfigurations>',
             '    <ColorConfiguration id="palette" displayName="cfg_palette" defaultValue="0">']
    for i, (name, bands_, accent) in enumerate(PALETTES):
        lines.append(f'      <ColorOption id="{i}" displayName="{name}" '
                     f'colors="{" ".join(palette_colors(bands_, accent))}" />')
    lines += ['    </ColorConfiguration>', '  </UserConfigurations>']
    return lines


def write():
    check_contrast()
    build()
    write_pngs()
    head = ['<?xml version="1.0" encoding="utf-8"?>',
            "<!-- Prisme — cadran Watch Face Format, 438 x 438, Galaxy Watch8 Classic 46 mm.",
            "     FICHIER GÉNÉRÉ par prisme/tools/generate.py : ne pas éditer à la main. -->",
            f'<WatchFace width="{W}" height="{W}" clipShape="CIRCLE">',
            '  <Metadata key="CLOCK_TYPE" value="DIGITAL" />',
            '  <Metadata key="PREVIEW_TIME" value="10:09:36" />',
            ""]
    body = head + config_xml() + ["", "  <Scene>"] + O.xml + ["", "  </Scene>", "</WatchFace>", ""]
    os.makedirs(os.path.join(RES, "raw"), exist_ok=True)
    with open(os.path.join(RES, "raw", "watchface.xml"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(body))

    fonts = os.path.join(os.path.abspath(RES), "font")
    faces = "".join(f"@font-face {{ font-family: {fam}; src: url('file://{fonts}/{res}.ttf'); }}\n"
                    for res, fam in wff.FONTS.items())
    for mode, frags in O.svg.items():
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{W}" viewBox="0 0 {W} {W}">',
               f"<style>{faces}</style>",
               f"<defs>{''.join(O.defs)}<clipPath id='face'><circle cx='{C}' cy='{C}' r='{C}' />"
               "</clipPath></defs>",
               f'<g clip-path="url(#face)"><rect width="{W}" height="{W}" fill="#000" />']
        svg += frags + ["</g></svg>", ""]
        name = "preview.svg" if mode == "normal" else "preview_ambient.svg"
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as fh:
            fh.write("\n".join(svg))


if __name__ == "__main__":
    write()
