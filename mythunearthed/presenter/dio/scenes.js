// The 13 diorama scenes of topics/ark_size. Each builder returns {group, env, cam(lt,u,dur), update(lt,u,dur,t), anchors:{name:()=>Vector3}}
import { THREE, V, clamp, sstep, lerp, mat, glow, woodMat, put, Sph, Box, Cyl, Cap, Cone, Pln, between, shade, tube, rnd, makeSky, makeWater, makeRain, makeJet, makePerson, poseArms, makeGiraffe, makeElephant, makeLion, makeSheep, makeCloud, makeMountain, sandTex, canvasTex, GRAD } from './kit.js';
import { makeArk, makeArkCutaway, makeCargoShip, makeTitanic, makeSchooner, makeToyBoat, makeField, makeForearm, makeRuler, makeBlueprint, makePill, makeSearchlight, slab } from './props.js';

const ease = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
const easeO = (x) => { x = clamp(x); return 1 - Math.pow(1 - x, 3); };
const mix3 = (a, b, u) => [lerp(a[0], b[0], u), lerp(a[1], b[1], u), lerp(a[2], b[2], u)];
const at = (obj, x, y, z) => () => obj.localToWorld(V(x, y, z));
const fixed = (x, y, z) => () => V(x, y, z);

// ------------------------------------------------------------- environments
const DUSK = { sky: { top: 0x2c3c78, mid: 0xe0803c, hor: 0xffc27a, below: 0x6a4a3a, sunCol: 0xfff0c0, glowK: 0.3, glowP: 12, sunSize: 0.0016 }, sunDir: [-0.25, 0.09, -1],
  fog: { color: 0xf2b074, near: 160, far: 1000 }, hemi: { sky: 0xffdcb4, ground: 0x9a7050, k: 0.95 }, key: { color: 0xffe0b0, k: 2.2, dir: [0.5, 0.75, 0.8], target: [0, 0, 0], ext: 130, far: 500, map: 4096 }, rim: { color: 0xffa860, k: 1.0, dir: [-0.3, 0.3, -1] }, water: 0x1d6fae };
const STORM = { sky: { top: 0x1c2a44, mid: 0x6a5a68, hor: 0xe09a5c, below: 0x2a3a4a, sunCol: 0xffd9a0, glowK: 0.55, glowP: 10, sunSize: 0.0004 }, sunDir: [-0.2, 0.06, -1],
  fog: { color: 0x9a8078, near: 120, far: 700 }, hemi: { sky: 0xc8c8d8, ground: 0x70604c, k: 0.95 }, key: { color: 0xffd8b0, k: 1.7, dir: [0.5, 0.8, 0.8], target: [0, 0, 0], ext: 130, far: 500, map: 4096 }, rim: { color: 0xff9a58, k: 0.9, dir: [-0.3, 0.3, -1] }, water: 0x23556f };
const NIGHT = { sky: { top: 0x0e1832, mid: 0x2a3a62, hor: 0x8a6a78, below: 0x141c30, sunCol: 0xaab8ff, glowK: 0.2, glowP: 30, sunSize: 0.0 }, sunDir: [0.3, 0.3, -1],
  fog: { color: 0x2a3858, near: 80, far: 700 }, hemi: { sky: 0x7a90c8, ground: 0x2a2a44, k: 0.9 }, key: { color: 0xa8b8ff, k: 1.1, dir: [0.4, 0.8, 0.6], target: [0, 0, 0], ext: 140, far: 600, map: 2048 }, rim: { color: 0x7a8ad0, k: 0.8, dir: [-0.3, 0.3, -1] }, water: 0x1a3858 };
const WARMROOM = { sky: { top: 0x3a2418, mid: 0x5a3a24, hor: 0x7a5030, below: 0x2a1a10, sunCol: 0x000000, glowK: 0, glowP: 10, sunSize: 0 }, sunDir: [0, 1, 0],
  fog: { color: 0x4a2e1c, near: 6, far: 26 }, hemi: { sky: 0xffe2c0, ground: 0x9a6a44, k: 1.5 }, key: { color: 0xffe2b8, k: 2.6, dir: [0.4, 1.0, 0.7], target: [0, 0, 0], ext: 3, far: 30, map: 2048 }, rim: { color: 0xffb070, k: 0.7, dir: [-0.5, 0.4, -0.7] }, water: 0x2a6a98 };
const env = (b, o = {}) => JSON.parse(JSON.stringify(Object.assign({}, b, o)));

// ------------------------------------------------------------- shared world pieces
function seaWorld(g, e, { amp = 0.6, speed = 1, steep = 1, rain = 0, clouds = true, size = 1400 } = {}) {
  const w = makeWater(size, 120, e.water); g.add(w);
  let rn = null; if (rain) { rn = makeRain(1500, [70, 45, 70], 1.6, 0.5 * rain); g.add(rn); }
  if (clouds) { const R = rnd(9); for (let i = 0; i < 7; i++) { const c = makeCloud(i + 3, i % 2 ? 0xffb482 : 0xf6c8a0, 1.6 + R()); c.position.set((R() - .5) * 700, 70 + R() * 50, -300 - R() * 180); g.add(c); } }
  return { w, rn, amp, speed, steep };
}
function sandWorld(g) {
  const gnd = new THREE.Mesh(new THREE.PlaneGeometry(1600, 1600, 60, 60).rotateX(-Math.PI / 2), new THREE.MeshToonMaterial({ map: sandTex(60, 60), gradientMap: GRAD })); gnd.receiveShadow = true;
  const p = gnd.geometry.attributes.position; for (let i = 0; i < p.count; i++) { const x = p.getX(i), z = p.getZ(i); const r = Math.hypot(x, z); p.setY(i, r > 150 ? Math.sin(x * 0.01) * Math.cos(z * 0.012) * (r - 150) * 0.05 : 0); } gnd.geometry.computeVertexNormals(); g.add(gnd);
  const R = rnd(4); for (let i = 0; i < 9; i++) { const m = makeMountain(40 + R() * 70, 90 + R() * 80, 20 + i, 0xa07048, 0xd8a870, 0.0); m.position.set(-420 + i * 105 + R() * 40, 0, -520 - R() * 120); g.add(m); }
  for (let i = 0; i < 30; i++) { const rk = Sph(0.8 + R() * 1.6, mat(0x9a7a58, { flat: true }), 1, 0.6, 1, 6); const a = R() * 6.28, d = 40 + R() * 160; rk.position.set(Math.cos(a) * d, 0.3, Math.sin(a) * d); rk.castShadow = true; g.add(rk); }
  return gnd;
}
function scaffold(g, L, B, H, z) { // wooden scaffold along the long side
  const wm = mat(0x8a5a30), pm = woodMat(2, 0.6, [190, 130, 76]);
  for (let x = -L / 2 + 6; x <= L / 2 - 4; x += 12) {
    for (const zz of [z, z + 4]) { const p = Cyl(0.22, 0.26, H + 4, wm, 8); p.position.set(x, (H + 4) / 2, zz); g.add(p); }
    for (const y of [4.6, 9.2]) { const b = Box(0.3, 0.3, 4.2, wm, 0.05); b.position.set(x, y, z + 2); g.add(b); }
    between(V(x, 0.5, z + 4), V(x + 12, 9.2, z + 4), 0.12, wm, g);
  }
  for (const y of [4.6, 9.2]) { const pl = Box(L - 10, 0.28, 3.4, pm, 0.05); pl.position.set(0, y + 0.2, z + 2); g.add(pl); const rl = Box(L - 10, 0.2, 0.2, wm, 0.03); rl.position.set(0, y + 1.3, z + 4); g.add(rl); }
  shade(g);
}
function workers(g, pts, seed = 1) {
  const R = rnd(seed); const cols = [0xd8503a, 0x3a8a5a, 0xe0a030, 0x4a7bd0, 0xa05a9a]; const out = [];
  for (const [x, z, ry] of pts) { const p = makePerson({ shirt: cols[Math.floor(R() * cols.length)], pants: 0x4a3a2a, hair: [0x2a1a10, 0x6a3a18, 0x1a1a1a][Math.floor(R() * 3)], hat: R() < 0.5 ? 0xe8c070 : undefined, scale: 1.55 }); p.position.set(x, 0, z); p.rotation.y = ry ?? R() * 6; shade(p); g.add(p); out.push(p); }
  return out;
}
function procession(g, ark, L = 137.2, Bm = 22.9) { // animal pairs walking up the ramp into the door (ark at x=0,z=0, keel on ground)
  const dx = -L * 0.14, dz = Bm / 2 + 0.3, mk = [() => makeGiraffe(1.25), () => makeElephant(1.1), () => makeLion(1.3), () => makeSheep(1.7), () => makeGiraffe(1.25), () => makeElephant(1.1), () => makeLion(1.3)];
  const items = []; mk.forEach((f, i) => { for (const lane of [-1, 1]) { const a = f(); a.rotation.y = Math.PI / 2; shade(a); g.add(a); items.push({ a, lane, i }); } });
  const zTop = dz + 0.5, zBot = dz + 12.6, zStart = dz + 46;
  const upd = (t) => items.forEach(({ a, lane, i }) => {
    const per = mk.length * 0.26, s0 = ((t * 0.5 + i * 0.26 + (lane > 0 ? 0.03 : 0)) % per) / per * (per + 0.0); // metres-ish phase 0..per
    const d = (t * 3.2 + (mk.length - i) * 7.2 + (lane > 0 ? 0.8 : 0)) % (mk.length * 7.2 + 20); // distance travelled along the path
    const z = zStart - d; let y = 0.1; if (z < zBot) y = 0.4 + (zBot - Math.max(z, zTop)) * 0 + (zBot - z) / (zBot - zTop) * 4.5;
    a.position.set(dx + lane * 1.2, y + 0.08 * Math.abs(Math.sin(t * 7 + i + lane)), Math.max(z, zTop));
    a.visible = z > zTop - 0.2 && z < zStart;
    a.scale.setScalar(a.visible ? 1 : 0.0001);
  });
  return upd;
}
function bob(obj, w, x, z, t, amp, speed, steep, k = 1, base = 0) { // float a body on the waves: y + gentle pitch/roll
  const h = w.userData.height(x, z, t, amp, speed, steep), hx = w.userData.height(x + 12, z, t, amp, speed, steep) - w.userData.height(x - 12, z, t, amp, speed, steep), hz = w.userData.height(x, z + 6, t, amp, speed, steep) - w.userData.height(x, z - 6, t, amp, speed, steep);
  obj.position.y = base + h * k; obj.rotation.z = Math.atan2(hx, 24) * k; obj.rotation.x = -Math.atan2(hz, 12) * k * 0.7;
}

// ============================================================= SCENE 1: toy boat -> colossal ark (2.1 s)
function s1() {
  const g = new THREE.Group(); const e = env(DUSK, { key: { ...DUSK.key, ext: 60, target: [0, 0, 0] } }); e.sunDir = [0.0, 0.14, -1];
  const sea = seaWorld(g, e, { amp: 0.28, speed: 1.1, steep: 1.2 });
  const toy = makeToyBoat(); toy.scale.setScalar(1.0); g.add(toy);
  const ark = makeArk({ ramp: true }); ark.position.set(-8, 0, -150); ark.rotation.y = 0.32; g.add(ark);
  return { group: g, env: e, water: sea,
    cam(lt, u, dur) { const k = ease((lt - 0.7) / 1.25); const p = mix3([1.5, 0.8, 2.7], [8, 26, 46], k); const l = mix3([0, 0.55, 0], [-6, 9, -120], k); return { p, l, fov: lerp(34, 44, k) }; },
    update(lt, u, dur, t) { sea.w.userData.update(t, sea.amp, sea.speed, sea.steep); bob(toy, sea.w, 0, 0, t, sea.amp, sea.speed, sea.steep, 1, 0.04); bob(ark, sea.w, ark.position.x, ark.position.z, t, sea.amp, sea.speed, sea.steep, 0.2, 0); },
    anchors: { boat: at(toy, 0, 0.45, 0), arkBow: () => ark.userData.pt(68.6, 14, 11.45), arkMid: () => ark.userData.pt(0, 14.6, 11.45) } };
}

// ============================================================= SCENE 2: ark on the stocks, dimension lines 300 / 50 / 30 (3.8 s)
function arkSite(withScaffold = true) {
  const g = new THREE.Group(); const e = env(DUSK, { key: { ...DUSK.key, ext: 130, target: [0, 0, 0], dir: [0.4, 0.8, 0.9] } }); e.water = 0; e.fog = { color: 0xf0b074, near: 260, far: 1400 }; e.sunDir = [-0.85, 0.12, -0.5];
  sandWorld(g);
  const ark = makeArk({ ramp: true }); ark.position.y = ark.userData.draft; g.add(ark);
  // wooden cradle blocks under the keel
  for (let x = -60; x <= 60; x += 15) { const b = Box(3, 1.2, 14, mat(0x6a4a2a), 0.15); b.position.set(x, 0.6 - 0.0, 0); b.castShadow = true; g.add(b); }
  if (withScaffold) scaffold(g, 137, 23, 13.7, 14.4);
  const ws = workers(g, [[-52, 24, 0.5], [-20, 27, -0.4], [14, 26, 0.9], [44, 30, 2.8], [60, 22, 2.0], [-70, 20, 1.2]], 5);
  return { g, e, ark, ws };
}
function s2() {
  const { g, e, ark, ws } = arkSite(false); const L = 137.2, B = 22.9, H = 13.7; const walk = procession(g, ark);
  return { group: g, env: e,
    cam(lt, u) { const k = ease(u); return { p: mix3([74, 5, 44], [66, 9, 62], k), l: mix3([-26, 9, 4], [-40, 9, 0], k), fov: 58 }; },
    update(lt, u, dur, t) { ws.forEach((w, i) => { w.position.y = 0.04 * Math.abs(Math.sin(t * 3 + i)); }); walk(t); },
    anchors: { L0: () => ark.userData.pt(-L / 2 - 1, 0, B / 2), L1: () => ark.userData.pt(L / 2 + 1, 0, B / 2), H0: () => ark.userData.pt(L / 2 + 1, 0, B / 2), H1: () => ark.userData.pt(L / 2 + 1, H + 0.9, B / 2), W0: () => ark.userData.pt(L / 2 + 1, 0, B / 2), W1: () => ark.userData.pt(L / 2 + 1, 0, -B / 2) } };
}

// ============================================================= SCENE 3: forearm and ruler (4.75 s)
function s3() {
  const g = new THREE.Group(); const e = env(WARMROOM, { key: { ...WARMROOM.key, k: 1.5, ext: 1.2, target: [0, 0, 0], dir: [0.3, 1.0, 0.5], far: 12 }, hemi: { sky: 0xffe2c0, ground: 0x9a6a44, k: 0.9 } }); e.fog = { color: 0x3a2214, near: 3, far: 12 };
  const table = Box(6, 0.2, 4, woodMat(0.5, 0.17, [150, 100, 58], { seed: 21 }), 0.03); table.position.y = -0.1; table.receiveShadow = true; g.add(table);
  const arm = makeForearm(); arm.rotation.y = Math.PI / 2; arm.position.set(-0.03, 0.075, 0.205); g.add(arm);          // elbow at z=+0.205+0.0, fingertip at z=-0.245
  const ruler = makeRuler(0.5); ruler.rotation.y = Math.PI / 2; ruler.position.set(0.1, 0.007, -0.02); g.add(ruler);
  const par = Box(0.3, 0.006, 0.4, mat(0xf0dcae), 0.003); par.position.set(-0.19, 0.003, -0.05); par.rotation.y = 0.15; g.add(par);
  const ink = Cyl(0.025, 0.03, 0.05, mat(0x2a2a3a)); ink.position.set(0.24, 0.025, -0.2); g.add(ink); const qu = Cap(0.004, 0.2, mat(0xf4efe6)); qu.position.set(0.22, 0.1, -0.18); qu.rotation.set(0, 0, -0.9); g.add(qu);
  shade(g);
  const R = rnd(3); const dust = []; for (let i = 0; i < 24; i++) { const d = Sph(0.0022 + R() * 0.002, glow(0xffd9a0), 1, 1, 1, 6); d.position.set((R() - .5) * 0.7, 0.05 + R() * 0.4, (R() - .5) * 0.7); d.userData.s = R(); d.userData.noShadow = true; g.add(d); dust.push(d); }
  return { group: g, env: e,
    cam(lt, u) { const a = lerp(-0.12, 0.12, ease(u)); const d = 0.86 - 0.09 * ease(u); return { p: [0.02 + Math.sin(a) * 0.3, d * 0.86, 0.12 + d * 0.5], l: [0.02, 0.02, -0.02], fov: 36, roll: 0.05 * Math.sin(u * 2.4) }; },
    update(lt, u, dur, t) { dust.forEach(d => { d.position.y += 0.0005 * (0.3 + d.userData.s); if (d.position.y > 0.45) d.position.y = 0.05; }); },
    anchors: { elbow: at(arm, -0.065, 0, 0), tip: at(arm, 0.45, 0, 0.012), rule0: at(ruler, -0.25, 0.006, 0), rule1: at(ruler, 0.25, 0.006, 0) } };
}

// ============================================================= SCENE 4: pull back along the hull, counter to 137 m (2.8 s)
function s4() {
  const { g, e, ark, ws } = arkSite(false); const L = 137.2, B = 22.9, H = 13.7; e.key.ext = 110; e.sunDir = [0.55, 0.12, -0.8]; const walk = procession(g, ark);
  const lamp = null;
  return { group: g, env: e,
    cam(lt, u) { const k = ease(u); return { p: mix3([-62, 9, 50], [72, 40, 150], k), l: mix3([-20, 7, 0], [-6, 7, 0], k), fov: 44 }; },
    update(lt, u, dur, t) { ws.forEach((w, i) => { w.position.y = 0.04 * Math.abs(Math.sin(t * 3 + i)); }); walk(t); },
    anchors: { L0: () => ark.userData.pt(-L / 2 - 1, H + 0.9, B / 2 + 1.5), L1: () => ark.userData.pt(L / 2 + 1, H + 0.9, B / 2 + 1.5), Lmid: () => ark.userData.pt(0, H + 0.9, B / 2 + 1.5) } };
}

// ============================================================= SCENE 5: football field + tiny person, ark slides alongside 1.5 fields (2.9 s)
function s5() {
  const g = new THREE.Group(); const e = env(DUSK, { key: { ...DUSK.key, ext: 150, target: [30, 0, 20], dir: [0.5, 0.8, 0.7] } }); e.sunDir = [0.45, 0.1, -1]; e.fog = { color: 0xf0b074, near: 260, far: 1300 };
  const sea = seaWorld(g, e, { amp: 0.25, speed: 0.8, steep: 1.0 }); sea.w.position.y = -0.4;
  const land = new THREE.Mesh(new THREE.BoxGeometry(700, 1, 70), mat(0xd6a864)); land.position.set(0, -0.6, -4); land.receiveShadow = true; g.add(land);
  const fld = makeField(); g.add(fld);
  const person = makePerson({ shirt: 0xd8402a, pants: 0x3a3a60, hair: 0x2a1a10, scale: 1.6 }); person.position.set(-45.72, 0, 0); person.rotation.y = Math.PI / 2; poseArms(person, [0, 0.12, 0], [0, 0.12, 0]); shade(person); g.add(person);
  const ark = makeArk({ ramp: false }); ark.position.set(0, 0, 46); g.add(ark);
  const FW = 91.44;
  return { group: g, env: e, water: sea,
    cam(lt, u) { const k = ease(u); return { p: [-74 + 6 * k, 22 - 2 * k, -34 + 6 * k], l: [lerp(-8, 0, k), 2, lerp(16, 20, k)], fov: 46 }; },
    update(lt, u, dur, t) { sea.w.userData.update(t, sea.amp, sea.speed, sea.steep); const k = easeO((lt - 0.1) / 1.9); ark.position.x = -45.72 + 68.6 + lerp(-110, 0, k); bob(ark, sea.w, ark.position.x, 46, t, sea.amp, sea.speed, sea.steep, 0.4, 0);
      const wv = ease((lt - 0.3) / 0.4) * (1 - ease((lt - 2.3) / 0.4)); poseArms(person, [0, -0.1, 0], [-0.2, 0.1 + 2.5 * wv + 0.25 * wv * Math.sin(t * 9), 0]); },
    anchors: { f0: fixed(-45.72, 0.05, -26), f1: fixed(45.72, 0.05, -26), a0: () => ark.userData.pt(-68.6, 3.4, -11.45), a1: () => ark.userData.pt(68.6, 3.4, -11.45), person: at(person, 0, 1.9, 0) } };
}

// ============================================================= SCENE 6: cutaway, 3 decks light up, door glows, roof opening (3.1 s)
function s6() {
  const g = new THREE.Group(); const e = env(WARMROOM, { key: { ...WARMROOM.key, k: 2.0, ext: 70, target: [0, 6, 0], dir: [0.3, 0.7, 1.0], far: 300 } }); e.hemi = { sky: 0xffe0b8, ground: 0x9a6a40, k: 1.8 }; e.key.k = 3.0;
  e.sky = { top: 0xb87a50, mid: 0xe0a060, hor: 0xf0c080, below: 0xc89860, sunCol: 0x000000, glowK: 0, glowP: 10, sunSize: 0 }; e.fog = { color: 0xe0a868, near: 200, far: 700 };
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(900, 900).rotateX(-Math.PI / 2), new THREE.MeshToonMaterial({ map: sandTex(40, 40), gradientMap: GRAD })); ground.position.y = -0.2; ground.receiveShadow = true; g.add(ground);
  const cut = makeArkCutaway(); g.add(cut); const U = cut.userData; const L = U.L, B = U.B, H = U.H;
  const lampCols = [0xffd890, 0xffd890, 0xffd890];
  return { group: g, env: e,
    cam(lt, u) { const k = ease(u); return { p: [lerp(-78, -48, k), lerp(14, 12, k), lerp(46, 40, k)], l: [lerp(-38, -22, k), 6.5, -4], fov: 52 }; },
    update(lt, u, dur, t) {
      U.lights.forEach((l, d) => { const on = ease((lt - (0.35 + d * 0.55)) / 0.25); l.mat.color.setRGB(lerp(0.2, 1.0, on), lerp(0.14, 0.82, on), lerp(0.08, 0.5, on)); });
      const pulse = 0.75 + 0.25 * Math.sin(t * 6); const don = ease((lt - 2.0) / 0.3); U.doorMat.color.setRGB(lerp(0.3, 1.0, don) * (0.9 + 0.1 * pulse), lerp(0.22, 0.82, don) * (0.9 + 0.1 * pulse), lerp(0.1, 0.5, don));
      const son = ease((lt - 2.5) / 0.3); U.slitMat.color.setRGB(lerp(0.2, 1, son), lerp(0.14, 0.85, son), lerp(0.08, 0.5, son));
      U.animals.forEach((a, i) => { a.position.y = U.decks[i < 8 ? 0 : i < 17 ? 1 : 2] + 0.03 * Math.abs(Math.sin(t * 2.4 + i * 1.3)); });
    },
    anchors: { d1: fixed(-48, 0.6 + 2.0, -B / 2 + 9), d2: fixed(-39, 4.9 + 2.0, -B / 2 + 9), d3: fixed(-30, 9.2 + 2.0, -B / 2 + 9), door: () => U.door.getWorldPosition(V()), roof: fixed(-20, H + 1.9, 0) } };
}

// ============================================================= SCENE 7: blueprint board 6:1 (1.84 s)
function s7() {
  const g = new THREE.Group(); const e = env(WARMROOM, { key: { ...WARMROOM.key, ext: 3, target: [0, 0.8, 0], dir: [0.2, 0.6, 1.0], far: 20 } }); e.fog = { color: 0x3a2214, near: 5, far: 18 };
  const floor = Box(14, 0.2, 10, woodMat(1.2, 0.4, [120, 76, 40], { seed: 30 }), 0.03); floor.position.y = -0.1; floor.receiveShadow = true; g.add(floor);
  const wall = Box(14, 5, 0.2, woodMat(1.2, 0.4, [96, 60, 32], { seed: 31 }), 0.03); wall.position.set(0, 2.5, -1.2); g.add(wall);
  const bp = makeBlueprint(); bp.position.set(0, 1.45, -0.9); bp.rotation.x = -0.12; g.add(bp);
  for (const s of [-1, 1]) { const leg = between(V(s * 1.3, 0.2, -0.5), V(s * 1.0, 2.5, -1.0), 0.035, mat(0x5a3a22), g); }
  const pen = Cap(0.012, 0.28, mat(0xffd23f)); pen.position.set(0.9, 0.11, 0.1); pen.rotation.set(0, 0.5, Math.PI / 2); g.add(pen);
  const rl = makeRuler(0.5); rl.position.set(-0.8, 0.1, 0.3); rl.rotation.y = 0.15; g.add(rl);
  shade(g);
  const Wb = bp.userData.W, Hb = bp.userData.H, uvx = (x) => (x / 1536 - 0.5) * Wb, uvy = (y) => (0.5 - y / 1024) * Hb;
  const px = 120, pw = 1536 - 240, py = 170, ph = pw / 6;
  return { group: g, env: e,
    cam(lt, u) { const k = ease(u); return { p: [lerp(-0.6, 0.6, k), lerp(1.8, 1.6, k), lerp(7.4, 6.2, k)], l: [0, 1.45, -0.9], fov: 40 }; },
    update() { },
    anchors: { P0: at(bp, uvx(px), uvy(py) , 0.06), P1: at(bp, uvx(px + pw), uvy(py), 0.06), P2: at(bp, uvx(px + pw), uvy(py + ph), 0.06), P3: at(bp, uvx(px), uvy(py + ph), 0.06) } };
}

// ============================================================= SCENE 8: ark and a modern cargo ship side by side on stormy waves (4.1 s)
function s8() {
  const g = new THREE.Group(); const e = env(STORM, { key: { ...STORM.key, ext: 150, target: [0, 0, 0] } });
  const sea = seaWorld(g, e, { amp: 1.1, speed: 1.2, steep: 1.1, rain: 1.0 });
  const ark = makeArk({ ramp: false }); ark.position.set(0, 0, -22); g.add(ark);
  const cargo = makeCargoShip(); cargo.position.set(0, 0, 24); g.add(cargo);
  return { group: g, env: e, water: sea,
    cam(lt, u) { const phi = lerp(1.0, 0.72, ease(u)); const R = 215; return { p: [Math.sin(phi) * R + 6, 26 - 4 * u, Math.cos(phi) * R], l: [-4, 7, 0], fov: 40 }; },
    update(lt, u, dur, t) { sea.w.userData.update(t, sea.amp, sea.speed, sea.steep); bob(ark, sea.w, 0, -22, t, sea.amp, sea.speed, sea.steep, 0.35, 0); bob(cargo, sea.w, 0, 24, t, sea.amp, sea.speed, sea.steep, 0.35, 0); sea.rn.userData.update(t, V(...(window.__camPos || [0, 0, 0])), 1); },
    anchors: { ark: () => ark.userData.pt(30, 14.5, 11.45), cargo: () => cargo.userData.pt(20, 11, 11.5), arkEnd: () => ark.userData.pt(68.6, 8, 11.5) } };
}

// ============================================================= SCENE 9: Titanic beside the ark (2.35 s)
function s9() {
  const g = new THREE.Group(); const e = env(DUSK, { key: { ...DUSK.key, ext: 220, target: [20, 0, 0], map: 4096 } }); e.sunDir = [0.5, 0.1, -1]; e.fog = { color: 0xf2b074, near: 300, far: 1500 };
  const sea = seaWorld(g, e, { amp: 0.5, speed: 0.9, steep: 0.9 });
  const ark = makeArk({ ramp: false }); ark.position.set(0, 0, 10); g.add(ark);
  const ti = makeTitanic(); g.add(ti);
  const L = 137.2;
  return { group: g, env: e, water: sea,
    cam(lt, u) { const k = ease(u); return { p: [lerp(210, 260, k), lerp(70, 62, k), lerp(150, 120, k)], l: [lerp(10, 0, k), 8, -10], fov: 44 }; },
    update(lt, u, dur, t) { sea.w.userData.update(t, sea.amp, sea.speed, sea.steep); const k = easeO((lt - 0.0) / 1.6); ti.position.set(-134.5 + 68.6 + lerp(-150, 0, k) - 68.6 + 68.6 - 0, 0, -48); ti.position.x = 68.6 - 134.5 + lerp(-130, 0, k); bob(ark, sea.w, 0, 10, t, sea.amp, sea.speed, sea.steep, 0.3, 0); bob(ti, sea.w, ti.position.x, -48, t, sea.amp, sea.speed, sea.steep, 0.25, 0); },
    anchors: { a0: () => ark.userData.pt(-68.6, 0, 11.45), a1: () => ark.userData.pt(68.6, 0, 11.45), t0: () => ti.userData.pt(-134.5, 0, 14), t1: () => ti.userData.pt(134.5, 0, 14) } };
}

// ============================================================= SCENE 10: hull flexes in heavy waves, leaks (2.9 s)
function s10() {
  const g = new THREE.Group(); const e = env(STORM, { key: { ...STORM.key, ext: 90, target: [0, 0, 0] } });
  const sea = seaWorld(g, e, { amp: 1.9, speed: 1.5, steep: 1.3, rain: 1.4 });
  const ark = makeArk({ ramp: false }); g.add(ark); const L = 137.2, B = 22.9;
  const jets = [ -48, -12, 22, 50 ].map((x) => { const j = makeJet(60, 0.28); g.add(j); return { j, x }; });
  const spray = makeJet(70, 0.4, 0xe8f4ff, 0.8); g.add(spray);
  let bendAmt = 0;
  return { group: g, env: e, water: sea,
    cam(lt, u) { const k = ease(u); return { p: [lerp(-70, 30, k), lerp(16, 22, k), lerp(86, 100, k)], l: [lerp(-30, 10, k), 7, 0], fov: 44 }; },
    update(lt, u, dur, t) {
      sea.w.userData.update(t, sea.amp, sea.speed, sea.steep);
      const A = 1.9 * Math.sin(t * 2.6); ark.userData.bend((x) => A * (1 - (x / (L / 2)) ** 2) * 0.9 - 0.0);
      ark.position.y = 0.55 * Math.sin(t * 2.1) + 0.2; ark.rotation.z = 0.025 * Math.sin(t * 1.7); ark.rotation.x = 0.04 * Math.sin(t * 1.3);
      ark.updateMatrixWorld(true);
      for (const o of jets) { const org = ark.userData.pt(o.x, 8.0 + 0.9 * Math.sin(o.x), B / 2 + 0.8); o.j.userData.update(t + o.x * 0.1, { origin: org, vel: V(0.5, 3.2, 7.0), spread: 0.8, g: 11, life: 1.1, rate: 1.4, scale: 1, on: 1 }); }
      spray.userData.update(t, { origin: ark.userData.pt(-12, 2.0, B / 2 + 4), vel: V(1.0, 12, 4), spread: 1.4, g: 12, life: 1.6, rate: 0.9, scale: 1 });
      sea.rn.userData.update(t, V(...(window.__camPos || [0, 0, 0])), 1);
    },
    anchors: { seam: () => ark.userData.pt(22, 8.4, B / 2 + 0.8), seam2: () => ark.userData.pt(-12, 8.0, B / 2 + 0.8) } };
}

// ============================================================= SCENE 11: wooden schooner, pumps gushing (4.0 s)
function s11() {
  const g = new THREE.Group(); const e = env(STORM, { key: { ...STORM.key, ext: 110, target: [0, 0, 0], map: 4096 } });
  const sea = seaWorld(g, e, { amp: 1.5, speed: 1.3, steep: 1.2, rain: 1.2 });
  const sc = makeSchooner(); g.add(sc); const U = sc.userData; const L = U.L, B = U.B;
  const jets = U.pumps.map((p) => { const j = makeJet(46, 0.3); g.add(j); return j; });
  return { group: g, env: e, water: sea,
    cam(lt, u) { const a = lerp(0.45, 1.15, ease(u)); const R = 190; return { p: [Math.sin(a) * R, 30 + 6 * u, Math.cos(a) * R], l: [0, 24, 0], fov: 46 }; },
    update(lt, u, dur, t) {
      sea.w.userData.update(t, sea.amp, sea.speed, sea.steep); bob(sc, sea.w, 0, 0, t, sea.amp, sea.speed, sea.steep, 0.35, 0); sc.updateMatrixWorld(true);
      U.pumps.forEach((p, i) => { p.userData.lever.rotation.x = 0.5 * Math.sin(t * 7 + i * 2); const org = p.localToWorld(V(0, 1.4, 1.5)); jets[i].userData.update(t + i * 0.3, { origin: org, vel: V(0.6, 7.5, 9.5), spread: 0.35, g: 12, life: 1.55, rate: 1.1, scale: 1.1 }); });
      sea.rn.userData.update(t, V(...(window.__camPos || [0, 0, 0])), 1);
    },
    anchors: { mast6: () => sc.userData.pt(U.masts[5], 52, 0), mast1: () => sc.userData.pt(U.masts[0], 56, 0), pump: () => U.pumps[1].localToWorld(V(0, 1.4, 1.5)) } };
}

// ============================================================= SCENE 12: empty mountain ridges + searchlight sweep (2.8 s)
function s12() {
  const g = new THREE.Group(); const e = env(NIGHT, { key: { ...NIGHT.key, ext: 160, target: [0, 20, -80] } });
  const gnd = new THREE.Mesh(new THREE.PlaneGeometry(1600, 1200).rotateX(-Math.PI / 2), mat(0x1c2c44, { flat: true })); gnd.receiveShadow = true; g.add(gnd);
  const R = rnd(12); const peaks = [];
  const layers = [[-140, 0x6a7a98, 70, 1], [-260, 0x4a5a80, 110, 1], [-420, 0x3a4a72, 150, 1]];
  layers.forEach(([z, col, hmax], li) => { for (let i = -5; i <= 5; i++) { const h = hmax * (0.55 + 0.6 * R()); const m = makeMountain(h, h * (1.0 + 0.5 * R()), 60 + li * 20 + i, col, 0xe8eeff, 0.3); m.position.set(i * (80 + li * 40) + R() * 40, 0, z - R() * 30); g.add(m); if (li === 0 && i === 1) peaks.push(m); } });
  const hero = makeMountain(70, 78, 99, 0x7a8aa8, 0xf0f4ff, 0.34); hero.position.set(18, 0, -110); g.add(hero);
  const R2 = rnd(77); for (let i = 0; i < 6; i++) { const c = makeCloud(30 + i, 0x7a88b0, 1.3 + R2()); c.position.set(-300 + i * 120, 110 + R2() * 40, -380); g.add(c); }
  const sl = makeSearchlight(); sl.position.set(-40, 0, 20); g.add(sl); const rn = makeRain(700, [70, 45, 70], 1.4, 0.25); g.add(rn);
  const stars = []; for (let i = 0; i < 60; i++) { const s = Sph(0.8, glow(0xdde6ff), 1, 1, 1, 6); s.position.set((R2() - .5) * 900, 140 + R2() * 160, -520); s.userData.noShadow = true; g.add(s); }
  return { group: g, env: e,
    cam(lt, u) { const k = ease(u); return { p: [lerp(-22, 14, k), lerp(16, 24, k), lerp(70, 46, k)], l: [lerp(0, 8, k), 28, -110], fov: 42 }; },
    update(lt, u, dur, t) { sl.userData.head.rotation.y = lerp(-0.2, -1.6, u) - 0.5; sl.userData.head.rotation.z = lerp(0.28, 0.16, u) + 0.08 * Math.sin(t * 1.6); rn.userData.update(t, V(...(window.__camPos || [0, 0, 0])), 1); },
    anchors: { peak: at(hero, 0, 70, 0), light: at(sl, 0, 12.8, 0) } };
}

// ============================================================= SCENE 13: colossal ark at dusk with rain, POSSIBLE / IMPOSSIBLE pills (5.2 s)
function s13() {
  const g = new THREE.Group(); const e = env(STORM, { key: { ...STORM.key, ext: 140, target: [0, 0, 0] } }); e.sky = { ...STORM.sky, mid: 0xb06a48, glowK: 0.85 }; e.fog = { color: 0xb88a72, near: 150, far: 900 };
  const sea = seaWorld(g, e, { amp: 0.5, speed: 0.9, steep: 1.0, rain: 0.9 });
  const ark = makeArk({ ramp: true }); ark.position.set(8, 0, -48); ark.rotation.y = 0.18; g.add(ark);
  const toy = makeToyBoat(); toy.scale.setScalar(1.3); toy.position.set(-6, 0, -4); g.add(toy);
  const p1 = makePill('POSSIBLE', 0x2f9a56, 9, 3.2), p2 = makePill('IMPOSSIBLE', 0xc8382e, 11, 3.2); g.add(p1, p2);
  shade(p1); shade(p2);
  return { group: g, env: e, water: sea,
    cam(lt, u) { const k = ease(u); return { p: [lerp(-22, -8, k), 8, lerp(54, 46, k)], l: [lerp(6, 3, k), 8, -48], fov: 42 }; },
    update(lt, u, dur, t) { sea.w.userData.update(t, sea.amp, sea.speed, sea.steep); bob(ark, sea.w, 8, -48, t, sea.amp, sea.speed, sea.steep, 0.2, 0); bob(toy, sea.w, -6, -4, t, sea.amp, sea.speed, sea.steep, 1, 0.05);
      const pop = (t0) => easeOut(clamp((lt - t0) / 0.5)); function easeOut(x) { return x <= 0 ? 0 : 1 - Math.pow(1 - x, 3) * Math.cos(x * 9); }
      const cam = window.__cam, D = 14, put3 = (pl, x, y, sc, rz) => { cam.updateMatrixWorld(true); pl.position.copy(cam.localToWorld(V(x, y, -D))); pl.quaternion.copy(cam.quaternion); pl.rotateZ(rz); pl.scale.setScalar(Math.max(0.0001, sc)); };
      put3(p1, -1.55, -0.55 + 0.04 * Math.sin(t * 1.7), 0.255 * pop(1.5), 0.025 * Math.sin(t * 1.3)); put3(p2, 1.3, -0.55 + 0.04 * Math.sin(t * 1.5 + 1), 0.255 * pop(2.1), -0.025 * Math.sin(t * 1.1));
      sea.rn.userData.update(t, V(...(window.__camPos || [0, 0, 0])), 1); },
    anchors: { p1: at(p1, 0, 0, 0), p2: at(p2, 0, 0, 0), arkBow: () => ark.userData.pt(68.6, 14, 11.45) } };
}

export const BUILD = [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, s13];
