// Shared warm "museum stage": long wooden floor, back wall with torches. buildStage(g, L, x0) -> {flames[], env}
import { THREE, V, mat, woodMat, Box, Cyl, shade, rnd } from './kit.js';
import { env, STAGE } from './world.js';
import { fire } from './things4.js';
export function stageEnv(L = 110, x0 = 0, o = {}) { return env(STAGE, { key: { ...STAGE.key, k: o.k ?? 2.0, ext: L * 0.55, target: [x0 + L / 2, 0, 0], far: L * 2, dir: o.dir ?? [-0.35, 0.9, 0.8] }, hemi: { ...STAGE.hemi, k: o.hemi ?? 0.95 }, fog: { color: o.fogc ?? 0x3a2214, near: 70, far: 280 } }); }
export function buildStage(g, L = 110, x0 = 0, o = {}) {
  const floor = Box(L, 0.8, 15, woodMat(3, 1, o.floor ?? [130, 86, 50], { seed: 24 }), 0.12); floor.position.set(x0 + L / 2, -0.4, 0); floor.receiveShadow = true; g.add(floor);
  const wall = Box(L, 14, 0.6, woodMat(3, 1.2, o.wall ?? [90, 58, 34], { seed: 25 }), 0.05); wall.position.set(x0 + L / 2, 7, -7.5); g.add(wall);
  const flames = []; for (let x = x0 - 4; x < x0 + L; x += 11) { const p = Cyl(0.07, 0.1, 2.4, mat(0x4a3020), 8); p.position.set(x, 1.2, -5.5); g.add(p); const f = fire(0.9, 0.5, 5, Math.floor(Math.abs(x))); f.position.set(x, 2.45, -5.5); g.add(f); flames.push(f); }
  return { flames, tick: (t) => flames.forEach((f, i) => f.userData.update(t + i, 1)) };
}
