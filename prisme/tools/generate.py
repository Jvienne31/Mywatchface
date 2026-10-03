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
                 line, rrect, text, group_open, group_close, image, condition, list_config)

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
HH_C, MM_C = (C - 22, 128), (C + 24, 266)   # centres des deux lignes de chiffres
DIGIT_SIZE = 160
OUTLINE_R, OUTLINE_N = 4.5, 12              # contour des chiffres : 12 copies décalées
MINUTE_TINT = 55                            # minutes : voile d'accent (0-255) sur le clair
DOME_TR, DOME_BL, DOME_R, DOME_K = (354, 122), (66, 268), 50, 1.2
SAMPLE = {"hh": "10", "mm": "09", "s": 36, "day": "02", "mon": "OCT", "dow": "VENDREDI",
          "temp": 18, "rain": 20, "uv": 3, "hr": 72, "batt": 86, "steps": 6420, "pct": 64}

# ---------------------------------------------------------------------------
# Masques : l'aperçu SVG utilise des clipPath, le XML des Group renderMode="MASK"
# ---------------------------------------------------------------------------

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


def hour_texts(tag, draw):
    """HH (12 ou 24 h selon la montre) et MM. draw(center, expr, is_minute)."""
    condition(f"h24_{tag}", "[IS_24_HOUR_MODE]",
              lambda: _group(lambda: draw(HH_C, "[HOUR_0_23_Z]", False)),
              lambda: _group(lambda: draw(HH_C, "[HOUR_1_12_Z]", False)), True)
    draw(MM_C, "[MINUTE_Z]", True)


def _digit(center, expr, font, color, dx=0, dy=0, alpha=None):
    w, h = 250, 170
    cx, cy = center
    sample = SAMPLE["hh"] if "HOUR" in expr else SAMPLE["mm"]
    text(cx - w / 2 + dx, cy - h / 2 + dy, w, h, ("expr", expr), sample, font, DIGIT_SIZE, color,
         alpha=alpha, slant=True)


def outlined_digits(center, expr, is_minute):
    """Chiffres clairs, contour sombre, ombre portée ; minutes voilées d'accent.
    Le contour (Font > Outline) n'est pas rendu sur la montre : il est fait de 12 copies
    du chiffre décalées en cercle dans la couleur sombre, sous le chiffre."""
    _digit(center, expr, DIGITS, "#000000", 3, 6, alpha=110)          # ombre
    for k in range(OUTLINE_N):
        a = 2 * math.pi * k / OUTLINE_N
        _digit(center, expr, DIGITS, BAND[0], OUTLINE_R * math.cos(a), OUTLINE_R * math.sin(a))
    _digit(center, expr, DIGITS, BAND[3])
    if is_minute:
        _digit(center, expr, DIGITS, ACCENT, alpha=MINUTE_TINT)


def layer_digits():
    O.comment("Chiffres : clairs, contour sombre (copies décalées), ombre ; minutes teintées d'accent")
    group_open("digits", show="normal")
    hour_texts("n", outlined_digits)
    group_close("normal")
    O.comment("AOD : chiffres fins sur noir, minutes en accent")
    group_open("digits_aod", show="ambient")
    hour_texts("aod", lambda c, e, m: _digit(c, e, DIGITS_AOD, ACCENT if m else "#D5DBE1"))
    group_close("ambient")


SECONDS_OPTIONS = [("sec_arc", "Arc"), ("sec_dot", "Point"), ("sec_none", "Aucune")]


def layer_seconds():
    O.comment("Secondes au choix (réglage) : arc qui se remplit, point qui tourne, ou rien")

    def sec_arc():
        draw_open("normal")
        arc(C, C, C - 5, 0, 360, ACCENT, 4, cap="ROUND", end_expr="6 * [SECOND]",
            svg_a1=6 * SAMPLE["s"])
        draw_close("normal")

    def sec_dot():
        draw_open("normal", angle_expr="6 * [SECOND]", svg_angle=6 * SAMPLE["s"])
        circle(C, 8, 5, fill=ACCENT)
        draw_close("normal")

    list_config("secondes", [sec_arc, sec_dot, lambda: None])


def dome_background(cx, cy, r, color):
    """Fond du dôme : disque uni de la couleur de la bande où il se trouve. (Les bandes
    agrandies laissaient un croissant de la bande voisine au bord du dôme haut.)"""
    box_draw(cx - r, cy - r, 2 * r, 2 * r, show="normal")
    circle(cx, cy, r, fill=color)
    draw_close("normal")





# ---------------------------------------------------------------------------
# Emplacements (ComplicationSlot) : donnée intégrée si vide, sinon source choisie
# ---------------------------------------------------------------------------

# Tous les types du format sur chaque emplacement : le sélecteur ne propose une source que si
# l'un de ses types est accepté (une donnée publiée seulement en image ou en graphique
# serait sinon invisible).
IMAGE_TYPES = "SMALL_IMAGE PHOTO_IMAGE WEIGHTED_ELEMENTS"
# Applis ouvertes au toucher des données intégrées (Launch : nom de paquet ou raccourci système)
APP_WEATHER = "com.samsung.android.watch.weather"   # Météo Samsung
APP_HEALTH = "com.samsung.android.wear.shealth"     # Samsung Health (montre)

TEXT_TYPES = f"SHORT_TEXT RANGED_VALUE GOAL_PROGRESS LONG_TEXT MONOCHROMATIC_IMAGE {IMAGE_TYPES} EMPTY"
GAUGE_TYPES = f"RANGED_VALUE GOAL_PROGRESS SHORT_TEXT LONG_TEXT MONOCHROMATIC_IMAGE {IMAGE_TYPES} EMPTY"
FRAC = {
    "RANGED_VALUE": "([COMPLICATION.RANGED_VALUE_VALUE] - [COMPLICATION.RANGED_VALUE_MIN]) / "
                    "([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN])",
    "GOAL_PROGRESS": "[COMPLICATION.GOAL_PROGRESS_VALUE] / [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE]",
}
CTEXT, CTITLE = ("expr", "[COMPLICATION.TEXT]"), ("expr", "[COMPLICATION.TITLE]")


def slot(sid, name, x, y, w, h, types, builtin, render, oval=False, scale=None, launch=None):
    """Donnée intégrée dessinée sur le cadran + ComplicationSlot par-dessus (masqués en AOD).

    Le moteur de la montre ne dessine pas la branche EMPTY d'un emplacement sans source
    (constaté sur émulateur) : la donnée intégrée est donc hors de l'emplacement. Quand une
    source est choisie, l'emplacement redessine d'abord le fond (bandes découpées à sa forme)
    pour cacher la donnée intégrée, puis la donnée de la source. render(t) : XML seulement."""
    px, py = x + w / 2, y + h / 2
    # zone sensible = l'emplacement : toucher la donnée intégrée ouvre l'appli correspondante
    group_open(f"data{sid}", x, y, w, h, show="normal", launch=launch, scale=scale,
               pivot=(px, py) if scale else None)
    builtin()
    group_close("normal")

    sc = f' scaleX="{scale}" scaleY="{scale}"' if scale else ""
    O.open(f'<ComplicationSlot slotId="{sid}" x="{x}" y="{y}" width="{w}" height="{h}"{sc} '
           f'supportedTypes="{types}" displayName="{name}" isCustomizable="TRUE">')
    O.x(f'<{"BoundingOval" if oval else "BoundingBox"} x="0" y="0" width="{w}" height="{h}" />')
    O.origin.append((x, y))
    O.mode_stack.append(("none", None))
    for t in types.split():
        if t == "EMPTY":
            O.x('<Complication type="EMPTY" />')
            continue
        O.open(f'<Complication type="{t}">')
        patch(f"patch{sid}_{t.lower()}", x, y, w, h, oval)
        if t in ("SMALL_IMAGE", "PHOTO_IMAGE"):
            source_image(t, x, y, w, h, oval)
        elif t == "WEIGHTED_ELEMENTS":   # graphique de la source non dessiné : son texte
            render("SHORT_TEXT")
        else:
            render(t)
        O.close("</Complication>")
    O.mode_stack.pop()
    O.origin.pop()
    O.x('<Variant mode="AMBIENT" target="alpha" value="0" />')
    O.close("</ComplicationSlot>")


def source_image(t, x, y, w, h, oval):
    """Image fournie par la source (vignette ou photo), centrée ; carré inscrit si dôme."""
    side = min(w, h) * (0.7 if oval else 1)
    rx, ry = rel(x + (w - side) / 2, y + (h - side) / 2)
    O.open(f'<PartImage {wff._box(rx, ry, side, side)}>')
    O.x(f'<Image resource="[COMPLICATION.{t}]" />')
    O.close("</PartImage>")


def patch(name, x, y, w, h, oval):
    """Fond du cadran découpé à la forme de l'emplacement : cache la donnée intégrée dessous.
    oval : couleur unie du dôme ; sinon bandes + ombrage découpés au rectangle."""
    if oval:
        box_draw(x, y, w, h)
        circle(x + w / 2, y + h / 2, DOME_R / DOME_K, fill=oval)   # x1,2 par la loupe = rayon du dôme
        draw_close()
        return
    group_open(name, x, y, w, h)
    draw_open(x=x, y=y, w=w, h=h, render_mode="MASK")
    rect(x, y, w, h, "#FFFFFF")
    draw_close()
    bands("both", f"{name}_bands")
    image(0, 0, W, W, "bands_shade")
    group_close()


def box_draw(x, y, w, h, alpha=None, show="both"):
    """PartDraw local (x / y entiers) couvrant la zone x, y, w, h."""
    x0, y0 = int(math.floor(x)), int(math.floor(y))
    draw_open(x=x0, y=y0, w=int(math.ceil(x + w)) - x0, h=int(math.ceil(y + h)) - y0, alpha=alpha, show=show)


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
    box_draw(cx - r - 5, cy - r - 5, 2 * r + 10, 2 * r + 10, alpha=track[1])
    arc(cx, cy, r, a0, a1, track[0], 7, cap="ROUND")
    draw_close()
    box_draw(cx - r - 5, cy - r - 5, 2 * r + 10, 2 * r + 10)
    arc(cx, cy, r, a0, a1, color, 7, cap="ROUND",
        end_expr=f"{a0} + {a1 - a0} * clamp({frac_expr}, 0, 1)",
        svg_a1=a0 + (a1 - a0) * frac_sample)
    draw_close()
    if icon:
        icon_img(cx, cy - 16, 16, icon, color)
    elif comp_ic:
        comp_icon(cx, cy - 16, 16, color)
    value(cx, cy - 13, 32)
    text(cx - 34, cy + r - 11, 68, 17, label, label if isinstance(label, str) else "", DATA_M, 13,
         soft[0], alpha=soft[1], spacing="0.1")


def icon_img(cx, cy, size, name, tint):
    image(cx - size / 2, cy - size / 2, size, size, f"ic_{name}", tint=tint)


def comp_icon(cx, cy, size, tint):
    """Icône monochrome fournie par la source de données (XML seulement)."""
    rx, ry = rel(cx - size / 2, cy - size / 2)
    O.open(f'<PartImage {wff._box(rx, ry, size, size)} tintColor="{tint}">')
    O.x('<Image resource="[COMPLICATION.MONOCHROMATIC_IMAGE]" />')
    O.close("</PartImage>")


def dome_slot(sid, name, center, gr, ink, soft, track, color, builtin, launch=None):
    cx, cy = center
    x, y, s = cx - DOME_R + 4, cy - DOME_R + 4, 2 * DOME_R - 8

    def render(t):
        if t in FRAC:
            gauge(cx, cy - 2, gr, FRAC[t], 0.5,
                  lambda x_, y_, h_: text(x_ - 34, y_, 68, h_, CTEXT, "", DATA, 22, ink),
                  CTITLE, soft, track, color, comp_ic=True)
        elif t in ("SHORT_TEXT", "LONG_TEXT"):   # texte plus large : « 6h 29m » ne doit pas être tronqué
            comp_icon(cx, cy - 19, 18, color)
            text(cx - 40, cy - 9, 80, 30, CTEXT, "", DATA, 22, ink)
            text(cx - 38, cy + 18, 76, 17, CTITLE, "", DATA_M, 13, soft[0], alpha=soft[1])
        elif t == "MONOCHROMATIC_IMAGE":
            comp_icon(cx, cy, 30, color)

    O.comment(f"Dôme {name} : ombre, fond agrandi, emplacement agrandi x{DOME_K}, verre")
    image(cx - DOME_R - 14 + 3, cy - DOME_R - 14 + 5, 2 * DOME_R + 28, 2 * DOME_R + 28, "dome_shadow",
          show="normal")
    bg = BAND[0] if sid == 3 else BAND[3]   # bande sous le dôme (bas gauche : 0, haut droite : 3)
    dome_background(cx, cy, DOME_R, bg)
    slot(sid, name, x, y, s, s, GAUGE_TYPES, builtin, render, oval=bg, scale=DOME_K, launch=launch)
    image(cx - DOME_R - 2, cy - DOME_R - 2, 2 * DOME_R + 4, 2 * DOME_R + 4, "dome_glass", show="normal")


def text_slot(sid, name, x, y, w, h, ink, soft, tint, builtin, big=26, centered=False, launch=None):
    """Emplacement texte : source au choix = icône + texte + titre."""
    def render(t):
        if t in ("SHORT_TEXT", "LONG_TEXT", "RANGED_VALUE", "GOAL_PROGRESS"):
            if centered:   # colonne droite : icône au-dessus, valeur, titre
                comp_icon(x + w / 2, y + 12, 22, tint)
                text(x, y + 24, w, big + 6, CTEXT, "", DATA, big, ink)
                text(x, y + h - 18, w, 18, CTITLE, "", DATA_M, 14, soft[0], alpha=soft[1], spacing="0.1")
            else:          # colonne gauche : icône à gauche, valeur, titre dessous
                comp_icon(x + 18, y + h / 2, 28, tint)
                text(x + 38, y, w - 38, h * 0.62, CTEXT, "", DATA, big, ink, align="START")
                text(x + 38, y + h * 0.6, w - 38, h * 0.4, CTITLE, "", DATA_M, 14, soft[0], alpha=soft[1],
                     align="START", spacing="0.1")
        elif t == "MONOCHROMATIC_IMAGE":
            comp_icon(x + w / 2, y + h / 2, min(w, h) - 12, tint)
    slot(sid, name, x, y, w, h, TEXT_TYPES, builtin, render, launch=launch)


# --- Données intégrées --------------------------------------------------------

def builtin_date():
    # « 02 OCT » en gros (jour du mois en accent), jour de la semaine en petit dessous
    text(30, 100, 52, 46, ("expr", "[DAY_Z]"), SAMPLE["day"], DATA, 48, ACCENT, align="END")
    text(87, 113, 66, 34, ("expr", "[MONTH_S]"), SAMPLE["mon"], DATA, 28, INK[0], align="START", upper=True)
    text(38, 149, 122, 21, ("expr", "[DAY_OF_WEEK_F]"), SAMPLE["dow"], DATA_M, 18, SOFT_D[0], alpha=SOFT_D[1],
         align="START", upper=True, spacing="0.08")


WEATHER_ICONS = [  # [WEATHER.CONDITION] -> pictogramme (défaut : nuage)
    ((1, 8), "sun"), ((14,), "partly"), ((4, 6, 12), "rain"), ((5, 7, 10, 11), "snow"),
    ((9,), "storm"), ((3, 13), "fog"),
]


def builtin_weather():
    ix, iy, isz = 52, 192, 32
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
              lambda: _group(lambda: text(74, 172, 84, 42, ("expr", "[WEATHER.TEMPERATURE]"),
                                          f"{SAMPLE['temp']}°", DATA, 38, INK[0], align="START",
                                          fmt="%s°")),
              lambda: _group(lambda: text(74, 172, 84, 42, "--", "--", DATA, 38, INK[0], align="START")),
              True)


def _group(fn):
    group_open(O.gid("g"))
    fn()
    group_close()


def builtin_uv():
    gauge(DOME_BL[0], DOME_BL[1] - 2, 31, "[WEATHER.UV_INDEX] / 11", SAMPLE["uv"] / 11,
          lambda x, y, h: text(x - 30, y, 60, h, ("expr", "[WEATHER.UV_INDEX]"), SAMPLE["uv"], DATA, 27, INK[0]),
          "UV", SOFT_D, TRACK_D, ACCENT, "uv")


def builtin_rain():
    gauge(DOME_TR[0], DOME_TR[1] - 2, 31, "[WEATHER.CHANCE_OF_PRECIPITATION] / 100", SAMPLE["rain"] / 100,
          lambda x, y, h: value_unit(x, y, h, ("expr", "[WEATHER.CHANCE_OF_PRECIPITATION]"), SAMPLE["rain"],
                                     "%", 27, INK[3], 15),
          "PLUIE", SOFT_L, TRACK_L, BAND[2], "drop")


def builtin_hr():
    icon_img(374, 190, 22, "heart", BAND[2])
    condition("hr_ok", "[HEART_RATE] > 0",
              lambda: _group(lambda: text(334, 196, 80, 48, ("expr", "[HEART_RATE]"), SAMPLE["hr"], DATA, 46,
                                          INK[3])),
              lambda: _group(lambda: text(334, 196, 80, 48, "--", "--", DATA, 46, INK[3])), True)
    text(334, 243, 80, 17, "BPM", "BPM", DATA_M, 15, SOFT_L[0], alpha=SOFT_L[1], spacing="0.15")


BATT_LOW = "[BATTERY_PERCENT] <= 20"      # batterie faible : pile et valeur en rouge
LOW_RED, LOW_RED_AOD = "#D7263D", "#FF5A5F"


def _battery(fill, ink):
    box_draw(356, 272, 38, 20)
    rrect(358, 274, 30, 16, 3, "#00000000", stroke=ink, th=2)
    rect(389, 279, 3, 6, ink)
    rect(360.5, 276.5, 25, 11, fill, width_expr="25 * [BATTERY_PERCENT] / 100",
         svg_w=25 * SAMPLE["batt"] / 100)
    draw_close()
    value_unit(374, 294, 36, ("expr", "[BATTERY_PERCENT]"), SAMPLE["batt"], "%", 38, ink, 20)


def builtin_battery():
    condition("batt_low", BATT_LOW,
              lambda: _group(lambda: _battery(LOW_RED, LOW_RED)),
              lambda: _group(lambda: _battery(BAND[2], INK[3])), SAMPLE["batt"] <= 20)


SEG_N, SEG_W, SEG_GAP, SEG_H, SEG_Y = 10, 12, 4, 15, 378
SEG_X0 = C - 91                         # pictogramme à gauche, pourcentage à droite : dans l'arc des secondes


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
    pct(x_end - 2, SEG_Y - 6, 27)


# Bloc des pas : « 6420 PAS » sur une ligne (nombre calé à droite, libellé collé derrière),
# puis pictogramme + barre + pourcentage sur la ligne du dessous.
STEPS_SPLIT = C - 8                     # fin du nombre, début de « PAS »
STEPS_ICON = (SEG_X0 - 17, SEG_Y + SEG_H / 2)


def builtin_steps():
    icon_img(*STEPS_ICON, 24, "steps", ACCENT)
    text(STEPS_SPLIT - 120, 331, 120, 40, ("expr", "[STEP_COUNT]"), SAMPLE["steps"], DATA, 36, INK[1], align="END")
    text(STEPS_SPLIT + 4, 347, 44, 21, "PAS", "PAS", DATA, 18, INK[1], align="START", spacing="0.1")
    steps_bar("[STEP_PERCENT] / 100", SAMPLE["pct"] / 100,
              lambda x, y, h: _pct_after(x, y, h, ("expr", "[STEP_PERCENT]"), SAMPLE["pct"]))


def _pct_after(x, y, h, content, sample):
    text(x, y, 30, h, content, sample, DATA, 22, INK[2], align="END")
    text(x + 31, y + 5, 18, h - 7, "%", "%", DATA, 15, INK[2], align="START")


def layer_slots():
    O.comment("Emplacement 1 — date (intégrée) ou source au choix")
    text_slot(1, "slot_date", 30, 100, 128, 70, INK[0], SOFT_D, ACCENT, builtin_date, big=38, launch="CALENDAR")
    O.comment("Emplacement 2 — météo (intégrée) ou source au choix")
    text_slot(2, "slot_left", 30, 172, 128, 44, INK[0], SOFT_D, ACCENT, builtin_weather, big=34, launch=APP_WEATHER)
    O.comment("Emplacement 3 — dôme bas gauche : indice UV (intégré) ou source au choix")
    dome_slot(3, "slot_dome_bl", DOME_BL, 31, INK[0], SOFT_D, TRACK_D, ACCENT, builtin_uv, launch=APP_WEATHER)
    O.comment("Emplacement 4 — dôme haut droite : pluie (intégrée) ou source au choix")
    dome_slot(4, "slot_dome_tr", DOME_TR, 31, INK[3], SOFT_L, TRACK_L, BAND[2], builtin_rain, launch=APP_WEATHER)
    O.comment("Emplacement 5 — cardio (intégré) ou source au choix")
    text_slot(5, "slot_right", 334, 176, 80, 86, INK[3], SOFT_L, BAND[2], builtin_hr, big=36, centered=True, launch="HEALTH_HEART_RATE")
    O.comment("Emplacement 6 — batterie (intégrée) ou source au choix")
    text_slot(6, "slot_right2", 334, 268, 80, 66, INK[3], SOFT_L, BAND[2], builtin_battery, big=30, centered=True, launch="BATTERY_STATUS")
    O.comment("Emplacement 7 — pas (intégrés) ou source au choix")

    def steps_render(t):
        comp_icon(*STEPS_ICON, 24, ACCENT)
        text(C - 100, 331, 200, 40, CTEXT, "", DATA, 36, INK[1])
        if t in FRAC:
            steps_bar(FRAC[t], 0.5,
                      lambda x, y, h: _pct_after(x, y, h, ("expr", f"round(100 * clamp({FRAC[t]}, 0, 1))"), ""))
        else:   # source sans progression (texte) : son titre à la place de la barre
            text(C - 90, SEG_Y - 4, 180, 24, CTITLE, "", DATA_M, 17, INK[1], alpha=190, spacing="0.1")
    slot(7, "slot_bottom", 100, 330, 256, 68,
         f"GOAL_PROGRESS RANGED_VALUE SHORT_TEXT LONG_TEXT MONOCHROMATIC_IMAGE {IMAGE_TYPES} EMPTY", builtin_steps, steps_render,
         launch=APP_HEALTH)


def layer_aod():
    O.comment("AOD : date, cardio, batterie, pas en texte simple sur noir")
    group_open("aod_data", show="ambient")
    text(30, 100, 52, 46, ("expr", "[DAY_Z]"), SAMPLE["day"], DATA, 44, ACCENT, align="END")
    text(87, 113, 66, 34, ("expr", "[MONTH_S]"), SAMPLE["mon"], DATA, 26, "#C9D1D9", align="START", upper=True)
    text(38, 149, 122, 21, ("expr", "[DAY_OF_WEEK_F]"), SAMPLE["dow"], DATA_M, 17, "#7D8791", align="START",
         upper=True, spacing="0.08")
    condition("hr_aod", "[HEART_RATE] > 0",
              lambda: _group(lambda: text(334, 198, 80, 46, ("expr", "[HEART_RATE]"), SAMPLE["hr"], DATA, 42,
                                          "#C9D1D9")),
              lambda: _group(lambda: text(334, 198, 80, 46, "--", "--", DATA, 42, "#C9D1D9")), True)
    text(334, 243, 80, 17, "BPM", "BPM", DATA_M, 14, "#7D8791", spacing="0.15")
    condition("batt_low_aod", BATT_LOW,
              lambda: _group(lambda: value_unit(374, 290, 36, ("expr", "[BATTERY_PERCENT]"), SAMPLE["batt"], "%", 34,
                                                LOW_RED_AOD, 18)),
              lambda: _group(lambda: value_unit(374, 290, 36, ("expr", "[BATTERY_PERCENT]"), SAMPLE["batt"], "%", 34,
                                                "#C9D1D9", 18)), SAMPLE["batt"] <= 20)
    text(C - 80, 340, 160, 38, ("expr", "[STEP_COUNT]"), SAMPLE["steps"], DATA, 32, "#C9D1D9")
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
    lines.append('    </ColorConfiguration>')
    lines.append('    <ListConfiguration id="secondes" displayName="cfg_secondes" defaultValue="0">')
    for i, (name, _) in enumerate(SECONDS_OPTIONS):
        lines.append(f'      <ListOption id="{i}" displayName="{name}" />')
    lines += ['    </ListConfiguration>', '  </UserConfigurations>']
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
