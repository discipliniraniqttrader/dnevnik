// Fire, kilns, ovens, thermometers.
import { THREE, V, mat, glow, woodMat, canvasTex, Sph, Box, Cyl, Cap, Cone, between, shade, rnd, lerp, clamp, GRAD } from './kit.js';
import { brickTex } from './bldg.js';
const bmat = (rx = 3, ry = 2) => { const t = brickTex(5).clone(); t.needsUpdate = true; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rx, ry); t.colorSpace = THREE.SRGBColorSpace; return new THREE.MeshToonMaterial({ map: t, gradientMap: GRAD, color: 0xc89a78, side: THREE.DoubleSide }); };
// animated flame cluster: userData.update(t, k=1) k = intensity scale
export function fire(h = 2, w = 1, n = 7, seed = 1) {
  const g = new THREE.Group(); const R = rnd(seed); const fl = []; const cols = [0xff7a1a, 0xffa030, 0xffd050, 0xff5a10];
  for (let i = 0; i < n; i++) { const a = i / n * Math.PI * 2, r = w * 0.3 * (i % 2 ? 1 : 0.5); const m = new THREE.Mesh(new THREE.ConeGeometry(w * (0.28 + 0.12 * R()), h * (0.7 + 0.5 * R()), 10), new THREE.MeshBasicMaterial({ color: cols[i % 4], fog: false })); m.position.set(Math.cos(a) * r, h * 0.35, Math.sin(a) * r); m.userData = { ph: R() * 6, base: m.geometry.parameters.height, s: 0.8 + 0.4 * R() }; m.userData.noShadow = true; g.add(m); fl.push(m); }
  const core = new THREE.Mesh(new THREE.ConeGeometry(w * 0.22, h * 0.85, 10), new THREE.MeshBasicMaterial({ color: 0xfff2b0, fog: false })); core.position.y = h * 0.38; core.userData.noShadow = true; g.add(core);
  const sp = []; for (let i = 0; i < 14; i++) { const s = Sph(0.05 * w + 0.02, new THREE.MeshBasicMaterial({ color: 0xffc060, fog: false }), 1, 1, 1, 5); s.userData = { ph: R(), x: (R() - .5) * w, z: (R() - .5) * w, noShadow: true }; g.add(s); sp.push(s); }
  g.userData.update = (t, k = 1) => { g.visible = k > 0.01; fl.forEach((m, i) => { const f = 0.85 + 0.3 * Math.sin(t * 9 * m.userData.s + m.userData.ph) * Math.sin(t * 4.3 + i); m.scale.set(0.9 + 0.1 * f, Math.max(0.0001, f * k), 0.9 + 0.1 * f); m.position.y = h * 0.35 * f * k; m.rotation.z = 0.12 * Math.sin(t * 5 + m.userData.ph); }); core.scale.set(1, Math.max(0.0001, (0.9 + 0.2 * Math.sin(t * 11)) * k), 1); core.position.y = h * 0.38 * k;
    sp.forEach(s => { const p = ((t * 0.6 + s.userData.ph) % 1); s.position.set(s.userData.x + Math.sin(t * 2 + s.userData.ph * 9) * 0.2, h * (0.4 + p * 1.6) * k, s.userData.z); s.scale.setScalar(Math.max(0.0001, (1 - p) * k)); }); };
  return g;
}
// brick kiln (dome + chimney + glowing mouth). cut=true: front half open to show the inside (floor glow, hatch ring)
export function kiln(o = {}) {
  const g = new THREE.Group(); const bm = bmat(4, 2); const cut = !!o.cut;
  const body = new THREE.Mesh(new THREE.CylinderGeometry(3.0, 3.4, 3.4, 32, 1, true, cut ? Math.PI * 0.45 : 0, cut ? Math.PI * 1.1 : Math.PI * 2), bm); body.position.y = 1.7; body.castShadow = body.receiveShadow = true; g.add(body);
  const dome = new THREE.Mesh(new THREE.SphereGeometry(3.0, 32, 14, cut ? Math.PI * 0.45 : 0, cut ? Math.PI * 1.1 : Math.PI * 2, 0, Math.PI / 2), bmat(4, 1.5)); dome.position.y = 3.4; dome.castShadow = true; g.add(dome);
  const ch = Cyl(0.75, 0.95, 3.2, bmat(1.5, 2), 16); ch.position.set(0, 6.6, -0.6); ch.castShadow = true; g.add(ch); for (const y of [0.5, 2.0, 3.2]) { const bd = new THREE.Mesh(new THREE.TorusGeometry(3.15 - y * 0.02, 0.09, 6, 36), mat(0x3a2a22)); bd.rotation.x = Math.PI / 2; bd.position.y = y; g.add(bd); }
  const base = Cyl(3.7, 3.9, 0.5, mat(0x5a4a40), 32); base.position.y = 0.25; g.add(base);
  const hole = new THREE.Mesh(new THREE.CircleGeometry(2.9, 32).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xff7a20, fog: false })); hole.position.y = 0.52; hole.userData.noShadow = true; if (cut) g.add(hole);
  if (!cut) { const mo = Box(1.8, 2.0, 0.6, new THREE.MeshBasicMaterial({ color: 0xff8a2a, fog: false }), 0.05); mo.position.set(0, 1.5, 3.1); mo.userData.noShadow = true; g.add(mo); const fr = Box(2.3, 2.4, 0.5, mat(0x3a2a22), 0.1); fr.position.set(0, 1.5, 3.0); g.add(fr); const fi = fire(1.8, 1.6, 7, 3); fi.position.set(0, 0.7, 3.25); g.add(fi); g.userData.mouthFire = fi; }
  const top = fire(2.8, 1.4, 7, 9); top.position.set(0, 8.1, -0.6); g.add(top); g.userData.topFire = top;
  const inner = fire(1.8, 2.4, 9, 5); inner.position.set(0, 0.6, -1.4); if (cut) { g.add(inner); g.userData.innerFire = inner; }
  shade(g); g.userData.mouth = V(0, 1.5, 3.4); g.userData.update = (t, k = 1) => { top.userData.update(t, k); if (g.userData.mouthFire) g.userData.mouthFire.userData.update(t + 1, k); if (g.userData.innerFire) g.userData.innerFire.userData.update(t + 2, k); }; return g;
}
export function oven(sc = 1) { const g = new THREE.Group(); const body = Box(0.62, 0.6, 0.58, mat(0xe8e8ec), 0.04); body.position.y = 0.3; g.add(body); const win = Box(0.44, 0.3, 0.02, new THREE.MeshBasicMaterial({ color: 0xff8a2a }), 0.01); win.position.set(0, 0.28, 0.3); win.userData.noShadow = true; g.add(win); const hd = Cyl(0.012, 0.012, 0.46, mat(0x888890), 6); hd.rotation.z = Math.PI / 2; hd.position.set(0, 0.46, 0.33); g.add(hd); for (let i = 0; i < 4; i++) { const k = Cyl(0.03, 0.03, 0.03, mat(0x444450), 10); k.rotation.x = Math.PI / 2; k.position.set(-0.2 + i * 0.13, 0.54, 0.3); g.add(k); } g.scale.setScalar(sc); shade(g); return g; }
// thermometer: glass tube h m, red fill set via set(k 0..1). bulb at bottom
export function thermo(h = 6.3, sc = 1) { const g = new THREE.Group(); const tube = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, h, 16), new THREE.MeshToonMaterial({ color: 0xdfeaf4, gradientMap: GRAD, transparent: true, opacity: 0.5 })); tube.position.y = h / 2 + 0.4; g.add(tube); const bulb = Sph(0.5, mat(0xd8321a, { e: 0x601008, ei: 0.5 }), 1, 1, 1, 18); bulb.position.y = 0.45; g.add(bulb); const fill = Cyl(0.13, 0.13, h, mat(0xd8321a, { e: 0x601008, ei: 0.5 }), 12); g.add(fill); fill.position.y = 0.45; for (let i = 0; i <= 10; i++) { const tk = Box(0.5, 0.06, 0.05, mat(0x3a2a22), 0.01); tk.position.set(0.5, 0.4 + i * h / 10, 0); g.add(tk); }
  g.scale.setScalar(sc); g.userData = { h, set(k) { const hh = Math.max(0.01, k * h); fill.scale.y = hh / h; fill.position.y = 0.45 + hh / 2; }, top: () => g.localToWorld(V(0, 0.45 + h, 0)) }; g.userData.set(1); return g; }
