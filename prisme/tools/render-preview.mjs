// Rend les aperçus SVG produits par generate.py en PNG, avec Chromium (Playwright).
//
//   node prisme/tools/render-preview.mjs
//
// preview.svg          -> src/main/res/drawable-nodpi/preview.png (aperçu du paquet)
// preview_ambient.svg  -> tools/preview_ambient.png (contrôle de l'AOD, non embarqué)
import { chromium } from 'playwright';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const jobs = [
  ['preview.svg', join(here, '..', 'src', 'main', 'res', 'drawable-nodpi', 'preview.png')],
  ['preview_ambient.svg', join(here, 'preview_ambient.png')],
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 438, height: 438 } });
for (const [svg, png] of jobs) {
  await page.goto(pathToFileURL(join(here, svg)).href);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: png, omitBackground: true });
  console.log(png);
}
await browser.close();
