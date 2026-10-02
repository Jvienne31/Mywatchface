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

const PALETTES = {
  volcan:  { bands: ['#1C1A19', '#5E281B', '#C4562C', '#ECE0CB'], ink: ['#ECE0CB', '#ECE0CB', '#1C1A19', '#1C1A19'], accent: '#FF8A3D', light: '#ECE0CB', dark: '#1C1A19', soft: '#9B8E80' },
  lagune:  { bands: ['#0A1729', '#0E4756', '#2A9BA6', '#DDEFF0'], ink: ['#DDEFF0', '#DDEFF0', '#0A1729', '#0A1729'], accent: '#7FE3EC', light: '#DDEFF0', dark: '#0A1729', soft: '#7F98A8' },
  ardoise: { bands: ['#151719', '#353A40', '#78808A', '#E9EBED'], ink: ['#E9EBED', '#E9EBED', '#151719', '#151719'], accent: '#C8F03A', light: '#E9EBED', dark: '#151719', soft: '#8A929B' },
};

const polar = (r, a, cx = C, cy = C) => {
  const t = (a * Math.PI) / 180;
  return [cx + r * Math.sin(t), cy - r * Math.cos(t)];
};
const n = (v) => Math.round(v * 100) / 100;
const fontUrl = (f) => pathToFileURL(join(here, '..', 'strate', 'fonts', f)).href;

function face(c, aod = false, gauges = false, dome = false) {
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
  p.push(digits(D.mm, C + 34, 334, 172));

  // Secondes : fin anneau au bord
  {
    const r = C - 5, a = D.s * 6;
    const [x0, y0] = polar(r, 0), [x1, y1] = polar(r, a);
    p.push(`<path d="M ${n(x0)} ${n(y0)} A ${r} ${r} 0 ${a > 180 ? 1 : 0} 1 ${n(x1)} ${n(y1)}" fill="none" stroke="${c.accent}" stroke-width="4" stroke-linecap="round" opacity="${aod ? 0 : 1}"/>`);
  }

  // Données — gauche (bande sombre) : jour, date, météo
  const L = aod ? '#C9D1D9' : c.light, Dk = aod ? '#C9D1D9' : c.dark, soft = aod ? '#6F7882' : c.soft;
  // Jauge en arc (270°, ouverte en bas) : valeur au centre, libellé dans l'ouverture
  function gauge(cx, cy, r, frac, value, label, ink, labelInk, track, color) {
    const a0 = -135, a1 = 135, af = a0 + (a1 - a0) * Math.min(1, frac);
    const arc = (b0, b1) => { const [x0, y0] = polar(r, b0, cx, cy), [x1, y1] = polar(r, b1, cx, cy);
      return `M ${n(x0)} ${n(y0)} A ${r} ${r} 0 ${b1 - b0 > 180 ? 1 : 0} 1 ${n(x1)} ${n(y1)}`; };
    return `<path d="${arc(a0, a1)}" fill="none" stroke="${track}" stroke-width="6" stroke-linecap="round"/>
      <path d="${arc(a0, af)}" fill="none" stroke="${color}" stroke-width="6" stroke-linecap="round"/>
      ${t(cx, cy + 7, 20, ink, value)}${t(cx, cy + r - 1, 11, labelInk, label, 'letter-spacing="1.6"')}`;
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
    p.push(sun + t(82, 191, 28, L, D.temp));
    // jauge calories (bas gauche, bande sombre)
    p.push(lens(68, 262, 46, gauge(68, 262, 30, D.kcal / D.kcalGoal, D.kcal, 'KCAL', L, soft, aod ? '#1a1d20' : '#1c2c3c', c.accent)));
  } else if (!aod) {
    // soleil
    let sun = `<circle cx="66" cy="232" r="7" fill="${c.accent}"/>`;
    for (let k = 0; k < 8; k++) { const [a1, b1] = polar(10, k * 45, 66, 232), [a2, b2] = polar(13.5, k * 45, 66, 232);
      sun += `<line x1="${n(a1)}" y1="${n(b1)}" x2="${n(a2)}" y2="${n(b2)}" stroke="${c.accent}" stroke-width="2" stroke-linecap="round"/>`; }
    p.push(sun);
    p.push(t(66, 274, 30, L, D.temp));
  }
  // Données — droite (bande claire) : pluie (jauge), cardio, batterie
  if (gauges) p.push(lens(354, 124, 46, gauge(354, 122, 28, D.rain / 100, `${D.rain}<tspan font-size="11">%</tspan>`, 'PLUIE',
    Dk, soft, aod ? '#1a1d20' : '#c3d6d8', aod ? soft : c.bands[2])));
  p.push(`<path d="M 370 196 C 360 189 363 180 370 185 C 377 180 380 189 370 196 Z" fill="${aod ? soft : c.bands[2]}"/>`);
  p.push(t(370, 228, 32, Dk, D.hr));
  p.push(t(370, 244, 12, soft, 'BPM', 'letter-spacing="2"'));
  p.push(`<rect x="357" y="270" width="22" height="12" rx="2.5" fill="none" stroke="${Dk}" stroke-width="1.8"/>
    <rect x="379.5" y="273.5" width="2.5" height="5" rx="1" fill="${Dk}"/><rect x="359.5" y="272.5" width="${n(17 * D.batt / 100)}" height="7" rx="1" fill="${aod ? soft : c.bands[2]}"/>`);
  p.push(t(370, 310, 26, Dk, `${D.batt}<tspan font-size="15">%</tspan>`));

  // Bas : pas (barre penchée comme les bandes) + calories
  if (!aod) {
    p.push(`<g transform="translate(${C} 372) skewX(-${ANGLE - 6})">
      <rect x="-70" y="0" width="140" height="7" rx="3.5" fill="#000" fill-opacity="0.35"/>
      <rect x="-70" y="0" width="${n(140 * D.stepPct / 100)}" height="7" rx="3.5" fill="${c.accent}"/></g>`);
    p.push(t(C - 30, 364, 22, c.ink[1], `${D.steps}`, '') + t(C + 30, 364, 13, c.ink[2], 'PAS', 'letter-spacing="2"'));
    if (!gauges) p.push(t(C + 4, 402, 15, c.ink[2], `${D.kcal} KCAL`, 'letter-spacing="1.5"'));
  } else {
    p.push(t(C, 372, 18, '#C9D1D9', `${D.steps} PAS`));
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
for (const [name, c] of Object.entries(PALETTES)) {
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
await browser.close();

execFileSync('convert', [...outs, join(here, 'prisme-aod.png'), '-background', '#1E1F22',
  '-splice', '24x0', '+append', '-chop', '24x0', join(here, 'planche.png')]);
const skin = join(here, '..', '..', 'race', 'emulator', 'skin-galaxy-watch8-classic', 'background.png');
if (existsSync(skin)) {
  execFileSync('convert', [skin, outs[0], '-geometry', '+101+191', '-composite', join(here, 'prisme-montre.png')]);
  console.log(join(here, 'prisme-montre.png'));
}
