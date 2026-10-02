// Maquette « Strate » : cadran numérique, heures et minutes sur deux lignes, en très grands
// chiffres, encadrés de deux colonnes de données. Dessin original.
//
//   node concepts/strate/render.mjs
//
// Lisibilité (écran 438 px ≈ 34 mm) : chiffres de l'heure ~150 px de haut, valeurs 26-30 px,
// libellés >= 13 px, aucune graduation décorative.
//
//   centre        HH / MM (Big Shoulders Display), trait des secondes entre les deux lignes
//   colonne gauche  cardio, pas, calories            [HEART_RATE] [STEP_COUNT] complication
//   colonne droite  météo, batterie, lever du soleil [WEATHER.*] [BATTERY_PERCENT] complication
//   haut (courbe)   jour et date                     [DAY_OF_WEEK_F] [DAY] [MONTH_F]
//   bas (courbe)    prochain événement               complication LONG_TEXT
//   pourtour        anneau de progression des pas    [STEP_PERCENT]
import { chromium } from 'playwright';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { writeFileSync, unlinkSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

const here = dirname(fileURLToPath(import.meta.url));
const W = 438, C = W / 2;
const D = {
  hh: '10', mm: '09', s: 36, hr: 72, steps: '6 420', stepPct: 64, kcal: 412,
  temp: 18, batt: 68, sunrise: '07:42', date: 'VENDREDI 2 OCTOBRE', event: '14:30 · RÉUNION ÉQUIPE',
};

const COLORWAYS = {
  glacier: { bg: ['#14202B', '#080C10'], hh: '#F2F6FA', mm: '#3FD4F5', accent: '#3FD4F5', soft: '#8EA0B2', track: '#16303B' },
  ambre:   { bg: ['#24180F', '#0C0805'], hh: '#FBF4EC', mm: '#FF9A2E', accent: '#FF9A2E', soft: '#B09A86', track: '#3A2612' },
  lime:    { bg: ['#162016', '#070A07'], hh: '#F1F7EE', mm: '#B6F23A', accent: '#B6F23A', soft: '#97A891', track: '#27360F' },
};

const polar = (r, a, cx = C, cy = C) => {
  const t = (a * Math.PI) / 180;
  return [cx + r * Math.sin(t), cy - r * Math.cos(t)];
};
const n = (v) => Math.round(v * 100) / 100;
const fontUrl = (f) => pathToFileURL(join(here, 'fonts', f)).href;
const arcPath = (r, a0, a1, sweep = 1) => {
  const [x0, y0] = polar(r, a0), [x1, y1] = polar(r, a1);
  return `M ${n(x0)} ${n(y0)} A ${r} ${r} 0 ${Math.abs(a1 - a0) > 180 ? 1 : 0} ${sweep} ${n(x1)} ${n(y1)}`;
};

// Pictogrammes simples (traits épais, lisibles à 18 px)
const ICON = {
  heart: (x, y, c) => `<path d="M ${x} ${y + 7} C ${x - 12} ${y - 1} ${x - 7} ${y - 10} ${x} ${y - 4} C ${x + 7} ${y - 10} ${x + 12} ${y - 1} ${x} ${y + 7} Z" fill="${c}"/>`,
  steps: (x, y, c) => `<ellipse cx="${x - 4}" cy="${y - 1}" rx="3.6" ry="6" fill="${c}"/><ellipse cx="${x + 4.5}" cy="${y + 2}" rx="3.6" ry="6" fill="${c}"/>`,
  flame: (x, y, c) => `<path d="M ${x} ${y - 9} C ${x + 8} ${y - 2} ${x + 7} ${y + 8} ${x} ${y + 8} C ${x - 7} ${y + 8} ${x - 7} ${y} ${x - 2} ${y - 3} C ${x - 2} ${y + 1} ${x + 1} ${y + 2} ${x + 1} ${y - 1} C ${x + 1} ${y - 4} ${x - 1} ${y - 6} ${x} ${y - 9} Z" fill="${c}"/>`,
  sun: (x, y, c) => {
    let s = `<circle cx="${x}" cy="${y}" r="5" fill="${c}"/>`;
    for (let k = 0; k < 8; k++) { const [a, b] = polar(7.5, k * 45, x, y), [e, f] = polar(10, k * 45, x, y);
      s += `<line x1="${n(a)}" y1="${n(b)}" x2="${n(e)}" y2="${n(f)}" stroke="${c}" stroke-width="1.8" stroke-linecap="round"/>`; }
    return s;
  },
  batt: (x, y, c) => `<rect x="${x - 10}" y="${y - 5.5}" width="18" height="11" rx="2.5" fill="none" stroke="${c}" stroke-width="1.8"/>
    <rect x="${x + 8.5}" y="${y - 2.5}" width="2.5" height="5" rx="1" fill="${c}"/><rect x="${x - 7.5}" y="${y - 3}" width="${n(13 * D.batt / 100)}" height="6" rx="1" fill="${c}"/>`,
  sunrise: (x, y, c) => `<path d="M ${x - 8} ${y + 3} A 8 8 0 0 1 ${x + 8} ${y + 3}" fill="none" stroke="${c}" stroke-width="1.9"/>
    <line x1="${x - 11}" y1="${y + 6}" x2="${x + 11}" y2="${y + 6}" stroke="${c}" stroke-width="1.9" stroke-linecap="round"/>
    <path d="M ${x} ${y - 10} L ${x} ${y - 3} M ${x - 3} ${y - 7} L ${x} ${y - 10} L ${x + 3} ${y - 7}" fill="none" stroke="${c}" stroke-width="1.7" stroke-linecap="round"/>`,
};

function face(c, aod = false) {
  const p = [], defs = [];
  const val = aod ? '#C9D1D9' : c.hh;
  const soft = aod ? '#6F7882' : c.soft;
  const acc = c.accent;

  // Fond : dégradé sombre (en WFF : aplat + PNG d'ombrage, cf. Race) ; noir pur en AOD
  if (aod) p.push(`<rect width="${W}" height="${W}" fill="#000"/>`);
  else {
    defs.push(`<radialGradient id="bg" cx="${C}" cy="${C - 40}" r="${C + 40}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="${c.bg[0]}"/><stop offset="1" stop-color="${c.bg[1]}"/></radialGradient>`);
    p.push(`<rect width="${W}" height="${W}" fill="url(#bg)"/>`);
  }

  // Anneau des pas au bord + curseur
  const RA = C - 7;
  p.push(`<circle cx="${C}" cy="${C}" r="${RA}" fill="none" stroke="${aod ? '#15181b' : c.track}" stroke-width="7"/>`);
  p.push(`<path d="${arcPath(RA, 0, 360 * D.stepPct / 100)}" fill="none" stroke="${acc}" stroke-width="7" stroke-linecap="round"/>`);

  // Texte courbe : date en haut, événement en bas
  defs.push(`<path id="topArc" d="${arcPath(C - 30, -70, 70)}"/>`);
  defs.push(`<path id="botArc" d="${arcPath(C - 30, 250, 110, 0)}"/>`);   // sens antihoraire : lisible en bas
  p.push(`<text font-family="Barlow" font-weight="600" font-size="17" letter-spacing="2" fill="${aod ? soft : c.hh}">
    <textPath href="#topArc" startOffset="50%" text-anchor="middle">${D.date}</textPath></text>`);
  if (!aod) p.push(`<text font-family="Barlow" font-weight="500" font-size="16" letter-spacing="1.2" fill="${soft}" dominant-baseline="hanging">
    <textPath href="#botArc" startOffset="50%" text-anchor="middle"><tspan fill="${acc}">14:30</tspan> · RÉUNION ÉQUIPE</textPath></text>`);

  // HH / MM sur deux lignes
  const hhFill = aod ? '#D5DBE1' : c.hh, mmFill = aod ? acc : c.mm;
  p.push(`<text x="${C}" y="190" font-family="Shoulders" font-weight="${aod ? 300 : 800}" font-size="152" letter-spacing="-2" fill="${hhFill}" text-anchor="middle">${D.hh}</text>`);
  p.push(`<text x="${C}" y="334" font-family="Shoulders" font-weight="${aod ? 300 : 800}" font-size="152" letter-spacing="-2" fill="${mmFill}" text-anchor="middle">${D.mm}</text>`);
  // Trait des secondes entre les deux lignes (se remplit en une minute)
  if (!aod) {
    const x0 = C - 62, w = 124;
    p.push(`<rect x="${x0}" y="203" width="${w}" height="5" rx="2.5" fill="${c.track}"/>`);
    p.push(`<rect x="${x0}" y="203" width="${n(w * D.s / 60)}" height="5" rx="2.5" fill="${acc}"/>`);
    p.push(`<circle cx="${n(x0 + w * D.s / 60)}" cy="205.5" r="4.5" fill="${c.hh}"/>`);
  }

  // Colonnes de données : pictogramme, valeur, libellé
  const cell = (x, y, icon, value, label, unit = '') => {
    let s = ICON[icon](x, y - 30, aod ? soft : acc);
    s += `<text x="${x}" y="${y + 2}" font-family="Barlow" font-weight="600" font-size="29" fill="${val}" text-anchor="middle">${value}<tspan font-size="16" fill="${soft}">${unit}</tspan></text>`;
    s += `<text x="${x}" y="${y + 18}" font-family="Barlow" font-weight="500" font-size="13" letter-spacing="1.4" fill="${soft}" text-anchor="middle">${label}</text>`;
    return s;
  };
  const LX = 74, RX = W - 74;
  p.push(cell(LX, 150, 'heart', D.hr, 'BPM'));
  p.push(cell(LX + 2, 236, 'steps', D.steps, 'PAS'));
  if (!aod) p.push(cell(LX + 16, 318, 'flame', D.kcal, 'KCAL'));
  p.push(cell(RX, 150, 'sun', D.temp, 'MÉTÉO', '°'));
  p.push(cell(RX - 6, 236, 'batt', D.batt, 'BATTERIE', '%'));
  if (!aod) p.push(cell(RX - 16, 318, 'sunrise', D.sunrise, 'LEVER'));

  // Filets verticaux discrets entre colonnes et heure
  if (!aod) for (const x of [128, W - 128])
    p.push(`<line x1="${x}" y1="128" x2="${x}" y2="318" stroke="${soft}" stroke-opacity="0.25" stroke-width="1"/>`);

  const style = `<style>
    @font-face { font-family: Shoulders; font-weight: 800; src: url('${fontUrl('big-shoulders-display-latin-800-normal.woff2')}'); }
    @font-face { font-family: Shoulders; font-weight: 300; src: url('${fontUrl('big-shoulders-display-latin-300-normal.woff2')}'); }
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
  const out = join(here, `strate-${name}.png`);
  await render(face(c), out);
  outs.push(out);
}
await render(face(COLORWAYS.glacier, true), join(here, 'strate-aod.png'));
await browser.close();

execFileSync('convert', [...outs, join(here, 'strate-aod.png'), '-background', '#1E1F22',
  '-splice', '24x0', '+append', '-chop', '24x0', join(here, 'planche.png')]);
const skin = join(here, '..', '..', 'race', 'emulator', 'skin-galaxy-watch8-classic', 'background.png');
if (existsSync(skin)) {
  execFileSync('convert', [skin, outs[0], '-geometry', '+101+191', '-composite', join(here, 'strate-montre.png')]);
  console.log(join(here, 'strate-montre.png'));
}
