// Maquette : la tuile « Santé du jour » actuelle et trois variantes Material 3 Expressive
// (modèles « Golden Tiles » de Google : titre + pastilles arrondies + bouton de bord), palette
// Lagune. Valeurs fictives.
//
//   node concepts/surfaces/tuiles-m3.mjs   →  concepts/surfaces/tuiles-m3.png
import { chromium } from 'playwright';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { writeFileSync, unlinkSync } from 'node:fs';

const here = dirname(fileURLToPath(import.meta.url));
const font = (f) => pathToFileURL(join(here, '..', 'strate', 'fonts', f)).href;
const L = { bg: '#0A1729', card: '#13323C', card2: '#1B4450', track: '#0E4756', b2: '#2A9BA6',
  ink: '#DDEFF0', acc: '#7FE3EC', soft: '#8FB3B8', onAcc: '#06222A' };
const S = 300, W = 438, C = 219;

const t = (x, y, s, txt, { size = 20, fill = L.ink, w = 600, anchor = 'middle', ls = 0 } = {}) =>
  `<text x="${x}" y="${y}" font-size="${size}" fill="${fill}" font-weight="${w}" text-anchor="${anchor}"
     letter-spacing="${ls}" font-family="Barlow">${txt}</text>`;
const pill = (x, y, w, h, r, fill) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}"/>`;
const ring = (cx, cy, r, p, th, col, track) => {
  const a = Math.min(p, 0.999) * 2 * Math.PI;
  return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${track}" stroke-width="${th}"/>
    <path d="M${cx} ${cy - r} A${r} ${r} 0 ${p > 0.5 ? 1 : 0} 1 ${cx + r * Math.sin(a)} ${cy - r * Math.cos(a)}"
      fill="none" stroke="${col}" stroke-width="${th}" stroke-linecap="round"/>`;
};
const bolt = (cx, cy, s, col) =>
  `<path transform="translate(${cx - s / 2} ${cy - s / 2}) scale(${s / 24})" fill="${col}"
     d="M13 2 4 14h6l-1 8 9-12h-6z"/>`;
// Bouton de bord : haut arrondi, bas qui suit le cercle de l'écran (comme EdgeButton)
const edge = (label) => {
  const y0 = 352, x0 = 129, x1 = 309, r = 205;
  const yb = (x) => C + Math.sqrt(r * r - (x - C) ** 2);
  return `<path d="M${x0} ${y0 + 24} A24 24 0 0 1 ${x0 + 24} ${y0} L${x1 - 24} ${y0} A24 24 0 0 1 ${x1} ${y0 + 24}
      L${x1} ${yb(x1)} A${r} ${r} 0 0 1 ${x0} ${yb(x0)} Z" fill="${L.acc}"/>
    ${t(C, 392, 0, label, { size: 22, fill: L.onAcc })}`;
};
const head = (title) => `${bolt(C, 46, 22, L.acc)}${t(C, 82, 0, title, { size: 20, fill: L.ink, w: 500 })}`;
const face = (body) => `<svg viewBox="0 0 ${W} ${W}" width="${S}" height="${S}">
  <circle cx="${C}" cy="${C}" r="${C}" fill="${L.bg}"/>${body}</svg>`;

// --- Actuelle (codée aujourd'hui) ---
const actuelle = face(`
  ${t(C, 62, 0, 'MAJ 08:12', { size: 20, fill: L.acc, w: 500, ls: 1 })}
  ${ring(C, 158, 72, 0.82, 14, L.acc, L.track)}
  ${t(C, 172, 0, '82', { size: 62 })}${t(C, 200, 0, 'ÉNERGIE', { size: 17, fill: L.soft, w: 500 })}
  ${t(110, 268, 0, 'SOMMEIL', { size: 16, fill: L.soft, w: 500 })}${t(219, 268, 0, 'PAS', { size: 16, fill: L.soft, w: 500 })}
  ${t(328, 268, 0, 'DISTANCE', { size: 16, fill: L.soft, w: 500 })}
  ${t(110, 305, 0, '6h29', { size: 36 })}${t(219, 305, 0, '7 412', { size: 36 })}${t(328, 305, 0, '5,3 km', { size: 32 })}
  ${t(110, 328, 0, 'score 78', { size: 16, fill: L.acc, w: 500 })}${t(328, 328, 0, '412 kcal', { size: 16, fill: L.acc, w: 500 })}
  ${pill(179, 316, 80, 7, 3.5, L.track)}${pill(179, 316, 59, 7, 3.5, L.acc)}
  ${pill(139, 352, 160, 48, 24, L.b2)}${t(C, 384, 0, 'Détails', { size: 22, fill: L.bg })}`);

// --- A « Deux scores » (modèle Latest run) : deux grandes pastilles côte à côte ---
const a = face(`${head('Santé du jour')}
  ${pill(78, 104, 138, 160, 52, L.card)}${pill(222, 104, 138, 160, 52, L.card)}
  ${t(147, 150, 0, 'Énergie', { size: 21, fill: L.soft, w: 500 })}${t(291, 150, 0, 'Sommeil', { size: 21, fill: L.soft, w: 500 })}
  ${t(147, 210, 0, '82', { size: 64 })}${t(291, 210, 0, '78', { size: 64 })}
  ${t(147, 240, 0, 'sur 100', { size: 18, fill: L.acc, w: 500 })}${t(291, 240, 0, '6 h 29', { size: 18, fill: L.acc, w: 500 })}
  ${t(C, 300, 0, '7 412 pas · 5,3 km', { size: 22, fill: L.ink, w: 500 })}
  ${pill(139, 312, 160, 8, 4, L.track)}${pill(139, 312, 118, 8, 4, L.acc)}
  ${edge('Détails')}`);

// --- B « Objectif » (modèle Steps) : grande pastille anneau + trois mini-pastilles ---
const b = face(`${head('Énergie')}
  ${pill(62, 100, 314, 118, 59, L.card)}
  ${t(96, 160, 0, '82', { size: 70, anchor: 'start' })}${t(98, 194, 0, 'sur 100 · en forme', { size: 19, fill: L.acc, w: 500, anchor: 'start' })}
  ${ring(318, 159, 38, 0.82, 11, L.acc, L.track)}${bolt(318, 159, 26, L.acc)}
  ${pill(62, 228, 100, 108, 34, L.card2)}${pill(169, 228, 100, 108, 34, L.card2)}${pill(276, 228, 100, 108, 34, L.card2)}
  ${t(112, 262, 0, 'Sommeil', { size: 16, fill: L.soft, w: 500 })}${t(219, 262, 0, 'Pas', { size: 16, fill: L.soft, w: 500 })}${t(326, 262, 0, 'Distance', { size: 16, fill: L.soft, w: 500 })}
  ${t(112, 298, 0, '6h29', { size: 30 })}${t(219, 298, 0, '7 412', { size: 30 })}${t(326, 298, 0, '5,3', { size: 30 })}
  ${t(112, 322, 0, 'score 78', { size: 15, fill: L.acc, w: 500 })}${t(219, 322, 0, '74 %', { size: 15, fill: L.acc, w: 500 })}${t(326, 322, 0, 'km', { size: 15, fill: L.acc, w: 500 })}
  ${edge('Détails')}`);

// --- C « Grille » (modèle Minutes) : quatre pastilles 2 × 2 avec anneaux ---
const cell = (x, y, label, value, sub, p) => `${pill(x, y, 150, 112, 46, L.card)}
  ${ring(x + 40, y + 56, 22, p, 7, L.acc, L.track)}
  ${t(x + 108, y + 46, 0, label, { size: 16, fill: L.soft, w: 500 })}
  ${t(x + 108, y + 82, 0, value, { size: 32 })}${t(x + 108, y + 102, 0, sub, { size: 14, fill: L.acc, w: 500 })}`;
const c = face(`${head('Santé du jour')}
  ${cell(66, 100, 'Énergie', '82', '/ 100', 0.82)}${cell(222, 100, 'Sommeil', '78', '6 h 29', 0.78)}
  ${cell(66, 220, 'Pas', '7,4k', '/ 10 000', 0.74)}${cell(222, 220, 'Distance', '5,3', 'km', 0.53)}
  ${edge('Détails')}`);

const shot = (svg, title, sub) => `<div class="shot"><div class="screen">${svg}</div>
  <b>${title}</b><span>${sub}</span></div>`;
const html = `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Barlow;font-weight:500;src:url(${font('barlow-condensed-latin-500-normal.woff2')})}
@font-face{font-family:Barlow;font-weight:600;src:url(${font('barlow-condensed-latin-600-normal.woff2')})}
body{margin:0;background:#EEF1F3;font-family:Barlow,sans-serif;color:#16222B;width:1500px}
h1{margin:0;padding:30px 44px 4px;font-size:38px;font-weight:600}
.sub{padding:0 44px 24px;font-size:20px;color:#55636E;font-weight:500}
.row{display:flex;justify-content:space-around;padding:0 20px 34px}
.shot{display:flex;flex-direction:column;align-items:center;gap:6px;width:330px;text-align:center}
.shot b{font-size:24px;margin-top:18px}.shot span{font-size:17px;color:#55636E;font-weight:500;line-height:1.3}
.screen{width:${S}px;height:${S}px;border-radius:50%;overflow:hidden;
  box-shadow:0 0 0 12px #2B2F33,0 0 0 15px #6C7278,0 10px 24px 14px rgba(0,0,0,.25)}
</style></head><body>
<h1>Tuile « Santé du jour » : vers Material 3 Expressive</h1>
<div class="sub">D'après les modèles officiels de Google (Golden Tiles). Palette Lagune, valeurs fictives.</div>
<div class="row">
${shot(actuelle, 'Actuelle', 'Anneau + 3 colonnes, bouton simple.<br>Textes petits, mise en page « maison ».')}
${shot(a, 'A · Deux scores', 'Énergie et sommeil en très grand<br>dans deux pastilles, pas et distance dessous.')}
${shot(b, 'B · Énergie d’abord', 'Grande pastille avec anneau,<br>trois mini-pastilles sommeil / pas / distance.')}
${shot(c, 'C · Grille', 'Quatre pastilles égales,<br>chacune avec son anneau de progression.')}
</div></body></html>`;

const tmp = join(here, '_tuiles.html');
writeFileSync(tmp, html);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1500, height: 600 } });
await page.goto(pathToFileURL(tmp).href);
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: join(here, 'tuiles-m3.png'), fullPage: true });
await browser.close();
unlinkSync(tmp);
