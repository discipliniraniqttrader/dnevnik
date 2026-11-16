"""STYLE "silhouette": one dusk world, every object a black silhouette with a thin warm rim light, always-moving camera.

Used by make_short.py when script.json has "style": "silhouette".  Everything is drawn with cv2/PIL/numpy vector shapes.
Pipeline: voice (shortkit.voice) -> plan (beat windows + 1-2 word captions + sound events) -> resumable chunk render -> mux -> 9 MB HEVC -> sheet -> report.json
"""
import hashlib, json, math, multiprocessing as mp, os, pickle, re, subprocess, sys, time
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw
from .common import W, H, FPS, F, ease, MONT_BLACK

SUN = (400, 1210)                       # sun position (screen)
GYB = 1290                              # reference ground line (screen y of world y=0)
WARM_W, GOLD_C = (255, 241, 214), (255, 206, 92)
KW_YELLOW = (255, 210, 63)              # #FFD23F
BLACK = np.array([5, 7, 9], np.float32)
DETC = np.array([70, 40, 22], np.float32)
RIMC = np.array([255, 170, 80], np.float32)
XF = 0.5                               # crossfade between scenes (s)
ALIAS = {"137": "thirty-seven", "never": "ever"}


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def sstep(x): x = clamp(x); return x * x * (3 - 2 * x)
def lerp(a, b, u): return a + (b - a) * u
def rot(pts, a, pv):
    c, s = math.cos(a), math.sin(a); p = np.asarray(pts, np.float32) - pv
    return np.stack([p[:, 0] * c - p[:, 1] * s, p[:, 0] * s + p[:, 1] * c], 1) + pv


# ====================================================================== drawing primitives
def _fx(p): return (np.clip(np.asarray(p, np.float32), -20000, 20000) * 16).astype(np.int32)


def fill(img, pts, val=255):
    cv2.fillPoly(img, [_fx(pts)], int(val) if np.ndim(val) == 0 else val, cv2.LINE_AA, 4)


def line(img, p, q, th=2, val=255):
    cv2.line(img, tuple(int(v) for v in _fx(p)), tuple(int(v) for v in _fx(q)), int(val), int(th), cv2.LINE_AA, 4)


def circ(img, c, r, val=255):
    cv2.circle(img, tuple(int(v) for v in _fx(c)), int(r * 16), int(val), -1, cv2.LINE_AA, 4)


class Cam:
    """world (metres, y up) -> screen. vex = vertical exaggeration (artistic)."""
    def __init__(s, z, cx, cy=0.0, gy=GYB, vex=1.0): s.z, s.cx, s.cy, s.gy, s.vex = z, cx, cy, gy, vex
    def p(s, pts, vex=None):
        a = np.asarray(pts, np.float32).reshape(-1, 2); v = s.vex if vex is None else vex
        return np.stack([540 + (a[:, 0] - s.cx) * s.z, s.gy - (a[:, 1] - s.cy) * s.z * v], 1)
    def pt(s, x, y, vex=None): return tuple(s.p([(x, y)], vex)[0])


class Cv:
    """one scene's layers.  sil: black silhouette, det: faint detail lines inside silhouettes, mid: hazy mid-ground layer,
    glow: additive light (half res), oW/oG: overlay masks (warm white / gold), texts drawn last."""
    def __init__(s, t):
        s.t = t
        s.sil = np.zeros((H, W), np.uint8); s.det = np.zeros((H, W), np.uint8); s.mid = None
        s.glow = None; s.hole = None; s.gf = None; s.oW = np.zeros((H, W), np.uint8); s.oG = np.zeros((H, W), np.uint8); s.texts = []; s.rain = 0.5; s.pills = []
    def midl(s):
        if s.mid is None: s.mid = np.zeros((H, W), np.uint8)
        return s.mid
    def gl(s):
        if s.glow is None: s.glow = np.zeros((H // 2, W // 2, 3), np.uint8)
        return s.glow
    def hpoly(s, pts, val=255):
        if s.hole is None: s.hole = np.zeros((H, W), np.uint8)
        fill(s.hole, pts, val)
    def gfpoly(s, pts, col):
        if s.gf is None: s.gf = np.zeros((H // 2, W // 2, 3), np.uint8)
        cv2.fillPoly(s.gf, [_fx(np.asarray(pts, np.float32) / 2)], tuple(int(c) for c in col), cv2.LINE_AA, 4)
    def gpoly(s, pts, col):                       # glow polygon (full-res coords)
        g = s.gl(); cv2.fillPoly(g, [_fx(np.asarray(pts, np.float32) / 2)], tuple(int(c) for c in col), cv2.LINE_AA, 4)
    def gcirc(s, c, r, col):
        g = s.gl(); cv2.circle(g, tuple(int(v) for v in _fx(np.asarray(c) / 2)), int(r / 2 * 16), tuple(int(c_) for c_ in col), -1, cv2.LINE_AA, 4)
    def ln(s, layer, p, q, th=3, a=1.0):
        line(s.oG if layer == "G" else s.oW, p, q, th, 255 * clamp(a))
    def text(s, txt, x, y, size, layer="W", a=1.0, anchor="mm"):
        if a > 0.01: s.texts.append((txt, x, y, size, layer, a, anchor))
    def finish(s):
        if s.glow is not None: s.glow[:] = cv2.GaussianBlur(s.glow, (0, 0), 6)
        if s.texts or s.pills:
            ims = {k: Image.new("L", (W, H), 0) for k in "WG"}; ds = {k: ImageDraw.Draw(v) for k, v in ims.items()}
            for (txt, x, y, size, layer, a, anchor) in s.texts: ds[layer].text((x, y), txt, font=F(MONT_BLACK, size), fill=int(255 * clamp(a)), anchor=anchor)
            for (box, layer, a, wd) in s.pills: ds[layer].rounded_rectangle(box, radius=(box[3] - box[1]) // 2, outline=int(255 * clamp(a)), width=wd)
            for k, tgt in (("W", s.oW), ("G", s.oG)): np.maximum(tgt, np.asarray(ims[k]), out=tgt)


def dim(C, a, b, off, prog, label=None, size=50, layer="G", alpha=1.0, lab=None, th=4, ext=True, tick=20):
    """dimension line from screen a to b, offset `off` px perpendicular, drawing on with prog 0..1; label fades in near the end"""
    a = np.array(a, np.float32); b = np.array(b, np.float32); d = b - a; L = float(np.hypot(*d)) + 1e-6; u = d / L; n = np.array([-u[1], u[0]], np.float32)
    a2, b2 = a + n * off, b + n * off; prog = clamp(prog)
    if prog <= 0: return
    e = a2 + (b2 - a2) * prog
    C.ln(layer, a2, e, th, alpha); C.ln(layer, a2 - n * tick, a2 + n * tick, th, alpha)
    if ext: C.ln(layer, a, a2 + n * np.sign(off) * 6, 2, alpha * 0.55)
    if prog > 0.995:
        C.ln(layer, b2 - n * tick, b2 + n * tick, th, alpha)
        if ext: C.ln(layer, b, b2 + n * np.sign(off) * 6, 2, alpha * 0.55)
    if label and prog > 0.7:
        m = lab if lab is not None else (a2 + b2) / 2 + n * np.sign(off) * 40
        C.text(label, float(clamp(m[0], 90, 990, )) if lab is None else m[0], m[1], size, layer, alpha * sstep((prog - 0.7) / 0.3))


# ====================================================================== shapes
def bez(p0, p1, p2, n=10):
    t = np.linspace(0, 1, n)[:, None]; p0, p1, p2 = map(np.array, (p0, p1, p2))
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2


def ark_polys(off=None):
    """Ark side view in metres (centre x=0, keel y=0). Genesis 6:15-16: 137 x 22.9 x 13.7 m (30 cubits high)."""
    top = lambda x: 8.4 + 2.2 * (abs(x) / 66.0) ** 3
    xs = np.linspace(-66, 66, 34)
    hull = [(-58, 0.2), (-63, 1.5), (-66.5, 5), (-67.2, 8.5)] + [(x, top(x)) for x in xs] + [(70, 11.6), (72.6, 12.5), (71.8, 9), (69.3, 5.5), (64, 2), (58, 0.2)]
    hull = hull[:4] + hull[4:]
    hull = np.array(hull, np.float32)
    bot = np.array([(x, 0.0) for x in np.linspace(54, -54, 14)], np.float32)
    hull = np.concatenate([hull, bot])
    house = np.array([(-57, 8.2), (-55.5, 12.6), (-51, 13.7), (51, 13.7), (55.5, 12.6), (57, 8.2)], np.float32)
    if off is not None:
        for P in (hull, house): P[:, 1] += off(P[:, 0])
    return hull, house


def draw_ark(C, cam, ox=0.0, oy=0.0, rot_a=0.0, off=None, detail=True, vex=None, seams=()):
    hull, house = ark_polys(off)
    pv = np.array([ox, oy], np.float32)
    parts = [np.asarray(h, np.float32) + pv for h in (hull, house)]
    if rot_a: parts = [rot(p, rot_a, pv) for p in parts]
    for p in parts: fill(C.sil, cam.p(p, vex))
    if detail:
        for k in range(1, 12):                         # planks
            y = 1.15 * k; xs = np.linspace(-66, 70, 16)
            pts = np.stack([xs, np.full_like(xs, y) + (off(xs) if off else 0)], 1) + pv
            if rot_a: pts = rot(pts, rot_a, pv)
            sp = cam.p(pts, vex)
            cv2.polylines(C.det, [_fx(sp)], False, 150 if k % 2 else 100, 1, cv2.LINE_AA, 4)
        for x in np.arange(-60, 62, 5.5):              # ribs on the house
            a, b = np.array([x, 8.4]), np.array([x, 13.2]); pts = np.array([a, b], np.float32) + pv
            if off: pts[:, 1] += off(np.array([x, x]))
            if rot_a: pts = rot(pts, rot_a, pv)
            sp = cam.p(pts, vex); line(C.det, sp[0], sp[1], 1, 90)
    return parts


def person(C, cam, x, y, h, step=0.0, vex=1.0, arms=0.0):
    s = h; P = lambda pts: cam.p(np.asarray(pts, np.float32) + np.array([x, y], np.float32), vex)
    k = 0.10 * s * math.sin(step)
    fill(C.sil, P([(-0.1 * s, 0.82 * s), (0.1 * s, 0.82 * s), (0.085 * s, 0.5 * s), (-0.085 * s, 0.5 * s)]))
    fill(C.sil, P([(-0.085 * s, 0.52 * s), (-0.005 * s, 0.52 * s), (-0.01 * s + k, 0.0), (-0.075 * s + k, 0.0)]))
    fill(C.sil, P([(0.085 * s, 0.52 * s), (0.005 * s, 0.52 * s), (0.01 * s - k, 0.0), (0.075 * s - k, 0.0)]))
    fill(C.sil, P([(-0.12 * s, 0.8 * s), (-0.095 * s, 0.8 * s), (-0.095 * s - 0.02 * s * arms, 0.52 * s + 0.2 * s * arms), (-0.14 * s, 0.52 * s)]))
    fill(C.sil, P([(0.12 * s, 0.8 * s), (0.095 * s, 0.8 * s), (0.095 * s, 0.52 * s), (0.14 * s, 0.52 * s)]))
    c = cam.p([(x, y + 0.905 * s)], vex)[0]; circ(C.sil, c, 0.072 * s * cam.z)


def wave_poly(cam, base, amp, wl, spd, t, ph=0.0):
    sx = np.arange(-12, W + 20, 8, dtype=np.float32); wx = cam.cx + (sx - 540) / cam.z
    y = base + amp * np.sin(2 * math.pi * (wx / wl - spd * t) + ph) + 0.45 * amp * np.sin(2 * math.pi * (wx / (wl * 0.53) - spd * 1.31 * t) + ph * 2.1)
    sy = cam.gy - (y - cam.cy) * cam.z
    return np.concatenate([np.stack([sx, sy], 1), [(W + 30, H + 60), (-30, H + 60)]]).astype(np.float32)


def land_poly(cam, h0, flat=80.0, amp=1.0, step=6):
    sx = np.arange(-12, W + 20, step, dtype=np.float32); wx = cam.cx + (sx - 540) / cam.z
    fade = np.clip((np.abs(wx) - flat) / 60.0, 0, 1) ** 1.2 * amp
    g = h0 + fade * (3.2 * np.sin(wx * 0.045 + 1) + 2.0 * np.sin(wx * 0.11 + 2) + 0.9 * np.sin(wx * 0.27))
    sy = cam.gy - (g - cam.cy) * cam.z - 5 * np.maximum(0, np.sin(wx * 5.1) * np.sin(wx * 12.0 + 1))
    return np.concatenate([np.stack([sx, sy], 1), [(W + 30, H + 60), (-30, H + 60)]]).astype(np.float32)


def solid(C, pts):
    fill(C.sil, pts); fill(C.det, pts, 0)


def spray(C, cam, ox, oy, vx, vy, t, n, seed, a=0.7, g=26.0, life=1.1, size=2.4, layer="W"):
    rng = np.random.default_rng(seed); img = C.oW if layer == "W" else C.oG
    for i in range(n):
        ph = (t / life + rng.random()) % 1.0; tt = ph * life
        v = rng.uniform(0.6, 1.25); x = ox + vx * v * tt + rng.normal(0, .12); y = oy + vy * v * tt - 0.5 * g * tt * tt
        sx, sy = cam.pt(x, y, 1.0); al = 255 * a * math.sin(math.pi * ph) ** 0.7 * (0.5 + 0.5 * rng.random())
        circ(img, (sx, sy), size * (0.6 + 0.8 * rng.random()), al)


def cargo_polys():
    hull = [(-100, -5), (95, -5), (103, 3), (110, 14), (100, 14), (-99, 14), (-100, 9)]
    house = [(-90, 14), (-90, 41), (-72, 41), (-72, 14)]
    wing = [(-93, 36), (-93, 40), (-69, 40), (-69, 36)]
    funnel = [(-86, 41), (-86, 49), (-79, 49), (-77, 41)]
    boxes = []
    rng = np.random.default_rng(5)
    for x in np.arange(-66, 92, 12.2):
        h = rng.choice([6, 9, 12, 15]); boxes.append([(x, 14), (x, 14 + h), (x + 11, 14 + h), (x + 11, 14)])
    return [hull, house, wing, funnel] + boxes, [(95, 14), (95, 25)]


def titanic_polys():
    hull = [(-132, -6), (112, -6), (124, 4), (134, 17.5), (125, 17.5), (-120, 17.5), (-128, 17.5), (-134, 16), (-133, 6)]
    deck = [(-96, 17.5), (-96, 24), (92, 24), (92, 17.5)]
    bridge = [(70, 24), (70, 29), (90, 29), (90, 24)]
    polys = [hull, deck, bridge]
    for fx in (-48, -17, 14, 45):
        polys.append([(fx - 4, 24), (fx - 5.2, 42), (fx + 3.2, 42), (fx + 4, 24)])
    polys.append([(100, 17.5), (100.8, 17.5), (100.8, 52), (100, 52)])
    polys.append([(-112, 17.5), (-111.2, 17.5), (-111.2, 41), (-112, 41)])
    return polys


def schooner_polys():
    hull = [(-54, -3), (40, -3), (52, 3), (64, 8), (52, 6), (-52, 6), (-56, 3)]
    polys = [hull]; lines = []
    masts = np.linspace(-42, 36, 6)
    for mx in masts:
        lines.append([(mx, 6), (mx, 46)])
        polys.append([(mx - 0.4, 6.5), (mx - 0.4, 38), (mx - 14, 33), (mx - 14, 7.5)])          # gaff sail trails aft
        polys.append([(mx - 0.4, 38.5), (mx - 0.4, 45), (mx - 9, 40)])                          # topsail
    lines.append([(52, 6), (66, 12)])                                                       # bowsprit
    lines.append([(66, 12), (masts[-1], 45)]); lines.append([(60, 11), (masts[-1], 30)])      # stays
    lines.append([(-52, 6), (masts[0], 44)])
    polys.append([(52, 7), (62, 11), (masts[-1] + 1, 43)])                                    # jib
    return polys, lines


def toy_boat(C, cx, cy, s, ang):
    P = lambda pts: rot(np.array(pts, np.float32) * s + np.array([cx, cy], np.float32), ang, np.array([cx, cy], np.float32))
    hull = np.concatenate([[(-1.0, -0.15), (1.0, -0.15)], bez((1.0, -0.15), (0.85, 0.55), (0.2, 0.6), 8), bez((-0.2, 0.6), (-0.8, 0.55), (-1.0, -0.15), 8)])
    fill(C.sil, P(hull)); fill(C.sil, P([(-0.05, -0.15), (0.0, -1.1), (0.05, -1.1), (0.08, -0.15)]))
    fill(C.sil, P([(0.1, -1.05), (0.1, -0.2), (0.62, -0.2)])); fill(C.sil, P([(-0.1, -0.95), (-0.1, -0.25), (-0.55, -0.25)]))
    fill(C.sil, P([(0.0, -1.1), (0.0, -1.3), (0.28, -1.22)]))


# ====================================================================== scene pieces: f(C, lt, dur)














def _ship_from(C, cam, polys, ox, oy, a=0.0, vex=1.0, lines_=()):
    pv = np.array([ox, 0.0], np.float32)
    for pl in polys:
        pts = np.asarray(pl, np.float32) + np.array([ox, oy], np.float32)
        if a: pts = rot(pts, a, np.array([ox, oy], np.float32))
        fill(C.sil, cam.p(pts, vex))
    for (q0, q1) in lines_:
        pts = np.array([q0, q1], np.float32) + np.array([ox, oy], np.float32)
        if a: pts = rot(pts, a, np.array([ox, oy], np.float32))
        s = cam.p(pts, vex); line(C.sil, s[0], s[1], 2)


def pc_cargo(C, lt, dur):
    p = lt / dur; t = C.t; cam = Cam(6.1, lerp(15, 170, sstep(p * 0.95)), vex=1.0)
    ark_cam = Cam(6.1, cam.cx, vex=1.5)
    sea = wave_poly(cam, 0.0, 1.1, 38, 0.05, t, 0.7); solid(C, cam.p(wave_poly(cam, 0.8, 0.7, 52, 0.04, t, 2.0), 1.0))
    ba = 0.55 * math.sin(t * 1.4); bb = 0.4 * math.sin(t * 1.2 + 1.0)
    draw_ark(C, ark_cam, 0, ba + 0.4, 0.012 * math.sin(t * 1.4 + 0.5), vex=1.5, detail=False)
    pl, mast = cargo_polys(); _ship_from(C, cam, pl, 195, bb + 0.9, 0.01 * math.sin(t * 1.2 + 1.0), 1.0, [mast])
    fill(C.sil, cam.p(sea, 1.0))
    ya = cam.pt(0, 25, 1.5)[1]; ax = cam.pt(0, 0)[0]; sx = cam.pt(195, 0)[0]
    ax = clamp(ax, 150, 930); C.text("ARK", ax, ya - 60, 60, "G", sstep(p / 0.15)); C.text("6 : 1", ax, ya - 5, 54, "W", sstep(p / 0.15))
    sx = clamp(sx, 230, 850); C.text("CARGO SHIP", sx, cam.pt(0, 58, 1.0)[1] - 30, 60, "G", sstep(p / 0.15)); C.text("~6 : 1", sx, cam.pt(0, 58, 1.0)[1] + 28, 54, "W", sstep(p / 0.15))
    C.rain = 0.7






def pc_schooner(C, lt, dur):
    p = lt / dur; t = C.t; cam = Cam(lerp(8.6, 10.2, p), lerp(-6, 6, p), vex=1.0)
    roll = 0.075 * math.sin(t * 1.5) + 0.02 * math.sin(t * 3.1)
    solid(C, cam.p(wave_poly(cam, 0.2, 2.4, 48, 0.07, t, 1.3), 1.0))
    polys, lines_ = schooner_polys(); oy = 3.2 + 1.0 * math.sin(t * 1.5 + 0.6)
    _ship_from(C, cam, polys, 0, oy, roll, 1.0, lines_)
    for k, px in enumerate([-14, 4, 20]):                     # pumps on deck, streams over the side
        pv = np.array([0, oy], np.float32); q = rot(np.array([(px, 6.0)], np.float32) + np.array([0, oy], np.float32), roll, pv)[0]
        fill(C.sil, cam.p(rot(np.array([(px - 0.8, 6), (px + 0.8, 6), (px + 0.5, 9.5), (px - 0.5, 9.5)], np.float32) + np.array([0, oy], np.float32), roll, pv), 1.0))
        sx0 = cam.p(rot(np.array([(px, 9.0)], np.float32) + np.array([0, oy], np.float32), roll, pv), 1.0)[0]
        o = cam.p([(0, 0)], 1.0)[0]
        w0 = np.array([px, 9.0 + oy]); spray(C, cam, px + 0.2, 9.0 + oy, 6.5 + k, 4.5, t + k * 0.31, 22, 70 + k, a=0.9, g=18, life=1.25, size=3.0)
    solid(C, cam.p(wave_poly(cam, -1.6, 2.6, 40, 0.09, t, 3.1), 1.0))
    C.text("WOODEN SCHOONER, 1909", 540, 560, 52, "W", sstep((p - 0.1) / 0.2))
    C.text("PUMPS RUNNING", 540, 640, 84, "G", sstep((p - 0.4) / 0.2))
    C.rain = 1.0









def pc_toy_and_ark(C, lt, dur):
    p = lt / dur; t = C.t; cam = Cam(6.2 + 0.9 * p, -2 + 8 * p, vex=1.6)
    rise = sstep((p - 0.42) / 0.5); oy = -27 * (1 - rise)
    draw_ark(C, cam, 0, oy + 0.3, vex=1.6)
    bsink = sstep((p - 0.45) / 0.3)
    bx = 540 - 640 * bsink; by = GYB - 175 + 26 * math.sin(t * 2.6) + 300 * bsink
    toy_boat(C, bx, by, 215, 0.12 * math.sin(t * 2.0 + 1) - 0.5 * bsink)
    solid(C, cam.p(wave_poly(cam, 0.5, 0.9, 30, 0.06, t, 0.4), 1.0))
    solid(C, cam.p(wave_poly(cam, -1.8, 1.1, 26, 0.08, t, 2.4), 1.0))
    a = sstep((p - 0.2) / 0.1); b = sstep((p - 0.29) / 0.1); fo = 1 - sstep((p - 0.62) / 0.1)
    cx, cy, r = bx, by - 30, 175
    if a > 0: C.ln("G", (cx - r, cy - r), (cx - r + 2 * r * a, cy - r + 2 * r * a), 16, fo)
    if b > 0: C.ln("G", (cx + r, cy - r), (cx + r - 2 * r * b, cy - r + 2 * r * b), 16, fo)
    C.rain = 0.6


def pc_dims(C, lt, dur):
    p = lt / dur; t = C.t; cam = Cam(5.9 + 0.9 * p, -6 + 12 * p, vex=2.0)
    draw_ark(C, cam, vex=2.0); solid(C, cam.p(land_poly(cam, 1.6, 74), 1.0))
    base = cam.pt(0, 0)[1]
    pL = clamp((p - 0.12) / 0.3); pH = clamp((p - 0.38) / 0.28); pW = clamp((p - 0.6) / 0.3)
    xl, xr = cam.pt(-67, 0)[0], cam.pt(73, 0)[0]
    dim(C, (xl, base + 8), (xr, base + 8), 105, pL, "300 CUBITS", 54, lab=(clamp((xl + xr) / 2, 300, 780), base + 175))
    xh = cam.pt(-28, 0)[0]; yb, yt = cam.pt(0, 0, 2.0)[1], cam.pt(0, 13.7, 2.0)[1]
    if pH > 0:
        C.ln("G", (xh, yb), (xh, yb + (yt - yb) * pH), 5, 1.0); C.ln("G", (xh - 22, yb), (xh + 22, yb), 5, 1.0)
        if pH > .99: C.ln("G", (xh - 22, yt), (xh + 22, yt), 5, 1.0)
    if pH > 0.7: C.text("30", xh, yt - 60, 66, "G", sstep((pH - .7) / .3))
    ix, iy, iw, ih = 560, 540, 330, 200
    ins = np.array([(ix, iy), (ix + iw, iy), (ix + iw, iy + ih * 0.62)] + list(bez((ix + iw, iy + ih * 0.62), (ix + iw * 0.92, iy + ih), (ix + iw * 0.7, iy + ih), 7)) + list(bez((ix + iw * 0.3, iy + ih), (ix + iw * 0.08, iy + ih), (ix, iy + ih * 0.62), 7)) + [(ix, iy)], np.float32)
    ia = sstep(pW / 0.5)
    if ia > 0:
        nn = max(2, int(len(ins) * ia))
        for k in range(nn - 1): C.ln("W", ins[k], ins[k + 1], 5, 0.9)
    dim(C, (ix, iy), (ix + iw, iy), -62, pW, "50", 62, layer="G", lab=(ix + iw / 2, iy - 135))
    C.rain = 0.55


def pc_forearm(C, lt, dur):
    p = lt / dur; t = C.t
    sc = 0.88 + 0.04 * p; ang = math.radians(-26 - 2 * p); org = np.array([-70 - 14 * p, GYB + 340 - 20 * p], np.float32)
    def T(u, v): c, s = math.cos(ang), math.sin(ang); return np.array([org[0] + (u * c - v * s) * sc, org[1] + (u * s + v * c) * sc], np.float32)
    us = np.linspace(0, 780, 24)
    wid = lambda u: 98 - 38 * (u / 780) + 13 * math.sin(math.pi * u / 780)
    top = [T(u, -wid(u)) for u in us]; bot = [T(u, wid(u) * 0.95) for u in us[::-1]]
    cap = [T(-95 * math.sin(a), -98 * math.cos(a)) for a in np.linspace(0, math.pi, 14)]
    fill(C.sil, np.array(cap + top + bot))
    fill(C.sil, np.array([T(740, -56), T(930, -66), T(930, 70), T(740, 62)]))
    for (v, ln_, w, fan) in [(-48, 235, 30, -0.07), (-16, 265, 31, -0.02), (16, 250, 30, 0.03), (48, 205, 27, 0.09)]:
        u0 = 920; u1 = u0 + ln_; dv = fan * ln_
        fill(C.sil, np.array([T(u0, v - w / 2), T(u1, v - w / 2 + dv), T(u1, v + w / 2 + dv), T(u0, v + w / 2)])); circ(C.sil, T(u1, v + dv), w * 0.5 * sc)
    fill(C.sil, np.array([T(780, -56), T(870, -130), T(930, -170), T(960, -150), T(910, -92), T(930, -66)])); circ(C.sil, T(945, -160), 17 * sc)
    lenpx = 1170
    pr = sstep((p - 0.08) / 0.45)
    cv2.fillPoly(C.oW, [_fx(np.array([T(0, 190), T(lenpx, 190), T(lenpx, 252), T(0, 252)]))], 38, cv2.LINE_AA, 4)
    ur = lenpx * pr
    if pr > 0:
        C.ln("W", T(0, 190), T(ur, 190), 3, 0.9); C.ln("W", T(0, 252), T(ur, 252), 3, 0.9)
        for k in range(0, 46):
            u = k * lenpx / 45.0
            if u > ur: break
            C.ln("W", T(u, 190), T(u, 190 + (46 if k % 5 == 0 else 26)), 3 if k % 5 == 0 else 2, 0.95)
    for k in (0, 15, 30, 45):
        u = k * lenpx / 45.0
        if u <= ur: C.text(str(k), *T(u, 330), 46, "W", 0.9)
    pe = sstep((p - 0.62) / 0.2)
    if pe > 0:
        C.text("ELBOW", *T(60, -200), 44, "W", pe * 0.9); C.text("FINGERTIP", *T(1180, -300), 44, "W", pe * 0.9)
        C.text("45 cm", 540, 600, 150, "G", pe)
    C.rain = 0.5


def pc_pullback(C, lt, dur):
    p = lt / dur; t = C.t; z = lerp(14.5, 6.6, sstep(p * 0.92)); cam = Cam(z, lerp(-44, 3, sstep(p * 0.92)), vex=2.0)
    draw_ark(C, cam, vex=2.0); solid(C, cam.p(land_poly(cam, 1.6, 74), 1.0))
    base = cam.pt(0, 0)[1]; prog = sstep((p - 0.05) / 0.78)
    xl = cam.pt(-67, 0)[0]; xr = cam.pt(73, 0)[0]
    dim(C, (xl, base + 8), (xr, base + 8), 105, prog, None, 50)
    C.text(f"{137 * prog:.0f} m", 540, 600, 190, "W", 1.0)
    C.rain = 0.55


def pc_field(C, lt, dur):
    p = lt / dur; t = C.t; zp = sstep(clamp(p / 0.72))
    z = lerp(52, 7.4, zp ** 0.85); cx = lerp(2, 62, zp); cam = Cam(z, cx, vex=1.0)
    ak = sstep((p - 0.30) / 0.42); axc = 69.5 + 190 * (1 - ak)
    draw_ark(C, Cam(z, cx, vex=2.0), axc, 0.2, vex=2.0)
    solid(C, cam.p(land_poly(cam, 0.0, 400), 1.0))
    C.gpoly(cam.p([(-3, 0), (95, 0), (95, 1.2), (-3, 1.2)], 1.0), (130, 92, 36))
    for k in range(0, 11):
        x = k * 9.1; C.ln("W", cam.pt(x, 0.05, 1.0), cam.pt(x, 0.9, 1.0), 2, 0.8)
    for gx in (0, 91):
        for (a, b) in [((gx, 0), (gx, 3.05)), ((gx - 2.8, 3.05), (gx + 2.8, 3.05)), ((gx - 2.8, 3.05), (gx - 2.8, 9.2)), ((gx + 2.8, 3.05), (gx + 2.8, 9.2))]:
            line(C.sil, cam.pt(*a, 1.0), cam.pt(*b, 1.0), max(2, 0.14 * z))
    for lx in (-7, 98):
        a, b = cam.pt(lx, 0, 1.0), cam.pt(lx, 26, 1.0); line(C.sil, a, b, max(2, 0.35 * z))
        fill(C.sil, cam.p([(lx - 2.6, 26), (lx + 2.6, 26), (lx + 2.6, 28.2), (lx - 2.6, 28.2)], 1.0))
        C.gcirc(b, 0.35 * z * 2 + 36, (170, 120, 50))
    person(C, cam, 3.0, 0, 1.82, 0.0, 1.0)
    fp = clamp((p - 0.22) / 0.25); ap = clamp((p - 0.7) / 0.25)
    base = cam.pt(0, 0, 1.0)[1]; x0, x1 = cam.pt(0, 0)[0], cam.pt(91, 0)[0]; x2 = cam.pt(137, 0)[0]
    dim(C, (x0, base + 6), (x1, base + 6), 70, fp, "FOOTBALL FIELD 91 m", 46, layer="W", lab=(clamp((x0 + x1) / 2, 330, 750), base + 160))
    dim(C, (x0, base + 6), (x2, base + 6), 215, ap, "ARK = 1.5 FIELDS", 54, layer="G", lab=(clamp((x0 + x2) / 2, 330, 750), base + 300))
    C.rain = 0.45


def pc_cutaway(C, lt, dur):
    p = lt / dur; t = C.t; cam = Cam(lerp(11.5, 14.5, p), lerp(36, 18, p), vex=1.6)
    draw_ark(C, cam, detail=False, vex=1.6)
    solid(C, cam.p(land_poly(cam, 0.8, 74), 1.0))
    decks = [(-56, 59, 1.1, 4.3), (-56, 59, 4.95, 8.15), (-53, 55, 8.8, 12.4)]
    cols = [(220, 118, 38), (240, 140, 52), (250, 165, 76)]
    for k, (xa, xb, ya, yb) in enumerate(decks):
        lit = sstep((p - (0.12 + 0.2 * k)) / 0.16)
        box = cam.p([(xa, ya), (xb, ya), (xb, yb), (xa, yb)], 1.6)
        C.hpoly(box, 255); C.gfpoly(box, tuple(c * (0.10 + 0.9 * lit) for c in cols[k]))
        for x in np.arange(xa + 8, xb - 4, 14): C.hpoly(cam.p([(x - .35, ya), (x + .35, ya), (x + .35, yb), (x - .35, yb)], 1.6), 0)
        if lit > 0.5: C.text(f"DECK {k + 1}", 90, 560 + k * 80, 54, "G", sstep((lit - .5) / .5), "lm")
        if lit > 0.3: C.ln("G", (330, 560 + k * 80), cam.pt(xa + 6, (ya + yb) / 2, 1.6), 2, sstep((lit - .3) / .4) * 0.7)
    dp = sstep((p - 0.55) / 0.15)
    C.hpoly(cam.p([(21, 1.1), (26, 1.1), (26, 6.4), (21, 6.4)], 1.6), 255)
    C.gfpoly(cam.p([(21, 1.1), (26, 1.1), (26, 6.4), (21, 6.4)], 1.6), tuple(int(c * (0.2 + 0.8 * dp)) for c in (255, 214, 140)))
    if dp > 0.4: C.text("DOOR", 900, 760, 54, "G", sstep((dp - .4) / .6)); C.ln("G", (900, 785), cam.pt(24, 6.4, 1.6), 2, 0.7)
    wp = sstep((p - 0.76) / 0.15)
    slit = cam.p([(-42, 12.95), (44, 12.95), (44, 13.55), (-42, 13.55)], 1.6)
    C.hpoly(slit, 255); C.gfpoly(slit, tuple(int(c * (0.2 + 0.8 * wp)) for c in (255, 226, 160)))
    C.gpoly(cam.p([(-36, 13.5), (40, 13.5), (46, 24), (-42, 24)], 1.6), tuple(int(c * 0.14 * wp) for c in (255, 226, 160)))
    if wp > 0.4: C.text("OPENING", 760, 480, 54, "G", sstep((wp - .4) / .6)); C.ln("G", (700, 505), cam.pt(-4, 13.6, 1.6), 2, 0.7)
    C.rain = 0.5


def pc_topdown(C, lt, dur):
    p = lt / dur; t = C.t; cam = Cam(7.1 + 0.5 * p, lerp(-3, 3, p), gy=1150, vex=1.0)
    plan = np.array([(-68, -11.45), (46, -11.45), (58, -9.2), (68, -4), (72, 0), (68, 4), (58, 9.2), (46, 11.45), (-68, 11.45)], np.float32)
    fill(C.sil, cam.p(plan, 1.0))
    for k in range(-5, 6): line(C.det, cam.pt(-68, k * 2.1, 1.0), cam.pt(60 - abs(k) * 1.4, k * 2.1, 1.0), 1, 110)
    wunit = 22.9; sqp = clamp((p - 0.12) / 0.62); x0 = -68
    for k in range(6):
        a = sstep(sqp * 6 - k)
        if a <= 0: continue
        xa, xb = x0 + k * wunit, x0 + (k + 1) * wunit
        box = cam.p([(xa, -11.45), (xb, -11.45), (xb, 11.45), (xa, 11.45)], 1.0)
        for (u, v) in [(0, 1), (1, 2), (2, 3), (3, 0)]: C.ln("G", box[u], box[v], 4, a * 0.95)
        c = box.mean(0); C.text(str(k + 1), c[0], c[1], 64, "G", a)
    C.text("6 : 1", 540, 600, 200, "G", sstep((p - 0.6) / 0.2))
    L1, L2 = cam.pt(-68, 0, 1.0)[0], cam.pt(72, 0, 1.0)[0]; yb = cam.pt(0, -11.45, 1.0)[1]
    dim(C, (L1, yb), (L2, yb), 56, clamp((p - 0.1) / 0.4), "LENGTH 300", 48, layer="W", lab=(540, yb + 140))
    yt = cam.pt(0, 11.45, 1.0)[1]
    C.text("WIDTH 50", 540, yt - 80, 50, "W", sstep((p - 0.45) / 0.2))
    C.rain = 0.5


def pc_titanic(C, lt, dur):
    p = lt / dur; t = C.t; z = 3.85; cx = 67 + 4 * p
    cT = Cam(z, cx, gy=1235, vex=1.0); cA = Cam(z, cx, gy=1385, vex=2.0)
    slide = sstep(p / 0.5); tx = 67 + 330 * (1 - slide)
    solid(C, cT.p(wave_poly(cT, 0.6, 0.9, 60, 0.04, t, 2.0), 1.0))
    _ship_from(C, cT, titanic_polys(), tx, 1.0 + 0.3 * math.sin(t * 1.1 + 1), 0.0, 1.0)
    solid(C, cT.p(wave_poly(cT, -0.5, 0.8, 44, 0.05, t, 0.7), 1.0))
    draw_ark(C, cA, 0, 0.5 + 0.35 * math.sin(t * 1.3), detail=False, vex=2.0)
    solid(C, cA.p(wave_poly(cA, -0.2, 0.7, 40, 0.05, t, 2.0), 1.0))
    base = cA.pt(0, 0)[1] + 20; xa0, xa1 = cA.pt(-67, 0)[0], cA.pt(73, 0)[0]; xt0, xt1 = cT.pt(tx - 134, 0)[0], cT.pt(tx + 134, 0)[0]
    pa = clamp((p - 0.3) / 0.25); pt_ = clamp((p - 0.5) / 0.3)
    dim(C, (xa0, base), (xa1, base), 40, pa, "ARK 137 m", 50, layer="G", lab=((xa0 + xa1) / 2, base + 100))
    dim(C, (xt0, base), (xt1, base), 190, pt_, "TITANIC 269 m", 50, layer="W", lab=(clamp((xt0 + xt1) / 2 + 160, 330, 750), base + 270))
    C.text("ABOUT HALF", 540, 600, 100, "G", sstep((p - 0.75) / 0.18))
    C.rain = 0.7


def pc_flex(C, lt, dur):
    p = lt / dur; t = C.t; cam = Cam(9.4, lerp(-8, 8, p), vex=1.6)
    A = 5.6 * math.sin(t * 2.0 * math.pi * 0.33)
    off = lambda x: A * (1 - (np.asarray(x, np.float32) / 70.0) ** 2)
    draw_ark(C, cam, 0, 0.6, 0.0, off=off, vex=1.6)
    for k, sx_ in enumerate([-38, -14, 12, 40]):
        yb = 1.2 + 0.7 * (k % 2); y1 = yb + 2.8
        sp = cam.p([(sx_, yb + float(off(sx_))), (sx_ + 0.9, y1 + float(off(sx_)))], 1.6); line(C.det, sp[0], sp[1], 2, 255)
        spray(C, cam, sx_ + 0.3, yb + float(off(sx_)) + 0.7, 5.5 * (1 if k % 2 else -1), 6.5, t + k * 0.37, 16, 10 + k, a=0.85, g=22, life=0.9, size=3.4)
    solid(C, cam.p(wave_poly(cam, -0.2, 0.8, 30, 0.07, t, 0.7), 1.0)); solid(C, cam.p(wave_poly(cam, -3.4, 1.2, 38, 0.08, t, 2.6), 1.0))
    for k in range(3): spray(C, cam, cam.cx - 18 + k * 18, 0.8, 4, 8, t + k, 10, 40 + k, a=0.5, g=24, life=1.0, size=2.6)
    C.text("BENDS  AND  LEAKS", 540, 600, 62, "G", sstep((p - 0.35) / 0.25) * 0.95)
    C.rain = 1.0


def snoise(x, vals):
    n = len(vals) - 1; xi = np.floor(x).astype(np.int64) % n; f = x - np.floor(x); f = f * f * (3 - 2 * f)
    return vals[xi] * (1 - f) + vals[xi + 1] * f


def mountain_layer(cam_x, base, amp, seed, par, scale, step=8):
    rng = np.random.default_rng(seed); sx = np.arange(-12, W + 20, step, dtype=np.float32); x = (sx + cam_x * par) / scale
    v = [rng.random(97).astype(np.float32) for _ in range(3)]
    for a in v: a[-1] = a[0]
    r = lambda n: 1 - np.abs(2 * n - 1)
    prof = 0.62 * r(snoise(x / 9.0, v[0])) ** 1.3 + 0.28 * r(snoise(x / 3.3, v[1])) + 0.10 * snoise(x / 1.1, v[2])
    y = base - amp * prof
    return np.concatenate([np.stack([sx, y], 1), [(W + 30, H + 60), (-30, H + 60)]]).astype(np.float32)


def pc_mountains(C, lt, dur):
    p = lt / dur; t = C.t; px = 200 * p; zoom = 1 + 0.07 * p
    fill(C.midl(), mountain_layer(px, 1235 + 40 * p, 330 * zoom, 3, 0.35, 10))
    fill(C.midl(), mountain_layer(px, 1335 + 60 * p, 300 * zoom, 7, 0.65, 9))
    fill(C.sil, mountain_layer(px, 1490 + 90 * p, 300 * zoom, 11, 1.0, 8))
    ang = math.radians(lerp(-60, -24, sstep(p * 0.95)) + 4 * math.sin(t * 0.7)); org = np.array([60.0, 1900.0])
    dirv = np.array([math.sin(-ang), -math.cos(ang)])
    far = org + dirv * 2300; nrm = np.array([-dirv[1], dirv[0]])
    C.gpoly(np.array([org + nrm * 8, org - nrm * 8, far - nrm * 150, far + nrm * 150]), (60, 56, 48)); C.gpoly(np.array([org + nrm * 3, org - nrm * 3, far - nrm * 55, far + nrm * 55]), (80, 74, 60))
    C.gcirc(org + dirv * 1450, 100, (110, 100, 76))
    C.text("NOT PROVEN", 540, 560, 100, "G", sstep((p - 0.08) / 0.2))
    C.text("NO TRACE FOUND", 540, 665, 62, "W", sstep((p - 0.45) / 0.2))
    C.rain = 0.45


def pc_finale(C, lt, dur):
    p = lt / dur; t = C.t; cam = Cam(lerp(6.4, 8.2, p), lerp(-4, 8, p), vex=2.0)
    draw_ark(C, cam, vex=2.0); solid(C, cam.p(land_poly(cam, 1.6, 74), 1.0))
    pa = sstep((p - 0.42) / 0.14)
    for (cx_, txt, layer) in [(285, "POSSIBLE", "G"), (795, "IMPOSSIBLE", "W")]:
        C.pills.append(((cx_ - 218, 1620, cx_ + 218, 1730), layer, pa, 5)); C.text(txt, cx_, 1677, 52, layer, pa)
    C.rain = 0.85


PIECES = [pc_toy_and_ark, pc_dims, pc_forearm, pc_pullback, pc_field, pc_cutaway, pc_topdown, pc_cargo, pc_titanic, pc_flex, pc_schooner, pc_mountains, pc_finale]


# ====================================================================== plan (timing, captions, sound events)
STOPW = set("a an the of to in on is it's and at for by but so or now add not".split())


def _clean(w): return re.sub(r"[^a-z0-9'\-]", "", w.lower())


def build_plan(S, voice, BT, TOTAL):
    from .voice import word_times
    beats = S["beats"]; n = len(beats); out = []; bounds = [0.0]
    for i in range(n - 1): bounds.append((BT[i]["t1"] + BT[i + 1]["t0"]) / 2)
    bounds.append(TOTAL)
    caps = []
    for i, b in enumerate(beats):
        wt = word_times(b["text"], BT[i]["t0"], BT[i]["speech"], voice)
        kw = _clean(ALIAS.get(b["keyword"] or "", b["keyword"] or "")) if b.get("keyword") else ""
        groups, k = [], 0
        while k < len(wt):
            g = [wt[k]]
            if k + 1 < len(wt) and len(wt[k][0]) + len(wt[k + 1][0]) <= 17 and not (_clean(wt[k][0]).startswith(kw[:4]) and kw and len(wt[k][0]) > 6):
                g.append(wt[k + 1])
            groups.append(g); k += len(g)
        # keyword stays visible alone if it is long and followed by a short word
        for gi, g in enumerate(groups):
            t0 = g[0][1]; t1 = groups[gi + 1][0][1] if gi + 1 < len(groups) else (BT[i + 1]["t0"] if i + 1 < n else TOTAL)
            words = [re.sub(r"[.,:;!]+$", "", w[0]).upper() for w in g]
            isk = [bool(kw) and _clean(w[0]).startswith(kw[:max(3, len(kw) - 2)]) for w in g]
            caps.append(dict(t0=float(t0) if gi else float(max(0.0, t0 - 0.0)), t1=float(t1), words=words, kw=isk))
    caps[0]["t0"] = 0.0
    # sound events
    creaks = []
    for i in (0, 1, 3, 5, 9):
        creaks += [bounds[i] + 0.5 + (bounds[i + 1] - bounds[i]) * 0.35, bounds[i] + 0.5 + (bounds[i + 1] - bounds[i]) * 0.78]
    thunder = [6.5, 19.0, 33.5, 41.0]
    return dict(bounds=bounds, caps=caps, total=float(TOTAL), n=n, creaks=creaks, thunder=thunder, whoosh=bounds[1:-1], keywords=[b["keyword"] for b in beats])


# ====================================================================== renderer
class Renderer:
    def __init__(s, plan_path):
        cv2.setNumThreads(1)
        D = pickle.load(open(plan_path, "rb")); s.P = D
        s.mt = 99.0
        hh, hw = H // 2, W // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(np.float32); Y, X = yy * 2, xx * 2
        stops = [(0, (8, 18, 25)), (420, (20, 38, 46)), (800, (48, 60, 62)), (1020, (118, 82, 58)), (1130, (214, 112, 42)), (1220, (240, 138, 50)), (1310, (120, 56, 28)), (1500, (24, 17, 16)), (1920, (8, 7, 8))]
        ys = np.arange(hh, dtype=np.float32) * 2
        base = np.stack([np.interp(ys, [a for a, _ in stops], [c[k] for _, c in stops]) for k in range(3)], -1)[:, None, :].repeat(hw, 1).astype(np.float32)
        d = np.sqrt((X - SUN[0]) ** 2 + ((Y - SUN[1]) * 1.25) ** 2)
        s.gcore, s.ghalo, s.gwide = np.exp(-d / 70), np.exp(-d / 330), np.exp(-d / 850)
        sky = base + s.gcore[..., None] * np.array([120, 90, 40], np.float32) * 1.2 + s.ghalo[..., None] * np.array([120, 52, 14], np.float32) * 0.85 + s.gwide[..., None] * np.array([54, 28, 18], np.float32)
        disc = np.clip((50 - d) / 14, 0, 1)[..., None] * np.array([255, 226, 150], np.float32) * 0.9
        s.sky0 = np.clip(sky + disc, 0, 255).astype(np.float32)
        rng = np.random.default_rng(11)
        from .common import fbm
        s.CT = cv2.resize(fbm(420, 330, [60, 22, 9], [1, .55, .3], 4), (2600, 960), interpolation=cv2.INTER_CUBIC)
        s.ang = np.arctan2(Y - SUN[1], X - SUN[0]); s.rr = np.sqrt((X - SUN[0]) ** 2 + (Y - SUN[1]) ** 2)
        s.vm = (sstep_arr((Y - 60) / 340) * (1 - sstep_arr((Y - 1150) / 110)))[..., None].astype(np.float32)
        s.hy = Y
        yv, xv = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xv - 540) / 540) ** 2 + ((yv - 960) / 960) ** 2)
        s.vig = (1 - 0.55 * np.clip((r - 0.55) / 0.95, 0, 1) ** 1.5)[..., None].astype(np.float32)
        dd = np.sqrt((xv - SUN[0]) ** 2 + (yv - SUN[1]) ** 2)
        s.rimw = ((0.32 + 0.68 * np.exp(-dd / 900)) * (1 - 0.72 * np.clip((yv - 1480) / 220, 0, 1))).astype(np.float32)
        del yv, xv, dd, r
        s.rain_p = np.random.default_rng(3).random((260, 5)).astype(np.float32)
        s.gr = np.random.default_rng(9)
        s.nz = {k: np.random.default_rng(100 + k).random(65).astype(np.float32) for k in range(4)}
        s.fontcache = {}
        rr = np.random.default_rng(21); N = 120
        s.reed = np.stack([np.sort(rr.uniform(-30, W + 30, N)), rr.random(N), rr.random(N), rr.random(N)], 1)


    # ---- sky
    def sky(s, t):
        hh, hw = H // 2, W // 2
        ox = 300 + t * 7.0
        M = np.float32([[1, 0, -ox], [0, 1, 0]]); ct = cv2.warpAffine(s.CT, M, (hw, hh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        dn = np.clip((ct - 0.46) * 3.0, 0, 1)[..., None] * s.vm
        lit = np.clip(s.ghalo * 1.5, 0, 1)[..., None]
        dark = np.array([22, 32, 40], np.float32); warm = np.array([205, 98, 44], np.float32)
        ccol = dark * (1 - lit) + warm * lit * (0.35 + 0.65 * np.clip(1.15 - ct[..., None], 0, 1))
        sky = s.sky0 * (1 - 0.88 * dn) + ccol * 0.88 * dn
        rays = (0.5 + 0.5 * np.sin(s.ang * 15 + 0.6 * np.sin(s.ang * 5 + t * 0.07) + t * 0.05)) ** 3 * np.exp(-s.rr / 800) * (s.hy < SUN[1] + 30) * 0.17
        sky += (rays * (1 - 0.7 * dn[..., 0]))[..., None] * np.array([255, 160, 80], np.float32)
        return cv2.resize(sky, (W, H), interpolation=cv2.INTER_LINEAR)

    def ridge(s, k, off, base, amp, par, sc):
        sx = np.arange(-12, W + 20, 8, dtype=np.float32); x = sx + off * par
        a = np.interp((x / sc) % 64, np.arange(65), s.nz[k], period=64); b = np.interp((x / (sc * 0.27)) % 64, np.arange(65), s.nz[(k + 1) % 4], period=64)
        y = base - amp * (a ** 1.3 * 0.8 + b * 0.25)
        m = np.zeros((H, W), np.uint8); fill(m, np.concatenate([np.stack([sx, y], 1), [(W + 30, H + 60), (-30, H + 60)]])); return m

    def bg_ridges(s, bg, t):
        pan = t * 9
        for (k, base, amp, par, sc, hz, col) in [(0, 1242, 70, 0.10, 14, 0.40, (14, 12, 16)), (1, 1272, 50, 0.22, 9, 0.22, (9, 9, 12))]:
            m = s.ridge(k, pan, base, amp, par, sc).astype(np.float32)[..., None] / 255
            bg[:] = bg * (1 - m) + (np.array(col, np.float32) + bg * hz) * m

    def reeds(s, t):
        m = np.zeros((H, W), np.uint8)
        for (x0, a, b, c) in s.reed:
            edge = max(0.0, abs(x0 - 540) / 540 - 0.35) / 0.65
            h = 40 + 110 * a + 330 * edge ** 1.8 * (0.5 + b)
            lean = (c - 0.5) * 0.35 * h + math.sin(t * 1.2 + x0 * 0.05) * 0.05 * h
            w = 3 + 4 * b; tip = (x0 + lean, H - h)
            fill(m, [(x0 - w, H + 6), (x0 + w, H + 6), (x0 + lean * 0.45 + 1, H - h * 0.55), tip])
            if b > 0.7 and h > 150: cv2.ellipse(m, tuple(int(v) for v in _fx(np.array(tip) + np.array([0, 22]))), (int(7 * 16), int(26 * 16)), 0, 0, 360, 255, -1, cv2.LINE_AA, 4)
        m[H - 36:] = 255
        return m.astype(np.float32) / 255

    def weights(s, t):
        b = s.P["bounds"]; out = []
        for i in range(len(b) - 1):
            lo, hi = b[i] - (XF / 2 if i else 0), b[i + 1] + (XF / 2 if i < len(b) - 2 else 0)
            if lo - 1e-6 <= t <= hi + 1e-6:
                w = 1.0
                if i and t < b[i] + XF / 2: w = sstep((t - (b[i] - XF / 2)) / XF)
                if i < len(b) - 2 and t > b[i + 1] - XF / 2: w = min(w, 1 - sstep((t - (b[i + 1] - XF / 2)) / XF))
                if w > 0.003: out.append((i, w))
        return out or [(0, 1.0)]

    def frame_array(s, fi):
        t = fi / FPS; P = s.P
        bg = s.sky(t); s.bg_ridges(bg, t)
        ws = s.weights(t)
        sil = np.zeros((H, W), np.float32); det = np.zeros((H, W), np.float32); mid = None; glow = None; hole = None; gf = None; oW = np.zeros((H, W), np.float32); oG = np.zeros((H, W), np.float32); rain = 0.0
        for (i, w) in ws:
            C = Cv(t); lt = t - P["bounds"][i]; dur = P["bounds"][i + 1] - P["bounds"][i]
            PIECES[i](C, lt, dur); C.finish()
            sil += C.sil * (w / 255.0); det += C.det * (w / 255.0); oW += C.oW * (w / 255.0); oG += C.oG * (w / 255.0); rain += C.rain * w
            if C.mid is not None: mid = (mid if mid is not None else 0) + C.mid.astype(np.float32) * (w / 255.0)
            if C.hole is not None:
                hh_ = C.hole.astype(np.float32) * (w / 255.0); hole = hh_ if hole is None else hole + hh_
                g2 = cv2.resize(C.gf, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) * w; gf = g2 if gf is None else gf + g2
            if C.glow is not None:
                g = cv2.resize(C.glow, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) * w; glow = g if glow is None else glow + g
        if mid is not None:
            m = np.clip(mid, 0, 1)[..., None]; bg[:] = bg * (1 - m) + (np.array([26, 22, 26], np.float32) + bg * 0.18) * m
        if glow is not None: bg += glow * 0.9
        sil = np.maximum(np.clip(sil, 0, 1), s.reeds(t)); sa = sil[..., None]
        bg = bg * (1 - sa) + BLACK * sa
        if hole is not None:
            h_ = np.clip(hole, 0, 1)[..., None]; bg = bg * (1 - h_) + gf * 0.95
        bg += (np.clip(det, 0, 1) * sil * 0.55)[..., None] * DETC
        # rim light (edges facing the sun, thin) + weaker top edge
        rl = np.zeros_like(sil); rr_ = np.zeros_like(sil); rt = np.zeros_like(sil)
        rl[:, 3:] = sil[:, 3:] * (1 - sil[:, :-3]); rr_[:, :-3] = sil[:, :-3] * (1 - sil[:, 3:]); rt[3:] = sil[3:] * (1 - sil[:-3])
        sx = SUN[0]; rim = np.where(np.arange(W)[None, :] >= sx, rl, rr_) + 0.5 * rt
        bg += (rim * s.rimw * 0.95)[..., None] * RIMC
        # rain
        bg += s.rain_layer(t, rain)
        # overlays with soft shadow
        oW = np.clip(oW, 0, 1); oG = np.clip(oG, 0, 1)
        if oW.max() > 0 or oG.max() > 0:
            u = np.maximum(oW, oG); sh = cv2.resize(cv2.GaussianBlur(cv2.resize(u, (W // 2, H // 2)), (0, 0), 5), (W, H))
            bg *= (1 - 0.5 * np.clip(sh * 1.6, 0, 1))[..., None]
            bg = bg * (1 - oW[..., None]) + np.array(WARM_W, np.float32) * oW[..., None]
            bg = bg * (1 - oG[..., None]) + np.array(GOLD_C, np.float32) * oG[..., None]
        bg *= s.vig
        g = s.gr.standard_normal((H // 2, W // 2)).astype(np.float32) * 3.2
        bg += cv2.resize(g, (W, H), interpolation=cv2.INTER_NEAREST)[..., None]
        return np.clip(bg, 0, 255).astype(np.uint8)

    def rain_layer(s, t, inten):
        n = int(60 + 190 * clamp(inten)); m = np.zeros((H, W), np.uint8)
        for k in range(n):
            x0, y0, sp, ln_, a = s.rain_p[k]
            y = (y0 * (H + 300) + t * (1500 + 900 * sp)) % (H + 300) - 150; x = x0 * (W + 500) - 0.3 * (y + 150) + 100 - 0.2 * t * 0
            l = 26 + 40 * ln_ * (0.5 + sp)
            line(m, (x, y), (x - 0.3 * l, y + l), 1 if sp < 0.6 else 2, 70 + 120 * a * sp)
        return (m.astype(np.float32) * (0.2 / 255))[..., None] * np.array([230, 205, 180], np.float32)

    def captions(s, img, t):
        c = None
        for cc in s.P["caps"]:
            if cc["t0"] - 1e-3 <= t < cc["t1"]: c = cc; break
        if c is None: return img
        f0 = (t - c["t0"]) * FPS; k = 0.92 + 0.08 * ease(f0 / 4); size = 76
        words = c["words"]
        def width(sz): return sum(F(MONT_BLACK, sz).getlength(w) for w in words) + sz * 0.3 * (len(words) - 1)
        while width(size) > 940 and size > 56: size -= 4
        s.mt = min(s.mt, size); sz = int(size * k); f = F(MONT_BLACK, sz)
        tw = sum(f.getlength(w) for w in words) + sz * 0.3 * (len(words) - 1); x = 540 - tw / 2
        im = Image.fromarray(img); d = ImageDraw.Draw(im, "RGBA")
        for w, isk in zip(words, c["kw"]):
            col = KW_YELLOW if isk else (255, 255, 255)
            d.text((x + 3, 333 + 4), w, font=f, fill=(0, 0, 0, 120), anchor="lm", stroke_width=5, stroke_fill=(0, 0, 0, 120))
            d.text((x, 330), w, font=f, fill=col, anchor="lm", stroke_width=4, stroke_fill=(12, 12, 14))
            x += f.getlength(w) + sz * 0.3
        return np.asarray(im)

    def frame(s, fi):
        a = s.frame_array(fi); a = s.captions(a, fi / FPS)
        return Image.fromarray(a)


def sstep_arr(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


_R = None


def init_worker(plan_path):
    global _R
    cv2.setNumThreads(1); _R = Renderer(plan_path)


def _probe_frames(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(path)], capture_output=True, text=True, timeout=120)
        return int(r.stdout.strip().split()[0]) if r.returncode == 0 and r.stdout.strip() else -1
    except Exception: return -1


def chunk_ok(path, side, n, key):
    try:
        if not Path(path).exists() or not Path(side).exists(): return None
        m = json.load(open(side))
        if m.get("key") != key or m.get("frames") != n or len(m.get("means", [])) != n: return None
        return m if _probe_frames(path) == n else None
    except Exception: return None


def render_chunk(job):
    idx, f0, f1, outdir, key = job
    path = Path(outdir) / f"_part{idx:03d}.mp4"; side = Path(outdir) / f"_part{idx:03d}.json"; n = f1 - f0
    m = chunk_ok(path, side, n, key)
    if m is not None: return str(path), m["means"], m["mintext"], True
    tmp = Path(outdir) / f"_part{idx:03d}.tmp.mp4"
    for q in (tmp, path, side): q.unlink(missing_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)], stdin=subprocess.PIPE)
    means = []; _R.mt = 9999.0
    for fi in range(f0, f1):
        a = np.asarray(_R.frame(fi)); means.append(float(a[::8, ::8].mean())); ff.stdin.write(a.tobytes())
    ff.stdin.close()
    if ff.wait() != 0: raise RuntimeError(f"ffmpeg failed on chunk {idx}")
    if _probe_frames(tmp) != n: raise RuntimeError(f"chunk {idx}: frame count mismatch")
    stmp = Path(outdir) / f"_part{idx:03d}.json.tmp"
    json.dump(dict(key=key, frames=n, means=means, mintext=float(_R.mt)), open(stmp, "w")); os.replace(stmp, side); os.replace(tmp, path)
    return str(path), means, float(_R.mt), False


# ====================================================================== audio
def make_audio(voice, total, P):
    from exodus.sfx import SR, noise, bp, add, whoosh, thunder
    n = int(total * SR); t = np.arange(n) / SR
    v = np.zeros(n, np.float32); v[:min(n, len(voice))] = voice[:n]
    hop = SR // 50
    rms = np.sqrt(np.convolve(v ** 2, np.ones(hop) / hop, mode="same"))
    act = np.clip(rms / 0.03, 0, 1); act = np.convolve(act, np.ones(int(0.3 * SR)) / int(0.3 * SR), mode="same")
    vr = np.sqrt(np.mean(v[rms > 0.02] ** 2))
    # somber pad: Am - F - Dm - E, 8 s each, slow attack/release, with a very slow sub pulse
    chords = [(110.0, 130.81, 164.81), (87.31, 130.81, 174.61), (73.42, 110.0, 146.83), (82.41, 123.47, 164.81)]
    seg = 8.0; pad = np.zeros(n, np.float32)
    for ci in range(int(total / seg) + 1):
        f = chords[ci % 4]; s0 = ci * seg
        idx = (t >= s0 - 2.5) & (t < s0 + seg + 3.0)
        if not idx.any(): continue
        tt = t[idx] - s0; env = np.clip((tt + 2.5) / 3.5, 0, 1) * np.clip((seg + 3.0 - tt) / 3.5, 0, 1)
        sig = np.zeros_like(tt)
        for fr in f:
            for det in (-0.5, 0.5):
                sig += np.sin(2 * np.pi * (fr + det) * tt) * .5 + np.sin(2 * np.pi * (fr * 2 + det * 1.4) * tt) * .08
        sig += np.sin(2 * np.pi * f[0] / 2 * tt) * .9
        pad[idx] += (sig * env * (0.88 + 0.12 * np.sin(2 * np.pi * 0.18 * t[idx] + ci))).astype(np.float32)
    pad /= np.max(np.abs(pad)) + 1e-6
    pulse = np.zeros(n, np.float32); beat = 60 / 54
    kn = int(0.6 * SR); kx = np.arange(kn) / SR; kick = (np.sin(2 * np.pi * np.cumsum(58 - 20 * np.minimum(kx / 0.4, 1)) / SR) * np.exp(-kx * 6.0)).astype(np.float32)
    for i in range(int(total / beat) + 1): add(pulse, 0.3 + i * beat, kick, 1.0 if i % 2 == 0 else 0.55)
    fade = np.clip(t / 1.5, 0, 1) * np.clip((total - t) / 2.2, 0, 1)
    pad *= fade; pulse *= fade
    pad = pad / (np.sqrt(np.mean(pad ** 2)) + 1e-9) * vr * 0.085; pulse = pulse / (np.sqrt(np.mean(pulse ** 2)) + 1e-9) * vr * 0.075
    music = (pad + pulse) * (1 - 0.55 * act)
    # rain: continuous, swells in the storm beats
    b = P["bounds"]; swell = np.interp(t, [0, b[9] - 1, b[9] + 1, b[11] - 1, b[11] + 1, total], [0.6, 0.6, 1.0, 1.0, 0.55, 0.7]) if "rain_pts" not in P else np.interp(t, *P["rain_pts"])
    r1 = bp(noise(n), 2200, 9500); r1 /= np.max(np.abs(r1)) + 1e-6
    r2 = bp(noise(n), 300, 1400); r2 /= np.max(np.abs(r2)) + 1e-6
    rain = (r1 * 0.5 + r2 * 0.16) * swell * fade
    rain = rain / (np.sqrt(np.mean(rain ** 2)) + 1e-9) * vr * 0.06
    # distant thunder rumble: soft, no crack
    s = np.zeros(n, np.float32)
    for tt_ in P["thunder"]:
        d = int(4.2 * SR); x = np.arange(d) / SR; z = bp(noise(d), 24, 110); z /= np.max(np.abs(z)) + 1e-6
        env = np.clip(x / 0.9, 0, 1) ** 1.5 * np.exp(-x * 0.85) * (0.7 + 0.3 * np.sin(2 * np.pi * x * 3.1 + 1)); add(s, tt_, (z * env).astype(np.float32), vr * 0.5)
    # wood creaks: stick-slip pulses on a gliding resonant tone
    for tt_ in P["creaks"]:
        d = int(0.9 * SR); x = np.arange(d) / SR; f = 95 + 70 * (x / 0.9) + 25 * np.sin(2 * np.pi * 9 * x)
        ph = 2 * np.pi * np.cumsum(f) / SR; tone = np.sin(ph) + 0.5 * np.sin(2 * ph * 1.01) + 0.35 * np.sin(3 * ph)
        slip = (np.sin(2 * np.pi * 31 * x) > 0.2).astype(np.float32) * 0.6 + 0.4; slip = np.convolve(slip, np.ones(60) / 60, mode="same")
        c = bp((tone * slip * np.sin(np.pi * x / 0.9) ** 1.4 + 0.25 * noise(d) * slip * np.sin(np.pi * x / 0.9)).astype(np.float32), 120, 1100)
        add(s, tt_, c / (np.max(np.abs(c)) + 1e-6), vr * 0.13)
    wh = whoosh(0.55) * np.linspace(1, 0.6, int(0.55 * SR))
    for tt_ in P["whoosh"]: add(s, tt_ - 0.28, wh, vr * 0.09)
    out = v + music + rain * (1 - 0.35 * act) + s * (1 - 0.4 * act)
    out = out / np.max(np.abs(out)) * 0.891
    return out.astype(np.float32)


# ====================================================================== driver
def run(topic, args):
    from . import script as SC, voice as VO, encode
    import soundfile as sf
    opt = lambda k: args[args.index(k) + 1] if k in args else None
    topic = Path(topic); out = topic / "out"; cache = topic / "cache"; out.mkdir(exist_ok=True); cache.mkdir(exist_ok=True); name = topic.name
    T = {}; t00 = time.time()
    def stage(nm, t0): T[nm] = round(time.time() - t0, 1); print(f"[{nm}] {T[nm]}s", flush=True)
    t0 = time.time(); S = SC.load(topic); beats = S["beats"]; stage("script", t0)
    if "--fake" in args:                                                  # dev only: fixed 3.3 s per beat, silence
        BT = [dict(t0=0.12 + i * 3.3, speech=3.0, t1=0.12 + (i + 1) * 3.3) for i in range(len(beats))]; TOTAL = BT[-1]["t1"] + 1.6; voice = np.zeros(int(TOTAL * VO.SR), np.float32)
    else:
        t0 = time.time(); VO.generate(topic, beats, S); stage("voice_tts", t0)
        t0 = time.time(); voice, BT, TOTAL = VO.narrate(topic, beats, cache); stage("narration", t0)
    P = build_plan(S, voice, BT, TOTAL); nframes = int(math.ceil(TOTAL * FPS))
    pkl = cache / "plan_sil.pkl"; tmpk = cache / "plan_sil.pkl.tmp"; pickle.dump(P, open(tmpk, "wb")); os.replace(tmpk, pkl)
    if opt("--frames"):
        r = Renderer(str(pkl)); fd = out / "frames"; fd.mkdir(exist_ok=True)
        for sec in [float(x) for x in opt("--frames").split(",")]:
            p = fd / f"f_{sec:06.2f}.png"; r.frame(int(round(sec * FPS))).save(p); print(p)
        return
    t0 = time.time(); audio = make_audio(voice, TOTAL, P); wav = cache / "audio.wav"; sf.write(wav, audio, VO.SR); stage("audio", t0)
    t0 = time.time(); step = 75
    key = hashlib.sha1(open(pkl, "rb").read() + Path(__file__).read_bytes() + f"{nframes}|{FPS}".encode()).hexdigest()[:16]
    for q in cache.glob("_part*.tmp.mp4"): q.unlink(missing_ok=True)
    jobs = [(i, f0, min(nframes, f0 + step), str(cache), key) for i, f0 in enumerate(range(0, nframes, step))]
    parts, means, mints, reused = [], [], [], 0
    with mp.get_context("spawn").Pool(4, initializer=init_worker, initargs=(str(pkl),)) as pool:
        for k, (path, mn, mt, skipped) in enumerate(pool.imap(render_chunk, jobs, chunksize=1)):
            parts.append(path); means += mn; mints.append(mt); reused += bool(skipped)
            print(f"  chunk {k + 1}/{len(jobs)}  {time.time() - t0:.0f}s{'  (reused)' if skipped else ''}", flush=True)
    stage("frames", t0)
    t0 = time.time(); final = out / f"{name}.mp4"; tmpf = out / f"{name}.tmp.mp4"; encode.mux(parts, wav, tmpf, cache); os.replace(tmpf, final); stage("mux", t0)
    m = np.array(means); jumps = np.abs(np.diff(m)); jmax = float(jumps.max()) if len(jumps) else 0.0; jt = float((int(jumps.argmax()) + 1) / FPS) if len(jumps) else 0.0
    dur_s = nframes / FPS; warns = list(S["warnings"]); min_text = float(min(mints)) if mints else 0.0
    if not (40 <= dur_s <= 50): warns.append(f"DURATION {dur_s:.1f}s outside 40-50s")
    if jmax > 15: warns.append(f"FLICKER max frame-to-frame brightness jump {jmax:.1f} at {jt:.2f}s > 15")
    small = out / f"{name}_9mb.mp4"; size9 = None
    if "--no-9mb" not in args:
        t0 = time.time(); size9, vb = encode.encode_9mb(final, small, TOTAL, cache); stage("encode_9mb", t0)
        if size9 >= 10_000_000: warns.append("9mb file still >= 10 MB")
    t0 = time.time(); encode.contact_sheet(final, out / f"{name}_sheet.png", TOTAL); stage("sheet", t0)
    T["total"] = round(time.time() - t00, 1)
    rep = dict(topic=name, title=S["title"], style="silhouette", duration_s=round(dur_s, 2), narration_s=round(TOTAL, 2), shot_count=P["n"], avg_shot_s=round(TOTAL / P["n"], 2),
               min_caption_px=round(min_text, 1), chunks=len(jobs), chunks_reused=reused, max_brightness_jump=round(jmax, 2), max_jump_at_s=round(jt, 2),
               words=sum(len(b["text"].split()) for b in beats), mp4_bytes=final.stat().st_size, mp4_9mb_bytes=size9, warnings=warns, stage_seconds=T)
    json.dump(rep, open(out / "report.json", "w"), indent=2); print(json.dumps(rep, indent=2))
