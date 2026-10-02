// Maquette « Méridien » v2 : finition haute horlogerie, informations lisibles sur 1,34".
// Dessin original.
//
//   node concepts/meridien/render.mjs
//
// Règles de lisibilité (écran 438 px ≈ 34 mm, ~13 px par mm) :
//   - pas de graduations décoratives : 12 index seulement, jauges en arc épais ;
//   - une grosse valeur par zone (28-34 px), libellés courts (≥ 13 px) ;
//   - police condensée Barlow Condensed SemiBold : gros chiffres dans peu de largeur.
//
//   12 h  météo : icône, température, max / min     [WEATHER.*] (WFF v2)
//   9 h   fréquence cardiaque, arc 40-200            [HEART_RATE]
//   3 h   batterie façon réserve de marche           [BATTERY_PERCENT]
//   6 h   phase de lune + jour et date               [MOON_PHASE_POSITION] [DAY_OF_WEEK] [DAY]
//   pourtour  anneau de progression des pas          [STEP_PERCENT]
//   centre    prochain événement (complication)      LONG_TEXT
//   bas       nombre de pas                          [STEP_COUNT]
import { chromium } from 'playwright';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { writeFileSync, unlinkSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

const here = dirname(fileURLToPath(import.meta.url));
const W = 438, C = W / 2;
const D = {
  h: 10, m: 9, s: 36, hr: 72, batt: 68, steps: 6420, stepPct: 64,
  temp: 18, tmin: 11, tmax: 22, moon: 0.62, dow: 'VEN', day: 2, event: '14:30 RÉUNION',
};

const COLORWAYS = {
  'anthracite-orange': {
    dial: ['#3A3E44', '#202327', '#0E1012'], ray: '#FFFFFF', well: '#111315',
    metal: ['#F2F4F6', '#A1A8B0', '#555C64'], lume: '#EAF2E6', text: '#E6EAEE', soft: '#9AA3AD',
    accent: '#FF7A1A', accent2: '#FFB36B', track: '#3A2618',
  },
  'bleu-glacier': {
    dial: ['#1C3F73', '#0E2346', '#061226'], ray: '#BFD8FF', well: '#071530',
    metal: ['#F4F6F8', '#9EA6B0', '#5A626C'], lume: '#E9F1E4', text: '#E6EEF6', soft: '#92A6C0',
    accent: '#36D3F2', accent2: '#9BEAFB', track: '#0F3A4C',
  },
  'panda': {
    dial: ['#F5F4F0', '#E2E0DA', '#BEBBB3'], ray: '#000000', well: '#15171A',
    metal: ['#4B525B', '#1E2226', '#0A0C0E'], lume: '#F7F3E8', text: '#1E2226', soft: '#5E656D',
    accent: '#D7262E', accent2: '#FF6B6B', track: '#3B1214', wellText: '#EEF1F4', wellSoft: '#9AA3AD',
  },
};

const polar = (r, a, cx = C, cy = C) => {
  const t = (a * Math.PI) / 180;
  return [cx + r * Math.sin(t), cy - r * Math.cos(t)];
};
const n = (v) => Math.round(v * 100) / 100;
const font = (f) => pathToFileURL(join(here, '..', 'nocturne', 'fonts', f)).href;
const arcPath = (cx, cy, r, a0, a1) => {
  const [x0, y0] = polar(r, a0, cx, cy), [x1, y1] = polar(r, a1, cx, cy);
  return `M ${n(x0)} ${n(y0)} A ${r} ${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${n(x1)} ${n(y1)}`;
};
const T = (x, y, size, fill, txt, extra = '') =>
  `<text x="${n(x)}" y="${n(y)}" font-family="Barlow" font-size="${size}" fill="${fill}" text-anchor="middle" ${extra}>${txt}</text>`;

function face(c, aod = false) {
  const p = [], defs = [];
  const wText = aod ? '#D5DBE1' : (c.wellText || c.text);
  const wSoft = aod ? '#7C858F' : (c.wellSoft || c.soft);
  defs.push(`<radialGradient id="dial" cx="${C}" cy="${C - 50}" r="${C + 70}" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="${c.dial[0]}"/><stop offset="0.6" stop-color="${c.dial[1]}"/><stop offset="1" stop-color="${c.dial[2]}"/></radialGradient>`);
  defs.push(`<linearGradient id="metalH" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="${c.metal[1]}"/>
    <stop offset="0.45" stop-color="${c.metal[0]}"/><stop offset="0.55" stop-color="${c.metal[2]}"/><stop offset="1" stop-color="${c.metal[1]}"/></linearGradient>`);
  defs.push(`<filter id="drop" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur in="SourceAlpha" stdDeviation="1.5"/>
    <feOffset dx="1.4" dy="2.2"/><feComponentTransfer><feFuncA type="linear" slope="0.55"/></feComponentTransfer>
    <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>`);
  defs.push(`<filter id="hand" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur in="SourceAlpha" stdDeviation="2.6"/>
    <feOffset dx="3" dy="5"/><feComponentTransfer><feFuncA type="linear" slope="0.5"/></feComponentTransfer>
    <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>`);
  defs.push(`<radialGradient id="well" cx="0.5" cy="0.35" r="0.65"><stop offset="0" stop-color="${c.well}" stop-opacity="0.8"/>
    <stop offset="1" stop-color="#000" stop-opacity="0.95"/></radialGradient>`);

  // --- Cadran soleillé -----------------------------------------------------------
  if (aod) p.push(`<rect width="${W}" height="${W}" fill="#000"/>`);
  else {
    p.push(`<rect width="${W}" height="${W}" fill="url(#dial)"/>`);
    const rays = [];
    for (let i = 0; i < 720; i++) {
      const a = i / 2;
      const sheen = Math.pow(Math.max(0, Math.cos(((a - 315) * Math.PI) / 180)), 3) * 0.12
                  + Math.pow(Math.max(0, Math.cos(((a - 135) * Math.PI) / 180)), 3) * 0.07;
      const [x, y] = polar(C, a);
      rays.push(`<line x1="${C}" y1="${C}" x2="${n(x)}" y2="${n(y)}" stroke="${c.ray}" stroke-opacity="${(0.012 + sheen * (i % 2 ? 1 : 0.5)).toFixed(3)}" stroke-width="0.9"/>`);
    }
    p.push(`<g>${rays.join('')}</g>`);
    p.push(`<circle cx="${C}" cy="${C}" r="${C - 6}" fill="none" stroke="#000" stroke-opacity="0.3" stroke-width="12"/>`);
  }

  // --- Anneau des pas (épais, lisible) ----------------------------------------------
  const RA = C - 10;
  p.push(`<circle cx="${C}" cy="${C}" r="${RA}" fill="none" stroke="${aod ? '#1a1d20' : c.track}" stroke-width="8"/>`);
  p.push(`<path d="${arcPath(C, C, RA, 0, 360 * D.stepPct / 100)}" fill="none" stroke="${c.accent}" stroke-width="8" stroke-linecap="round"/>`);

  // --- Index (12, 3, 6, 9 remplacés par la météo et les compteurs) ------------------------------------
  const marker = (a, dbl) => {
    const len = 22, w = 8, rOut = C - 22;
    const one = (dx) => `<rect x="${n(C + dx - w / 2)}" y="${n(C - rOut)}" width="${w}" height="${len}" rx="1.4"
      fill="${aod ? '#000' : 'url(#metalH)'}" stroke="${aod ? '#9aa3ad' : c.metal[2]}" stroke-width="${aod ? 1.1 : 0.6}"/>` +
      (aod ? '' : `<rect x="${n(C + dx - 1.5)}" y="${n(C - rOut + 5)}" width="3" height="${len - 10}" rx="1.5" fill="${c.lume}" opacity="0.9"/>`);
    return `<g transform="rotate(${a} ${C} ${C})" ${aod ? '' : 'filter="url(#drop)"'}>${dbl ? one(-6) + one(6) : one(0)}</g>`;
  };
  for (let h = 0; h < 12; h++) if (h % 3 !== 0) p.push(marker(h * 30, false));  // 12 h : la météo

  // --- Compteurs : jauge en arc épais + grosse valeur -------------------------------------
  const SR = 58;
  const well = (cx, cy) => aod
    ? `<circle cx="${cx}" cy="${cy}" r="${SR}" fill="#000" stroke="#3a3f45" stroke-width="1.2"/>`
    : `<circle cx="${cx}" cy="${cy}" r="${SR + 3}" fill="url(#metalH)" filter="url(#drop)"/><circle cx="${cx}" cy="${cy}" r="${SR}" fill="url(#well)"/>`;
  const gauge = (cx, cy, a0, sweep, frac, warn) => {
    const r = SR - 9;
    let s = `<path d="${arcPath(cx, cy, r, a0, a0 + sweep)}" fill="none" stroke="${aod ? '#1a1d20' : c.track}" stroke-width="7" stroke-linecap="round"/>`;
    if (warn && !aod) s += `<path d="${arcPath(cx, cy, r, a0, a0 + sweep * warn)}" fill="none" stroke="#E5484D" stroke-opacity="0.55" stroke-width="7" stroke-linecap="round"/>`;
    s += `<path d="${arcPath(cx, cy, r, a0, a0 + sweep * frac)}" fill="none" stroke="${c.accent}" stroke-width="7" stroke-linecap="round"/>`;
    const [x, y] = polar(r, a0 + sweep * frac, cx, cy);
    if (!aod) s += `<circle cx="${n(x)}" cy="${n(y)}" r="5.5" fill="${c.accent2}" stroke="${c.well}" stroke-width="2"/>`;
    return s;
  };

  // 9 h — cardio
  { const cx = C - 108, cy = C;
    p.push(well(cx, cy));
    p.push(gauge(cx, cy, -135, 270, (D.hr - 40) / 160));
    p.push(T(cx, cy + 12, 34, wText, D.hr, 'font-weight="600"'));
    p.push(T(cx, cy + 32, 13, c.accent, 'BPM', 'letter-spacing="1.5"')); }

  // 3 h — batterie (réserve de marche)
  { const cx = C + 108, cy = C;
    p.push(well(cx, cy));
    p.push(gauge(cx, cy, -135, 270, D.batt / 100, 0.2));
    p.push(T(cx - 4, cy + 12, 34, wText, D.batt, 'font-weight="600"') + T(cx + 21, cy + 12, 16, wSoft, '%'));
    p.push(T(cx, cy + 32, 13, c.accent, 'BATTERIE', 'letter-spacing="1.5"')); }

  // 6 h — lune + jour / date
  { const cx = C, cy = C + 104;
    p.push(well(cx, cy));
    if (!aod) {
      defs.push(`<clipPath id="moonWin"><path d="M ${cx - 34} ${cy - 6} A 34 34 0 0 1 ${cx + 34} ${cy - 6} Z"/></clipPath>`);
      defs.push(`<radialGradient id="sky" cx="0.5" cy="1" r="1"><stop offset="0" stop-color="#1b3b78"/><stop offset="1" stop-color="#07122b"/></radialGradient>`);
      defs.push(`<radialGradient id="moonG" cx="0.4" cy="0.35" r="0.7"><stop offset="0" stop-color="#FFF6D6"/><stop offset="1" stop-color="#D9B568"/></radialGradient>`);
      const off = (D.moon - 0.5) * 2 * 30;
      let stars = '';
      for (const [sx, sy, r] of [[-25, -12, 1], [-14, -27, 0.8], [17, -22, 0.9], [27, -10, 0.7], [5, -31, 0.7]])
        stars += `<circle cx="${cx + sx}" cy="${cy + sy}" r="${r}" fill="#fff" opacity="0.85"/>`;
      p.push(`<g clip-path="url(#moonWin)"><rect x="${cx - 36}" y="${cy - 42}" width="72" height="36" fill="url(#sky)"/>${stars}
        <circle cx="${cx}" cy="${cy - 19}" r="12.5" fill="url(#moonG)"/>
        <circle cx="${n(cx + off)}" cy="${cy - 19}" r="13" fill="#07122b" opacity="0.92"/></g>`);
      p.push(`<path d="M ${cx - 35} ${cy - 6} A 35 35 0 0 1 ${cx + 35} ${cy - 6} Z" fill="none" stroke="${c.metal[1]}" stroke-width="1.3"/>`);
    }
    p.push(T(cx - 15, cy + 28, 17, c.accent, D.dow, 'letter-spacing="1"'));
    p.push(T(cx + 18, cy + 30, 30, wText, D.day, 'font-weight="600"')); }

  // 12 h — météo
  { const w = 150, h = 58, x = C - w / 2, y = 44;
    if (!aod) {
      p.push(`<rect x="${x - 2}" y="${y - 2}" width="${w + 4}" height="${h + 4}" rx="14" fill="url(#metalH)" filter="url(#drop)"/>`);
      p.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="12" fill="url(#well)"/>`);
      const ix = x + 30, iy = y + 27;
      let sun = `<circle cx="${ix - 4}" cy="${iy - 5}" r="9" fill="${c.accent2}"/>`;
      for (let k = 0; k < 8; k++) { const [a1, b1] = polar(12.5, k * 45, ix - 4, iy - 5), [a2, b2] = polar(16, k * 45, ix - 4, iy - 5);
        sun += `<line x1="${n(a1)}" y1="${n(b1)}" x2="${n(a2)}" y2="${n(b2)}" stroke="${c.accent2}" stroke-width="1.8" stroke-linecap="round"/>`; }
      sun += `<path d="M ${ix - 12} ${iy + 13} h 26 a 7.5 7.5 0 0 0 -2.5 -14.6 a 10 10 0 0 0 -19 2.8 a 6.4 6.4 0 0 0 -4.5 11.8 z" fill="#E7ECF1"/>`;
      p.push(sun);
      p.push(T(x + 84, y + 38, 34, c.wellText || c.text, `${D.temp}°`, 'font-weight="600"'));
      p.push(`<text x="${x + w - 12}" y="${y + 24}" font-family="Barlow" font-size="14" fill="${c.accent2}" text-anchor="end">${D.tmax}°</text>`);
      p.push(`<text x="${x + w - 12}" y="${y + 43}" font-family="Barlow" font-size="14" fill="${c.wellSoft || c.soft}" text-anchor="end">${D.tmin}°</text>`);
    } else {
      p.push(T(C, y + 38, 30, '#D5DBE1', `${D.temp}°`));
    } }

  // Marque discrète + prochain événement (complication) au centre haut
  if (!aod) {
    p.push(`<text x="${C}" y="${C - 64}" font-family="Cormorant" font-size="15" letter-spacing="4.5" fill="${c.text}" fill-opacity="0.85" text-anchor="middle">MÉRIDIEN</text>`);
    p.push(T(C, C - 40, 15, c.text, D.event, 'letter-spacing="1"'));
  }
  // Pas, en bas
  p.push(T(C, C + 190, 18, aod ? '#D5DBE1' : c.text, `<tspan fill="${c.accent}" font-weight="600">${D.steps.toLocaleString('fr-FR')}</tspan> PAS`, 'letter-spacing="1"'));

  // --- Aiguilles ---------------------------------------------------------------------
  const sword = (len, w, angle, tail) => {
    const half = w / 2;
    if (aod) return `<g transform="rotate(${n(angle)} ${C} ${C})"><path d="M ${C} ${C - len} L ${C - half} ${C - len + 16} L ${C - half} ${C + tail} L ${C + half} ${C + tail} L ${C + half} ${C - len + 16} Z" fill="#000" stroke="#d5dbe1" stroke-width="1.4"/></g>`;
    return `<g transform="rotate(${n(angle)} ${C} ${C})" filter="url(#hand)">
      <path d="M ${C} ${C - len} L ${C - half} ${C - len + 16} L ${C - half} ${C + tail} L ${C} ${C + tail} Z" fill="${c.metal[0]}"/>
      <path d="M ${C} ${C - len} L ${C + half} ${C - len + 16} L ${C + half} ${C + tail} L ${C} ${C + tail} Z" fill="${c.metal[2]}"/>
      <rect x="${C - half + 2.4}" y="${C - len + 20}" width="${w - 4.8}" height="${len - 50}" rx="1.4" fill="${c.lume}" opacity="0.92"/></g>`;
  };
  p.push(sword(112, 12, (D.h % 12 + D.m / 60) * 30, 16));
  p.push(sword(172, 10, (D.m + D.s / 60) * 6, 20));
  if (!aod) {
    p.push(`<g transform="rotate(${D.s * 6} ${C} ${C})" filter="url(#drop)">
      <line x1="${C}" y1="${C + 36}" x2="${C}" y2="${C - 182}" stroke="${c.accent}" stroke-width="1.8"/>
      <circle cx="${C}" cy="${C + 30}" r="5" fill="none" stroke="${c.accent}" stroke-width="2"/></g>`);
  }
  p.push(`<circle cx="${C}" cy="${C}" r="6.5" fill="${aod ? '#000' : c.accent}" stroke="${aod ? '#d5dbe1' : c.metal[2]}"/>`);
  p.push(`<circle cx="${C}" cy="${C}" r="2.2" fill="${aod ? '#d5dbe1' : c.metal[0]}"/>`);

  const style = `<style>
    @font-face { font-family: Cormorant; src: url('${font('cormorant-garamond-latin-600-normal.woff2')}'); }
    @font-face { font-family: Barlow; font-weight: 500; src: url('${font('barlow-condensed-latin-500-normal.woff2')}'); }
    @font-face { font-family: Barlow; font-weight: 600; src: url('${font('barlow-condensed-latin-600-normal.woff2')}'); }
    text { font-weight: 500; }</style>`;
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
for (const [name, c] of Object.entries(COLORWAYS)) {
  const out = join(here, `meridien-${name}.png`);
  await render(face(c), out);
  outs.push(out);
}
await render(face(COLORWAYS['anthracite-orange'], true), join(here, 'meridien-aod.png'));
await browser.close();

execFileSync('convert', [...outs, join(here, 'meridien-aod.png'), '-background', '#1E1F22',
  '-splice', '24x0', '+append', '-chop', '24x0', join(here, 'planche.png')]);
const skin = join(here, '..', '..', 'race', 'emulator', 'skin-galaxy-watch8-classic', 'background.png');
if (existsSync(skin)) {
  execFileSync('convert', [skin, outs[0], '-geometry', '+101+191', '-composite', join(here, 'meridien-montre.png')]);
  console.log(join(here, 'meridien-montre.png'));
}
