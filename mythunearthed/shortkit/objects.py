"""Silhouette props under a spotlight (EVENT scene 'object'): ark_box scroll jar crown gold_pile ship tower gate fire ruins whale."""
import math
from functools import lru_cache
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
from .common import W, H, F, ease, out_back, vgrad, radial, fit_font

S = 2          # supersample
N = 700        # sprite box


def _canvas():
    im = Image.new("RGBA", (N * S, N * S), (0, 0, 0, 0)); return im, ImageDraw.Draw(im)


def P(pts): return [(x * S, y * S) for x, y in pts]


def poly(d, pts, fill): d.polygon(P(pts), fill=fill)


def rect(d, x0, y0, x1, y1, fill): d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill)


def ell(d, x0, y0, x1, y1, fill): d.ellipse([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill)


def line(d, pts, fill, w): d.line(P(pts), fill=fill, width=int(w * S), joint="curve")


def _finish(im):
    """outline + vertical shade + rim light -> RGBA (N x N)"""
    im = im.resize((N, N), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32); al = a[..., 3] / 255
    yy = np.linspace(0, 1, N)[:, None]; xx = np.linspace(0, 1, N)[None, :]
    shade = (1.12 - .30 * yy - .10 * xx)[..., None]
    rgb = np.clip(a[..., :3] * shade, 0, 255)
    rim = np.clip(al - np.roll(np.roll(cv2.GaussianBlur(al, (0, 0), 1.2), 5, 0), 5, 1), 0, 1)[..., None] * al[..., None]
    rgb = np.clip(rgb + rim * np.array([120, 100, 70], np.float32), 0, 255)
    mask = cv2.dilate((al > .3).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
    mask = cv2.GaussianBlur(mask, (0, 0), 1.5)
    out = np.zeros((N, N, 4), np.float32)
    out[..., :3] = np.array([18, 12, 10], np.float32)
    out[..., 3] = mask * 255
    ra = al[..., None]
    out[..., :3] = out[..., :3] * (1 - ra) + rgb * ra
    out[..., 3] = np.maximum(out[..., 3], al * 255)
    return Image.fromarray(out.astype(np.uint8), "RGBA")


GOLD1, GOLD2, GOLD3 = (222, 176, 70, 255), (170, 124, 40, 255), (250, 222, 130, 255)
WOOD1, WOOD2 = (150, 100, 62, 255), (104, 66, 40, 255)
STONE1, STONE2 = (176, 160, 138, 255), (126, 112, 96, 255)


def d_ark_box():
    im, d = _canvas()
    line(d, [(70, 470), (630, 470)], WOOD2, 16)
    rect(d, 150, 330, 550, 520, GOLD2); rect(d, 160, 340, 540, 510, GOLD1)
    for x in (200, 350, 500): rect(d, x - 4, 340, x + 4, 510, GOLD2)
    rect(d, 150, 520, 550, 540, GOLD2)
    rect(d, 140, 292, 560, 336, GOLD1); rect(d, 140, 326, 560, 336, GOLD2)
    for sx, sgn in ((250, 1), (450, -1)):       # two kneeling cherubim with raised wings facing each other
        ell(d, sx - 22, 190, sx + 22, 236, GOLD3)
        poly(d, [(sx - 30 * sgn, 300), (sx + 30 * sgn, 300), (sx + 26 * sgn, 236), (sx - 26 * sgn, 236)], GOLD1)
        poly(d, [(sx, 250), (sx + sgn * 20, 160), (sx - sgn * 90, 80), (sx - sgn * 70, 190), (sx - sgn * 36, 260)], GOLD3)
        poly(d, [(sx, 250), (sx - sgn * 60, 140), (sx - sgn * 70, 190), (sx - sgn * 36, 260)], GOLD1)
    for x in (130, 570): ell(d, x - 14, 456, x + 14, 484, GOLD3)
    return _finish(im)


def d_scroll():
    im, d = _canvas()
    PAR, PAR2 = (236, 218, 176, 255), (200, 176, 128, 255)
    rect(d, 180, 230, 520, 490, PAR)
    for k in range(9):
        w = 280 - (k % 3) * 40; line(d, [(210, 275 + k * 24), (210 + w, 275 + k * 24)], (110, 80, 50, 255), 5)
    for y in (200, 490):
        rect(d, 160, y, 540, y + 36, PAR2); ell(d, 130, y - 2, 190, y + 38, PAR); ell(d, 510, y - 2, 570, y + 38, PAR)
        ell(d, 140, y + 8, 180, y + 28, (150, 110, 70, 255)); ell(d, 520, y + 8, 560, y + 28, (150, 110, 70, 255))
    poly(d, [(330, 480), (370, 480), (390, 560), (350, 540), (310, 560)], (170, 40, 40, 255)); ell(d, 325, 440, 375, 490, (190, 50, 44, 255))
    return _finish(im)


def d_jar():
    im, d = _canvas()
    CL, CL2 = (178, 108, 66, 255), (130, 76, 46, 255)
    ys = np.linspace(90, 600, 60)
    def rad(y):
        u = (y - 90) / 510
        return 46 + 150 * math.sin(math.pi * min(1, u * 1.05)) ** 1.1 * (0.35 + 0.65 * u) + (22 if u < .08 else 0)
    L = [(350 - rad(y), y) for y in ys]; R = [(350 + rad(y), y) for y in ys[::-1]]
    for sgn in (-1, 1):
        line(d, [(350 + sgn * 70, 150), (350 + sgn * 170, 150), (350 + sgn * 190, 260), (350 + sgn * 150, 330)], CL2, 22)
    poly(d, L + R, CL)
    poly(d, [(350 + 0.0, 90)] + [(350 + rad(y), y) for y in ys] + [(350 + 20, 600)] + [(350 + 10, 90)], CL2)
    for y, h in ((250, 14), (330, 22), (470, 14)):
        r = rad(y); rect(d, 350 - r, y, 350 + r, y + h, (236, 200, 140, 255))
    ell(d, 300, 70, 400, 110, CL2)
    return _finish(im)


def d_crown():
    im, d = _canvas()
    poly(d, [(170, 300), (230, 160), (290, 280), (350, 130), (410, 280), (470, 160), (530, 300), (520, 470), (180, 470)], GOLD1)
    poly(d, [(350, 130), (410, 280), (470, 160), (530, 300), (520, 470), (350, 470)], GOLD2)
    rect(d, 170, 440, 530, 500, GOLD3); rect(d, 170, 490, 530, 510, GOLD2)
    for x, c in ((230, (200, 30, 50, 255)), (350, (40, 90, 200, 255)), (470, (30, 160, 90, 255))):
        ell(d, x - 28, 412 - 28, x + 28, 412 + 28, c); ell(d, x - 12, 412 - 18, x + 4, 412 - 4, (255, 255, 255, 150))
    for x, y in ((230, 150), (350, 118), (470, 150)): ell(d, x - 18, y - 18, x + 18, y + 18, GOLD3)
    return _finish(im)


def d_gold_pile():
    im, d = _canvas()
    rng = np.random.default_rng(7)
    rows = 11
    for r in range(rows):
        n = 14 - r; y = 560 - r * 36; w = 54
        for k in range(n):
            x = 350 + (k - (n - 1) / 2) * w * .86 + rng.uniform(-8, 8)
            ell(d, x - w / 2, y - 18, x + w / 2, y + 18, GOLD2); ell(d, x - w / 2, y - 24, x + w / 2, y + 10, GOLD1 if (k + r) % 3 else GOLD3)
            ell(d, x - w / 4, y - 16, x + w / 4, y - 2, (255, 240, 170, 200))
    for x0 in (100, 540):
        poly(d, [(x0, 590), (x0 + 90, 590), (x0 + 74, 548), (x0 + 16, 548)], GOLD1)
    return _finish(im)


def d_ship():
    im, d = _canvas()
    poly(d, [(60, 430), (640, 430), (580, 540), (150, 540)], WOOD2); poly(d, [(60, 430), (640, 430), (620, 462), (80, 462)], WOOD1)
    poly(d, [(60, 430), (30, 380), (80, 424)], WOOD1); poly(d, [(640, 430), (676, 360), (624, 424)], WOOD1)
    rect(d, 340, 110, 360, 440, WOOD2)
    poly(d, [(190, 150), (520, 150), (500, 380), (210, 380)], (236, 222, 190, 255)); poly(d, [(350, 150), (520, 150), (500, 380), (350, 380)], (206, 188, 150, 255))
    for k in range(3): rect(d, 200, 200 + k * 60, 510, 212 + k * 60, (170, 50, 44, 255))
    poly(d, [(360, 110), (360, 70), (420, 90)], (200, 60, 50, 255))
    for x in range(160, 560, 60): ell(d, x - 17, 468, x + 17, 502, (190, 160, 96, 255))
    for k in range(8):
        pts = [(x, 560 + 8 * math.sin(x / 26 + k)) for x in range(40, 670, 18)]
        line(d, [(x, y + k * 3) for x, y in pts], (96, 150, 190, 255) if k % 2 else (140, 190, 220, 255), 9)
    return _finish(im)


def d_tower():
    im, d = _canvas()
    BR, BR2 = (172, 112, 76, 255), (122, 76, 52, 255)
    tiers = [(120, 560, 580, 90), (170, 470, 530, 80), (215, 390, 485, 72), (255, 318, 445, 66), (290, 252, 410, 60), (320, 192, 380, 56)]
    for x0, y0, x1, h in tiers:
        rect(d, x0, y0, x1, y0 + h, BR); rect(d, (x0 + x1) / 2, y0, x1, y0 + h, BR2)
        for k in range(int((x1 - x0) / 38)): rect(d, x0 + 10 + k * 38, y0 + 10, x0 + 24 + k * 38, y0 + 44, (60, 38, 30, 255))
    line(d, [(560, 590), (470, 510), (520, 430), (430, 350), (470, 280), (400, 230), (365, 150)], (240, 214, 160, 255), 14)
    rect(d, 330, 130, 370, 192, BR2); poly(d, [(322, 132), (350, 80), (378, 132)], GOLD1)
    return _finish(im)


def d_gate():
    im, d = _canvas()
    for x0 in (70, 480):
        rect(d, x0, 190, x0 + 150, 590, STONE1); rect(d, x0 + 75, 190, x0 + 150, 590, STONE2)
        for k in range(4): rect(d, x0 + k * 40, 150, x0 + k * 40 + 26, 190, STONE1)
        rect(d, x0 + 62, 270, x0 + 88, 340, (30, 22, 20, 255))
    rect(d, 200, 250, 480, 590, STONE1); rect(d, 200, 250, 480, 300, STONE2)
    for k in range(8): rect(d, 200 + k * 36, 214, 200 + k * 36 + 22, 250, STONE1)
    ell(d, 240, 330, 440, 530, (24, 18, 20, 255)); rect(d, 240, 430, 440, 590, (24, 18, 20, 255))
    rect(d, 240, 430, 336, 590, WOOD1); rect(d, 344, 430, 440, 590, WOOD2)
    for y in (470, 540): rect(d, 240, y, 440, y + 10, (60, 46, 40, 255))
    return _finish(im)


def _flame(d, cx, base, h, w, col, ph):
    L, R = [], []
    for k in range(0, 25):
        u = k / 24; y = base - h * u
        hw = w * (math.sin(math.pi * min(1.0, u ** .62))) * (1 - u) ** .35
        sway = 20 * math.sin(ph + u * 6.5) * u + 10 * math.sin(ph * 1.7 + u * 3) * u
        L.append((cx - hw + sway, y)); R.append((cx + hw + sway, y))
    poly(d, L + R[::-1], col)


def d_fire(t=0.0):
    im, d = _canvas()
    for sgn in (-1, 1):
        poly(d, [(350 + sgn * 40, 600), (350 + sgn * 260, 560), (350 + sgn * 250, 530), (350 + sgn * 30, 570)], WOOD2)
    _flame(d, 350, 580, 420 + 24 * math.sin(t * 9), 170, (200, 40, 20, 255), t * 7)
    _flame(d, 330, 570, 330 + 26 * math.sin(t * 11 + 1), 120, (240, 110, 30, 255), t * 8 + 1)
    _flame(d, 380, 570, 300 + 22 * math.sin(t * 10 + 2), 100, (248, 160, 40, 255), t * 9 + 2)
    _flame(d, 350, 570, 210 + 20 * math.sin(t * 12 + 3), 78, (255, 226, 130, 255), t * 10 + 3)
    poly(d, [(250, 590), (450, 590), (470, 540), (230, 540)], WOOD1)
    return _finish(im)


def d_ruins():
    im, d = _canvas()
    rect(d, 60, 560, 640, 600, STONE2); rect(d, 90, 540, 610, 566, STONE1)
    for x, h, br in ((150, 330, 0), (300, 210, 1), (450, 380, 1), (570, 150, 1)):
        rect(d, x - 34, 540 - h, x + 34, 540, STONE1); rect(d, x, 540 - h, x + 34, 540, STONE2)
        for k in range(0, int(h), 60): rect(d, x - 36, 540 - h + k, x + 36, 540 - h + k + 6, STONE2)
        top = 540 - h
        if br: poly(d, [(x - 40, top + 4), (x - 18, top - 28), (x, top + 2), (x + 16, top - 36), (x + 40, top + 4)], STONE1)
        else: rect(d, x - 44, top - 22, x + 44, top, STONE1)
    poly(d, [(150, 190), (150, 150), (230, 140), (300, 200), (260, 330), (220, 300), (180, 210)], STONE1) if False else None
    ell(d, 200, 505, 330, 560, STONE1); rect(d, 200, 530, 330, 560, STONE2)
    return _finish(im)


def d_whale():
    im, d = _canvas()
    BL, BL2 = (76, 104, 140, 255), (50, 72, 104, 255)
    body = [(70, 380), (130, 300), (260, 240), (420, 250), (540, 300), (600, 360), (650, 300), (690, 230), (640, 220), (610, 270), (590, 340), (540, 410),
            (440, 470), (300, 480), (180, 460), (100, 430)]
    poly(d, body, BL)
    poly(d, [(110, 410), (200, 430), (330, 450), (450, 440), (540, 400), (480, 470), (330, 480), (190, 465)], (214, 220, 230, 255))
    poly(d, [(600, 360), (660, 380), (700, 300), (650, 320)], BL2)
    poly(d, [(330, 400), (400, 430), (360, 520), (320, 470)], BL2)
    ell(d, 170, 330, 196, 356, (240, 240, 240, 255)); ell(d, 178, 338, 190, 350, (20, 20, 30, 255))
    for k in range(6): line(d, [(140 + k * 20, 395 + k * 4), (190 + k * 20, 408 + k * 4)], (160, 170, 190, 255), 4)
    for sgn in (-1, 1):
        line(d, [(250, 238), (250 + sgn * 20, 170), (250 + sgn * 60, 110)], (150, 200, 240, 255), 10)
    for k in range(7):
        pts = [(x, 520 + 10 * math.sin(x / 30 + k)) for x in range(40, 690, 20)]
        line(d, [(x, y + k * 6) for x, y in pts], (60, 120, 170, 255) if k % 2 else (110, 170, 210, 255), 9)
    return _finish(im)


DRAW = {"ark_box": d_ark_box, "scroll": d_scroll, "jar": d_jar, "crown": d_crown, "gold_pile": d_gold_pile, "ship": d_ship, "tower": d_tower,
        "gate": d_gate, "ruins": d_ruins, "whale": d_whale}


@lru_cache(None)
def sprite(name): return DRAW[name]()


def sprite_t(name, t):
    return d_fire(t) if name == "fire" else sprite(name)


@lru_cache(None)
def _spot_bg(hue):
    bg = vgrad([(0, (10, 10, 22)), (900, (22, 20, 36)), (H, (8, 8, 16))])
    cone = Image.new("L", (W, H), 0); d = ImageDraw.Draw(cone)
    d.polygon([(540 - 60, 0), (540 + 60, 0), (540 + 520, 1500), (540 - 520, 1500)], fill=255)
    cone = np.asarray(cone.filter(ImageFilter.GaussianBlur(40)), np.float32) / 255
    cone *= np.clip(1 - np.arange(H) / 1600, 0, 1)[:, None] ** .7
    tint = np.array([[255, 236, 190], [190, 220, 255], [255, 200, 170]][hue % 3], np.float32)
    bg = bg + cone[..., None] * tint * .22 + radial(540, 1380, 520, 1.6)[..., None] * tint * .22
    return np.clip(bg, 0, 255)


def object_scene(lt, dur, t, name, sub=0, label=""):
    bg = _spot_bg(0).copy()
    sp = sprite_t(name, t)
    size = 880
    # turntable feel: width squashes/stretches with a light sweep across the surface
    phi = 0.95 * math.sin(0.8 * t + sub * 1.4)
    sx = 0.80 + 0.20 * math.cos(phi); tilt = 3.5 * math.sin(0.6 * t + sub)
    im = sp.resize((int(size * sx), size), Image.LANCZOS).rotate(tilt, expand=True, resample=Image.BICUBIC)
    a = np.asarray(im, np.float32)
    al = a[..., 3:4] / 255
    # moving specular sweep (diagonal band) masked by the sprite
    hh, ww = a.shape[:2]
    xx = np.arange(ww, dtype=np.float32)[None, :] + np.arange(hh, dtype=np.float32)[:, None] * .35
    pos = ((t * 150 + sub * 300) % (ww + hh * .35 + 400)) - 200
    band = np.exp(-((xx - pos) / 70) ** 2)[..., None] * .26
    rgb = np.clip(a[..., :3] * (1 + band * 1.2) + band * 40, 0, 255)
    bob = 10 * math.sin(t * 1.3)
    cx, cy = 540, 850 + bob
    # shadow pool
    pool = Image.new("L", (W, H), 0); ImageDraw.Draw(pool).ellipse([cx - 330, 1300 - 60, cx + 330, 1300 + 60], fill=200)
    pool = np.asarray(pool.filter(ImageFilter.GaussianBlur(26)), np.float32) / 255
    bg *= (1 - pool[..., None] * .5)
    x0, y0 = int(cx - ww / 2), int(cy - hh / 2)
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + ww, W), min(y0 + hh, H)
    if X1 > X0 and Y1 > Y0:
        s_rgb = rgb[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]; s_a = al[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
        bg[Y0:Y1, X0:X1] = bg[Y0:Y1, X0:X1] * (1 - s_a) + s_rgb * s_a
    # dust motes in the beam
    r = np.random.default_rng(3)
    pim = np.zeros((H, W, 3), np.uint8)
    for i in range(80):
        x = (r.uniform(150, 930) + math.sin(t * .6 + i) * 24); y = (r.uniform(0, 1500) - t * r.uniform(8, 30)) % 1500
        al_ = (.35 + .65 * math.sin(t * 1.4 + i) ** 2)
        cv2.circle(pim, (int(x), int(y)), int(r.uniform(1, 3.2)), (int(255 * al_), int(236 * al_), int(190 * al_)), -1, cv2.LINE_AA)
    bg = bg + pim * .55
    if label:
        pil = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(pil)
        f, lines = fit_font("serif-bold.ttf", label.upper(), 900, 200, 90, 44)
        a_ = ease((lt - .25) / .5)
        for i, ln in enumerate(lines):
            d.text((540, 1300 + i * f.size * 1.1), ln, font=f, fill=(246, 236, 210), anchor="mm", stroke_width=6, stroke_fill=(10, 8, 6))
        pil2 = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))
        return np.asarray(Image.blend(pil2, pil, a_))
    return np.clip(bg, 0, 255).astype(np.uint8)
