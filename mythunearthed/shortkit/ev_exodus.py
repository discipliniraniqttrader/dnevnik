"""Procedural scenes for the Exodus Short. Every function returns an RGB PIL image (1080x1920)."""
import math
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

A = Path(__file__).resolve().parent.parent / "assets"
from .common import W, H


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def out_back(x, s=1.9):
    x = max(0.0, min(1.0, x)) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def F(name, size):
    return _font(name, size)


@lru_cache(None)
def _font(name, size):
    return ImageFont.truetype(str(A / name), size)


def vgrad(stops, h=H, w=W):
    """stops: [(y, (r,g,b))] -> float32 (h,w,3)"""
    ys = np.arange(h)
    cols = np.array([s[1] for s in stops], np.float32)
    pos = np.array([s[0] for s in stops], np.float32)
    col = np.stack([np.interp(ys, pos, cols[:, k]) for k in range(3)], -1)
    return np.broadcast_to(col[:, None, :], (h, w, 3)).copy()


def to_img(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


@lru_cache(None)
def radial(cx, cy, r, power=2.0):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
    return np.clip(1 - d, 0, 1) ** power


def ridge(x, t, comps, base, speed):
    """x: array; comps [(amp, period, phase)] -> y array. Periodic so it can drift forever."""
    y = np.full_like(x, base, dtype=np.float32)
    for amp, per, ph in comps:
        y += amp * np.sin(2 * np.pi * (x + t * speed) / per + ph)
    return y


@lru_cache(None)
def _particles(n=130):
    r = np.random.default_rng(5)
    return r.uniform(0, W, n), r.uniform(300, 1500, n), r.uniform(1.5, 5.5, n), r.uniform(10, 60, n), r.uniform(0, 6.28, n)


# ===================================================================== counter scene
@lru_cache(None)
def _crowd(n=3400):
    r = np.random.default_rng(21)
    d = r.random(n) ** 0.9
    order = np.argsort(d)
    d = d[order]
    return dict(d=d, x=r.uniform(0, W + 60, n), ph=r.uniform(0, 6.28, n), rank=r.permutation(n))


def counter_scene(lt, dur, t, number=600000, label="MEN ON FOOT", crowd=3400):
    arr = vgrad([(0, (22, 14, 40)), (380, (104, 48, 72)), (640, (232, 130, 70)), (700, (214, 120, 66)), (900, (118, 66, 54)), (H, (46, 28, 34))])
    arr += radial(540, 660, 700, 2.0)[..., None] * np.array([90, 50, 10], np.float32)
    img = to_img(arr)
    d = ImageDraw.Draw(img)
    prog = ease(lt / (dur * 0.86)) ** 0.8
    val = int(round((number or 0) * prog))
    c = _crowd(crowd)
    n = int(len(c["d"]) * prog)
    for i in range(len(c["d"])):
        if c["rank"][i] >= n:
            continue
        dd = float(c["d"][i])
        r = 1.6 + 6.8 * dd
        y = 690 + 860 * dd
        x = (c["x"][i] + t * (14 + 70 * dd)) % (W + 60) - 30
        bob = abs(math.sin(t * 8 + c["ph"][i])) * r * 0.35
        y -= bob
        col = (int(86 - 62 * dd), int(46 - 34 * dd), int(46 - 34 * dd))
        if r < 2.6:
            d.rectangle([x - 1, y - r * 3, x + 1, y], fill=col)
            continue
        d.ellipse([x - r, y - r * 5.2, x + r, y - r * 3.4], fill=col)
        d.line([(x, y - r * 3.4), (x, y - r * 1.4)], fill=col, width=max(2, int(r * 1.5)))
        sw = math.sin(t * 8 + c["ph"][i]) * r * 0.8
        d.line([(x, y - r * 1.4), (x - sw, y)], fill=col, width=max(1, int(r * 0.6)))
        d.line([(x, y - r * 1.4), (x + sw, y)], fill=col, width=max(1, int(r * 0.6)))
    # haze + shade on lower area so text/caption stay legible
    # counter text
    sc = 1.0
    if prog >= 1:
        sc = 1 + 0.12 * max(0, 1 - (lt - dur * 0.86) / 0.25)
    if number is None:
        return img
    txt = f"{val:,}"
    fs_ = 196
    while fs_ > 70 and F("sans-black.ttf", fs_).getlength(txt) > 940: fs_ -= 6
    f = F("sans-black.ttf", int(fs_ * sc))
    d.text((540, 470), txt, font=f, fill=(255, 244, 222), anchor="mm", stroke_width=12, stroke_fill=(24, 12, 8))
    g = F("sans-black.ttf", 84)
    d.text((540, 660), label.upper()[:28], font=g, fill=(244, 188, 60), anchor="mm", stroke_width=9, stroke_fill=(24, 12, 8))
    return img


# ===================================================================== sea parting
@lru_cache(None)
def _wave_grid():
    yy, xx = np.mgrid[0:H // 6, 0:W // 6].astype(np.float32)
    return xx, yy


def water_tex(t, scroll=0.0, vert=False):
    xx, yy = _wave_grid()
    v = (np.sin(xx * 0.26 + yy * 0.11 - t * 2.4) + np.sin(yy * 0.21 - xx * 0.07 + t * 1.9 + 1.3) * 0.8
         + np.sin(xx * 0.5 + yy * 0.33 - t * 3.3) * 0.4 + np.sin((yy + scroll) * 0.45) * 0.3)
    v = v / 2.5
    crest = np.clip(v - 0.25, 0, 1) ** 1.5
    base = np.array([16, 88, 108], np.float32) + (v[..., None] * 20)
    col = base + crest[..., None] * np.array([120, 130, 110], np.float32)
    return Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)


def _sand(h_top, h_bot):
    return vgrad([(0, (170, 138, 96)), (H, (214, 184, 132))])


def sea_top(lt, dur, t):
    u = lt / dur
    img = water_tex(t, scroll=-t * 40)
    g = ease((u - 0.10) / 0.55) * 250
    cx = 540
    yy = np.arange(H, dtype=np.float32)
    wob = 12 * np.sin(yy * 0.018 + t * 3.0) + 7 * np.sin(yy * 0.047 - t * 2.1)
    if g > 4:
        lx, rx = cx - g + wob, cx + g + wob
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # dry seabed
        sand = to_img(_sand(0, H)).convert("RGBA")
        mask = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(mask)
        md.polygon([(float(a), float(y)) for a, y in zip(lx, yy)] + [(float(a), float(y)) for a, y in zip(rx[::-1], yy[::-1])], fill=255)
        sd = ImageDraw.Draw(sand)
        for k in range(0, H, 46):
            yk = (k + t * 90) % H
            sd.line([(cx - g - 30, yk), (cx + g + 30, yk + 10)], fill=(150, 118, 82, 120), width=3)
        img.paste(sand.convert("RGB"), (0, 0), mask)
        # cliff shading: dark shadow cast on sand + foam line on wall edge
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sdr = ImageDraw.Draw(sh)
        for k in range(8):
            a = int(120 * (1 - k / 8))
            off = k * 7
            sdr.line([(float(a_ + off), float(y_)) for a_, y_ in zip(lx, yy)][::6], fill=(20, 30, 30, a), width=9)
            sdr.line([(float(a_ - off), float(y_)) for a_, y_ in zip(rx, yy)][::6], fill=(20, 30, 30, a), width=9)
        # wall highlights (water standing tall)
        for k in range(8):
            off = 6 + k * 14
            a = int(110 * (1 - k / 8))
            sdr.line([(float(a_ - off), float(y_)) for a_, y_ in zip(lx, yy)][::6], fill=(150, 220, 225, a), width=15)
            sdr.line([(float(a_ + off), float(y_)) for a_, y_ in zip(rx, yy)][::6], fill=(150, 220, 225, a), width=15)
        sdr.line([(float(a_), float(y_)) for a_, y_ in zip(lx, yy)][::3], fill=(240, 252, 255, 255), width=8)
        sdr.line([(float(a_), float(y_)) for a_, y_ in zip(rx, yy)][::3], fill=(240, 252, 255, 255), width=8)
        rr = np.random.default_rng(int(t * 12) % 7)
        for _ in range(90):
            y = float(rr.uniform(0, H)); side = rr.choice([-1, 1])
            x = (lx if side < 0 else rx)[int(y) % H] + side * rr.uniform(-6, 28)
            s = rr.uniform(3, 9)
            sdr.ellipse([x - s, y - s, x + s, y + s], fill=(255, 255, 255, int(rr.uniform(110, 230))))
        img = Image.alpha_composite(img.convert("RGBA"), sh).convert("RGB")
        # people crossing: tiny silhouettes walking up the path
        d = ImageDraw.Draw(img)
        if g > 80:
            vis = min(1, (g - 80) / 120)
            for i in range(22):
                y = H + 80 - ((i * 118 + t * 150) % (H + 160))
                x = cx + wob[int(min(max(y, 0), H - 1))] + math.sin(i * 2.3) * g * 0.35
                bob = math.sin(t * 9 + i) * 2
                d.ellipse([x - 13 + 3, y - 10 + 8, x + 13 + 3, y + 10 + 8], fill=(60, 44, 30))  # shadow
                d.ellipse([x - 13, y - 10 + bob, x + 13, y + 10 + bob], fill=(46, 30, 26))
                d.ellipse([x - 8, y - 8 + bob, x + 8, y + 8 + bob], fill=(224, 176, 130))
        return img
    # before the split: a hint of wind lines on the water
    return img


def sea_corridor(lt, dur, t):
    vy, vx = 780, 540
    sky = to_img(vgrad([(0, (36, 70, 96)), (500, (120, 170, 176)), (vy, (250, 214, 150)), (H, (250, 214, 150))]))
    img = sky.copy()
    wt = water_tex(t, scroll=-t * 120)
    # perspective wall polygons
    pl = [(vx - 14, vy), (vx - 14 - 480 * 1.0, vy + (H - vy)), (0, H), (0, 0), (vx - 14 - 340, -420)]
    pl = [(vx - 14, vy - 20), (vx - 14 - (vx - 40) * 0.0 - 0, vy)]
    leftw = [(vx - 12, vy - 24), (110, H), (0, H), (0, -200), (vx - 12 - 280, -300)]
    rightw = [(vx + 12, vy - 24), (W - 110, H), (W, H), (W, -200), (vx + 12 + 280, -300)]
    # darken water with distance haze
    hz = np.clip(1 - (np.arange(H) - 700) / 900, 0, 1)[:, None, None]
    wa = np.asarray(wt, np.float32)
    wa = wa * (0.55 + 0.45 * (1 - hz)) + hz * np.array([30, 70, 80], np.float32) * 0.5
    # top shading: walls tower, darker toward top
    top = np.clip(1 - np.arange(H) / 800, 0, 1)[:, None, None]
    wa = wa * (1 - 0.35 * top)
    wimg = to_img(wa)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.polygon(leftw, fill=255); md.polygon(rightw, fill=255)
    # path
    pd = ImageDraw.Draw(img)
    pd.polygon([(vx - 12, vy), (vx + 12, vy), (W - 110, H), (110, H)], fill=(196, 160, 108))
    img.paste(wimg, (0, 0), mask)
    d = ImageDraw.Draw(img, "RGBA")
    # wet sand edges + sand ripples (perspective lines)
    for k in range(40):
        s = ((k / 40) + t * 0.22) % 1.0
        y = vy + (H - vy) * s ** 2.0
        hw = 12 + (W / 2 - 110 - 12 + 98) * (y - vy) / (H - vy)
        d.line([(vx - hw, y), (vx + hw, y)], fill=(130, 98, 64, int(40 + 110 * s)), width=max(1, int(1 + 4 * s)))
    # foam along wall bases and wall tops
    for (a, b) in (((vx - 12, vy), (110, H)), ((vx + 12, vy), (W - 110, H))):
        d.line([a, b], fill=(240, 252, 255, 255), width=9)
        d.line([(a[0] + (-10 if a[0] < vx else 10), a[1]), (b[0] + (-60 if a[0] < vx else 60), b[1])], fill=(150, 220, 226, 110), width=26)
    # figures walking away
    figs = []
    for i in range(10):
        s = 0.10 + ((i / 10) * 0.75 - t * 0.07) % 0.75
        lane = [-1.1, 0.2, 1.1, 0.7, -0.5][i % 5]
        figs.append((s, lane, i))
    for s, lane, i in sorted(figs):
        y = vy + (H - vy) * s * 0.9
        hgt = 50 + 400 * s
        hw = (12 + (W / 2 - 110 - 12 + 98) * (y - vy) / (H - vy)) * 0.62
        x = vx + lane * hw
        bob = math.sin(t * 8 + i) * hgt * 0.012
        w = hgt * 0.12
        col = (44, 28, 24, 255)
        d.ellipse([x - w * 1.3, y - hgt * 0.03, x + w * 1.3, y + hgt * 0.03], fill=(60, 40, 28, 120))
        d.polygon([(x - w, y - hgt * 0.30 + bob), (x + w, y - hgt * 0.30 + bob), (x + w * 1.1, y - hgt * 0.74 + bob), (x - w * 1.1, y - hgt * 0.74 + bob)], fill=col)
        d.rectangle([x - w * .85, y - hgt * 0.30 + bob, x - w * .25, y], fill=col)
        d.rectangle([x + w * .25, y - hgt * 0.30 + bob, x + w * .85, y], fill=col)
        d.ellipse([x - w * .8, y - hgt * 1.0 + bob, x + w * .8, y - hgt * 0.72 + bob], fill=col)
    # light + spray at the far end
    arr = np.asarray(img, np.float32)
    arr += radial(vx, vy, 520, 1.8)[..., None] * np.array([90, 70, 30], np.float32)
    return to_img(arr)


# ===================================================================== icons card
@lru_cache(None)
def _icons():
    S = 4
    sp = Image.new("RGBA", (128 * S, 128 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(sp)
    d.ellipse([10 * S, 70 * S, 118 * S, 122 * S], fill=(30, 110, 140, 255), outline=(235, 250, 255, 255), width=4 * S)
    d.ellipse([30 * S, 84 * S, 98 * S, 110 * S], fill=(90, 190, 220, 255))
    d.polygon([(64 * S, 8 * S), (92 * S, 62 * S), (36 * S, 62 * S)], fill=(110, 210, 240, 255), outline=(235, 250, 255, 255))
    d.ellipse([36 * S, 40 * S, 92 * S, 94 * S], fill=(110, 210, 240, 255), outline=(235, 250, 255, 255), width=3 * S)
    d.ellipse([50 * S, 52 * S, 62 * S, 68 * S], fill=(255, 255, 255, 230))
    sp = sp.resize((128, 128), Image.LANCZOS)
    pm = Image.new("RGBA", (128 * S, 128 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(pm)
    d.line([(64 * S, 122 * S), (66 * S, 82 * S), (62 * S, 50 * S)], fill=(120, 76, 36, 255), width=9 * S, joint="curve")
    for ang, ln in [(-150, 52), (-120, 56), (-90, 48), (-60, 56), (-30, 52), (-175, 40), (-5, 40)]:
        a = math.radians(ang)
        ex, ey = 62 * S + math.cos(a) * ln * S, 50 * S + math.sin(a) * ln * S + (18 * S if abs(ang + 90) > 50 else 0)
        mx, my = 62 * S + math.cos(a) * ln * .5 * S, 50 * S + math.sin(a) * ln * .5 * S - 12 * S
        d.line([(62 * S, 50 * S), (mx, my), (ex, ey)], fill=(64, 156, 70, 255), width=10 * S, joint="curve")
    d.ellipse([56 * S, 44 * S, 70 * S, 58 * S], fill=(150, 100, 50, 255))
    pm = pm.resize((128, 128), Image.LANCZOS)
    return sp, pm


def icons_scene(lt, t, springs_at, palms_at):
    img = to_img(vgrad([(0, (10, 40, 44)), (900, (22, 70, 66)), (H, (10, 30, 34))]))
    arr = np.asarray(img, np.float32) + radial(540, 900, 800, 2)[..., None] * np.array([20, 50, 30], np.float32)
    img = to_img(arr)
    sp, pm = _icons()
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([90, 460, 990, 770], 30, fill=(0, 0, 0, 70), outline=(110, 210, 240, 90), width=3)
    d.rounded_rectangle([60, 850, 1020, 1450], 30, fill=(0, 0, 0, 70), outline=(110, 190, 90, 90), width=3)
    def put(icon, cx, cy, size, a):
        if a <= 0:
            return
        s = max(2, int(size * out_back(a, 2.6)))
        im = icon.resize((s, s), Image.BILINEAR)
        img.paste(im, (int(cx - s / 2), int(cy - s / 2)), im)
    for i in range(12):
        r, c = divmod(i, 6)
        put(sp, 195 + c * 138, 540 + r * 130 + 30, 118, (lt - springs_at - i * 0.045) / 0.22)
    for i in range(70):
        r, c = divmod(i, 10)
        put(pm, 156 + c * 85, 900 + r * 78 + 40, 82, (lt - palms_at - i * 0.014) / 0.2)
    return img


# ===================================================================== manna
@lru_cache(None)
def _flakes(n=300):
    r = np.random.default_rng(8)
    return dict(x=r.uniform(0, W, n), y=r.uniform(0, H, n), s=r.uniform(3, 12, n), v=r.uniform(110, 330, n), sw=r.uniform(10, 40, n), ph=r.uniform(0, 6.28, n))


def manna_scene(lt, t):
    arr = vgrad([(0, (110, 128, 184)), (520, (214, 170, 176)), (900, (250, 206, 150)), (1010, (255, 232, 176)), (1030, (226, 178, 118)), (1300, (190, 140, 96)), (H, (120, 82, 62))])
    arr += radial(300, 1010, 700, 2.0)[..., None] * np.array([70, 50, 10], np.float32)
    img = to_img(arr)
    d = ImageDraw.Draw(img, "RGBA")
    xs = np.arange(0, W + 8, 8, dtype=np.float32)
    for col, base, comps, spd in [((204, 150, 104), 1050, [(14, 700, 0.5), (7, 300, 2)], 4), ((176, 124, 86), 1160, [(22, 820, 2.2), (10, 360, 1)], 9)]:
        ys = ridge(xs, t, comps, base, spd)
        d.polygon([(float(x), float(y)) for x, y in zip(xs, ys)] + [(W + 8, H), (0, H)], fill=col)
    # accumulating manna on the ground
    r = np.random.default_rng(3)
    nacc = int(min(1, lt / 1.8) * 420)
    for i in range(nacc):
        x, y = r.uniform(0, W), r.uniform(1140, 1850)
        s = 2 + 5 * (y - 1140) / 700
        d.ellipse([x - s, y - s * .6, x + s, y + s * .6], fill=(255, 250, 238, 235))
    f = _flakes()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    tt = t + lt  # flakes already falling when the shot starts
    for x, y, s, v, sw, ph in zip(f["x"], f["y"], f["s"], f["v"], f["sw"], f["ph"]):
        yy = (y + tt * v) % (H + 40) - 20
        xx = x + math.sin(tt * 1.4 + ph) * sw
        od.ellipse([xx - s, yy - s, xx + s, yy + s], fill=(255, 252, 244, 235 if s < 8 else 200))
    ov = ov.filter(ImageFilter.GaussianBlur(0.8))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


# ===================================================================== mountain
@lru_cache(None)
def _mount():
    r = np.random.default_rng(14)
    xs = np.arange(0, W + 12, 12, dtype=np.float32)
    layers = []
    for i, (peak_h, wid, cx, jag) in enumerate([(640, 520, 700, 26), (840, 400, 470, 34), (1000, 300, 560, 40)]):
        prof = peak_h * np.exp(-((xs - cx) / wid) ** 2 * 1.6)
        prof += peak_h * 0.30 * np.exp(-((xs - (cx + 420 * (-1) ** i)) / (wid * 0.5)) ** 2)
        n = np.cumsum(r.normal(0, 1, len(xs)))
        n = (n - np.linspace(n[0], n[-1], len(xs))) * jag * 0.55
        n += r.normal(0, jag * 0.5, len(xs))
        layers.append(np.maximum(prof + n + 120, 60))
    # clouds
    c = r.random((60, 90)).astype(np.float32)
    big = np.asarray(Image.fromarray((c * 255).astype(np.uint8)).resize((1440, 700), Image.BICUBIC), np.float32) / 255
    c2 = r.random((16, 24)).astype(np.float32)
    big2 = np.asarray(Image.fromarray((c2 * 255).astype(np.uint8)).resize((1440, 700), Image.BICUBIC), np.float32) / 255
    cl = np.clip((big * 0.6 + big2 * 0.5 - 0.42) * 2.6, 0, 1)
    cl = np.asarray(Image.fromarray((cl * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7)), np.float32) / 255
    return xs, layers, cl


def _bolt(seed, x0, y0, x1, y1):
    r = np.random.default_rng(seed)
    pts = [(x0, y0)]
    n = 14
    for i in range(1, n + 1):
        f = i / n
        pts.append((x0 + (x1 - x0) * f + r.normal(0, 38) * (1 - f * 0.4), y0 + (y1 - y0) * f))
    branches = []
    for _ in range(3):
        k = r.integers(3, 10)
        bx, by = pts[k]
        dirx = r.choice([-1, 1])
        bp = [(bx, by)]
        for j in range(1, 6):
            bp.append((bx + dirx * j * 40 + r.normal(0, 18), by + j * 50))
        branches.append(bp)
    return pts, branches


FLASHES = [0.9, 1.7]  # seconds from shot start


def mountain_scene(lt, t, flashes=None):
    FLASHES_ = flashes or FLASHES
    xs, layers, cl = _mount()
    fl = 0.0
    for ft in FLASHES_:
        dt = lt - ft
        if 0 <= dt < 0.5:
            fl = max(fl, math.exp(-dt * 9) * 0.2)
    sky = vgrad([(0, (31, 33, 68)), (700, (78, 87, 134)), (1100, (150, 139, 172)), (H, (52, 47, 71))])
    sky += fl * np.array([150, 160, 205], np.float32)
    # cloud decks scrolling
    off = int(t * 22) % 360
    cc = np.tile(cl, (1, 2))[:, off:off + 1080]
    ccf = np.zeros((H, W), np.float32)
    ccf[60:760] = cc
    ccf[820:1380, :] = 0
    shade = np.array([42, 44, 76], np.float32) + fl * np.array([140, 140, 170], np.float32)
    mask = np.clip(ccf * np.clip(1 - np.abs(np.arange(H) - 330) / 520, 0, 1)[:, None] * 1.5, 0, 1)
    sky = sky * (1 - mask[..., None] * 0.9) + shade * mask[..., None] * 0.9
    img = to_img(sky)
    d = ImageDraw.Draw(img, "RGBA")
    rise = ease(lt / 1.35)
    for i, (hy, col) in enumerate(zip(layers, [(68, 70, 102), (38, 38, 60), (14, 12, 24)])):
        delay = ease((lt - i * 0.15) / 1.25)
        base = H - 420 + (1 - delay) * 1100
        col = tuple(int(min(255, c + fl * 120 * (0.5 + 0.3 * i))) for c in col)
        pts = [(float(x), float(base - h)) for x, h in zip(xs, hy)] + [(W + 12, H), (0, H)]
        d.polygon(pts, fill=col)
        d.line(pts[:-2], fill=(150, 160, 200, int(60 + 150 * fl)), width=3)
    # lightning bolts
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for k, ft in enumerate(FLASHES_):
        dt = lt - ft
        if 0 <= dt < 0.22 and not (0.09 < dt < 0.12):
            pts, brs = _bolt(7 + k * 3, 300 + k * 350, 120, 380 + k * 330, 860)
            for w, col in ((26, (150, 170, 255, 90)), (12, (210, 225, 255, 180))):
                od.line(pts, fill=col, width=w, joint="curve")
                for b in brs:
                    od.line(b, fill=col, width=w // 2, joint="curve")
            od.line(pts, fill=(255, 255, 255, 255), width=6, joint="curve")
            for b in brs:
                od.line(b, fill=(255, 255, 255, 255), width=3, joint="curve")
    glow = ov.filter(ImageFilter.GaussianBlur(10))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    img = Image.alpha_composite(img, ov)
    # low fog at the foot
    arr = np.asarray(img.convert("RGB"), np.float32)
    fog = np.exp(-((np.arange(H) - 1560) / 160.0) ** 2)[:, None, None] * 0.35
    arr = arr * (1 - fog) + np.array([110, 112, 140], np.float32) * fog
    # heavy cloud banks drifting in front, upper third
    return to_img(arr)
