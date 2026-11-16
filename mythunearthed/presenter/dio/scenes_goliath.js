// goliath: one warm diorama stage. Left: the 2.9 m version (scroll A), right: the 2.0 m version (scroll B), a shared measuring pole between, then armour + spear.
import { THREE, V, mat, woodMat, Sph, Box, Cyl, Cap, Cone, between, shade, rnd, lerp, makeSky, poseArms } from './kit.js';
import { makePill, makeSearchlight } from './props.js';
import { REG, reg, ease, easeO, easeOB, at, fixed, camRig, env, STAGE, billboard, popIn, pillFront } from './world.js';
import { person, spear, shield, armorStand, walkCycle } from './folk.js';
import { measurePole, doorFrame, scroll, jar, lamp, balance, table, cypress, rock, patch, goldBar } from './things.js';
import { canvasTex, GRAD } from './kit.js';
import { makeMountain } from './kit.js';

function goliathFig(h) { const p = person({ h, shirt: 0x6a3a22, pants: 0x3a2a1c, hair: 0x2a1a10, beard: 0x5a3018, helmet: 0xb07a30, crest: false, armor: 0xb07a30 }); const sp = spear(h * 0.92 / 1.0 + 0.4); sp.position.set(h * 0.2, 0, h * 0.08); sp.rotation.z = -0.05; const g = new THREE.Group(); g.add(p, sp); poseArms(p, [0.15, 0.1, 0.2], [-0.2, 0.15, 0]); const sh = shield(h * 0.21); sh.position.set(-h * 0.23, h * 0.4, h * 0.12); sh.rotation.y = 0.15; g.add(sh); shade(g); g.userData = { p, sp, top: h, h }; return g; }

reg('gol_stage', () => {
  const g = new THREE.Group(); const e = env(STAGE, { key: { ...STAGE.key, k: 2.0, ext: 40, target: [8, 0, 0] }, hemi: { ...STAGE.hemi, k: 0.95 } });
  const floor = Box(58, 0.8, 15, woodMat(3, 1, [150, 100, 58], { seed: 21 }), 0.12); floor.position.set(8, -0.4, 0); floor.receiveShadow = true; g.add(floor);
  const R = rnd(8); for (let i = 0; i < 9; i++) { const m = makeMountain(5 + R() * 4, 8 + R() * 5, 30 + i, i % 2 ? 0x6a5a6a : 0x7a6070, 0xd8b888, 0.0); m.position.set(-16 + i * 7.5, 0, -22 - R() * 4); g.add(m); }
  const pA = patch(3.4, 0x6fa84a); pA.position.set(-3.2, 0, 0.5); g.add(pA); const pB = patch(3.4, 0x6fa84a); pB.position.set(3.2, 0, 0.5); g.add(pB);
  const cy = [[-6.8, -3], [-1.5, -3.4], [1.6, -3.2], [7.0, -3.0]].map(([x, z], i) => { const c = cypress(5.5 + i % 2, 0x3a6a30); c.position.set(x, 0, z); g.add(c); return c; });
  const GA = goliathFig(2.9); GA.position.set(-3.2, 0.12, 0.5); g.add(GA); const GB = goliathFig(2.0); GB.position.set(3.2, 0.12, 0.5); g.add(GB);
  const pole = measurePole(3.2); pole.position.set(0, 0, 1.6); g.add(pole);
  const easel = (x) => { const e_ = new THREE.Group(); for (const s of [-1, 1]) { const l = between(V(s * 0.8, 0, -0.5), V(s * 0.3, 2.7, 0), 0.04, mat(0x6a4020), e_); } const bk = between(V(0, 0, -1.1), V(0, 2.6, 0), 0.04, mat(0x6a4020), e_); e_.position.set(x, 0, 1.2); g.add(e_); return e_; };
  const eA = easel(-7.6), eB = easel(8.2); const scA = scroll(2.6, 1.9, { big: '6½', seed: 4 }); scA.position.set(-7.6, 2.2, 1.45); scA.rotation.y = 0.3; g.add(scA);
  const scB = scroll(2.6, 1.9, { big: '4½', seed: 7 }); scB.position.set(8.2, 2.2, 1.45); scB.rotation.y = -0.3; g.add(scB);
  const jr = jar(0.9); jr.position.set(10.4, 0, 2.2); g.add(jr); const ex1 = scroll(0.9, 0.7, { seed: 12, lines: 4 }), ex2 = scroll(0.9, 0.7, { seed: 13, lines: 4 }); ex1.position.set(11.8, 0.5, 2.4); ex1.rotation.set(-0.3, -0.5, 0); ex2.position.set(12.2, 0.5, 1.2); ex2.rotation.set(-0.3, -0.9, 0); g.add(ex1, ex2);
  const door = doorFrame(1.0, 2.05); door.position.set(3.2, 0.12, -0.35); g.add(door);
  const sold = [0, 1, 2].map(i => { const s = person({ h: 1.6, shirt: [0x4a7bd0, 0x3a8a5a, 0xa05a9a][i], pants: 0x4a3a2a, hair: 0x2a1a10, helmet: 0x9aa4ae, crest: false }); s.position.set(4.7 + i * 0.85, 0.12, 1.0); s.rotation.y = 0.2; g.add(s); const sp_ = spear(2.0); sp_.position.set(0.5, 0, 0.12); s.add(sp_); sp_.scale.setScalar(1.27 / 1.6 * 1.0); return s; });
  const arm = armorStand(2.1); arm.position.set(16.5, 0, 0.8); g.add(arm); const bal = balance(1.5); bal.position.set(19.3, 0, 0.8); g.add(bal);
  const wtex = canvasTex(256, 128, (c, w, h) => { c.fillStyle = '#4a5058'; c.fillRect(0, 0, w, h); c.fillStyle = '#f0ead8'; c.font = '900 84px sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('57 KG', w / 2, h / 2 + 4); }); const wt = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.4, 0.4), [mat(0x4a5058), mat(0x4a5058), mat(0x4a5058), mat(0x4a5058), new THREE.MeshToonMaterial({ map: wtex, gradientMap: GRAD }), mat(0x4a5058)]); wt.castShadow = true; const blk = new THREE.Group(); blk.add(wt); g.add(blk);
  const manA = person({ h: 1.6, shirt: 0x4a7bd0, pants: 0x4a3a2a, hair: 0x2a1a10, helmet: 0x9aa4ae, crest: false }); manA.position.set(-1.45, 0.12, 1.4); manA.rotation.y = -0.3; g.add(manA); const spM = spear(1.9); spM.position.set(0.5, 0, 0.1); spM.scale.setScalar(1.27 / 1.6); manA.add(spM);
  const bal2 = balance(1.5); bal2.position.set(24.5, 0, 0.8); g.add(bal2);
  const leaf = new THREE.Shape(); leaf.moveTo(0, -0.42); leaf.quadraticCurveTo(0.2, -0.15, 0.1, 0.08); leaf.lineTo(0, 0.5); leaf.lineTo(-0.1, 0.08); leaf.quadraticCurveTo(-0.2, -0.15, 0, -0.42);
  const spearhead = new THREE.Group(); const lf = new THREE.Mesh(new THREE.ExtrudeGeometry(leaf, { depth: 0.05, bevelEnabled: true, bevelThickness: 0.015, bevelSize: 0.015, bevelSegments: 2 }), mat(0xb8c0c8)); lf.position.z = -0.03; spearhead.add(lf); const rib = Box(0.03, 0.9, 0.07, mat(0x8a929a), 0.01); rib.position.y = 0.03; spearhead.add(rib); const sock = Cyl(0.06, 0.045, 0.28, mat(0x6a6e74), 12); sock.position.y = -0.52; spearhead.add(sock); spearhead.rotation.z = 0.0; g.add(spearhead); shade(spearhead);
  const kgTex = (txt) => canvasTex(256, 128, (c, w, h) => { c.fillStyle = '#4a5058'; c.fillRect(0, 0, w, h); c.fillStyle = '#f0ead8'; c.font = '900 84px sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(txt, w / 2, h / 2 + 4); });
  const wmat = new THREE.MeshToonMaterial({ map: kgTex('7 KG'), gradientMap: GRAD }); const wb = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.34, 0.34), [mat(0x4a5058), mat(0x4a5058), mat(0x4a5058), mat(0x4a5058), wmat, mat(0x4a5058)]); wb.castShadow = true; g.add(wb);
  const rk = { visible: true, scale: { setScalar() { } } };
  const lmp = lamp(1.6); const lp = Cyl(0.1, 0.14, 0.9, mat(0x6a4020), 10); lp.position.set(-10.6, 0.45, 1.0); g.add(lp); lmp.position.set(-10.6, 0.9, 1.0); g.add(lmp);
  const q = new THREE.Group(); const qm = new THREE.Mesh(new THREE.TorusGeometry(0.5, 0.16, 12, 24, Math.PI * 1.5), mat(0xffc42e, { e: 0x6a4a00, ei: 0.4 })); qm.rotation.z = -0.6; q.add(qm); const qd = Sph(0.17, mat(0xffc42e, { e: 0x6a4a00, ei: 0.4 })); qd.position.set(0, -0.95, 0); q.add(qd); q.position.set(0, 4.5, 1.0); g.add(q); q.scale.setScalar(0.0001);
  const pA_ = makePill('A  2.0 M', 0x2f9a56, 11, 3.2), pB_ = makePill('B  2.9 M', 0xc8382e, 11, 3.2); g.add(pA_, pB_);
  const dust = []; const Rr = rnd(5); for (let i = 0; i < 30; i++) { const d = Sph(0.025, new THREE.MeshBasicMaterial({ color: 0xffd9a0 }), 1, 1, 1, 6); d.position.set(Rr() * 40 - 12, 0.5 + Rr() * 5, Rr() * 4 - 1); d.userData.s = Rr(); d.userData.noShadow = true; g.add(d); dust.push(d); }
  shade(g);
  return { group: g, env: e,
    cam: camRig([[0, [-3.6, 2.6, 13.5], [-2.4, 1.6, 0.6], 44], [[0, 0.8], [-3.4, 2.6, 13.0], [-2.3, 1.6, 0.6], 44], [[1, 0.3], [0, 3.4, 27], [0.3, 2.0, 0.5], 44], [[1, 0.9], [0, 3.4, 26], [0.3, 2.0, 0.5], 44], [[2, 0.3], [-7.0, 2.4, 9.5], [-7.6, 2.1, 1.4], 38], [[2, 0.9], [-7.2, 2.3, 9.0], [-7.6, 2.1, 1.4], 38], [[3, 0.3], [-5.4, 2.0, 12.5], [-3.2, 1.6, 0.5], 42], [[3, 0.9], [-5.4, 2.0, 12], [-3.2, 1.6, 0.5], 42],
      [[4, 0.3], [8.8, 2.4, 10.4], [8.2, 2.1, 1.4], 38], [[4, 0.9], [8.6, 2.4, 10], [8.2, 2.1, 1.4], 38], [[5, 0.3], [10.6, 2.0, 8], [11.2, 0.9, 1.8], 38], [[5, 0.9], [10.8, 2.0, 7.6], [11.4, 0.9, 1.8], 38], [[6, 0.3], [4.2, 1.6, 8.4], [3.2, 1.5, 0.3], 40], [[6, 0.9], [4.0, 1.6, 8.0], [3.2, 1.5, 0.3], 40], [[7, 0.3], [4.6, 1.8, 12.5], [4.6, 1.4, 0.8], 42], [[7, 0.9], [4.4, 1.8, 12], [4.6, 1.4, 0.8], 42],
      [[8, 0.4], [17.6, 2.8, 12.2], [17.9, 1.3, 0.8], 44], [[8, 0.9], [18.2, 2.8, 11.8], [18.1, 1.3, 0.8], 44], [[9, 0.3], [24.5, 2.6, 11.0], [24.5, 1.3, 0.8], 42], [[9, 0.9], [24.5, 2.6, 10.6], [24.5, 1.3, 0.8], 42], [[10, 0.3], [8, 3.6, 18], [1.6, 2.2, 0.5], 44], [[10, 0.9], [6, 3.6, 18], [1.0, 2.2, 0.5], 44], [[11, 0.2], [0.2, 3.4, 24], [0.2, 2.0, 0.5], 44], [[11, 1.0], [0.2, 3.5, 22], [0.2, 2.0, 0.5], 44]]),
    update(lt, u, dur, t, B) {
      GB.visible = lt > B[1] - 0.2; popIn(GB, lt, B[1] - 0.2, 1, 0.8); popIn(scB, lt, B[1] - 0.1, 1, 0.7); popIn(eB, lt, B[1] - 0.1, 1, 0.7); popIn(pB, lt, B[1] - 0.2, 1, 0.5); popIn(cy[2], lt, B[1], 1, 0.6); popIn(cy[3], lt, B[1], 1, 0.6);
      popIn(jr, lt, B[4] + 0.1, 1, 0.6); popIn(ex1, lt, B[5] + 0.1, 1, 0.5); popIn(ex2, lt, B[5] + 0.35, 1, 0.5);
      door.position.x = 3.2; door.position.y = 0.12 - 3.2 * (1 - easeO((lt - B[6] + 0.3) / 1.0)); door.visible = lt > B[6] - 0.4;
      sold.forEach((s, i) => { popIn(s, lt, B[7] + 0.1 + i * 0.25, 1, 0.5); });
      popIn(arm, lt, B[8] - 0.4, 1, 0.7); popIn(bal, lt, B[8] - 0.3, 1.5, 0.7); const hv = ease((lt - B[8] - 1.0) / 0.8), ta = 0.2 * hv + 0.025 * Math.sin(t * 2); bal.userData.tilt(ta);
      blk.position.set(19.3 - 0.52 * Math.cos(ta) * 1.5, 1.5 * (1.0 - 0.52 * Math.sin(ta) - 0.5) + 0.22, 0.8); blk.scale.setScalar(Math.max(0.0001, easeOB((lt - B[8] - 0.5) / 0.5)) * 1.2);
      popIn(bal2, lt, B[9] - 0.4, 1.5, 0.6); { const ta2 = 0.16 * ease((lt - B[9] - 0.8) / 0.8) + 0.02 * Math.sin(t * 2); bal2.userData.tilt(ta2); spearhead.position.set(24.5 - 0.52 * Math.cos(ta2) * 1.5, 1.5 * (1.0 - 0.52 * Math.sin(ta2) - 0.5) + 0.62, 0.8); spearhead.rotation.z = -1.2; spearhead.scale.setScalar(Math.max(0.0001, easeOB((lt - B[9] - 0.2) / 0.6))); wb.position.set(24.5 + 0.52 * Math.cos(ta2) * 1.5, 1.5 * (1.0 + 0.52 * Math.sin(ta2) - 0.5) + 0.2, 0.8); wb.scale.setScalar(Math.max(0.0001, easeOB((lt - B[9] - 0.4) / 0.6))); }
      popIn(q, lt, B[10] + 0.4, 1, 0.8); q.rotation.y = 0.5 * Math.sin(t * 1.2); q.position.y = 4.6 + 0.12 * Math.sin(t * 1.8);
      const pop_ = (t0) => easeOB((lt - t0) / 0.5); pillFront(pA_, 1.3, 0.55 + 0.03 * Math.sin(t * 1.7), 0.24 * pop_(B[11] + 0.9), 0.02 * Math.sin(t * 1.3), 14); pillFront(pB_, -1.3, 0.55 + 0.03 * Math.sin(t * 1.5 + 1), 0.24 * pop_(B[11] + 1.4), -0.02 * Math.sin(t * 1.1), 14);
      lmp.userData.update(t); dust.forEach(d => { d.position.y += 0.002 * (0.3 + d.userData.s); if (d.position.y > 6) d.position.y = 0.5; });
      GA.userData.p.position.y = 0.012 * Math.sin(t * 1.6); GB.userData.p.position.y = 0.012 * Math.sin(t * 1.6 + 1);
    },
    anchors: { headA: at(GA, 0, 2.9, 0), footA: at(GA, 0, 0, 0.0), headB: at(GB, 0, 2.0, 0), footB: at(GB, 0, 0, 0), scrollA: at(scA, 0, 0, 0), scrollB: at(scB, 0, 0, 0), headS: at(sold[1], 0, 1.6, 0), footS: at(sold[1], 0, 0, 0), armor: at(arm, 0, 1.6, 0), spearhead: at(spearhead, 0, 0.3, 0), q: at(q, 0, -0.2, 0), pA: at(pA_, 0, 0, 0), pB: at(pB_, 0, 0, 0), extra: at(ex1, 0, 0, 0), jr: at(jr, 0, 0.9, 0) } };
});
