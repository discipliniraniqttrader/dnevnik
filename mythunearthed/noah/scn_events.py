"""Procedural EVENT / TEXT scenes: aerial photo mound, MOUNTAINS shatter, al-Judi glow, clay tablet, three birds."""
import math
from functools import lru_cache
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.spatial import cKDTree
import sys
from pathlib import Path
A = Path(__file__).resolve().parent.parent / "assets"
W, H = 1080, 1920


def ease(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def out_back(x, s=1.9):
    x = max(0.0, min(1.0, x)) - 1; return 1 + (s + 1) * x ** 3 + s * x ** 2


@lru_cache(None)
def F(name, size): return ImageFont.truetype(str(A / name), size)


def fbm(h, w, scales, weights, seed):
    rng = np.random.default_rng(seed); acc = np.zeros((h, w), np.float32)
    for s, wt in zip(scales, weights):
        small = rng.random((max(h // s, 2) + 3, max(w // s, 2) + 3)).astype(np.float32)
        acc += cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC) * wt
    acc /= sum(weights); lo, hi = np.percentile(acc, [2, 98]); return np.clip((acc - lo) / (hi - lo), 0, 1)


def vgrad(stops, h=H, w=W):
    ys = np.arange(h, dtype=np.float32)
    pos = np.array([s[0] for s in stops], np.float32); cols = np.array([s[1] for s in stops], np.float32)
    return np.stack([np.interp(ys, pos, cols[:, k]) for k in range(3)], -1)[:, None, :].repeat(w, 1)


def radial(cx, cy, r, power=2.0, h=H, w=W):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    return np.clip(1 - np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r, 0, 1) ** power


def paste_rgba(dst, src_rgba_f, x, y):
    """dst float32 HxWx3 ; src float32 hxwx4 (0..255, alpha 0..1 in ch 3)"""
    h, w = src_rgba_f.shape[:2]
    X0, Y0, X1, Y1 = max(x, 0), max(y, 0), min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if X0 >= X1 or Y0 >= Y1: return
    s = src_rgba_f[Y0 - y:Y1 - y, X0 - x:X1 - x]
    a = s[..., 3:4]
    dst[Y0:Y1, X0:X1] = dst[Y0:Y1, X0:X1] * (1 - a) + s[..., :3] * a


# ======================================================================== aerial photo with boat-shaped mound
AW, AH = 1620, 2880


@lru_cache(None)
def _aerial():
    rng = np.random.default_rng(31)
    yy, xx = np.mgrid[0:AH, 0:AW].astype(np.float32)
    hill = fbm(AH, AW, [700, 260, 90, 30, 10], [1, .8, .6, .35, .2], 7)
    slope = (xx / AW) * .25 + (yy / AH) * .12            # broad hillside gradient
    # boat-shaped mound: lens with a pointed bow (right) and blunt stern (left)
    cx, cy, L, Wd = 880, 1500, 560, 150
    u = (xx - cx) / L; v = (yy - cy) / Wd
    hull = np.clip(1 - (v * (1 + .55 * np.clip(u, -1, 1)) / (np.clip(1 - np.abs(u) ** 2.2, 0, 1) ** .55 + 1e-4)) ** 2, 0, 1)
    hull = np.where(np.abs(u) < 1, hull, 0)
    keel = np.clip(1 - (np.abs(v) / 0.35), 0, 1) * (np.abs(u) < .9) * .35
    mound = (hull ** .6) * 1.0 + keel * hull
    z = (hill * .4 + slope + mound * .9).astype(np.float32)
    gx = cv2.Sobel(cv2.GaussianBlur(z, (0, 0), 2.0), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(cv2.GaussianBlur(z, (0, 0), 2.0), cv2.CV_32F, 0, 1, ksize=3)
    shade = np.clip(.62 - (gx * 1.0 + gy * .7) * 3.4, 0, 1.2)
    tex = fbm(AH, AW, [14, 5, 2], [1, .8, .6], 9)
    g = shade * .75 + (hill - .5) * .22 + (tex - .5) * .16
    # field patches / goat tracks (faint lines)
    for _ in range(40):
        x0, y0 = rng.uniform(0, AW), rng.uniform(0, AH)
        ang = rng.uniform(-.5, .5) + 1.0
        pts = np.array([[x0 + k * 40 * math.cos(ang) + rng.normal(0, 8), y0 + k * 40 * math.sin(ang) + rng.normal(0, 8)] for k in range(14)], np.int32)
        cv2.polylines(g, [pts.reshape(-1, 1, 2)], False, float(g.mean() + .08), 2, cv2.LINE_AA)
    g = np.clip(g, 0, 1)
    img = np.stack([g * 232 + 14, g * 214 + 12, g * 176 + 8], -1)      # sepia print tone
    # photo vignette + paper fibre
    vy = np.linspace(-1, 1, AH)[:, None]; vx = np.linspace(-1, 1, AW)[None, :]
    img *= (1 - np.clip((vx ** 2 + vy ** 2 * .8 - .35), 0, 1) ** 1.2 * .55)[..., None]
    return np.clip(img, 0, 255).astype(np.uint8), (cx, cy, L, Wd)


def aerial_scene(lt, dur, t, zoom=(1.0, 1.25), focus=(0.5, 0.5), qmark_at=None, ring_at=0.4):
    """full-frame photo look. focus given in photo-fractions. returns RGB uint8"""
    img, (mx, my, L, Wd) = _aerial()
    u = ease(lt / max(dur, 1e-3))
    z = zoom[0] + (zoom[1] - zoom[0]) * u
    # crop window in photo px: base crop covers 1080x1920 at scale 1.0*(1/1.5)... photo is 1.5x screen
    cw, ch = W / z * 1.5, H / z * 1.5
    fx, fy = focus[0] * AW, focus[1] * AH
    # slight handheld drift
    fx += 12 * math.sin(t * 1.3); fy += 9 * math.sin(t * 1.7 + 1)
    x0 = min(max(fx - cw / 2, 0), AW - cw); y0 = min(max(fy - ch / 2, 0), AH - ch)
    out = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA if z < 1.5 else cv2.INTER_CUBIC, dst=None) if False else None
    M = np.array([[W / cw, 0, -x0 * W / cw], [0, H / ch, -y0 * H / ch]], np.float32)
    out = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_AREA if W / cw < 1 else cv2.INTER_CUBIC).astype(np.float32)
    S = lambda px, py: ((px - x0) * W / cw, (py - y0) * H / ch)
    sx, sy = S(mx, my); k = W / cw
    # film grain + flicker
    r = np.random.default_rng(int(t * 30) % 997)
    out += r.normal(0, 7, (H, W))[..., None]
    out *= 1 + 0.025 * math.sin(t * 23)
    outu = np.clip(out, 0, 255).astype(np.uint8)
    pil = Image.fromarray(outu); d = ImageDraw.Draw(pil, "RGBA")
    # survey crosshair + targeting ring around the mound
    ra = ease((lt - ring_at) / .5)
    if ra > 0:
        rr = (L * 0.78) * k
        for q in range(4):
            a0 = q * 90 + 20 + 40 * (1 - ra)
            d.arc([sx - rr, sy - rr * .62, sx + rr, sy + rr * .62], a0, a0 + 52 * ra, fill=(255, 236, 190, 255), width=5)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            d.line([(sx + dx * (rr * .36), sy + dy * (rr * .36 * .62)), (sx + dx * rr * .52, sy + dy * rr * .52 * .62)], fill=(255, 236, 190, int(255 * ra)), width=4)
    # question mark pops on the mound
    if qmark_at is not None and lt >= qmark_at:
        q = out_back((lt - qmark_at) / .45, 2.4)
        f = F("sans-black.ttf", int(330 * k * q + 1))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
        gd.text((sx, sy - 10), "?", font=f, fill=(255, 70, 54, 255), anchor="mm", stroke_width=16, stroke_fill=(30, 8, 6, 255))
        glow = glow.rotate(-6, center=(sx, sy))
        pil = pil.convert("RGBA"); pil.alpha_composite(glow); d = ImageDraw.Draw(pil, "RGBA")
    pil = pil.convert("RGB")
    # ---- "aerial photo" frame look: dark film border, edge ticks, caption strip
    d = ImageDraw.Draw(pil, "RGBA")
    d.rectangle([0, 0, W, 56], fill=(10, 8, 6, 255)); d.rectangle([0, H - 56, W, H], fill=(10, 8, 6, 255))
    d.rectangle([0, 0, 38, H], fill=(10, 8, 6, 255)); d.rectangle([W - 38, 0, W, H], fill=(10, 8, 6, 255))
    for i in range(0, H, 48):
        d.rectangle([14, i + 12, 26, i + 28], fill=(60, 52, 40, 255)); d.rectangle([W - 26, i + 12, W - 14, i + 28], fill=(60, 52, 40, 255))
    d.rectangle([38, 56, W - 38, H - 56], outline=(236, 224, 190, 200), width=3)
    for i in range(1, 8):
        xx = 38 + i * (W - 76) / 8
        d.line([(xx, 56), (xx, 78)], fill=(236, 224, 190, 190), width=3); d.line([(xx, H - 56), (xx, H - 78)], fill=(236, 224, 190, 190), width=3)
    for i in range(1, 14):
        yy = 56 + i * (H - 112) / 14
        d.line([(38, yy), (60, yy)], fill=(236, 224, 190, 190), width=3); d.line([(W - 38, yy), (W - 60, yy)], fill=(236, 224, 190, 190), width=3)
    f = F("sans-semi.ttf", 30)
    d.text((64, 78), "1959 AERIAL SURVEY", font=f, fill=(246, 236, 200, 235), stroke_width=3, stroke_fill=(10, 8, 6, 255))
    d.text((W - 64, H - 78), "PRINT " + f"{int(17 + (t * 9) % 60):03d}", font=f, fill=(246, 236, 200, 210), anchor="rd", stroke_width=3, stroke_fill=(10, 8, 6, 255))
    return np.asarray(pil)


# ======================================================================== MOUNTAINS shatter into peaks
@lru_cache(None)
def _shards(word, size, nseed=46):
    f = F("sans-black.ttf", size)
    tw = int(f.getlength(word)) + 40
    im = Image.new("RGBA", (tw, size + 80), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((tw / 2, (size + 80) / 2), word, font=f, fill=(255, 255, 255, 255), anchor="mm")
    a = np.asarray(im)[..., 3] > 128
    ys, xs = np.nonzero(a)
    rng = np.random.default_rng(12)
    seeds = np.c_[rng.uniform(xs.min(), xs.max(), nseed), rng.uniform(ys.min(), ys.max(), nseed)]
    _, lab = cKDTree(seeds).query(np.c_[xs, ys])
    out = []
    arr = np.asarray(im)
    for k in range(nseed):
        sel = lab == k
        if sel.sum() < 40: continue
        px, py = xs[sel], ys[sel]
        x0, x1, y0, y1 = px.min(), px.max() + 1, py.min(), py.max() + 1
        crop = np.zeros((y1 - y0 + 4, x1 - x0 + 4, 4), np.uint8)
        crop[py - y0 + 2, px - x0 + 2] = arr[py, px]
        out.append(dict(img=crop, c=(px.mean(), py.mean()), box=(x0 - 2, y0 - 2), n=int(sel.sum())))
    return (tw, size + 80), out


@lru_cache(None)
def _peaks():
    r = np.random.default_rng(5)
    xs = np.linspace(80, 1000, 7)
    hs = r.uniform(.55, 1.0, 7); hs[3] = 1.0
    return [dict(x=float(x) + r.uniform(-18, 18), h=float(260 + 330 * h), w=float(180 + 170 * h)) for x, h in zip(xs, hs)]


def _draw_peak(canvas, cx, base_y, h, w, glow=0.0, scl=1.0):
    d = ImageDraw.Draw(canvas, "RGBA")
    hh, ww = h * scl, w * scl
    top = (cx, base_y - hh)
    L = (cx - ww / 2, base_y); R_ = (cx + ww / 2, base_y)
    d.polygon([L, top, R_], fill=(70, 84, 112, 255))
    d.polygon([top, (cx + ww * .06, base_y), R_], fill=(46, 58, 86, 255))        # shaded face
    # snow cap with jagged skirt
    cap = hh * .34
    ptsL = [(cx - ww * .5 * (cap / hh), base_y - hh + cap)]
    d.polygon([top, (cx - ww * .17, base_y - hh + cap), (cx - ww * .09, base_y - hh + cap * .78), (cx - ww * .02, base_y - hh + cap * 1.0),
               (cx + ww * .05, base_y - hh + cap * .72), (cx + ww * .12, base_y - hh + cap * .96), (cx + ww * .17, base_y - hh + cap)], fill=(236, 242, 252, 255))
    d.polygon([top, (cx + ww * .02, base_y - hh + cap * .98), (cx + ww * .05, base_y - hh + cap * .72), (cx + ww * .12, base_y - hh + cap * .96), (cx + ww * .17, base_y - hh + cap)], fill=(186, 200, 226, 255))
    if glow > 0:
        d.line([L, top, R_], fill=(255, 214, 120, int(255 * glow)), width=7, joint="curve")


def shatter_scene(lt, t, t_quote, t_word, t_shatter, t_peaks_end):
    """times are absolute within the scene (lt). returns RGB uint8"""
    bg = vgrad([(0, (14, 22, 40)), (800, (28, 46, 72)), (1300, (64, 80, 104)), (H, (22, 28, 44))]) + radial(540, 760, 700, 2.0)[..., None] * np.array([40, 34, 26], np.float32)
    # drifting wind streaks
    r = np.random.default_rng(3)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for k in range(26):
        y = r.uniform(200, 1500); L = r.uniform(120, 360); sp = r.uniform(120, 380); x = (r.uniform(0, W + 400) + t * sp) % (W + 500) - 250
        od.line([(x, y), (x + L, y)], fill=(210, 226, 240, int(r.uniform(18, 50))), width=2)
    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)); img.paste(ov.convert("RGB"), (0, 0), ov.split()[3])
    # peaks row rising after shatter
    base_y = 1300
    if lt >= t_shatter - 0.05:
        for i, p in enumerate(sorted(_peaks(), key=lambda p: abs(p["x"] - 540), reverse=True)):
            dt = lt - (t_shatter + 0.06 * i)
            if dt < 0: continue
            sc = out_back(dt / .55, 1.5)
            hl = 0.0
            if lt > t_peaks_end:   # sweep a golden highlight along the row ("many peaks")
                j = (lt - t_peaks_end) * 6.5
                hl = float(np.clip(1 - abs(j - sorted(_peaks(), key=lambda q: q["x"]).index(p)) / 1.5, 0, 1))
            _draw_peak(img, p["x"], base_y, p["h"], p["w"], hl, sc)
        d = ImageDraw.Draw(img, "RGBA")
        ga = ease((lt - t_shatter - .3) / .6)
        d.rectangle([0, base_y - 4, W, H], fill=(18, 24, 40, 255))
        d.line([(0, base_y - 4), (W, base_y - 4)], fill=(120, 140, 170, int(200 * ga)), width=3)
    d = ImageDraw.Draw(img, "RGBA")
    # quote phase: GENESIS 8:4 + "the ... of Ararat"
    qa = ease((lt - t_quote) / .35) * (1 - ease((lt - t_shatter - .1) / .3))
    if qa > 0:
        f = F("sans-black.ttf", 64); g = F("serif-bold.ttf", 76)
        d.text((540, 560), "GENESIS 8:4", font=f, fill=(232, 170, 40, int(255 * qa)), anchor="mm", stroke_width=5, stroke_fill=(10, 8, 6, int(255 * qa)))
        d.text((540, 650), "“the", font=g, fill=(246, 236, 210, int(255 * qa)), anchor="mm")
    # the word
    (tw, th), shards = _shards("MOUNTAINS", 150)
    cx, cy = 540, 830
    if lt >= t_word and lt < t_shatter:
        s = 1.0 + 1.6 * (1 - out_back((lt - t_word) / .28, 1.6)) * 0.55
        wob = 1 + .015 * math.sin(t * 40) * ease((lt - t_shatter + .5) / .5)   # shivers before it breaks
        f = F("sans-black.ttf", int(150 * s * wob))
        a = min(1, (lt - t_word) / .1)
        d.text((cx, cy), "MOUNTAINS", font=f, fill=(250, 244, 226, int(255 * a)), anchor="mm", stroke_width=10, stroke_fill=(8, 10, 16, int(255 * a)))
        d.text((cx, cy + 120), "of Ararat”", font=F("serif-bold.ttf", 76), fill=(246, 236, 210, int(255 * a)), anchor="mm")
        cr = ease((lt - t_shatter + .4) / .4)     # hairline cracks just before the break
        if cr > 0:
            rr = np.random.default_rng(1)
            for _ in range(14):
                x = cx + rr.uniform(-420, 420); y = cy + rr.uniform(-60, 60)
                d.line([(x, y), (x + rr.uniform(-60, 60), y + rr.uniform(-60, 60))], fill=(255, 214, 140, int(230 * cr)), width=3)
    elif lt >= t_shatter:
        dt = lt - t_shatter
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        rng = np.random.default_rng(21)
        for k, s in enumerate(shards):
            ang = rng.uniform(0, 2 * math.pi); sp = rng.uniform(260, 820)
            ox, oy = s["c"][0] - tw / 2, s["c"][1] - th / 2
            vx = math.cos(ang) * sp + ox * 2.2; vy = math.sin(ang) * sp * .8 - 420 + oy * 1.4
            om = rng.uniform(-420, 420)
            px = cx + ox + vx * dt; py = cy + oy + vy * dt + 1500 * dt * dt * .5
            al = float(np.clip(1 - (dt - .55) / .55, 0, 1))
            if al <= 0: continue
            crop = s["img"]; ch_, cw_ = crop.shape[:2]
            Mx = cv2.getRotationMatrix2D((cw_ / 2, ch_ / 2), om * dt, 1.0)
            Mx[:, 2] += [px - cw_ / 2 + (s["c"][0] - s["box"][0] - cw_ / 2) * 0, py - ch_ / 2]
            Mx[0, 2] += (-(s["c"][0] - s["box"][0]) + cw_ / 2)    # keep shard centre at its own centroid
            Mx[1, 2] += (-(s["c"][1] - s["box"][1]) + ch_ / 2)
            tmp = cv2.warpAffine(crop, Mx, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
            tmp[..., 3] = (tmp[..., 3] * al).astype(np.uint8)
            tint = np.array([250, 244, 226], np.float32) * (0.75 + .25 * rng.random()) 
            tmp[..., :3] = tint.astype(np.uint8)
            sh = Image.alpha_composite(sh, Image.fromarray(tmp, "RGBA"))
        img.paste(sh.convert("RGB"), (0, 0), sh.split()[3])
        # flash ring at the break
        if dt < .35:
            e = dt / .35
            ov2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ov2).ellipse([cx - 80 - 520 * e, cy - 40 - 260 * e, cx + 80 + 520 * e, cy + 40 + 260 * e], outline=(255, 236, 190, int(220 * (1 - e))), width=int(10 * (1 - e)) + 2)
            img.paste(ov2.convert("RGB"), (0, 0), ov2.split()[3])
    return np.asarray(img.convert("RGB"))


# ======================================================================== al-Judi glow
def judi_scene(lt, dur, t, t_text, t_dissolve, map_frame=None):
    """dark glowing text scene that dissolves into `map_frame` (uint8 RGB or None)."""
    yy = vgrad([(0, (6, 14, 18)), (900, (14, 40, 44)), (H, (6, 14, 20)) ])
    k = ease((lt - t_text) / .8)
    yy += radial(540, 860, 760, 1.8)[..., None] * np.array([90, 64, 18], np.float32) * k
    # radiating rays
    ang = np.arctan2(*(np.mgrid[0:H, 0:W].astype(np.float32) - np.array([860, 540], np.float32)[:, None, None]))
    rays = (np.sin(ang * 18 + t * .25) * .5 + .5) ** 3 * radial(540, 860, 900, 1.3) * .35 * k
    yy += rays[..., None] * np.array([120, 92, 30], np.float32)
    base = np.clip(yy, 0, 255)
    dis = ease((lt - t_dissolve) / 1.1)
    if map_frame is not None and dis > 0:
        base = base * (1 - dis) + map_frame.astype(np.float32) * dis
    # text layer
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(txt)
    s = 0.92 + .08 * ease((lt - t_text) / 1.2) + .16 * dis
    f = F("serif-bold.ttf", int(250 * s))
    d.text((540, 860), "al-Judi", font=f, fill=(255, 226, 150, 255), anchor="mm", stroke_width=3, stroke_fill=(120, 70, 10, 255))
    a = np.asarray(txt).astype(np.float32)
    fade = k * (1 - dis)
    glowl = cv2.GaussianBlur(a, (0, 0), 28) * np.array([1, .9, .6, 1.4], np.float32) 
    glowm = cv2.GaussianBlur(a, (0, 0), 8 + 26 * dis)
    pulse = .8 + .2 * math.sin(t * 5)
    out = base.copy()
    ga = np.clip(glowl[..., 3:4] / 255 * 1.2 * pulse * fade, 0, 1)
    out = out * (1 - ga * .6) + np.array([255, 190, 70], np.float32) * ga * .6
    blur_mix = dis
    ta_ = (glowm[..., 3:4] / 255) * blur_mix + (a[..., 3:4] / 255) * (1 - blur_mix)
    tc = glowm[..., :3] * blur_mix + a[..., :3] * (1 - blur_mix)
    ta_ = ta_ * fade
    out = out * (1 - ta_) + tc * ta_
    # dust particles lifting off the lettering during the dissolve
    if k > 0:
        r = np.random.default_rng(8)
        pimg = Image.fromarray(np.zeros((H, W, 3), np.uint8)); pd = ImageDraw.Draw(pimg)
        for i in range(160):
            px = 540 + r.normal(0, 260); py = 860 + r.normal(0, 70)
            sp = r.uniform(30, 120); ph = r.uniform(0, 6.28)
            up = (lt - t_dissolve) if lt > t_dissolve else 0
            x = px + math.sin(t * 1.5 + ph) * 14 + up * r.uniform(-90, 90); y = py - ((t * sp * .25) % 160) - up * sp * 1.3
            al = (0.4 + .6 * math.sin(t * 3 + ph) ** 2) * k * (1 - ease(up / 1.4))
            rr = r.uniform(1.5, 4.2)
            pd.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(int(255 * al), int(214 * al), int(120 * al)))
        pa = np.asarray(pimg.filter(ImageFilter.GaussianBlur(1.1))).astype(np.float32)
        out = out + pa
    return np.clip(out, 0, 255).astype(np.uint8)


# ======================================================================== clay tablet
TW, TH = 800, 1080


@lru_cache(None)
def _tablet():
    rng = np.random.default_rng(17)
    yy, xx = np.mgrid[0:TH, 0:TW].astype(np.float32)
    # outline: rounded rectangle with slightly pillowed edges
    mk = Image.new("L", (TW, TH), 0)
    ImageDraw.Draw(mk).rounded_rectangle([14, 14, TW - 14, TH - 14], 90, fill=255)
    mk = np.asarray(mk.filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
    dist = cv2.distanceTransform((mk > .5).astype(np.uint8), cv2.DIST_L2, 5)
    base_h = np.clip(dist / 60, 0, 1) ** .7
    noise = fbm(TH, TW, [180, 60, 20, 6], [1, .8, .5, .3], 4)
    cracks = np.zeros((TH, TW), np.float32)
    for _ in range(7):
        x, y = rng.uniform(40, TW - 40), rng.uniform(40, TH - 40); pts = [(x, y)]
        for _k in range(18):
            x += rng.normal(0, 14); y += rng.normal(8, 18); pts.append((x, y))
        cv2.polylines(cracks, [np.array(pts, np.int32).reshape(-1, 1, 2)], False, 1.0, 2, cv2.LINE_AA)
    # carving layer (cuneiform-like wedges) and the boat-on-peak picture
    carve = np.zeros((TH, TW), np.float32); rowid = np.zeros((TH, TW), np.int32)
    marks_y0, rows, rowh = 520, 10, 52
    nrows = rows
    for r_ in range(nrows):
        yc = marks_y0 + r_ * rowh
        x = 70
        while x < TW - 90:
            nw = int(rng.integers(2, 6))
            for _k in range(nw):
                ox, oy = x + rng.integers(0, 10), yc + rng.integers(-8, 8)
                kind = rng.integers(0, 3)
                L = int(rng.integers(16, 30))
                layer = np.zeros((TH, TW), np.float32)
                if kind == 0:    # horizontal wedge
                    cv2.fillConvexPoly(layer, np.array([[ox, oy - 7], [ox, oy + 7], [ox + L, oy]], np.int32), 1.0)
                elif kind == 1:  # vertical wedge
                    cv2.fillConvexPoly(layer, np.array([[ox - 7, oy - 14], [ox + 7, oy - 14], [ox, oy + L - 12]], np.int32), 1.0)
                else:            # diagonal wedge
                    cv2.fillConvexPoly(layer, np.array([[ox - 6, oy - 10], [ox + 6, oy - 4], [ox + L * .7, oy + L * .7]], np.int32), 1.0)
                carve = np.maximum(carve, layer); rowid[layer > 0] = r_
                ox += 11 + int(rng.integers(0, 6))
            x += 20 + nw * 17 + int(rng.integers(10, 26))
    # picture frame near the top: peak with a little boat on it, waves
    pic = np.zeros((TH, TW), np.float32)
    px0, py0, px1, py1 = 160, 100, 640, 440
    cv2.rectangle(pic, (px0, py0), (px1, py1), 1.0, 7)
    cv2.rectangle(pic, (px0 + 16, py0 + 16), (px1 - 16, py1 - 16), 1.0, 3)
    peak = np.array([[px0 + 70, py1 - 26], [px0 + 235, py0 + 120], [px0 + 300, py0 + 170], [px0 + 330, py0 + 140], [px1 - 60, py1 - 26]], np.int32)
    cv2.polylines(pic, [peak.reshape(-1, 1, 2)], False, 1.0, 9, cv2.LINE_AA)
    cv2.polylines(pic, [np.array([[px0 + 235, py0 + 120], [px0 + 215, py0 + 152], [px0 + 252, py0 + 146], [px0 + 235, py0 + 120]], np.int32).reshape(-1, 1, 2)], False, 1.0, 6, cv2.LINE_AA)  # snow notch
    bx, by = px0 + 235, py0 + 112
    hull = np.array([[bx - 62, by - 38], [bx + 62, by - 38], [bx + 40, by - 8], [bx - 40, by - 8]], np.int32)
    cv2.polylines(pic, [hull.reshape(-1, 1, 2)], True, 1.0, 7, cv2.LINE_AA)
    cv2.line(pic, (bx, by - 38), (bx, by - 88), 1.0, 6, cv2.LINE_AA)
    cv2.line(pic, (bx - 20, by - 38), (bx - 20, by - 62), 1.0, 5, cv2.LINE_AA)
    cv2.line(pic, (bx - 62, by - 52), (bx - 80, by - 66), 1.0, 5, cv2.LINE_AA)
    cv2.line(pic, (bx + 62, by - 52), (bx + 80, by - 66), 1.0, 5, cv2.LINE_AA)
    for k in range(3):
        wv = np.array([[px0 + 40 + j * 12, py1 - 62 - k * 0 + 10 * math.sin(j * .9 + k)] for j in range(34)], np.int32)
        cv2.polylines(pic, [wv.reshape(-1, 1, 2)], False, 1.0, 4, cv2.LINE_AA)
    pic_mask = cv2.GaussianBlur(pic, (0, 0), .8)
    hgt = base_h * (.8 + .2 * noise) - cracks * .08
    cm = cv2.GaussianBlur(carve, (0, 0), 1.2); pm = pic_mask
    hgt = hgt.astype(np.float32)
    return dict(mk=mk, hgt=hgt, noise=noise, carve=cm, pic=pm, rowid=rowid, carve_raw=carve, cracks=cracks, marks_y0=marks_y0, rowh=rowh, rows=nrows)


def tablet_scene(lt, dur, t, t_marks, zoom_pic_at, pic_glow_at):
    T = _tablet()
    z_pic = ease((lt - zoom_pic_at) / .6)
    # reveal of carving per row, left to right (typing effect)
    yy, xx = np.mgrid[0:TH, 0:TW].astype(np.float32)
    rowprog = np.clip((lt - t_marks) / 1.6, 0, 1.4)
    thr = (rowprog * T["rows"] - T["rowid"]) * (TW + 80) / 1.0 - 40
    reveal = np.clip((thr - xx) / 18, 0, 1) * (T["carve_raw"] > 0)
    reveal = np.maximum(reveal, 0)
    cm_t = T["carve"] * cv2.GaussianBlur(reveal, (0, 0), 1.0)
    pic_t = T["pic"] * ease((lt - t_marks + .25) / .6)
    hgt_c = (T["hgt"] - cm_t * .34 - pic_t * .3).astype(np.float32)
    gx = cv2.Sobel(cv2.GaussianBlur(hgt_c, (0, 0), 1.0), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(cv2.GaussianBlur(hgt_c, (0, 0), 1.0), cv2.CV_32F, 0, 1, ksize=3)
    light = np.array([-.55, -.75], np.float32)
    sh = np.clip(.62 - (gx * light[0] + gy * light[1]) * 3.2, .1, 1.4)
    clay = np.array([196, 150, 98], np.float32) * (0.82 + .3 * T["noise"])[..., None]
    col = clay * sh[..., None] * (.74 + .26 * np.clip(T["hgt"] * 1.3, 0, 1))[..., None]
    col -= T["cracks"][..., None] * np.array([70, 60, 42], np.float32) * .7
    # carved areas slightly darker and warmer
    ca = np.clip(cm_t * 1.2 + pic_t * 1.0, 0, 1)[..., None]
    col = col * (1 - ca * .22)
    # amber glow in the carved picture once "proposed" lands
    ga = ease((lt - pic_glow_at) / .5) * (.75 + .25 * math.sin(t * 5))
    if ga > 0:
        col += (T["pic"] * ga)[..., None] * np.array([150, 80, 14], np.float32) * 1.4
    rgba = np.dstack([np.clip(col, 0, 255), T["mk"] * 1.0]).astype(np.float32)
    rgba[..., 3] = T["mk"]
    # page: dark warm room with lamp light
    bg = vgrad([(0, (22, 14, 12)), (900, (52, 32, 22)), (H, (18, 11, 10))]) + radial(540, 900, 900, 1.7)[..., None] * np.array([70, 40, 14], np.float32)
    # tablet transform: slow float + slight rotation, zoom to the picture later
    ent = out_back(lt / .55, 1.2)
    sc = (1.02 + .05 * lt / dur) * (1 - .0) * (0.8 + .2 * ent)
    sc = sc * (1 + z_pic * 1.05)
    ang = -3.2 + 1.2 * math.sin(t * .8) + z_pic * 3.2
    tcx, tcy = 540, 1010
    # zoom target: picture centre (400,270 in tablet px)
    px, py = 400 - TW / 2, 270 - TH / 2
    ox = -px * sc * z_pic * 0.92; oy = -py * sc * z_pic * 0.92
    M = cv2.getRotationMatrix2D((TW / 2, TH / 2), ang, sc)
    M[0, 2] += tcx - TW / 2 + ox; M[1, 2] += tcy - TH / 2 + oy + (1 - ent) * -300
    warped = cv2.warpAffine(rgba, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    # drop shadow
    sh_a = cv2.GaussianBlur(warped[..., 3], (0, 0), 24)
    sh_a = np.roll(np.roll(sh_a, 34, 0), 18, 1)
    out = bg * (1 - sh_a[..., None] * .75)
    a = warped[..., 3:4]
    out = out * (1 - a) + warped[..., :3] * a
    # dust motes in lamplight
    r = np.random.default_rng(2)
    pimg = np.zeros((H, W, 3), np.uint8)
    for i in range(70):
        x = (r.uniform(0, W) + t * r.uniform(-10, 14)) % W; y = (r.uniform(0, H) - t * r.uniform(5, 26)) % H
        al = (.4 + .6 * math.sin(t * 1.6 + i) ** 2) * .8
        cv2.circle(pimg, (int(x), int(y)), int(r.uniform(1, 3)), (int(255 * al), int(214 * al), int(150 * al)), -1, cv2.LINE_AA)
    out = out + pimg * .6
    vig = 1 - np.clip(((np.mgrid[0:H, 0:W][1] - 540) / 760.) ** 2 + ((np.mgrid[0:H, 0:W][0] - 960) / 1180.) ** 2 - .35, 0, 1) * .6
    return np.clip(out * vig[..., None], 0, 255).astype(np.uint8)


# ======================================================================== birds
def _bird_sprite(kind, ph, size=200):
    """RGBA sprite facing right. ph = flap phase 0..1"""
    S = 3; w, h = size * S, int(size * .8) * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy = w * .5, h * .56
    L = {"dove": 1.0, "swallow": .86, "raven": 1.18}[kind] * size * S * .30      # half body length
    col = {"dove": (250, 250, 252), "swallow": (26, 34, 70), "raven": (16, 14, 20)}[kind]
    shade = {"dove": (206, 214, 232), "swallow": (14, 18, 44), "raven": (34, 30, 42)}[kind]
    wing_col = {"dove": (244, 246, 252), "swallow": (22, 30, 62), "raven": (14, 12, 18)}[kind]
    fl = math.sin(ph * 2 * math.pi)       # +1 up, -1 down
    # tail
    if kind == "swallow":
        for s_ in (-1, 1):
            d.polygon([(cx - L * .7, cy - 2 * S), (cx - L * 1.9, cy + s_ * L * .55), (cx - L * 1.7, cy + s_ * L * .22), (cx - L * .5, cy + 4 * S)], fill=col)
    elif kind == "raven":
        d.polygon([(cx - L * .8, cy - L * .22), (cx - L * 1.65, cy - L * .42), (cx - L * 1.75, cy + L * .05), (cx - L * 1.55, cy + L * .42), (cx - L * .7, cy + L * .24)], fill=col)
    else:
        d.polygon([(cx - L * .8, cy - L * .18), (cx - L * 1.55, cy - L * .28), (cx - L * 1.6, cy + L * .22), (cx - L * .75, cy + L * .2)], fill=shade)
        d.polygon([(cx - L * .8, cy - L * .14), (cx - L * 1.5, cy - L * .2), (cx - L * 1.5, cy + L * .1), (cx - L * .8, cy + L * .1)], fill=col)
    # far wing (behind body), near wing (front)
    def wing(sign, lift, far):
        a0 = (cx + L * .1, cy - L * .12)
        tipx = cx - L * .5 + lift * 0 + L * (.25 - .35 * abs(lift)); tipy = cy - lift * L * 2.0 - (0 if lift else 0)
        spread = L * 1.9
        tip = (cx - L * .35 + L * .2 * (1 - abs(lift)), cy - lift * spread * (1 if not far else .92))
        mid_up = (cx + L * .05, cy - lift * L * 1.0 - L * .55 * (1 - abs(lift)))
        pts = [a0, (cx + L * .55, cy - lift * L * .9 - L * .1), tip, (cx - L * .55, cy - lift * L * 1.1 + L * .05), (cx - L * .55, cy + L * .08)]
        d.polygon(pts, fill=wing_col if not far else shade)
        if kind != "raven":
            for q in range(4):   # primaries
                fx = cx - L * (.1 + q * .22); fy = cy - lift * spread * (.92 - q * .08)
                d.line([(fx + L * .1, cy - lift * L * .6), (fx, fy)], fill=shade if kind == "dove" else wing_col, width=int(3 * S))
    wing(1, fl * .85 if fl > 0 else fl * .85, True)
    # body
    d.ellipse([cx - L, cy - L * .36, cx + L * .85, cy + L * .38], fill=col)
    d.ellipse([cx - L * .5, cy + L * .02, cx + L * .55, cy + L * .4], fill=shade)
    # head + beak + eye
    hx, hy = cx + L * .95, cy - L * .1
    d.ellipse([hx - L * .3, hy - L * .28, hx + L * .3, hy + L * .28], fill=col)
    bl = {"dove": .3, "swallow": .2, "raven": .5}[kind]
    d.polygon([(hx + L * .26, hy - L * (.1 if kind != "raven" else .14)), (hx + L * (.26 + bl), hy + L * .03), (hx + L * .26, hy + L * (.1 if kind != "raven" else .16))], fill=(236, 170, 70) if kind == "dove" else (30, 28, 36))
    if kind == "swallow": d.ellipse([hx + L * .05, hy + L * .02, hx + L * .3, hy + L * .22], fill=(190, 70, 52))
    d.ellipse([hx + L * .08, hy - L * .12, hx + L * .2, hy], fill=(10, 10, 14) if kind == "dove" else (230, 230, 240))
    wing(1, fl * .85, False)
    im = im.resize((w // S, h // S), Image.LANCZOS)
    return im


@lru_cache(None)
def _bird_frames(kind, n=12, size=330):
    return [_bird_sprite(kind, k / n, size) for k in range(n)]


def _bird_path(kind, u):
    """u = seconds since release. returns (x, y, angle_deg, scale, flap_rate)"""
    if kind == "dove":
        x = 360 + 700 * u * .62 + 40 * u * u; y = 1130 - 360 * u * .95 + 120 * math.sin(u * 2.2) * 0 - 60 * math.sin(u * 3.0)
        return x, y, -math.degrees(math.atan2(380 + 110 * math.cos(u * 3.0), 520)) * .8, 1.0 - .04 * u, 2.6
    if kind == "swallow":
        x = 380 + 880 * u * .72; y = 1100 - 210 * u * .6 + 190 * math.sin(u * 5.4) * (u / (u + .6)) - 120 * u
        return x, y, -math.degrees(math.atan2(-(190 * 5.4 * math.cos(u * 5.4)) * (u / (u + .6)) + 200 + 120, 640)), .8 - .05 * u, 4.4
    x = 340 + 330 * u * .75 + 200 * math.sin(u * 1.3); y = 1120 - 300 * u * .8 - 40 * math.sin(u * 2.4)
    return x, y, -math.degrees(math.atan2(260, 330 + 200 * math.cos(u * 1.3) * 1.3)) * .7, 1.25 - .03 * u, 1.9


def birds_scene(lt, t, release):
    """release: dict kind -> time (lt) when released"""
    bg = vgrad([(0, (28, 30, 66)), (520, (94, 66, 118)), (860, (214, 118, 118)), (1100, (250, 176, 128)), (1180, (250, 204, 148)), (H, (40, 34, 50))])
    bg += radial(780, 1130, 560, 2.0)[..., None] * np.array([90, 56, 20], np.float32)
    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    # soft clouds
    r = np.random.default_rng(9)
    for i in range(9):
        x = (r.uniform(0, W + 600) + t * r.uniform(8, 22)) % (W + 600) - 300; y = r.uniform(250, 1000)
        for j in range(5):
            rr = r.uniform(60, 150)
            d.ellipse([x + j * 70 - rr, y - rr * .3, x + j * 70 + rr, y + rr * .3], fill=(255, 214, 196, 26))
    # sea
    sea_y = 1180
    d.rectangle([0, sea_y, W, H], fill=(30, 40, 72, 255))
    for k in range(34):
        y = sea_y + 14 + k * 20 + (k % 3) * 4
        a = int(60 * (1 - k / 40))
        x0 = ((k * 137) % 400) - 200 + 30 * math.sin(t * .8 + k)
        for xx in range(int(x0), W + 200, 260):
            d.line([(xx, y), (xx + 90 + k * 2, y)], fill=(210, 190, 190, a), width=3)
    d.polygon([(0, sea_y - 2), (W, sea_y - 2), (W, sea_y + 14), (0, sea_y + 14)], fill=(250, 190, 140, 110))
    # the ark: hull + cabin with an open hatch, bobbing
    bob = 8 * math.sin(t * 1.3); tilt = 1.6 * math.sin(t * 1.0 + .5)
    ark = Image.new("RGBA", (900, 520), (0, 0, 0, 0)); ad = ImageDraw.Draw(ark)
    ad.polygon([(40, 250), (860, 250), (790, 420), (130, 420)], fill=(52, 34, 30, 255))
    ad.polygon([(40, 250), (860, 250), (850, 276), (50, 276)], fill=(86, 56, 40, 255))
    ad.rectangle([190, 110, 700, 250], fill=(66, 44, 34, 255)); ad.polygon([(160, 112), (730, 112), (640, 56), (250, 56)], fill=(78, 54, 40, 255))
    ad.rectangle([560, 150, 640, 206], fill=(20, 12, 12, 255)); ad.ellipse([548, 138, 650, 166], fill=(250, 200, 100, 120))
    for q in range(6): ad.line([(120 + q * 120, 296), (110 + q * 120, 400)], fill=(40, 26, 24, 255), width=4)
    ark = ark.rotate(tilt, center=(450, 300), resample=Image.BICUBIC)
    img.paste(ark.convert("RGB"), (-70, int(sea_y - 330 + bob)), ark.split()[3])
    # birds
    for kind in ("dove", "swallow", "raven"):
        if kind not in release or lt < release[kind]: continue
        u = lt - release[kind]
        x, y, ang, sc, rate = _bird_path(kind, u)
        fr = _bird_frames(kind)[int((u * rate * 12) % 12)]
        spr = fr.rotate(ang, expand=True, resample=Image.BICUBIC)
        spr = spr.resize((int(spr.width * sc), int(spr.height * sc)), Image.LANCZOS)
        # glow behind the dove
        if kind == "dove":
            gl = Image.new("RGBA", spr.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).ellipse([spr.width * .1, spr.height * .1, spr.width * .9, spr.height * .9], fill=(255, 236, 210, 60))
            g2 = gl.filter(ImageFilter.GaussianBlur(24)); img.paste(g2.convert("RGB"), (int(x - spr.width / 2), int(y - spr.height / 2)), g2.split()[3])
        a = ease(u / .2)
        if a < 1: spr.putalpha(spr.split()[3].point(lambda v: int(v * a)))
        img.paste(spr.convert("RGB"), (int(x - spr.width / 2), int(y - spr.height / 2)), spr.split()[3])
        # trail streaks
        for q in range(1, 5):
            xs_, ys_, _a, _s, _r = _bird_path(kind, max(0, u - q * .05))
            d2 = ImageDraw.Draw(img, "RGBA")
            d2.ellipse([xs_ - 4, ys_ - 4, xs_ + 4, ys_ + 4], fill=(255, 240, 220, int(80 - q * 16)))
    return np.asarray(img.convert("RGB"))
