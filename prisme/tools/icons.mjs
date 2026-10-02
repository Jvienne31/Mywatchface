// Pictogrammes blancs de Prisme (recolorés sur la montre par tintColor), rendus avec Chromium.
//
//   node prisme/tools/icons.mjs   ->  src/main/res/drawable-nodpi/ic_*.png  (96 x 96)
//
// Dessin sur une grille 24 x 24 centrée en (12, 12), comme les maquettes de concepts/prisme.
import { chromium } from 'playwright';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, '..', 'src', 'main', 'res', 'drawable-nodpi');
const S = 'fill="none" stroke="#fff" stroke-linecap="round" stroke-linejoin="round"';

const rays = (cx, cy, r1, r2, n = 8, a0 = 0, w = 1.9) =>
  Array.from({ length: n }, (_, i) => {
    const a = ((a0 + (360 / n) * i) * Math.PI) / 180;
    return `<line x1="${cx + r1 * Math.sin(a)}" y1="${cy - r1 * Math.cos(a)}" x2="${cx + r2 * Math.sin(a)}" y2="${cy - r2 * Math.cos(a)}" ${S} stroke-width="${w}"/>`;
  }).join('');
const cloud = (dx = 0, dy = 0, k = 1) =>
  `<path transform="translate(${dx} ${dy}) scale(${k})" d="M7 18.5h10.5a4 4 0 0 0 .4-8 5.6 5.6 0 0 0-10.8 1.4A3.3 3.3 0 0 0 7 18.5z" fill="#fff"/>`;

const ICONS = {
  heart: '<path d="M12 21C5 16 2.5 12.3 2.5 8.6 2.5 5.6 4.8 3.5 7.5 3.5c1.9 0 3.4 1 4.5 2.6 1.1-1.6 2.6-2.6 4.5-2.6 2.7 0 5 2.1 5 5.1 0 3.7-2.5 7.4-9.5 12.4z" fill="#fff"/>',
  drop: '<path d="M12 2.5C16.5 8 18.5 11.5 18.5 14.5a6.5 6.5 0 0 1-13 0C5.5 11.5 7.5 8 12 2.5z" fill="#fff"/>',
  uv: `<circle cx="12" cy="12" r="4.6" ${S} stroke-width="2.2"/>` + rays(12, 12, 8, 10.8, 8, 0, 2),
  sun: '<circle cx="12" cy="12" r="5" fill="#fff"/>' + rays(12, 12, 7.6, 10.6, 8, 0, 2),
  partly: '<circle cx="9" cy="8.5" r="3.8" fill="#fff"/>' + rays(9, 8.5, 5.6, 7.6, 8, 0, 1.6) +
    '<path d="M6 21h11.5a4 4 0 0 0 .5-8 5.6 5.6 0 0 0-10.8 1.5A3.3 3.3 0 0 0 6 21z" fill="#000"/>' + cloud(0.4, 2, 1),
  cloud: cloud(-0.5, -2, 1.05),
  rain: cloud(0, -4.5, 1) + [7.5, 12, 16.5].map((x) => `<line x1="${x}" y1="17" x2="${x - 1.5}" y2="21.5" ${S} stroke-width="1.9"/>`).join(''),
  snow: cloud(0, -4.5, 1) + [7.5, 12, 16.5].map((x, i) => `<circle cx="${x}" cy="${18 + (i % 2) * 2.5}" r="1.4" fill="#fff"/>`).join(''),
  storm: cloud(0, -4.5, 1) + '<path d="M12.5 14.5 9.5 19h3l-1.5 4 4.5-5.5h-3l1.5-3z" fill="#fff"/>',
  fog: [7, 11.5, 16].map((y, i) => `<line x1="${4 + i}" y1="${y}" x2="${20 - (i % 2) * 2}" y2="${y}" ${S} stroke-width="2.2"/>`).join('') +
    '<line x1="6" y1="20.5" x2="15" y2="20.5" ' + S + ' stroke-width="2.2"/>',
  steps: [[-4.5, 2.5, -12], [4.5, -3.5, 12]].map(([dx, dy, rot]) =>
    `<g transform="rotate(${rot} ${12 + dx} ${12 + dy})"><ellipse cx="${12 + dx}" cy="${12 + dy - 2.5}" rx="3.6" ry="5.8" fill="#fff"/>` +
    `<ellipse cx="${12 + dx}" cy="${12 + dy + 5.6}" rx="2.7" ry="2.3" fill="#fff"/></g>`).join(''),
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 96, height: 96 } });
for (const [name, body] of Object.entries(ICONS)) {
  // « partly » : le soleil est masqué par une silhouette noire, rendue transparente ensuite
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 24 24">
    <defs><mask id="m"><rect width="24" height="24" fill="#fff"/>${name === 'partly' ? '<path d="M5 22h12.5a5 5 0 0 0 .5-10 6.6 6.6 0 0 0-12.6 1.5A4.3 4.3 0 0 0 5 22z" fill="#000"/>' : ''}</mask></defs>
    <g mask="url(#m)">${name === 'partly' ? ICONS.partly.split('<path')[0] : ''}</g>${name === 'partly' ? cloud(0.4, 2, 1) : body}</svg>`;
  await page.setContent(`<html><body style="margin:0;background:transparent">${svg}</body></html>`);
  await page.screenshot({ path: join(out, `ic_${name}.png`), omitBackground: true, clip: { x: 0, y: 0, width: 96, height: 96 } });
  console.log(`ic_${name}.png`);
}
await browser.close();
