// Icônes des options de réglage (Secondes, Dôme gauche) : l'éditeur Samsung n'affiche que
// l'icône d'une option (sans icône : un rond vide). Disque sombre + dessin cyan, lisible sur
// fond clair (téléphone) comme sombre (montre).
//
//   node prisme/tools/option-icons.mjs   →  src/main/res/drawable-nodpi/opt_*.png
import { chromium } from 'playwright';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { writeFileSync, unlinkSync } from 'node:fs';

const here = dirname(fileURLToPath(import.meta.url));
const res = join(here, '..', 'src', 'main', 'res');
const font = pathToFileURL(join(res, 'font', 'barlowcondensed_semibold.ttf')).href;
const BG = '#0A1729', TRACK = '#1E4A57', ACC = '#7FE3EC', INK = '#DDEFF0', S = 96, C = 48;

const arc = (r, a0, a1, col, w) => {
  const p = (a) => [C + r * Math.sin((a * Math.PI) / 180), C - r * Math.cos((a * Math.PI) / 180)];
  const [x0, y0] = p(a0), [x1, y1] = p(a1);
  return `<path d="M${x0} ${y0} A${r} ${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1} ${y1}" fill="none"
    stroke="${col}" stroke-width="${w}" stroke-linecap="round"/>`;
};
const ring = `<circle cx="${C}" cy="${C}" r="30" fill="none" stroke="${TRACK}" stroke-width="7"/>`;
const t = (y, s, txt, col = INK) =>
  `<text x="${C}" y="${y}" font-size="${s}" fill="${col}" text-anchor="middle" font-family="B">${txt}</text>`;
const sun = (cx, cy) => `<circle cx="${cx}" cy="${cy}" r="5" fill="${ACC}"/>` +
  [0, 45, 90, 135, 180, 225, 270, 315].map((a) => {
    const r = (a * Math.PI) / 180;
    return `<line x1="${cx + 8 * Math.sin(r)}" y1="${cy - 8 * Math.cos(r)}" x2="${cx + 11 * Math.sin(r)}"
      y2="${cy - 11 * Math.cos(r)}" stroke="${ACC}" stroke-width="2.5" stroke-linecap="round"/>`;
  }).join('');

const ICONS = {
  opt_sec_arc: ring + arc(30, 0, 250, ACC, 7),
  opt_sec_dot: ring + `<circle cx="${C + 30 * Math.sin(1.1)}" cy="${C - 30 * Math.cos(1.1)}" r="8" fill="${ACC}"/>`,
  opt_sec_none: ring + `<line x1="34" y1="62" x2="62" y2="34" stroke="${INK}" stroke-width="5" stroke-linecap="round"/>`,
  opt_dg_uv: sun(C, 31) + t(70, 30, 'UV'),
  opt_dg_maxmin: t(47, 28, '21°') + t(74, 22, '12°', ACC),
  opt_dg_1h: t(46, 22, 'DANS', ACC) + t(76, 32, '1 h'),
  opt_dg_3h: t(46, 22, 'DANS', ACC) + t(76, 32, '3 h'),
};

const tmp = join(here, '_icons.html');
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: S, height: S } });
for (const [name, body] of Object.entries(ICONS)) {
  writeFileSync(tmp, `<!doctype html><html><head><style>@font-face{font-family:B;src:url(${font})}
    body{margin:0;background:transparent}</style></head><body>
    <svg width="${S}" height="${S}" viewBox="0 0 ${S} ${S}"><circle cx="${C}" cy="${C}" r="${C}" fill="${BG}"/>${body}</svg>
    </body></html>`);
  await page.goto(pathToFileURL(tmp).href);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: join(res, 'drawable-nodpi', `${name}.png`), omitBackground: true });
}
await browser.close();
unlinkSync(tmp);
console.log(Object.keys(ICONS).join(' '));
