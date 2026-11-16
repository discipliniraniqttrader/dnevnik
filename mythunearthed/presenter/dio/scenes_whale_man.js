// whale_man: Jonah's great fish, breath-holding, stomach, Bartley's sperm whale, logbook, beach.
import { THREE, V, clamp, mat, glow, woodMat, Sph, Box, Cyl, Cap, Cone, between, shade, rnd, lerp, sandTex, GRAD, poseArms, makeMountain, makeCloud, makeWater } from './kit.js';
import { makePill } from './props.js';
import { REG, reg, ease, easeO, easeOB, at, fixed, camRig, env, mixEnv, pillFront, popIn, bob, seaWorld, DUSK, STORM, WARMROOM, DAY } from './world.js';
import { person } from './folk.js';
import { makeWhale, rowboat, brig, stopwatch, gauge, logbook, stomach } from './things3.js';
import { scroll, lamp, table, rock } from './things.js';

const SEAENV = (k) => { const e = env(STORM, { key: { ...STORM.key, ext: 60, target: [0, 0, 0] } }); e.sky = { ...STORM.sky, mid: 0xc0704a, glowK: 0.9 }; e.sunDir = [-0.3, 0.08, -1]; e.fog = { color: 0xb88a72, near: 80, far: 700 }; return e; };
function shadowDisc(g, r = 14) { const m = new THREE.Mesh(new THREE.CircleGeometry(1, 32).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x06141c, transparent: true, opacity: 0.5, depthWrite: false })); m.scale.set(r * 1.6, 1, r * 0.7); m.position.y = 0.55; m.userData.noShadow = true; g.add(m); return m; }

reg('whale_sea', () => {
  const g = new THREE.Group(); const e = SEAENV(); const sea = seaWorld(g, e, { amp: 0.3, speed: 0.9, steep: 1.1, rain: 0.9 });
  const boat = rowboat(5); g.add(boat); const jn = person({ h: 1.4, shirt: 0xc8a070, pants: 0x6a4a30, hair: 0x2a1a10, cloth: 0xe8e0d0 }); jn.position.set(0, 0.4, 0); jn.rotation.y = 0.6; boat.add(jn); jn.scale.multiplyScalar(0.8); poseArms(jn, [0, 1.5, 0.3], [0, 1.5, 0.3]);
  const fish = makeWhale(30, 'fish'); g.add(fish); const sh = shadowDisc(g, 14);
  return { group: g, env: e, water: sea,
    cam: camRig([[0, [22, 6, 36], [-4, 2.5, 0], 46], [[0, 0.9], [20, 6.5, 34], [-4, 3.0, 0], 46], [[1, 0.3], [26, 12, 40], [-2, 0.5, 0], 46], [1, [30, 17, 42], [-2, 0, 0], 46]]),
    update(lt, u, dur, t, B) { sea.w.userData.update(t, sea.amp, sea.speed, sea.steep); sea.rn.userData.update(t, V(...(window.__camPos || [0, 0, 0])), 1); const up = ease((lt - 0.2) / 1.6) * (1 - ease((lt - B[1] + 0.2) / 1.2));
      fish.position.set(-7 - 3 * up, -10 + 12.5 * up, -2); fish.rotation.z = 0.35 * up; fish.rotation.y = 0.3; fish.userData.tail.rotation.y = 0.3 * Math.sin(t * 2.4); fish.visible = up > 0.01;
      const lift = up * 1.3; bob(boat, sea.w, 0, 0, t, sea.amp, sea.speed, sea.steep, 0.6, 0.3 + lift); boat.rotation.x += 0.12 * up; sh.visible = lt > B[1] - 0.6; sh.material.opacity = 0.5 * ease((lt - B[1] + 0.6) / 0.8); sh.position.set(-3, 0.45, 1); sh.rotation.y = 0.3; },
    anchors: { boat: at(boat, 0, 1.5, 0), fishHead: () => fish.localToWorld(V(13, 2, 0)), shadow: () => V(-3, 0.5, 1) } };
});

reg('whale_breath', () => {
  const g = new THREE.Group(); const e = env(WARMROOM, { key: { ...WARMROOM.key, ext: 4, target: [0, 1.4, 0], dir: [0.3, 0.6, 1.0], k: 2.4 }, hemi: { sky: 0xffe2c0, ground: 0x9a6a44, k: 1.4 } }); e.fog = { color: 0x3a2214, near: 8, far: 30 };
  const wall = Box(14, 8, 0.3, woodMat(1.4, 0.5, [120, 76, 40], { seed: 31 }), 0.03); wall.position.set(0, 3, -2.2); g.add(wall); const fl = Box(14, 0.2, 8, woodMat(1.2, 0.4, [150, 100, 58], { seed: 30 }), 0.02); fl.position.y = -0.1; g.add(fl);
  const p = person({ h: 1.8, shirt: 0x4a7bd0, pants: 0x39406a, hair: 0x4a2c18 }); g.add(p); const head = p.userData.parts.head; const sc = 1.8 / 1.27;
  const chk = [-1, 1].map(s => { const c = Sph(0.1, mat(0xf2b090), 1, 1, 1, 16); c.position.set(s * 0.2, -0.07, 0.2); head.add(c); return c; });
  const mouth = Sph(0.07, mat(0x4a1810), 1.2, 1.0, 0.5, 14); mouth.position.set(0, -0.12, 0.25); mouth.scale.setScalar(0.0001); head.add(mouth);
  const sw = stopwatch(1.0); sw.position.set(1.05, 1.15, 0.9); sw.rotation.y = -0.5; g.add(sw); const pst = Cyl(0.15, 0.2, 1.0, mat(0x6a4020), 10); pst.position.set(1.05, 0.55, 0.9); g.add(pst);
  shade(g);
  return { group: g, env: e,
    cam: camRig([[0, [0.9, 1.75, 4.6], [0.5, 1.45, 0], 36], [[0, 0.9], [0.7, 1.7, 4.3], [0.6, 1.4, 0], 36], [[1, 0.1], [0.9, 1.6, 4.8], [0.6, 1.4, 0], 38], [1, [0.7, 1.6, 4.4], [0.7, 1.4, 0], 38]]),
    update(lt, u, dur, t, B) { const puff = ease((lt - 0.4) / 0.8) * (lt < B[1] ? 1 : 1 - ease((lt - B[1] - 0.3) / 0.4)); chk.forEach(c => { c.scale.setScalar(1 + 0.7 * puff); c.position.x = Math.sign(c.position.x) * (0.2 + 0.04 * puff); c.position.z = 0.17 + 0.03 * puff; });
      const gasp = ease((lt - B[1] - 0.5) / 0.4); mouth.scale.setScalar(Math.max(0.0001, gasp * (0.9 + 0.25 * Math.sin(t * 9)))); head.rotation.x = -0.25 * gasp + 0.03 * Math.sin(t * 2); p.userData.parts.body.position.y = 0.02 * Math.sin(t * 9) * gasp;
      sw.userData.setSec(lt < B[1] ? 30 * ease(lt / (B[1] - 0.2)) : 30 + 30 * ease((lt - B[1]) / 3.0)); sw.rotation.y = -0.5 + 0.04 * Math.sin(t * 1.3); },
    anchors: { watch: () => sw.localToWorld(V(0, 0.9, 0.1)), face: at(head, 0, 0.35, 0.2) } };
});

reg('whale_inside', () => {
  const g = new THREE.Group(); const e = env(WARMROOM, { key: { ...WARMROOM.key, ext: 20, target: [0, -2, 0], dir: [0.2, 1.0, 0.6], k: 2.0, color: 0xffb0c0 }, hemi: { sky: 0xff9ab0, ground: 0x5a2a3a, k: 1.3 } }); e.fog = { color: 0x3a1020, near: 14, far: 44 }; e.sky = { top: 0x2a0c18, mid: 0x3a1020, hor: 0x4a1a28, below: 0x1a0810, sunCol: 0, glowK: 0, glowP: 10, sunSize: 0 };
  const st = stomach(); g.add(st); const gg = gauge(2.0); gg.position.set(0, 1.5, -3); g.add(gg); const dr = rnd(2);
  return { group: g, env: e,
    cam: camRig([[0, [-5, 0.5, 10], [0, 0.5, -2], 48], [[0, 0.9], [-2, 0.8, 9], [0, 1.0, -2], 48], [[1, 0.3], [4, -1.0, 8], [0, -3.2, 0], 50], [1, [6, -0.4, 6.5], [0, -3.5, 0], 50]]),
    update(lt, u, dur, t, B) { const k = ease((lt - 0.4) / 2.6); gg.userData.set(1 - 0.92 * k + 0.02 * Math.sin(t * 5)); gg.scale.setScalar(Math.max(0.0001, 2.0 * easeOB((lt - 0.2) / 0.5)) * (lt < B[1] ? 1 : 1 - ease((lt - B[1] + 0.1) / 0.6))); gg.visible = gg.scale.x > 0.01; st.userData.update(t, 0.35 + 0.65 * ease((lt - B[1] + 0.2) / 0.8)); },
    anchors: { gauge: at(gg, 0, 0.3, 0.1), pool: fixed(0, -4.0, 0), bubbles: fixed(2, -3.2, 0) } };
});

reg('whale_ship', () => {
  const g = new THREE.Group(); const e = env(DUSK, { key: { ...DUSK.key, ext: 70, target: [0, 0, 0] } }); e.sky = { ...DUSK.sky, top: 0x5a6aa8, mid: 0xf0a078, hor: 0xffdcb0 }; e.sunDir = [-0.3, 0.1, -1]; e.fog = { color: 0xf4c8a0, near: 100, far: 900 };
  const sea = seaWorld(g, e, { amp: 0.5, speed: 0.9, steep: 1.0, clouds: true }); const sh = brig(30); sh.position.set(-34, 0, -26); sh.rotation.y = 0.3; g.add(sh);
  const wh = makeWhale(24, 'sperm'); g.add(wh); const sailor = person({ h: 1.9, shirt: 0xf0f0f0, pants: 0x3a4a7a, hair: 0x4a2c18 }); sailor.position.set(2, 1.4, 0); g.add(sailor); poseArms(sailor, [0, 0.9, 0.3], [0, 0.9, 0.3]);
  const glowS = Sph(2.4, new THREE.MeshBasicMaterial({ color: 0xfff0b0, transparent: true, opacity: 0.0, depthWrite: false }), 1, 1.3, 1, 12); glowS.userData.noShadow = true; g.add(glowS);
  return { group: g, env: e, water: sea,
    cam: camRig([[0, [30, 6, 40], [-10, 4, -10], 44], [[0, 0.9], [34, 7, 36], [-4, 4, -8], 44], [[1, 0.3], [16, 6, 26], [8, 3, -6], 42], [1, [12, 5, 22], [8, 3, -6], 42]]),
    update(lt, u, dur, t, B) { sea.w.userData.update(t, sea.amp, sea.speed, sea.steep); bob(sh, sea.w, -34, -26, t, sea.amp, sea.speed, sea.steep, 0.4, 0); wh.position.set(6, 1.6 + 0.35 * Math.sin(t * 1.1), -8); wh.rotation.set(0, 0.5, 0.05 * Math.sin(t * 0.9)); wh.userData.tail.rotation.y = 0.25 * Math.sin(t * 1.8);
      const tr = ease((lt - B[1] - 0.3) / 1.0); wh.userData.setOpacity(1 - 0.72 * tr); sailor.visible = tr > 0.05; sailor.position.set(6 + 1.2, 1.9 + 0.35 * Math.sin(t * 1.1), -8 - 1.2); sailor.rotation.y = 0.5; glowS.position.copy(sailor.position).add(V(0, 1, 0)); glowS.material.opacity = 0.35 * tr; },
    anchors: { whale: () => wh.localToWorld(V(2, 5.5, 0)), ship: () => sh.localToWorld(V(0, 12, 0)), sailor: () => sailor.position.clone().add(V(0, 2.2, 0)) } };
});

reg('whale_end', () => {
  const g = new THREE.Group(); const e = env(DUSK, { key: { ...DUSK.key, ext: 50, target: [0, 0, 0], dir: [-0.3, 0.7, 0.9], k: 2.0 } }); e.sunDir = [0.1, 0.08, -1]; e.fog = { color: 0xf0b074, near: 60, far: 700 };
  const sea = seaWorld(g, e, { amp: 0.25, speed: 0.8, steep: 1.0, clouds: true }); const sand = new THREE.Mesh(new THREE.PlaneGeometry(300, 50).rotateX(-Math.PI / 2), new THREE.MeshToonMaterial({ map: sandTex(30, 9), gradientMap: GRAD })); sand.position.set(0, 0.3, 14); sand.receiveShadow = true; g.add(sand);
  const tb = table(1.6, 1.0, 0.7); tb.position.set(-14, 0.3, 4); g.add(tb); const lb = logbook(0.55, 0.38); lb.position.set(-14, 1.05, 4); lb.rotation.y = 0.2; g.add(lb); const lmp = lamp(2.2); lmp.position.set(-13.3, 1.05, 3.8); g.add(lmp);
  const lone = person({ h: 1.75, shirt: 0xa8805a, pants: 0x4a3a2a, hair: 0x2a1a10 }); lone.position.set(-3, 0.3, 5); lone.rotation.y = Math.PI; g.add(lone);
  const rk = rock(1.6, 0x9a8a78, 4); rk.position.set(5, 0.3, 4); g.add(rk); const sc = scroll(1.5, 1.0, { seed: 15, lines: 6 }); sc.position.set(5.2, 1.2, 5.3); sc.rotation.set(-0.5, -0.3, 0); g.add(sc);
  const boat = rowboat(5); g.add(boat); const fish = makeWhale(30, 'fish'); g.add(fish); fish.visible = false; const sd = shadowDisc(g, 13); sd.position.set(14, 0.45, -22);
  const p1 = makePill('PARABLE', 0x2f9a56, 11, 3.2), p2 = makePill('MIRACLE', 0xc8382e, 11, 3.2); g.add(p1, p2); shade(g);
  return { group: g, env: e, water: sea,
    cam: camRig([[0, [-11.5, 2.4, 9], [-14, 1.1, 4], 38], [[0, 0.9], [-11, 2.4, 9], [-13.6, 1.1, 4], 38], [[1, 0.3], [-1.2, 1.9, 11], [-3, 1.4, 5], 40], [[1, 0.9], [-0.5, 1.9, 10.6], [-3, 1.4, 5], 40], [[2, 0.3], [7.2, 2.3, 10], [5, 1.5, 4.5], 38], [[2, 0.9], [7.0, 2.2, 9.6], [5, 1.5, 4.5], 38], [[3, 0.3], [16, 4.5, 30], [14, 0.5, -20], 46], [[3, 1.0], [20, 6, 34], [14, 0.5, -22], 46]]),
    update(lt, u, dur, t, B) { sea.w.userData.update(t, sea.amp, sea.speed, sea.steep); lmp.userData.update(t); bob(boat, sea.w, 14, -22, t, sea.amp, sea.speed, sea.steep, 0.5, 0.2); boat.position.x = 14; boat.position.z = -22; boat.visible = lt > B[3] - 1.0; sd.visible = lt > B[3] - 1.0; sd.material.opacity = 0.5 * ease((lt - B[3] + 1.0) / 1.0);
      const pop = (t0) => easeOB((lt - t0) / 0.5); pillFront(p1, -1.3, 0.5, 0.24 * pop(B[3] + 1.2), 0.02 * Math.sin(t * 1.3), 14); pillFront(p2, 1.3, 0.5, 0.24 * pop(B[3] + 1.8), -0.02 * Math.sin(t * 1.1), 14); },
    anchors: { log: at(lb, 0, 0.3, 0), lone: at(lone, 0, 2.2, 0), scroll: at(sc, 0, 0.7, 0), fish: fixed(14, 0.6, -22) } };
});
