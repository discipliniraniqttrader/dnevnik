// furnace: one night courtyard stage, vignettes along +x: kiln & king, bricks, oven, fire column, sun vs thermometers, scribe, soldiers + bound men, cut-away kiln with four men, tablet, silhouettes.
import { THREE, V, clamp, mat, glow, woodMat, Sph, Box, Cyl, Cap, Cone, between, shade, rnd, lerp, GRAD, poseArms, makeMountain } from './kit.js';
import { makePill } from './props.js';
import { REG, reg, ease, easeO, easeOB, at, fixed, camRig, env, mixEnv, pillFront, popIn, FIRENIGHT } from './world.js';
import { person, spear, walkCycle } from './folk.js';
import { tablet, lamp, table, rock } from './things.js';
import { fire, kiln, oven, thermo } from './things4.js';
import { brickTex } from './bldg.js';

reg('fur_night', () => {
  const g = new THREE.Group(); const e = env(FIRENIGHT, { key: { ...FIRENIGHT.key, k: 2.3, ext: 70, target: [47, 0, 0], dir: [0.15, 0.6, 1.0], far: 240, map: 4096 }, hemi: { ...FIRENIGHT.hemi, k: 1.1 }, fog: { color: 0x2a1c22, near: 70, far: 320 } });
  const tex = brickTex(11).clone(); tex.needsUpdate = true; tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.repeat.set(30, 6); tex.colorSpace = THREE.SRGBColorSpace;
  const floor = new THREE.Mesh(new THREE.BoxGeometry(124, 0.6, 30), new THREE.MeshToonMaterial({ map: tex, gradientMap: GRAD, color: 0x8a7a76 })); floor.position.set(47, -0.3, 2); floor.receiveShadow = true; g.add(floor);
  const wall = new THREE.Mesh(new THREE.BoxGeometry(124, 9, 1.2), new THREE.MeshToonMaterial({ map: tex, gradientMap: GRAD, color: 0x6a5a56 })); wall.position.set(47, 4.5, -9); g.add(wall); for (let x = -12; x < 110; x += 9) { const cr = Box(5, 1.4, 1.4, mat(0x6a5a56), 0.2); cr.position.set(x, 9.7, -9); g.add(cr); }
  const R = rnd(3); for (let i = 0; i < 70; i++) { const s = Sph(0.18, glow(0xdde6ff), 1, 1, 1, 5); s.position.set(-20 + R() * 140, 20 + R() * 40, -60); s.userData.noShadow = true; g.add(s); }
  const k1 = kiln(); k1.position.set(0, 0, 0); g.add(k1);
  const king = person({ h: 1.9, shirt: 0x6a2a8a, robe: 0x6a2a8a, sash: 0xf2c23c, crown: true, beard: 0x2a1a10, hair: 0x2a1a10 }); king.position.set(-6.5, 0, 3.5); king.rotation.y = Math.PI / 2 - 0.2; g.add(king); poseArms(king, [-1.45, 0.05, 0.05], [0.1, 0.1, 0.1]);
  const stacks = []; const workers = [0, 1, 2].map(i => { const w = person({ h: 1.75, shirt: [0x4a7bd0, 0xd8503a, 0x3a8a5a][i], pants: 0xb89868, hair: 0x2a1a10, cloth: 0xe8e0d0 }); w.position.set(7 + i * 2.4, 0, 4.5); w.rotation.y = -0.4; g.add(w); const st = new THREE.Group(); for (let j = 0; j < 8; j++) { const b = Box(0.45, 0.22, 0.28, mat(0xc8855a), 0.03); b.position.set((j % 2) * 0.2 - 0.1, 0.12 + Math.floor(j / 2) * 0.22, 0); st.add(b); } st.position.set(7 + i * 2.4 + 1.1, 0, 5.4); g.add(st); stacks.push(st); return w; });
  const tb = table(1.4, 0.9, 0.6); tb.position.set(15, 0, 3.5); g.add(tb); const ov = oven(1.0); ov.position.set(15, 0.65, 3.5); g.add(ov);
  const pit = Cyl(3.0, 3.3, 0.6, mat(0x4a3a34), 24); pit.position.set(25, 0.3, 2); g.add(pit); const col = fire(13, 4.2, 9, 12); col.position.set(25, 0.6, 2); g.add(col);
  const th1 = thermo(6.3, 1.0), th2 = thermo(5.5, 1.0); th1.position.set(34, 0, 3); th2.position.set(38, 0, 3); g.add(th1, th2); const sun = Sph(3.2, new THREE.MeshBasicMaterial({ color: 0xfff0a0, fog: false }), 1, 1, 1, 24); sun.position.set(36.5, 9.5, -3); g.add(sun); sun.userData.noShadow = true; const halo = Sph(4.4, new THREE.MeshBasicMaterial({ color: 0xffc040, transparent: true, opacity: 0.35, fog: false, depthWrite: false }), 1, 1, 1, 20); halo.position.copy(sun.position); halo.userData.noShadow = true; g.add(halo);
  const tb2 = table(2.2, 1.2, 0.8); tb2.position.set(47, 0, 3.5); g.add(tb2); const tab = tablet(0.9, 0.65, { seed: 21, rows: 0 }); tab.position.set(47, 0.89, 3.5); g.add(tab); const marks = []; for (let i = 0; i < 7; i++) { const m = Box(0.05, 0.04, 0.2, mat(0x3a2410), 0.01); m.position.set(47 - 0.33 + i * 0.11, 0.935, 3.5); m.scale.setScalar(0.0001); g.add(m); marks.push(m); } const lm = lamp(1.6); lm.position.set(48.2, 0.85, 3.2); g.add(lm); const scr = person({ h: 1.7, shirt: 0xd8b070, pants: 0x6a5a40, hair: 0x2a1a10, cloth: 0xe8e0d0 }); scr.position.set(47, 0, 1.9); scr.rotation.y = 0; g.add(scr); poseArms(scr, [-0.9, 0.1, 0.4], [-0.9, 0.1, 0.4]);
  const k2 = kiln(); k2.position.set(60, 0, 0); g.add(k2);
  const sold = [0, 1, 2].map(i => { const s = person({ h: 1.85, shirt: 0xa83a2a, pants: 0x4a3a2a, hair: 0x2a1a10, helmet: 0xc0c8d0, crest: 0xc0392b }); s.position.set(56.5 + i * 3.4, 0, 9.5); s.rotation.y = Math.PI; g.add(s); return s; });
  const bound = [0, 1, 2].map(i => { const b = person({ h: 1.7, shirt: [0xe8e0d0, 0xe0d0b0, 0xd8d0c0][i], pants: 0x6a5a40, hair: 0x2a1a10, beard: 0x2a1a10 }); b.position.set(57.5 + i * 2.5, 0, 6.8); b.rotation.y = Math.PI; g.add(b); poseArms(b, [0.1, 0.12, 0.1], [0.1, 0.12, 0.1]); const rp = new THREE.Mesh(new THREE.TorusGeometry(0.22, 0.03, 6, 16), mat(0x8a6a3a)); rp.rotation.x = Math.PI / 2; rp.position.set(0, 0.62, 0); b.userData.parts.body.add(rp); return b; });
  const rope = []; for (let i = 0; i < 2; i++) { const r = between(V(57.5 + i * 2.5, 1.0, 6.8), V(59.5 + i * 2.5, 1.0, 6.8), 0.03, mat(0x8a6a3a), g); rope.push(r); }
  const k3 = kiln({ cut: true }); k3.position.set(73, 0, 0); k3.rotation.y = 0.0; g.add(k3);
  const four = [-1.6, -0.55, 0.55, 1.6].map((x, i) => { const p = person({ h: 1.95, shirt: i === 3 ? 0xfff0b0 : 0x2a2018, pants: i === 3 ? 0xfff0b0 : 0x1a1410, hair: 0x120a08, skin: i === 3 ? 0xffe8c0 : 0x3a2418 }); p.position.set(x * 0.95 + 73, 0.62, 0.9 + (i % 2) * 0.3); g.add(p); return p; });
  const aura = Sph(0.8, new THREE.MeshBasicMaterial({ color: 0xffe8a0, transparent: true, opacity: 0.25, depthWrite: false, fog: false }), 1, 1.6, 0.8, 14); aura.userData.noShadow = true; g.add(aura);
  const tb3 = table(2.6, 1.4, 0.8); tb3.position.set(85, 0, 3.5); g.add(tb3); const tab2 = tablet(1.4, 1.0, { seed: 33, rows: 6 }); tab2.position.set(85, 0.89, 3.5); g.add(tab2); const lm2 = lamp(2.0); lm2.position.set(86.3, 0.85, 3.3); g.add(lm2);
  const k4 = kiln(); k4.position.set(98, 0, 0); g.add(k4); const sil = [-1.2, 0, 1.2].map(x => { const s = person({ h: 1.75, shirt: 0x120e0c, pants: 0x0c0a08, hair: 0x080606, skin: 0x1a100c }); s.position.set(98 + x, 0, 4.6); s.rotation.y = Math.PI; g.add(s); return s; });
  const p1 = makePill('LITERAL', 0xc8382e, 11, 3.2), p2 = makePill('IDIOM', 0x2f9a56, 9, 3.2); g.add(p1, p2);
  shade(g); const lights = [lm, lm2];
  const KC = (x, z) => [x, z];
  return { group: g, env: e,
    cam: camRig([[0, [5, 4.4, 22], [0, 4.2, 0], 46], [[0, 0.9], [3, 4.6, 21], [-1, 4.4, 0], 46], [[1, 0.3], [-1.5, 2.2, 12.5], [-5.5, 1.6, 3.6], 42], [[1, 0.9], [-1.0, 2.3, 12], [-5.0, 1.7, 3.6], 42], [[2, 0.3], [11.5, 2.0, 12], [9, 1.2, 4.8], 40], [[2, 0.9], [12.5, 2.0, 11], [10, 1.2, 4.8], 40],
      [[3, 0.3], [16.2, 1.5, 8.2], [15, 0.95, 3.5], 36], [[3, 0.9], [16.0, 1.4, 7.6], [15, 0.95, 3.5], 36], [[4, 0.3], [22, 5.5, 17], [25, 5.5, 2], 46], [[4, 0.9], [24, 5.5, 16], [25, 6, 2], 46], [[5, 0.3], [35, 6.0, 20], [36, 5.5, 0], 46], [[5, 0.9], [36, 6.0, 19], [36.5, 5.5, 0], 46],
      [[6, 0.3], [46, 2.6, 8.5], [47, 0.95, 3.5], 38], [[6, 0.9], [46.6, 2.6, 8.2], [47, 0.95, 3.5], 38], [[7, 0.3], [58, 3.0, 20], [59, 1.4, 6], 46], [[7, 0.9], [59, 3.0, 19], [59.5, 1.4, 6], 46], [[8, 0.3], [62, 2.6, 17], [60, 1.4, 4], 44], [[8, 0.9], [61, 2.4, 16], [60, 1.4, 4], 44], [[9, 0.3], [72, 2.8, 10.5], [73, 1.9, 0.5], 42], [[9, 0.9], [73, 3.0, 9.6], [73, 2.0, 0.5], 42],
      [[10, 0.3], [85, 2.4, 9], [85, 0.95, 3.5], 38], [[10, 0.9], [85, 2.4, 8.5], [85, 0.95, 3.5], 38], [[11, 0.2], [98, 3.2, 17], [98, 2.4, 0], 46], [[11, 1.0], [98, 3.4, 15], [98, 2.4, 0], 46]]),
    update(lt, u, dur, t, B) {
      k1.userData.update(t); k2.userData.update(t + 3, lt > B[7] - 0.5 ? (lt > B[8] + 0.6 ? 1.35 : 1) : 1); k3.userData.update(t + 5); k4.userData.update(t + 7); col.userData.update(t + 1, ease((lt - B[4] + 0.3) / 0.9)); col.visible = lt > B[4] - 0.3;
      popIn(oven_w(tb), lt, 0, 1, 0.1); const f = 1; workers.forEach((w, i) => { w.position.y = 0.03 * Math.abs(Math.sin(t * 3 + i)); poseArms(w, [-0.7, 0.1, 0.5], [-0.7, 0.1, 0.5]); });
      stacks.forEach((s, i) => { s.children.forEach((b, j) => { b.visible = lt > B[2] - 0.2 + i * 0.2 + j * 0.05; }); });
      const hv = ease((lt - B[5] - 0.3) / 1.4); th1.userData.set(hv); th2.userData.set(hv * 5.5 / 6.3); sun.visible = halo.visible = lt > B[5] - 0.5; sun.scale.setScalar(Math.max(0.0001, easeOB((lt - B[5] + 0.4) / 0.8))); halo.scale.copy(sun.scale).multiplyScalar(1.0 + 0.05 * Math.sin(t * 3)); th1.visible = th2.visible = lt > B[5] - 0.6;
      marks.forEach((m, i) => { m.scale.setScalar(Math.max(0.0001, easeOB((lt - B[6] - 0.4 - i * 0.35) / 0.3))); });
      lights.forEach(l => l.userData.update(t));
      const fall = ease((lt - B[8] - 0.5) / 0.9); sold.forEach((s, i) => { s.rotation.x = -fall * 1.45; s.position.set(56.5 + i * 3.4, 0.1 + 0.5 * fall * 0, 9.5 - 0.0); s.position.y = fall * 0.6; s.position.z = 9.5 - fall * 2.8; });
      bound.forEach((b, i) => { b.position.z = 6.8 - ease((lt - B[7] - 0.8 - i * 0.2) / 1.0) * 0 + 0; const th = ease((lt - B[7] - 1.2 - i * 0.3) / 0.9); b.position.x = 57.5 + i * 2.5 + (59.8 - (57.5 + i * 2.5)) * th * 0.0; b.position.y = th * 0.0; b.visible = lt < B[8] + 0.2 || true; });
      const ag = 1 - ease((lt - B[9] - 0.2) / 1.0) * 0; aura.position.set(73 + 1.52, 2.0, 1.1); aura.material.opacity = 0.22 + 0.08 * Math.sin(t * 4); four.forEach((p, i) => { p.position.y = 0.62 + 0.04 * Math.sin(t * 2 + i); const w = lt > B[9] - 0.2; p.visible = true; walkCycle(p, t + i * 1.3, 2.5, 0.25); p.rotation.y = i % 2 ? 0.3 : -0.3; });
      const pop = (t0) => easeOB((lt - t0) / 0.5); pillFront(p1, -1.3, 2.4, 0.24 * pop(B[11] + 1.0), 0.02 * Math.sin(t * 1.3), 14); pillFront(p2, 1.3, 2.4, 0.24 * pop(B[11] + 1.6), -0.02 * Math.sin(t * 1.1), 14);
    },
    anchors: { flame: () => k1.localToWorld(V(0, 10.4, -0.6)), king: at(king, 0, 2.3, 0), brickS: at(stacks[1], 0, 1.4, 0), ovenA: () => ov.localToWorld(V(0, 0.75, 0)), colA: () => V(25, 12, 2), thA: () => th1.localToWorld(V(0, 7.3, 0)), thB: () => th2.localToWorld(V(0, 6.5, 0)), sunA: () => sun.position.clone().add(V(0, 3.7, 0)), tabA: () => V(47, 1.4, 3.5), mouth: () => k2.localToWorld(V(0, 2.9, 3.4)), men: () => bound[1].localToWorld(V(0, 2.2, 0)), hatch: () => k3.localToWorld(V(0, 6.2, 0)), four: () => V(74.6, 3.5, 0), tab2: () => V(85, 1.6, 3.5), glow: () => k4.localToWorld(V(0, 3.6, 3.2)) } };
});
const oven_w = (o) => o;
