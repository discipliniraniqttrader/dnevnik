// babel_tower: Etemenanki ziggurat (91 m), tablet, high-rise comparison, demolition, pit, glory.
import { THREE, V, clamp, mat, glow, woodMat, Sph, Box, Cyl, Cap, Cone, between, shade, rnd, lerp, sandTex, GRAD, poseArms, makeMountain, makeCloud } from './kit.js';
import { makePill } from './props.js';
import { REG, reg, ease, easeO, easeOB, at, fixed, camRig, env, mixEnv, pillFront, popIn, DUSK, STORM } from './world.js';
import { person, walkCycle, spear } from './folk.js';
import { ziggurat, highrise, cityWall, brickTex } from './bldg.js';
import { tablet } from './things.js';
import { dustPuffs } from './things2.js';

const ZW = 91, ZH = 91;
function palm(h = 12) { const g = new THREE.Group(); const t = Cyl(h * 0.03, h * 0.05, h, mat(0x7a5a38), 8); t.position.y = h / 2; t.rotation.z = 0.1; g.add(t); for (let i = 0; i < 7; i++) { const l = Cone(h * 0.05, h * 0.5, mat(0x4a8a3a), 5); l.position.set(Math.cos(i) * h * 0.18, h + 0.2, Math.sin(i) * h * 0.18); l.rotation.set(Math.sin(i) * 1.1, 0, -Math.cos(i) * 1.1); g.add(l); } shade(g); return g; }
function world(g, e) {
  const gnd = new THREE.Mesh(new THREE.PlaneGeometry(1600, 1200).rotateX(-Math.PI / 2), new THREE.MeshToonMaterial({ map: sandTex(80, 60), gradientMap: GRAD })); gnd.receiveShadow = true; g.add(gnd);
  const wl = cityWall(520, 14); wl.position.set(0, 0, -150); g.add(wl); const R = rnd(7);
  for (let i = 0; i < 10; i++) { const p = palm(10 + R() * 5); p.position.set(-200 + i * 45 + R() * 20, 0, -120 + R() * 8); g.add(p); }
  for (let i = 0; i < 8; i++) { const m = makeMountain(30 + R() * 30, 70 + R() * 50, 120 + i, 0xa07a60, 0xd8b090, 0.0); m.position.set(-420 + i * 120, 0, -420 - R() * 60); g.add(m); }
  for (let i = 0; i < 5; i++) { const c = makeCloud(i + 3, 0xffb482, 2.0 + R()); c.position.set(-400 + i * 200, 110 + R() * 40, -500); g.add(c); }
}
const RAMP = 40;
function addRamp(z, g) { const sh = z.userData.sh, a = Math.atan2(sh, RAMP); const r = Box(ZW * 0.1, 0.9, Math.hypot(RAMP, sh), mat(0xd8b078), 0.1); r.position.set(0, sh / 2, ZW / 2 + RAMP / 2); r.rotation.x = a; r.castShadow = true; g.add(r); return r; }
function brickCarrier(i, seed) { const p = person({ h: 1.7, shirt: [0xd8503a, 0x3a8a5a, 0xe0a030, 0x4a7bd0][i % 4], pants: 0xb89868, hair: 0x2a1a10, cloth: 0xe8e0d0 }); const b = Box(0.5, 0.3, 0.4, mat(0xc8855a), 0.04); b.position.set(0, 1.45, -0.1); p.add(b); b.scale.setScalar(1.27 / 1.7); return p; }
function sunSet(e) { e.sunDir = [-0.6, 0.12, -1]; e.fog = { color: 0xf0b074, near: 300, far: 1500 }; e.key = { ...e.key, ext: 150, target: [0, 40, 40], dir: [0.5, 0.7, 0.8], k: 2.2, map: 4096 }; }

reg('bab_site', () => {
  const g = new THREE.Group(); const e = env(DUSK); sunSet(e); world(g, e);
  const z = ziggurat({ W: ZW, H: ZH }); g.add(z); addRamp(z, g);
  const sh = z.userData.sh; const carriers = Array.from({ length: 12 }, (_, i) => { const c = brickCarrier(i, i); g.add(c); return c; }); const pots = [0, 1, 2].map(i => { const p = Cyl(0.5, 0.45, 0.9, mat(0x2a2420), 12); p.position.set(-9 + i * 1.3, 0.45, ZW / 2 + 12); p.castShadow = true; g.add(p); return p; });
  const idle = Array.from({ length: 7 }, (_, i) => { const p = person({ h: 1.7, shirt: 0xd8b070, pants: 0x6a5a40, hair: 0x2a1a10 }); p.position.set(-28 + i * 9 + (i % 2) * 3, 0, ZW / 2 + 26 + (i % 3) * 5); p.rotation.y = 3.14 + (i - 3) * 0.1; g.add(p); return p; });
  return { group: g, env: e,
    cam: camRig([[0, [95, 34, 190], [0, 40, 20], 44], [[0, 0.9], [88, 32, 180], [0, 42, 20], 44], [[1, 0.3], [14, 5.5, 138], [4, 8, 76], 42], [[1, 0.95], [18, 6.5, 132], [4, 9, 74], 42], [[2, 0.4], [-60, 52, 200], [0, 50, 10], 46], [[2, 1.0], [-80, 62, 190], [0, 54, 10], 46]]),
    update(lt, u, dur, t, B) { carriers.forEach((c, i) => { const per = 22; const d = ((t * 2.2 + i * 1.9) % per) / per; const zz = ZW / 2 + RAMP - d * RAMP; c.position.set(-3 + (i % 3) * 3, sh * d + 0.45, zz); c.rotation.y = Math.PI; walkCycle(c, t + i, 7, 0.4); c.visible = lt > B[1] - 0.3 || i < 3; });
      idle.forEach((p, i) => { p.position.y = 0.04 * Math.abs(Math.sin(t * 3 + i)); }); },
    anchors: { H0: () => V(ZW / 2 + 7, 0, ZW / 2 + 7), H1: () => V(ZW / 2 + 7, ZH, ZW / 2 + 7), top: () => z.userData.pt(0, ZH + 6, 0), brick: () => V(-3, sh * 0.5 + 1.5, ZW / 2 + RAMP * 0.5) } };
});

reg('bab_size', () => {
  const S_ = { lt: 0, B: [0, 1, 2, 3, 4, 5, 6] };
  const g = new THREE.Group(); const e = env(DUSK); sunSet(e); world(g, e);
  const z = ziggurat({ W: ZW, H: ZH }); g.add(z); addRamp(z, g); const sh = z.userData.sh;
  const tb = tablet(3.2, 2.2, { seed: 4, rows: 8 }); const tabG = new THREE.Group(); tb.rotation.x = Math.PI / 2; tb.position.y = 1.4; tabG.add(tb); const stand = Box(4, 0.5, 1.2, mat(0x8a7a68), 0.08); stand.position.y = 0.25; tabG.add(stand); tabG.position.set(-20, 0, 80); tabG.rotation.y = 0.35; tabG.rotation.x = 0; g.add(tabG); shade(tabG);
  const hr = highrise(30, 91 / 30, 30); hr.position.set(70, 0, 78); g.add(hr);
  const scaf = new THREE.Group(); const wm = mat(0x8a5a30); for (let x = -40; x <= 40; x += 10) for (let lv = 0; lv < 3; lv++) { const p = Cyl(0.25, 0.25, sh * (lv + 1) + 1, wm, 6); p.position.set(x, (sh * (lv + 1) + 1) / 2, ZW / 2 + 4 + lv * 0.0); scaf.add(p); } for (let lv = 1; lv <= 3; lv++) { const pl = Box(ZW * 0.9, 0.4, 3, mat(0xb88858), 0.05); pl.position.set(0, sh * lv, ZW / 2 + 3); scaf.add(pl); } g.add(scaf); shade(scaf);
  const wk = Array.from({ length: 8 }, (_, i) => { const p = person({ h: 1.7, shirt: 0xd8503a, pants: 0xb89868, hair: 0x2a1a10, cloth: 0xe8e0d0 }); p.position.set(-30 + i * 8, sh * (1 + i % 3) + 0.2, ZW / 2 + 3); g.add(p); return p; });
  const bars = z.userData.stages.map(s => s.material);
  return { group: g, env: e,
    cam: camRig([[0, [-14, 2.6, 78], [-20, 1.6, 80], 38], [[0, 0.5], [-14, 3.0, 82], [-18, 2.2, 74], 40], [[0, 0.95], [10, 38, 190], [0, 28, 40], 44], [[1, 0.3], [30, 4, 150], [0, 55, 40], 50], [[1, 0.95], [34, 6, 150], [0, 56, 40], 50], [[2, 0.2], [90, 50, 240], [30, 42, 60], 46], [[2, 0.95], [110, 56, 250], [30, 46, 60], 46], [[3, 0.3], [-40, 46, 190], [0, 36, 40], 46], [[3, 0.95], [-62, 50, 180], [0, 38, 40], 46], [[4, 0.2], [74, 52, 190], [72, 46, 78], 44], [[4, 0.95], [78, 52, 185], [72, 46, 78], 44], [[5, 0.3], [70, 40, 190], [0, 40, 40], 46], [[5, 1.0], [30, 38, 175], [0, 42, 40], 46]]),
    update(lt, u, dur, t, B) {
      S_.lt = lt; S_.B = B; popIn(tabG, lt, 0.2, 1, 0.7); hr.visible = lt > B[2] - 0.4 && lt < B[5] - 0.2; hr.position.y = lerp(-95, 0, easeO((lt - B[2] + 0.4) / 1.4)); const nl = Math.floor(ease((lt - B[4] - 0.3) / 3.0) * 30 + 0.001); hr.userData.setLit(lt > B[4] - 0.2 ? nl : (lt > B[2] ? 30 : 0), 0xffd060);
      scaf.visible = lt > B[3] - 0.2 && lt < B[5] - 0.3; scaf.scale.y = Math.max(0.0001, ease((lt - B[3] + 0.2) / 0.9)); wk.forEach((w, i) => { w.visible = scaf.visible && lt > B[3] + 0.5; w.position.y = sh * (1 + i % 3) * scaf.scale.y + 0.2 + 0.05 * Math.abs(Math.sin(t * 4 + i)); });
      bars.forEach((m, i) => { const on = clamp(1 - Math.abs((lt - (B[5] + 0.4 + i * 0.4)) / 0.5), 0, 1) * (lt > B[5] ? 1 : 0); m.emissive = m.emissive || new THREE.Color(); m.emissive.setRGB(0.7 * on, 0.45 * on, 0.1 * on); });
      z.userData.temple.children[0].material.emissiveIntensity = 0.4 + 0.5 * Math.sin(t * 3);
    },
    anchors: { W0: () => V(-ZW / 2, 0.3, ZW / 2 + 5), W1: () => V(ZW / 2, 0.3, ZW / 2 + 5), H0: () => V(ZW / 2 + 7, 0, ZW / 2 + 7), H1: () => V(ZW / 2 + 7, ZH, ZW / 2 + 7), tablet: () => tabG.localToWorld(V(0, 1.4, 0.2)), hr0: () => hr.localToWorld(V(-16, 0, 16)), hr1: () => hr.localToWorld(V(-16, 91, 16)), hrTop: () => hr.localToWorld(V(0, 94, 0)), scaf: () => V(0, sh * 2.5, ZW / 2 + 4), floors: () => hr.localToWorld(V(0, 91 * Math.max(0.05, Math.min(1, ease((S_.lt - S_.B[4] - 0.3) / 3.0))), 15.5)), temple: () => z.userData.pt(0, ZH + 8, 0) } };
});

reg('bab_end', () => {
  const g = new THREE.Group(); const e = env(STORM, { key: { ...STORM.key, ext: 150, target: [0, 20, 40], map: 4096 } }); e.sky = { ...STORM.sky, mid: 0xb06a48, glowK: 0.8 }; e.sunDir = [-0.5, 0.1, -1]; e.fog = { color: 0xb88a72, near: 250, far: 1300 };
  const eS = env(DUSK); sunSet(eS); const eA = JSON.parse(JSON.stringify(e)); world(g, e);
  const z = ziggurat({ W: ZW, H: ZH }); g.add(z); const st = z.userData.stages; const sh = z.userData.sh; const dust = dustPuffs(24); g.add(dust);
  const pit = new THREE.Group(); for (const [w, d, x, zz] of [[ZW, 3, 0, ZW / 2], [ZW, 3, 0, -ZW / 2], [3, ZW, ZW / 2, 0], [3, ZW, -ZW / 2, 0]]) { const b = Box(w, 2.2, d, mat(0xb08858), 0.3); b.position.set(x, 1.1, zz); pit.add(b); } const floor = Box(ZW - 3, 0.4, ZW - 3, mat(0x3a2a20), 0.1); floor.position.y = 0.1; pit.add(floor); const rub = rnd(3); for (let i = 0; i < 30; i++) { const rk = Sph(0.8 + rub() * 1.4, mat(0x8a6a4a, { flat: true }), 1, 0.6, 1, 6); rk.position.set((rub() - .5) * 80, 0.5, (rub() - .5) * 80); pit.add(rk); } g.add(pit); shade(pit); pit.visible = false;
  const sold = Array.from({ length: 9 }, (_, i) => { const s = person({ h: 1.75, shirt: 0xa83a2a, pants: 0x4a3a2a, hair: 0x2a1a10, helmet: 0xc0c8d0, crest: 0xc0392b }); s.position.set(-34 + i * 8.5, 0, ZW / 2 + 8 + (i % 2) * 4); s.rotation.y = Math.PI; const sp = spear(2.2); sp.position.set(0.5, 0, 0.1); sp.scale.setScalar(1.0); s.add(sp); g.add(s); return s; });
  const arg = Array.from({ length: 8 }, (_, i) => { const w = person({ h: 1.7, shirt: [0xd8503a, 0x3a8a5a, 0xe0a030, 0x4a7bd0][i % 4], pants: 0xb89868, hair: 0x2a1a10, cloth: 0xe8e0d0 }); const pair = Math.floor(i / 2), side = i % 2 ? 1 : -1; w.position.set(-24 + pair * 16 + side * 2.2, 0, ZW / 2 + 12); w.rotation.y = side > 0 ? Math.PI / 2 + 0.3 : -Math.PI / 2 - 0.3; g.add(w); poseArms(w, [-0.4, 0.9, 0.9], [-0.4, 0.9, 0.9]); return w; });
  const p1 = makePill('YES', 0x2f9a56, 7, 3.2), p2 = makePill('NO', 0xc8382e, 7, 3.2); g.add(p1, p2);
  return { group: g, env: e,
    cam: camRig([[0, [70, 30, 150], [0, 36, 40], 44], [[0, 0.9], [74, 30, 144], [0, 38, 40], 44], [[1, 0.3], [-30, 3.2, 62], [0, 8, 46], 42], [[1, 0.95], [-26, 3.4, 60], [0, 8, 46], 42], [[2, 0.3], [40, 40, 125], [0, 0, 0], 46], [[2, 0.95], [44, 42, 120], [0, 0, 0], 46], [[3, 0.3], [90, 34, 180], [0, 6, 0], 46], [[3, 0.95], [96, 36, 176], [0, 6, 0], 46], [[4, 0.1], [100, 40, 200], [0, 38, 0], 46], [[4, 1.0], [76, 40, 196], [0, 40, 0], 46]]),
    update(lt, u, dur, t, B) {
      // stage i shrinks (melts) at hide[i] and grows back at show[i]: no hard pops (brightness jumps stay small)
      const hide = [B[2] + 1.0, B[2] + 0.55, B[2] + 0.1, 2.5, 1.9, 1.3, 0.7], show = [0, 1, 2, 3, 4, 5, 6].map(i => B[4] + 0.6 + i * 0.4);
      st.forEach((s, i) => { let k = 1 - ease((lt - hide[i]) / 0.45); if (lt > B[4]) k = ease((lt - show[i]) / 0.45); s.scale.y = Math.max(0.0001, k); s.position.y = sh * i + sh * 0.5 * s.scale.y; s.visible = k > 0.01; });
      z.userData.temple.visible = (lt < hide[6] + 0.1) || (lt > B[4] && lt > show[6]); z.userData.temple.scale.setScalar(Math.max(0.0001, lt > B[4] ? ease((lt - show[6]) / 0.4) : 1 - ease((lt - hide[6]) / 0.35))); const keep = 0; const ramp = false; pit.visible = lt >= B[2] - 0.2 && lt < B[4] + 0.2; popIn(pit, lt, B[2] - 0.2, 1, 0.8);
      sold.forEach((s, i) => { s.visible = lt < B[1]; walkCycle(s, t + i, 4, 0.2); s.position.z = ZW / 2 + 8 + (i % 2) * 4 + 1.2 * Math.sin(t * 1.5 + i); });
      arg.forEach((w, i) => { w.visible = lt >= B[1] - 0.2 && lt < B[2]; poseArms(w, [-0.3, 0.9 + 0.2 * Math.sin(t * 6 + i), 0.9], [-0.3, 0.9 + 0.2 * Math.sin(t * 6 + i + 1), 0.9]); });
      dust.userData.update((lt < B[1] ? (lt % 1.6) / 1.6 : lt > B[2] - 0.2 && lt < B[2] + 1.8 ? (lt - B[2] + 0.2) / 1.8 : -1), [0, 6, ZW / 2], 40, 8, 4.5);
      if (lt >= B[3] - 0.2) { const k = ease((lt - B[3]) / 1.2); e.fog = { color: 0xcdb7a6, near: lerp(250, 60, k), far: lerp(1300, 520, k) }; } if (lt >= B[4]) { mixEnv(e, eA, eS, ease((lt - B[4]) / 1.6)); e.fog = { color: 0xf0b074, near: lerp(60, 300, ease((lt - B[4]) / 1.6)), far: lerp(520, 1500, ease((lt - B[4]) / 1.6)) }; }
      const pop = (t0) => easeOB((lt - t0) / 0.5); pillFront(p1, -1.2, 0.5, 0.17 * pop(B[4] + 2.0), 0.02 * Math.sin(t * 1.3), 14); pillFront(p2, 1.2, 0.5, 0.17 * pop(B[4] + 2.6), -0.02 * Math.sin(t * 1.1), 14);
    },
    anchors: { stand: () => V(-24, 2.5, ZW / 2 + 12), pitC: () => V(0, 1, 0), pitA: () => V(-ZW / 2, 1.2, ZW / 2), pitB: () => V(ZW / 2, 1.2, ZW / 2), fogP: () => V(0, 20, 0), soldier: () => V(0, 6, ZW / 2 + 8) } };
});
