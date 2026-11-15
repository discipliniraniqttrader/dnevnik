"""Shared constants + small drawing helpers for shortkit (1080x1920, 30 fps)."""
import math
from functools import lru_cache
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
ROOT = Path(__file__).resolve().parent.parent          # /home/user/zenit
ASSETS = ROOT / "assets"
GOLD, CREAM, INK = (232, 170, 40), (246, 236, 210), (10, 8, 6)
INTER_BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
MONT_BLACK = "montserrat-black.ttf"               # assets/ (Montserrat Black, latin)
KW_GOLD = (255, 196, 46)


def ease(x):
    x = max(0.0, min(1.0, float(x))); return x * x * (3 - 2 * x)


def out_back(x, s=1.9):
    x = max(0.0, min(1.0, float(x))) - 1; return 1 + (s + 1) * x ** 3 + s * x ** 2


def lerp(a, b, u): return a + (b - a) * u


@lru_cache(None)
def F(name, size):
    p = Path(name)
    if not p.is_absolute(): p = ASSETS / name
    return ImageFont.truetype(str(p), int(size))


def cap_font(word, size=76):
    """Black sans; Inter Black for words with glyphs outside Latin-1 (ğ ş ı ...)."""
    if any(ord(c) > 255 for c in word): return F(INTER_BLACK, size)
    return F("sans-black.ttf", size)


def big_font(word, size=110):
    """Viral-caption face: Montserrat Black; Inter Black for glyphs Montserrat-latin lacks (ğ ş ı ...)."""
    if any(ord(c) > 255 and c not in "’‘“”–—…" for c in word): return F(INTER_BLACK, size)
    return F(MONT_BLACK, size)


def vgrad(stops, h=H, w=W):
    ys = np.arange(h, dtype=np.float32)
    pos = np.array([s[0] for s in stops], np.float32); cols = np.array([s[1] for s in stops], np.float32)
    col = np.stack([np.interp(ys, pos, cols[:, k]) for k in range(3)], -1)
    return np.broadcast_to(col[:, None, :], (h, w, 3)).copy()


@lru_cache(64)
def radial(cx, cy, r, power=2.0, h=H, w=W):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    return np.clip(1 - np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r, 0, 1) ** power


def fbm(h, w, scales, weights, seed, wrap_x=False):
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
    lo, hi = np.percentile(acc, [3, 97]); return np.clip((acc - lo) / (hi - lo + 1e-9), 0, 1)


def to_img(arr): return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def ridge(x, t, comps, base, speed):
    y = np.full_like(x, base, dtype=np.float32)
    for amp, per, ph in comps:
        y += amp * np.sin(2 * np.pi * (x + t * speed) / per + ph)
    return y


def text_outline(d, xy, s, font, fill, stroke=8, stroke_fill=INK, anchor="mm"):
    d.text(xy, s, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)


def wrap_text(s, font, maxw):
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if font.getlength(t) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


def fit_font(name, text, maxw, maxh, start, minimum=34, line_gap=1.12):
    """Largest font size (<= start) so wrapped text fits maxw x maxh. returns (font, lines)"""
    size = start
    while size >= minimum:
        f = F(name, size); lines = wrap_text(text, f, maxw)
        if len(lines) * size * line_gap <= maxh and max(f.getlength(l) for l in lines) <= maxw: return f, lines
        size -= 4
    f = F(name, minimum); return f, wrap_text(text, f, maxw)
