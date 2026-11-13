"""PRESENTER backdrops: city (walls/towers), night (stars/torch), sea (waves + horizon). Each returns (back RGB PIL, front RGBA PIL)."""
import math
from functools import lru_cache
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
from .common import W, H, vgrad, radial, ridge, to_img, fbm


def _strip_shift(strip_rgba, shift):
    """strip is 2W wide RGBA; return the W-wide window at `shift` px (wraps)"""
    s = int(shift) % W
    return strip_rgba.crop((s, 0, s + W, strip_rgba.height))


# =============================================================== CITY
@lru_cache(None)
def _city_sky(v):
    tops = [(26, 24, 66), (22, 34, 70), (44, 24, 62)][v]
    stops = [(0, tops), (520, tuple(int(c * 1.5 + 18) for c in tops)), (900, (150, 84, 110)), (1120, (240, 150, 104)), (1260, (252, 204, 140)), (H, (140, 96, 100))]
    sky = vgrad(stops)
    sx, sy = [(780, 1190), (300, 1200), (540, 1170)][v]
    sky += radial(sx, sy, 700, 2.2)[..., None] * np.array([110, 62, 22], np.float32)
    sky += radial(sx, sy, 200, 1.3)[..., None] * np.array([100, 90, 56], np.float32)
    rng = np.random.default_rng(6 + v)
    for _ in range(70):
        x, y = int(rng.integers(0, W)), int(rng.random() ** 1.6 * 700); a = rng.uniform(.2, .8) * (1 - y / 760)
        sky[y, x] = sky[y, x] * (1 - a) + 250 * a
    return sky


@lru_cache(None)
def _skyline(layer, v):
    """2W-wide RGBA strip, periodic in W. layer 0 = far towers/domes, 1 = wall + towers"""
    S = 2
    img = Image.new("RGBA", (2 * W * S, 700 * S), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    rng = np.random.default_rng(100 * layer + v + 3)
    base_y = 680 * S
    col = [(88, 62, 100, 255), (58, 40, 66, 255)][layer]
    lit = [(255, 214, 130), (255, 190, 100)][layer]
    items = []
    if layer == 0:
        x = 0
        while x < W:
            kind = rng.choice(["block", "tower", "dome", "mina", "block"])
            w = int(rng.integers(60, 150)); h = int(rng.integers(90, 300))
            items.append((kind, x, w, h)); x += w + int(rng.integers(-10, 30))
        for rep in range(2):
            for kind, x, w, h in items:
                X = (x + rep * W) * S; w_, h_ = w * S, h * S
                if kind == "block": d.rectangle([X, base_y - h_, X + w_, base_y], fill=col)
                elif kind == "tower":
                    d.rectangle([X, base_y - h_, X + w_ * .6, base_y], fill=col)
                    d.polygon([(X - 6 * S, base_y - h_), (X + w_ * .3, base_y - h_ - w_ * .6), (X + w_ * .6 + 6 * S, base_y - h_)], fill=col)
                elif kind == "dome":
                    d.rectangle([X, base_y - h_ * .6, X + w_, base_y], fill=col)
                    d.pieslice([X + 4 * S, base_y - h_ * .6 - w_ * .5, X + w_ - 4 * S, base_y - h_ * .6 + w_ * .5], 180, 360, fill=col)
                    d.line([(X + w_ / 2, base_y - h_ * .6 - w_ * .5), (X + w_ / 2, base_y - h_ * .6 - w_ * .5 - 22 * S)], fill=col, width=3 * S)
                else:
                    d.rectangle([X + w_ * .3, base_y - h_ * 1.3, X + w_ * .6, base_y], fill=col)
                    d.polygon([(X + w_ * .28, base_y - h_ * 1.3), (X + w_ * .45, base_y - h_ * 1.3 - 70 * S), (X + w_ * .62, base_y - h_ * 1.3)], fill=col)
    else:
        wall_top = base_y - 150 * S
        d.rectangle([0, wall_top, 2 * W * S, base_y], fill=col)
        for X in range(0, 2 * W * S, 26 * S):                  # crenellations
            d.rectangle([X, wall_top - 18 * S, X + 14 * S, wall_top], fill=col)
        tx = [140, 470, 790]
        for rep in range(2):
            for k, x in enumerate(tx):
                X = (x + rep * W) * S; hh = (260 + 40 * (k % 2)) * S; ww = 110 * S
                d.rectangle([X - ww / 2, base_y - hh, X + ww / 2, base_y], fill=col)
                d.rectangle([X - ww / 2 - 8 * S, base_y - hh - 16 * S, X + ww / 2 + 8 * S, base_y - hh], fill=col)
                for q in range(4): d.rectangle([X - ww / 2 - 8 * S + q * (ww + 16 * S) / 3.4, base_y - hh - 40 * S, X - ww / 2 - 8 * S + q * (ww + 16 * S) / 3.4 + 22 * S, base_y - hh - 16 * S], fill=col)
                d.polygon([(X - ww * .3, base_y - hh - 40 * S), (X, base_y - hh - 130 * S), (X + ww * .3, base_y - hh - 40 * S)], fill=col)
                d.rectangle([X - 8 * S, base_y - hh * .62, X + 8 * S, base_y - hh * .62 + 34 * S], fill=(255, 196, 96, 255))     # lit slit
            gx = (310 + rep * W) * S                          # arched gate
            d.rectangle([gx - 70 * S, base_y - 130 * S, gx + 70 * S, base_y], fill=(26, 18, 30, 255))
            d.pieslice([gx - 70 * S, base_y - 200 * S, gx + 70 * S, base_y - 60 * S], 180, 360, fill=(26, 18, 30, 255))
    # lit windows
    wins = []
    for _ in range(46 if layer == 0 else 16):
        x = int(rng.integers(0, W)); y = int(rng.integers(base_y // S - (280 if layer == 0 else 130), base_y // S - 14))
        wins.append((x, y, rng.uniform(0, 6.28)))
    return img.resize((2 * W, 700), Image.LANCZOS), wins, lit


def city(t, v=0):
    sky = _city_sky(v % 3)
    img = to_img(sky).convert("RGBA")
    for layer, (y0, spd, haze) in enumerate([(560, 5, .35), (700, 11, .0)]):
        strip, wins, lit = _skyline(layer, v % 3)
        win = _strip_shift(strip, t * spd)
        if haze:
            a = np.asarray(win, np.float32); a[..., :3] = a[..., :3] * (1 - haze) + np.array([196, 120, 118], np.float32) * haze
            win = Image.fromarray(a.astype(np.uint8), "RGBA")
        img.alpha_composite(win, (0, y0 + (580 if layer == 0 else 520) - 580 + (0 if layer == 0 else 0)))
        d = ImageDraw.Draw(img, "RGBA")
        sh = int(t * spd) % W
        for x, y, ph in wins:
            fl = .55 + .45 * math.sin(t * 2.2 + ph)
            xx = (x - sh) % W
            d.rectangle([xx, y0 + y, xx + 5, y0 + y + 8], fill=lit + (int(190 * fl),))
    # warm ground haze + torch glow dots along the wall
    arr = np.asarray(img.convert("RGB"), np.float32)
    hz = np.clip((np.arange(H) - 1180) / 260, 0, 1)[:, None, None] ** 1.2
    arr = arr * (1 - hz * .35) + np.array([160, 100, 96], np.float32) * hz * .35
    gm = np.clip((np.arange(H) - 1380) / 6, 0, 1)[:, None, None]
    arr = arr * (1 - gm) + np.array([46, 32, 54], np.float32) * gm
    back = to_img(arr)
    front = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fd = ImageDraw.Draw(front)
    ys = ridge(np.arange(0, W + 8, 8, dtype=np.float32), t, [(6, 700, 1.0), (3, 260, 2.0)], 1478, 0)
    fd.polygon([(float(x), float(y)) for x, y in zip(np.arange(0, W + 8, 8), ys)] + [(W + 8, H), (0, H)], fill=(32, 22, 34, 255))
    for X in range(-10, W + 30, 54):
        fd.rectangle([X, 1448, X + 34, 1486], fill=(32, 22, 34, 255))
    fd.line([(0, 1488), (W, 1488)], fill=(200, 120, 90, 255), width=3)
    # torch on the parapet (flicker small)
    fl = .85 + .15 * math.sin(t * 9) * math.sin(t * 5.3 + 1)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    for tx in (70, W - 70):
        gd.ellipse([tx - 120, 1330 - 120, tx + 120, 1330 + 120], fill=(255, 150, 60, int(46 * fl)))
        fd.rectangle([tx - 5, 1370, tx + 5, 1450], fill=(70, 44, 30, 255))
        fd.polygon([(tx - 13, 1372), (tx, 1318 - 8 * fl), (tx + 13, 1372)], fill=(255, 176, 70, 255))
        fd.polygon([(tx - 7, 1372), (tx, 1342 - 4 * fl), (tx + 7, 1372)], fill=(255, 236, 160, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(22))
    back = Image.alpha_composite(back.convert("RGBA"), glow).convert("RGB")
    return back, front


# =============================================================== NIGHT
@lru_cache(None)
def _night_static(v):
    stops = [(0, (4, 6, 22)), (500, (10, 16, 48)), (1000, (24, 36, 84)), (1300, (46, 56, 106)), (H, (14, 18, 40))]
    sky = vgrad(stops)
    mx, my = [(800, 380), (260, 440), (560, 330)][v]
    sky += radial(mx, my, 640, 2.0)[..., None] * np.array([26, 36, 60], np.float32)
    nb = fbm(H, W, [300, 110, 40], [1, .6, .3], 40 + v)
    sky += ((nb - .5) * 16)[..., None] * np.array([1, 1.2, 1.6], np.float32) * np.clip(1 - np.arange(H) / 1300, 0, 1)[:, None, None]
    img = to_img(sky).convert("RGBA"); d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([mx - 74, my - 74, mx + 74, my + 74], fill=(240, 240, 224, 255))
    d.ellipse([mx - 30, my - 18, mx - 4, my + 8], fill=(214, 216, 204, 255)); d.ellipse([mx + 14, my + 14, mx + 48, my + 44], fill=(220, 222, 210, 255))
    d.ellipse([mx - 15, my - 55, mx + 25, my - 25], fill=(222, 224, 212, 255))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(glow).ellipse([mx - 190, my - 190, mx + 190, my + 190], fill=(200, 214, 255, 52))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(50)))
    xs = np.arange(0, W + 8, 8, dtype=np.float32)
    for col, base, comps in [((20, 28, 66), 1250, [(30, 800, 0.6), (14, 360, 2.0)]), ((12, 18, 46), 1340, [(36, 980, 3.0), (16, 430, 1.1)])]:
        ys = ridge(xs, 0, comps, base, 0)
        d.polygon([(float(x), float(y)) for x, y in zip(xs, ys)] + [(W + 8, H), (0, H)], fill=col + (255,))
    return img, (mx, my)


@lru_cache(None)
def _stars(v):
    r = np.random.default_rng(77 + v)
    n = 230
    return r.uniform(0, W, n), r.random(n) ** 1.5 * 1150, r.uniform(1.0, 2.8, n), r.uniform(0, 6.28, n), r.uniform(.6, 2.4, n)


def night(t, v=0):
    base, (mx, my) = _night_static(v % 3)
    img = base.copy(); d = ImageDraw.Draw(img, "RGBA")
    sx, sy, ss, sp, sf = _stars(v % 3)
    for x, y, s, ph, f in zip(sx, sy, ss, sp, sf):
        a = int(150 + 100 * math.sin(t * f + ph))
        d.ellipse([x - s, y - s, x + s, y + s], fill=(250, 248, 240, max(60, min(255, a))))
    # distant camp fires
    for fx, fy, ph in [(180, 1300, 0.3), (330, 1330, 1.7), (900, 1290, 2.9)]:
        fl = .8 + .2 * math.sin(t * 8 + ph)
        d.ellipse([fx - 26, fy - 18, fx + 26, fy + 18], fill=(255, 150, 60, int(50 * fl)))
        d.ellipse([fx - 5, fy - 5, fx + 5, fy + 2], fill=(255, 210, 120, 255))
    back = img.convert("RGB")
    front = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fd = ImageDraw.Draw(front)
    xs = np.arange(0, W + 8, 8, dtype=np.float32)
    ys = ridge(xs, 0, [(18, 820, 1.0), (9, 380, 2.2), (5, 170, .4)], 1472, 0)
    fd.polygon([(float(x), float(y)) for x, y in zip(xs, ys)] + [(W + 8, H), (0, H)], fill=(8, 10, 24, 255))
    fl = .8 + .2 * math.sin(t * 9.5) * math.sin(t * 4.1 + 2) + .05 * math.sin(t * 23)
    tx = [90, 990, 90][v % 3] if v != 2 else 90
    fd.rectangle([tx - 7, 1330, tx + 7, 1480], fill=(54, 34, 24, 255))
    fd.polygon([(tx - 20, 1334), (tx, 1250 - 14 * fl), (tx + 20, 1334)], fill=(255, 150, 50, 255))
    fd.polygon([(tx - 11, 1334), (tx + 2, 1286 - 8 * fl), (tx + 11, 1334)], fill=(255, 230, 150, 255))
    arr = np.asarray(back, np.float32) + radial(tx, 1270, 560, 2.2)[..., None] * np.array([84, 36, 8], np.float32) * fl
    return to_img(arr), front


# =============================================================== SEA
@lru_cache(None)
def _sea_static(v):
    hy = [1010, 1060, 980][v]
    stops = [(0, (30, 44, 100)), (420, (86, 84, 140)), (760, (214, 128, 130)), (hy - 30, (252, 200, 150)), (hy, (252, 214, 168)),
             (hy + 4, (96, 118, 150)), (hy + 200, (40, 84, 120)), (1500, (16, 46, 84)), (H, (8, 26, 52))]
    arr = vgrad(stops)
    sx = [760, 300, 540][v]
    arr += radial(sx, hy, 650, 2.2)[..., None] * np.array([120, 66, 22], np.float32) * (np.arange(H) < hy)[:, None, None]
    return to_img(arr).convert("RGBA"), hy, sx


@lru_cache(None)
def _clouds_strip(v):
    wv = fbm(260, W * 2, [200, 80, 30], [1, .6, .3], 31 + v, wrap_x=True)
    a = np.clip((wv - .5) * 2.8, 0, 1) ** 1.3 * np.clip(1 - np.abs(np.linspace(-1, 1, 260)), 0, 1)[:, None] ** .8
    return a.astype(np.float32)


def sea(t, v=0):
    base, hy, sx = _sea_static(v % 3)
    img = base.copy(); d = ImageDraw.Draw(img, "RGBA")
    sh = int(t * 8) % (W * 2)
    a = np.roll(_clouds_strip(v % 3), -sh, axis=1)[:, :W]
    cl = np.zeros((260, W, 4), np.uint8); cl[..., 0], cl[..., 1], cl[..., 2] = 244, 180, 170; cl[..., 3] = (a * 120).astype(np.uint8)
    img.alpha_composite(Image.fromarray(cl, "RGBA"), (0, 520))
    d.ellipse([sx - 80, hy - 80, sx + 80, hy + 80], fill=(255, 238, 196, 255)); d.rectangle([0, hy, W, hy + 3], fill=(250, 214, 170, 255))
    # sun glitter column
    r = np.random.default_rng(int(t * 6))
    for k in range(70):
        y = hy + 8 + (k / 70) ** 1.6 * 520; wdt = 14 + (y - hy) * .28
        x = sx + r.normal(0, wdt * .6)
        d.line([(x - wdt * .3, y), (x + wdt * .3, y)], fill=(255, 226, 170, int(r.uniform(60, 180))), width=3)
    # perspective wave lines
    for k in range(34):
        u = k / 34; y = hy + 12 + u ** 1.7 * 760
        amp = 1.5 + 11 * u; per = 90 + 520 * u; sp = 25 + 140 * u
        pts = [(x, y + amp * math.sin((x + t * sp) / per * 6.283 + k)) for x in range(-20, W + 40, 24)]
        d.line(pts, fill=(210, 232, 244, int(26 + 60 * u)), width=max(1, int(1 + 4 * u)))
    # small ship far away
    shx = (200 + t * 6) % (W + 300) - 150
    d.polygon([(shx - 26, hy - 3), (shx + 26, hy - 3), (shx + 18, hy + 6), (shx - 18, hy + 6)], fill=(26, 20, 34, 255))
    d.line([(shx, hy - 3), (shx, hy - 34)], fill=(26, 20, 34, 255), width=3)
    d.polygon([(shx + 3, hy - 32), (shx + 3, hy - 8), (shx + 22, hy - 8)], fill=(40, 30, 44, 255))
    back = img.convert("RGB")
    front = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fd = ImageDraw.Draw(front)
    xs = np.arange(0, W + 8, 8, dtype=np.float32)
    ys = ridge(xs, t, [(16, 620, 0.0), (8, 260, 1.4), (4, 120, 2.6)], 1478, 70)
    fd.polygon([(float(x), float(y)) for x, y in zip(xs, ys)] + [(W + 8, H), (0, H)], fill=(10, 30, 56, 255))
    fd.line(list(zip(xs.tolist(), (ys - 1).tolist())), fill=(190, 226, 238, 230), width=4)
    return back, front
