// Scenes of topics/ark_size (7 scenes, each >= 4.5 s; beats are grouped, the camera keeps moving inside one set).
import { THREE, V, clamp, sstep, lerp, mat, glow, woodMat, put, Sph, Box, Cyl, Cap, Cone, Pln, between, shade, tube, rnd, makeSky, makeWater, makeRain, makeJet, makePerson, poseArms, makeGiraffe, makeElephant, makeLion, makeSheep, makeCloud, makeMountain, sandTex, canvasTex, GRAD } from './kit.js';
import { makeArk, makeArkCutaway, makeCargoShip, makeTitanic, makeSchooner, makeToyBoat, makeField, makeForearm, makeRuler, makeBlueprint, makePill, makeSearchlight, slab } from './props.js';
import { REG, reg, ease, easeO, easeOB, mix3, at, fixed, bp, camRig, DUSK, STORM, NIGHT, WARMROOM, env, seaWorld, sandWorld, workers, bob } from './world.js';

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

// ------------------------------------------------------------------ SCENE A: toy boat in the sand yard, camera sweeps to the colossal ark; dimension lines (beats 1-2)
reg('ark_yard', () => {
  const { g, e, ark, ws } = arkSite(false); const L = 137.2, B = 22.9, H = 13.7; const walk = procession(g, ark);
  const toy = makeToyBoat(); toy.position.set(56, 0, 52); toy.rotation.y = -0.5; shade(toy); g.add(toy);
  const dust = new THREE.Group(); g.add(dust);
  return { group: g, env: e,
    cam: camRig([[0, [58.6, 1.1, 56.2], [56, 0.6, 52], 34], [[0, 0.55], [60, 3.2, 60], [40, 3.5, 40], 40], [[1, 0.0], [62, 5.5, 64], [8, 8, 18], 48], [1, [70, 9, 66], [-38, 9, 0], 58]]),
    update(lt, u, dur, t, B_) { ws.forEach((w, i) => { w.position.y = 0.04 * Math.abs(Math.sin(t * 3 + i)); }); walk(t); toy.position.y = 0.02 * Math.sin(t * 2.2); toy.rotation.z = 0.03 * Math.sin(t * 1.7); },
    anchors: { boat: at(toy, 0, 0.5, 0), arkMid: () => ark.userData.pt(0, 14.6, 11.45),
      L0: () => ark.userData.pt(-L / 2 - 1, 0, B / 2), L1: () => ark.userData.pt(L / 2 + 1, 0, B / 2), H0: () => ark.userData.pt(L / 2 + 1, 0, B / 2), H1: () => ark.userData.pt(L / 2 + 1, H + 0.9, B / 2), W0: () => ark.userData.pt(L / 2 + 1, 0, B / 2), W1: () => ark.userData.pt(L / 2 + 1, 0, -B / 2) } };
});

// ------------------------------------------------------------------ SCENE B: forearm and ruler (beat 3)
reg('ark_forearm', () => {
  const g = new THREE.Group(); const e = env(WARMROOM, { key: { ...WARMROOM.key, k: 1.5, ext: 1.2, target: [0, 0, 0], dir: [0.3, 1.0, 0.5], far: 12 }, hemi: { sky: 0xffe2c0, ground: 0x9a6a44, k: 0.9 } }); e.fog = { color: 0x3a2214, near: 3, far: 12 };
  const table = Box(6, 0.2, 4, woodMat(0.5, 0.17, [150, 100, 58], { seed: 21 }), 0.03); table.position.y = -0.1; table.receiveShadow = true; g.add(table);
  const arm = makeForearm(); arm.rotation.y = Math.PI / 2; arm.position.set(-0.03, 0.075, 0.205); g.add(arm);          // elbow back at z=+0.27, middle fingertip at z=-0.245
  const ruler = makeRuler(0.5); ruler.rotation.y = Math.PI / 2; ruler.position.set(0.1, 0.007, -0.02); g.add(ruler);
  const par = Box(0.3, 0.006, 0.4, mat(0xcdb27c), 0.003); par.position.set(-0.42, 0.003, -0.05); par.rotation.y = 0.15; g.add(par);
  const ink = Cyl(0.025, 0.03, 0.05, mat(0x2a2a3a)); ink.position.set(0.24, 0.025, -0.2); g.add(ink); const qu = Cap(0.004, 0.2, mat(0xf4efe6)); qu.position.set(0.22, 0.1, -0.18); qu.rotation.set(0, 0, -0.9); g.add(qu);
  shade(g);
  const R = rnd(3); const dust = []; for (let i = 0; i < 24; i++) { const d = Sph(0.0022 + R() * 0.002, glow(0xffd9a0), 1, 1, 1, 6); d.position.set((R() - .5) * 0.7, 0.05 + R() * 0.4, (R() - .5) * 0.7); d.userData.s = R(); d.userData.noShadow = true; g.add(d); dust.push(d); }
  return { group: g, env: e,
    cam(lt, u) { const a = lerp(-0.12, 0.12, ease(u)); const d = 1.0 - 0.08 * ease(u); return { p: [0.02 + Math.sin(a) * 0.3, d * 0.86, 0.12 + d * 0.5], l: [0.02, 0.02, -0.02], fov: 38, roll: 0.05 * Math.sin(u * 2.4) }; },
    update(lt, u, dur, t) { dust.forEach(d => { d.position.y += 0.0005 * (0.3 + d.userData.s); if (d.position.y > 0.45) d.position.y = 0.05; }); },
    anchors: { elbow: () => arm.localToWorld(arm.userData.elbow.clone()), tip: () => arm.localToWorld(arm.userData.tip.clone()), rule0: at(ruler, -0.25, 0.006, 0), rule1: at(ruler, 0.25, 0.006, 0) } };
});

// ------------------------------------------------------------------ SCENE C: ark on the sand beside a football field; pull back along the hull, then 1.5 fields (beats 4-5)
reg('ark_field', () => {
  const g = new THREE.Group(); const e = env(DUSK, { key: { ...DUSK.key, ext: 150, target: [20, 0, 20], dir: [0.5, 0.8, 0.7] } }); e.sunDir = [0.55, 0.12, -0.8]; e.fog = { color: 0xf0b074, near: 300, far: 1500 };
  e.water = 0; sandWorld(g); const L = 137.2, B = 22.9, H = 13.7, X0 = -45.72;
  const ark = makeArk({ ramp: true }); ark.position.set(X0 + L / 2, ark.userData.draft, 0); g.add(ark);
  for (let x = -60; x <= 60; x += 15) { const b = Box(3, 1.2, 14, mat(0x6a4a2a), 0.15); b.position.set(X0 + L / 2 + x, 0.6, 0); b.castShadow = true; g.add(b); }
  const fld = makeField(); fld.position.set(0, 0.0, 50); g.add(fld);
  const person = makePerson({ shirt: 0xd8402a, pants: 0x3a3a60, hair: 0x2a1a10, scale: 1.6 }); person.position.set(X0 - 1.0, 0.0, 50); person.rotation.y = Math.PI / 2; poseArms(person, [0, 0.12, 0], [0, 0.12, 0]); shade(person); g.add(person);
  const ws = workers(g, [[-20, 22, 0.5], [30, 24, -0.4], [60, 22, 2.0]], 5);
  return { group: g, env: e,
    cam: camRig([[0, [X0 - 40, 7, 45], [X0 + 25, 6, 8], 44], [[1, 0.0], [X0 - 36, 10, 62], [X0 + 45, 4, 36], 48], [1, [X0 - 18, 44, 110], [X0 + 38, 3, 30], 50]]),
    update(lt, u, dur, t, B_) { ws.forEach((w, i) => { w.position.y = 0.04 * Math.abs(Math.sin(t * 3 + i)); });
      const wv = ease((lt - B_[1] - 0.5) / 0.4) * (1 - ease((lt - B_[1] - 2.1) / 0.4)); poseArms(person, [0, -0.1, 0], [-0.2, 0.1 + 2.5 * wv + 0.25 * wv * Math.sin(t * 9), 0]); },
    anchors: { L0: () => ark.userData.pt(-L / 2 - 1, H + 0.9, B / 2 + 1.5), L1: () => ark.userData.pt(L / 2 + 1, H + 0.9, B / 2 + 1.5),
      f0: fixed(-45.72, 0.05, 50 - 28), f1: fixed(45.72, 0.05, 50 - 28), a0: () => ark.userData.pt(-L / 2, 3.4, B / 2 + 0.3), a1: () => ark.userData.pt(L / 2, 3.4, B / 2 + 0.3), person: at(person, 0, 1.9, 0) } };
});

// ------------------------------------------------------------------ SCENE D: inside the ark (3 decks, door, roof opening), then six squares laid along the hull (beats 6-7)
reg('ark_inside', () => {
  const g = new THREE.Group(); const e = env(WARMROOM, { key: { ...WARMROOM.key, k: 2.0, ext: 90, target: [0, 6, 0], dir: [0.3, 0.7, 1.0], far: 300 } }); e.hemi = { sky: 0xffe0b8, ground: 0x9a6a40, k: 1.6 }; e.key.k = 2.8;
  e.sky = { top: 0xb87a50, mid: 0xe0a060, hor: 0xf0c080, below: 0xc89860, sunCol: 0x000000, glowK: 0, glowP: 10, sunSize: 0 }; e.fog = { color: 0xe0a868, near: 220, far: 800 };
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(900, 900).rotateX(-Math.PI / 2), new THREE.MeshToonMaterial({ map: sandTex(40, 40), gradientMap: GRAD })); ground.position.y = -0.2; ground.receiveShadow = true; g.add(ground);
  const cut = makeArkCutaway(); g.add(cut); const U = cut.userData; const L = U.L, B = U.B, H = U.H;
  const tiles = []; for (let i = 0; i < 6; i++) { const t = Box(B - 0.5, 0.25, B - 0.5, mat(i === 0 ? 0xf0b020 : 0xd8c8a0, { e: i === 0 ? 0x4a3000 : 0x1a1408, ei: 0.4 }), 0.08); t.position.set(-L / 2 + B / 2 + i * (L - B) / 5 * 0 + i * (B + 0.6) - 0.0 * 0, 0.1, B / 2 + 14.5); t.userData.noShadow = true; t.scale.setScalar(0.0001); g.add(t); tiles.push(t); }
  const px0 = -L / 2 + 0.0;
  return { group: g, env: e,
    cam: camRig([[0, [-78, 14, 46], [-38, 6.5, -4], 52], [[1, 0.0], [-46, 12, 42], [-22, 6.5, -4], 52], [1, [-150, 105, 175], [-20, 0, 18], 52]]),
    update(lt, u, dur, t, B_) {
      U.lights.forEach((l, d) => { const on = ease((lt - (0.35 + d * 0.55)) / 0.25); l.mat.color.setRGB(lerp(0.2, 1.0, on), lerp(0.14, 0.82, on), lerp(0.08, 0.5, on)); });
      const pulse = 0.75 + 0.25 * Math.sin(t * 6); const don = ease((lt - 2.0) / 0.3); U.doorMat.color.setRGB(lerp(0.3, 1.0, don) * (0.9 + 0.1 * pulse), lerp(0.22, 0.82, don) * (0.9 + 0.1 * pulse), lerp(0.1, 0.5, don));
      const son = ease((lt - 2.5) / 0.3); U.slitMat.color.setRGB(lerp(0.2, 1, son), lerp(0.14, 0.85, son), lerp(0.08, 0.5, son));
      U.animals.forEach((a, i) => { a.position.y = U.decks[i < 8 ? 0 : i < 17 ? 1 : 2] + 0.03 * Math.abs(Math.sin(t * 2.4 + i * 1.3)); });
      { const kk = ease((lt - B_[1] + 1.4) / 1.2); e.key.k = lerp(2.8, 1.5, kk); e.hemi.k = lerp(1.6, 0.95, kk); }
      tiles.forEach((tl, i) => { const k = easeOB((lt - B_[1] - 0.15 - i * 0.2) / 0.5); tl.scale.setScalar(Math.max(k, 0.0001)); });
    },
    anchors: { d1: fixed(-48, 0.6 + 2.0, -B / 2 + 9), d2: fixed(-39, 4.9 + 2.0, -B / 2 + 9), d3: fixed(-30, 9.2 + 2.0, -B / 2 + 9), door: () => U.door.getWorldPosition(V()), roof: fixed(-20, H + 1.9, 0),
      P0: fixed(-L / 2 + 0.2, 0.3, B / 2 + 14.5 + B / 2 + 2), P1: fixed(-L / 2 + 6 * (B + 0.6) - 0.6, 0.3, B / 2 + 14.5 + B / 2 + 2), Q0: fixed(-L / 2 + 6 * (B + 0.6) + 1.0, 0.3, B / 2 + 14.5 - B / 2 + 0.2), Q1: fixed(-L / 2 + 6 * (B + 0.6) + 1.0, 0.3, B / 2 + 14.5 + B / 2 - 0.2) } };
});

// ------------------------------------------------------------------ SCENE E: ark + cargo ship on stormy waves, then the Titanic slides in (beats 8-9)
reg('ark_ships', () => {
  const g = new THREE.Group(); const e = env(STORM, { key: { ...STORM.key, ext: 230, target: [0, 0, 0], map: 4096 } }); e.sky = { ...STORM.sky, mid: 0xb06a48, glowK: 0.85 }; e.fog = { color: 0xb88a72, near: 200, far: 1200 }; e.sunDir = [0.5, 0.1, -1];
  const sea = seaWorld(g, e, { amp: 0.9, speed: 1.1, steep: 1.0, rain: 0.9 });
  const ark = makeArk({ ramp: false }); ark.position.set(0, 0, 0); g.add(ark);
  const cargo = makeCargoShip(); cargo.position.set(0, 0, 48); g.add(cargo);
  const ti = makeTitanic(); g.add(ti);
  return { group: g, env: e, water: sea,
    cam: camRig([[0, [150, 24, 190], [-4, 8, 10], 40], [[1, 0.0], [210, 40, 230], [-30, 8, 0], 44], [1, [300, 90, 270], [-60, 6, -20], 50]]),
    update(lt, u, dur, t, B_) { sea.w.userData.update(t, sea.amp, sea.speed, sea.steep); const k = easeO((lt - B_[1] + 0.2) / 1.9), kc = ease((lt - B_[1] + 0.3) / 1.8);
      cargo.position.x = lerp(0, 380, kc); ti.position.set(68.6 - 134.5 + lerp(-380, 0, k), 0, -56);
      bob(ark, sea.w, 0, 0, t, sea.amp, sea.speed, sea.steep, 0.35, 0); bob(cargo, sea.w, cargo.position.x, 48, t, sea.amp, sea.speed, sea.steep, 0.35, 0); bob(ti, sea.w, ti.position.x, -56, t, sea.amp, sea.speed, sea.steep, 0.25, 0);
      sea.rn.userData.update(t, V(...(window.__camPos || [0, 0, 0])), 1); ti.visible = k > 0.001; cargo.visible = kc < 0.999; },
    anchors: { ark: () => ark.userData.pt(30, 14.5, 11.45), cargo: () => cargo.userData.pt(20, 11, 11.5), a0: () => ark.userData.pt(-68.6, 0, 11.45), a1: () => ark.userData.pt(68.6, 0, 11.45), t0: () => ti.userData.pt(-134.5, 0, 14), t1: () => ti.userData.pt(134.5, 0, 14) } };
});

// ------------------------------------------------------------------ SCENE F: the hull flexes and leaks, a wooden schooner sails in with its pumps gushing (beats 10-11)
reg('ark_storm', () => {
  const g = new THREE.Group(); const e = env(STORM, { key: { ...STORM.key, ext: 150, target: [0, 0, -30], map: 4096 } });
  const sea = seaWorld(g, e, { amp: 1.7, speed: 1.4, steep: 1.2, rain: 1.3 });
  const ark = makeArk({ ramp: false }); g.add(ark); const L = 137.2, B = 22.9;
  const jets = [-48, -12, 22, 50].map((x) => { const j = makeJet(60, 0.28); g.add(j); return { j, x }; });
  const spray = makeJet(70, 0.4, 0xe8f4ff, 0.8); g.add(spray);
  const sc = makeSchooner(); g.add(sc); const SU = sc.userData; const sjets = SU.pumps.map(() => { const j = makeJet(46, 0.3); g.add(j); return j; });
  return { group: g, env: e, water: sea,
    cam: camRig([[0, [-70, 16, 86], [-30, 7, 0], 44], [[0, 0.7], [-10, 20, 104], [10, 7, -10], 44], [[1, 0.0], [34, 22, 122], [60, 12, -36], 46], [[1, 0.5], [70, 24, 150], [105, 20, -70], 46], [1, [118, 28, 160], [112, 22, -80], 46]]),
    update(lt, u, dur, t, B_) {
      sea.w.userData.update(t, sea.amp, sea.speed, sea.steep);
      const bendK = 1 - ease((lt - B_[1] - 0.6) / 1.0);
      const A = 1.9 * Math.sin(t * 2.6) * bendK; ark.userData.bend((x) => A * (1 - (x / (L / 2)) ** 2) * 0.9);
      ark.position.y = 0.55 * Math.sin(t * 2.1) * bendK + 0.2; ark.rotation.z = 0.025 * Math.sin(t * 1.7); ark.rotation.x = 0.04 * Math.sin(t * 1.3); ark.updateMatrixWorld(true);
      for (const o of jets) { const org = ark.userData.pt(o.x, 8.0 + 0.9 * Math.sin(o.x), B / 2 + 0.8); o.j.userData.update(t + o.x * 0.1, { origin: org, vel: V(0.5, 3.2, 7.0), spread: 0.8, g: 11, life: 1.1, rate: 1.4, scale: 1, on: 1 }); }
      spray.userData.update(t, { origin: ark.userData.pt(-12, 2.0, B / 2 + 4), vel: V(1.0, 12, 4), spread: 1.4, g: 12, life: 1.6, rate: 0.9, scale: 1 });
      const ks = ease((lt - B_[1] + 2.4) / 3.4); sc.position.set(lerp(360, 112, ks), 0, -80); bob(sc, sea.w, sc.position.x, -80, t, sea.amp, sea.speed, sea.steep, 0.35, 0); sc.updateMatrixWorld(true);
      SU.pumps.forEach((p, i) => { p.userData.lever.rotation.x = 0.5 * Math.sin(t * 7 + i * 2); const org = p.localToWorld(V(0, 1.4, 1.5)); sjets[i].userData.update(t + i * 0.3, { origin: org, vel: V(0.6, 7.5, 9.5), spread: 0.35, g: 12, life: 1.55, rate: 1.1, scale: 1.1, on: ks > 0.97 ? 1 : 0 }); });
      sea.rn.userData.update(t, V(...(window.__camPos || [0, 0, 0])), 1);
    },
    anchors: { seam: () => ark.userData.pt(22, 8.4, B / 2 + 0.8), mast6: () => sc.userData.pt(SU.masts[5], 52, 0), pump: () => SU.pumps[1].localToWorld(V(0, 1.4, 1.5)) } };
});

// ------------------------------------------------------------------ SCENE G: mountains and a searchlight (no trace), then the ark with the toy boat and POSSIBLE / IMPOSSIBLE (beats 12-13)
reg('ark_end', () => {
  const g = new THREE.Group(); const e = env(STORM, { key: { ...STORM.key, ext: 150, target: [0, 0, -40] } }); e.sky = { ...STORM.sky, mid: 0xb06a48, glowK: 0.85 }; e.fog = { color: 0xb88a72, near: 150, far: 900 };
  const sea = seaWorld(g, e, { amp: 0.45, speed: 0.9, steep: 1.0, rain: 0.6, clouds: true }); sea.w.position.y = 0;
  const land = Box(1700, 3, 400, mat(0x44546a, { flat: true }), 0.2); land.position.set(0, -1.2, -400); g.add(land);
  const R = rnd(12); const layers = [[-250, 0x5a6a8a, 70], [-380, 0x4a5a80, 110], [-520, 0x3a4a72, 150]];
  layers.forEach(([z, col, hmax], li) => { for (let i = -5; i <= 5; i++) { const h = hmax * (0.55 + 0.6 * R()); const m = makeMountain(h, h * (1.0 + 0.5 * R()), 60 + li * 20 + i, col, 0xe8eeff, 0.3); m.position.set(i * (80 + li * 40) + R() * 40, -2, z - R() * 30); g.add(m); } });
  const hero = makeMountain(80, 92, 99, 0x7a8aa8, 0xf0f4ff, 0.34); hero.position.set(40, -2, -190); g.add(hero);
  const sl = makeSearchlight(); sl.position.set(-14, 0, -120); g.add(sl);
  const ark = makeArk({ ramp: true }); ark.rotation.y = 0.35; g.add(ark);
  const toy = makeToyBoat(); toy.scale.setScalar(1.3); toy.position.set(-6, 0, -4); g.add(toy);
  const p1 = makePill('POSSIBLE', 0x2f9a56, 9, 3.2), p2 = makePill('IMPOSSIBLE', 0xc8382e, 11, 3.2); g.add(p1, p2); shade(p1); shade(p2);
  return { group: g, env: e, water: sea,
    cam: camRig([[0, [-30, 8, 20], [14, 34, -190], 42], [[1, 0.0], [-24, 8, 30], [10, 20, -150], 42], [[1, 0.5], [-14, 7, 44], [6, 10, -95], 42], [1, [-6, 8, 52], [6, 10, -95], 42]]),
    update(lt, u, dur, t, B_) { sea.w.userData.update(t, sea.amp, sea.speed, sea.steep); ark.position.x = lerp(330, 12, ease((lt - B_[1] + 0.6) / 3.0)); ark.position.z = -95; bob(ark, sea.w, ark.position.x, -95, t, sea.amp, sea.speed, sea.steep, 0.2, 0); bob(toy, sea.w, -6, -4, t, sea.amp, sea.speed, sea.steep, 1, 0.05);
      sl.userData.head.rotation.y = lerp(0.2, -1.2, ease(lt / B_[1])) + 0.5; sl.userData.head.rotation.z = lerp(0.28, 0.16, u) + 0.08 * Math.sin(t * 1.6);
      const pop = (t0) => easeOB((lt - t0) / 0.5); const cam = window.__cam, D = 14, put3 = (pl, x, y, sc, rz) => { cam.updateMatrixWorld(true); pl.position.copy(cam.localToWorld(V(x, y, -D))); pl.quaternion.copy(cam.quaternion); pl.rotateZ(rz); pl.scale.setScalar(Math.max(0.0001, sc)); };
      put3(p1, -1.55, -0.55 + 0.04 * Math.sin(t * 1.7), 0.255 * pop(B_[1] + 1.5), 0.025 * Math.sin(t * 1.3)); put3(p2, 1.3, -0.55 + 0.04 * Math.sin(t * 1.5 + 1), 0.255 * pop(B_[1] + 2.1), -0.025 * Math.sin(t * 1.1));
      sea.rn.userData.update(t, V(...(window.__camPos || [0, 0, 0])), 1); },
    anchors: { peak: at(hero, 0, 80, 0), p1: at(p1, 0, 0, 0), p2: at(p2, 0, 0, 0) } };
});
