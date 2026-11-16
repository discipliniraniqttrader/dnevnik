#!/usr/bin/env node
// Usage: node diorama_render.js <plan.json> <out_dir> <frames: "a-b" | "a,b,c"> [--force-scene N]
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require('playwright');
const [planPath, outDir, spec] = process.argv.slice(2);
const fi = process.argv.indexOf('--force-scene');
const plan = JSON.parse(fs.readFileSync(planPath, 'utf8')); if (fi > 0) plan.forceScene = +process.argv[fi + 1];
fs.mkdirSync(outDir, { recursive: true });
let frames = []; if (spec.includes('-') && !spec.includes(',')) { const [a, b] = spec.split('-').map(Number); for (let i = a; i < b; i++) frames.push(i); } else frames = spec.split(',').map(Number);
const mime = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };
const server = http.createServer((req, res) => { const p = path.join(__dirname, decodeURIComponent(req.url.split('?')[0])); if (!p.startsWith(__dirname) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'Content-Type': mime[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res); });
(async () => {
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('page error:', e.message)); page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.error('console:', m.text()); });
  await page.goto(`http://127.0.0.1:${server.address().port}/diorama.html`);
  await page.waitForFunction('window.READY === true', null, { timeout: 90000 });
  await page.evaluate(p => window.setup(p), plan);
  const meta = {}; const t0 = Date.now();
  for (const f of frames) {
    const r = await page.evaluate(k => window.renderFrame(k), f);
    fs.writeFileSync(path.join(outDir, String(f).padStart(5, '0') + '.jpg'), Buffer.from(r.img.split(',')[1], 'base64')); delete r.img; meta[f] = r;
  }
  fs.writeFileSync(path.join(outDir, `meta_${frames[0]}.json`), JSON.stringify(meta));
  console.log(`rendered ${frames.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  await browser.close(); server.close();
})().catch(e => { console.error(e); process.exit(1); });
