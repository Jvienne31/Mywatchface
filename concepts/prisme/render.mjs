// Maquette « Prisme » : cadran numérique à bandes diagonales. Heures et minutes sur deux
// lignes, chiffres géants penchés qui changent de couleur à chaque bande traversée.
// Dessin original (inspiration : principe des chiffres « découpés » par des aplats).
//
//   node concepts/prisme/render.mjs
//
// En WFF : bandes en Rectangle dans un Group tourné ; l'inversion des chiffres par bande se
// fait avec les modes de fusion de Group (WFF v3+, Wear OS 5.1 et plus : Watch8 = Wear OS 6)
// ou en dessinant les chiffres une fois par bande dans un Group masqué.
import { chromium } from 'playwright';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { writeFileSync, unlinkSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

const here = dirname(fileURLToPath(import.meta.url));
const W = 438, C = W / 2;
const D = {
  hh: '10', mm: '09', s: 36, dow: 'VEN', date: '02 OCT', temp: '18°', hr: 72, batt: 86,
  steps: '6 420', stepPct: 64, kcal: 412, kcalGoal: 600, rain: 20,
};

// Bandes : bords à x = 128, 206, 286 (mesuré à mi-hauteur), inclinées de ANGLE degrés.
const ANGLE = 18;
const EDGES = [-400, 128, 206, 286, 900];

// Palettes : 4 bandes (sombre -> claire) + accent. L'encre des chiffres et des textes est
// calculée par bande selon sa luminance, pour que l'inversion marche avec toutes.
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const lum = (h) => { const [r, g, b] = hex(h).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
const mix = (a, b, k) => '#' + hex(a).map((v, i) => Math.round(v + (hex(b)[i] - v) * k).toString(16).padStart(2, '0')).join('');
const pal = (label, bands, accent) => {
  const light = bands[3], dark = bands[0];
  // encre : celle des deux extrêmes qui contraste le plus avec la bande
  const contrast = (x, y) => { const [l1, l2] = [lum(x), lum(y)].sort((u, v) => v - u); return (l1 + 0.05) / (l2 + 0.05); };
  const ink = bands.map((bd) => (contrast(bd, light) >= contrast(bd, dark) ? light : dark));
  return { label, bands, ink, accent, light, dark, soft: mix(light, dark, 0.45),
           trackL: mix(bands[3], bands[2], 0.35), trackD: mix(bands[0], bands[1], 0.6) };
};
const PALETTES = {
  volcan:   pal('Volcan',    ['#1C1A19', '#5E281B', '#C4562C', '#ECE0CB'], '#FF8A3D'),
  lagune:   pal('Lagune',    ['#0A1729', '#0E4756', '#2A9BA6', '#DDEFF0'], '#7FE3EC'),
  ardoise:  pal('Ardoise',   ['#151719', '#353A40', '#78808A', '#E9EBED'], '#C8F03A'),
  moka:     pal('Moka',      ['#2B1D17', '#5A3B2E', '#A47864', '#EADBC8'], '#F0B86E'),
  sauge:    pal('Sauge',     ['#18221C', '#3F5A4A', '#8FA98F', '#E6ECDF'], '#F2C14E'),
  lavande:  pal('Lavande',   ['#1C1830', '#45386B', '#9C8FD0', '#ECE8F8'], '#FFB3C7'),
  cerise:   pal('Cerise',    ['#1A0E12', '#5B1424', '#B3263E', '#F5E1DF'], '#FFC9A3'),
  cobalt:   pal('Cobalt',    ['#0A1330', '#1E3A8A', '#4C7BF3', '#E4EAFB'], '#FFD23F'),
  olive:    pal('Olive',     ['#1C1E12', '#474B26', '#8F9A4E', '#EEEDDA'], '#FF8C42'),
  dune:     pal('Dune',      ['#2A2118', '#8C6A47', '#D2B48C', '#F7EFE2'], '#2FB3A8'),
  neon:     pal('Néon',      ['#0B0B12', '#22224A', '#FF2E88', '#F4F4F8'], '#00E5FF'),
  graphite: pal('Graphite',  ['#101010', '#2F2F2F', '#8A8A8A', '#F2F2F2'], '#FF3B30'),
  foret:    pal('Forêt',     ['#0E1A14', '#1F3D2E', '#3E7C5A', '#DDEBE2'], '#E6C35C'),
  peche:    pal('Pêche',     ['#2A1C1A', '#8A4F3D', '#F2A07B', '#FDEDE3'], '#2E6E9E'),
  beurre:   pal('Beurre',    ['#26231A', '#6B6342', '#E8D27A', '#FBF6E3'], '#D9544D'),
  bordeaux: pal('Bordeaux',  ['#1A0C10', '#4A1621', '#8E2C3B', '#EBDCCD'], '#D9AE62'),
  abysse:   pal('Abysse',    ['#05121C', '#0B3954', '#087E8B', '#C4DCEC'], '#FF6B6B'),
  aurore:   pal('Aurore',    ['#1A1530', '#5A2A6E', '#E0607E', '#FFE6D8'], '#FFC857'),
};


const polar = (r, a, cx = C, cy = C) => {
  const t = (a * Math.PI) / 180;
  return [cx + r * Math.sin(t), cy - r * Math.cos(t)];
};
const n = (v) => Math.round(v * 100) / 100;
const fontUrl = (f) => pathToFileURL(join(here, '..', 'strate', 'fonts', f)).href;

// Contenu des deux dômes (emplacements personnalisables : ce sont des complications)
let DOME_TR = { label: 'PLUIE', value: `${D.rain}<tspan font-size="11">%</tspan>`, frac: D.rain / 100, icon: 'drop' };
let DOME_BL = { label: 'KCAL', value: D.kcal, frac: D.kcal / D.kcalGoal, icon: 'flame' };
let LEFT2 = null;   // 2e ligne de gauche : null = météo, sinon { icon, value }

function face(c, aod = false, gauges = false, dome = false, allDomes = false, slots = false) {
  const p = [], defs = [];
  const rot = `rotate(${ANGLE} ${C} ${C})`;
  // Bandes (et leurs masques pour les chiffres)
  for (let i = 0; i < 4; i++) {
    const x0 = EDGES[i], x1 = EDGES[i + 1];
    defs.push(`<clipPath id="b${i}"><rect x="${x0}" y="-300" width="${x1 - x0}" height="1100" transform="${rot}"/></clipPath>`);
    if (!aod) p.push(`<rect x="${x0}" y="-300" width="${x1 - x0}" height="1100" fill="${c.bands[i]}" transform="${rot}"/>`);
  }
  if (aod) p.push(`<rect width="${W}" height="${W}" fill="#000"/>`);
  // léger ombrage sur chaque bande (volume) — en WFF : un PNG translucide
  if (!aod) {
    defs.push(`<linearGradient id="shade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity="0.22"/>
      <stop offset="0.25" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="0.05"/></linearGradient>`);
    for (let i = 1; i < 4; i++)
      p.push(`<rect x="${EDGES[i]}" y="-300" width="${EDGES[i + 1] - EDGES[i]}" height="1100" fill="url(#shade)" transform="${rot}"/>`);
  }

  // Chiffres : dessinés une fois par bande, chacun dans la couleur d'encre de sa bande
  const digits = (txt, cx, base, size) => {
    let s = '';
    for (let i = 0; i < 4; i++) {
      const fill = aod ? (i < 2 ? '#D5DBE1' : c.accent) : c.ink[i];
      s += `<g clip-path="url(#b${i})"><text transform="translate(${cx} ${base}) skewX(-${ANGLE - 6})"
        font-family="Shoulders" font-weight="${aod ? 300 : 800}" font-size="${size}" letter-spacing="-4" fill="${fill}" text-anchor="middle">${txt}</text></g>`;
    }
    return s;
  };
  p.push(digits(D.hh, C - 30, 192, 172));
  p.push(digits(D.mm, C + (allDomes ? 18 : 34), 334, 172));   // décalées si 4 dômes

  // Secondes : fin anneau au bord
  {
    const r = C - 5, a = D.s * 6;
    const [x0, y0] = polar(r, 0), [x1, y1] = polar(r, a);
    p.push(`<path d="M ${n(x0)} ${n(y0)} A ${r} ${r} 0 ${a > 180 ? 1 : 0} 1 ${n(x1)} ${n(y1)}" fill="none" stroke="${c.accent}" stroke-width="4" stroke-linecap="round" opacity="${aod ? 0 : 1}"/>`);
  }

  // Données — gauche (bande sombre) : jour, date, météo
  const L = aod ? '#C9D1D9' : c.light, Dk = aod ? '#C9D1D9' : c.dark, soft = aod ? '#6F7882' : c.soft;
  // Jauge en arc (270°, ouverte en bas) : valeur au centre, libellé dans l'ouverture
  // Pictogrammes (traits pleins, lisibles à 12-16 px)
  const ICON = {
    drop: (x, y, col, k = 1) => `<path d="M ${x} ${n(y - 8 * k)} C ${n(x + 6 * k)} ${n(y - 1 * k)} ${n(x + 6 * k)} ${n(y + 5 * k)} ${x} ${n(y + 6 * k)} C ${n(x - 6 * k)} ${n(y + 5 * k)} ${n(x - 6 * k)} ${n(y - 1 * k)} ${x} ${n(y - 8 * k)} Z" fill="${col}"/>`,
    flame: (x, y, col, k = 1) => `<path d="M ${x} ${n(y - 9 * k)} C ${n(x + 8 * k)} ${n(y - 2 * k)} ${n(x + 7 * k)} ${n(y + 7 * k)} ${x} ${n(y + 7 * k)} C ${n(x - 7 * k)} ${n(y + 7 * k)} ${n(x - 7 * k)} ${y} ${n(x - 2 * k)} ${n(y - 3 * k)} C ${n(x - 2 * k)} ${n(y + 1 * k)} ${n(x + 1 * k)} ${n(y + 2 * k)} ${n(x + 1 * k)} ${n(y - 1 * k)} C ${n(x + 1 * k)} ${n(y - 4 * k)} ${n(x - 1 * k)} ${n(y - 6 * k)} ${x} ${n(y - 9 * k)} Z" fill="${col}"/>`,
    uv: (x, y, col, k = 1) => `<circle cx="${x}" cy="${y}" r="${n(5 * k)}" fill="none" stroke="${col}" stroke-width="2"/>` +
      [0, 60, 120, 180, 240, 300].map((a) => { const [a1, b1] = polar(8 * k, a, x, y), [a2, b2] = polar(10.5 * k, a, x, y);
        return `<line x1="${n(a1)}" y1="${n(b1)}" x2="${n(a2)}" y2="${n(b2)}" stroke="${col}" stroke-width="1.8" stroke-linecap="round"/>`; }).join(''),
    stairs: (x, y, col, k = 1) => `<path d="M ${n(x - 8 * k)} ${n(y + 7 * k)} h ${n(5 * k)} v ${n(-5 * k)} h ${n(5 * k)} v ${n(-5 * k)} h ${n(5 * k)} v ${n(-5 * k)}" fill="none" stroke="${col}" stroke-width="2.2" stroke-linejoin="round"/>`,
    sunrise: (x, y, col, k = 1) => `<path d="M ${n(x - 8 * k)} ${n(y + 4 * k)} A ${n(8 * k)} ${n(8 * k)} 0 0 1 ${n(x + 8 * k)} ${n(y + 4 * k)}" fill="none" stroke="${col}" stroke-width="2"/>
      <line x1="${n(x - 11 * k)}" y1="${n(y + 7 * k)}" x2="${n(x + 11 * k)}" y2="${n(y + 7 * k)}" stroke="${col}" stroke-width="2" stroke-linecap="round"/>`,
    // deux empreintes de pas, décalées
    steps: (x, y, col) => [[-5, 3, -12], [5, -4, 12]].map(([dx, dy, rot]) =>
      `<g transform="rotate(${rot} ${x + dx} ${y + dy})"><ellipse cx="${x + dx}" cy="${y + dy - 2}" rx="4" ry="6.5" fill="${col}"/>
       <ellipse cx="${x + dx}" cy="${y + dy + 7}" rx="3" ry="2.6" fill="${col}"/></g>`).join(''),
  };
  function gauge(cx, cy, r, frac, value, label, ink, labelInk, track, color, icon) {
    const a0 = -135, a1 = 135, af = a0 + (a1 - a0) * Math.min(1, frac);
    const arc = (b0, b1) => { const [x0, y0] = polar(r, b0, cx, cy), [x1, y1] = polar(r, b1, cx, cy);
      return `M ${n(x0)} ${n(y0)} A ${r} ${r} 0 ${b1 - b0 > 180 ? 1 : 0} 1 ${n(x1)} ${n(y1)}`; };
    return `<path d="${arc(a0, a1)}" fill="none" stroke="${track}" stroke-width="6" stroke-linecap="round"/>
      <path d="${arc(a0, af)}" fill="none" stroke="${color}" stroke-width="6" stroke-linecap="round"/>
      ${icon ? ICON[icon](cx, cy - 13, color, 0.85) : ''}
      ${t(cx, cy + (icon ? 12 : 7), 20, ink, value)}${t(cx, cy + r - 1, 11, labelInk, label, 'letter-spacing="1.6"')}`;
  }
  // Loupe : le contenu (bandes + jauge) est redessiné agrandi dans un disque, puis
  // ombre portée, bord assombri (réfraction), reflet et croissant de lumière.
  // En WFF : Group mis à l'échelle (scaleX/scaleY) sous un masque rond + PNG de verre.
  const bandsSvg = () => {
    let b = '';
    for (let i = 0; i < 4; i++)
      b += `<rect x="${EDGES[i]}" y="-300" width="${EDGES[i + 1] - EDGES[i]}" height="1100" fill="${aod ? '#000' : c.bands[i]}" transform="${rot}"/>`;
    return b;
  };
  function lens(cx, cy, R, inner, k = 1.2) {
    if (!dome || aod) return inner;
    const id = `lens${Math.round(cx)}`;
    defs.push(`<clipPath id="${id}"><circle cx="${cx}" cy="${cy}" r="${R}"/></clipPath>`);
    defs.push(`<radialGradient id="${id}e" cx="${cx}" cy="${cy}" r="${R}" gradientUnits="userSpaceOnUse">
      <stop offset="0.72" stop-color="#000" stop-opacity="0"/><stop offset="0.93" stop-color="#000" stop-opacity="0.28"/>
      <stop offset="1" stop-color="#000" stop-opacity="0.55"/></radialGradient>`);
    defs.push(`<radialGradient id="${id}h" cx="${cx - R * 0.38}" cy="${cy - R * 0.45}" r="${R * 0.62}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#fff" stop-opacity="0.55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>`);
    defs.push(`<filter id="${id}s" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>`);
    const mag = `translate(${cx} ${cy}) scale(${k}) translate(${-cx} ${-cy})`;
    return `<circle cx="${cx + 3}" cy="${cy + 5}" r="${R}" fill="#000" opacity="0.38" filter="url(#${id}s)"/>
      <g clip-path="url(#${id})"><g transform="${mag}">${bandsSvg()}${inner}</g>
        <circle cx="${cx}" cy="${cy}" r="${R}" fill="url(#${id}e)"/>
        <ellipse cx="${n(cx - R * 0.3)}" cy="${n(cy - R * 0.42)}" rx="${n(R * 0.5)}" ry="${n(R * 0.28)}" fill="url(#${id}h)" transform="rotate(-30 ${n(cx - R * 0.3)} ${n(cy - R * 0.42)})"/>
        <path d="M ${n(cx + R * 0.15)} ${n(cy + R * 0.86)} A ${R * 0.9} ${R * 0.9} 0 0 0 ${n(cx + R * 0.86)} ${n(cy + R * 0.2)}" fill="none" stroke="#fff" stroke-opacity="0.35" stroke-width="2.2" stroke-linecap="round"/></g>
      <circle cx="${cx}" cy="${cy}" r="${R - 0.5}" fill="none" stroke="#fff" stroke-opacity="0.45" stroke-width="1"/>
      <circle cx="${cx}" cy="${cy}" r="${R + 0.8}" fill="none" stroke="#000" stroke-opacity="0.35" stroke-width="1.2"/>`;
  }
  const t = (x, y, size, fill, txt, extra = '') =>
    `<text x="${n(x)}" y="${n(y)}" font-family="Barlow" font-weight="600" font-size="${size}" fill="${fill}" text-anchor="middle" ${extra}>${txt}</text>`;
  p.push(t(66, gauges ? 118 : 132, 28, c.accent, D.dow, 'letter-spacing="1.5"'));
  p.push(t(66, gauges ? 140 : 154, 17, L, D.date, 'letter-spacing="1"'));
  if (gauges) {
    // météo compacte : soleil + température sur une ligne
    let sun = `<circle cx="48" cy="181" r="6" fill="${aod ? soft : c.accent}"/>`;
    for (let k = 0; k < 8; k++) { const [a1, b1] = polar(8.5, k * 45, 48, 181), [a2, b2] = polar(11.5, k * 45, 48, 181);
      sun += `<line x1="${n(a1)}" y1="${n(b1)}" x2="${n(a2)}" y2="${n(b2)}" stroke="${aod ? soft : c.accent}" stroke-width="1.8" stroke-linecap="round"/>`; }
    if (LEFT2) p.push(ICON[LEFT2.icon](48, 182, aod ? soft : c.accent, 1.1) + t(86, 191, 26, L, LEFT2.value));
    else p.push(sun + t(82, 191, 28, L, D.temp));
    // jauge calories (bas gauche, bande sombre)
    p.push(lens(68, 262, 46, gauge(68, 262, 30, DOME_BL.frac, DOME_BL.value, DOME_BL.label, L, soft, aod ? '#1a1d20' : c.trackD, c.accent, DOME_BL.icon)));
  } else if (!aod) {
    // soleil
    let sun = `<circle cx="66" cy="232" r="7" fill="${c.accent}"/>`;
    for (let k = 0; k < 8; k++) { const [a1, b1] = polar(10, k * 45, 66, 232), [a2, b2] = polar(13.5, k * 45, 66, 232);
      sun += `<line x1="${n(a1)}" y1="${n(b1)}" x2="${n(a2)}" y2="${n(b2)}" stroke="${c.accent}" stroke-width="2" stroke-linecap="round"/>`; }
    p.push(sun);
    p.push(t(66, 274, 30, L, D.temp));
  }
  // Données — droite (bande claire) : pluie (jauge), cardio, batterie
  if (gauges) p.push(lens(354, 124, 46, gauge(354, 122, 28, DOME_TR.frac, DOME_TR.value, DOME_TR.label,
    Dk, soft, aod ? '#1a1d20' : c.trackL, aod ? soft : c.bands[2], DOME_TR.icon)));
  if (allDomes) {
    // cardio et batterie en jauges sous dôme, comme pluie et calories
    const hrCol = aod ? soft : c.bands[2];
    p.push(lens(374, 222, 40, gauge(374, 220, 24, (D.hr - 40) / 160,
      D.hr, 'BPM', Dk, soft, aod ? '#1a1d20' : c.trackL, hrCol)));
    p.push(lens(366, 312, 40, gauge(366, 310, 24, D.batt / 100,
      `${D.batt}<tspan font-size="11">%</tspan>`, 'BATT', Dk, soft, aod ? '#1a1d20' : c.trackL, hrCol)));
  } else {
    p.push(`<path d="M 370 196 C 360 189 363 180 370 185 C 377 180 380 189 370 196 Z" fill="${aod ? soft : c.bands[2]}"/>`);
    p.push(t(370, 228, 32, Dk, D.hr));
    p.push(t(370, 244, 12, soft, 'BPM', 'letter-spacing="2"'));
    p.push(`<rect x="357" y="270" width="22" height="12" rx="2.5" fill="none" stroke="${Dk}" stroke-width="1.8"/>
      <rect x="379.5" y="273.5" width="2.5" height="5" rx="1" fill="${Dk}"/><rect x="359.5" y="272.5" width="${n(17 * D.batt / 100)}" height="7" rx="1" fill="${aod ? soft : c.bands[2]}"/>`);
    p.push(t(370, 310, 26, Dk, `${D.batt}<tspan font-size="15">%</tspan>`));
  }

  // Bas : pas — empreintes, nombre, barre de 10 segments penchés comme les bandes, %
  if (!aod) {
    const seg = 10, sw = 14, sg = 3.5, sh = 12, y = 377;
    const x0 = C - (seg * (sw + sg) - sg) / 2 - 8;
    const lit = D.stepPct / 10;
    let bar = '';
    for (let i = 0; i < seg; i++) {
      const fill = i < Math.floor(lit) ? c.accent : '#000';
      const op = i < Math.floor(lit) ? 1 : (i < lit ? 0.55 : 0.28);
      bar += `<rect x="${n(x0 + i * (sw + sg))}" y="0" width="${sw}" height="${sh}" rx="1.5" fill="${i < lit ? c.accent : fill}" fill-opacity="${op}"
        ${i < lit ? `stroke="${c.dark}" stroke-opacity="0.55" stroke-width="1"` : ''}/>`;
    }
    p.push(`<g transform="translate(0 ${y}) skewX(-${ANGLE})" >${bar}</g>`);
    const barEnd = x0 + seg * (sw + sg);
    p.push(t(barEnd + 2, y + 11, 17, c.dark, `${D.stepPct}<tspan font-size="11">%</tspan>`, 'text-anchor="start"').replace('text-anchor="middle" ', ''));
    // empreintes + nombre + libellé, au-dessus de la barre
    p.push(ICON.steps(C - 66, 352, c.accent));
    p.push(`<text x="${C - 50}" y="364" font-family="Barlow" font-weight="600" font-size="26" fill="${c.light}" style="paint-order:stroke" stroke="${c.bands[1]}" stroke-width="0.6">${D.steps}</text>`);
    p.push(`<text x="${C + 18}" y="364" font-family="Barlow" font-weight="600" font-size="13" letter-spacing="2" fill="${c.dark}">PAS</text>`);
    if (!gauges) p.push(t(C + 4, 410, 15, c.ink[2], `${D.kcal} KCAL`, 'letter-spacing="1.5"'));
  } else {
    p.push(ICON.steps(C - 50, 362, '#6F7882') + t(C + 8, 372, 18, '#C9D1D9', `${D.steps} PAS`));
  }

  if (slots) {
    // schéma des emplacements personnalisables
    const tag = (x, y, k) => `<circle cx="${x}" cy="${y}" r="11" fill="#FF3B6B"/><text x="${x}" y="${y + 5}" font-family="Barlow" font-weight="600" font-size="15" fill="#fff" text-anchor="middle">${k}</text>`;
    const box = (x, y, w, h) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="8" fill="#FF3B6B" fill-opacity="0.12" stroke="#FF3B6B" stroke-width="2" stroke-dasharray="6 4"/>`;
    const ring = (x, y, r) => `<circle cx="${x}" cy="${y}" r="${r}" fill="#FF3B6B" fill-opacity="0.12" stroke="#FF3B6B" stroke-width="2" stroke-dasharray="6 4"/>`;
    p.push(box(26, 92, 84, 60) + tag(112, 94, 1));
    p.push(box(30, 166, 90, 34) + tag(30, 166, 2));
    p.push(ring(68, 262, 48) + tag(28, 228, 3));
    p.push(ring(354, 124, 48) + tag(306, 86, 4));
    p.push(box(336, 176, 68, 76) + tag(404, 176, 5));
    p.push(box(336, 262, 68, 64) + tag(404, 262, 6));
    p.push(box(116, 334, 220, 62) + tag(116, 334, 7));
  }

  const style = `<style>
    @font-face { font-family: Shoulders; font-weight: 800; src: url('${fontUrl('big-shoulders-display-latin-800-normal.woff2')}'); }
    @font-face { font-family: Shoulders; font-weight: 300; src: url('${fontUrl('big-shoulders-display-latin-300-normal.woff2')}'); }
    @font-face { font-family: Barlow; font-weight: 600; src: url('${fontUrl('barlow-condensed-latin-600-normal.woff2')}'); }</style>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${W}" viewBox="0 0 ${W} ${W}">${style}
    <defs>${defs.join('')}<clipPath id="round"><circle cx="${C}" cy="${C}" r="${C}"/></clipPath></defs>
    <g clip-path="url(#round)">${p.join('\n')}</g></svg>`;
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: W, height: W } });
const render = async (svg, out) => {
  const tmp = join(here, '_tmp.svg');
  writeFileSync(tmp, svg);
  await page.goto(pathToFileURL(tmp).href);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: out, omitBackground: true });
  unlinkSync(tmp);
  console.log(out);
};
const outs = [];
for (const [name, c] of Object.entries(PALETTES).slice(0, 3)) {
  const out = join(here, `prisme-${name}.png`);
  await render(face(c), out);
  outs.push(out);
}
await render(face(PALETTES.volcan, true), join(here, 'prisme-aod.png'));
// Essai « plus de données » : jauges pluie (haut droite) et calories (bas gauche), palette lagune
await render(face(PALETTES.lagune, false, true), join(here, 'prisme-lagune-jauges.png'));
await render(face(PALETTES.lagune, true, true), join(here, 'prisme-lagune-jauges-aod.png'));
// Essai « dôme » : loupes de verre bombé sur les deux jauges
await render(face(PALETTES.lagune, false, true, true), join(here, 'prisme-lagune-dome.png'));
// Toutes les palettes, version retenue (2 dômes) -> planche-palettes.png
const palOuts = [];
for (const [name, c] of Object.entries(PALETTES)) {
  const out = join(here, 'palettes', `${name}.png`);
  await render(face(c, false, true, true), out);
  palOuts.push([out, c.label]);
}
// Schéma des emplacements + exemple avec d'autres données
await render(face(PALETTES.lagune, false, true, true, false, true), join(here, 'emplacements-cadran.png'));
const saved = [DOME_TR, DOME_BL, LEFT2];
DOME_TR = { label: 'UV', value: 3, frac: 3 / 11, icon: 'uv' };
DOME_BL = { label: 'ÉTAGES', value: 8, frac: 8 / 10, icon: 'stairs' };
LEFT2 = { icon: 'sunrise', value: '07:42' };
await render(face(PALETTES.moka, false, true, true), join(here, 'exemple-donnees-moka.png'));
[DOME_TR, DOME_BL, LEFT2] = saved;
// Essai « 4 dômes » : cardio et batterie aussi en jauges sous dôme
await render(face(PALETTES.lagune, false, true, true, true), join(here, 'prisme-lagune-4domes.png'));
await browser.close();

execFileSync('montage', [...palOuts.flatMap(([f, l]) => ['-label', l, f]), '-tile', '6x3', '-geometry', '200x200+14+10',
  '-background', '#1E1F22', '-fill', '#E6E8EB', '-pointsize', '18', join(here, 'planche-palettes.png')]);
execFileSync('convert', [...outs, join(here, 'prisme-aod.png'), '-background', '#1E1F22',
  '-splice', '24x0', '+append', '-chop', '24x0', join(here, 'planche.png')]);
const skin = join(here, '..', '..', 'race', 'emulator', 'skin-galaxy-watch8-classic', 'background.png');
if (existsSync(skin)) {
  execFileSync('convert', [skin, outs[0], '-geometry', '+101+191', '-composite', join(here, 'prisme-montre.png')]);
  console.log(join(here, 'prisme-montre.png'));
}
