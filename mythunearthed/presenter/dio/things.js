// Shared toon props: measuring pole, door, scrolls, jars, lamps, scales, coins, gold, tablets, stage platform.
import { THREE, V, mat, glow, woodMat, canvasTex, Sph, Box, Cyl, Cap, Cone, between, shade, tube, rnd, lerp, clamp, GRAD, RoundedBoxGeometry } from './kit.js';
const tm = (map, o = {}) => new THREE.MeshToonMaterial({ map, gradientMap: GRAD, ...o });
// ---- vertical measuring board with ticks (0..h metres). Faces +z. anchors: bottom (0,0) / top (0,h) in local space
export function measurePole(h = 3, o = {}) {
  const g = new THREE.Group(); const W = o.w ?? 0.34; const pxm = 220;
  const tex = canvasTex(128, Math.round(h * pxm), (c, w, hh) => { c.fillStyle = '#f2c94c'; c.fillRect(0, 0, w, hh); c.fillStyle = '#3a2a10'; c.strokeStyle = '#3a2a10'; c.font = 'bold 30px sans-serif'; c.textAlign = 'left';
    for (let i = 0; i <= Math.round(h * 10); i++) { const y = hh - i * pxm / 10; const L = i % 10 === 0 ? 70 : i % 5 === 0 ? 50 : 30; c.lineWidth = i % 5 === 0 ? 5 : 3; c.beginPath(); c.moveTo(0, y); c.lineTo(L, y); c.stroke(); if (i % 5 === 0 && i > 0) c.fillText((i / 10).toFixed(i % 10 ? 1 : 0), L + 6, y + 10); } });
  const b = new THREE.Mesh(new THREE.BoxGeometry(W, h, 0.05), [mat(0xd8aa30), mat(0xd8aa30), mat(0xd8aa30), mat(0xd8aa30), tm(tex), mat(0xd8aa30)]); b.position.y = h / 2; g.add(b);
  const bs = Cyl(0.22, 0.26, 0.06, mat(0x6a4a2a), 18); bs.position.y = 0.03; g.add(bs); shade(g); g.userData = { H: h }; return g;
}
// ---- door frame (posts + lintel) with a lit interior panel; opening w x h metres, faces +z
export function doorFrame(w = 1.0, h = 2.05, o = {}) {
  const g = new THREE.Group(); const wd = mat(o.col ?? 0x7a4a26), t = 0.16, dp = 0.3;
  for (const s of [-1, 1]) { const p = Box(t, h + t, dp, wd, 0.03); p.position.set(s * (w / 2 + t / 2), (h + t) / 2, 0); g.add(p); }
  const lt = Box(w + 2 * t + 0.1, t, dp + 0.06, wd, 0.03); lt.position.set(0, h + t / 2, 0); g.add(lt);
  const wall = Box(w + 1.6, h + 0.6, 0.12, mat(o.wall ?? 0xd8b078), 0.03); wall.position.set(0, (h + 0.6) / 2, -0.12); g.add(wall);
  const hole = Box(w, h, 0.14, new THREE.MeshBasicMaterial({ color: o.glow ?? 0xffcf80 }), 0.0); hole.position.set(0, h / 2, -0.1); hole.userData.noShadow = true; g.add(hole);
  shade(g); g.userData = { w, h, lintelY: h, top: h + t }; return g;
}
// ---- scroll / parchment: sheet w x h with text; rods top+bottom. text lines array; big = centred big label
export function scroll(w = 1.4, h = 1.0, o = {}) {
  const g = new THREE.Group(); const tex = canvasTex(512, Math.round(512 * h / w), (c, cw, ch) => {
    c.fillStyle = o.paper ?? '#ead6a4'; c.fillRect(0, 0, cw, ch); const R = rnd(o.seed ?? 5);
    for (let i = 0; i < 70; i++) { c.fillStyle = `rgba(120,80,30,${0.03 + R() * 0.05})`; c.beginPath(); c.arc(R() * cw, R() * ch, 8 + R() * 40, 0, 7); c.fill(); }
    c.fillStyle = '#4a3016'; c.textAlign = 'center'; const heb = o.heb ?? ['וגבה שש אמות', 'וזרת', 'ארבע אמות'];
    const n = o.lines ?? 6; for (let i = 0; i < n; i++) { const y = ch * (0.14 + i * (o.big ? 0.1 : 0.115)); const lw = cw * (0.5 + R() * 0.32); c.fillRect((cw - lw) / 2, y, lw, 7); if (o.heb !== false && i % 2 === 0 && !o.big) { c.font = `bold ${Math.round(ch * 0.07)}px sans-serif`; c.fillText(heb[i / 2 % heb.length | 0], cw / 2, y + 2); } }
    if (o.big) { c.font = `900 ${Math.round(ch * (o.bigSize ?? 0.36))}px sans-serif`; c.fillStyle = o.bigCol ?? '#9a2a1a'; c.fillText(o.big, cw / 2, ch * 0.78); } });
  const sh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), tm(tex, { side: THREE.DoubleSide })); g.add(sh); sh.castShadow = sh.receiveShadow = true;
  for (const y of [h / 2, -h / 2]) { const rd = Cyl(0.035 * w / 1.4 + 0.012, 0.035 * w / 1.4 + 0.012, w + 0.14, mat(0x6a4020), 12); rd.rotation.z = Math.PI / 2; rd.position.y = y; g.add(rd); for (const s of [-1, 1]) { const kn = Sph(0.05 * w / 1.4 + 0.02, mat(0xc9923a)); kn.position.set(s * (w / 2 + 0.07), y, 0); g.add(kn); } }
  shade(g); return g;
}
// ---- clay jar (lathe)
export function jar(h = 0.6, col = 0xc9824a) {
  const pts = [[0.001, 0], [0.2, 0.01], [0.28, 0.15], [0.3, 0.3], [0.24, 0.45], [0.14, 0.52], [0.15, 0.58], [0.19, 0.62], [0.001, 0.62]].map(p => new THREE.Vector2(p[0] * h / 0.62, p[1] * h / 0.62));
  const m = new THREE.Mesh(new THREE.LatheGeometry(pts, 28), new THREE.MeshToonMaterial({ color: col, gradientMap: GRAD, side: THREE.DoubleSide })); m.castShadow = m.receiveShadow = true;
  const g = new THREE.Group(); g.add(m); const bd = new THREE.Mesh(new THREE.TorusGeometry(0.3 * h / 0.62, 0.012, 6, 28), mat(0x7a4020)); bd.rotation.x = Math.PI / 2; bd.position.y = 0.3 * h / 0.62; g.add(bd); return g;
}
// ---- oil lamp with animated flame. userData.flame (group) ; light-ish glow sphere
export function lamp(sc = 1) {
  const g = new THREE.Group(); const cm = mat(0xc9923a);
  const bowl = Sph(0.06, cm, 1.5, 0.7, 1); bowl.position.y = 0.04; g.add(bowl); const sp = Cone(0.02, 0.07, cm, 8); sp.rotation.z = -Math.PI / 2; sp.position.set(0.11, 0.055, 0); g.add(sp);
  const fl = new THREE.Group(); fl.position.set(0.14, 0.08, 0); const f1 = Sph(0.03, glow(0xffb040), 0.8, 1.7, 0.8, 10); f1.position.y = 0.03; fl.add(f1); const f2 = Sph(0.018, glow(0xfff0b0), 0.8, 1.6, 0.8, 10); f2.position.y = 0.02; fl.add(f2); f1.userData.noShadow = f2.userData.noShadow = true; g.add(fl);
  g.scale.setScalar(sc); shade(g); g.userData.flame = fl; g.userData.update = (t) => { fl.scale.set(1, 0.85 + 0.25 * Math.sin(t * 13) * Math.sin(t * 7.3 + 1), 1); fl.rotation.z = 0.12 * Math.sin(t * 5); }; return g;
}
// ---- balance scale; userData.tilt(a) tilts beam (a>0 : left pan down). pans at (+-0.5, ..)
export function balance(sc = 1) {
  const g = new THREE.Group(); const br = mat(0xc9923a), wd = mat(0x6a4020);
  const base = Cyl(0.28, 0.34, 0.06, wd, 20); base.position.y = 0.03; g.add(base); const post = Cyl(0.035, 0.045, 0.95, br, 12); post.position.y = 0.5; g.add(post); const top = Sph(0.06, br); top.position.y = 1.0; g.add(top);
  const beam = new THREE.Group(); beam.position.y = 1.0; g.add(beam); const bm = Box(1.1, 0.04, 0.05, br, 0.015); beam.add(bm);
  const pans = [-1, 1].map(s => { const p = new THREE.Group(); p.position.set(s * 0.52, -0.02, 0); beam.add(p); for (const z of [-0.12, 0, 0.12]) { const ch = between(V(0, 0, 0), V(s * 0.0, -0.4, z * 1.3), 0.004, br, p); } const dish = new THREE.Mesh(new THREE.SphereGeometry(0.2, 22, 8, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), new THREE.MeshToonMaterial({ color: 0xd8a940, gradientMap: GRAD, side: THREE.DoubleSide })); dish.position.y = -0.4; dish.scale.y = 0.45; p.add(dish); p.userData.dishY = -0.38; return p; });
  g.scale.setScalar(sc); shade(g); g.userData.pans = pans; g.userData.beam = beam;
  g.userData.tilt = (a) => { beam.rotation.z = a; pans.forEach(p => { p.rotation.z = -a; }); }; return g;
}
// ---- coin (silver / gold) with a simple embossed eagle disc
const coinTex = {};
function coinFace(col) { if (!coinTex[col]) coinTex[col] = canvasTex(128, 128, (c, w, h) => { c.fillStyle = col; c.fillRect(0, 0, w, h); c.strokeStyle = 'rgba(70,70,80,0.55)'; c.lineWidth = 6; c.beginPath(); c.arc(64, 64, 54, 0, 7); c.stroke(); c.fillStyle = 'rgba(70,70,80,0.5)'; c.beginPath(); c.moveTo(64, 30); c.lineTo(88, 52); c.lineTo(106, 44); c.lineTo(86, 74); c.lineTo(70, 98); c.lineTo(64, 84); c.lineTo(58, 98); c.lineTo(42, 74); c.lineTo(22, 44); c.lineTo(40, 52); c.closePath(); c.fill(); }); return coinTex[col]; }
export function coin(r = 0.05, kind = 'silver') {
  const col = kind === 'gold' ? '#f2c23c' : '#d6dbe2'; const edge = kind === 'gold' ? 0xd9a520 : 0xaeb6c0;
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, r * 0.16, 28), [mat(edge), tm(coinFace(col)), tm(coinFace(col))]); m.castShadow = m.receiveShadow = true; return m;
}
export function coinPile(n = 30, r = 0.05, kind = 'silver', spread = 0.3, seed = 3) { const g = new THREE.Group(); const R = rnd(seed); for (let i = 0; i < n; i++) { const c = coin(r, kind); const a = R() * 6.28, d = Math.sqrt(R()) * spread; c.position.set(Math.cos(a) * d, r * 0.1 + (1 - d / spread) * r * 1.6 * R() * 3, Math.sin(a) * d); c.rotation.set((R() - .5) * 0.5, R() * 6, (R() - .5) * 0.5); g.add(c); } return g; }
export function pouch(r = 0.2, col = 0x7a4a2a) { const g = new THREE.Group(); const b = Sph(r, mat(col), 1, 1.05, 1); b.position.y = r * 0.9; g.add(b); const nk = Cyl(r * 0.3, r * 0.5, r * 0.5, mat(col), 14); nk.position.y = r * 1.8; g.add(nk); const tie = new THREE.Mesh(new THREE.TorusGeometry(r * 0.34, r * 0.07, 8, 16), mat(0xd8b070)); tie.rotation.x = Math.PI / 2; tie.position.y = r * 1.62; g.add(tie); const top = new THREE.Mesh(new THREE.SphereGeometry(r * 0.45, 12, 8, 0, 6.28, 0, 1.6), mat(col)); top.position.y = r * 2.0; top.scale.set(1.3, 0.8, 1.3); g.add(top); shade(g); return g; }
// ---- gold bar (trapezoid prism) ; stack = instanced grid
export function barGeom(l = 0.46, w = 0.16, h = 0.1) { const g = new THREE.CylinderGeometry(0.5, 0.5 * 1.28, 1, 4, 1); g.rotateY(Math.PI / 4); g.scale(l * 0.72 * 1.0, h, w * 0.72 * 1.4); return g; }
export function goldBar(s = 1) { const m = new THREE.Mesh(barGeom(), mat(0xe0a820, { e: 0x3a2400, ei: 0.12 })); m.scale.setScalar(s); m.castShadow = m.receiveShadow = true; return m; }
export function barStack(nx, ny, nz, sx = 0.35, sy = 0.105, sz = 0.18, col = 0xe0a820) {
  const n = nx * ny * nz; const im = new THREE.InstancedMesh(barGeom(), mat(col, { e: 0x3a2400, ei: 0.12 }), n); const d = new THREE.Object3D(); let k = 0;
  for (let y = 0; y < ny; y++) for (let z = 0; z < nz; z++) for (let x = 0; x < nx; x++) { d.position.set((x - (nx - 1) / 2) * sx, y * sy + sy / 2, (z - (nz - 1) / 2) * sz); d.rotation.y = ((y % 2) ? Math.PI / 2 : 0) * 0; d.updateMatrix(); im.setMatrixAt(k++, d.matrix); }
  im.castShadow = im.receiveShadow = true; const g = new THREE.Group(); g.add(im); g.userData.count = n; g.userData.im = im; return g;
}
// ---- clay tablet with cuneiform wedges
export function tablet(w = 0.7, h = 0.5, o = {}) {
  const g = new THREE.Group(); const tex = canvasTex(512, Math.round(512 * h / w), (c, cw, ch) => { c.fillStyle = o.col ?? '#c79a63'; c.fillRect(0, 0, cw, ch); const R = rnd(o.seed ?? 9);
    for (let i = 0; i < 80; i++) { c.fillStyle = `rgba(110,70,35,${0.04 + R() * 0.06})`; c.beginPath(); c.arc(R() * cw, R() * ch, 5 + R() * 28, 0, 7); c.fill(); }
    c.fillStyle = 'rgba(70,40,18,0.85)'; const rows = o.rows ?? 7; for (let r = 0; r < rows; r++) for (let x = 0; x < 20; x++) { if (R() < 0.18) continue; const px = cw * 0.08 + x * (cw * 0.84 / 20), py = ch * 0.1 + r * (ch * 0.8 / rows); c.save(); c.translate(px, py); c.rotate((R() - .5) * 0.5); c.beginPath(); c.moveTo(0, 0); c.lineTo(16, 5); c.lineTo(0, 12); c.closePath(); c.fill(); if (R() < 0.6) { c.fillRect(-10, 4, 12, 3); } c.restore(); } });
  const b = new THREE.Mesh(new RoundedBoxGeometry(w, 0.07, h, 3, 0.03), [mat(0xb0834f), mat(0xb0834f), tm(tex), mat(0xb0834f), mat(0xb0834f), mat(0xb0834f)]); b.castShadow = b.receiveShadow = true; g.add(b); return g;
}
// ---- stage platform: round wooden diorama base with beveled rim; objects stand at y=0
export function stage(r = 14, col = [150, 100, 58], o = {}) {
  const g = new THREE.Group(); const top = new THREE.Mesh(new THREE.CylinderGeometry(r, r + 0.4, 0.8, 64), woodMat(2.4, 0.8, col, { seed: o.seed ?? 21 })); top.position.y = -0.4; top.receiveShadow = true; g.add(top);
  const rim = new THREE.Mesh(new THREE.TorusGeometry(r + 0.05, 0.28, 10, 64), mat(0x6a4326)); rim.rotation.x = Math.PI / 2; rim.position.y = -0.04; g.add(rim); return g;
}
// ---- flat patch of grass / ground on a stage (cylinder disc, slightly raised)
export function patch(r, col = 0x6fa84a, h = 0.12) { const m = Cyl(r, r + 0.15, h, mat(col), 40); m.position.y = h / 2 - 0.0; m.receiveShadow = true; return m; }
// ---- cypress tree
export function cypress(h = 6, col = 0x3a6a30) { const g = new THREE.Group(); const t = Cyl(h * 0.03, h * 0.04, h * 0.2, mat(0x6a4a2a), 8); t.position.y = h * 0.1; g.add(t); const c = Cone(h * 0.16, h * 0.86, mat(col), 14); c.position.y = h * 0.2 + h * 0.43; g.add(c); const c2 = Cone(h * 0.12, h * 0.6, mat(0x4a7a3a), 14); c2.position.y = h * 0.62 + h * 0.2; g.add(c2); shade(g); return g; }
export function rock(r = 0.5, col = 0x9a8a78, seed = 1) { const R = rnd(seed); const m = Sph(r, mat(col, { flat: true }), 1 + R() * 0.3, 0.65, 1 + R() * 0.3, 7); m.position.y = r * 0.3; m.rotation.y = R() * 6; m.castShadow = m.receiveShadow = true; return m; }
export function table(w = 3, d = 1.6, h = 0.8, col = [150, 100, 58]) { const g = new THREE.Group(); const t = Box(w, 0.1, d, woodMat(1, 0.3, col, { seed: 22 }), 0.03); t.position.y = h; g.add(t); for (const sx of [-1, 1]) for (const sz of [-1, 1]) { const l = Box(0.12, h, 0.12, mat(0x5a3a22), 0.03); l.position.set(sx * (w / 2 - 0.15), h / 2, sz * (d / 2 - 0.15)); g.add(l); } shade(g); g.userData.top = h + 0.05; return g; }
