// Maquettes explicatives : tuile Santé Sync, écran de l'appli montre (actuel / Compose),
// second cadran. Dessin original ; valeurs fictives.
//
//   node concepts/surfaces/render.mjs   →  concepts/surfaces/planche.png
import { chromium } from 'playwright';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { writeFileSync, unlinkSync } from 'node:fs';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..', '..');
const url = (p) => pathToFileURL(join(root, p)).href;
const font = (f) => url(`concepts/strate/fonts/${f}`);

const L = { bg: '#0A1729', b1: '#0E4756', b2: '#2A9BA6', ink: '#DDEFF0', acc: '#7FE3EC', soft: '#8FB3B8' };
const S = 300; // diamètre d'un écran sur la planche

// Arc de progression (0-1) autour du centre, départ à midi.
function ring(cx, cy, r, p, w, color, track) {
  const a = Math.min(p, 0.999) * 2 * Math.PI;
  const x = cx + r * Math.sin(a), y = cy - r * Math.cos(a);
  return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${track}" stroke-width="${w}"/>
    <path d="M${cx} ${cy - r} A${r} ${r} 0 ${p > 0.5 ? 1 : 0} 1 ${x} ${y}" fill="none" stroke="${color}" stroke-width="${w}" stroke-linecap="round"/>`;
}

// ---- Tuile : surface plein écran, mise en page fixe (titre, contenu, bouton) ----
const tile = `<svg viewBox="0 0 438 438" width="${S}" height="${S}">
  <circle cx="219" cy="219" r="219" fill="${L.bg}"/>
  <text x="219" y="62" class="lab" fill="${L.acc}" text-anchor="middle" font-size="20">AUJOURD'HUI · 10:09</text>
  ${ring(219, 158, 72, 0.82, 14, L.acc, L.b1)}
  <text x="219" y="172" class="big" fill="${L.ink}" text-anchor="middle" font-size="64">82</text>
  <text x="219" y="200" class="lab" fill="${L.soft}" text-anchor="middle" font-size="17">ÉNERGIE</text>
  <g class="lab" font-size="16" fill="${L.soft}" text-anchor="middle">
    <text x="110" y="268">SOMMEIL</text><text x="219" y="268">PAS</text><text x="328" y="268">DISTANCE</text>
  </g>
  <g class="val" font-size="36" fill="${L.ink}" text-anchor="middle">
    <text x="110" y="305">6h29</text><text x="219" y="305">7 412</text><text x="328" y="305">5,3<tspan font-size="20"> km</tspan></text>
  </g>
  <g class="lab" font-size="16" fill="${L.acc}" text-anchor="middle">
    <text x="110" y="328">score 78</text><text x="328" y="328">412 kcal</text>
  </g>
  <rect x="179" y="316" width="80" height="7" rx="3.5" fill="${L.b1}"/><rect x="179" y="316" width="59" height="7" rx="3.5" fill="${L.acc}"/>
  <rect x="139" y="352" width="160" height="48" rx="24" fill="${L.b2}"/>
  <text x="219" y="384" class="val" font-size="22" fill="${L.bg}" text-anchor="middle">Actualiser</text>
</svg>`;

// ---- Écran actuel : un TextView brut ----
const current = `<div class="screen" style="background:#000">
  <div style="padding:46px 34px 0;color:#fff;font:13px/1.45 Roboto,Arial,sans-serif;text-align:center">
  Santé Sync<br>Téléphone : reçu à 08:12<br>Montre : pas, distance, calories, étages en direct<br><br>
  Score d'énergie : 82<br>Score de sommeil : 78<br>Durée de sommeil : 6h29<br>Pas : 7412<br>
  Objectif de pas : 10000<br>Distance : 5,3 km<br>Calories actives : 412<br>Étages : 6<br>
  Fréquence cardiaque repos : 58<br>Eau : 1,2 L<br>Poids : 78,4 kg</div></div>`;

// ---- Écran Compose for Wear OS : liste qui se réduit sur les bords ----
const card = (label, value, sub, p, scale, op) => `
  <div class="card" style="transform:scale(${scale});opacity:${op}">
    <div class="lab" style="color:${L.soft};font-size:13px">${label}</div>
    <div class="val" style="color:${L.ink};font-size:28px;line-height:1">${value}
      <span class="lab" style="font-size:13px;color:${L.acc}">${sub}</span></div>
    ${p == null ? '' : `<div class="bar"><i style="width:${p * 100}%"></i></div>`}
  </div>`;
const compose = `<div class="screen" style="background:#05090F">
  <div class="lab" style="position:absolute;top:12px;width:100%;text-align:center;color:#fff;font-size:15px">10:09</div>
  <div style="position:absolute;top:36px;width:100%;display:flex;flex-direction:column;align-items:center;gap:7px">
    <div class="val" style="color:${L.acc};font-size:19px;margin-bottom:2px">Santé Sync</div>
    ${card('ÉNERGIE', '82', '/ 100', 0.82, 0.96, 1)}
    ${card('SOMMEIL', '6h29', 'score 78', null, 1, 1)}
    ${card('PAS', '7 412', '/ 10 000', 0.74, 0.94, 1)}
    ${card('DISTANCE', '5,3 km', '412 kcal', null, 0.82, 0.55)}
  </div>
  <svg width="${S}" height="${S}" style="position:absolute;inset:0">
    <path d="M${S - 10} ${S / 2 - 40} A${S / 2 - 10} ${S / 2 - 10} 0 0 1 ${S - 10} ${S / 2 + 40}" fill="none" stroke="#333" stroke-width="4" stroke-linecap="round"/>
    <path d="M${S - 10} ${S / 2 - 40} A${S / 2 - 10} ${S / 2 - 10} 0 0 1 ${S - 13} ${S / 2 - 8}" fill="none" stroke="#ddd" stroke-width="4" stroke-linecap="round"/>
  </svg></div>`;

const img = (p) => `<img class="screen" src="${url(p)}">`;
const arrow = (t) => `<div class="arrow"><div>${t}</div><span>→</span></div>`;

const row = (n, title, why, screens) => `
  <section><div class="txt"><div class="num">${n}</div><h2>${title}</h2>${why}</div>
  <div class="screens">${screens}</div></section>`;

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Barlow;font-weight:500;src:url(${font('barlow-condensed-latin-500-normal.woff2')})}
@font-face{font-family:Barlow;font-weight:600;src:url(${font('barlow-condensed-latin-600-normal.woff2')})}
body{margin:0;background:#EEF1F3;font-family:Barlow,sans-serif;color:#16222B;width:1500px}
h1{margin:0;padding:34px 48px 6px;font-size:40px;font-weight:600}
.sub{padding:0 48px 18px;font-size:21px;color:#55636E;font-weight:500}
section{display:flex;align-items:center;gap:36px;margin:0 32px 22px;padding:26px 30px;background:#fff;border-radius:22px}
.txt{width:440px;font-size:19px;line-height:1.35;font-weight:500;color:#33424D}
.txt h2{margin:4px 0 10px;font-size:29px;color:#16222B;font-weight:600}
.txt b{color:#16222B;font-weight:600}
.num{display:inline-block;background:#0E4756;color:#fff;border-radius:50%;width:38px;height:38px;text-align:center;line-height:38px;font-size:22px;font-weight:600}
.screens{display:flex;align-items:center;gap:40px;flex:1;justify-content:center}
.shot{display:flex;flex-direction:column;align-items:center;gap:10px;font-size:18px;font-weight:600;color:#55636E}
.screen{position:relative;width:${S}px;height:${S}px;border-radius:50%;overflow:hidden;display:block;
  box-shadow:0 0 0 12px #2B2F33,0 0 0 15px #6C7278,0 10px 24px 14px rgba(0,0,0,.25)}
.arrow{display:flex;flex-direction:column;align-items:center;color:#55636E;font-size:16px;font-weight:600;text-align:center;width:110px}
.arrow span{font-size:44px;line-height:1;color:#0E4756}
.lab{font-family:Barlow;font-weight:500;letter-spacing:.04em}
.val,.big{font-family:Barlow;font-weight:600}
.card{width:230px;box-sizing:border-box;padding:9px 16px 10px;background:#13232E;border-radius:22px;transform-origin:center}
.bar{height:6px;border-radius:3px;background:${L.b1};margin-top:6px}.bar i{display:block;height:6px;border-radius:3px;background:${L.acc}}
</style></head><body>
<h1>Trois idées pour la suite</h1>
<div class="sub">Maquettes : valeurs fictives, palette Lagune. Rien n'est codé.</div>
${row(1, 'Tuile Santé Sync',
  `Depuis le cadran, <b>on glisse vers la gauche</b> : un écran plein dédié à la santé du jour.
   <br><br>Le cadran n'a que 2 dômes pour les données ; la tuile montre <b>tout en grand d'un coup d'œil</b>
   (énergie, sommeil, pas, distance), sans ouvrir d'appli.<br><br>Elle se met à jour toute seule avec les
   données que Santé Sync reçoit déjà. Ça se code en Kotlin dans l'appli montre existante.`,
  `<div class="shot">${img('prisme/docs/lagune.png')}Cadran Prisme</div>${arrow('glisser vers la gauche')}
   <div class="shot"><div class="screen">${tile}</div>Tuile Santé Sync</div>`)}
${row(2, "Écran de l'appli montre",
  `Aujourd'hui, l'icône Santé Sync ouvre <b>un texte brut</b> : petit, coupé par le bord rond, sans hiérarchie.
   <br><br>En <b>Compose for Wear OS</b> (la boîte à outils de Google pour montres) : des cartes lisibles,
   une liste qui <b>défile avec la lunette tournante</b> et rétrécit sur les bords, l'heure en haut.
   <br><br>Utile, mais moins prioritaire : on ouvre rarement cet écran.`,
  `<div class="shot">${current}Actuel</div>${arrow('refonte')}<div class="shot">${compose}Compose for Wear OS</div>`)}
${row(3, 'Un second cadran',
  `Les maquettes <b>Méridien</b> (style horloger, aiguilles, textures carbone, bambou, soleillé…) et
   <b>Strate</b> (numérique, gros chiffres sur deux lignes) existent déjà.<br><br>Le générateur Python et les
   règles apprises sur Prisme (contour, emplacements, toucher, AOD) se réutilisent : <b>beaucoup plus rapide</b>
   que Prisme. Ce serait un cadran de plus à choisir sur la montre, voire à publier.`,
  `<div class="shot">${img('concepts/meridien/meridien-anthracite-orange.png')}Méridien</div>
   <div class="shot">${img('concepts/strate/strate-glacier.png')}Strate</div>`)}
</body></html>`;

const tmp = join(here, '_planche.html');
writeFileSync(tmp, html);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1500, height: 800 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(tmp).href);
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: join(here, 'planche.png'), fullPage: true });
await browser.close();
unlinkSync(tmp);
