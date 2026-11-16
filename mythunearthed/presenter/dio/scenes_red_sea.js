// red_sea: crossing between water walls, stadium x25, endless column, 1 km front, clans, reeds, footprints.
import { THREE, V, clamp, mat, glow, woodMat, Sph, Box, Cyl, Cap, Cone, shade, rnd, lerp, sandTex, GRAD, makeWater, makeMountain, makeCloud } from './kit.js';
import { makePill } from './props.js';
import { REG, reg, ease, easeO, easeOB, at, fixed, camRig, env, mixEnv, pillFront, popIn, DUSK, NIGHT } from './world.js';
import { person, walkCycle } from './folk.js';
import { makeCrowd } from './things2.js';
import { stopwatch } from './things3.js';
import { waterWall, stadium, tent, reeds, footprints, moon } from './things6.js';

const MOONLIT = (o = {}) => { const e = env(NIGHT, { key: { ...NIGHT.key, k: 1.6, ext: 90, target: [30, 0, 0], dir: [-0.3, 0.7, 0.6], far: 320, map: 4096 }, hemi: { sky: 0x8aa0d8, ground: 0x4a4a5a, k: 1.1 } }); e.fog = { color: 0x1c2a48, near: 60, far: 520 }; return e; };
const seabed = (g, w = 900, d = 300) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d).rotateX(-Math.PI / 2), new THREE.MeshToonMaterial({ map: sandTex(60, 20), gradientMap: GRAD, color: 0x8a96b0 })); m.receiveShadow = true; return m; };
function march(cr, N, t, o) { for (let i = 0; i < N; i++) { const c = o.c[i]; const x = ((c.x0 + t * c.sp * 1.0) % o.len + o.len) % o.len + o.x0; cr.userData.set(i, x, 0.03 * Math.abs(Math.sin(t * 6 + i)), c.z, Math.PI / 2 + (c.ry || 0), (c.s) * (o.vis(i)), 0, 0); } cr.userData.done(); }
function mkMarch(N, seed, zr = 9, kids = 0.0) { const R = rnd(seed); return Array.from({ length: N }, (_, i) => ({ x0: R() * 160, z: (R() - .5) * 2 * zr, sp: 1.1 + R() * 0.5, s: i % 3 === 0 ? 0.68 : (0.92 + R() * 0.2), ry: (R() - .5) * 0.2 })); }

reg('red_cross', () => {
  const g = new THREE.Group(); const e = MOONLIT(); const sb = seabed(g); g.add(sb);
  const wl = [-1, 1].map(s => { const w = waterWall(320, 30, 8); w.position.set(30, 0, s * 17); g.add(w); return w; }); const mn = moon(9); mn.position.set(260, 55, -40); g.add(mn);
  const R = rnd(2); for (let i = 0; i < 80; i++) { const s = Sph(0.4, new THREE.MeshBasicMaterial({ color: 0xdde6ff, fog: false }), 1, 1, 1, 5); s.position.set(-100 + R() * 400, 40 + R() * 60, -150); s.userData.noShadow = true; g.add(s); }
  const N = 700; const cr = makeCrowd(N, 5, [0xc8b898, 0xb89868, 0x8a6a4a, 0x6a8a9a, 0xa05a4a, 0xd8d0c0]); g.add(cr); const C = mkMarch(N, 9, 10);
  return { group: g, env: e,
    cam: camRig([[0, [-26, 2.8, 4], [30, 4, 0], 46], [[0, 0.9], [-20, 3.0, 6], [34, 4, 0], 46], [[1, 0.3], [8, 6, 20], [30, 3, 0], 46], [[1, 0.9], [14, 7, 20], [34, 3, 0], 46], [[2, 0.3], [-10, 18, 40], [26, 3, 0], 50], [[2, 1.0], [-6, 26, 44], [30, 2, 0], 50]]),
    update(lt, u, dur, t, B) { wl.forEach(w => w.userData.tick(t)); mn.position.y = 55 + 0.5 * Math.sin(t * 0.3);
      march(cr, N, t, { c: C, len: 150, x0: -50, vis: (i) => 1.5 * (i < 240 ? easeOB((lt - 0.1 - i * 0.003) / 0.5) : i < 460 ? easeOB((lt - B[1] + 0.3 - (i - 240) * 0.003) / 0.5) : easeOB((lt - B[2] - (i - 460) * 0.003) / 0.5)) }); },
    anchors: { crowd: fixed(30, 7, 0), men: fixed(14, 5, 3), fam: fixed(40, 4, -4) } };
});

const ORDER = [...Array(25).keys()].sort((a, b) => (Math.abs((a % 5) - 2) + Math.abs(Math.floor(a / 5) - 2)) - (Math.abs((b % 5) - 2) + Math.abs(Math.floor(b / 5) - 2)) || a - b);
reg('red_plain', () => {
  const g = new THREE.Group(); const eA = env(DUSK, { key: { ...DUSK.key, ext: 260, target: [200, 0, 0], k: 2.0, dir: [0.4, 0.8, 0.6], far: 800, map: 4096 } }); eA.sunDir = [-0.5, 0.1, -1]; eA.fog = { color: 0xf0b074, near: 400, far: 2200 }; const eN = MOONLIT(); eN.key.ext = 260; eN.fog = { color: 0x1c2a48, near: 200, far: 1400 }; const e = JSON.parse(JSON.stringify(eA));
  const gnd = new THREE.Mesh(new THREE.PlaneGeometry(3000, 1500).rotateX(-Math.PI / 2), new THREE.MeshToonMaterial({ map: sandTex(150, 75), gradientMap: GRAD })); gnd.receiveShadow = true; g.add(gnd);
  const road = new THREE.Mesh(new THREE.PlaneGeometry(1500, 14).rotateX(-Math.PI / 2), mat(0xb89868)); road.position.set(780, 0.05, 0); g.add(road);
  const sts = []; for (let i = 0; i < 25; i++) { const s = stadium(30); const gx = (i % 5) - 2, gz = Math.floor(i / 5) - 2; s.position.set(gx * 85, 0, gz * 85); g.add(s); sts.push(s); }
  const NC = 5000; const col = makeCrowd(NC, 6, [0xc8b898, 0xb89868, 0x8a6a4a, 0x6a8a9a, 0xa05a4a, 0xd8d0c0]); g.add(col); const R = rnd(4);
  const clock = stopwatch(14); clock.position.set(300, 16, -26); clock.rotation.y = -0.5; g.add(clock);
  const mn = moon(30); mn.position.set(900, 160, -300); g.add(mn); const Rr = rnd(3); for (let i = 0; i < 60; i++) { const s = Sph(1.2, new THREE.MeshBasicMaterial({ color: 0xdde6ff, fog: false }), 1, 1, 1, 5); s.position.set(-200 + Rr() * 1200, 120 + Rr() * 180, -500); s.userData.noShadow = true; g.add(s); }
  shade(g);
  return { group: g, env: e,
    cam: camRig([[0, [-60, 16, 80], [0, 8, 0], 44], [[0, 0.6], [-80, 26, 100], [0, 10, 0], 44], [[0, 1.0], [-20, 120, 330], [0, 0, 0], 50], [[1, 0.15], [262, 5, 12], [900, 6, 0], 52], [[1, 0.9], [265, 6, 12], [900, 6, 0], 52], [[2, 0.3], [284, 10, 8], [300, 12, -24], 44], [[2, 1.0], [288, 11, 8], [300, 13, -24], 44]]),
    update(lt, u, dur, t, B) { sts.forEach((s, i) => { const rank = ORDER.indexOf(i); const k = i === 12 ? 1 : easeO((lt - 0.4 - rank * 0.11) / 0.45); s.visible = k > 0.002; s.scale.setScalar(Math.max(0.0001, i === 12 ? 1 : k)); });
      const cl = lt > B[1] - 0.3; col.visible = cl; if (cl) { const rows = 500; for (let r = 0; r < rows; r++) for (let k = 0; k < 10; k++) { const i = r * 10 + k; if (i >= NC) break; const x = 262 + r * 1.3 + 0.0, z = -6.0 + k * 1.3 + 0.2 * Math.sin(r * 3.1 + k); col.userData.set(i, x, 0.04 * Math.abs(Math.sin(t * 6 + r * 0.7)), z, Math.PI / 2, lt - B[1] + 0.2 > r * 0.004 ? 1 : 0.0001); } col.userData.done(); }
      clock.visible = lt > B[2] - 0.4; clock.userData.setSec(60 * ease((lt - B[2]) / 3.0) * 2 + t * 6); mixEnv(e, eA, eN, ease((lt - B[2] + 0.6) / 2.0)); },
    anchors: { stad: () => V(0, 40, 0), bigGrid: () => V(0, 70, 0), colA: () => V(560, 14, 0), clockA: () => clock.localToWorld(V(0, 1.0, 0)), colEnd: () => V(900, 4, 0) } };
});

reg('red_front', () => {
  const g = new THREE.Group(); const e = env(DUSK, { key: { ...DUSK.key, ext: 90, target: [40, 0, -10], dir: [0.3, 0.8, 0.8], k: 2.0, far: 400, map: 4096 } }); e.sunDir = [0.3, 0.1, -1]; e.fog = { color: 0xf0b074, near: 120, far: 1500 };
  const gnd = new THREE.Mesh(new THREE.PlaneGeometry(2600, 400).rotateX(-Math.PI / 2), new THREE.MeshToonMaterial({ map: sandTex(130, 20), gradientMap: GRAD })); gnd.position.set(500, 0, -10); gnd.receiveShadow = true; g.add(gnd); const sea = makeWater(2600, 80, 0x3a86b8); sea.position.set(500, -0.2, -240); g.add(sea);
  const R = rnd(5); for (let i = 0; i < 6; i++) { const c = makeCloud(i + 3, 0xffb482, 2 + R()); c.position.set(-100 + i * 300, 80 + R() * 40, -450); g.add(c); }
  const row = makeCrowd(1000, 7, [0xc8b898, 0xb89868, 0x8a6a4a, 0x6a8a9a, 0xa05a4a]); g.add(row); const F0 = (() => { const f = Cyl(0.08, 0.08, 5, mat(0xc8402a), 6); f.position.set(0, 2.5, 2); const fl = Box(1.4, 0.9, 0.05, mat(0xc8402a), 0.02); fl.position.set(0.7, 4.4, 2); const gg = new THREE.Group(); gg.add(f, fl); return gg; })(); g.add(F0); const F1 = F0.clone(); F1.position.x = 1000; g.add(F1);
  const tents = Array.from({ length: 12 }, (_, i) => { const tt = tent(1.5, i % 3 ? 0xe8dcc0 : 0xc8a070); tt.position.set(8 + (i % 6) * 10 + (i > 5 ? 4 : 0), 0, i > 5 ? -26 : -16); g.add(tt); return tt; });
  const kin = makeCrowd(70, 11, [0xd8503a, 0x3a8a5a, 0xe0a030, 0x4a7bd0, 0xa05a9a]); g.add(kin); const KR = rnd(12); const kp = Array.from({ length: 70 }, (_, i) => { const tix = Math.floor(i / 6); return [8 + (tix % 6) * 10 + (tix > 5 ? 4 : 0) + (KR() - .5) * 4, tix > 5 ? -22 : -12, KR() * 6]; });
  const band = makeCrowd(30, 13, [0xc8b898, 0xb89868, 0x8a6a4a, 0x6a8a9a]); g.add(band); const BR = rnd(2);
  shade(g);
  return { group: g, env: e,
    cam: camRig([[0, [-24, 3.2, 8], [300, 4, 0], 48], [[0, 0.9], [-18, 3.6, 10], [300, 4, 0], 48], [[1, 0.3], [30, 4, 8], [40, 2, -18], 46], [[1, 0.9], [36, 5, 10], [40, 2.5, -20], 46], [[2, 0.3], [30, 3, -20], [30, 1.6, -44], 44], [[2, 1.0], [30, 3.4, -22], [30, 1.6, -46], 44]]),
    update(lt, u, dur, t, B) { const g7 = ease((lt - 0.2) / 2.0), g8 = lt > B[1] - 0.2 ? 1 : 0; for (let i = 0; i < 1000; i++) { const vis = (i / 1000 < g7 ? 1 : 0.0001) * (lt > B[1] + 0.1 ? 0.0001 : 1); row.userData.set(i, i * 1.0 + 0.5, 0, 0.3 * Math.sin(i * 1.7), Math.PI / 2, vis * (0.9 + 0.1 * Math.sin(i))); } row.userData.done();
      tents.forEach((tt, i) => { popIn(tt, lt, B[1] + 0.1 + i * 0.1, 1.5, 0.4); }); for (let i = 0; i < 70; i++) { const p = kp[i]; kin.userData.set(i, p[0], 0, p[1] + 3 + p[2] * 0.3, p[2], (lt > B[1] + 0.5 + i * 0.01 && lt < B[2] + 0.2 ? 1 : 0.0001) * 0.9); } kin.userData.done();
      for (let i = 0; i < 30; i++) { const s = easeOB((lt - B[2] - 0.2 - i * 0.04) / 0.4); band.userData.set(i, 24 + (i % 6) * 1.4 + 0.1 * Math.sin(t + i), 0, -46 + Math.floor(i / 6) * 1.4, 0.5 * Math.sin(i), s * 0.95); } band.userData.done(); },
    anchors: { f0: fixed(0, 4, 2), f1: fixed(1000, 4, 2), front: fixed(200, 3, 0), clans: fixed(40, 6, -16), bandA: fixed(27, 3, -45) } };
});

reg('red_reeds', () => {
  const g = new THREE.Group(); const eA = env(DUSK, { key: { ...DUSK.key, ext: 80, target: [0, 0, -10], dir: [0.4, 0.7, 0.6], k: 1.9, far: 300, map: 4096 } }); eA.sunDir = [-0.4, 0.06, -1]; eA.sky = { ...DUSK.sky, top: 0x6a7ab0, mid: 0xf0a090, hor: 0xffd8b0 }; eA.fog = { color: 0xf4c8b0, near: 80, far: 700 };
  const eG = JSON.parse(JSON.stringify(eA)); eG.sky = { ...eG.sky, top: 0x6a7080, mid: 0x9a9aa0, hor: 0xc8c4c0 }; eG.fog = { color: 0xa8a8aa, near: 40, far: 420 }; eG.key.k = 1.2; eG.hemi.k = 0.9; const eN = MOONLIT(); const e = JSON.parse(JSON.stringify(eA));
  const gnd = new THREE.Mesh(new THREE.PlaneGeometry(900, 500).rotateX(-Math.PI / 2), new THREE.MeshToonMaterial({ map: sandTex(60, 30), gradientMap: GRAD })); gnd.receiveShadow = true; g.add(gnd);
  const pond = new THREE.Mesh(new THREE.CircleGeometry(60, 40).rotateX(-Math.PI / 2), new THREE.MeshToonMaterial({ color: 0x4a9a9a, gradientMap: GRAD, emissive: 0x0a3a3a, emissiveIntensity: 0.5 })); pond.position.set(0, 0.06, -40); g.add(pond);
  const rd = reeds(300, [140, 40], 4); rd.position.set(0, 0, -28); g.add(rd); const rd2 = reeds(180, [30, 24], 9); rd2.position.set(-30, 0, 12); g.add(rd2);
  const fp = footprints(60, 5); fp.position.set(-20, 0, 14); g.add(fp);
  const wl = [-1, 1].map(s => { const w = waterWall(260, 30, 8); w.position.set(30, -34, s * 17); g.add(w); return w; }); const mn = moon(9); mn.position.set(220, 55, -40); g.add(mn); mn.visible = false;
  const N = 220; const cr = makeCrowd(N, 15, [0x120e0c, 0x1a1210, 0x0c0a08]); g.add(cr); const C = mkMarch(N, 21, 8);
  const p1 = makePill('TWO MILLION', 0xc8382e, 15, 3.2), p2 = makePill('SMALL BAND', 0x2f9a56, 13, 3.2); g.add(p1, p2); shade(g);
  return { group: g, env: e,
    cam: camRig([[0, [-30, 5.0, 40], [0, 3.0, -24], 46], [[0, 0.9], [-24, 5.0, 38], [0, 3.0, -26], 46], [[1, 0.3], [-18, 4.0, 14], [24, 0.6, 14], 44], [[1, 0.9], [-10, 4.2, 15], [30, 0.6, 14], 44], [[2, 0.2], [-34, 9.0, 4], [60, 6, 0], 48], [[2, 1.0], [-30, 10.0, 8], [60, 6, 0], 48]]),
    update(lt, u, dur, t, B) { const k1 = ease((lt - B[1] + 0.4) / 1.0), k2 = ease((lt - B[2] + 0.4) / 1.4); mixEnv(e, eA, eG, k1); if (k2 > 0) mixEnv(e, eG, eN, k2); mn.visible = k2 > 0.3; pond.material.color.setHex(0x4a9a9a);
      fp.userData.m.opacity = 0.6 * (lt < B[1] ? 0.0 : 1 - ease((lt - B[1] - 0.8) / 2.4)) * (lt < B[2] ? 1 : 0); wl.forEach((w, i) => { w.position.y = lerp(-34, 0, ease((lt - B[2] - 0.3) / 1.6)); w.userData.tick(t); });
      march(cr, N, t, { c: C, len: 150, x0: -40, vis: (i) => easeOB((lt - B[2] - 0.8 - i * 0.004) / 0.5) });
      const pop = (t0) => easeOB((lt - t0) / 0.5); pillFront(p1, 0, 3.7, 0.2 * pop(B[2] + 2.0), 0.02 * Math.sin(t * 1.3), 14); pillFront(p2, 0, 2.1, 0.2 * pop(B[2] + 2.5), -0.02 * Math.sin(t * 1.1), 14); },
    anchors: { reedA: fixed(0, 6, -28), prints: fixed(10, 1.2, 14) } };
});
