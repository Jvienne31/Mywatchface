// Maquette « Palettes » : cadran numérique façon afficheur à palettes (tableaux des départs
// des gares et aéroports). Heures et minutes sur deux lignes. Dessin original.
//
//   node concepts/palettes/render.mjs
//
//   centre          HH / MM : une palette par chiffre (pli central, charnières, ombre)
//   haut            jour, date, mois sur trois palettes
//   colonnes        mini-afficheurs : cardio, pas (+ barre d'objectif), calories /
//                   météo, batterie, lever du soleil
//   bas             prochain événement en « tableau des départs », une lettre par palette
//   pourtour        60 LED : les secondes s'allument au fil de la minute
// En WFF : palettes en PNG (fond + pli), chiffres en texte ou en images, bascule animable
// par Transform sur scaleY au changement de minute.
import { chromium } from 'playwright';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { writeFileSync, unlinkSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

const here = dirname(fileURLToPath(import.meta.url));
const W = 438, C = W / 2;
const D = {
  hh: '10', mm: '09', s: 36, hr: 72, steps: '6420', stepPct: 64, kcal: 412,
  temp: '18°', batt: '68%', sunrise: '07:42', dow: 'VEN', day: '02', mon: 'OCT',
  board: '14:30 RÉUNION',
};

const COLORWAYS = {
  gare:     { body: ['#2A2D31', '#121417'], tile: ['#2E3238', '#1B1E22', '#17191C', '#101214'], digit: '#F4F1E8', accent: '#FFC629', soft: '#8E959D', led: '#2A2E33' },
  cuivre:   { body: ['#2B2420', '#100C0A'], tile: ['#332B26', '#201A17', '#1B1613', '#120E0C'], digit: '#F6EBDD', accent: '#E8895A', soft: '#A08F84', led: '#33281F' },
  arctique: { body: ['#C9CED4', '#8E959D'], tile: ['#FBFCFD', '#E9ECEF', '#E1E5E9', '#D3D8DD'], digit: '#15181B', accent: '#1E7BE0', soft: '#5B636C', led: '#AEB5BC', light: true },
};

const polar = (r, a, cx = C, cy = C) => {
  const t = (a * Math.PI) / 180;
  return [cx + r * Math.sin(t), cy - r * Math.cos(t)];
};
const n = (v) => Math.round(v * 100) / 100;
const fontUrl = (f) => pathToFileURL(join(here, '..', 'strate', 'fonts', f)).href;

function face(c, aod = false) {
  const p = [], defs = [];
  const digit = aod ? '#C9D1D9' : c.digit;
  const soft = aod ? '#6F7882' : c.soft;

  defs.push(`<linearGradient id="tTop" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${c.tile[0]}"/><stop offset="1" stop-color="${c.tile[1]}"/></linearGradient>`);
  defs.push(`<linearGradient id="tBot" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${c.tile[2]}"/><stop offset="1" stop-color="${c.tile[3]}"/></linearGradient>`);
  defs.push(`<filter id="sh" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur in="SourceAlpha" stdDeviation="2"/>
    <feOffset dx="0" dy="3"/><feComponentTransfer><feFuncA type="linear" slope="${c.light ? 0.35 : 0.7}"/></feComponentTransfer>
    <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>`);

  // Une palette : moitié haute / moitié basse, pli, charnières, texte coupé par le pli
  const tile = (x, y, w, h, txt, size, color = digit, opts = {}) => {
    const r = Math.min(5, w / 6), mid = y + h / 2;
    if (aod) {
      return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="#000" stroke="#2c3136" stroke-width="1"/>
        <line x1="${x}" y1="${mid}" x2="${x + w}" y2="${mid}" stroke="#2c3136" stroke-width="1"/>
        <text x="${n(x + w / 2)}" y="${n(mid + size * 0.36)}" font-family="Barlow" font-weight="500" font-size="${size}" fill="${color}" text-anchor="middle" ${opts.ls ? `letter-spacing="${opts.ls}"` : ''}>${txt}</text>`;
    }
    const id = `c${Math.round(x)}_${Math.round(y)}`;
    defs.push(`<clipPath id="${id}"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}"/></clipPath>`);
    let s = `<g filter="url(#sh)"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="url(#tBot)"/></g>`;
    s += `<g clip-path="url(#${id})"><rect x="${x}" y="${y}" width="${w}" height="${h / 2}" fill="url(#tTop)"/>`;
    s += `<text x="${n(x + w / 2)}" y="${n(mid + size * 0.36)}" font-family="Barlow" font-weight="600" font-size="${size}" fill="${color}" text-anchor="middle" ${opts.ls ? `letter-spacing="${opts.ls}"` : ''}>${txt}</text>`;
    // moitié basse légèrement plus sombre : volet incliné
    s += `<rect x="${x}" y="${mid}" width="${w}" height="${h / 2}" fill="#000" fill-opacity="${c.light ? 0.05 : 0.14}"/>`;
    s += `<rect x="${x}" y="${mid - 1}" width="${w}" height="2" fill="#000" fill-opacity="${c.light ? 0.45 : 0.85}"/>`;
    s += `<rect x="${x}" y="${mid + 1}" width="${w}" height="0.8" fill="#fff" fill-opacity="${c.light ? 0.6 : 0.08}"/>`;
    s += `<rect x="${x}" y="${y}" width="${w}" height="1" fill="#fff" fill-opacity="${c.light ? 0.8 : 0.10}"/></g>`;
    if (w > 30) for (const hx of [x - 2, x + w - 1])   // charnières
      s += `<rect x="${hx}" y="${mid - 4}" width="3" height="8" rx="1" fill="${c.light ? '#9AA2AA' : '#4A5057'}"/>`;
    return s;
  };

  // Boîtier : métal sombre brossé (ou clair pour « arctique") ; noir en AOD
  if (aod) p.push(`<rect width="${W}" height="${W}" fill="#000"/>`);
  else {
    defs.push(`<radialGradient id="body" cx="${C}" cy="${C - 50}" r="${C + 40}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="${c.body[0]}"/><stop offset="1" stop-color="${c.body[1]}"/></radialGradient>`);
    defs.push(`<filter id="brush" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.002 0.8" numOctaves="2" seed="4"/>
      <feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.5 -0.12"/></filter>`);
    p.push(`<rect width="${W}" height="${W}" fill="url(#body)"/><rect width="${W}" height="${W}" filter="url(#brush)" opacity="${c.light ? 0.35 : 0.25}"/>`);
  }

  // 60 LED des secondes
  for (let i = 0; i < 60; i++) {
    const [x, y] = polar(C - 11, i * 6);
    const on = i <= D.s, big = i % 5 === 0;
    if (aod && !big) continue;
    const fill = aod ? '#3a3f45' : (on ? c.accent : c.led);
    p.push(`<circle cx="${n(x)}" cy="${n(y)}" r="${big ? 3.4 : 2.4}" fill="${fill}"/>`);
    if (on && !aod && i === D.s) p.push(`<circle cx="${n(x)}" cy="${n(y)}" r="7" fill="${c.accent}" opacity="0.25"/>`);
  }

  // Date : trois palettes en haut
  { const y = 40, h = 32; let x = C - 72;
    for (const [txt, w] of [[D.dow, 50], [D.day, 38], [D.mon, 50]]) {
      p.push(tile(x, y, w, h, txt, 22, txt === D.day ? c.accent : digit, { ls: 1 }));
      x += w + 6;
    } }

  // HH / MM : une palette par chiffre
  { const w = 70, h = 106, gap = 8, y1 = 84, y2 = 200;
    const xs = [C - gap / 2 - w, C + gap / 2];
    [...D.hh].forEach((d, i) => p.push(tile(xs[i], y1, w, h, d, 98)));
    [...D.mm].forEach((d, i) => p.push(tile(xs[i], y2, w, h, d, 98)));
    if (!aod) p.push(`<circle cx="${C}" cy="${y2 - 5}" r="3" fill="${c.accent}"/>`); }

  // Colonnes : mini-afficheurs (libellé en couleur, valeur sur palette)
  const mini = (x, y, label, value, extra = '') => {
    const w = 82, h = 40;
    let s = `<text x="${x + w / 2}" y="${y - 6}" font-family="Barlow" font-weight="600" font-size="13" letter-spacing="1.6" fill="${aod ? soft : c.accent}" text-anchor="middle">${label}</text>`;
    s += tile(x, y, w, h, value, 28, digit);
    return s + extra;
  };
  const LX = 34, RX = W - 34 - 82;
  p.push(mini(LX + 6, 118, 'BPM', D.hr));
  const barW = 82 * D.stepPct / 100;
  p.push(mini(LX, 190, 'PAS', D.steps, aod ? '' :
    `<rect x="${LX}" y="236" width="82" height="4" rx="2" fill="${c.led}"/><rect x="${LX}" y="236" width="${n(barW)}" height="4" rx="2" fill="${c.accent}"/>`));
  if (!aod) p.push(mini(LX + 14, 266, 'KCAL', D.kcal));
  p.push(mini(RX - 6, 118, 'MÉTÉO', D.temp));
  p.push(mini(RX, 190, 'BATTERIE', D.batt));
  if (!aod) p.push(mini(RX - 14, 266, 'LEVER', D.sunrise));

  // Tableau des départs : prochain événement, une lettre par palette
  if (!aod) {
    const chars = [...D.board], cw = 15, ch = 24, gap = 2;
    let x = C - (chars.length * (cw + gap) - gap) / 2;
    const y = 330;
    for (const ch_ of chars) {
      p.push(ch_ === ' ' ? '' : tile(x, y, cw, ch, ch_, 17, /\d|:/.test(ch_) ? c.accent : digit));
      x += cw + gap;
    }
    p.push(`<text x="${C}" y="${y + ch + 18}" font-family="Barlow" font-weight="600" font-size="12" letter-spacing="2.4" fill="${soft}" text-anchor="middle">PROCHAIN DÉPART</text>`);
  }

  const style = `<style>
    @font-face { font-family: Barlow; font-weight: 500; src: url('${fontUrl('barlow-condensed-latin-500-normal.woff2')}'); }
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
for (const [name, c] of Object.entries(COLORWAYS)) {
  const out = join(here, `palettes-${name}.png`);
  await render(face(c), out);
  outs.push(out);
}
await render(face(COLORWAYS.gare, true), join(here, 'palettes-aod.png'));
await browser.close();

execFileSync('convert', [...outs, join(here, 'palettes-aod.png'), '-background', '#1E1F22',
  '-splice', '24x0', '+append', '-chop', '24x0', join(here, 'planche.png')]);
const skin = join(here, '..', '..', 'race', 'emulator', 'skin-galaxy-watch8-classic', 'background.png');
if (existsSync(skin)) {
  execFileSync('convert', [skin, outs[0], '-geometry', '+101+191', '-composite', join(here, 'palettes-montre.png')]);
  console.log(join(here, 'palettes-montre.png'));
}
