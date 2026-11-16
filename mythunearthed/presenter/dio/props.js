// Diorama props: ark, interior, ships, field, blueprint, pills, forearm, toy boat, searchlight ...
import { THREE, V, mat, glow, woodMat, canvasTex, put, Sph, Box, Cyl, Cap, Cone, Pln, between, shade, tube, rnd, clamp, lerp, sstep, RoundedBoxGeometry, makePerson, poseArms, makeGiraffe, makeElephant, makeLion, makeSheep, sandTex, GRAD } from './kit.js';

// ---------------------------------------------------------------- extruded slab from a polygon in (x,y), depth along z, with soft bevel
export function slab(pts, depth, m, bevel = 0.4, curveSeg = 1) {
  const sh = new THREE.Shape(pts.map(p => new THREE.Vector2(p[0], p[1])));
  const g = new THREE.ExtrudeGeometry(sh, { depth: Math.max(depth - 2 * bevel, 0.01), bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelSegments: 3, steps: 1, curveSegments: curveSeg });
  g.translate(0, 0, -(depth - 2 * bevel) / 2);
  const o = new THREE.Mesh(g, m); o.castShadow = o.receiveShadow = true; return o;
}
function rectPts(x0, x1, y0, y1, step = 2.5) { // rectangle polygon with extra points on long edges (for bending)
  const p = []; for (let x = x0; x < x1 - 1e-6; x += step) p.push([x, y0]); p.push([x1, y0], [x1, y1]);
  for (let x = x1 - step; x > x0 + 1e-6; x -= step) p.push([x, y1]); p.push([x0, y1]); return p;
}
export const windowTex = (cols = 3, rows = 1, lit = true, wcol = '#ffd27a', bg = '#2a1a10') => canvasTex(256, 128 * rows, (g, w, h) => {
  g.fillStyle = bg; g.fillRect(0, 0, w, h); const cw = w / cols, rh = h / rows;
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) { g.fillStyle = wcol; g.fillRect(c * cw + cw * 0.18, r * rh + rh * 0.2, cw * 0.64, rh * 0.6); g.fillStyle = 'rgba(255,255,255,0.35)'; g.fillRect(c * cw + cw * 0.18, r * rh + rh * 0.2, cw * 0.64, rh * 0.12); g.fillStyle = bg; g.fillRect(c * cw + cw * 0.5 - 2, r * rh + rh * 0.2, 4, rh * 0.6); }
});

// ---------------------------------------------------------------- rounded-rectangle plan extruded upward (soft bevel) -- used for the ark hull
export function rrPts(L, B, r, step = 2.5) {
  const hx = L / 2, hz = B / 2, P = [], arc = (cx, cz, a0) => { for (let i = 0; i <= 6; i++) { const a = a0 + i / 6 * Math.PI / 2; P.push([cx + r * Math.cos(a), cz + r * Math.sin(a)]); } };
  for (let x = -hx + r; x < hx - r - 1e-6; x += step) P.push([x, -hz]);
  arc(hx - r, -hz + r, -Math.PI / 2); arc(hx - r, hz - r, 0);
  for (let x = hx - r - step; x > -hx + r + 1e-6; x -= step) P.push([x, hz]);
  arc(-hx + r, hz - r, Math.PI / 2); arc(-hx + r, -hz + r, Math.PI);
  return P.filter((p, i) => i === 0 || Math.hypot(p[0] - P[i - 1][0], p[1] - P[i - 1][1]) > 1e-3);
}
export function plate(L, B, r, h, y0, m, bevel = 0.4, step = 2.5) { // outer size = L x B x h (bevel included)
  const pts = rrPts(L - 2 * bevel, B - 2 * bevel, Math.max(r - bevel, 0.5), step);
  const g = new THREE.ExtrudeGeometry(new THREE.Shape(pts.map(p => new THREE.Vector2(p[0], p[1]))), { depth: Math.max(h - 2 * bevel, 0.01), bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelSegments: 3, curveSegments: 1 });
  g.rotateX(-Math.PI / 2); g.translate(0, y0 + bevel, 0);
  const o = new THREE.Mesh(g, m); o.castShadow = o.receiveShadow = true; return o;
}

// ---------------------------------------------------------------- THE ARK  (300 x 50 x 30 cubits = 137 x 22.9 x 13.7 m: long, LOW, box-shaped, rounded ends)
export function makeArk(o = {}) {
  const L = o.L ?? 137.2, Bm = o.B ?? 22.9, Hh = o.H ?? 13.7, draft = o.draft ?? 3.4;
  const root = new THREE.Group(); const g = new THREE.Group(); g.position.y = -draft; root.add(g);
  const bigs = [], smalls = [];
  const big = (m) => { bigs.push(m); m.userData.orig = m.geometry.attributes.position.array.slice(); g.add(m); return m; };
  const small = (m) => { smalls.push(m); m.userData.x0 = m.position.x; m.userData.y0 = m.position.y; g.add(m); return m; };
  const plank = woodMat(5.5, 1.5, [176, 118, 66], { seed: o.seed ?? 3 }), pitch = mat(0x3d2517);
  big(plate(L - 4, Bm - 2.4, 9, 3.7, 0, pitch, 1.1));
  big(plate(L, Bm, 6.5, Hh - 3.4, 3.4, plank, 0.6));
  big(plate(L + 1.0, Bm + 1.0, 7, 0.9, 3.0, mat(0x5a3a22), 0.3));
  big(plate(L + 3.2, Bm + 2.8, 8, 1.0, Hh - 0.15, woodMat(8, 3, [214, 150, 88], { seed: 5 }), 0.45));
  big(plate(L * 0.78, 3.4, 1.6, 1.0, Hh + 0.8, mat(0x7a4a28), 0.3));
  const slit = new THREE.MeshBasicMaterial({ color: 0xffd98a }); const sl = Box(L * 0.74, 0.3, 2.6, slit, 0.05); sl.position.set(0, Hh + 1.85, 0); sl.userData.noShadow = true; small(sl); root.userData.skylight = sl;
  // window strip under the roof (bends with the hull), both sides
  const wt = windowTex(3, 1); wt.wrapS = wt.wrapT = THREE.RepeatWrapping; wt.repeat.set(1 / 7.5, 1 / 1.8);
  const wm = new THREE.MeshToonMaterial({ map: wt, emissiveMap: wt, emissive: 0xffffff, emissiveIntensity: 0.9, gradientMap: GRAD });
  const WL = L - 17;
  for (const s of [-1, 1]) { const w = new THREE.Mesh(new THREE.PlaneGeometry(WL, 1.8, Math.round(WL / 2.5), 1), wm); w.position.set(0, Hh - 2.6, s * (Bm / 2 + 0.06)); if (s < 0) w.rotation.y = Math.PI; w.userData.noShadow = true; big(w); }
  const rib = mat(0x6a4326);
  for (let x = -L / 2 + 14; x < L / 2 - 8; x += 9) for (const s of [-1, 1]) { const r = Box(0.7, Hh - 4.6, 0.5, rib, 0.1); r.position.set(x, 3.9 + (Hh - 4.6) / 2, s * (Bm / 2 + 0.2)); small(r); }
  // rope fender band along the waterline
  for (const s of [-1, 1]) { const rp = Box(L - 18, 0.55, 0.5, mat(0xc9a468), 0.2); rp.position.set(0, 3.2, s * (Bm / 2 + 0.3)); small(rp); }
  // side door (+z) with glowing opening and ramp
  const dx = o.doorX ?? -L * 0.14, dz = Bm / 2 + 0.3, dy = 4.8 + 2.7;
  const df = Box(5.0, 7.0, 0.6, mat(0x4a2c16), 0.12); df.position.set(dx, dy, dz); small(df);
  const dg = new THREE.MeshBasicMaterial({ color: 0xffcf80 }); const dp = Box(3.6, 6.0, 0.2, dg, 0.05); dp.position.set(dx, dy, dz + 0.4); dp.userData.noShadow = true; small(dp); root.userData.door = dp;
  const dl1 = Box(1.75, 6.0, 0.25, mat(0x6a4326), 0.08); dl1.position.set(dx - 1.0, dy, dz + 0.65); small(dl1); const dl2 = Box(1.75, 6.0, 0.25, mat(0x6a4326), 0.08); dl2.position.set(dx + 1.0, dy, dz + 0.65); small(dl2);
  if (o.ramp !== false) { const rp = Box(5.0, 0.4, 14, mat(0x8a5a30), 0.08); rp.position.set(dx, 2.9, dz + 6.4); rp.rotation.x = 0.36; g.add(rp); for (const s of [-1, 1]) { const r = Box(0.2, 0.9, 13.5, mat(0x5a3a22), 0.05); r.position.set(dx + s * 2.4, 3.6, dz + 6.4); r.rotation.x = 0.36; g.add(r); } }
  // lanterns + roof vents
  for (let x = -L / 2 + 14; x < L / 2 - 10; x += 18) for (const s of [-1, 1]) { const lp = new THREE.Mesh(new THREE.SphereGeometry(0.55, 10, 8), new THREE.MeshBasicMaterial({ color: 0xffd27a })); lp.position.set(x, Hh - 4.4, s * (Bm / 2 + 1.0)); lp.userData.noShadow = true; small(lp); }
  for (let k = 0; k < 6; k++) for (const s of [-1, 1]) { const v = Box(1.3, 0.8, 1.3, mat(0x8a5a30), 0.15); v.position.set(-L / 2 + 14 + k * 20, Hh + 1.4, s * 7.5); small(v); }
  shade(root);
  root.userData.L = L; root.userData.B = Bm; root.userData.H = Hh; root.userData.draft = draft; root.userData.inner = g;
  root.userData.bend = (fn) => {
    const d = 0.05;
    for (const m of bigs) { const p = m.geometry.attributes.position.array, q = m.userData.orig; for (let i = 0; i < p.length; i += 3) p[i + 1] = q[i + 1] + fn(q[i] + m.position.x); m.geometry.attributes.position.needsUpdate = true; m.geometry.computeVertexNormals(); }
    for (const m of smalls) { m.position.y = m.userData.y0 + fn(m.userData.x0); m.rotation.z = (fn(m.userData.x0 + d) - fn(m.userData.x0 - d)) / (2 * d); }
  };
  root.userData.pt = (x, y, z) => root.localToWorld(V(x, y - draft, z));
  return root;
}

// ---------------------------------------------------------------- ark interior (cutaway): 3 decks, stalls, strip lights, animals
export function makeArkCutaway(o = {}) {
  const L = o.L ?? 137.2, Bm = o.B ?? 22.9, Hh = 13.7; const g = new THREE.Group();
  const wood = woodMat(5.5, 1.5, [176, 118, 66]), dark = woodMat(5.5, 1.5, [120, 76, 40], { seed: 9 });
  const floorM = new THREE.MeshToonMaterial({ map: sandTex(L / 14, Bm / 14), gradientMap: GRAD });
  const back = Box(L, Hh + 1, 0.8, wood, 0.1); back.position.set(0, (Hh + 1) / 2, -Bm / 2); g.add(back);
  for (const s of [-1, 1]) { const e = Box(0.9, Hh + 1, Bm, wood, 0.1); e.position.set(s * L / 2, (Hh + 1) / 2, 0); g.add(e); }
  const decks = [0.6, 4.9, 9.2], lights = [];
  decks.forEach((y, d) => {
    const fl = Box(L, 0.6, Bm, d === 0 ? floorM : wood, 0.1); fl.position.set(0, y - 0.3, 0); g.add(fl);
    const strip = new THREE.MeshBasicMaterial({ color: 0x3a2a1c }); const st = []; // glowing ceiling strip lights
    for (let x = -L / 2 + 5; x < L / 2 - 3; x += 7) { const b = Box(3.4, 0.24, 0.5, strip, 0.08); b.position.set(x, y + 3.6, -Bm / 2 + 3.0); b.userData.noShadow = true; g.add(b); st.push(b); }
    lights.push({ mat: strip, meshes: st });
    for (let x = -L / 2 + 4; x < L / 2; x += 8) { const p = Box(0.5, 4.0, 0.5, dark, 0.08); p.position.set(x, y + 2, Bm / 2 - 1.4); g.add(p); const bm = Box(0.5, 0.5, Bm - 2, dark, 0.08); bm.position.set(x, y + 3.9, 0); g.add(bm); }
    for (let x = -L / 2 + 8; x < L / 2 - 4; x += 8) { const stall = Box(7, 0.45, 0.25, dark, 0.06); stall.position.set(x, y + 0.7, -Bm / 2 + 6); g.add(stall); const st2 = Box(0.25, 1.2, 4.2, dark, 0.06); st2.position.set(x - 3.5, y + 0.6, -Bm / 2 + 4); g.add(st2); }
  });
  const roof = Box(L + 2, 0.8, Bm + 2.4, woodMat(8, 3, [214, 150, 88]), 0.12); roof.position.set(0, Hh + 0.6, 0); g.add(roof);
  // animals per deck
  const A = [];
  const place = (a, x, y, z, ry = 0) => { a.position.set(x, y, z); a.rotation.y = ry; g.add(a); A.push(a); return a; };
  const R = rnd(31);
  const kinds = [() => makeGiraffe(0.5), () => makeElephant(0.85), () => makeLion(1.0)];
  for (let i = 0; i < 8; i++) { const x = -L / 2 + 10 + i * 9; const a = kinds[i % 3](); place(a, x, decks[0], -Bm / 2 + 8.5 + R() * 2, 0.0); }
  for (let i = 0; i < 9; i++) { const x = -L / 2 + 9 + i * 9; place(i % 2 ? makeLion(1.0) : makeSheep(1.5), x, decks[1], -Bm / 2 + 8 + R() * 2.5, 0.0); }
  for (let i = 0; i < 9; i++) { const x = -L / 2 + 9 + i * 9; place(i % 3 === 0 ? makeLion(1.0) : makeSheep(1.5), x, decks[2], -Bm / 2 + 8 + R() * 2.5, 0.0); }
  // near-side wall segment with the door (right 22% of the length), roof opening is the ridge strip
  const DX = -20; const wr = Box(L * 0.14, Hh - 1, 0.8, wood, 0.1); wr.position.set(DX, 0.5 + (Hh - 1) / 2, Bm / 2); g.add(wr);
  const dg = new THREE.MeshBasicMaterial({ color: 0xffcf80 }); const door = Box(4.2, 6.2, 0.3, dg, 0.05); door.position.set(DX, 4.0 + 0.6, Bm / 2 + 0.55); door.userData.noShadow = true; g.add(door);
  const df = Box(5.2, 7.0, 0.5, mat(0x4a2c16), 0.1); df.position.set(door.position.x, door.position.y, Bm / 2 + 0.35); g.add(df);
  const slit = new THREE.MeshBasicMaterial({ color: 0x3a2a1c }); const sl = Box(L * 0.7, 0.35, 3.0, slit, 0.05); sl.position.set(0, Hh + 1.06, 0); sl.userData.noShadow = true; g.add(sl);
  shade(g); g.userData = { L, B: Bm, H: Hh, decks, lights, door, doorFrame: df, slit, slitMat: slit, doorMat: dg, animals: A, wall: wr };
  return g;
}

// ---------------------------------------------------------------- ships
function hullBlock(L, B, h, bowSharp, sternR, m, y0 = 0, bevel = 0.5) { // ship plan (pointed bow, rounded stern) extruded upward
  const hb = B / 2, P = [];
  for (let x = -L / 2 + sternR; x < L / 2 - bowSharp; x += 2.5) P.push([x, -hb]);
  for (let i = 0; i <= 10; i++) { const a = i / 10; P.push([L / 2 - bowSharp + bowSharp * Math.pow(a, 0.85), -hb * Math.pow(1 - a * a, 0.75)]); }
  for (let i = 9; i >= 1; i--) { const a = i / 10; P.push([L / 2 - bowSharp + bowSharp * Math.pow(a, 0.85), hb * Math.pow(1 - a * a, 0.75)]); }
  for (let x = L / 2 - bowSharp; x > -L / 2 + sternR; x -= 2.5) P.push([x, hb]);
  for (let i = 0; i <= 6; i++) { const a = i / 6 * Math.PI / 2; P.push([-L / 2 + sternR - sternR * Math.sin(a), hb - sternR + sternR * Math.cos(a)]); }
  for (let i = 0; i <= 6; i++) { const a = i / 6 * Math.PI / 2; P.push([-L / 2 + sternR * (1 - Math.cos(a)), -hb + sternR - sternR * Math.sin(a)]); }
  const poly = P.filter((p, i) => i === 0 || Math.hypot(p[0] - P[i - 1][0], p[1] - P[i - 1][1]) > 1e-3);
  const g = new THREE.ExtrudeGeometry(new THREE.Shape(poly.map(p => new THREE.Vector2(p[0], p[1]))), { depth: Math.max(h - 2 * bevel, 0.01), bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelSegments: 2, curveSegments: 1 });
  g.rotateX(-Math.PI / 2); g.translate(0, y0 + bevel, 0);
  const o = new THREE.Mesh(g, m); o.castShadow = o.receiveShadow = true; return o;
}
export function makeCargoShip(o = {}) {
  const L = o.L ?? 140, B = o.B ?? 23, Hh = 11, draft = 5; const root = new THREE.Group(); const g = new THREE.Group(); g.position.y = -draft; root.add(g);
  g.add(hullBlock(L, B - 1, draft + 0.6, 14, 6, mat(0xb83a2a), 0, 0.4));
  g.add(hullBlock(L, B, Hh - draft, 16, 6, mat(0x2d3d52), draft, 0.5));
  const deck = hullBlock(L - 2, B - 2.5, 0.8, 14, 5, mat(0x8a98a8), Hh, 0.2); g.add(deck);
  const cols = [0xd8402a, 0x2f6fc8, 0xf2a328, 0x3aa05a, 0xe8d24a, 0xc84a8a, 0x40b0c0]; const R = rnd(14);
  const cm = cols.map(c => mat(c));
  for (let x = -L / 2 + 28; x < L / 2 - 22; x += 6.3) for (let z = -2; z <= 2; z++) { const n = 1 + Math.floor(R() * 3.6); const sm = x > L / 2 - 36 ? Math.min(n, 2) : n; for (let k = 0; k < sm; k++) { const c = Box(5.9, 2.5, 2.7, cm[Math.floor(R() * cm.length)], 0.12); c.position.set(x, Hh + 1.6 + k * 2.6, z * 3.05); c.castShadow = c.receiveShadow = true; g.add(c); } }
  const wt = windowTex(8, 1, true, '#9fd4ff', '#e8edf2'); wt.wrapS = wt.wrapT = THREE.RepeatWrapping;
  const wm = new THREE.MeshToonMaterial({ map: wt, gradientMap: GRAD });
  const tw = Box(12, 18, B - 5, mat(0xf2f2ee), 0.3); tw.position.set(-L / 2 + 14, Hh + 9.6, 0); g.add(tw);
  for (let k = 0; k < 4; k++) { const wp = Pln(11.6, 1.7, wm.clone()); wp.material.map = wt.clone(); wp.material.map.needsUpdate = true; wp.material.map.repeat.set(1, 1); wp.position.set(-L / 2 + 14, Hh + 3 + k * 4.2, B / 2 - 2.45); g.add(wp); const w2 = wp.clone(); w2.position.z = -(B / 2 - 2.45); w2.rotation.y = Math.PI; g.add(w2); }
  const br = Box(10, 3.6, B + 2, mat(0xf2f2ee), 0.3); br.position.set(-L / 2 + 14.5, Hh + 20.4, 0); g.add(br);
  const bw = Box(0.3, 1.8, B + 2.1, mat(0x203a58), 0.05); bw.position.set(-L / 2 + 19.6, Hh + 20.6, 0); g.add(bw);
  const fn = Cyl(2.2, 2.6, 7, mat(0xd8402a)); fn.position.set(-L / 2 + 10, Hh + 22.6, 0); g.add(fn); const ft = Cyl(2.25, 2.25, 1.6, mat(0x20262e)); ft.position.set(-L / 2 + 10, Hh + 26.2, 0); g.add(ft);
  const cr = Cyl(0.3, 0.3, 9, mat(0xdddddd)); cr.position.set(L / 2 - 20, Hh + 5, 0); g.add(cr);
  shade(root); root.userData.L = L; root.userData.B = B; root.userData.draft = draft; root.userData.pt = (x, y, z) => root.localToWorld(V(x, y - draft, z)); return root;
}
export function makeTitanic(o = {}) {
  const L = o.L ?? 269, B = 28, Hh = 19, draft = 10.5; const root = new THREE.Group(); const g = new THREE.Group(); g.position.y = -draft; root.add(g);
  g.add(hullBlock(L, B - 1.5, draft + 0.6, 26, 12, mat(0xa83222), 0, 0.5));
  g.add(hullBlock(L, B, Hh - draft - 0.5, 28, 12, mat(0x1b1f27), draft, 0.5));
  const strip = hullBlock(L - 1, B + 0.4, 0.9, 28, 12, mat(0xe8dcc0), draft + 1.0, 0.2); g.add(strip);
  g.add(hullBlock(L - 6, B - 3, 0.8, 24, 10, mat(0x9a7a50), Hh - 0.4, 0.2));
  const wt = windowTex(30, 1, true, '#ffe29a', '#f1ecde'); wt.wrapS = wt.wrapT = THREE.RepeatWrapping;
  const dk = (len, x0, y0, wd, h, k) => { const b = Box(len, h, wd, mat(0xf3eee2), 0.35); b.position.set(x0, y0 + h / 2, 0); g.add(b);
    for (const s of [-1, 1]) { const w = Pln(len - 1, h * 0.5, new THREE.MeshToonMaterial({ map: wt.clone(), gradientMap: GRAD })); w.material.map.needsUpdate = true; w.material.map.repeat.set(len / 40, 1); w.position.set(x0, y0 + h * 0.5, s * (wd / 2 + 0.05)); if (s < 0) w.rotation.y = Math.PI; g.add(w); } };
  dk(L * 0.62, 4, Hh, B - 5, 4.2, 1); dk(L * 0.5, 4, Hh + 4.2, B - 8, 4.2, 2); dk(L * 0.26, 2, Hh + 8.4, B - 12, 3.8, 3);
  for (let i = 0; i < 4; i++) { const x = 30 - i * 24 - 8; const f = Cyl(5.2, 6.2, 22, mat(0xe6a54a)); f.scale.z = 1.3; f.position.set(x, Hh + 8.4 + 3.8 + 9, 0); g.add(f); const t = Cyl(5.25, 5.25, 4.0, mat(0x14161a)); t.scale.z = 1.3; t.position.set(x, Hh + 8.4 + 3.8 + 20.2, 0); g.add(t); }
  for (const x of [L / 2 - 52, -L / 2 + 46]) { const m = Cyl(0.5, 0.7, 34, mat(0xc8c0b0)); m.position.set(x, Hh + 14, 0); g.add(m); }
  const R = rnd(2); for (let x = -80; x < 70; x += 8) for (const s of [-1, 1]) { const lb = Box(6, 1.6, 2, mat(0xf0e8d6), 0.3); lb.position.set(x, Hh + 13.6, s * 7); lb.castShadow = true; g.add(lb); }
  shade(root); root.userData.L = L; root.userData.B = B; root.userData.draft = draft; root.userData.pt = (x, y, z) => root.localToWorld(V(x, y - draft, z)); return root;
}
export function makeSchooner(o = {}) {
  const L = o.L ?? 110, B = 15.2, Hh = 8.5, draft = 5.5; const root = new THREE.Group(); const g = new THREE.Group(); g.position.y = -draft; root.add(g);
  const wood = woodMat(5, 1.4, [120, 74, 40], { seed: 12 });
  g.add(hullBlock(L, B, Hh, 18, 7, wood, 0, 0.5));
  g.add(hullBlock(L - 2, B + 0.6, 0.9, 18, 7, mat(0xd8d0b8), Hh - 1.4, 0.2));
  g.add(hullBlock(L - 2, B - 2.0, 0.6, 16, 6, woodMat(4, 1.2, [190, 130, 76]), Hh, 0.15));
  const masts = []; const sail = mat(0xf6ecd4, { side: THREE.DoubleSide }); const sailD = new THREE.MeshToonMaterial({ color: 0xf2e6c8, gradientMap: GRAD, side: THREE.DoubleSide });
  const mstep = (L - 24) / 5;
  for (let i = 0; i < 6; i++) {
    const x = -L / 2 + 14 + i * mstep; const m = Cyl(0.55, 0.8, 42, mat(0x7a4a28)); m.position.set(x, Hh + 21, 0); g.add(m); masts.push(x);
    const top = Cyl(0.3, 0.4, 14, mat(0x7a4a28)); top.position.set(x, Hh + 46, 0); g.add(top);
    const boom = Cyl(0.3, 0.3, mstep * 0.95, mat(0x6a3e20)); boom.rotation.z = Math.PI / 2; boom.position.set(x - mstep * 0.45, Hh + 5, 0); g.add(boom);
    const sh = new THREE.Shape(); sh.moveTo(0, 0); sh.lineTo(-mstep * 0.95, 0); sh.lineTo(-mstep * 0.8, 24); sh.lineTo(0, 30); sh.closePath();
    const sg = new THREE.ShapeGeometry(sh, 4); const sp = sg.attributes.position; for (let k = 0; k < sp.count; k++) sp.setZ(k, Math.sin((-sp.getX(k) / (mstep * 0.95)) * Math.PI) * 1.6 + sp.getY(k) * 0.02); sg.computeVertexNormals();
    const s1 = new THREE.Mesh(sg, sailD); s1.position.set(x - 0.2, Hh + 5.3, 0.3); s1.castShadow = true; g.add(s1);
    const sh2 = new THREE.Shape(); sh2.moveTo(0, 0); sh2.lineTo(-mstep * 0.6, 0); sh2.lineTo(-mstep * 0.45, 14); sh2.lineTo(0, 17); sh2.closePath();
    const s2 = new THREE.Mesh(new THREE.ShapeGeometry(sh2, 2), sailD); s2.position.set(x - 0.2, Hh + 36, 0.2); g.add(s2);
  }
  for (let i = 0; i < 3; i++) { const sh = new THREE.Shape(); sh.moveTo(0, 0); sh.lineTo(16, 0); sh.lineTo(0, 30); sh.closePath(); const s = new THREE.Mesh(new THREE.ShapeGeometry(sh), sailD); s.position.set(L / 2 - 6 + i * 3, Hh + 6 + i * 3, 0); s.scale.x = 1 + i * 0.3; g.add(s); }
  const bow = Cyl(0.5, 0.6, 24, mat(0x6a3e20)); bow.rotation.z = -1.2; bow.position.set(L / 2 + 8, Hh + 3, 0); g.add(bow);
  const rig = mat(0x2a1a10);
  for (let i = 0; i < 5; i++) for (const s of [-1, 1]) between(V(masts[i], Hh + 44, 0), V(masts[i] - mstep * 0.7, Hh + 1.2, s * (B / 2 - 0.5)), 0.07, rig, g);
  for (let i = 0; i < 6; i++) for (const s of [-1, 1]) between(V(masts[i], Hh + 40, 0), V(masts[i] + 6, Hh + 1.2, s * (B / 2 - 0.5)), 0.07, rig, g);
  for (let i = 0; i < 5; i++) between(V(masts[i], Hh + 52, 0), V(masts[i + 1], Hh + 52, 0), 0.06, rig, g);
  const hs = Box(14, 4.4, 8, mat(0xe9dfc6), 0.25); hs.position.set(-L / 2 + 9, Hh + 2.8, 0); g.add(hs);
  const pumps = [];
  for (let i = 0; i < 3; i++) { const p = new THREE.Group(); p.position.set(-L / 2 + 28 + i * 24, Hh + 0.6, B / 2 - 2.2); const bar = Cyl(0.7, 0.8, 1.8, mat(0xc8402a)); bar.position.y = 0.9; p.add(bar); const pipe = Cyl(0.3, 0.3, 2.2, mat(0x7a8088)); pipe.rotation.z = Math.PI / 2; pipe.position.set(0, 1.4, 1.2); pipe.rotation.x = Math.PI / 2; pipe.rotation.set(Math.PI / 2, 0, 0); p.add(pipe); const lev = Box(0.25, 0.25, 2.6, mat(0x3a2a1e), 0.04); lev.position.set(0, 2.4, 0); p.add(lev); p.userData.lever = lev; g.add(p); pumps.push(p); }
  shade(root); root.userData = { L, B, draft, masts, pumps, pt: (x, y, z) => root.localToWorld(V(x, y - draft, z)) }; return root;
}

// ---------------------------------------------------------------- toy boat (cute, small)
export function makeToyBoat() {
  const g = new THREE.Group();
  const hull = new THREE.Mesh(new THREE.SphereGeometry(0.5, 28, 14, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), mat(0xe03a3a, { side: THREE.DoubleSide })); hull.scale.set(1.3, 0.7, 0.75); hull.position.y = 0.3; g.add(hull);
  const rim = new THREE.Mesh(new THREE.TorusGeometry(0.5, 0.045, 10, 36), mat(0xfff4e0)); rim.rotation.x = Math.PI / 2; rim.scale.set(1.3, 0.75, 1); rim.position.y = 0.3; g.add(rim);
  const stripe = new THREE.Mesh(new THREE.TorusGeometry(0.45, 0.04, 8, 32), mat(0xffd23f)); stripe.rotation.x = Math.PI / 2; stripe.scale.set(1.3, 0.75, 1); stripe.position.y = 0.17; g.add(stripe);
  const mast = Cyl(0.025, 0.03, 0.9, mat(0xfff4e0)); mast.position.y = 0.72; g.add(mast);
  const sh = new THREE.Shape(); sh.moveTo(0, 0); sh.lineTo(0.55, 0); sh.lineTo(0, 0.75); sh.closePath(); const sail = new THREE.Mesh(new THREE.ShapeGeometry(sh), mat(0xffffff, { side: THREE.DoubleSide })); sail.position.set(0.04, 0.38, 0); g.add(sail);
  const sh2 = new THREE.Shape(); sh2.moveTo(0, 0); sh2.lineTo(-0.4, 0); sh2.lineTo(0, 0.55); sh2.closePath(); const sail2 = new THREE.Mesh(new THREE.ShapeGeometry(sh2), mat(0xffd23f, { side: THREE.DoubleSide })); sail2.position.set(-0.04, 0.38, 0); g.add(sail2);
  const fl = new THREE.Mesh(new THREE.ShapeGeometry((() => { const s = new THREE.Shape(); s.moveTo(0, 0); s.lineTo(0.2, 0.06); s.lineTo(0, 0.12); s.closePath(); return s; })()), mat(0xe03a3a, { side: THREE.DoubleSide })); fl.position.set(0, 1.12, 0); g.add(fl);
  const duck = Sph(0.16, mat(0xffd23f)); duck.position.set(-0.28, 0.5, 0); g.add(duck); const dh = Sph(0.1, mat(0xffd23f)); dh.position.set(-0.22, 0.68, 0); g.add(dh); const bk = Cone(0.04, 0.1, mat(0xf08a2a)); bk.rotation.z = -Math.PI / 2; bk.position.set(-0.11, 0.68, 0); g.add(bk);
  shade(g); return g;
}

// ---------------------------------------------------------------- football (American) field, goal posts
export function makeField() {
  const FW = 109.7, FH = 48.8; const g = new THREE.Group();
  const tex = canvasTex(2048, 912, (c, w, h) => {
    const yd = w / 120; // 120 yd (incl. end zones)
    for (let i = 0; i < 12; i++) { c.fillStyle = i % 2 ? '#3f9a3e' : '#46a846'; c.fillRect(i * 10 * yd, 0, 10 * yd, h); }
    c.fillStyle = '#c0392b'; c.fillRect(0, 0, 10 * yd, h); c.fillStyle = '#2b5fb0'; c.fillRect(110 * yd, 0, 10 * yd, h);
    c.strokeStyle = 'rgba(255,255,255,0.95)'; c.lineWidth = 7; c.strokeRect(4, 4, w - 8, h - 8);
    for (let i = 0; i <= 20; i++) { const x = (10 + i * 5) * yd; c.lineWidth = i % 2 ? 3 : 7; if (i % 2 === 0) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, h); c.stroke(); } else { for (const yy of [h * 0.3, h * 0.7]) { c.beginPath(); c.moveTo(x, yy - 10); c.lineTo(x, yy + 10); c.stroke(); } } }
    c.fillStyle = 'rgba(255,255,255,0.9)'; c.font = `bold ${h * 0.09}px sans-serif`; c.textAlign = 'center';
    for (let i = 1; i <= 9; i++) { const v = i <= 5 ? i * 10 : (10 - i) * 10; const x = (10 + i * 10) * yd; c.fillText(String(v), x, h * 0.2); c.save(); c.translate(x, h * 0.84); c.rotate(Math.PI); c.fillText(String(v), 0, 0); c.restore(); }
  });
  const turf = new THREE.Mesh(new THREE.BoxGeometry(FW + 6, 0.8, FH + 6), [mat(0x2f7a38), mat(0x2f7a38), new THREE.MeshToonMaterial({ map: tex, gradientMap: GRAD }), mat(0x2f7a38), mat(0x2f7a38), mat(0x2f7a38)]);
  // top face texture covers only the pitch area -> use separate plane on top
  turf.material = mat(0x378a3a); turf.position.y = -0.4; turf.receiveShadow = true; g.add(turf);
  const pitch = new THREE.Mesh(new THREE.PlaneGeometry(FW, FH), new THREE.MeshToonMaterial({ map: tex, gradientMap: GRAD })); pitch.rotation.x = -Math.PI / 2; pitch.position.y = 0.02; pitch.receiveShadow = true; g.add(pitch);
  const post = (x) => { const p = new THREE.Group(); const m = mat(0xf2c418); const base = Cyl(0.16, 0.16, 3.2, m); base.position.y = 1.6; p.add(base); const bar = Cyl(0.13, 0.13, 5.6, m); bar.rotation.x = Math.PI / 2; bar.position.y = 3.2; p.add(bar);
    for (const s of [-1, 1]) { const up = Cyl(0.12, 0.12, 6.5, m); up.position.set(0, 3.2 + 3.25, s * 2.8); p.add(up); } p.position.x = x; shade(p); return p; };
  g.add(post(-FW / 2 + 0.2), post(FW / 2 - 0.2));
  g.userData = { FW, FH, goalA: -45.72 };  // goal lines at x = -45.72 and +45.72 (91.44 m apart)
  return g;
}

// ---------------------------------------------------------------- toon hand + forearm (a cubit)
// Hand lies along +x (wrist at x=0, fingers toward +x), palm facing -y. Palm = soft ellipsoid, four fingers (3 phalanges each, slight curl), thumb on the -z side
// springing from the palm heel at ~38 degrees. userData.curl(k) closes the fingers (0 relaxed .. 1 fist); userData.tipX = x of the middle fingertip extreme.
export function makeHand(o = {}) {
  const skinC = o.skin ?? 0xf2c19a, skin = mat(skinC), nailM = mat(new THREE.Color(skinC).lerp(new THREE.Color(0xffe6d6), 0.55).getHex()), shade2 = mat(new THREE.Color(skinC).multiplyScalar(0.9).getHex());
  const g = new THREE.Group(); const s = o.scale ?? 1;
  const RX = 0.105; const palm = Sph(0.056, skin, 1.0, 0.36, 0.95, 24); palm.position.set(0.054, 0, 0); g.add(palm);                      // heel -> knuckles, 0.1 long x 0.097 wide
  const ridge = Sph(0.05, skin, 0.4, 0.34, 0.98, 20); ridge.position.set(RX - 0.002, 0.0, 0); g.add(ridge);              // knuckle ridge so the fingers grow out of a rounded edge
  const FINGERS = [ // z of knuckle (thumb side is -z), length of the three phalanges together, radius, spread (rad about y)
    { z: -0.034, len: 0.076, r: 0.0118, sp: -0.06 }, { z: -0.0115, len: 0.088, r: 0.0122, sp: -0.015 }, { z: 0.0115, len: 0.081, r: 0.0118, sp: 0.03 }, { z: 0.033, len: 0.064, r: 0.0106, sp: 0.09 }];
  const fr = [0.46, 0.3, 0.24], curlBase = o.curl ?? [0.04, 0.12, 0.1]; const fingers = [];
  const chainEnd = (len, r, cur) => { let x = 0, y = 0, a = 0; fr.forEach((f, i) => { a += cur[i]; x += Math.cos(a) * len * f; y -= Math.sin(a) * len * f; }); return [x, y, a, r]; };   // end point of the last joint (cap centre); the extreme in +x is x + r
  let scaleMid = 1;
  { const [ex] = chainEnd(FINGERS[1].len, FINGERS[1].r, curlBase); scaleMid = ((o.tipX ?? 0.18) - RX - FINGERS[1].r * (1 - 0.05 * 2)) / ex; }   // knuckle root at x=0.094; cap radius of the 3rd phalanx added back
  FINGERS.forEach((F, fi) => {
    const len = F.len * scaleMid; const root = new THREE.Group(); root.position.set(RX, 0.004, F.z); root.rotation.y = F.sp; g.add(root); const js = []; let parent = root;
    fr.forEach((f, i) => { const j = new THREE.Group(); if (i) j.position.x = len * fr[i - 1]; parent.add(j); js.push(j);
      const r = F.r * (1 - 0.05 * i); const bone = Cap(r, len * f, skin, 12); bone.rotation.z = Math.PI / 2; bone.position.x = len * f / 2; j.add(bone); parent = j; });
    const lastJ = js[2]; const nail = Sph(F.r * 0.8, nailM, 1.1, 0.35, 0.85, 10); nail.position.set(len * fr[2] * 0.62, F.r * 0.62, 0); lastJ.add(nail);
    fingers.push({ js, curl: curlBase.slice(), len, r: F.r });
  });
  // thumb: heel blob + two phalanges angled out of the palm side (-z), slightly lifted
  const th = new THREE.Group(); th.position.set(0.022, -0.004, -0.04); th.rotation.y = 0.4; th.rotation.x = 0.0; g.add(th);
  const heel = Sph(0.027, skin, 1.2, 0.7, 0.9, 14); heel.position.set(0.014, 0, 0.006); th.add(heel);
  const t1 = new THREE.Group(); t1.position.set(0.03, 0, 0); th.add(t1); const b1 = Cap(0.0128, 0.04, skin, 12); b1.rotation.z = Math.PI / 2; b1.position.x = 0.02; t1.add(b1);
  const t2 = new THREE.Group(); t2.position.set(0.04, 0, 0); t1.add(t2); const b2 = Cap(0.0118, 0.03, skin, 12); b2.rotation.z = Math.PI / 2; b2.position.x = 0.015; t2.add(b2);
  const tn = Sph(0.01, nailM, 1.1, 0.35, 0.85, 10); tn.position.set(0.02, 0.0085, 0); t2.add(tn); t1.rotation.z = -0.05; t2.rotation.z = -0.1;
  const thumb = { t1, t2 };
  const setCurl = (k) => { fingers.forEach((F, i) => { const c = [curlBase[0] + 1.05 * k, curlBase[1] + 1.2 * k, curlBase[2] + 0.9 * k]; F.js.forEach((j, n) => { j.rotation.z = -c[n]; }); });
    thumb.t1.rotation.z = -0.1 - 0.5 * k; thumb.t2.rotation.z = -0.2 - 0.7 * k; thumb.t1.rotation.y = -0.45 * k; };
  setCurl(o.fist ?? 0);
  const ce = chainEnd(FINGERS[1].len * scaleMid, FINGERS[1].r, curlBase), tipX = RX + ce[0] + FINGERS[1].r * 0.9, tipY = 0.004 + ce[1];
  g.scale.setScalar(s); shade(g); g.userData = { curl: setCurl, tipX, tipY, fingers, thumb }; return g;
}
export function makeForearm() {
  const g = new THREE.Group(); const skin = mat(0xf2c19a), sleeve = mat(0x4a7bd0), cuff = mat(0xf4efe6);
  // arm lies along +x: back of the elbow at x=-0.055, middle fingertip exactly at x=0.45 (a cubit)
  const elbow = Sph(0.055, sleeve); g.add(elbow);
  const sl = Cyl(0.047, 0.056, 0.2, sleeve); sl.rotation.z = -Math.PI / 2; sl.position.set(0.08, 0, 0); g.add(sl);
  const cf = Cyl(0.04, 0.04, 0.026, cuff); cf.rotation.z = -Math.PI / 2; cf.position.set(0.19, 0, 0); g.add(cf);
  const fa = Cyl(0.03, 0.036, 0.08, skin); fa.rotation.z = -Math.PI / 2; fa.position.set(0.23, 0, 0); g.add(fa);
  const WX = 0.255; const wr = Sph(0.034, skin, 0.9, 0.8, 1.15); wr.position.set(WX, 0, 0); g.add(wr);
  const FZ = -0.0115; const hand = makeHand({ tipX: 0.45 - WX }); hand.position.set(WX, 0.0, 0); g.add(hand);
  const tip = V(WX + hand.userData.tipX, hand.userData.tipY, FZ);
  shade(g); g.userData = { elbow: V(-0.055, 0, 0), tip, hand }; return g;
}
export function makeRuler(len = 0.5) {
  const g = new THREE.Group();
  const tex = canvasTex(1024, 128, (c, w, h) => { c.fillStyle = '#f2c94c'; c.fillRect(0, 0, w, h); c.strokeStyle = '#3a2a10'; c.fillStyle = '#3a2a10'; c.font = 'bold 30px sans-serif'; c.textAlign = 'center';
    for (let i = 0; i <= 50; i++) { const x = 20 + i * (w - 40) / 50; const L = i % 10 === 0 ? 46 : i % 5 === 0 ? 34 : 20; c.lineWidth = 3; c.beginPath(); c.moveTo(x, 0); c.lineTo(x, L); c.stroke(); if (i % 10 === 0) c.fillText(String(i), x, 82); } });
  const b = new THREE.Mesh(new RoundedBoxGeometry(len + 0.04, 0.012, 0.055, 2, 0.005), [mat(0xd8aa30), mat(0xd8aa30), new THREE.MeshToonMaterial({ map: tex, gradientMap: GRAD }), mat(0xd8aa30), mat(0xd8aa30), mat(0xd8aa30)]);
  b.castShadow = b.receiveShadow = true; g.add(b); g.userData.len = len; return g;
}

// ---------------------------------------------------------------- blueprint board
export function makeBlueprint() {
  const g = new THREE.Group();
  const tex = canvasTex(1536, 1024, (c, w, h) => {
    c.fillStyle = '#1c5ea6'; c.fillRect(0, 0, w, h); c.strokeStyle = 'rgba(255,255,255,0.12)'; c.lineWidth = 1; for (let x = 0; x < w; x += 32) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, h); c.stroke(); } for (let y = 0; y < h; y += 32) { c.beginPath(); c.moveTo(0, y); c.lineTo(w, y); c.stroke(); }
    c.strokeStyle = '#ffffff'; c.fillStyle = '#ffffff'; c.lineWidth = 5; c.textAlign = 'center';
    c.font = 'bold 54px sans-serif'; c.fillText('THE ARK  -  PLAN', w / 2, 90);
    // plan view: 6:1 rectangle with grid
    const px = 120, pw = w - 240, ph = pw / 6; const py = 170;
    c.strokeRect(px, py, pw, ph); c.lineWidth = 2; for (let i = 1; i < 30; i++) { c.beginPath(); c.moveTo(px + pw * i / 30, py); c.lineTo(px + pw * i / 30, py + ph); c.stroke(); } c.beginPath(); c.moveTo(px, py + ph / 2); c.lineTo(px + pw, py + ph / 2); c.stroke();
    c.font = 'bold 34px sans-serif'; c.fillText('LENGTH 300 CUBITS', w / 2, py - 18); c.fillText('WIDTH 50', px + pw + 0, py + ph + 52);
    // side elevation with 3 decks
    const sy = 520, sh = pw / 10; c.lineWidth = 5; c.strokeRect(px, sy, pw, sh); c.lineWidth = 2.5; for (let d = 1; d < 3; d++) { c.beginPath(); c.moveTo(px, sy + sh * d / 3); c.lineTo(px + pw, sy + sh * d / 3); c.stroke(); }
    c.fillStyle = '#ffd23f'; c.fillRect(px + pw * 0.72, sy + sh * 0.35, 40, sh * 0.65); c.fillStyle = '#fff'; c.font = 'bold 40px sans-serif'; c.fillText('ONE DOOR IN THE SIDE', px + pw * 0.72, sy + sh + 60);
    c.fillText('3 DECKS', px + pw * 0.25, sy + sh + 60); c.font = 'bold 120px sans-serif'; c.fillStyle = '#ffd23f'; c.fillText('6 : 1', w / 2, 930); c.font = 'bold 40px sans-serif'; c.fillStyle = '#fff'; c.fillText('LONG AND NARROW', w / 2 + 320, 930);
  });
  const W = 3.0, Hh = 2.0; const frame = Box(W + 0.2, Hh + 0.2, 0.1, mat(0x6a4326), 0.04); g.add(frame);
  const sheet = new THREE.Mesh(new THREE.PlaneGeometry(W, Hh), new THREE.MeshToonMaterial({ map: tex, gradientMap: GRAD, emissive: 0x1a3a6a, emissiveIntensity: 0.4 })); sheet.position.z = 0.056; g.add(sheet);
  shade(g); g.userData = { W, H: Hh, tex }; return g;
}

// ---------------------------------------------------------------- choice pills
export function makePill(text, color, w = 9, h = 3.2) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new RoundedBoxGeometry(w, h, 1.4, 6, h / 2.05), new THREE.MeshToonMaterial({ color, gradientMap: GRAD, depthTest: false })); body.castShadow = true; body.renderOrder = 20; g.add(body);
  const tex = canvasTex(768, 270, (c, W, H) => { c.fillStyle = 'rgba(255,255,255,0.16)'; c.fillRect(0, 0, W, H * 0.45); c.fillStyle = '#fff'; let fs_ = 118; c.font = '900 118px Inter, sans-serif'; while (c.measureText(text).width > W * 0.9 && fs_ > 40) { fs_ -= 4; c.font = `900 ${fs_}px Inter, sans-serif`; } c.textAlign = 'center'; c.textBaseline = 'middle'; c.shadowColor = 'rgba(0,0,0,0.45)'; c.shadowBlur = 8; c.fillText(text, W / 2, H / 2 + 6); });
  const lab = new THREE.Mesh(new THREE.PlaneGeometry(w * 0.94, h * 0.94), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, depthTest: false })); lab.renderOrder = 21; lab.position.z = 0.71; g.add(lab); lab.userData.noShadow = true;
  return g;
}

// ---------------------------------------------------------------- searchlight tower + beam
export function makeSearchlight() {
  const g = new THREE.Group(); const tw = Cyl(0.9, 1.6, 12, mat(0x5a6470)); tw.position.y = 6; g.add(tw);
  const base = Cyl(2.4, 2.8, 1, mat(0x3a4048)); base.position.y = 0.5; g.add(base);
  const head = new THREE.Group(); head.position.y = 12.8; g.add(head);
  const drum = Cyl(1.5, 1.5, 3.0, mat(0x8a96a2)); drum.rotation.z = Math.PI / 2; head.add(drum); const lens = Cyl(1.3, 1.3, 0.2, new THREE.MeshBasicMaterial({ color: 0xfff6d0 })); lens.rotation.z = Math.PI / 2; lens.position.x = 1.55; head.add(lens);
  const tex = canvasTex(8, 256, (c, w, h) => { const gr = c.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, 'rgba(255,248,210,0.0)'); gr.addColorStop(0.06, 'rgba(255,248,210,0.75)'); gr.addColorStop(1, 'rgba(255,248,210,0.0)'); c.fillStyle = gr; c.fillRect(0, 0, w, h); });
  const len = 260; const cg = new THREE.CylinderGeometry(26, 1.0, len, 28, 1, true); cg.translate(0, len / 2, 0); cg.rotateZ(-Math.PI / 2);
  const beam = new THREE.Mesh(cg, new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false }));
  // uv v runs along the cylinder height: bottom (v=0) -> top (v=1); our narrow end is the bottom => fine
  beam.position.x = 1.6; beam.renderOrder = 5; beam.userData.noShadow = true; head.add(beam);
  shade(g); g.userData = { head, beam }; return g;
}
