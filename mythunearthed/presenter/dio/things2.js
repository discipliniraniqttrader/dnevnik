// More props: calendar slab, birds, window room, stadium/crowd helpers (added per topic).
import { THREE, V, mat, glow, woodMat, canvasTex, Sph, Box, Cyl, Cap, Cone, between, shade, tube, rnd, lerp, clamp, GRAD, RoundedBoxGeometry } from './kit.js';
export function calendar(cols = 15, rows = 10, tile = 0.62) {
  const g = new THREE.Group(); const W = cols * tile + 0.5, H = rows * tile + 0.5;
  const slab = Box(W, H, 0.4, mat(0x8a8478), 0.1); slab.position.set(W / 2 - 0.25, H / 2 - 0.25, 0); g.add(slab); const fr = Box(W + 0.3, H + 0.3, 0.3, mat(0x5a4a38), 0.08); fr.position.set(W / 2 - 0.25, H / 2 - 0.25, -0.12); g.add(fr);
  const tiles = []; for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) { const m = new THREE.MeshToonMaterial({ color: 0x6a665c, gradientMap: GRAD }); const t = Box(tile * 0.84, tile * 0.84, 0.12, m, 0.03); t.position.set(c * tile + tile / 2 - 0.0, (rows - 1 - r) * tile + tile / 2, 0.24); g.add(t); tiles.push(t); }
  shade(g); g.userData = { tiles, W, H, cols, rows, tile, set(i, col, k = 1) { const t = tiles[i]; if (!t) return; t.material.color.setHex(col); t.position.z = 0.24 + 0.05 * k; } }; return g;
}
export function bird(kind = 'raven') {
  const g = new THREE.Group(); const col = kind === 'raven' ? 0x1c1c26 : 0xfafafa, wing = kind === 'raven' ? 0x2a2a38 : 0xe8eef6; const bm = mat(col), wm = mat(wing);
  const body = Sph(0.2, bm, 1.6, 0.8, 0.85); g.add(body); const hd = Sph(0.11, bm); hd.position.set(0.3, 0.07, 0); g.add(hd); const bk = Cone(0.035, 0.14, mat(kind === 'raven' ? 0x101018 : 0xe89a3a), 8); bk.rotation.z = -Math.PI / 2; bk.position.set(0.42, 0.05, 0); g.add(bk);
  const tl = Box(0.3, 0.03, 0.14, bm, 0.01); tl.position.set(-0.36, 0.0, 0); tl.rotation.z = 0.1; g.add(tl);
  const ey = Sph(0.02, glow(0xffffff)); for (const s of [-1, 1]) { const e = Sph(0.022, mat(0xffffff)); e.position.set(0.34, 0.1, s * 0.07); g.add(e); const p = Sph(0.011, mat(0x000000)); p.position.set(0.355, 0.1, s * 0.075); g.add(p); }
  const wings = [-1, 1].map(s => { const w = new THREE.Group(); w.position.set(0.02, 0.06, s * 0.12); const a = Sph(0.2, wm, 1.1, 0.12, 1.5); a.position.set(-0.04, 0, s * 0.26); w.add(a); const b2 = Sph(0.14, wm, 1.2, 0.1, 1.1); b2.position.set(-0.12, 0, s * 0.52); w.add(b2); g.add(w); return w; });
  if (kind === 'dove') { const lf = new THREE.Group(); const l1 = Sph(0.05, mat(0x5a9a2a), 1.8, 0.25, 0.8); l1.position.set(0.09, 0, 0); lf.add(l1); const st = Cyl(0.006, 0.006, 0.12, mat(0x4a3a1a), 5); st.rotation.z = Math.PI / 2; st.position.x = -0.02; lf.add(st); lf.position.set(0.5, 0.0, 0); g.add(lf); g.userData.leaf = lf; }
  g.userData.flap = (t, sp = 9) => { const a = Math.sin(t * sp) * 0.7; wings[0].rotation.x = -a; wings[1].rotation.x = a; }; shade(g); return g;
}
// room with a window on the -z wall: returns group; window opening centred at (0, 1.6) size 2.2 x 2.0 ; room 7 wide, 5 deep
export function windowRoom() {
  const g = new THREE.Group(); const wall = mat(0xd9b486), floor = woodMat(1.6, 0.5, [130, 84, 46], { seed: 40 });
  const fl = Box(8, 0.2, 6, floor, 0.02); fl.position.set(0, -0.1, 0.5); g.add(fl);
  const wl = (x, w) => { const b = Box(w, 3.6, 0.3, wall, 0.02); b.position.set(x, 1.8, -2.4); g.add(b); };
  wl(-2.9, 2.2); wl(2.9, 2.2); const bot = Box(3.6, 0.6, 0.3, wall, 0.02); bot.position.set(0, 0.3, -2.4); g.add(bot); const top = Box(3.6, 1.0, 0.3, wall, 0.02); top.position.set(0, 3.1, -2.4); g.add(top);
  const frm = mat(0x6a4020); for (const [x, y, w, h] of [[-1.15, 1.6, 0.12, 2.2], [1.15, 1.6, 0.12, 2.2], [0, 0.6, 2.4, 0.12], [0, 2.6, 2.4, 0.12], [0, 1.6, 0.08, 2.0], [0, 1.6, 2.2, 0.08]]) { const b = Box(w, h, 0.16, frm, 0.02); b.position.set(x, y, -2.32); g.add(b); }
  const side = Box(0.3, 3.6, 6, wall, 0.02); side.position.set(-3.9, 1.8, 0.5); g.add(side); const sr = side.clone(); sr.position.x = 3.9; g.add(sr);
  shade(g); return g;
}

// ---- instanced crowd of little people (body capsule + head), colours per instance. userData.set(i, x,y,z, ry, scale, tiltZ) ; userData.n
export function makeCrowd(n, seed = 1, palette = [0xd8503a, 0x3a8a5a, 0xe0a030, 0x4a7bd0, 0xa05a9a, 0xe8e0d0, 0x8a5a3a], hcols = [0xf2c19a, 0xd9a47a, 0xb98058]) {
  const g = new THREE.Group(); const R = rnd(seed);
  const bodyG = new THREE.CapsuleGeometry(0.17, 0.42, 4, 8); bodyG.translate(0, 0.55, 0); const headG = new THREE.SphereGeometry(0.15, 10, 8); headG.translate(0, 1.12, 0);
  const bodies = new THREE.InstancedMesh(bodyG, new THREE.MeshToonMaterial({ gradientMap: GRAD }), n), heads = new THREE.InstancedMesh(headG, new THREE.MeshToonMaterial({ gradientMap: GRAD }), n);
  const c = new THREE.Color(); for (let i = 0; i < n; i++) { bodies.setColorAt(i, c.setHex(palette[Math.floor(R() * palette.length)])); heads.setColorAt(i, c.setHex(hcols[Math.floor(R() * hcols.length)])); }
  bodies.castShadow = heads.castShadow = true; bodies.frustumCulled = heads.frustumCulled = false; g.add(bodies, heads); const d = new THREE.Object3D();
  g.userData = { n, bodies, heads, set(i, x, y, z, ry = 0, s = 1, tz = 0, tx = 0) { d.position.set(x, y, z); d.rotation.set(tx, ry, tz); d.scale.setScalar(Math.max(s, 0.0001)); d.updateMatrix(); bodies.setMatrixAt(i, d.matrix); heads.setMatrixAt(i, d.matrix); }, done() { bodies.instanceMatrix.needsUpdate = true; heads.instanceMatrix.needsUpdate = true; } };
  return g;
}
// ---- soft dust puffs: userData.update(t, on, origin, spread)
export function dustPuffs(n = 16, col = 0xe8d0a8) {
  const g = new THREE.Group(); const R = rnd(11); const ps = []; for (let i = 0; i < n; i++) { const m = new THREE.Mesh(new THREE.SphereGeometry(1, 10, 8), new THREE.MeshToonMaterial({ color: col, gradientMap: GRAD, transparent: true, opacity: 0.0, depthWrite: false })); m.userData.noShadow = true; m.userData.r = [R(), R(), R()]; g.add(m); ps.push(m); }
  g.userData.update = (k, org, spread = 6, rise = 5, size = 3) => { ps.forEach((m, i) => { const r = m.userData.r; const kk = Math.max(0, Math.min(1, k * 1.2 - r[0] * 0.2)); m.position.set(org[0] + (r[1] - .5) * spread * (0.4 + kk), org[1] + kk * rise * (0.4 + r[2]), org[2] + (r[2] - .5) * spread); m.scale.setScalar(Math.max(0.0001, size * (0.4 + kk * 1.2) * (0.6 + r[1] * 0.6))); m.material.opacity = 0.22 * Math.sin(Math.PI * Math.min(kk, 1)) * (k > 0 && k < 1.2 ? 1 : 0); }); }; return g;
}
