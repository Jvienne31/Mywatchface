// Dessine le skin d'émulateur « Galaxy Watch8 Classic » (boîtier noir, lunette rotative
// graduée, deux boutons, cornes et bracelet) et le rend en PNG avec Chromium (Playwright).
//
//   node race/emulator/build-skin.mjs
//
// Produit dans skin-galaxy-watch8-classic/ :
//   background.png  le boîtier complet, écran noir (fond du skin)
//   mask.png        la partie du boîtier qui recouvre le rectangle de l'écran, trou rond
//                   au centre : l'émulateur la pose par-dessus l'affichage pour l'arrondir
// et skin-preview.png (le skin avec l'aperçu du cadran Race dedans, pour contrôle).
//
// Dessin original, inspiré des proportions de la montre ; aucune image Samsung.
import { chromium } from 'playwright';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { mkdirSync, writeFileSync } from 'node:fs';

const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, 'skin-galaxy-watch8-classic');
mkdirSync(out, { recursive: true });

// Géométrie : l'écran 438 x 438 est centré dans une image 640 x 820.
export const SKIN_W = 640, SKIN_H = 820;
const SKIN_BG = '#1E1F22';
const D = 438;                           // écran
const CX = SKIN_W / 2, CY = SKIN_H / 2;  // centre de l'écran
export const DISPLAY_X = CX - D / 2, DISPLAY_Y = CY - D / 2;
const R_SCREEN = D / 2;                  // 219
const R_GLASS = 230;                     // filet noir autour de l'écran
const R_BEZEL_IN = 236, R_BEZEL_OUT = 284;
const R_CASE = 300;

const fontUrl = pathToFileURL(join(here, '..', 'src', 'main', 'res', 'font', 'oswald_semibold.ttf')).href;

const polar = (r, a) => {
  const t = (a * Math.PI) / 180;
  return [CX + r * Math.sin(t), CY - r * Math.cos(t)];
};
const n = (v) => Math.round(v * 100) / 100;

function body() {
  // Fond uni (thème sombre d'Android Studio) : masque aussi les coins carrés de l'écran
  const parts = [`<rect width="${SKIN_W}" height="${SKIN_H}" fill="${SKIN_BG}"/>`];
  // Bracelet (cuir noir, coutures)
  for (const [y0, y1] of [[0, 190], [630, SKIN_H]]) {
    parts.push(`<rect x="${CX - 118}" y="${y0}" width="236" height="${y1 - y0}" rx="18" fill="url(#strap)"/>`);
    for (const dx of [-100, 100]) {
      parts.push(`<line x1="${CX + dx}" y1="${y0 + 10}" x2="${CX + dx}" y2="${y1 - 10}" stroke="#4a4d52" stroke-width="2" stroke-dasharray="7 6"/>`);
    }
  }
  // Cornes : trapèzes entre le boîtier et le bracelet
  parts.push(`<path d="M ${CX - 150} 230 L ${CX - 128} 150 L ${CX + 128} 150 L ${CX + 150} 230 Z" fill="url(#metal)"/>`);
  parts.push(`<path d="M ${CX - 150} ${SKIN_H - 230} L ${CX - 128} ${SKIN_H - 150} L ${CX + 128} ${SKIN_H - 150} L ${CX + 150} ${SKIN_H - 230} Z" fill="url(#metal)"/>`);
  // Boutons à droite (2 h et 4 h)
  for (const a of [62, 118]) {
    const [bx, by] = polar(R_CASE - 4, a);
    parts.push(`<rect x="${n(bx - 6)}" y="${n(by - 26)}" width="34" height="52" rx="12" fill="url(#button)" stroke="#0c0d0f" stroke-width="2"/>`);
  }
  // Boîtier
  parts.push(`<circle cx="${CX}" cy="${CY}" r="${R_CASE}" fill="url(#case)"/>`);
  parts.push(`<circle cx="${CX}" cy="${CY}" r="${R_CASE - 1.5}" fill="none" stroke="#5b6068" stroke-width="1.5" opacity="0.6"/>`);
  // Lunette rotative : anneau noir, bord moleté
  parts.push(`<circle cx="${CX}" cy="${CY}" r="${(R_BEZEL_IN + R_BEZEL_OUT) / 2}" fill="none" stroke="#141518" stroke-width="${R_BEZEL_OUT - R_BEZEL_IN}"/>`);
  const knurl = [];
  for (let i = 0; i < 180; i++) {
    const a = i * 2;
    const [x1, y1] = polar(R_BEZEL_OUT - 7, a);
    const [x2, y2] = polar(R_BEZEL_OUT + 1, a);
    knurl.push(`<line x1="${n(x1)}" y1="${n(y1)}" x2="${n(x2)}" y2="${n(y2)}"/>`);
  }
  parts.push(`<g stroke="#34373c" stroke-width="1.6">${knurl.join('')}</g>`);
  parts.push(`<circle cx="${CX}" cy="${CY}" r="${R_BEZEL_OUT - 8}" fill="none" stroke="#2a2d31" stroke-width="1"/>`);
  // Graduations : points chaque minute, chiffres toutes les 5 (00 = double barre)
  const marks = [];
  for (let m = 0; m < 60; m++) {
    const a = m * 6;
    if (m % 5 !== 0) {
      const [x, y] = polar(R_BEZEL_IN + 21, a);
      marks.push(`<circle cx="${n(x)}" cy="${n(y)}" r="1.6" fill="#8c9096"/>`);
    } else if (m === 0) {
      for (const da of [-1.3, 1.3]) {
        const [x1, y1] = polar(R_BEZEL_IN + 12, a + da);
        const [x2, y2] = polar(R_BEZEL_IN + 32, a + da);
        marks.push(`<line x1="${n(x1)}" y1="${n(y1)}" x2="${n(x2)}" y2="${n(y2)}" stroke="#d6d9dd" stroke-width="3"/>`);
      }
    } else {
      const [x, y] = polar(R_BEZEL_IN + 22, a);
      marks.push(`<text x="${n(x)}" y="${n(y)}" transform="rotate(${a} ${n(x)} ${n(y)})" font-family="Oswald" font-size="17" fill="#b9bdc2" text-anchor="middle" dominant-baseline="central">${String(m).padStart(2, '0')}</text>`);
    }
  }
  parts.push(marks.join(''));
  // Verre / filet noir autour de l'écran
  parts.push(`<circle cx="${CX}" cy="${CY}" r="${R_BEZEL_IN}" fill="#050506"/>`);
  parts.push(`<circle cx="${CX}" cy="${CY}" r="${R_GLASS}" fill="none" stroke="#1d1f22" stroke-width="1.2"/>`);
  return parts.join('\n');
}

const defs = `
<defs>
  <radialGradient id="case" cx="${CX - 90}" cy="${CY - 110}" r="420" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#4a4e55"/><stop offset="0.55" stop-color="#25282c"/><stop offset="1" stop-color="#0f1012"/>
  </radialGradient>
  <linearGradient id="metal" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#1a1c1f"/><stop offset="0.5" stop-color="#3b3f45"/><stop offset="1" stop-color="#16181a"/>
  </linearGradient>
  <linearGradient id="button" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#1b1d20"/><stop offset="0.6" stop-color="#4b5058"/><stop offset="1" stop-color="#202226"/>
  </linearGradient>
  <linearGradient id="strap" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#0c0d0e"/><stop offset="0.5" stop-color="#1c1d20"/><stop offset="1" stop-color="#0c0d0e"/>
  </linearGradient>
  <mask id="hole">
    <rect width="${SKIN_W}" height="${SKIN_H}" fill="white"/>
    <circle cx="${CX}" cy="${CY}" r="${R_SCREEN}" fill="black"/>
  </mask>
</defs>`;

const style = `<style>@font-face { font-family: Oswald; src: url('${fontUrl}'); }</style>`;
const svg = (inner, w = SKIN_W, h = SKIN_H, vb = `0 0 ${SKIN_W} ${SKIN_H}`) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="${vb}">${style}${defs}${inner}</svg>`;

const BODY = body();
const screenBlack = `<circle cx="${CX}" cy="${CY}" r="${R_SCREEN}" fill="#000"/>`;
const facePng = pathToFileURL(join(here, '..', 'src', 'main', 'res', 'drawable-nodpi', 'preview.png')).href;

const jobs = [
  ['background.png', svg(BODY + screenBlack), SKIN_W, SKIN_H],
  // Masque : uniquement le rectangle de l'écran, trou rond transparent au centre
  ['mask.png', svg(`<g mask="url(#hole)">${BODY}</g>`, D, D, `${DISPLAY_X} ${DISPLAY_Y} ${D} ${D}`), D, D],
  ['../skin-preview.png', svg(BODY + screenBlack +
    `<image x="${DISPLAY_X}" y="${DISPLAY_Y}" width="${D}" height="${D}" href="${facePng}"/>`), SKIN_W, SKIN_H],
];

const browser = await chromium.launch();
for (const [name, content, w, h] of jobs) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  const tmp = join(out, '_tmp.svg');
  writeFileSync(tmp, content);
  await page.goto(pathToFileURL(tmp).href);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: join(out, name), omitBackground: true });
  await page.close();
  console.log(join(out, name));
}
await browser.close();
(await import('node:fs')).unlinkSync(join(out, '_tmp.svg'));
