"""New generic EVENT scenes: crowd, fire_rain, icon_grid, split_compare."""
import math
from functools import lru_cache
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
from .common import W, H, F, ease, out_back, vgrad, radial, fbm, to_img, fit_font, ridge, wrap_text
from . import ev_exodus as EX
from . import maps as _maps
import fx as FX


# =============================================================== crowd
def crowd_scene(lt, dur, t, label="", count=3000):
    img = EX.counter_scene(lt * .55 + dur * .30, dur, t, number=None, crowd=count)       # already-gathered field, still filling
    if label:
        d = ImageDraw.Draw(img)
        f, lines = fit_font("sans-black.ttf", label.upper(), 940, 240, 110, 50)
        a = ease((lt - .15) / .4)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        for i, ln in enumerate(lines):
            ld.text((540, 470 + i * f.size * 1.1), ln, font=f, fill=(255, 244, 222, int(255 * a)), anchor="mm", stroke_width=10, stroke_fill=(24, 12, 8, int(255 * a)))
        img = Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB")
    return img


# =============================================================== fire rain
@lru_cache(None)
def _fire_static():
    sky = vgrad([(0, (14, 4, 8)), (500, (58, 14, 16)), (900, (150, 40, 24)), (1180, (236, 110, 42)), (1300, (250, 170, 80)), (H, (30, 10, 8))])
    nb = fbm(H, W, [260, 90, 30], [1, .6, .3], 61)
    sky = sky * (.82 + .36 * nb[..., None] * np.clip(1 - np.arange(H) / 1100, 0, 1)[:, None, None] + .0)
    img = to_img(sky).convert("RGBA"); d = ImageDraw.Draw(img, "RGBA")
    rng = np.random.default_rng(12)
    x = 0; base = 1330
    bl = []
    while x < W:
        w = int(rng.integers(50, 130)); h = int(rng.integers(60, 230)); bl.append((x, w, h)); x += w + int(rng.integers(0, 16))
    for x, w, h in bl:
        d.rectangle([x, base - h, x + w, H], fill=(18, 8, 10, 255))
        if h > 140: d.polygon([(x - 4, base - h), (x + w / 2, base - h - 50), (x + w + 4, base - h)], fill=(18, 8, 10, 255))
    d.rectangle([0, base + 60, W, H], fill=(14, 6, 8, 255))
    return img, bl, base


def fire_rain_scene(lt, dur, t, n=120):
    base_img, bl, base = _fire_static()
    img = base_img.copy(); d = ImageDraw.Draw(img, "RGBA")
    for x, w, h in bl:                       # burning windows + roof flames
        r = np.random.default_rng(x)
        for _ in range(int(h / 40)):
            wx = x + r.uniform(8, w - 14); wy = base - r.uniform(20, h - 16); fl = .5 + .5 * math.sin(t * 6 + r.uniform(0, 6.28))
            d.rectangle([wx, wy, wx + 7, wy + 11], fill=(255, 170, 60, int(120 + 100 * fl)))
        fa = ease((lt - .3 - (x % 7) * .08) / .8)
        if fa > 0 and h > 110:
            fh = (40 + 26 * math.sin(t * 9 + x)) * fa
            d.polygon([(x + w * .2, base - h), (x + w * .35, base - h - fh), (x + w * .5, base - h), (x + w * .7, base - h - fh * 1.4), (x + w * .85, base - h)], fill=(255, 150, 40, 200))
    r = np.random.default_rng(5)
    glow = np.zeros((H, W, 3), np.uint8)
    for i in range(n):
        x0 = r.uniform(-200, W + 300); sp = r.uniform(520, 980); y0 = r.uniform(0, H + 400); ln = r.uniform(110, 300); sz = r.uniform(5, 13)
        y = (y0 + t * sp) % (H + 500) - 250; x = x0 - (y + 250) * .42 - t * 0 
        ux, uy = -.38, -.93
        for k, (w_, col) in enumerate(((sz * 1.7, (160, 40, 14)), (sz, (255, 120, 30)), (sz * .45, (255, 220, 140)))):
            cv2.line(glow, (int(x), int(y)), (int(x - ux * ln * (1 - .18 * k)), int(y - uy * ln * (1 - .18 * k))), tuple(int(c * .55) for c in col), max(1, int(w_ * (.6 if k else .4))), cv2.LINE_AA)
        cv2.circle(glow, (int(x), int(y)), int(sz), (255, 190, 90), -1, cv2.LINE_AA)
        if y > base - 20 and y < base + 30:
            pass
    gb = cv2.GaussianBlur(glow, (0, 0), 9)
    arr = np.asarray(img.convert("RGB"), np.float32) + glow.astype(np.float32) * .85 + gb.astype(np.float32) * .8
    return np.clip(arr, 0, 255).astype(np.uint8)


# =============================================================== icon grid
def _icon_sprite(kind):
    _maps.register_icons()
    if kind not in FX.Marker._icons: FX.Marker._icons[kind] = FX.make_icon(kind)
    return FX.Marker._icons[kind]


def icon_grid_scene(lt, dur, t, icon="dot", count=12, label=""):
    bg = vgrad([(0, (10, 24, 34)), (900, (20, 44, 56)), (H, (8, 18, 26))]) + radial(540, 900, 900, 2)[..., None] * np.array([18, 40, 34], np.float32)
    pil = to_img(bg).convert("RGBA")
    spr = _icon_sprite(icon)
    show = min(count, 80)
    cols = 3 if show <= 6 else 4 if show <= 12 else 5 if show <= 25 else 6 if show <= 42 else 8
    rows = int(math.ceil(show / cols))
    gw, gh = 960, 900
    cell = min(gw / cols, gh / rows, 230)
    sc = cell * .92 / spr.shape[1]
    x0 = 540 - cell * cols / 2; y0 = 620 + (gh - cell * rows) / 2 * .6
    span = max(dur * .62, .6)
    nshown = 0
    for i in range(show):
        ti = .2 + span * i / max(show, 1)
        e = out_back((lt - ti) / .28, 2.2)
        if e <= 0: continue
        nshown = i + 1
        r_, c_ = divmod(i, cols)
        cx = x0 + (c_ + .5) * cell; cy = y0 + (r_ + 1) * cell - cell * .08
        w_, h_ = max(2, int(spr.shape[1] * sc * e)), max(2, int(spr.shape[0] * sc * e))
        im = Image.fromarray(spr).resize((w_, h_), Image.LANCZOS)
        if i == nshown - 1 and lt - ti < .3:        # newest icon glows
            gl = im.filter(ImageFilter.GaussianBlur(10)); pil.alpha_composite(gl, (int(cx - w_ / 2), int(cy - h_)))
        pil.alpha_composite(im, (int(cx - w_ / 2), int(cy - h_)))
    d = ImageDraw.Draw(pil)
    shown_n = int(round(count * min(1, max(0, (lt - .2) / span)) ** .9))
    f = F("sans-black.ttf", 190)
    d.text((540, 360), f"{shown_n}", font=f, fill=(255, 244, 222), anchor="mm", stroke_width=12, stroke_fill=(10, 18, 24))
    if label:
        f2, lines = fit_font("sans-black.ttf", label.upper(), 940, 160, 76, 44)
        for i, ln in enumerate(lines):
            d.text((540, 520 + i * f2.size * 1.1), ln, font=f2, fill=(244, 188, 60), anchor="mm", stroke_width=8, stroke_fill=(10, 18, 24))
    return np.asarray(pil.convert("RGB"))


# =============================================================== split compare
def _panel(w, h, col_top, col_bot, border):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    g = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(col_top, np.float32) * (1 - g) + np.array(col_bot, np.float32) * g)
    arr = np.broadcast_to(arr, (h, w, 3)).astype(np.uint8)
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], 44, fill=255)
    im.paste(Image.fromarray(arr), (0, 0), m)
    d.rounded_rectangle([2, 2, w - 3, h - 3], 44, outline=border, width=8)
    return im


@lru_cache(None)
def _panels():
    return (_panel(960, 520, (150, 92, 36), (82, 44, 24), (255, 200, 90, 255)), _panel(960, 520, (34, 92, 130), (18, 44, 80), (150, 220, 255, 255)))


def split_scene(lt, dur, t, left, right, sub=0):
    bg = vgrad([(0, (14, 12, 22)), (H, (8, 8, 16))]) + radial(540, 900, 1000, 2)[..., None] * np.array([16, 14, 24], np.float32)
    pil = to_img(bg).convert("RGBA")
    pl, pr = _panels()
    focus = 0 if (lt / max(dur, .1)) < .5 else 1                     # emphasise the side being talked about
    tx = ease((lt - (dur * .5 - .25)) / .5)
    for i, (txt, pan, y, sgn) in enumerate(((left, pl, 250, -1), (right, pr, 830, 1))):
        e = out_back((lt - (.08 + i * .22)) / .5, 1.5)
        if e <= 0: continue
        x = 60 + sgn * (1 - min(e, 1)) * 1200
        p = pan.copy(); d = ImageDraw.Draw(p)
        f, lines = fit_font("sans-black.ttf", txt.upper(), 840, 330, 100, 44, 1.1)
        y_ = 260 - (len(lines) - 1) * f.size * .55 + 20
        for ln in lines:
            d.text((480, y_), ln, font=f, fill=(255, 246, 226, 255), anchor="mm", stroke_width=8, stroke_fill=(20, 10, 6, 255)); y_ += f.size * 1.1
        d.text((70, 66), "A" if i == 0 else "B", font=F("sans-black.ttf", 64), fill=(255, 220, 140, 255) if i == 0 else (190, 236, 255, 255), anchor="mm", stroke_width=6, stroke_fill=(10, 8, 6, 255))
        dim = .72 + .28 * (1 - abs((1 - focus) - i) if False else (1 if focus == i else 0))
        dim = 1.0 - .28 * ((tx if i == 0 else (1 - tx)))
        a = np.asarray(p, np.float32); a[..., :3] *= dim
        p = Image.fromarray(a.astype(np.uint8), "RGBA")
        sc = 1.0 + (.03 if (focus == i) else 0)
        if sc != 1.0: p = p.resize((int(p.width * sc), int(p.height * sc)), Image.BICUBIC)
        pil.alpha_composite(p, (int(x - (p.width - 960) / 2), int(y - (p.height - 520) / 2)))
    vs = out_back((lt - .5) / .4, 2.4)
    if vs > 0:
        d = ImageDraw.Draw(pil); r = 68 * vs * (1 + .04 * math.sin(t * 6))
        d.ellipse([540 - r, 810 - r, 540 + r, 810 + r], fill=(250, 240, 220, 255), outline=(10, 8, 6, 255), width=7)
        d.text((540, 812), "VS", font=F("sans-black.ttf", int(70 * vs) + 1), fill=(20, 12, 8, 255), anchor="mm")
    return np.asarray(pil.convert("RGB"))
