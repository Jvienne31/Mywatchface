// Prisme v2 : propositions après essai sur la montre (données trop petites, chiffres coupés
// en deux couleurs difficiles à lire). Illustration avant développement.
//
//   node concepts/prisme/v2.mjs   ->  concepts/prisme/v2-chiffres.png, v2-palettes.png
//
// Les contours se font en WFF en dessinant le chiffre 8 fois décalé dans la couleur du
// contour, puis par-dessus (l'élément Outline n'est pas rendu sur la montre).
import { chromium } from 'playwright';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { writeFileSync, unlinkSync } from 'node:fs';

const here = dirname(fileURLToPath(import.meta.url));
const W = 438, C = W / 2, ANGLE = 18, EDGES = [-400, 128, 206, 286, 900];
const fontUrl = (f) => pathToFileURL(join(here, '..', 'strate', 'fonts', f)).href;
const n = (v) => Math.round(v * 100) / 100;
const polar = (r, a, cx = C, cy = C) => [cx + r * Math.sin((a * Math.PI) / 180), cy - r * Math.cos((a * Math.PI) / 180)];

const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const mix = (a, b, k) => '#' + hex(a).map((v, i) => Math.round(v + (hex(b)[i] - v) * k).toString(16).padStart(2, '0')).join('');
const pal = (bands, accent) => ({ bands, accent, light: bands[3], dark: bands[0],
  ink: [bands[3], bands[3], bands[0], bands[0]], softD: mix(bands[3], bands[0], 0.38), softL: mix(bands[0], bands[3], 0.4) });
const PAL = {
  neon: pal(['#0B0B12', '#22224A', '#FF2E88', '#F4F4F8'], '#00E5FF'),
  lagune: pal(['#0A1729', '#0E4756', '#2A9BA6', '#DDEFF0'], '#7FE3EC'),
  cobalt: pal(['#0A1330', '#1E3A8A', '#4C7BF3', '#E4EAFB'], '#FFD23F'),
  volcan: pal(['#1C1A19', '#5E281B', '#C4562C', '#ECE0CB'], '#FF8A3D'),
};

// mode : 'actuel' | 'contour' (inversion + contour opposé) | 'uni' (clair + contour sombre)
// big : données agrandies
function face(c, mode, big = true) {
  const p = [], defs = [];
  const rot = `rotate(${ANGLE} ${C} ${C})`;
  for (let i = 0; i < 4; i++) {
    const x0 = EDGES[i], x1 = EDGES[i + 1];
    defs.push(`<clipPath id="b${i}"><rect x="${x0}" y="-300" width="${x1 - x0}" height="1100" transform="${rot}"/></clipPath>`);
    p.push(`<rect x="${x0}" y="-300" width="${x1 - x0}" height="1100" fill="${c.bands[i]}" transform="${rot}"/>`);
  }
  defs.push(`<linearGradient id="shade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity="0.22"/>
    <stop offset="0.25" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="0.05"/></linearGradient>`);
  for (let i = 1; i < 4; i++)
    p.push(`<rect x="${EDGES[i]}" y="-300" width="${EDGES[i + 1] - EDGES[i]}" height="1100" fill="url(#shade)" transform="${rot}"/>`);

  // Chiffres
  const glyph = (txt, cx, base, fill, stroke, sw) => // chiffres un peu réduits pour loger les données agrandies
   
    `<text transform="translate(${cx} ${base}) skewX(-12)" font-family="Shoulders" font-weight="800" font-size="${big ? 160 : 172}"
      letter-spacing="-4" text-anchor="middle" fill="${fill}"${stroke ? ` stroke="${stroke}" stroke-width="${sw}" stroke-linejoin="round" paint-order="stroke"` : ''}>${txt}</text>`;
  const digits = (txt, cx, base) => {
    if (mode === 'uni') {
      // ombre portée douce + contour sombre épais + chiffre clair, identique sur toutes les bandes
      defs.push(`<filter id="ds" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3"/></filter>`);
      return `<g opacity="0.45" filter="url(#ds)" transform="translate(3 5)">${glyph(txt, cx, base, '#000', '#000', 10)}</g>` +
        glyph(txt, cx, base, c.light, c.dark, 9);
    }
    let s = '';
    for (let i = 0; i < 4; i++) {
      const ink = c.ink[i], opp = ink === c.light ? c.dark : c.light;
      s += `<g clip-path="url(#b${i})">${mode === 'contour' ? glyph(txt, cx, base, ink, opp, 7) : glyph(txt, cx, base, ink)}</g>`;
    }
    return s;
  };
  p.push(digits('23', big ? C - 22 : C - 30, big ? 186 : 192));
  p.push(digits('54', big ? C + 24 : C + 34, big ? 324 : 334));

  // Secondes
  { const r = C - 5, a = 36 * 6, [x0, y0] = polar(r, 0), [x1, y1] = polar(r, a);
    p.push(`<path d="M ${n(x0)} ${n(y0)} A ${r} ${r} 0 1 1 ${n(x1)} ${n(y1)}" fill="none" stroke="${c.accent}" stroke-width="4" stroke-linecap="round"/>`); }

  const k = big ? 1 : 0;   // big : nouvelles tailles ; sinon tailles actuelles
  const t = (x, y, size, fill, txt, extra = '', anchor = 'middle') =>
    `<text x="${n(x)}" y="${n(y)}" font-family="Barlow" font-weight="600" font-size="${size}" fill="${fill}" text-anchor="${anchor}" ${extra}>${txt}</text>`;
  const L = c.light, Dk = c.dark;
  const ICON = {
    sun: (x, y, s, col) => `<circle cx="${x}" cy="${y}" r="${n(s * 0.22)}" fill="${col}"/>` + [0, 45, 90, 135, 180, 225, 270, 315].map((a) => {
      const [a1, b1] = polar(s * 0.34, a, x, y), [a2, b2] = polar(s * 0.47, a, x, y);
      return `<line x1="${n(a1)}" y1="${n(b1)}" x2="${n(a2)}" y2="${n(b2)}" stroke="${col}" stroke-width="${n(s / 13)}" stroke-linecap="round"/>`; }).join(''),
    heart: (x, y, s, col) => `<path transform="translate(${x - s / 2} ${y - s / 2}) scale(${s / 24})" d="M12 21C5 16 2.5 12.3 2.5 8.6 2.5 5.6 4.8 3.5 7.5 3.5c1.9 0 3.4 1 4.5 2.6 1.1-1.6 2.6-2.6 4.5-2.6 2.7 0 5 2.1 5 5.1 0 3.7-2.5 7.4-9.5 12.4z" fill="${col}"/>`,
    drop: (x, y, s, col) => `<path transform="translate(${x - s / 2} ${y - s / 2}) scale(${s / 24})" d="M12 2.5C16.5 8 18.5 11.5 18.5 14.5a6.5 6.5 0 0 1-13 0C5.5 11.5 7.5 8 12 2.5z" fill="${col}"/>`,
    moon: (x, y, s, col) => `<path transform="translate(${x - s / 2} ${y - s / 2}) scale(${s / 24})" d="M15 3a9 9 0 1 0 6 15.5A8 8 0 0 1 15 3z" fill="${col}"/>`,
    steps: (x, y, s, col) => [[-0.19, 0.1, -12], [0.19, -0.15, 12]].map(([dx, dy, r]) => {
      const X = x + dx * s, Y = y + dy * s;
      return `<g transform="rotate(${r} ${X} ${Y})"><ellipse cx="${X}" cy="${n(Y - s * 0.1)}" rx="${n(s * 0.15)}" ry="${n(s * 0.24)}" fill="${col}"/><ellipse cx="${X}" cy="${n(Y + s * 0.23)}" rx="${n(s * 0.11)}" ry="${n(s * 0.095)}" fill="${col}"/></g>`; }).join(''),
  };
  // tailles : [actuel, nouveau]
  const S = (a, b) => (big ? b : a);

  // Date
  p.push(t(S(82, 36), S(134, 140), S(36, 48), c.accent, `02<tspan font-size="${S(22, 28)}" fill="${L}" dx="5">OCT</tspan>`, '', big ? 'start' : 'middle'));
  p.push(t(S(82, 38), S(155, 164), S(15, 18), c.softD, 'VENDREDI', 'letter-spacing="1.5"', big ? 'start' : 'middle'));
  // Météo
  p.push(ICON.sun(S(48, 52), S(181, 192), S(24, 32), c.accent));
  p.push(t(S(82, 74), S(191, 205), S(28, 38), L, '21°', '', 'start'));

  // Dôme (fond uni + verre)
  const dome = (cx, cy, R, bg, inner) => {
    const id = `d${cx}`;
    defs.push(`<radialGradient id="${id}e" cx="${cx}" cy="${cy}" r="${R}" gradientUnits="userSpaceOnUse"><stop offset="0.72" stop-color="#000" stop-opacity="0"/><stop offset="0.93" stop-color="#000" stop-opacity="0.28"/><stop offset="1" stop-color="#000" stop-opacity="0.55"/></radialGradient>
      <radialGradient id="${id}h" cx="${cx - R * 0.38}" cy="${cy - R * 0.45}" r="${R * 0.62}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#fff" stop-opacity="0.5"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
      <filter id="${id}s" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>`);
    return `<circle cx="${cx + 3}" cy="${cy + 5}" r="${R}" fill="#000" opacity="0.38" filter="url(#${id}s)"/>
      <circle cx="${cx}" cy="${cy}" r="${R}" fill="${bg}"/>${inner}
      <circle cx="${cx}" cy="${cy}" r="${R}" fill="url(#${id}e)"/>
      <ellipse cx="${n(cx - R * 0.3)}" cy="${n(cy - R * 0.42)}" rx="${n(R * 0.5)}" ry="${n(R * 0.28)}" fill="url(#${id}h)" transform="rotate(-30 ${n(cx - R * 0.3)} ${n(cy - R * 0.42)})"/>
      <circle cx="${cx}" cy="${cy}" r="${R - 0.5}" fill="none" stroke="#fff" stroke-opacity="0.45"/>`;
  };
  const gauge = (cx, cy, r, frac, value, unit, label, ink, soft, track, col, icon) => {
    const a0 = -135, af = a0 + 270 * frac;
    const arc = (b0, b1) => { const [x0, y0] = polar(r, b0, cx, cy), [x1, y1] = polar(r, b1, cx, cy);
      return `M ${n(x0)} ${n(y0)} A ${r} ${r} 0 ${b1 - b0 > 180 ? 1 : 0} 1 ${n(x1)} ${n(y1)}`; };
    return `<path d="${arc(a0, 135)}" fill="none" stroke="${track}" stroke-width="${S(7, 8)}" stroke-linecap="round"/>
      ${frac > 0 ? `<path d="${arc(a0, af)}" fill="none" stroke="${col}" stroke-width="${S(7, 8)}" stroke-linecap="round"/>` : ''}
      ${ICON[icon](cx, cy - S(15, 19), S(16, 19), col)}
      ${t(cx, cy + S(10, 13), S(24, 32), ink, `${value}<tspan font-size="${S(13, 17)}">${unit}</tspan>`)}
      ${t(cx, cy + r + S(2, 3), S(12, 15), soft, label, 'letter-spacing="1.2"')}`;
  };
  p.push(dome(S(68, 66), S(262, 268), S(46, 50), c.bands[0],
    gauge(S(68, 66), S(260, 266), S(34, 37), 0.75, '6h29', '', 'SOMMEIL', L, c.softD, mix(c.bands[0], c.bands[1], 0.7), c.accent, 'moon')));
  p.push(dome(354, S(124, 122), S(46, 50), c.bands[3],
    gauge(354, S(122, 120), S(34, 37), 0.72, '72', '%', 'PLUIE', Dk, c.softL, mix(c.bands[3], c.bands[2], 0.35), c.bands[2], 'drop')));

  // Cardio, batterie
  p.push(ICON.heart(S(370, 374), S(190, 190), S(16, 22), c.bands[2]));
  p.push(t(S(370, 374), S(228, 236), S(32, 46), Dk, '80'));
  p.push(t(S(370, 374), S(244, 256), S(12, 15), c.softL, 'BPM', 'letter-spacing="2"'));
  { const bx = S(358, 358), by = S(270, 274), bw = S(22, 30), bh = S(12, 16);
    p.push(`<rect x="${bx}" y="${by}" width="${bw}" height="${bh}" rx="3" fill="none" stroke="${Dk}" stroke-width="2"/>
      <rect x="${bx + bw + 1}" y="${by + bh * 0.3}" width="3" height="${bh * 0.4}" fill="${Dk}"/>
      <rect x="${bx + 2.5}" y="${by + 2.5}" width="${(bw - 5) * 0.81}" height="${bh - 5}" fill="${c.bands[2]}"/>`); }
  p.push(t(S(370, 374), S(310, 324), S(26, 38), Dk, `81<tspan font-size="${S(15, 20)}">%</tspan>`));

  // Pas
  const sx = S(C - 66, C - 78), sy = S(352, 352);
  p.push(ICON.steps(sx, sy, S(22, 30), c.accent));
  p.push(t(sx + S(16, 20), S(364, 364), S(26, 36), L, '3461', `stroke="${c.bands[1]}" stroke-width="0.6" paint-order="stroke"`, 'start'));
  p.push(t(sx + S(84, 112), S(364, 364), S(13, 17), L, 'PAS', 'letter-spacing="2"', 'start'));
  { const sw = S(14, 15), sg = S(3.5, 4), sh = S(12, 15), y = S(377, 378), x0 = S(C - 95, C - 106);
    for (let i = 0; i < 10; i++) {
      const lit = 0.57 * 10 - i, x = x0 + i * (sw + sg);
      const fill = lit >= 1 ? c.accent : lit > 0 ? c.accent : '#000';
      const op = lit >= 1 ? 1 : lit > 0 ? 0.55 : 0.28;
      p.push(`<rect x="${n(x)}" y="${y}" width="${sw}" height="${sh}" fill="${fill}" opacity="${op}" transform="skewX(-18)" style="transform-box:fill-box;transform-origin:center"/>`);
    }
    p.push(t(x0 + 10 * (sw + sg) + 6, y + sh - 1, S(17, 22), Dk, `57<tspan font-size="${S(11, 15)}">%</tspan>`, '', 'start')); }

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${W}" viewBox="0 0 ${W} ${W}">
    <defs>${defs.join('')}<clipPath id="face"><circle cx="${C}" cy="${C}" r="${C}"/></clipPath></defs>
    <g clip-path="url(#face)">${p.join('\n')}</g></svg>`;
}

const style = `<style>
  @font-face { font-family: Shoulders; font-weight: 800; src: url('${fontUrl('big-shoulders-display-latin-800-normal.woff2')}'); }
  @font-face { font-family: Barlow; font-weight: 600; src: url('${fontUrl('barlow-condensed-latin-600-normal.woff2')}'); }
  body { margin: 0; background: #1b1d21; font-family: Barlow; color: #e8eaed; }
  .row { display: flex; gap: 36px; padding: 28px 36px 10px; }
  .cell { text-align: center; }
  h2 { font-weight: 600; font-size: 30px; margin: 14px 0 2px; letter-spacing: 1px; }
  p { margin: 0; font-size: 20px; color: #9aa3ad; }
</style>`;
const cell = (svg, title, sub) => `<div class="cell">${svg}<h2>${title}</h2><p>${sub}</p></div>`;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1500, height: 640 } });
const shoot = async (html, out, w, h) => {
  await page.setViewportSize({ width: w, height: h });
  // page écrite sur disque : les polices locales (file://) ne se chargent pas depuis setContent
  const tmp = join(here, '_v2.html');
  writeFileSync(tmp, `<html><head>${style}</head><body>${html}</body></html>`);
  await page.goto(pathToFileURL(tmp).href);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: join(here, out) });
  unlinkSync(tmp);
  console.log(out);
};
const c = PAL.neon;
await shoot(`<div class="row">
  ${cell(face(c, 'actuel', false), 'Actuel', 'chiffres coupés, données petites')}
  ${cell(face(c, 'contour'), 'A · Inversé + contour', 'couleur par bande, contour opposé')}
  ${cell(face(c, 'uni'), 'B · Uni + contour', 'chiffres clairs, contour sombre')}
</div>`, 'v2-chiffres.png', 1462, 600);
await shoot(`<div class="row">
  ${['lagune', 'cobalt', 'volcan'].map((k) => cell(face(PAL[k], 'uni'), `B · ${k[0].toUpperCase() + k.slice(1)}`, 'mêmes réglages, autre palette')).join('')}
</div>`, 'v2-palettes.png', 1462, 600);
await browser.close();
