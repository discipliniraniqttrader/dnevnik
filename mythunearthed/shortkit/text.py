"""TEXT shots: quote, word_shatter, glow_word, big_number."""
import math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
from .common import W, H, F, ease, out_back, vgrad, radial, fit_font, to_img
from . import ev_noah as EN


def _dust(arr, t, n=70, seed=2, col=(255, 214, 150)):
    r = np.random.default_rng(seed); p = np.zeros((H, W, 3), np.uint8)
    for i in range(n):
        x = (r.uniform(0, W) + t * r.uniform(-10, 14)) % W; y = (r.uniform(0, H) - t * r.uniform(5, 26)) % H
        al = (.4 + .6 * math.sin(t * 1.6 + i) ** 2) * .8
        cv2.circle(p, (int(x), int(y)), int(r.uniform(1, 3)), tuple(int(c * al) for c in col), -1, cv2.LINE_AA)
    return arr + p * .6


def quote_scene(lt, dur, t, text, attribution=""):
    bg = vgrad([(0, (18, 14, 26)), (900, (40, 30, 44)), (H, (14, 10, 18))]) + radial(540, 820, 900, 1.8)[..., None] * np.array([46, 32, 14], np.float32)
    ang = np.arctan2(*(np.mgrid[0:H, 0:W].astype(np.float32) - np.array([200, 540], np.float32)[:, None, None]))
    bg += ((np.sin(ang * 9 + t * .18) * .5 + .5) ** 3 * radial(540, 200, 1300, 1.4) * .22)[..., None] * np.array([120, 90, 40], np.float32)
    bg = _dust(bg, t)
    pil = to_img(bg).convert("RGBA")
    f, lines = fit_font("serif-bold.ttf", text, 900, 760, 96, 44, 1.2)
    words = [w for ln in lines for w in ln.split()]
    nw = len(words); span = max(dur * .72, .8)
    d = ImageDraw.Draw(pil)
    qa = ease((lt - .05) / .4)
    d.text((150, 500), "“", font=F("serif-bold.ttf", 260), fill=(232, 170, 40, int(255 * qa)), anchor="mm")
    y = 830 - (len(lines) - 1) * f.size * 1.2 / 2
    k = 0
    for ln in lines:
        ws = ln.split(); total = sum(f.getlength(w + " ") for w in ws) - f.getlength(" ")
        x = 540 - total / 2
        for w in ws:
            ti = .15 + span * k / max(nw, 1); a = ease((lt - ti) / .28)
            if a > 0:
                last = lt < ti + span / max(nw, 1) * 1.6 and k < nw - 1
                col = (255, 214, 120) if last else (246, 236, 210)
                d.text((x, y + (1 - a) * 22), w, font=f, fill=col + (int(255 * a),), anchor="lm", stroke_width=4, stroke_fill=(10, 8, 6, int(255 * a)))
            x += f.getlength(w + " "); k += 1
        y += f.size * 1.2
    if attribution:
        aa = ease((lt - span * .5) / .5)
        d.line([(340, 1250), (740, 1250)], fill=(232, 170, 40, int(255 * aa)), width=4)
        d.text((540, 1300), attribution.upper()[:40], font=F("sans-semi.ttf", 44), fill=(236, 214, 150, int(255 * aa)), anchor="mm", stroke_width=3, stroke_fill=(10, 8, 6, int(255 * aa)))
    return np.asarray(pil.convert("RGB"))


def big_number_scene(lt, dur, t, number, unit="", decimals=0):
    bg = vgrad([(0, (10, 12, 26)), (900, (24, 22, 46)), (H, (8, 8, 18))]) + radial(540, 860, 760, 1.7)[..., None] * np.array([70, 48, 12], np.float32)
    ang = np.arctan2(*(np.mgrid[0:H, 0:W].astype(np.float32) - np.array([860, 540], np.float32)[:, None, None]))
    bg += ((np.sin(ang * 14 + t * .3) * .5 + .5) ** 3 * radial(540, 860, 900, 1.3) * .22)[..., None] * np.array([120, 90, 30], np.float32)
    bg = _dust(bg, t, 90, 4)
    pil = to_img(bg).convert("RGBA"); d = ImageDraw.Draw(pil)
    run = max(dur * .62, .7)
    p = ease(lt / run) ** .85
    val = number * p
    txt = f"{val:,.{decimals}f}" if decimals else f"{int(round(val)):,}"
    full = f"{number:,.{decimals}f}" if decimals else f"{int(round(number)):,}"
    size = 300
    while size > 90 and F("sans-black.ttf", size).getlength(full) > 940: size -= 8
    pop = 1 + .10 * max(0, 1 - (lt - run) / .3) if lt >= run else 1.0
    # fixed-width digits so the number does not jitter: draw right-aligned in a box centered on the final width
    f = F("sans-black.ttf", int(size * pop))
    fw = F("sans-black.ttf", size).getlength(full)
    d.text((540 + fw * pop / 2, 860), txt, font=f, fill=(255, 244, 222), anchor="rm", stroke_width=14, stroke_fill=(24, 12, 8))
    ring = ease((lt - run) / .6)
    if 0 < ring < 1:
        r = 200 + 520 * ring; d.ellipse([540 - r, 860 - r * .45, 540 + r, 860 + r * .45], outline=(255, 214, 120, int(180 * (1 - ring))), width=6)
    if unit:
        u = ease((lt - .2) / .5)
        f2, lines = fit_font("sans-black.ttf", unit.upper(), 940, 200, 96, 44)
        for i, ln in enumerate(lines):
            d.text((540, 1090 + i * f2.size * 1.1), ln, font=f2, fill=(244, 188, 60, int(255 * u)), anchor="mm", stroke_width=9, stroke_fill=(24, 12, 8, int(255 * u)))
    # progress bar
    bw = 700 * p
    d.rounded_rectangle([190, 1250, 890, 1274], 12, fill=(255, 255, 255, 40)); d.rounded_rectangle([190, 1250, 190 + bw, 1274], 12, fill=(232, 170, 40, 255))
    return np.asarray(pil.convert("RGB"))


def render(c):
    """c: scene context (SimpleNamespace) with lt, dur, t, b (beat), tm (times dict)"""
    b = c.b; k = b["kind"]
    if k == "quote":
        return quote_scene(c.lt, c.dur, c.t, b["display"], b["source"] if b.get("source") not in (None, "-") else "")
    if k == "big_number":
        dec = 1 if (b["number"] % 1) else 0
        return big_number_scene(c.lt, c.dur, c.t, b["number"], b.get("unit") or "", dec)
    if k == "glow_word":
        return EN.glow_scene(c.lt, c.dur, c.t, b["display"], c.tm["t_text"], c.tm["t_dis"])
    # word_shatter
    import re
    word = b["display"].upper()
    ctx = b["source"] if re.search(r"[A-Za-z]+\.? \d+[:.]\d+", b.get("source") or "") else None
    peaks = bool(re.search(r"MOUNT|PEAK|HILL|ARARAT|SINAI", word))
    return EN.shatter_scene(c.lt, c.t, c.tm["t_quote"], c.tm["t_word"], c.tm["t_shatter"], c.tm["t_peaks_end"], word, ctx, peaks, b.get("after"))
