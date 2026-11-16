// samson_temple: Philistine temple with two central wooden pillars on stone bases; dusk (story), dig site (archaeology + reconstruction + collapse), coast (question).
import { THREE, V, mat, glow, woodMat, Sph, Box, Cyl, Cap, Cone, between, shade, rnd, lerp, sandTex, GRAD, poseArms, makeWater, makeMountain, makeCloud, tube } from './kit.js';
import { makePill } from './props.js';
import { REG, reg, ease, easeO, easeOB, at, fixed, camRig, env, mixEnv, pillFront, popIn, DUSK, DAY } from './world.js';
import { person } from './folk.js';
import { makeCrowd, dustPuffs } from './things2.js';
import { rock, patch } from './things.js';

const PX = 1.15, PH = 5.0;                      // pillar axis offset (2.4 m apart), pillar height
function buildTemple(g, { crowdN = 220 } = {}) {
  const T = { g: new THREE.Group() }; g.add(T.g); const brick = woodMat(2.2, 1.1, [196, 150, 100], { seed: 61 }), stone = mat(0x9a8e7e), wood = woodMat(1.0, 0.5, [140, 92, 50], { seed: 62 }), plank = woodMat(2, 0.6, [170, 120, 70], { seed: 63 });
  const walls = new THREE.Group(); T.walls = walls; T.g.add(walls);
  const bw = Box(13, 5.6, 0.8, brick, 0.1); bw.position.set(0, 2.8, -5); walls.add(bw); for (const s of [-1, 1]) { const sw = Box(0.8, 5.6, 10.8, brick, 0.1); sw.position.set(s * 6.4, 2.8, 0); walls.add(sw); }
  const fl = Box(13.6, 0.3, 11, mat(0xc8a876), 0.05); fl.position.set(0, 0.15, 0); T.g.add(fl);
  T.bases = [-1, 1].map(s => { const b = Cyl(0.62, 0.72, 0.4, stone, 20); b.position.set(s * PX, 0.5, 0); T.g.add(b); return b; });
  T.pillars = [-1, 1].map(s => { const p = new THREE.Group(); p.position.set(s * PX, 0.7, 0); const c = Cyl(0.34, 0.4, PH, wood, 16); c.position.y = PH / 2; p.add(c); const cap = Box(0.9, 0.3, 0.9, wood, 0.06); cap.position.y = PH + 0.1; p.add(cap); T.g.add(p); return p; });
  // roof halves (hinged at the outer walls) = beams + slab + parapet
  T.roof = [-1, 1].map(s => { const h = new THREE.Group(); h.position.set(s * 6.4, PH + 0.9, 0); const inner = new THREE.Group(); inner.position.x = -s * 3.2; h.add(inner);
    const sl = Box(6.4, 0.5, 11, plank, 0.06); sl.position.y = 0.45; inner.add(sl); const bm = Box(6.4, 0.5, 0.5, wood, 0.06); bm.position.y = 0.0; inner.add(bm); for (let z = -4.5; z <= 4.5; z += 1.5) { const b2 = Box(6.4, 0.3, 0.3, wood, 0.05); b2.position.set(0, 0.1, z); inner.add(b2); }
    const pf = Box(6.4, 0.5, 0.35, brick, 0.05); pf.position.set(0, 0.95, 5.3); inner.add(pf); T.g.add(h); h.userData.inner = inner; return h; });
  T.crowd = makeCrowd(crowdN, 12); T.g.add(T.crowd); T.crowdN = crowdN; const R = rnd(33); T.cpos = Array.from({ length: crowdN }, () => ({ x: (R() - .5) * 11, z: (R() - .5) * 9.4, ry: R() * 6.28, s: 0.82 + R() * 0.3, d: R(), vy: 0, y: 0, vx: (R() - .5), vz: (R() - .5), tz: 0, tx: 0 }));
  T.dust = dustPuffs(18); T.g.add(T.dust);
  // state setters
  T.setRoof = (k, lift = 0) => { T.roof.forEach((h, i) => { const s = i ? 1 : -1; h.rotation.z = -s * -0.0; h.rotation.z = (i ? 1 : -1) * k * 0.0; }); };
  T.collapse = (k) => { const a = k * 0.34; T.roof[0].rotation.z = -a * 1.0 * -1; T.roof[1].rotation.z = a * -1; T.roof[0].rotation.z = -a; T.roof[1].rotation.z = a; T.roof[0].rotation.z *= -1; T.roof[1].rotation.z *= -1; T.roof[0].position.y = PH + 0.9 - k * 0.0; T.pillars.forEach((p, i) => { const s = i ? 1 : -1; p.rotation.z = -s * k * 0.55; p.position.x = s * (PX + k * 0.5); p.position.y = 0.7 - k * 0.25; }); };
  T.placeCrowd = (vis, k = 0, lt = 0) => { const n = T.crowdN; for (let i = 0; i < n; i++) { const c = T.cpos[i]; const sc = c.s * Math.max(0, Math.min(1, (vis * 1.5 - c.d * 0.5))); const sideI = c.x < 0 ? 0 : 1; const roofY = PH + 0.9 + 0.7 + 0.0;
      let y = roofY, x = c.x, z = c.z, tz = 0, tx = 0; if (k > 0) { const kk = Math.max(0, k * 1.3 - c.d * 0.3); const a = Math.min(kk, 1) * 0.34; const sgn = sideI ? 1 : -1; y = roofY - Math.abs(c.x) * 0.0 - (6.4 - Math.abs(c.x)) * Math.sin(a) * 0.0; const rel = 6.4 - Math.abs(c.x); y = roofY - rel * Math.sin(a) - 0.0; x = c.x + sgn * (0); tz = -sgn * a * 0; const fall = Math.max(0, kk - 0.55) * 3.0; y -= fall * fall * 6.0; tz = (c.vx > 0 ? 1 : -1) * fall * 2.5; tx = fall * 2.0 * c.vz; x += c.vx * fall * 3.0; z += c.vz * fall * 2.0; if (y < 0.4) { y = 0.4; } }
      T.crowd.userData.set(i, x, y, z, c.ry, sc, tz, tx); } T.crowd.userData.done(); };
  T.hideAll = () => { T.crowd.visible = false; };
  return T;
}
function samson(h = 1.9) { const p = person({ h, shirt: 0xb89868, pants: 0xb89868, hair: 0x1a0e08, skin: 0xe0a878 }); const hd = p.userData.parts.head; const band = new THREE.Mesh(new THREE.TorusGeometry(0.26, 0.05, 8, 24), mat(0xf0ead8)); band.rotation.x = Math.PI / 2; band.position.set(0, 0.04, 0); hd.add(band); const front = Box(0.34, 0.12, 0.06, mat(0xf0ead8), 0.02); front.position.set(0, 0.04, 0.26); hd.add(front);
  const hairL = Cap(0.1, 0.5, mat(0x1a0e08), 8); hairL.position.set(0, -0.22, -0.24); hd.add(hairL); for (const s of [-1, 1]) { const hl = Cap(0.07, 0.4, mat(0x1a0e08), 8); hl.position.set(s * 0.2, -0.25, -0.12); hd.add(hl); }
  // strained face: flip the smile into a downturned, gritted mouth, brows pulled in and down
  hd.children.forEach(c => { if (c.geometry && c.geometry.type === 'TorusGeometry' && Math.abs(c.geometry.parameters.arc - Math.PI) < 0.01) { c.rotation.z = 0; c.position.y = -0.14; c.scale.set(1.15, 1.0, 1); } });
  for (const s of [-1, 1]) { const br = Box(0.15, 0.035, 0.05, mat(0x1a0e08), 0.01); br.position.set(s * 0.1, 0.13, 0.27); br.rotation.z = s * -0.45; hd.add(br); }
  const grit = Box(0.1, 0.03, 0.03, mat(0xf4efe6), 0.01); grit.position.set(0, -0.125, 0.255); hd.add(grit);
  // both palms on the pillars: left arm swings out with -z, right arm with +z (poseArms uses the same sign for both otherwise)
  p.userData.spread = (k) => { const a = 0.12 * (1 - k) + 1.5 * k; poseArms(p, [0, -a, 0.0], [0, a, 0.0]); }; p.userData.spread(0); return p; }
function sunSky(e, mid) { return e; }

reg('sam_dusk', () => {
  const g = new THREE.Group(); const e = env(DUSK, { key: { ...DUSK.key, ext: 30, target: [0, 3, 0], dir: [0.3, 0.7, 1.0], k: 2.0 } }); e.sunDir = [-0.2, 0.12, -1]; e.fog = { color: 0xf0b074, near: 60, far: 600 };
  const gnd = new THREE.Mesh(new THREE.PlaneGeometry(800, 800).rotateX(-Math.PI / 2), new THREE.MeshToonMaterial({ map: sandTex(50, 50), gradientMap: GRAD })); gnd.receiveShadow = true; g.add(gnd);
  const R = rnd(4); for (let i = 0; i < 8; i++) { const m = makeMountain(25 + R() * 30, 50 + R() * 40, 90 + i, 0x9a6a50, 0xd8a870, 0.0); m.position.set(-200 + i * 60, 0, -190 - R() * 40); g.add(m); }
  const T = buildTemple(g); const S = samson(1.9); S.position.set(0, 0.3, 0.05); g.add(S);
  const chain = tube([V(-0.8, 1.15, 0.45), V(-0.3, 0.85, 0.7), V(0.3, 0.85, 0.7), V(0.8, 1.15, 0.45)], 0.025, mat(0x6a6e74), 20); chain.visible = false; g.add(chain);
  const pf = Box(0.01, 0.01, 0.01, mat(0xffffff)); g.add(pf);
  return { group: g, env: e,
    cam: camRig([[0, [-9, 4.5, 24], [0, 3.2, 0], 44], [[0, 0.9], [-7, 4.2, 22], [0, 3.4, 0], 44], [[1, 0.5], [3, 9, 26], [0, 5.8, 0], 46], [[1, 0.95], [5, 10, 24], [0, 6.2, 0], 46], [[2, 0.2], [0.4, 2.2, 9], [0, 1.7, 0], 38], [[2, 0.9], [0.2, 2.0, 7.6], [0, 1.7, 0], 38], [[3, 0.3], [0, 1.9, 8.2], [0, 1.7, 0], 40], [[3, 1.0], [0, 1.9, 7.4], [0, 1.7, 0], 40]]),
    update(lt, u, dur, t, B) { T.placeCrowd(ease((lt - B[1] - 0.2) / 1.6), 0); chain.visible = lt > B[2] - 0.1 && lt < B[2] + 1.6; S.userData.spread(ease((lt - B[2] - 0.6) / 1.2)); S.position.y = 0.3 + 0.01 * Math.sin(t * 2); },
    anchors: { roof: fixed(0, PH + 2.4, 0), headS: at(S, 0, 1.9, 0), gapL: fixed(-PX + 0.34, 1.7, 0.0), gapR: fixed(PX - 0.34, 1.7, 0.0), baseL: fixed(-PX + 0.4, 0.75, 0.5), baseR: fixed(PX - 0.4, 0.75, 0.5) } };
});

reg('sam_dig', () => {
  const g = new THREE.Group(); const e = env(DAY, { key: { ...DAY.key, ext: 30, target: [0, 3, 0], dir: [0.5, 0.8, 0.9], k: 2.2 } }); e.fog = { color: 0xf0d8b0, near: 60, far: 600 }; e.sky = { ...e.sky, top: 0x6a98d4, mid: 0xcfdcea, hor: 0xffe8c8 }; e.sunDir = [-0.5, 0.4, -1]; const eC = JSON.parse(JSON.stringify(e));
  const gnd = new THREE.Mesh(new THREE.PlaneGeometry(800, 800).rotateX(-Math.PI / 2), new THREE.MeshToonMaterial({ map: sandTex(50, 50), gradientMap: GRAD })); gnd.receiveShadow = true; g.add(gnd);
  const R = rnd(8); for (let i = 0; i < 8; i++) { const m = makeMountain(22 + R() * 25, 50 + R() * 40, 95 + i, 0xa8805e, 0xe0b888, 0.0); m.position.set(-200 + i * 60, 0, -190 - R() * 40); g.add(m); }
  const T = buildTemple(g); const S = samson(1.9); S.position.set(0, 0.3, 0.05); g.add(S);
  const dig = new THREE.Group(); g.add(dig); for (const [x, z, ry] of [[-2.2, 3.4, 0.6], [2.6, 3.0, -0.8]]) { const a = person({ h: 1.7, shirt: 0xe8e0c8, pants: 0x6a5a40, hair: 0x4a2c18, hat: 0xe8c070 }); a.position.set(x, 0, z); a.rotation.set(0.5, ry, 0); dig.add(a); poseArms(a, [-1.2, 0.1, 0.3], [-1.2, 0.1, 0.3]); a.userData.arm = true; }
  const brush = Cyl(0.02, 0.02, 0.22, mat(0x6a4020), 6); brush.position.set(-1.7, 0.45, 2.3); brush.rotation.z = 1.0; dig.add(brush); const bs = Cone(0.04, 0.1, mat(0xe0d0a0), 8); bs.position.set(-1.78, 0.36, 2.3); bs.rotation.z = 1.0 + Math.PI; dig.add(bs);
  for (const [x, z] of [[-5, 3.5], [5, 3.5], [-5, 7], [5, 7]]) { const st = Cyl(0.05, 0.05, 0.6, mat(0xc8402a), 6); st.position.set(x, 0.3, z); dig.add(st); } for (const [x1, z1, x2, z2] of [[-5, 3.5, 5, 3.5], [-5, 7, 5, 7], [-5, 3.5, -5, 7], [5, 3.5, 5, 7]]) between(V(x1, 0.5, z1), V(x2, 0.5, z2), 0.012, mat(0xe8e0d0), dig);
  const crate = Box(1.0, 0.6, 0.7, woodMat(0.5, 0.2, [150, 100, 58], { seed: 5 }), 0.04); crate.position.set(-4.4, 0.3, 5); dig.add(crate); shade(dig);
  return { group: g, env: e,
    cam: camRig([[0, [-4, 3.4, 12], [0, 1.0, 1], 42], [[0, 0.9], [-3, 3.0, 11], [0, 0.9, 1], 42], [[1, 0.2], [6, 6.5, 19], [0, 3.2, 0], 46], [[1, 0.9], [9, 7.5, 19], [0, 3.6, 0], 46], [[2, 0.3], [0.6, 2.4, 8], [0, 1.0, 0.3], 36], [[2, 0.9], [0.2, 2.2, 7.4], [0, 0.9, 0.3], 36], [[3, 0.3], [4.0, 3.4, 13], [0, 3.8, 0], 44], [[3, 0.9], [3.5, 3.4, 12.5], [0, 3.8, 0], 44], [[4, 0.1], [11, 6.5, 22], [0, 4.5, 0], 46], [[4, 1.0], [13, 8.5, 20], [0, 3.5, 0], 46]]),
    update(lt, u, dur, t, B) {
      const rb = ease((lt - B[1] - 0.2) / 1.4); T.walls.scale.y = lerp(0.1, 1, rb); T.pillars.forEach((p, i) => { p.scale.y = Math.max(0.0001, easeOB((lt - B[1] - 0.5 - i * 0.2) / 0.8)); }); T.roof.forEach((h, i) => { const d = 1 - easeO((lt - B[1] - 1.2 - i * 0.15) / 1.0); h.position.y = PH + 0.9 + d * 10; h.visible = lt > B[1] + 1.0; });
      dig.children.forEach(c => { if (c.userData.arm) { poseArms(c, [-1.2 + 0.2 * Math.sin(t * 9), 0.1, 0.3], [-1.2 + 0.2 * Math.sin(t * 9 + 2), 0.1, 0.3]); } }); dig.visible = lt < B[3] + 1.0;
      const kc = ease((lt - B[3] - 0.9) / 2.2); const sv = lt > B[3] + 0.2; S.visible = sv; S.userData.spread(ease((lt - B[3] - 0.2) / 0.8) * (1 - 0.35 * ease((lt - B[3] - 1.0) / 0.9)) + 0.0); S.position.set(0, 0.3, 0.05);
      T.collapse(kc * (lt > B[3] + 0.6 ? 1 : 0)); T.placeCrowd(lt > B[3] + 0.8 ? 1 : 0, lt > B[4] - 0.2 ? Math.max(kc, 0) : 0);
      T.dust.userData.update(kc > 0.05 ? (kc - 0.05) * 1.1 : -1, [0, 1, 4.5], 12, 5, 1.7);
      if (lt < B[3] + 0.8) T.crowd.visible = false; else T.crowd.visible = true;
    },
    anchors: { stoneL: fixed(-PX, 0.72, 0.6), stoneR: fixed(PX, 0.72, 0.6), roofA: fixed(0, PH + 1.8, 0), brushA: () => V(-1.7, 0.5, 2.3), pillarTop: fixed(0, PH * 0.6, 0.5), roofC: fixed(2, PH + 2, 2) } };
});

reg('sam_end', () => {
  const g = new THREE.Group(); const e = env(DUSK, { key: { ...DUSK.key, ext: 40, target: [0, 2, 0], dir: [-0.2, 0.55, 1.0], k: 1.8 } }); e.sunDir = [0.0, 0.07, -1]; e.fog = { color: 0xf0a868, near: 60, far: 700 };
  const sand = new THREE.Mesh(new THREE.PlaneGeometry(500, 300).rotateX(-Math.PI / 2), new THREE.MeshToonMaterial({ map: sandTex(40, 24), gradientMap: GRAD })); sand.position.set(0, 0, 0); sand.receiveShadow = true; g.add(sand);
  const sea = makeWater(900, 90, 0x2a78a8); sea.position.set(0, -0.1, -430); g.add(sea);
  const R = rnd(6); for (let i = 0; i < 4; i++) { const c = makeCloud(i + 2, 0xffb482, 2.0 + R()); c.position.set(-300 + i * 200, 80 + R() * 40, -520); g.add(c); }
  const bases = [-1, 1].map(s => { const b = Cyl(0.62, 0.72, 0.4, mat(0x9a8e7e), 20); b.position.set(s * PX, 0.2, 0); g.add(b); const p = Cyl(0.34, 0.4, PH, woodMat(1.0, 0.5, [140, 92, 50], { seed: 62 }), 16); p.position.set(s * PX, 0.4 + PH / 2, 0); g.add(p); return p; });
  const S = samson(1.9); S.position.set(0, 0.05, 0.05); S.rotation.y = 0.0; g.add(S); S.userData.spread(1);
  for (let i = 0; i < 6; i++) { const rk = rock(0.4 + R() * 0.7, 0x8a6a4a, i + 3); rk.position.set((R() - .5) * 30, 0, (R() - .5) * 10 + 6); g.add(rk); }
  const q = new THREE.Group(); const qm = new THREE.Mesh(new THREE.TorusGeometry(1.2, 0.38, 12, 24, Math.PI * 1.5), mat(0xffc42e, { e: 0x6a4a00, ei: 0.4 })); qm.rotation.z = -0.6; q.add(qm); const qd = Sph(0.4, mat(0xffc42e, { e: 0x6a4a00, ei: 0.4 })); qd.position.set(0, -2.2, 0); q.add(qd); q.position.set(-9, 6, 4); g.add(q);
  const p1 = makePill('LEGEND', 0xc8382e, 9, 3.2), p2 = makePill('MEMORY', 0x2f9a56, 9, 3.2); g.add(p1, p2);
  shade(g);
  return { group: g, env: e,
    cam: camRig([[0, [-24, 3.5, 16], [-10, 5, -40], 44], [[0, 0.9], [-20, 3.8, 15], [-8, 5, -40], 44], [[1, 0.4], [-5, 5, 22], [0, 3.0, 0], 44], [[1, 0.95], [3, 5.5, 24], [0, 3.2, 0], 44], [[2, 0.2], [0.0, 1.6, 11], [0, 2.8, -6], 42], [[2, 1.0], [0.0, 1.5, 9.5], [0, 3.2, -10], 42]]),
    update(lt, u, dur, t, B) { q.rotation.y = 0.6 * Math.sin(t * 1.1); q.position.y = 6 + 0.2 * Math.sin(t * 1.7); q.visible = lt < B[2]; sea.userData.update(t, 0.5, 0.7, 1.0);
      const pop = (t0) => easeOB((lt - t0) / 0.5); pillFront(p1, -1.3, 0.55 + 0.03 * Math.sin(t * 1.7), 0.26 * pop(B[2] + 1.0), 0.02 * Math.sin(t * 1.3), 14); pillFront(p2, 1.3, 0.55 + 0.03 * Math.sin(t * 1.5 + 1), 0.26 * pop(B[2] + 1.6), -0.02 * Math.sin(t * 1.1), 14); },
    anchors: { q: () => q.position.clone().add(V(0, -1, 0)), shore: fixed(-8, 0.2, -30), gap: fixed(0, 2.5, 0.2) } };
});
