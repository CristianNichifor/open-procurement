// Draws site/og-image.png, the 1200x630 card shown when the site is linked in a chat or
// a social post. Only the site's own motif and words: the three ascending bars of the
// favicon on the accent navy. Rerun after changing the wording:
//
//   node scripts/make_og_image.mjs
import { chromium } from '@playwright/test';
import { fileURLToPath } from 'node:url';

const out = fileURLToPath(new URL('../site/og-image.png', import.meta.url));

const html = `<!doctype html><html lang="ro"><meta charset="utf-8"><style>
  html, body { margin:0; width:1200px; height:630px; }
  body { background:#123a6b; color:#fff; font-family:system-ui,"Segoe UI",sans-serif;
         display:flex; flex-direction:column; justify-content:center; padding:0 96px;
         box-sizing:border-box; }
  svg { width:120px; height:120px; margin-bottom:40px; }
  h1 { font-size:68px; line-height:1.1; margin:0 0 24px; letter-spacing:-.02em; }
  p { font-size:32px; margin:0; color:#cfdcec; }
  .url { position:absolute; left:96px; bottom:56px; font-size:26px; color:#9fb6d3; }
</style><body>
  <svg viewBox="0 0 16 16"><rect x="3.5" y="8.5" width="2.5" height="4.5" fill="#fff"/>
    <rect x="6.75" y="5.5" width="2.5" height="7.5" fill="#fff"/>
    <rect x="10" y="3" width="2.5" height="10" fill="#fff"/></svg>
  <h1>Achiziții publice din România</h1>
  <p>Prețuri unitare comparabile, interogabile în browser. Date deschise.</p>
  <div class="url">projects.cristian-nichifor.com/open-procurement</div>
</body></html>`;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
await page.setContent(html);
await page.screenshot({ path: out });
await browser.close();
console.log(`wrote ${out}`);
