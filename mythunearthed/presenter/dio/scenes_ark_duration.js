// ark_duration: flood calendar (sea), ark resting on the mesa while the water falls, birds, then a window looking out.
import { THREE, V, clamp, mat, glow, woodMat, Sph, Box, Cyl, Cap, Cone, between, shade, rnd, lerp, makeWater, makeMountain, makeCloud, sandTex, GRAD, poseArms, makePerson, makeRain } from './kit.js';
import { makeArk, makePill, makeToyBoat } from './props.js';
import { REG, reg, ease, easeO, easeOB, at, fixed, camRig, env, mixEnv, pillFront, bob, seaWorld, DUSK, STORM, NIGHT, WARMROOM, popIn } from './world.js';
import { person } from './folk.js';
import { calendar, bird, windowRoom } from './things2.js';

const SUNRISE = { sky: { top: 0x5a6aa8, mid: 0xf09a78, hor: 0xffd8a0, below: 0x6a5a58, sunCol: 0xfff0c0, glowK: 0.5, glowP: 10, sunSize: 0.002 }, sunDir: [-0.6, 0.12, -1],
  fog: { color: 0xf6c8a0, near: 220, far: 1300 }, hemi: { sky: 0xffe0c8, ground: 0xa07a58, k: 1.0 }, key: { color: 0xffd8a8, k: 2.4, dir: [0.7, 0.6, 0.6], target: [0, 100, 0], ext: 150, far: 600, map: 4096 }, rim: { color: 0xffa860, k: 0.9, dir: [-0.3, 0.3, -1] }, water: 0x3a8ab8 };

reg('dur_flood', () => {
  const g = new THREE.Group(); const e = env(STORM, { key: { ...STORM.key, ext: 130, target: [0, 0, -20] } }); e.sunDir = [0.1, 0.07, -1]; const eS = env(DUSK, { key: { ...DUSK.key, ext: 130, target: [0, 0, -20] } }); eS.sunDir = [0.1, 0.1, -1]; eS.fog = { color: 0xf0b074, near: 200, far: 1200 };
  const eA = JSON.parse(JSON.stringify(e)); const sea = seaWorld(g, e, { amp: 0.7, speed: 1.0, steep: 1.0, rain: 1.3 });
  const ark = makeArk({ ramp: true }); ark.position.set(10, 0, -60); ark.rotation.y = 0.3; g.add(ark);
  const cal = calendar(15, 10, 0.62); cal.scale.setScalar(2.0); cal.position.set(-24, -14, -16); cal.rotation.y = 0.55; g.add(cal);
  const tiles = cal.userData; const BLUE = 0x4a9ad8, GOLD = 0xffc42e, TEAL = 0x3ab8a8;
  return { group: g, env: e, water: sea,
    cam: camRig([[0, [-20, 14, 44], [8, 14, -60], 40], [[1, 0.0], [-14, 12, 40], [-2, 10, -50], 40], [[2, 0.0], [-2, 14, 20], [-18, 8, -16], 44], [[3, 0.0], [20, 40, 70], [-6, 10, -40], 46], [[3, 1.0], [34, 50, 96], [-4, 8, -44], 48]]),
    update(lt, u, dur, t, B) {
      mixEnv(e, eA, eS, ease((lt - B[3] + 0.3) / 2.0)); sea.w.userData.update(t, sea.amp * (1 - 0.5 * ease((lt - B[3]) / 2)), sea.speed, sea.steep); sea.rn.userData.update(t, V(...(window.__camPos || [0, 0, 0])), 1 - 0.8 * ease((lt - B[3]) / 1.5));
      bob(ark, sea.w, 10, -60, t, sea.amp, sea.speed, sea.steep, 0.2, 0);
      const rise = easeO((lt - B[1] + 0.1) / 1.0); cal.position.y = lerp(-14, 0.2, rise); cal.visible = lt > B[1] - 0.2;
      const n2 = ease((lt - B[1] - 0.2) / 2.2) * 40; for (let i = 0; i < 150; i++) { let c = 0x6a665c, k = 0; if (i < n2) { c = BLUE; k = 1; } if (lt > B[2] + 0.3 && i === 46) { c = GOLD; k = 1 + 3 * (0.5 + 0.5 * Math.sin(t * 6)); } if (i >= 40 && i < 150) { const n4 = ease((lt - B[3] - 0.3) / 2.4) * 150; if (i < n4 && i !== 46) { c = TEAL; k = 1; } } tiles.set(i, c, k); }
      cal.userData.tiles[46].scale.setScalar(lt > B[2] + 0.3 ? 1.25 : 1);
    },
    anchors: { arkMid: () => ark.userData.pt(0, 14.6, 11.45), cal: () => cal.localToWorld(V(4.6, 6.8, 0.2)), day47: () => cal.localToWorld(V(tiles.tile * 1 * (46 % 15) + 0.31, tiles.tile * (9 - Math.floor(46 / 15)) + 0.31, 0.45)), calMid: () => cal.localToWorld(V(4.6, 3.1, 0.3)) } };
});

reg('dur_land', () => {
  const g = new THREE.Group(); const e = env(SUNRISE); const eA = JSON.parse(JSON.stringify(e));
  const sea = (() => { const w = makeWater(1600, 110, 0x3a8ab8); g.add(w); return w; })();
  const mesa = new THREE.Mesh(new THREE.CylinderGeometry(95, 280, 120, 11, 4), mat(0x9a7a5a, { flat: true })); mesa.position.y = 60; mesa.castShadow = mesa.receiveShadow = true; g.add(mesa);
  const gp = mesa.geometry.attributes.position; for (let i = 0; i < gp.count; i++) { const y = gp.getY(i); if (y > -59 && y < 59) { gp.setX(i, gp.getX(i) * (1 + 0.05 * Math.sin(i * 12.9))); gp.setZ(i, gp.getZ(i) * (1 + 0.05 * Math.cos(i * 7.7))); } } mesa.geometry.computeVertexNormals();
  const R = rnd(6); for (let i = 0; i < 40; i++) { const rk = Sph(2 + R() * 5, mat(0x8a6a4a, { flat: true }), 1, 0.7, 1, 6); const a = R() * 6.28, d = R() * 80; rk.position.set(Math.cos(a) * d, 120.5, Math.sin(a) * d); rk.castShadow = true; g.add(rk); }
  const mud = new THREE.Mesh(new THREE.CircleGeometry(330, 40).rotateX(-Math.PI / 2), new THREE.MeshToonMaterial({ map: (() => { const t = sandTex(30, 30); return t; })(), gradientMap: GRAD, color: 0xb89a78 })); mud.position.y = -30; g.add(mud);
  const ark = makeArk({ ramp: true }); ark.position.set(0, 121.5, 0); ark.rotation.set(0.0, 0.5, 0.03); g.add(ark);
  for (let i = 0; i < 7; i++) { const m = makeMountain(60 + R() * 70, 120 + R() * 60, 40 + i, 0x8a8aa8, 0xe8e8f0, 0.2); m.position.set(-500 + i * 170, -30, -520 - R() * 100); g.add(m); }
  const cl = []; for (let i = 0; i < 6; i++) { const c = makeCloud(i + 4, 0xffd0b0, 2.0 + R()); c.position.set((R() - .5) * 900, 190 + R() * 60, -420); g.add(c); }
  const raven = bird('raven'); raven.scale.setScalar(13); g.add(raven); const dove = bird('dove'); dove.scale.setScalar(13); g.add(dove);
  const crack = []; const hz = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), glow(0x000000)); // placeholder (none)
  const bow = () => ark.localToWorld(V(68, 12, 6));
  return { group: g, env: e,
    cam: camRig([[0, [-170, 190, 210], [0, 125, 0], 44], [[1, 0.0], [-190, 198, 160], [0, 125, 0], 44], [[1, 0.6], [-40, 205, 230], [20, 128, 0], 44], [[2, 0.0], [90, 200, 220], [20, 128, 0], 44], [[3, 0.0], [190, 170, 130], [10, 124, 0], 44], [[4, 0.0], [-60, 150, 190], [0, 100, 0], 48], [[4, 1.0], [-110, 160, 160], [0, 104, 0], 48]]),
    update(lt, u, dur, t, B) {
      sea.userData.update(t, 0.8, 1.0, 1.0); sea.position.y = lerp(121.0, -28, ease((lt - 0.3) / (B[4] - 0.3 + 0.8)));
      const bw = bow(); const out = V(1, 0.15, 0.4).normalize();
      const k6 = (lt - B[1]) / 3.0; raven.visible = lt > B[1] - 0.1 && lt < B[2] + 0.6; { const s = clamp01(k6); const d = 55 * Math.sin(s * Math.PI * 3) * (0.5 + 0.5 * Math.sin(s * Math.PI)); raven.position.set(bw.x + 8 + out.x * Math.abs(d), bw.y + 6 + 12 * Math.sin(s * 9), bw.z + out.z * Math.abs(d) * 0.8 + 18 * Math.sin(s * 5)); raven.rotation.y = -Math.atan2(out.z * Math.sign(Math.cos(s * Math.PI * 3)), out.x * Math.sign(Math.cos(s * Math.PI * 3))); raven.userData.flap(t, 10); }
      const tD = lt - B[2]; dove.visible = tD > -0.1 && tD < 4.5; { const fl = Math.floor(clamp(tD, 0, 3.3) / 1.1), s = (clamp(tD, 0, 3.3) - fl * 1.1) / 1.1; const dd = fl < 2 ? 50 * Math.sin(s * Math.PI) : 80 * s; dove.position.set(bw.x + 6 + out.x * dd, bw.y + 8 + 10 * Math.sin(s * 3 + fl), bw.z + out.z * dd + 14 * fl); dove.rotation.y = -Math.atan2(out.z * (fl < 2 && s > 0.5 ? -1 : 1), out.x * (fl < 2 && s > 0.5 ? -1 : 1)); dove.userData.flap(t, 11); dove.userData.leaf.visible = fl === 1 && s > 0.5; if (fl === 2 && s > 0.99) dove.visible = false; }
      e.sky.mid = new THREE.Color(0xf09a78).lerp(new THREE.Color(0xffc060), ease((lt - B[4]) / 2)).getHex();
    },
    anchors: { ark: () => ark.localToWorld(V(0, 16, 12)), raven: () => raven.position.clone(), dove: () => dove.position.clone(), ground: () => V(40, -26, 40), bowA: () => bow() } };
});
const clamp01 = (x) => Math.max(0, Math.min(1, x));

reg('dur_window', () => {
  const g = new THREE.Group(); const eA = env(STORM, { key: { ...STORM.key, ext: 20, target: [0, 1.5, -2], dir: [0.3, 0.7, 1.0], k: 2.2 }, hemi: { sky: 0xffdcc0, ground: 0xa07a58, k: 1.2 } }); eA.fog = { color: 0x8a7a78, near: 30, far: 520 };
  const eB = env(DUSK, { key: { ...DUSK.key, ext: 20, target: [0, 1.5, -2], dir: [0.3, 0.7, 1.0], k: 2.2 } }); eB.fog = { color: 0xf0b074, near: 80, far: 900 }; eB.sunDir = [0.1, 0.12, -1]; const e = JSON.parse(JSON.stringify(eA));
  const room = windowRoom(); g.add(room);
  const out = new THREE.Group(); out.position.z = -3; g.add(out);
  const sea = seaWorld(out, e, { amp: 0.35, speed: 0.8, steep: 1.0, rain: 0.9, clouds: true }); sea.w.position.y = -8;
  const ark = makeArk({ ramp: false }); ark.position.set(-20, -8, -250); ark.rotation.y = 1.05; out.add(ark);
  const R = rnd(14); const ridge = makeMountain(70, 120, 77, 0x7a8aa8, 0xf0f4ff, 0.3); ridge.position.set(60, -8, -330); out.add(ridge); const ridge2 = makeMountain(50, 100, 78, 0x8a96b0, 0xf0f4ff, 0.2); ridge2.position.set(-90, -8, -300); out.add(ridge2);
  const pr = person({ h: 1.75, shirt: 0xc8603a, pants: 0x3a3a60, hair: 0x2a1a10 }); pr.position.set(0.5, 0, -1.4); pr.rotation.y = Math.PI + 0.2; g.add(pr); poseArms(pr, [0.2, 0.2, 0.9], [-0.1, 0.3, 0.2]);
  const sofa = Box(2.2, 0.5, 0.9, mat(0x8a3a2a), 0.12); sofa.position.set(-2.4, 0.25, 0.6); g.add(sofa); const rug = Box(3, 0.04, 2.2, mat(0x9a4a3a), 0.02); rug.position.set(0, 0.02, -0.2); g.add(rug);
  const p1 = makePill('FORTY DAYS', 0xc8382e, 11, 3.2), p2 = makePill('A YEAR', 0x2f9a56, 9, 3.2); g.add(p1, p2);
  shade(g);
  return { group: g, env: e,
    cam: camRig([[0, [1.4, 1.7, 3.6], [0.2, 1.6, -2.0], 62], [[0, 0.9], [0.9, 1.7, 2.8], [0.1, 1.7, -2.4], 58], [[1, 0.3], [0.4, 1.8, 0.0], [0, 2.0, -6], 56], [[1, 0.9], [0, 2.2, -3.5], [0, 5, -120], 50], [[2, 0.2], [0, 3, -8], [-2, 8, -200], 46], [[2, 1.0], [0, 4, -12], [-2, 8, -200], 46]]),
    update(lt, u, dur, t, B) { mixEnv(e, eA, eB, ease((lt - B[1] - 0.8) / 2.6)); sea.w.userData.update(t, sea.amp, sea.speed, sea.steep); sea.rn.userData.update(t, V(...(window.__camPos || [0, 0, -3])), 1 - 0.85 * ease((lt - B[1]) / 3)); bob(ark, sea.w, -20, -253, t, sea.amp, sea.speed, sea.steep, 0.2, -8);
      { const kk = 1 - ease((lt - B[1] + 0.3) / 0.9); pr.scale.setScalar(Math.max(0.0001, kk) * 1.378); pr.visible = kk > 0.01; } const pop = (t0) => easeOB((lt - t0) / 0.5); pillFront(p1, -1.5, -0.62 + 0.04 * Math.sin(t * 1.5), 0.26 * pop(B[2] + 1.6), 0.02 * Math.sin(t * 1.3)); pillFront(p2, 1.35, -0.62 + 0.04 * Math.sin(t * 1.7 + 1), 0.26 * pop(B[2] + 2.2), -0.02 * Math.sin(t * 1.1)); },
    anchors: { person: at(pr, 0, 1.6, 0), ridge: () => V(60, 60, -333), arkW: () => ark.userData.pt(0, 14, 11) } };
});
