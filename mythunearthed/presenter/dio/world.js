// Shared world helpers for all diorama scenes: registry, easing, environments, camera rig, ground/sea sets.
// A scene builder returns {group, env, cam(lt,u,dur,B,t), update(lt,u,dur,t,B), anchors:{name:()=>Vector3}}; B = beat start times (s, relative to scene start) + scene end.
import { THREE, V, clamp, sstep, lerp, mat, glow, woodMat, put, Sph, Box, Cyl, Cap, Cone, Pln, between, shade, tube, rnd, makeSky, makeWater, makeRain, makeJet, makePerson, poseArms, makeGiraffe, makeElephant, makeLion, makeSheep, makeCloud, makeMountain, sandTex, canvasTex, GRAD } from './kit.js';

export const REG = {}; export const reg = (name, fn) => { REG[name] = fn; };
export const ease = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
export const easeO = (x) => { x = clamp(x); return 1 - Math.pow(1 - x, 3); };
export const easeOB = (x) => { x = clamp(x); return x <= 0 ? 0 : x >= 1 ? 1 : 1 - Math.pow(1 - x, 3) * Math.cos(x * 7); };   // overshoot pop
export const mix3 = (a, b, u) => [lerp(a[0], b[0], u), lerp(a[1], b[1], u), lerp(a[2], b[2], u)];
export const at = (obj, x, y, z) => () => obj.localToWorld(V(x, y, z));
export const fixed = (x, y, z) => () => V(x, y, z);
// progress of a pop-in/animation that starts at beat k (+delay s) and lasts d seconds
export const bp = (B, k, delay = 0, d = 0.6, lt) => ease((lt - (B[k] + delay)) / d);

// Calm camera: Hermite spline through keys [[when, pos, look, fov]], zero velocity at both ends (slow start/stop).
// when = fraction of the scene (0..1) or [beatIndex, fractionOfThatBeat]. Result is smooth (C1), never stops in the middle.
export function camRig(keys) {
  return (lt, u, dur, B) => {
    const ks = keys.map(k => { const w = k[0]; const t = Array.isArray(w) ? B[w[0]] + (B[w[0] + 1] - B[w[0]]) * (w[1] ?? 0) : w * dur; return { t, p: k[1], l: k[2], f: k[3] ?? 40, r: k[4] ?? 0 }; });
    if (lt <= ks[0].t) return { p: ks[0].p, l: ks[0].l, fov: ks[0].f, roll: ks[0].r };
    const n = ks.length; if (lt >= ks[n - 1].t) return { p: ks[n - 1].p, l: ks[n - 1].l, fov: ks[n - 1].f, roll: ks[n - 1].r };
    let i = 0; while (i < n - 2 && lt > ks[i + 1].t) i++;
    const a = ks[i], b = ks[i + 1], h = Math.max(b.t - a.t, 1e-4), s = (lt - a.t) / h, s2 = s * s, s3 = s2 * s;
    const h00 = 2 * s3 - 3 * s2 + 1, h10 = s3 - 2 * s2 + s, h01 = -2 * s3 + 3 * s2, h11 = s3 - s2;
    const lim = (m, d) => (m * d <= 0 ? 0 : Math.sign(m) * Math.min(Math.abs(m), 3 * Math.abs(d)));   // monotone-ish tangents: no overshoot past a key (camera never flies backwards)
    const hv = (c, k) => { const d = (b[c][k] - a[c][k]) / h; const m0 = lim(i <= 0 ? 0 : (ks[i + 1][c][k] - ks[i - 1][c][k]) / Math.max(ks[i + 1].t - ks[i - 1].t, 1e-4), d), m1 = lim(i + 1 >= n - 1 ? 0 : (ks[i + 2][c][k] - ks[i][c][k]) / Math.max(ks[i + 2].t - ks[i].t, 1e-4), d); return h00 * a[c][k] + h10 * h * m0 + h01 * b[c][k] + h11 * h * m1; };
    const hs = (c) => { const d = (b[c] - a[c]) / h; const m0 = lim(i <= 0 ? 0 : (ks[i + 1][c] - ks[i - 1][c]) / Math.max(ks[i + 1].t - ks[i - 1].t, 1e-4), d), m1 = lim(i + 1 >= n - 1 ? 0 : (ks[i + 2][c] - ks[i][c]) / Math.max(ks[i + 2].t - ks[i].t, 1e-4), d); return h00 * a[c] + h10 * h * m0 + h01 * b[c] + h11 * h * m1; };
    return { p: [hv('p', 0), hv('p', 1), hv('p', 2)], l: [hv('l', 0), hv('l', 1), hv('l', 2)], fov: hs('f'), roll: hs('r') };
  };
}

// ------------------------------------------------------------- environments
export const DUSK = { sky: { top: 0x2c3c78, mid: 0xe0803c, hor: 0xffc27a, below: 0x6a4a3a, sunCol: 0xfff0c0, glowK: 0.3, glowP: 12, sunSize: 0.0016 }, sunDir: [-0.25, 0.09, -1],
  fog: { color: 0xf2b074, near: 160, far: 1000 }, hemi: { sky: 0xffdcb4, ground: 0x9a7050, k: 0.95 }, key: { color: 0xffe0b0, k: 2.2, dir: [0.5, 0.75, 0.8], target: [0, 0, 0], ext: 130, far: 500, map: 4096 }, rim: { color: 0xffa860, k: 1.0, dir: [-0.3, 0.3, -1] }, water: 0x1d6fae };
export const STORM = { sky: { top: 0x1c2a44, mid: 0x6a5a68, hor: 0xe09a5c, below: 0x2a3a4a, sunCol: 0xffd9a0, glowK: 0.55, glowP: 10, sunSize: 0.0004 }, sunDir: [-0.2, 0.06, -1],
  fog: { color: 0x9a8078, near: 120, far: 700 }, hemi: { sky: 0xc8c8d8, ground: 0x70604c, k: 0.95 }, key: { color: 0xffd8b0, k: 1.7, dir: [0.5, 0.8, 0.8], target: [0, 0, 0], ext: 130, far: 500, map: 4096 }, rim: { color: 0xff9a58, k: 0.9, dir: [-0.3, 0.3, -1] }, water: 0x23556f };
export const NIGHT = { sky: { top: 0x0e1832, mid: 0x2a3a62, hor: 0x8a6a78, below: 0x141c30, sunCol: 0xaab8ff, glowK: 0.2, glowP: 30, sunSize: 0.0 }, sunDir: [0.3, 0.3, -1],
  fog: { color: 0x2a3858, near: 80, far: 700 }, hemi: { sky: 0x7a90c8, ground: 0x2a2a44, k: 0.9 }, key: { color: 0xa8b8ff, k: 1.1, dir: [0.4, 0.8, 0.6], target: [0, 0, 0], ext: 140, far: 600, map: 2048 }, rim: { color: 0x7a8ad0, k: 0.8, dir: [-0.3, 0.3, -1] }, water: 0x1a3858 };
export const WARMROOM = { sky: { top: 0x3a2418, mid: 0x5a3a24, hor: 0x7a5030, below: 0x2a1a10, sunCol: 0x000000, glowK: 0, glowP: 10, sunSize: 0 }, sunDir: [0, 1, 0],
  fog: { color: 0x4a2e1c, near: 6, far: 26 }, hemi: { sky: 0xffe2c0, ground: 0x9a6a44, k: 1.5 }, key: { color: 0xffe2b8, k: 2.6, dir: [0.4, 1.0, 0.7], target: [0, 0, 0], ext: 3, far: 30, map: 2048 }, rim: { color: 0xffb070, k: 0.7, dir: [-0.5, 0.4, -0.7] }, water: 0x2a6a98 };
export const env = (b, o = {}) => JSON.parse(JSON.stringify(Object.assign({}, b, o)));

// ------------------------------------------------------------- shared world pieces
export function seaWorld(g, e, { amp = 0.6, speed = 1, steep = 1, rain = 0, clouds = true, size = 1400 } = {}) {
  const w = makeWater(size, 120, e.water); g.add(w);
  let rn = null; if (rain) { rn = makeRain(1500, [70, 45, 70], 1.6, 0.5 * rain); g.add(rn); }
  if (clouds) { const R = rnd(9); for (let i = 0; i < 7; i++) { const c = makeCloud(i + 3, i % 2 ? 0xffb482 : 0xf6c8a0, 1.6 + R()); c.position.set((R() - .5) * 700, 70 + R() * 50, -300 - R() * 180); g.add(c); } }
  return { w, rn, amp, speed, steep };
}
export function sandWorld(g) {
  const gnd = new THREE.Mesh(new THREE.PlaneGeometry(1600, 1600, 60, 60).rotateX(-Math.PI / 2), new THREE.MeshToonMaterial({ map: sandTex(60, 60), gradientMap: GRAD })); gnd.receiveShadow = true;
  const p = gnd.geometry.attributes.position; for (let i = 0; i < p.count; i++) { const x = p.getX(i), z = p.getZ(i); const r = Math.hypot(x, z); p.setY(i, r > 150 ? Math.sin(x * 0.01) * Math.cos(z * 0.012) * (r - 150) * 0.05 : 0); } gnd.geometry.computeVertexNormals(); g.add(gnd);
  const R = rnd(4); for (let i = 0; i < 9; i++) { const m = makeMountain(40 + R() * 70, 90 + R() * 80, 20 + i, 0xa07048, 0xd8a870, 0.0); m.position.set(-420 + i * 105 + R() * 40, 0, -520 - R() * 120); g.add(m); }
  for (let i = 0; i < 30; i++) { const rk = Sph(0.8 + R() * 1.6, mat(0x9a7a58, { flat: true }), 1, 0.6, 1, 6); const a = R() * 6.28, d = 40 + R() * 160; rk.position.set(Math.cos(a) * d, 0.3, Math.sin(a) * d); rk.castShadow = true; g.add(rk); }
  return gnd;
}
export function workers(g, pts, seed = 1) {
  const R = rnd(seed); const cols = [0xd8503a, 0x3a8a5a, 0xe0a030, 0x4a7bd0, 0xa05a9a]; const out = [];
  for (const [x, z, ry] of pts) { const p = makePerson({ shirt: cols[Math.floor(R() * cols.length)], pants: 0x4a3a2a, hair: [0x2a1a10, 0x6a3a18, 0x1a1a1a][Math.floor(R() * 3)], hat: R() < 0.5 ? 0xe8c070 : undefined, scale: 1.55 }); p.position.set(x, 0, z); p.rotation.y = ry ?? R() * 6; shade(p); g.add(p); out.push(p); }
  return out;
}
export function bob(obj, w, x, z, t, amp, speed, steep, k = 1, base = 0) { // float a body on the waves: y + gentle pitch/roll
  const h = w.userData.height(x, z, t, amp, speed, steep), hx = w.userData.height(x + 12, z, t, amp, speed, steep) - w.userData.height(x - 12, z, t, amp, speed, steep), hz = w.userData.height(x, z + 6, t, amp, speed, steep) - w.userData.height(x, z - 6, t, amp, speed, steep);
  obj.position.y = base + h * k; obj.rotation.z = Math.atan2(hx, 24) * k; obj.rotation.x = -Math.atan2(hz, 12) * k * 0.7;
}


// ------------------------------------------------------------- more environments
export const DAY = { sky: { top: 0x4d86d4, mid: 0x9cc4ea, hor: 0xffe2b8, below: 0x8a7a60, sunCol: 0xfff4d0, glowK: 0.3, glowP: 14, sunSize: 0.0014 }, sunDir: [-0.4, 0.35, -1],
  fog: { color: 0xf3dcb8, near: 160, far: 1100 }, hemi: { sky: 0xdfeaff, ground: 0xa88a60, k: 1.05 }, key: { color: 0xfff0d0, k: 2.3, dir: [0.5, 0.8, 0.8], target: [0, 0, 0], ext: 60, far: 400, map: 4096 }, rim: { color: 0xffc890, k: 0.8, dir: [-0.3, 0.3, -1] }, water: 0x2a80b8 };
export const FIRENIGHT = { sky: { top: 0x0c1428, mid: 0x1c2438, hor: 0x5a3a3a, below: 0x120e14, sunCol: 0x000000, glowK: 0, glowP: 10, sunSize: 0 }, sunDir: [0, 1, 0],
  fog: { color: 0x2a1c22, near: 30, far: 260 }, hemi: { sky: 0x6a7cb0, ground: 0x5a3a2a, k: 1.0 }, key: { color: 0xffa860, k: 2.4, dir: [0.2, 0.6, 1.0], target: [0, 0, 0], ext: 40, far: 200, map: 2048 }, rim: { color: 0x7a8ad0, k: 0.7, dir: [-0.4, 0.3, -1] }, water: 0x1a3858 };

// ------------------------------------------------------------- ground sets
export function groundPlane(g, color, size = 1600, tex = null) {
  const gnd = new THREE.Mesh(new THREE.PlaneGeometry(size, size).rotateX(-Math.PI / 2), tex ? new THREE.MeshToonMaterial({ map: tex, gradientMap: GRAD }) : mat(color)); gnd.receiveShadow = true; g.add(gnd); return gnd;
}
export function grassTex(rx = 30, ry = 30, base = '#6fa84a') {
  return canvasTex(512, 512, (c, w, h) => { c.fillStyle = base; c.fillRect(0, 0, w, h); const R = rnd(7);
    for (let i = 0; i < 1100; i++) { c.fillStyle = `rgba(${R() < .5 ? '40,110,30' : '210,230,120'},${0.05 + R() * 0.08})`; c.beginPath(); c.arc(R() * w, R() * h, 2 + R() * 10, 0, 7); c.fill(); } }, [rx, ry]);
}
export function hillRing(g, cols, seed = 3, z0 = -420, n = 9, hmin = 40) {
  const R = rnd(seed); for (let i = 0; i < n; i++) { const m = makeMountain(hmin + R() * 60, 90 + R() * 80, 20 + i + seed, cols[i % cols.length], cols[(i + 1) % cols.length], 0.0); m.position.set(-420 + i * 105 + R() * 40, 0, z0 - R() * 120); g.add(m); }
}
export function cloudsDusk(g, seed = 9, n = 7, cols = [0xffb482, 0xf6c8a0]) {
  const R = rnd(seed); for (let i = 0; i < n; i++) { const c = makeCloud(i + 3, cols[i % cols.length], 1.6 + R()); c.position.set((R() - .5) * 700, 70 + R() * 50, -300 - R() * 180); g.add(c); }
}
// small gentle motion helper for dust motes / sparks
export function motes(g, n, box, col = 0xffd9a0, size = 0.003, seed = 3) {
  const R = rnd(seed); const out = []; for (let i = 0; i < n; i++) { const d = Sph(size * (0.6 + R()), glow(col), 1, 1, 1, 6); d.position.set(box[0] + (R() - .5) * box[3], box[1] + R() * box[4], box[2] + (R() - .5) * box[5]); d.userData.s = R(); d.userData.noShadow = true; g.add(d); out.push(d); }
  return (dt, rise = 0.0005, top = box[1] + box[4]) => out.forEach(d => { d.position.y += rise * (0.3 + d.userData.s); if (d.position.y > top) d.position.y = box[1]; });
}

export const STAGE = { sky: { top: 0x24150e, mid: 0x4a2c1a, hor: 0x7a4a2a, below: 0x1a0e08, sunCol: 0x000000, glowK: 0, glowP: 10, sunSize: 0 }, sunDir: [0, 1, 0],
  fog: { color: 0x3a2214, near: 50, far: 140 }, hemi: { sky: 0xffe2c0, ground: 0xa87a50, k: 1.35 }, key: { color: 0xffe0b0, k: 2.6, dir: [-0.35, 0.9, 0.8], target: [0, 0, 0], ext: 34, far: 120, map: 4096 }, rim: { color: 0xffb070, k: 0.8, dir: [0.4, 0.4, -0.8] }, water: 0x2a6a98 };
export function billboard(obj) { const cam = window.__cam; cam.updateMatrixWorld(true); obj.quaternion.copy(cam.quaternion); }
// pop-in: scale an object 0->s with overshoot starting at time t0 (local seconds)
export function popIn(obj, lt, t0, s = 1, d = 0.55) { const k = easeOB((lt - t0) / d); obj.scale.setScalar(Math.max(k * s, 0.0001)); obj.visible = k > 0.002; return k; }
export const camAt = (lt, B, k, d = 0) => lt - (B[k] + d);

// blend two environment presets into `out` (mutates every frame): colours via THREE.Color, numbers and arrays linearly
export function mixEnv(out, A, B, k) {
  const mixv = (a, b) => (typeof a === 'number' && typeof b === 'number') ? lerp(a, b, k) : Array.isArray(a) ? a.map((x, i) => lerp(x, b[i], k)) : a;
  const isCol = (key, v) => typeof v === 'number' && /(top|mid|hor|below|sunCol|color|sky|ground)$/.test(key);
  const rec = (o, a, b) => { for (const key of Object.keys(a)) { const va = a[key], vb = b[key]; if (vb === undefined) continue; if (va && typeof va === 'object' && !Array.isArray(va)) { o[key] = o[key] || {}; rec(o[key], va, vb); } else if (isCol(key, va)) o[key] = new THREE.Color(va).lerp(new THREE.Color(vb), k).getHex(); else o[key] = mixv(va, vb); } };
  rec(out, A, B); return out;
}
// camera-attached pill (3D choice tag) placed at screen-ish offset in front of the camera
export function pillFront(pl, x, y, sc, rz = 0, D = 14) { const cam = window.__cam; cam.updateMatrixWorld(true); pl.position.copy(cam.localToWorld(V(x, y, -D))); pl.quaternion.copy(cam.quaternion); pl.rotateZ(rz); pl.scale.setScalar(Math.max(0.0001, sc)); }
