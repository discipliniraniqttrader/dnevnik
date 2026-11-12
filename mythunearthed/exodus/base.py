"""High-res regional base map for the Exodus Short (same look as paul_v2's base)."""
import json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
A = HERE.parent / "assets"
LON0, LON1, LAT0, LAT1 = 30.0, 38.0, 26.5, 33.5
KX = math.cos(math.radians(36.5))   # same projection as paul_v2
S0 = 750                            # px per degree of latitude (paul_v2 used 280)
BW, BH = int((LON1 - LON0) * KX * S0), int((LAT1 - LAT0) * S0)


def wpx(lat, lon):
    return (lon - LON0) * KX * S0, (LAT1 - lat) * S0


# lat, lon, label, solid?, label side
PLACES = {
    "rameses": (30.80, 31.83, "Rameses", True, "left"),
    "succoth": (30.55, 32.10, "Succoth", False, "left"),
    "etham": (30.45, 32.30, "Etham", False, "right"),
    "pihahiroth": (30.10, 32.50, "Pi-hahiroth", False, "right"),
    "crossing": (29.95, 32.55, "", False, "left"),
    "marah": (29.15, 32.95, "Marah", False, "left"),
    "elim": (28.95, 33.05, "Elim", False, "right"),
    "sin": (28.65, 33.45, "Wilderness of Sin", False, "left"),
    "rephidim": (28.70, 33.60, "Rephidim", False, "right"),
    "sinai": (28.54, 33.97, "Mount Sinai", False, "below"),
    "moab": (31.83, 35.63, "Plains of Moab", True, "right"),
}
ROUTE = ["rameses", "succoth", "etham", "pihahiroth", "crossing", "marah", "elim", "sin", "rephidim", "sinai"]


def chaikin(pts, it=2):
    for _ in range(it):
        out = []
        for a, b in zip(pts, pts[1:]):
            out += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        pts = [pts[0]] + out + [pts[-1]]
    return pts


def build_base():
    cache, mc = HERE / "ex_base.png", HERE / "ex_mask.npy"
    if cache.exists() and mc.exists():
        return Image.open(cache).convert("RGB"), np.load(mc)
    land = json.load(open(A / "med.json"))
    rings = []
    for poly in land:
        for k, ring in enumerate(poly):
            if any(LON0 - 1 < lo < LON1 + 1 and LAT0 - 1 < la < LAT1 + 1 for lo, la in ring):
                rings.append((k, chaikin([wpx(la, lo) for lo, la in ring], 2)))
    mask = Image.new("L", (BW, BH), 0)
    md = ImageDraw.Draw(mask)
    for k, r in rings:
        md.polygon(r, fill=255 if k == 0 else 0)
    # Dead Sea (approximate)
    dead = [(31.78, 35.52), (31.76, 35.57), (31.66, 35.58), (31.55, 35.58), (31.45, 35.57), (31.35, 35.55), (31.25, 35.53), (31.15, 35.52),
            (31.07, 35.48), (31.03, 35.42), (31.10, 35.39), (31.25, 35.40), (31.40, 35.42), (31.55, 35.45), (31.68, 35.48), (31.75, 35.49)]
    dp = [wpx(*q) for q in dead]
    dead_px = chaikin(dp + [dp[0]], 3)
    md.polygon(dead_px, fill=0)
    mask = mask.filter(ImageFilter.GaussianBlur(1.2))
    m = np.asarray(mask, np.float32) / 255
    rng = np.random.default_rng(3)

    def noise(scale, amp):
        small = rng.random((BH // scale + 2, BW // scale + 2)).astype(np.float32)
        return np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((BW, BH), Image.BICUBIC), np.float32) / 255 * amp

    tex = noise(170, 1) * .45 + noise(42, 1) * .3 + noise(10, 1) * .15 + noise(3, 1) * .10
    inner = np.asarray(mask.filter(ImageFilter.GaussianBlur(36)), np.float32) / 255
    parch = np.stack([np.full((BH, BW), c, np.float32) for c in (214, 196, 154)], -1)
    parch *= (0.86 + 0.18 * tex)[..., None]
    edge = np.clip((1 - inner) * 1.6, 0, 1) * m
    parch *= (1 - 0.30 * edge)[..., None]
    sea = np.stack([np.full((BH, BW), c, np.float32) for c in (16, 42, 52)], -1)
    sea *= (0.85 + 0.25 * tex)[..., None]
    outer = np.asarray(mask.filter(ImageFilter.GaussianBlur(58)), np.float32) / 255
    rip = np.zeros_like(outer)
    for lvl in (0.30, 0.17, 0.08):
        rip += np.exp(-((outer - lvl) / 0.012) ** 2)
    sea += (np.clip(rip, 0, 1) * (1 - m) * 26)[..., None] * np.array([0.8, 1.2, 1.2], np.float32)
    img = parch * m[..., None] + sea * (1 - m[..., None])
    base = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(base, "RGBA")
    for lat in np.arange(27, 34, 1.0):
        y = (LAT1 - lat) * S0
        d.line([(0, y), (BW, y)], fill=(90, 80, 60, 150), width=2)
    for lon in np.arange(31, 37, 1.0):
        x = (lon - LON0) * KX * S0
        d.line([(x, 0), (x, BH)], fill=(90, 80, 60, 150), width=2)
    # rivers (stylised, approximate)
    water = (30, 70, 80)
    def river(pts, w):
        px = chaikin([wpx(*p) for p in pts], 3)
        d.line(px, fill=(70, 52, 34), width=w + 4, joint="curve")
        d.line(px, fill=water, width=w, joint="curve")
    river([(26.5, 31.9), (27.2, 31.2), (28.1, 30.8), (29.1, 31.1), (30.05, 31.25)], 9)
    river([(30.05, 31.25), (30.5, 31.30), (31.0, 31.60), (31.42, 31.81)], 8)
    river([(30.15, 31.18), (30.8, 30.90), (31.46, 30.36)], 8)
    river([(32.70, 35.57), (32.3, 35.56), (31.95, 35.54), (31.78, 35.52)], 6)
    # hill marks over southern Sinai
    inky = (92, 66, 40, 200)
    hr = np.random.default_rng(11)
    for _ in range(420):
        la, lo = hr.uniform(27.6, 29.3), hr.uniform(33.3, 34.6)
        if la > 29.3 - (lo - 33.3) * 0.0 and False:
            continue
        x, y = wpx(la, lo)
        if m[int(y), int(x)] < 0.5 or inner[int(y), int(x)] < 0.8:
            continue
        if any(math.dist((x, y), wpx(PLACES[k][0], PLACES[k][1])) < 95 for k in PLACES):
            continue
        s = hr.uniform(14, 26)
        d.line([(x - s, y + s * .6), (x, y - s * .6), (x + s, y + s * .6)], fill=inky, width=3, joint="curve")
        d.line([(x, y - s * .6), (x + s * .35, y + s * .6)], fill=(92, 66, 40, 110), width=2)
    # ink coastline
    for k, r in rings:
        d.line(r, fill=(70, 52, 34), width=5, joint="curve")
    d.line(dead_px, fill=(70, 52, 34), width=5, joint="curve")
    # map labels
    ital = ImageFont.truetype(str(A / "serif-bold.ttf"), 44)
    def lab(lat, lon, txt, col, ang=0):
        im = Image.new("RGBA", (700, 90), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((350, 45), txt, font=ital, fill=col, anchor="mm")
        im = im.rotate(ang, Image.BICUBIC, expand=True)
        x, y = wpx(lat, lon)
        base.paste(im, (int(x - im.width / 2), int(y - im.height / 2)), im)
    lab(32.55, 32.4, "Mediterranean Sea", (120, 170, 180, 190))
    lab(29.55, 32.05, "Gulf of Suez", (120, 90, 55, 220), 0)
    lab(29.05, 34.75, "Gulf of Aqaba", (120, 90, 55, 220), 0)
    lab(31.35, 35.98, "Dead Sea", (120, 90, 55, 220), 0)
    lab(29.3, 31.35, "EGYPT", (130, 100, 60, 150))
    lab(30.0, 34.35, "SINAI", (130, 100, 60, 130))
    lab(28.0, 31.2, "Nile", (60, 110, 120, 200), 70)
    base.save(cache)
    np.save(mc, m > 0.5)
    return base, m > 0.5


if __name__ == "__main__":
    b, m = build_base()
    print(b.size)
    for k, (la, lo, *_r) in PLACES.items():
        x, y = wpx(la, lo)
        print(k, "land" if m[int(y), int(x)] else "SEA")


def snapped_places(m):
    """World-pixel positions for markers; places that fall in coarse-coastline water are nudged to nearest land."""
    cache = HERE / "snapped.json"
    if cache.exists():
        return {k: tuple(v) for k, v in json.load(open(cache)).items()}
    out = {}
    R = 320
    for k, (la, lo, *_r) in PLACES.items():
        x, y = wpx(la, lo)
        ix, iy = int(x), int(y)
        win = Image.fromarray((m[iy - R:iy + R, ix - R:ix + R] * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(61))
        cand = np.asarray(win) > 0
        if k not in ("crossing", "moab") and not cand[R, R]:
            ys, xs = np.nonzero(cand)
            j = np.argmin((xs - R) ** 2 + (ys - R) ** 2)
            x, y = float(ix - R + xs[j]), float(iy - R + ys[j])
        out[k] = (x, y)
    json.dump(out, open(cache, "w"))
    return out
