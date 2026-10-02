// Maquette « Nocturne » : cadran analogique d'inspiration haute horlogerie (dessin original).
//
//   node concepts/nocturne/render.mjs
//
// Produit : nocturne-<coloris>.png (438 x 438), nocturne-aod.png, planche.png (les coloris
// côte à côte) et nocturne-montre.png (dans le skin Galaxy Watch8 Classic de race/emulator).
//
// Éléments : cadran soleillé, rehaut avec chemin de fer, index appliqués facettés avec insert
// luminescent, aiguilles dauphine bicolores, petite seconde guillochée à 6 h, guichet de date
// à 3 h, ombres portées des aiguilles. Tout est transposable en Watch Face Format : soleillé,
// index et aiguilles en PNG, rotations par Transform (cf. race/tools/generate.py).
import { chromium } from 'playwright';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { writeFileSync, unlinkSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

const here = dirname(fileURLToPath(import.meta.url));
const W = 438, C = W / 2;
const TIME = { h: 10, m: 9, s: 36, day: 2 };

const COLORWAYS = {
  'bleu-nuit': {
    dial: ['#1B4A8F', '#0C2550', '#050F24'], ray: '#9CC2FF',
    metal: ['#F4F6F8', '#9EA6B0', '#5A626C'], lume: '#E9F1E4',
    text: '#DCE3EC', accent: '#C9D3DF', seconds: '#E8EDF2',
  },
  'vert-imperial': {
    dial: ['#1D6B4C', '#0B3A28', '#031A11'], ray: '#A6F0C8',
    metal: ['#FFF1C9', '#D9B568', '#8A6A2A'], lume: '#F6EBCB',
    text: '#EBD9A8', accent: '#D9B568', seconds: '#F0D58C',
  },
  'saumon': {
    dial: ['#F2BBA2', '#D88E73', '#9C5640'], ray: '#FFE6DA',
    metal: ['#5B6470', '#262B31', '#0F1215'], lume: '#FFF8EE',
    text: '#3A2A25', accent: '#4A3A34', seconds: '#1E5FB4',
  },
};

const polar = (r, a, cx = C, cy = C) => {
  const t = (a * Math.PI) / 180;
  return [cx + r * Math.sin(t), cy - r * Math.cos(t)];
};
const n = (v) => Math.round(v * 100) / 100;
const font = (file) => pathToFileURL(join(here, 'fonts', file)).href;

function face(c, aod = false) {
  const p = [];
  const defs = [];
  const SUB = { x: C, y: 300, r: 46 };     // petite seconde
  // --- Cadran ---------------------------------------------------------------
  if (aod) {
    p.push(`<rect width="${W}" height="${W}" fill="#000"/>`);
  } else {
    defs.push(`<radialGradient id="dial" cx="${C}" cy="${C - 40}" r="${C + 60}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="${c.dial[0]}"/><stop offset="0.6" stop-color="${c.dial[1]}"/>
      <stop offset="1" stop-color="${c.dial[2]}"/></radialGradient>`);
    p.push(`<rect width="${W}" height="${W}" fill="url(#dial)"/>`);
    // Soleillé : rayons fins dont l'éclat varie avec l'angle (reflet de la lumière)
    const rays = [];
    for (let i = 0; i < 720; i++) {
      const a = i / 2;
      const sheen = Math.pow(Math.max(0, Math.cos(((a - 315) * Math.PI) / 180)), 3) * 0.16
                  + Math.pow(Math.max(0, Math.cos(((a - 135) * Math.PI) / 180)), 3) * 0.10;
      const [x, y] = polar(C, a);
      rays.push(`<line x1="${C}" y1="${C}" x2="${n(x)}" y2="${n(y)}" stroke="${c.ray}" stroke-opacity="${(0.015 + sheen * (i % 2 ? 1 : 0.55)).toFixed(3)}" stroke-width="0.9"/>`);
    }
    p.push(`<g>${rays.join('')}</g>`);
    // Rehaut : anneau plus sombre, incliné
    p.push(`<circle cx="${C}" cy="${C}" r="${C - 9}" fill="none" stroke="#000" stroke-opacity="0.28" stroke-width="18"/>`);
  }
  // Chemin de fer + minutes sur le rehaut
  const track = [];
  for (let m = 0; m < 60; m++) {
    const a = m * 6, major = m % 5 === 0;
    const [x1, y1] = polar(C - (major ? 17 : 14), a);
    const [x2, y2] = polar(C - 4, a);
    track.push(`<line x1="${n(x1)}" y1="${n(y1)}" x2="${n(x2)}" y2="${n(y2)}" stroke="${aod ? '#5c636b' : c.accent}" stroke-width="${major ? 1.8 : 0.9}" stroke-opacity="${aod ? 1 : 0.85}"/>`);
  }
  p.push(track.join(''));
  p.push(`<circle cx="${C}" cy="${C}" r="${C - 18.5}" fill="none" stroke="${aod ? '#3a3f45' : c.accent}" stroke-opacity="0.6" stroke-width="0.8"/>`);

  // --- Index appliqués ---------------------------------------------------------
  defs.push(`<linearGradient id="metalH" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="${c.metal[1]}"/><stop offset="0.45" stop-color="${c.metal[0]}"/>
    <stop offset="0.55" stop-color="${c.metal[2]}"/><stop offset="1" stop-color="${c.metal[1]}"/></linearGradient>`);
  defs.push(`<filter id="drop" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="1.6"/><feOffset dx="1.6" dy="2.4"/>
    <feComponentTransfer><feFuncA type="linear" slope="0.55"/></feComponentTransfer>
    <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>`);
  defs.push(`<filter id="handShadow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="2.6"/><feOffset dx="3" dy="5"/>
    <feComponentTransfer><feFuncA type="linear" slope="0.5"/></feComponentTransfer>
    <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>`);
  const marker = (a, double = false) => {
    const len = 38, w = 9, r0 = C - 24 - len;
    const one = (dx) => {
      const fill = aod ? '#000' : 'url(#metalH)';
      const stroke = aod ? '#9aa3ad' : c.metal[2];
      const lume = aod ? '' : `<rect x="${n(C + dx - 1.6)}" y="${n(C - r0 - len + 7)}" width="3.2" height="${len - 14}" rx="1.6" fill="${c.lume}" opacity="0.92"/>`;
      return `<rect x="${n(C + dx - w / 2)}" y="${n(C - r0 - len)}" width="${w}" height="${len}" rx="1.5" fill="${fill}" stroke="${stroke}" stroke-width="${aod ? 1.2 : 0.6}"/>${lume}`;
    };
    const body = double ? one(-7) + one(7) : one(0);
    return `<g transform="rotate(${a} ${C} ${C})" ${aod ? '' : 'filter="url(#drop)"'}>${body}</g>`;
  };
  for (let h = 0; h < 12; h++) {
    if (h === 3 || h === 6) continue;  // guichet de date, petite seconde
    p.push(marker(h * 30, h === 0));
  }

  // --- Écritures -----------------------------------------------------------------
  if (!aod) {
    p.push(`<text x="${C}" y="132" font-family="Cormorant" font-size="27" letter-spacing="6" fill="${c.text}" text-anchor="middle">NOCTURNE</text>`);
    p.push(`<line x1="${C - 26}" y1="142" x2="${C + 26}" y2="142" stroke="${c.text}" stroke-opacity="0.5" stroke-width="0.8"/>`);
    p.push(`<text x="${C}" y="156" font-family="Montserrat" font-size="7.5" letter-spacing="3.2" fill="${c.text}" fill-opacity="0.75" text-anchor="middle">ATELIER · SUMMIT</text>`);
  }

  // --- Guichet de date à 3 h ----------------------------------------------------
  const dx = C + 128, dw = 34, dh = 26;
  if (!aod) {
    p.push(`<rect x="${dx - 2}" y="${C - dh / 2 - 2}" width="${dw + 4}" height="${dh + 4}" rx="3" fill="url(#metalH)" filter="url(#drop)"/>`);
    p.push(`<rect x="${dx}" y="${C - dh / 2}" width="${dw}" height="${dh}" rx="2" fill="#F7F4EE"/>`);
    p.push(`<rect x="${dx}" y="${C - dh / 2}" width="${dw}" height="5" fill="#000" fill-opacity="0.12"/>`);
    p.push(`<text x="${dx + dw / 2}" y="${C + 7.5}" font-family="Cormorant" font-size="22" fill="#1b1b1b" text-anchor="middle">${TIME.day}</text>`);
  }

  // --- Petite seconde guillochée à 6 h -----------------------------------------------
  if (!aod) {
    defs.push(`<radialGradient id="sub" cx="${SUB.x}" cy="${SUB.y - 10}" r="${SUB.r + 8}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#000" stop-opacity="0.05"/><stop offset="0.85" stop-color="#000" stop-opacity="0.22"/>
      <stop offset="1" stop-color="#000" stop-opacity="0.45"/></radialGradient>`);
    p.push(`<circle cx="${SUB.x}" cy="${SUB.y}" r="${SUB.r}" fill="url(#sub)"/>`);
    const rings = [];
    for (let r = 3; r < SUB.r - 10; r += 2.2) {
      rings.push(`<circle cx="${SUB.x}" cy="${SUB.y}" r="${n(r)}" fill="none" stroke="${c.ray}" stroke-opacity="${r % 4.4 < 2.2 ? 0.10 : 0.04}" stroke-width="1"/>`);
    }
    p.push(rings.join(''));
    p.push(`<circle cx="${SUB.x}" cy="${SUB.y}" r="${SUB.r}" fill="none" stroke="${c.metal[1]}" stroke-width="1.4"/>`);
    const st = [];
    for (let s = 0; s < 60; s++) {
      const a = s * 6, major = s % 10 === 0;
      const [x1, y1] = polar(SUB.r - (major ? 8 : 4.5), a, SUB.x, SUB.y);
      const [x2, y2] = polar(SUB.r - 1.5, a, SUB.x, SUB.y);
      st.push(`<line x1="${n(x1)}" y1="${n(y1)}" x2="${n(x2)}" y2="${n(y2)}" stroke="${c.accent}" stroke-width="${major ? 1.4 : 0.7}"/>`);
    }
    p.push(st.join(''));
    for (const [v, a] of [[60, 0], [20, 120], [40, 240]]) {
      const [x, y] = polar(SUB.r - 17, a, SUB.x, SUB.y);
      p.push(`<text x="${n(x)}" y="${n(y + 3.5)}" font-family="Montserrat" font-size="9" fill="${c.text}" fill-opacity="0.85" text-anchor="middle">${v}</text>`);
    }
  } else {
    p.push(`<circle cx="${SUB.x}" cy="${SUB.y}" r="${SUB.r}" fill="none" stroke="#3a3f45" stroke-width="1.2"/>`);
  }

  // --- Aiguilles ---------------------------------------------------------------------
  // Dauphine : losange effilé, deux facettes (une claire, une sombre)
  const dauphine = (len, wBase, tail, angle) => {
    const half = wBase / 2;
    const left = `M ${C} ${C - len} L ${C - half} ${C - len * 0.18} L ${C} ${C + tail} Z`;
    const right = `M ${C} ${C - len} L ${C + half} ${C - len * 0.18} L ${C} ${C + tail} Z`;
    if (aod) {
      return `<g transform="rotate(${n(angle)} ${C} ${C})"><path d="M ${C} ${C - len} L ${C - half} ${C - len * 0.18} L ${C} ${C + tail} L ${C + half} ${C - len * 0.18} Z" fill="#000" stroke="#d5dbe1" stroke-width="1.4"/></g>`;
    }
    return `<g transform="rotate(${n(angle)} ${C} ${C})" filter="url(#handShadow)">
      <path d="${left}" fill="${c.metal[0]}"/><path d="${right}" fill="${c.metal[2]}"/>
      <path d="M ${C} ${C - len * 0.86} L ${C} ${C - len * 0.32}" stroke="${c.lume}" stroke-width="2.4" stroke-linecap="round" opacity="0.9"/></g>`;
  };
  const hourA = (TIME.h % 12 + TIME.m / 60) * 30;
  const minA = (TIME.m + TIME.s / 60) * 6;
  p.push(dauphine(118, 15, 14, hourA));
  p.push(dauphine(184, 12, 18, minA));
  // Moyeu
  p.push(`<circle cx="${C}" cy="${C}" r="6.5" fill="${aod ? '#000' : c.metal[1]}" stroke="${aod ? '#d5dbe1' : c.metal[2]}" stroke-width="1"/>`);
  p.push(`<circle cx="${C}" cy="${C}" r="2.2" fill="${aod ? '#d5dbe1' : c.metal[0]}"/>`);
  // Trotteuse de la petite seconde (masquée en AOD)
  if (!aod) {
    const sa = TIME.s * 6;
    p.push(`<g transform="rotate(${sa} ${SUB.x} ${SUB.y})" filter="url(#drop)">
      <line x1="${SUB.x}" y1="${SUB.y + 9}" x2="${SUB.x}" y2="${SUB.y - SUB.r + 5}" stroke="${c.seconds}" stroke-width="1.3"/>
      <circle cx="${SUB.x}" cy="${SUB.y}" r="3" fill="${c.seconds}"/></g>`);
  }

  const style = `<style>
    @font-face { font-family: Cormorant; src: url('${font('cormorant-garamond-latin-600-normal.woff2')}'); }
    @font-face { font-family: Montserrat; src: url('${font('montserrat-latin-500-normal.woff2')}'); }
  </style>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${W}" viewBox="0 0 ${W} ${W}">
    ${style}<defs>${defs.join('')}<clipPath id="round"><circle cx="${C}" cy="${C}" r="${C}"/></clipPath></defs>
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
  const out = join(here, `nocturne-${name}.png`);
  await render(face(c), out);
  outs.push(out);
}
await render(face(COLORWAYS['bleu-nuit'], true), join(here, 'nocturne-aod.png'));
await browser.close();

// Planche des coloris + AOD, et le premier coloris dans le skin de la montre (ImageMagick)
execFileSync('convert', [...outs, join(here, 'nocturne-aod.png'), '-background', '#1E1F22',
  '-splice', '24x0', '+append', '-chop', '24x0', join(here, 'planche.png')]);
const skin = join(here, '..', '..', 'race', 'emulator', 'skin-galaxy-watch8-classic', 'background.png');
if (existsSync(skin)) {
  execFileSync('convert', [skin, outs[0], '-geometry', '+101+191', '-composite', join(here, 'nocturne-montre.png')]);
  console.log(join(here, 'nocturne-montre.png'));
}
