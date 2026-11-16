// Toon kit for the "diorama" style: materials, textures, sky, water, rain, spray + simple prop builders. Units = metres.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
export { THREE, RoundedBoxGeometry };

export const V = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);
export const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
export const sstep = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
export const lerp = (a, b, u) => a + (b - a) * u;
export const rnd = (seed) => { let s = seed >>> 0 || 1; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; };

// ------------------------------------------------------------------ toon materials (soft 6-band ramp)
const ramp = new Uint8Array([105, 148, 186, 216, 238, 255]);
export const GRAD = new THREE.DataTexture(ramp, ramp.length, 1, THREE.RedFormat); GRAD.minFilter = GRAD.magFilter = THREE.NearestFilter; GRAD.needsUpdate = true;
const cache = new Map();
export function mat(color, o = {}) {
  const key = JSON.stringify([color, o.e, o.ei, o.flat, o.op, o.side, o.vc, o.map && o.map.uuid, o.fog]);
  if (cache.has(key) && !o.fresh) return cache.get(key);
  const p = { color, gradientMap: GRAD };
  if (o.e !== undefined) { p.emissive = o.e; p.emissiveIntensity = o.ei ?? 1; }
  if (o.map) p.map = o.map;
  if (o.op !== undefined) { p.transparent = true; p.opacity = o.op; p.depthWrite = o.depthWrite ?? (o.op > 0.95); }
  if (o.side) p.side = o.side;
  if (o.vc) p.vertexColors = true;
  if (o.fog === false) p.fog = false;
  const m = new THREE.MeshToonMaterial(p); cache.set(key, m); return m;
}
export const glow = (color, k = 1) => new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(k), fog: false });

export function canvasTex(w, h, draw, repeat = null) {
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h; const g = cv.getContext('2d'); draw(g, w, h);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(repeat[0], repeat[1]); }
  return t;
}
const hex = (r, g, b) => `rgb(${r | 0},${g | 0},${b | 0})`;
const woodCache = {};
// plank texture: tile contains `planks` rows. returns a texture whose repeat maps world metres (tileW x tileH per tile) when uv are in metres
export function woodTex(base = [168, 112, 62], planks = 4, seed = 3, o = {}) {
  const key = base.join() + planks + seed + (o.vert ? 'v' : '');
  if (!woodCache[key]) woodCache[key] = canvasTex(512, 512, (g, w, h) => {
    const R = rnd(seed); const ph = h / planks;
    for (let p = 0; p < planks; p++) {
      const k = 0.9 + 0.2 * R(); g.fillStyle = hex(base[0] * k, base[1] * k, base[2] * k); g.fillRect(0, p * ph, w, ph);
      for (let i = 0; i < 26; i++) { const y = p * ph + R() * ph, x = R() * w, l = 60 + R() * 260; g.strokeStyle = `rgba(${R() < .5 ? '60,30,10' : '255,225,170'},${0.05 + R() * 0.09})`; g.lineWidth = 1 + R() * 2; g.beginPath(); g.moveTo(x, y); g.lineTo(x + l, y + (R() - .5) * 3); g.stroke(); }
      const jx = R() * w; g.fillStyle = 'rgba(50,25,8,0.55)'; g.fillRect(jx, p * ph, 3, ph);
      g.fillStyle = 'rgba(40,20,6,0.8)'; g.fillRect(0, p * ph + ph - 4, w, 4); g.fillStyle = 'rgba(255,230,180,0.22)'; g.fillRect(0, p * ph, w, 3);
      for (const nx of [jx - 12, jx + 14]) { g.fillStyle = 'rgba(40,22,10,0.7)'; g.beginPath(); g.arc(nx, p * ph + ph / 2, 3, 0, 7); g.fill(); }
    }
  });
  return woodCache[key];
}
// material with its own repeat (so each mesh can choose a tiling) sharing the canvas
export function woodMat(tileW, tileH, base, o = {}) {
  const t = woodTex(base, o.planks || 4, o.seed || 3).clone(); t.needsUpdate = true; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(1 / tileW, 1 / tileH); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  return new THREE.MeshToonMaterial({ map: t, gradientMap: GRAD, color: o.tint ?? 0xffffff, emissive: o.e ?? 0x000000, side: o.side ?? THREE.FrontSide });
}
export function sandTex(rx = 6, ry = 6) {
  return canvasTex(512, 512, (g, w, h) => {
    g.fillStyle = '#d8a45c'; g.fillRect(0, 0, w, h); const R = rnd(11);
    for (let i = 0; i < 900; i++) { g.fillStyle = `rgba(${R() < .5 ? '255,220,150' : '150,95,40'},${0.04 + R() * 0.07})`; g.beginPath(); g.arc(R() * w, R() * h, 2 + R() * 12, 0, 7); g.fill(); }
    g.strokeStyle = 'rgba(120,70,25,0.35)'; g.lineWidth = 2; for (let i = 0; i < 26; i++) { let x = R() * w, y = R() * h; g.beginPath(); g.moveTo(x, y); for (let k = 0; k < 6; k++) { x += (R() - .5) * 70; y += (R() - .5) * 70; g.lineTo(x, y); } g.stroke(); }
  }, [rx, ry]);
}

// ------------------------------------------------------------------ geometry shortcuts
export function put(parent, obj, x = 0, y = 0, z = 0) { obj.position.set(x, y, z); parent.add(obj); return obj; }
export const Sph = (r, m, sx = 1, sy = 1, sz = 1, seg = 28) => { const o = new THREE.Mesh(new THREE.SphereGeometry(r, seg, Math.round(seg * 0.65)), m); o.scale.set(sx, sy, sz); return o; };
export const Box = (w, h, d, m, r = 0.05) => new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 3, Math.min(r, w / 2.01, h / 2.01, d / 2.01)), m);
export const Cyl = (rt, rb, h, m, seg = 28) => new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), m);
export const Cap = (r, len, m, seg = 16) => new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 6, seg), m);
export const Cone = (r, h, m, seg = 24) => new THREE.Mesh(new THREE.ConeGeometry(r, h, seg), m);
export const Pln = (w, h, m) => new THREE.Mesh(new THREE.PlaneGeometry(w, h), m);
export function between(a, b, r, m, parent) { // capsule/cylinder from a to b
  const d = b.clone().sub(a), L = d.length(); const o = Cyl(r, r, L, m, 10); o.position.copy(a).addScaledVector(d, 0.5); o.quaternion.setFromUnitVectors(V(0, 1, 0), d.normalize()); if (parent) parent.add(o); return o;
}
export function shade(obj, cast = true, recv = true) { obj.traverse(o => { if (o.isMesh && !o.userData.noShadow) { o.castShadow = cast; o.receiveShadow = recv; } }); return obj; }
export function tube(pts, r, m, seg = 40) { return new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), seg, r, 10, false), m); }

// ------------------------------------------------------------------ sky dome with sun glow
export function makeSky() {
  const u = { top: { value: new THREE.Color(0x2a3a6a) }, mid: { value: new THREE.Color(0xd9803a) }, hor: { value: new THREE.Color(0xffc070) }, sunCol: { value: new THREE.Color(0xfff0c0) },
    sunDir: { value: V(0, 0.1, -1).normalize() }, sunSize: { value: 0.0008 }, glowK: { value: 0.6 }, glowP: { value: 18 }, below: { value: new THREE.Color(0x203040) } };
  const m = new THREE.ShaderMaterial({ uniforms: u, side: THREE.BackSide, depthWrite: false, fog: false,
    vertexShader: 'varying vec3 vD; void main(){ vD=position; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }',
    fragmentShader: `varying vec3 vD; uniform vec3 top,mid,hor,sunCol,sunDir,below; uniform float sunSize,glowK,glowP;
      void main(){ vec3 d=normalize(vD); float h=d.y; vec3 c=mix(hor,mid,smoothstep(0.0,0.22,h)); c=mix(c,top,smoothstep(0.18,0.8,h)); c=mix(c,below,smoothstep(0.0,-0.25,h));
        float s=max(dot(d,normalize(sunDir)),0.); c+=sunCol*(pow(s,glowP)*glowK + pow(s,glowP*6.)*glowK*0.8 + smoothstep(1.-sunSize*1.6,1.-sunSize,s));
        gl_FragColor=vec4(c,1.);
        #include <colorspace_fragment>
      }` });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(900, 32, 20), m); mesh.renderOrder = -10; mesh.frustumCulled = false; mesh.userData.noShadow = true;
  mesh.userData.u = u; return mesh;
}

// ------------------------------------------------------------------ low-poly sea (flat-shaded facets, animated)
export function makeWater(size = 900, n = 90, color = 0x2f78b0) {
  const g = new THREE.PlaneGeometry(size, size, n, n).rotateX(-Math.PI / 2).toNonIndexed();
  const col = new Float32Array(g.attributes.position.count * 3); g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const m = new THREE.MeshToonMaterial({ color: 0xffffff, gradientMap: GRAD, vertexColors: true, emissive: new THREE.Color(color).multiplyScalar(0.28) });
  const mesh = new THREE.Mesh(g, m); mesh.receiveShadow = true;
  const base = g.attributes.position.array.slice(); const c0 = new THREE.Color(color), c1 = new THREE.Color(color).lerp(new THREE.Color(0xbfeaff), 0.5);
  mesh.userData.update = (t, amp = 0.6, speed = 1, steep = 1, calmR = 0, calmC = [0, 0]) => {
    const p = g.attributes.position.array, c = g.attributes.color.array;
    for (let i = 0, j = 0; i < p.length; i += 3, j += 3) {
      const x = base[i], z = base[i + 2];
      let h = Math.sin(x * 0.045 * steep + t * 0.9 * speed) * 0.55 + Math.sin(z * 0.06 * steep - t * 0.7 * speed + 1.3) * 0.45 + Math.sin((x + z) * 0.11 * steep + t * 1.7 * speed) * 0.28 + Math.sin((x - z * 1.3) * 0.2 * steep - t * 2.3 * speed) * 0.12;
      h *= amp; p[i + 1] = h;
      const k = clamp(0.35 + 0.5 * h / (amp + 1e-6) + 0.1 * Math.sin(x * 0.8 + z * 0.6), 0, 1);
      const f = clamp(Math.hypot(x, z) / 450, 0, 1);
      c[j] = lerp(c0.r, c1.r, k * (1 - 0.5 * f)); c[j + 1] = lerp(c0.g, c1.g, k * (1 - 0.5 * f)); c[j + 2] = lerp(c0.b, c1.b, k * (1 - 0.5 * f));
    }
    g.attributes.position.needsUpdate = true; g.attributes.color.needsUpdate = true; g.computeVertexNormals();
  };
  mesh.userData.height = (x, z, t, amp = 0.6, speed = 1, steep = 1) => (Math.sin(x * 0.045 * steep + t * 0.9 * speed) * 0.55 + Math.sin(z * 0.06 * steep - t * 0.7 * speed + 1.3) * 0.45 + Math.sin((x + z) * 0.11 * steep + t * 1.7 * speed) * 0.28 + Math.sin((x - z * 1.3) * 0.2 * steep - t * 2.3 * speed) * 0.12) * amp;
  return mesh;
}

// ------------------------------------------------------------------ rain (3D streaks following the camera)
export function makeRain(n = 1400, box = [60, 40, 60], len = 1.4, opacity = 0.45) {
  const g = new THREE.BufferGeometry(); const pos = new Float32Array(n * 6); g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const R = rnd(5); const seed = Array.from({ length: n }, () => [R(), R(), R(), 0.7 + 0.6 * R()]);
  const m = new THREE.LineBasicMaterial({ color: 0xcfe0ff, transparent: true, opacity, fog: false, depthWrite: false });
  const ln = new THREE.LineSegments(g, m); ln.frustumCulled = false; ln.userData.noShadow = true;
  ln.userData.update = (t, cam, k = 1) => {
    for (let i = 0; i < n; i++) {
      const s = seed[i]; const sp = 26 * s[3];
      const y = ((s[1] * box[1] - t * sp) % box[1] + box[1]) % box[1]; const dx = -y * 0.12;
      const x = cam.x + (s[0] - 0.5) * box[0] + dx, z = cam.z + (s[2] - 0.5) * box[2] - box[2] * 0.3, yy = cam.y - box[1] * 0.35 + y;
      pos.set([x, yy, z, x - 0.12 * len, yy + len * s[3], z], i * 6);
    }
    g.attributes.position.needsUpdate = true; m.opacity = opacity * k;
  };
  return ln;
}

// ------------------------------------------------------------------ water droplets (ballistic arcs, analytic)
export function makeJet(n, r = 0.22, color = 0xcfeaff, opacity = 0.9) {
  const m = new THREE.MeshToonMaterial({ color, gradientMap: GRAD, emissive: 0x6aa0c8, emissiveIntensity: 0.6, transparent: true, opacity });
  const im = new THREE.InstancedMesh(new THREE.SphereGeometry(r, 8, 6), m, n); im.frustumCulled = false; im.userData.noShadow = true;
  const R = rnd(21); const ph = Array.from({ length: n }, () => [R(), R(), R()]); const d = new THREE.Object3D();
  im.userData.update = (t, o) => { // o: origin V, v0 (speed vector), spread, g, life, rate, scale
    const { origin, vel, spread = 0.3, g = 9.8, life = 1.3, rate = 1, scale = 1, on = 1 } = o;
    for (let i = 0; i < n; i++) {
      const s = ((t * rate + ph[i][0]) % 1 + 1) % 1, tt = s * life;
      const vx = vel.x * (1 + (ph[i][1] - .5) * spread), vy = vel.y * (1 + (ph[i][2] - .5) * spread * .6), vz = vel.z * (1 + (ph[i][1] - .5) * spread);
      d.position.set(origin.x + vx * tt, origin.y + vy * tt - 0.5 * g * tt * tt, origin.z + vz * tt);
      const sc = on * scale * (0.5 + 0.8 * Math.sin(Math.PI * Math.min(1, s * 1.1))) * (0.6 + 0.6 * ph[i][2]); d.scale.setScalar(Math.max(sc, 0.0001)); d.updateMatrix(); im.setMatrixAt(i, d.matrix);
    }
    im.instanceMatrix.needsUpdate = true;
  };
  return im;
}

// ------------------------------------------------------------------ people (big head, soft body, poseable arms)
export function makePerson(o = {}) {
  const skin = o.skin ?? 0xf2c19a, shirt = o.shirt ?? 0x4a7bd0, pants = o.pants ?? 0x39406a, hair = o.hair ?? 0x4a2c18;
  const g = new THREE.Group(); g.userData.parts = {};
  const mSkin = mat(skin), mShirt = mat(shirt), mPants = mat(pants), mHair = mat(hair), mDark = mat(0x201410), mWhite = mat(0xffffff);
  const body = new THREE.Group(); g.add(body);
  const legs = [-1, 1].map(s => { const l = new THREE.Group(); l.position.set(s * 0.1, 0.34, 0); const leg = Cap(0.075, 0.22, mPants); leg.position.y = -0.14; l.add(leg); const shoe = Sph(0.09, mat(0x2b1a12), 1, 0.6, 1.5); shoe.position.set(0, -0.31, 0.05); l.add(shoe); body.add(l); return l; });
  const torso = Cap(0.17, 0.2, mShirt); torso.position.y = 0.58; torso.scale.set(1, 1, 0.82); body.add(torso);
  const belt = Cyl(0.18, 0.18, 0.04, mat(0x3a2418)); belt.position.y = 0.42; belt.scale.z = 0.82; body.add(belt);
  const arms = [-1, 1].map(s => { const sh = new THREE.Group(); sh.position.set(s * 0.2, 0.7, 0); const up = Cap(0.052, 0.14, mShirt); up.position.y = -0.1; sh.add(up); const el = new THREE.Group(); el.position.y = -0.2; sh.add(el); const lo = Cap(0.046, 0.12, mShirt); lo.position.y = -0.09; el.add(lo); const hand = Sph(0.058, mSkin); hand.position.y = -0.2; el.add(hand); body.add(sh); sh.userData.el = el; return sh; });
  const head = new THREE.Group(); head.position.y = 0.97; body.add(head);
  const skull = Sph(0.27, mSkin); head.add(skull);
  const capH = new THREE.Mesh(new THREE.SphereGeometry(0.285, 28, 18, 0, Math.PI * 2, 0, Math.PI * 0.52), mHair); capH.rotation.x = -0.35; capH.position.set(0, 0.02, -0.02); head.add(capH);
  if (o.hat) { const hat = Cyl(0.25, 0.28, 0.1, mat(o.hat)); hat.position.y = 0.2; head.add(hat); const top = Cyl(0.18, 0.2, 0.14, mat(o.hat)); top.position.y = 0.3; head.add(top); }
  for (const s of [-1, 1]) { const e = Sph(0.034, mDark, 1, 1.25, 0.6); e.position.set(s * 0.1, 0.02, 0.25); head.add(e); const h = Sph(0.012, mWhite); h.position.set(s * 0.1 + 0.01, 0.045, 0.275); head.add(h);
    const ch = Sph(0.045, mat(0xf29a8a), 1, 0.6, 0.4); ch.position.set(s * 0.17, -0.07, 0.21); head.add(ch); const ear = Sph(0.05, mSkin, 0.6, 1, 1); ear.position.set(s * 0.27, 0, 0); head.add(ear); }
  const sm = new THREE.Mesh(new THREE.TorusGeometry(0.05, 0.009, 6, 16, Math.PI), mat(0x6a2a20)); sm.rotation.z = Math.PI; sm.position.set(0, -0.09, 0.255); head.add(sm);
  g.userData.parts = { body, head, arms, legs };
  g.scale.setScalar(o.scale ?? 1);
  return g;
}
export function poseArms(p, L, R) { // [shoulder x rot, shoulder z rot, elbow x rot]
  const a = p.userData.parts.arms; a[0].rotation.set(L[0], 0, L[1]); a[0].userData.el.rotation.x = L[2]; a[1].rotation.set(R[0], 0, R[1]); a[1].userData.el.rotation.x = R[2];
}

// ------------------------------------------------------------------ animals (cute, round)
function eyes(head, y, z, sx, r = 0.05) { const m = mat(0x1a1210); for (const s of [-1, 1]) { const e = Sph(r, m, 1, 1.2, 0.6); e.position.set(s * sx, y, z); head.add(e); const h = Sph(r * 0.35, mat(0xffffff)); h.position.set(s * sx + r * 0.3, y + r * 0.45, z + r * 0.5); head.add(h); } }
export function makeGiraffe(sc = 1) {
  const g = new THREE.Group(); const yel = mat(0xf2b441), brn = mat(0xa8601f), cream = mat(0xf7dc9a), dk = mat(0x4a2c18);
  const body = Sph(0.62, yel, 1.45, 0.82, 0.78); body.position.y = 1.55; g.add(body);
  for (const [x, z] of [[-0.62, -0.28], [-0.62, 0.28], [0.62, -0.28], [0.62, 0.28]]) { const l = Cap(0.1, 1.0, yel); l.position.set(x, 0.78, z); g.add(l); const hf = Sph(0.115, dk, 1, 0.7, 1.1); hf.position.set(x, 0.12, z + 0.01); g.add(hf); }
  const neck = new THREE.Group(); neck.position.set(0.7, 1.9, 0); neck.rotation.z = -0.28; g.add(neck);
  const nk = Cap(0.19, 1.7, yel); nk.position.y = 0.95; neck.add(nk);
  const head = new THREE.Group(); head.position.set(0.2, 2.05, 0); neck.add(head); head.rotation.z = -0.35;
  head.add(Sph(0.28, yel, 1.15, 0.9, 0.95)); const sn = Sph(0.2, cream, 1.3, 0.8, 0.85); sn.position.set(0.28, -0.07, 0); head.add(sn); const ns = Sph(0.04, dk); ns.position.set(0.46, -0.03, 0.09); head.add(ns); const ns2 = ns.clone(); ns2.position.z = -0.09; head.add(ns2);
  eyes(head, 0.1, 0.19, 0.0, 0.055); head.children.slice(-4).forEach(e => { }); // placeholder, replaced below
  head.remove(...head.children.slice(-4));
  for (const s of [-1, 1]) { const e = Sph(0.06, mat(0x1a1210), 1, 1.2, 0.7); e.position.set(0.13, 0.1, s * 0.22); head.add(e); const h = Sph(0.02, mat(0xffffff)); h.position.set(0.15, 0.13, s * 0.25); head.add(h);
    const oss = Cyl(0.03, 0.04, 0.22, yel); oss.position.set(-0.02, 0.32, s * 0.1); head.add(oss); const kn = Sph(0.055, dk); kn.position.set(-0.02, 0.45, s * 0.1); head.add(kn);
    const ear = Sph(0.09, yel, 1.2, 0.5, 0.6); ear.position.set(-0.12, 0.17, s * 0.3); ear.rotation.x = s * 0.5; head.add(ear); }
  const R = rnd(8); for (let i = 0; i < 16; i++) { const sp = Sph(0.12 + R() * 0.07, brn, 1, 1, 0.3); const a = R() * 6.28, hgt = (R() - 0.5) * 0.9; sp.position.set(Math.cos(a) * 0.86 * 1.45 * 0.62 / 0.86 * 0.9 * R() * 0.9 + (R() - .5) * .2, 1.55 + hgt * 0.6, Math.sign(Math.sin(a)) * 0.58); sp.lookAt(sp.position.clone().multiplyScalar(2).setY(sp.position.y)); g.add(sp); }
  for (let i = 0; i < 9; i++) { const sp = Sph(0.1, brn, 1, 1, 0.3); sp.position.set(0.04 * Math.sin(i), 0.35 + i * 0.17, 0.17); sp.rotation.y = 0; nk.add(sp); const sp2 = sp.clone(); sp2.position.z = -0.17; nk.add(sp2); }
  const tail = Cap(0.03, 0.5, yel); tail.position.set(-0.95, 1.5, 0); tail.rotation.z = 0.5; g.add(tail); const tf = Sph(0.07, dk); tf.position.set(-1.12, 1.2, 0); g.add(tf);
  g.userData.neck = neck; g.userData.head = head; g.scale.setScalar(sc); return g;
}
export function makeElephant(sc = 1, col = 0x9ea6b4) {
  const g = new THREE.Group(); const gr = mat(col), dk = mat(new THREE.Color(col).multiplyScalar(0.8).getHex()), pink = mat(0xe8a8a8), ivory = mat(0xfff4dd);
  const body = Sph(0.9, gr, 1.3, 1.0, 1.0); body.position.y = 1.35; g.add(body);
  for (const [x, z] of [[-0.6, -0.42], [-0.6, 0.42], [0.65, -0.42], [0.65, 0.42]]) { const l = Cyl(0.22, 0.25, 0.85, gr); l.position.set(x, 0.43, z); g.add(l); const f = Cyl(0.26, 0.27, 0.1, dk); f.position.set(x, 0.06, z); g.add(f); }
  const head = new THREE.Group(); head.position.set(1.1, 1.55, 0); g.add(head); head.add(Sph(0.55, gr, 1, 1.02, 0.95));
  for (const s of [-1, 1]) { const ear = Sph(0.5, gr, 0.22, 1.0, 0.9); ear.position.set(-0.05, 0.05, s * 0.6); ear.rotation.y = s * 0.35; head.add(ear); const ei = Sph(0.4, pink, 0.1, 0.85, 0.75); ei.position.set(-0.0, 0.05, s * 0.65); ei.rotation.y = s * 0.35; head.add(ei);
    const e = Sph(0.07, mat(0x1a1210), 0.6, 1.2, 1); e.position.set(0.42, 0.18, s * 0.28); head.add(e); const h = Sph(0.022, mat(0xffffff)); h.position.set(0.46, 0.22, s * 0.3); head.add(h);
    const tk = Cone(0.07, 0.5, ivory); tk.position.set(0.52, -0.38, s * 0.22); tk.rotation.z = -1.0; head.add(tk); }
  const tr = tube([V(0.45, -0.1, 0), V(0.75, -0.5, 0), V(0.85, -0.95, 0), V(0.95, -1.2, 0), V(1.12, -1.28, 0)], 0.15, gr, 20); head.add(tr); const trt = Sph(0.15, gr); trt.position.set(1.12, -1.28, 0); head.add(trt);
  const tail = Cap(0.03, 0.5, gr); tail.position.set(-1.15, 1.2, 0); tail.rotation.z = 0.3; g.add(tail);
  g.userData.head = head; g.userData.trunk = tr; g.scale.setScalar(sc); return g;
}
export function makeLion(sc = 1) {
  const g = new THREE.Group(); const tan = mat(0xe8a64a), mane = mat(0x9b5a1c), cream = mat(0xf6dca0), dk = mat(0x3a2012);
  const body = Sph(0.55, tan, 1.5, 0.78, 0.8); body.position.y = 0.72; g.add(body);
  for (const [x, z] of [[-0.45, -0.22], [-0.45, 0.22], [0.5, -0.22], [0.5, 0.22]]) { const l = Cap(0.1, 0.35, tan); l.position.set(x, 0.3, z); g.add(l); const p = Sph(0.12, cream, 1.2, 0.7, 1); p.position.set(x + 0.03, 0.06, z); g.add(p); }
  const head = new THREE.Group(); head.position.set(0.82, 0.98, 0); g.add(head);
  head.add(Sph(0.5, mane, 0.8, 1, 1)); const fc = Sph(0.33, tan, 0.95, 0.95, 0.95); fc.position.set(0.18, -0.03, 0); head.add(fc);
  const sn = Sph(0.17, cream, 1.2, 0.8, 1); sn.position.set(0.44, -0.1, 0); head.add(sn); const ns = Sph(0.05, dk, 1, 0.8, 1.2); ns.position.set(0.58, -0.04, 0); head.add(ns);
  for (const s of [-1, 1]) { const e = Sph(0.055, mat(0x1a1210), 0.7, 1.2, 1); e.position.set(0.4, 0.1, s * 0.15); head.add(e); const h = Sph(0.018, mat(0xffffff)); h.position.set(0.43, 0.13, s * 0.16); head.add(h); const ear = Sph(0.1, tan, 0.6, 1, 1); ear.position.set(0.06, 0.4, s * 0.25); head.add(ear); }
  const R = rnd(3); for (let i = 0; i < 14; i++) { const a = i / 14 * 6.28; const t = Sph(0.15, mane, 0.7, 1, 1); t.position.set(-0.08, Math.sin(a) * 0.5, Math.cos(a) * 0.5); head.add(t); }
  const tail = tube([V(-0.8, 0.8, 0), V(-1.15, 0.9, 0), V(-1.3, 1.15, 0), V(-1.25, 1.35, 0)], 0.04, tan, 12); g.add(tail); const tf = Sph(0.1, mane); tf.position.set(-1.25, 1.4, 0); g.add(tf);
  g.userData.head = head; g.scale.setScalar(sc); return g;
}
export function makeSheep(sc = 1) {
  const g = new THREE.Group(); const wool = mat(0xfaf6ee), face = mat(0x3a2c28);
  const R = rnd(4); for (let i = 0; i < 12; i++) { const s = Sph(0.28 + R() * 0.08, wool); s.position.set((R() - .5) * 0.7, 0.55 + (R() - .3) * 0.3, (R() - .5) * 0.4); g.add(s); }
  const body = Sph(0.42, wool, 1.3, 0.9, 0.9); body.position.y = 0.55; g.add(body);
  for (const [x, z] of [[-0.25, -0.15], [-0.25, 0.15], [0.25, -0.15], [0.25, 0.15]]) { const l = Cap(0.045, 0.2, face); l.position.set(x, 0.14, z); g.add(l); }
  const head = new THREE.Group(); head.position.set(0.52, 0.72, 0); g.add(head); head.add(Sph(0.19, face, 1.15, 1.0, 0.9));
  for (const s of [-1, 1]) { const e = Sph(0.03, mat(0xffffff), 1, 1.2, 0.8); e.position.set(0.13, 0.05, s * 0.09); head.add(e); const p = Sph(0.015, mat(0x000000)); p.position.set(0.15, 0.05, s * 0.09); head.add(p); const ear = Sph(0.07, face, 1.2, 0.5, 0.5); ear.position.set(-0.04, 0.06, s * 0.2); head.add(ear); }
  const tuft = Sph(0.13, wool); tuft.position.set(-0.02, 0.17, 0); head.add(tuft);
  g.userData.head = head; g.scale.setScalar(sc); return g;
}

// ------------------------------------------------------------------ clouds & mountains
export function makeCloud(seed, col = 0xffe9d0, sc = 1) {
  const g = new THREE.Group(); const R = rnd(seed); const m = mat(col, { flat: true, fog: false });
  const n = 7; for (let i = 0; i < n; i++) { const s = Sph((7 + R() * 7) * sc, m, 1, 0.62, 0.9, 12); s.position.set((i - n / 2) * 8 * sc + (R() - .5) * 4, (R() - .3) * 3 * sc, (R() - .5) * 6); s.userData.noShadow = true; g.add(s); }
  return g;
}
export function makeMountain(h, rad, seed, col = 0x6a7a8a, snow = 0xf4f6fa, snowFrac = 0.28) {
  const R = rnd(seed); const g = new THREE.ConeGeometry(rad, h, 9, 5, true).toNonIndexed(); g.translate(0, h / 2, 0);
  const p = g.attributes.position; const c = new Float32Array(p.count * 3); const k0 = new THREE.Color(col), k1 = new THREE.Color(snow);
  const jit = new Map(); for (let i = 0; i < p.count; i++) { const key = p.getX(i).toFixed(2) + p.getY(i).toFixed(2) + p.getZ(i).toFixed(2); if (!jit.has(key)) jit.set(key, [(R() - .5) * rad * 0.18, (R() - .5) * h * 0.06, (R() - .5) * rad * 0.18]); const j = jit.get(key); const f = p.getY(i) / h < 0.98 ? 1 : 0; p.setXYZ(i, p.getX(i) + j[0] * f, p.getY(i) + j[1] * f, p.getZ(i) + j[2] * f); }
  g.computeVertexNormals();
  for (let i = 0; i < p.count; i += 3) { const yc = (p.getY(i) + p.getY(i + 1) + p.getY(i + 2)) / 3 / h; const k = yc > 1 - snowFrac ? k1 : k0.clone().multiplyScalar(0.85 + 0.3 * R()); c.set([k.r, k.g, k.b, k.r, k.g, k.b, k.r, k.g, k.b], i * 3); }
  g.setAttribute('color', new THREE.BufferAttribute(c, 3));
  const m = new THREE.Mesh(g, new THREE.MeshToonMaterial({ vertexColors: true, gradientMap: GRAD })); m.castShadow = m.receiveShadow = true; return m;
}
