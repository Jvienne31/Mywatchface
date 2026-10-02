// Maquette « Méridien » : finition haute horlogerie, densité d'information d'une montre
// connectée. Dessin original.
//
//   node concepts/meridien/render.mjs
//
// Chaque compteur porte une donnée, comme les compteurs d'un chronographe :
//   9 h  fréquence cardiaque (aiguille + valeur)      [HEART_RATE]
//   3 h  batterie façon réserve de marche             [BATTERY_PERCENT]
//   6 h  phase de lune + jour et date                 [MOON_PHASE_POSITION] [DAY_OF_WEEK] [DAY]
//   12 h météo : icône, température, min / max        [WEATHER.*] (WFF v2)
//   pourtour : anneau de progression des pas          [STEP_PERCENT] [STEP_COUNT]
//   bas : ligne de complication (prochain événement), trotteuse centrale.
import { chromium } from 'playwright';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { writeFileSync, unlinkSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

const here = dirname(fileURLToPath(import.meta.url));
const W = 438, C = W / 2;
const D = {
  h: 10, m: 9, s: 36, hr: 72, batt: 68, steps: 6420, stepPct: 64,
  temp: 18, tmin: 11, tmax: 22, cond: 'NUAGEUX', moon: 0.62,   // 0 nouvelle, 0.5 pleine
  dow: 'VEN', day: 2, event: '14:30  RÉUNION ÉQUIPE',
};

const COLORWAYS = {
  'anthracite-orange': {
    dial: ['#3A3E44', '#202327', '#0E1012'], ray: '#FFFFFF', sub: '#121416',
    metal: ['#F2F4F6', '#A1A8B0', '#555C64'], lume: '#EAF2E6', text: '#D9DEE3',
    accent: '#FF7A1A', accent2: '#FFB36B',
  },
  'bleu-glacier': {
    dial: ['#1C3F73', '#0E2346', '#061226'], ray: '#BFD8FF', sub: '#081831',
    metal: ['#F4F6F8', '#9EA6B0', '#5A626C'], lume: '#E9F1E4', text: '#DCE5EF',
    accent: '#36D3F2', accent2: '#9BEAFB',
  },
  'panda': {
    dial: ['#F5F4F0', '#E2E0DA', '#BEBBB3'], ray: '#000000', sub: '#17191C',
    metal: ['#4B525B', '#1E2226', '#0A0C0E'], lume: '#F7F3E8', text: '#25292E',
    accent: '#D7262E', accent2: '#FF6B6B', subText: '#D9DEE3',
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

function face(c, aod = false) {
  const p = [], defs = [];
  const subText = c.subText || c.text;
  const lineCol = aod ? '#5c636b' : c.text;
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
  defs.push(`<radialGradient id="well" cx="0.5" cy="0.4" r="0.6"><stop offset="0" stop-color="${c.sub}" stop-opacity="0.75"/>
    <stop offset="1" stop-color="#000" stop-opacity="0.95"/></radialGradient>`);

  // --- Cadran soleillé + rehaut ---------------------------------------------------
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
    p.push(`<circle cx="${C}" cy="${C}" r="${C - 9}" fill="none" stroke="#000" stroke-opacity="0.32" stroke-width="18"/>`);
  }
  // Chemin de fer
  for (let m = 0; m < 60; m++) {
    const a = m * 6, major = m % 5 === 0;
    const [x1, y1] = polar(C - (major ? 16 : 13), a), [x2, y2] = polar(C - 4, a);
    p.push(`<line x1="${n(x1)}" y1="${n(y1)}" x2="${n(x2)}" y2="${n(y2)}" stroke="${lineCol}" stroke-opacity="0.8" stroke-width="${major ? 1.8 : 0.8}"/>`);
  }
  // Anneau d'activité (pas) juste sous le rehaut
  const RA = C - 22;
  p.push(`<circle cx="${C}" cy="${C}" r="${RA}" fill="none" stroke="${aod ? '#1c1f22' : '#000'}" stroke-opacity="${aod ? 1 : 0.35}" stroke-width="4"/>`);
  p.push(`<path d="${arcPath(C, C, RA, 0, 360 * D.stepPct / 100)}" fill="none" stroke="${c.accent}" stroke-width="4" stroke-linecap="round"/>`);
  { const [x, y] = polar(RA, 360 * D.stepPct / 100);
    p.push(`<circle cx="${n(x)}" cy="${n(y)}" r="4.5" fill="${aod ? '#000' : c.accent2}" stroke="${c.accent}" stroke-width="1.5"/>`); }

  // --- Index appliqués (sauf 3, 6, 9 occupés par les compteurs) ----------------------
  const marker = (a, dbl) => {
    const len = 24, w = 8, rOut = C - 30;
    const one = (dx) => `<rect x="${n(C + dx - w / 2)}" y="${n(C - rOut)}" width="${w}" height="${len}" rx="1.4"
      fill="${aod ? '#000' : 'url(#metalH)'}" stroke="${aod ? '#9aa3ad' : c.metal[2]}" stroke-width="${aod ? 1.1 : 0.6}"/>` +
      (aod ? '' : `<rect x="${n(C + dx - 1.5)}" y="${n(C - rOut + 5)}" width="3" height="${len - 10}" rx="1.5" fill="${c.lume}" opacity="0.9"/>`);
    return `<g transform="rotate(${a} ${C} ${C})" ${aod ? '' : 'filter="url(#drop)"'}>${dbl ? one(-6) + one(6) : one(0)}</g>`;
  };
  for (let h = 0; h < 12; h++) if (h % 3 !== 0 || h === 0) p.push(marker(h * 30, h === 0));

  // --- Compteurs -------------------------------------------------------------------
  const SR = 50;
  const subdial = (cx, cy) => {
    if (aod) return `<circle cx="${cx}" cy="${cy}" r="${SR}" fill="#000" stroke="#3a3f45" stroke-width="1.2"/>`;
    let s = `<circle cx="${cx}" cy="${cy}" r="${SR + 3}" fill="url(#metalH)" filter="url(#drop)"/>`;
    s += `<circle cx="${cx}" cy="${cy}" r="${SR}" fill="url(#well)"/>`;
    for (let r = 4; r < SR - 4; r += 2.4)   // guilloché
      s += `<circle cx="${cx}" cy="${cy}" r="${n(r)}" fill="none" stroke="#fff" stroke-opacity="${r % 4.8 < 2.4 ? 0.05 : 0.02}"/>`;
    return s;
  };
  const scale = (cx, cy, a0, sweep, count, labels) => {
    let s = '';
    for (let i = 0; i < count; i++) {
      const a = a0 + sweep * i / (count - 1), major = labels && labels[i] !== undefined;
      const [x1, y1] = polar(SR - (major ? 9 : 5), a, cx, cy), [x2, y2] = polar(SR - 2, a, cx, cy);
      s += `<line x1="${n(x1)}" y1="${n(y1)}" x2="${n(x2)}" y2="${n(y2)}" stroke="${aod ? '#5c636b' : subText}" stroke-width="${major ? 1.3 : 0.7}"/>`;
      if (major && !aod) {
        const [lx, ly] = polar(SR - 17, a, cx, cy);
        s += `<text x="${n(lx)}" y="${n(ly + 3)}" font-family="Montserrat" font-size="7.5" fill="${subText}" fill-opacity="0.8" text-anchor="middle">${labels[i]}</text>`;
      }
    }
    return s;
  };
  const needle = (cx, cy, a, len) => aod
    ? `<g transform="rotate(${n(a)} ${cx} ${cy})"><line x1="${cx}" y1="${cy + 6}" x2="${cx}" y2="${cy - len}" stroke="${c.accent}" stroke-width="1.6"/></g>`
    : `<g transform="rotate(${n(a)} ${cx} ${cy})" filter="url(#drop)"><path d="M ${cx - 2.2} ${cy + 8} L ${cx} ${cy - len} L ${cx + 2.2} ${cy + 8} Z" fill="${c.accent}"/>
       <circle cx="${cx}" cy="${cy}" r="3.6" fill="${c.metal[1]}"/></g>`;

  // 9 h — cardio, 40 à 200, sur 270°
  { const cx = C - 104, cy = C;
    p.push(subdial(cx, cy));
    p.push(scale(cx, cy, -135, 270, 17, { 0: 40, 4: 80, 8: 120, 12: 160, 16: 200 }));
    if (!aod) p.push(`<path d="${arcPath(cx, cy, SR - 4, 135 - 270 * 40 / 160, 135)}" fill="none" stroke="${c.accent}" stroke-opacity="0.55" stroke-width="3"/>`);
    p.push(`<text x="${cx}" y="${cy + 22}" font-family="Montserrat" font-size="14" fill="${aod ? '#d5dbe1' : subText}" text-anchor="middle">${D.hr}</text>`);
    p.push(`<text x="${cx}" y="${cy + 33}" font-family="Montserrat" font-size="6.5" letter-spacing="1.5" fill="${c.accent}" text-anchor="middle">BPM</text>`);
    p.push(needle(cx, cy, -135 + 270 * (D.hr - 40) / 160, SR - 8)); }

  // 3 h — réserve de marche (batterie), 0 à 100 sur 240°
  { const cx = C + 104, cy = C;
    p.push(subdial(cx, cy));
    p.push(scale(cx, cy, -120, 240, 11, { 0: 0, 5: 50, 10: 100 }));
    if (!aod) p.push(`<path d="${arcPath(cx, cy, SR - 4, -120, -120 + 240 * 0.2)}" fill="none" stroke="#E5484D" stroke-width="3"/>`);
    p.push(`<text x="${cx}" y="${cy + 22}" font-family="Montserrat" font-size="14" fill="${aod ? '#d5dbe1' : subText}" text-anchor="middle">${D.batt}%</text>`);
    p.push(`<text x="${cx}" y="${cy + 33}" font-family="Montserrat" font-size="6.5" letter-spacing="1.5" fill="${c.accent}" text-anchor="middle">RÉSERVE</text>`);
    p.push(needle(cx, cy, -120 + 240 * D.batt / 100, SR - 8)); }

  // 6 h — phase de lune + jour / date
  { const cx = C, cy = C + 100;
    p.push(subdial(cx, cy));
    if (!aod) {
      defs.push(`<clipPath id="moonWin"><path d="M ${cx - 30} ${cy - 2} A 30 30 0 0 1 ${cx + 30} ${cy - 2} Z"/></clipPath>`);
      defs.push(`<radialGradient id="sky" cx="0.5" cy="1" r="1"><stop offset="0" stop-color="#1b3b78"/><stop offset="1" stop-color="#07122b"/></radialGradient>`);
      defs.push(`<radialGradient id="moonG" cx="0.4" cy="0.35" r="0.7"><stop offset="0" stop-color="#FFF6D6"/><stop offset="1" stop-color="#D9B568"/></radialGradient>`);
      // ciel étoilé + lune (ombre décalée selon la phase)
      const off = (D.moon - 0.5) * 2 * 26;
      let stars = '';
      for (const [sx, sy, r] of [[-22, -10, 0.9], [-12, -22, 0.7], [15, -18, 0.8], [24, -7, 0.6], [4, -26, 0.6], [-25, -4, 0.5]])
        stars += `<circle cx="${cx + sx}" cy="${cy + sy}" r="${r}" fill="#fff" opacity="0.85"/>`;
      p.push(`<g clip-path="url(#moonWin)"><rect x="${cx - 32}" y="${cy - 34}" width="64" height="34" fill="url(#sky)"/>${stars}
        <circle cx="${cx}" cy="${cy - 13}" r="11" fill="url(#moonG)"/>
        <circle cx="${n(cx + off)}" cy="${cy - 13}" r="11.5" fill="#07122b" opacity="0.92"/></g>`);
      p.push(`<path d="M ${cx - 31} ${cy - 2} A 31 31 0 0 1 ${cx + 31} ${cy - 2} Z" fill="none" stroke="${c.metal[1]}" stroke-width="1.2"/>`);
    }
    p.push(`<text x="${cx}" y="${cy + 16}" font-family="Montserrat" font-size="9" letter-spacing="2" fill="${c.accent}" text-anchor="middle">${D.dow}</text>`);
    p.push(`<text x="${cx}" y="${cy + 36}" font-family="Cormorant" font-size="22" fill="${aod ? '#d5dbe1' : subText}" text-anchor="middle">${D.day}</text>`); }

  // 12 h — météo dans un cartouche appliqué
  { const x = C - 58, y = 64, w = 116, h = 50;
    if (!aod) {
      p.push(`<rect x="${x - 2}" y="${y - 2}" width="${w + 4}" height="${h + 4}" rx="12" fill="url(#metalH)" filter="url(#drop)"/>`);
      p.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="10" fill="url(#well)"/>`);
      // icône soleil voilé
      const ix = x + 24, iy = y + 22;
      let sun = `<circle cx="${ix - 3}" cy="${iy - 4}" r="7" fill="${c.accent2}"/>`;
      for (let k = 0; k < 8; k++) { const [a1, b1] = polar(10, k * 45, ix - 3, iy - 4), [a2, b2] = polar(13, k * 45, ix - 3, iy - 4);
        sun += `<line x1="${n(a1)}" y1="${n(b1)}" x2="${n(a2)}" y2="${n(b2)}" stroke="${c.accent2}" stroke-width="1.4" stroke-linecap="round"/>`; }
      sun += `<path d="M ${ix - 9} ${iy + 10} h 20 a 6 6 0 0 0 -2 -11.6 a 8 8 0 0 0 -15 2.2 a 5 5 0 0 0 -3 9.4 z" fill="#E7ECF1"/>`;
      p.push(sun);
      p.push(`<text x="${x + 76}" y="${y + 26}" font-family="Montserrat" font-size="20" fill="${c.subText || '#E8EDF2'}" text-anchor="middle">${D.temp}°</text>`);
      p.push(`<text x="${x + 76}" y="${y + 39}" font-family="Montserrat" font-size="7" letter-spacing="0.6" fill="${c.subText || '#E8EDF2'}" fill-opacity="0.75" text-anchor="middle">MAX ${D.tmax}° · MIN ${D.tmin}°</text>`);
      p.push(`<text x="${x + 24}" y="${y + 44}" font-family="Montserrat" font-size="5.6" letter-spacing="0.8" fill="${c.accent}" text-anchor="middle">${D.cond}</text>`);
    } else {
      p.push(`<text x="${C}" y="${y + 30}" font-family="Montserrat" font-size="16" fill="#d5dbe1" text-anchor="middle">${D.temp}°</text>`);
    } }

  // Bas : pas + complication « prochain événement »
  if (!aod) {
    p.push(`<text x="${C}" y="${C + 168}" font-family="Montserrat" font-size="8" letter-spacing="2.2" fill="${c.text}" text-anchor="middle"><tspan fill="${c.accent}">${D.steps.toLocaleString('fr-FR')}</tspan> PAS · ${D.stepPct} %</text>`);
    p.push(`<text x="${C}" y="${C + 181}" font-family="Montserrat" font-size="7" letter-spacing="1.6" fill="${c.text}" fill-opacity="0.7" text-anchor="middle">${D.event}</text>`);
  }
  // Signature
  if (!aod) {
    p.push(`<text x="${C}" y="${C - 52}" font-family="Cormorant" font-size="17" letter-spacing="4.5" fill="${c.text}" text-anchor="middle">MÉRIDIEN</text>`);
    p.push(`<text x="${C}" y="${C - 41}" font-family="Montserrat" font-size="5.5" letter-spacing="2.4" fill="${c.text}" fill-opacity="0.65" text-anchor="middle">COMPLICATION CONNECTÉE</text>`);
  }

  // --- Aiguilles ---------------------------------------------------------------------
  const sword = (len, w, angle, tail) => {
    const half = w / 2;
    if (aod) return `<g transform="rotate(${n(angle)} ${C} ${C})"><path d="M ${C} ${C - len} L ${C - half} ${C - len + 16} L ${C - half} ${C + tail} L ${C + half} ${C + tail} L ${C + half} ${C - len + 16} Z" fill="#000" stroke="#d5dbe1" stroke-width="1.3"/></g>`;
    return `<g transform="rotate(${n(angle)} ${C} ${C})" filter="url(#hand)">
      <path d="M ${C} ${C - len} L ${C - half} ${C - len + 16} L ${C - half} ${C + tail} L ${C} ${C + tail} Z" fill="${c.metal[0]}"/>
      <path d="M ${C} ${C - len} L ${C + half} ${C - len + 16} L ${C + half} ${C + tail} L ${C} ${C + tail} Z" fill="${c.metal[2]}"/>
      <rect x="${C - half + 2.2}" y="${C - len + 20}" width="${w - 4.4}" height="${len - 50}" rx="1.4" fill="${c.lume}" opacity="0.92"/></g>`;
  };
  p.push(sword(112, 10, (D.h % 12 + D.m / 60) * 30, 16));
  p.push(sword(176, 8, (D.m + D.s / 60) * 6, 20));
  if (!aod) {
    const sa = D.s * 6;
    p.push(`<g transform="rotate(${sa} ${C} ${C})" filter="url(#drop)">
      <line x1="${C}" y1="${C + 40}" x2="${C}" y2="${C - 190}" stroke="${c.accent}" stroke-width="1.4"/>
      <rect x="${C - 2}" y="${C - 168}" width="4" height="12" rx="1" fill="${c.accent}"/>
      <circle cx="${C}" cy="${C + 34}" r="5" fill="none" stroke="${c.accent}" stroke-width="1.6"/></g>`);
  }
  p.push(`<circle cx="${C}" cy="${C}" r="6" fill="${aod ? '#000' : c.accent}" stroke="${aod ? '#d5dbe1' : c.metal[2]}"/>`);
  p.push(`<circle cx="${C}" cy="${C}" r="2" fill="${aod ? '#d5dbe1' : c.metal[0]}"/>`);

  const style = `<style>
    @font-face { font-family: Cormorant; src: url('${font('cormorant-garamond-latin-600-normal.woff2')}'); }
    @font-face { font-family: Montserrat; src: url('${font('montserrat-latin-500-normal.woff2')}'); }</style>`;
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
