#!/usr/bin/env node
// Usage: node render.js <timeline.json> <out_dir>
const fs = require('fs');
const path = require('path');
const http = require('http');
const { chromium } = require('playwright');

const [tlPath, outDir] = process.argv.slice(2);
if (!tlPath || !outDir) { console.error('usage: node render.js <timeline.json> <out_dir>'); process.exit(1); }
const timeline = JSON.parse(fs.readFileSync(tlPath, 'utf8'));
timeline.fps = timeline.fps || 30;
fs.mkdirSync(outDir, { recursive: true });

const mime = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const p = path.join(__dirname, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(__dirname) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': mime[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});

(async () => {
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 900, height: 1200 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('page error:', e.message));
  page.on('console', m => { if (m.type() === 'error') console.error('console:', m.text()); });
  await page.goto(`http://127.0.0.1:${port}/index.html`);
  await page.waitForFunction('window.READY === true', null, { timeout: 60000 });
  const n = await page.evaluate(tl => window.setup(tl), timeline);
  const t0 = Date.now();
  for (let i = 0; i < n; i++) {
    const url = await page.evaluate(k => window.renderFrame(k), i);
    fs.writeFileSync(path.join(outDir, String(i).padStart(5, '0') + '.png'), Buffer.from(url.split(',')[1], 'base64'));
  }
  const s = (Date.now() - t0) / 1000;
  console.log(`rendered ${n} frames in ${s.toFixed(1)}s (${(s / n).toFixed(3)} s/frame)`);
  await browser.close(); server.close();
})().catch(e => { console.error(e); process.exit(1); });
