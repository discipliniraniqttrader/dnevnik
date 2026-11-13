"""Misty mountain dusk backdrop for PRESENTER shots (snowy volcanic cone like Ararat, layered ridges, drifting clouds)."""
import math
from functools import lru_cache
import numpy as np, cv2
from PIL import Image, ImageDraw

from .common import W, H


def _fbm(h, w, scales, weights, seed, wrap_x=False):
    rng = np.random.default_rng(seed); acc = np.zeros((h, w), np.float32)
    for s, wt in zip(scales, weights):
        gh, gw = max(h // s, 2) + 3, max(w // s, 2) + 3
        small = rng.random((gh, gw)).astype(np.float32)
        if wrap_x:
            gw = max(w // s, 2); small = rng.random((gh, gw)).astype(np.float32); small = np.concatenate([small, small[:, :3]], 1)
            big = cv2.resize(small, (int((gw + 3) * (w / gw)) + 1, h), interpolation=cv2.INTER_CUBIC)[:, :w]
        else:
            big = cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)
        acc += big * wt
    acc /= sum(weights)
    lo, hi = np.percentile(acc, [3, 97]); return np.clip((acc - lo) / (hi - lo), 0, 1)


def _vgrad(stops, h=H, w=W):
    ys = np.arange(h, dtype=np.float32)
    pos = np.array([s[0] for s in stops], np.float32); cols = np.array([s[1] for s in stops], np.float32)
    return np.stack([np.interp(ys, pos, cols[:, k]) for k in range(3)], -1)[:, None, :].repeat(w, 1)


def _radial(cx, cy, r, power=2.0):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    return np.clip(1 - np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r, 0, 1) ** power


@lru_cache(None)
def _static(variant):
    """sky + sun glow + cone, as float image; also cone mask."""
    tint = [(0, 0, 0), (10, -4, -12), (-6, 6, 10)][variant]
    stops = [(0, (20, 24, 56)), (380, (48, 46, 92)), (760, (112, 74, 128)), (1000, (214, 124, 130)), (1180, (250, 178, 140)), (1330, (252, 214, 160)), (H, (120, 90, 110))]
    sky = _vgrad([(y, tuple(np.clip(np.array(c) + tint, 0, 255))) for y, c in stops])
    sx, sy = [(250, 1210), (860, 1190), (540, 1220)][variant]
    sky += _radial(sx, sy, 760, 2.2)[..., None] * np.array([120, 66, 24], np.float32)
    sky += _radial(sx, sy, 230, 1.4)[..., None] * np.array([110, 96, 60], np.float32)
    # stars
    rng = np.random.default_rng(4)
    for _ in range(90):
        x, y = rng.integers(0, W), int(rng.random() ** 1.7 * 640)
        a = rng.uniform(.25, .9) * (1 - y / 700)
        cv2.circle(sky, (int(x), int(y)), int(rng.choice([1, 1, 2])), (255 * a + sky[y, x, 0] * (1 - a), 250 * a + sky[y, x, 1] * (1 - a), 240 * a + sky[y, x, 2] * (1 - a)), -1)
    # ---- the cone (Ararat-like: broad volcano + a smaller twin)
    cx = [650, 400, 520][variant]; peak = 700; base = 1320
    xs = np.arange(W, dtype=np.float32)
    def cone(cx, peak, half, pw):
        u = np.clip(np.abs(xs - cx) / half, 0, 1)
        prof = peak + (base - peak) * (u ** pw)
        prof = np.where(np.abs(xs - cx) > half, base + 30, prof)
        return prof
    n1 = (_fbm(1, W, [40, 12, 4], [1, .5, .3], 3)[0] - .5)
    big = cone(cx, peak, 640, 0.72) + n1 * 14
    off = -440 if cx > 500 else 440
    small = cone(cx + off, peak + 150, 300, 0.80) + n1[::-1] * 10
    prof = np.minimum(big, small)
    body = np.zeros((H, W), np.uint8)
    pts = [(int(x), int(y)) for x, y in zip(xs, prof)] + [(W, H), (0, H)]
    cv2.fillPoly(body, [np.array(pts, np.int32)], 255)
    m = body.astype(np.float32) / 255
    # colour: cool violet body, warm lit flank toward the sun, snow cap
    yy = np.arange(H, dtype=np.float32)[:, None]
    depth = np.clip((yy - 700) / 640, 0, 1)
    col = np.zeros((H, W, 3), np.float32)
    col[:] = np.array([66, 62, 112], np.float32) * (1 - depth[..., None] * .35) + np.array([118, 88, 132], np.float32) * depth[..., None] * .5
    side = np.clip(((sx - xs[None, :]) / W) * 1.3 + .45, 0, 1)[..., None] if True else 0
    lit = (np.clip(1 - np.abs(xs[None, :] - sx) / 900, 0, 1) ** 1.5)[..., None]
    col += lit * np.array([84, 40, 26], np.float32) * (0.5 + 0.5 * depth[..., None])
    tex = _fbm(H, W, [160, 48, 14, 5], [1, .8, .6, .5], 8)
    col *= (.82 + .36 * tex)[..., None]
    # snow: above a jagged line
    snowline = 700 + 250 + (_fbm(1, W, [60, 20, 7], [1, .7, .5], 9)[0] - .5) * 120
    snowline = np.where(np.abs(xs - cx) < 640, snowline + np.abs(xs - cx) * 0.06, 9999)
    snow = np.clip((snowline[None, :] - yy) / 18, 0, 1) * (0.55 + 0.45 * tex)
    snow_col = np.array([226, 224, 246], np.float32) * (0.78 + 0.22 * np.clip(1 - np.abs(xs[None, :] - cx + 30) / 380, 0, 1)[..., None])
    snow_col = snow_col + lit * np.array([36, 14, 0], np.float32)
    col = col * (1 - snow[..., None] * m[..., None]) + snow_col * (snow[..., None] * m[..., None])
    # rim light on the right slope crest toward the sun side
    rim = cv2.GaussianBlur(m, (0, 0), 2) - cv2.GaussianBlur(m, (0, 0), 9)
    col += np.clip(rim, 0, 1)[..., None] * np.array([150, 90, 70], np.float32) * 1.2
    # haze at the base of the cone
    hz = np.clip((yy - 1050) / 300, 0, 1) ** 1.2
    col = col * (1 - hz[..., None] * .55) + np.array([238, 168, 150], np.float32) * hz[..., None] * .55
    out = sky * (1 - m[..., None]) + col * m[..., None]
    return np.clip(out, 0, 255).astype(np.uint8), body


@lru_cache(None)
def _clouds():
    """two seamless horizontally-wrapping RGBA cloud strips"""
    strips = []
    for k, (h, scl, seed) in enumerate([(360, [180, 80, 30], 21), (300, [220, 90, 40], 22), (240, [140, 60, 24], 23)]):
        wv = _fbm(h, W * 2, scl, [1, .6, .3], seed, wrap_x=True)
        a = np.clip((wv - .5) * 2.6, 0, 1) ** 1.3
        vy = np.clip(1 - np.abs(np.linspace(-1, 1, h)), 0, 1)[:, None] ** .8
        a *= vy
        strips.append(a.astype(np.float32))
    return strips


def _ridge(x, t, comps, base, speed):
    y = np.full_like(x, base, dtype=np.float32)
    for amp, per, ph in comps:
        y += amp * np.sin(2 * np.pi * (x + t * speed) / per + ph)
    return y


@lru_cache(None)
def _pines():
    r = np.random.default_rng(14)
    return [(r.uniform(-20, W + 20), r.uniform(46, 120)) for _ in range(34)]


def backdrop(t, variant=0):
    img, body = _static(variant)
    f = img.astype(np.float32)
    # drifting cloud bands (behind/around the cone) -- warm-lit, soft
    cl = _clouds()
    for k, (y0, spd, col, amp) in enumerate([(330, 9, (150, 120, 170), .55), (560, 14, (214, 150, 160), .5), (890, 20, (240, 188, 176), .42)]):
        a = cl[k]; h = a.shape[0]
        sh = int((t * spd) % (W * 2))
        a2 = np.roll(a, -sh, axis=1)[:, :W]
        y1 = min(H, y0 + h)
        reg = f[y0:y1]
        al = (a2[: y1 - y0] * amp)[..., None]
        reg[:] = reg * (1 - al) + np.array(col, np.float32) * al
    # ridge layers with fog between
    xs = np.arange(0, W + 8, 8, dtype=np.float32)
    ov = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(ov, "RGBA")
    layers = [((116, 84, 128), 1236, [(26, 760, 0.3), (14, 380, 1.7), (7, 190, 4.1)], 5),
              ((82, 62, 106), 1308, [(34, 900, 2.1), (16, 430, 0.4), (8, 210, 3.3)], 10),
              ((52, 42, 78), 1380, [(40, 1080, 4.0), (20, 520, 1.1), (9, 260, 5.0)], 18)]
    fog = _clouds()[2]
    for li, (col, base, comps, spd) in enumerate(layers):
        ys = _ridge(xs, t, comps, base, spd)
        d.polygon([(float(x), float(y)) for x, y in zip(xs, ys)] + [(W + 8, H), (0, H)], fill=col + (255,))
        d.line(list(zip(xs.tolist(), (ys + 1).tolist())), fill=(250, 170, 130, 38), width=3)
        # mist band hugging the ridge crest
        if li < 2:
            hh = fog.shape[0]
            sh = int((t * (12 + li * 8) + li * 300) % (W * 2))
            a = np.roll(fog, -sh, axis=1)[:, :W]
            ya = int(base - 90)
            band = np.zeros((hh, W, 4), np.uint8)
            band[..., 0], band[..., 1], band[..., 2] = 236, 190, 190
            band[..., 3] = (a * 120).astype(np.uint8)
            ov.alpha_composite(Image.fromarray(band, "RGBA"), (0, ya))
            d = ImageDraw.Draw(ov, "RGBA")
    back = ov.convert("RGB")
    # foreground (in front of Ezra): dark ridge with pines + low mist
    front = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fd = ImageDraw.Draw(front)
    ys = _ridge(xs, t, [(20, 840, 1.0), (11, 410, 2.6), (6, 190, 0.7)], 1470, 26)
    fd.polygon([(float(x), float(y)) for x, y in zip(xs, ys)] + [(W + 8, H), (0, H)], fill=(26, 22, 44, 255))
    for px, ph in _pines():
        px2 = (px + t * 26 * 0) % W
        yb = float(np.interp(px2, xs, ys)) + 8
        w2 = ph * .36
        for lv in range(4):
            yy = yb - ph * (lv * .26); ww = w2 * (1 - lv * .2)
            fd.polygon([(px2 - ww, yy), (px2 + ww, yy), (px2, yy - ph * .42)], fill=(22, 20, 40, 255))
    fd.line(list(zip(xs.tolist(), ys.tolist())), fill=(216, 130, 120, 255), width=3)
    return back, front
