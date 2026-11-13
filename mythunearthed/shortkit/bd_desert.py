"""Desert-sunset backdrop for PRESENTER shots (from the Exodus Short)."""
import math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw
from .common import W, H, vgrad, radial, ridge, to_img


@lru_cache(None)
def _sky(variant):
    tint = [(0, 0, 0), (-8, 10, 12), (10, -6, -14)][variant]
    stops = [(0, (38, 22, 58)), (520, (112, 52, 78)), (900, (206, 98, 72)), (1130, (246, 168, 90)), (1300, (252, 208, 128)), (H, (200, 120, 80))]
    arr = vgrad([(y, tuple(np.clip(np.array(c) + tint, 0, 255))) for y, c in stops])
    sx, sy = [(760, 1120), (330, 1100), (800, 1060)][variant]
    arr += radial(sx, sy, 640, 2.2)[..., None] * np.array([120, 70, 20], np.float32)
    arr += radial(sx, sy, 210, 1.2)[..., None] * np.array([120, 110, 70], np.float32)
    return arr, sx, sy


@lru_cache(None)
def _particles(n=130):
    r = np.random.default_rng(5)
    return r.uniform(0, W, n), r.uniform(300, 1500, n), r.uniform(1.5, 5.5, n), r.uniform(10, 60, n), r.uniform(0, 6.28, n)


def backdrop(t, variant=0):
    sky, sx, sy = _sky(variant)
    img = to_img(sky); d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([sx - 92, sy - 92, sx + 92, sy + 92], fill=(255, 238, 190, 255))
    d.ellipse([sx - 70, sy - 70, sx + 70, sy + 70], fill=(255, 248, 224, 255))
    xs = np.arange(0, W + 8, 8, dtype=np.float32)
    layers = [((148, 78, 84), 1196, [(26, 760, 0.3), (14, 380, 1.7), (7, 190, 4.1)], 7),
              ((112, 58, 70), 1280, [(34, 900, 2.1), (16, 430, 0.4), (8, 210, 3.3)], 15),
              ((78, 42, 56), 1360, [(40, 1080, 4.0), (20, 520, 1.1), (9, 260, 5.0)], 28)]
    for col, base, comps, spd in layers:
        ys = ridge(xs, t, comps, base, spd)
        d.polygon([(float(x), float(y)) for x, y in zip(xs, ys)] + [(W + 8, H), (0, H)], fill=col)
        d.line(list(zip(xs.tolist(), (ys + 1).tolist())), fill=(250, 170, 110, 90), width=3)
    px, py, ps, pv, pp = _particles()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for x, y, s, v, ph in zip(px, py, ps, pv, pp):
        xx = (x + t * v * 1.6) % (W + 40) - 20; yy = y + math.sin(t * 0.8 + ph) * 18
        a = int(70 + 60 * math.sin(t * 1.3 + ph))
        od.ellipse([xx - s, yy - s, xx + s, yy + s], fill=(255, 214, 160, max(20, a)))
    img = Image.alpha_composite(img.convert("RGBA"), ov)
    front = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fd = ImageDraw.Draw(front)
    ys = ridge(xs, t, [(20, 840, 1.0), (11, 410, 2.6), (6, 190, 0.7)], 1452, 36)
    fd.polygon([(float(x), float(y)) for x, y in zip(xs, ys)] + [(W + 8, H), (0, H)], fill=(40, 24, 34, 255))
    fd.line(list(zip(xs.tolist(), ys.tolist())), fill=(214, 120, 84, 255), width=4)
    grad = np.clip((np.arange(H) - 1440) / 480, 0, 1)[:, None] ** 1.3
    a = np.asarray(front, np.float32); a[..., :3] *= (1 - 0.45 * grad[..., None])
    return img.convert("RGB"), Image.fromarray(a.astype(np.uint8), "RGBA")
