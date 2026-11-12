#!/usr/bin/env python3
"""Illustrated-atlas terrain base builder, any region.

  python3 mapfx/build_terrain.py                      # Egypt/Sinai/Levant/Anatolia -> assets/terrain_base.png (paul_base drop-in)
  python3 mapfx/build_terrain.py mesopotamia          # preset
  python3 mapfx/build_terrain.py custom 38 50 28 40 200   # name lon0 lon1 lat0 lat1 [ppd]

Outputs per region <name>: assets/terrain_<name>.png, terrain_<name>_mask.npy (bool land), terrain_<name>_dem.npy (int16 m),
terrain_<name>.json (bounds, S0=px/deg lat, KX, BW, BH, zoom).  Projection: x=(lon-lon0)*KX*S0, y=(lat1-lat)*S0.
"""
import json, math, sys
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tiles

HERE = Path(__file__).resolve().parent.parent
A = HERE / "assets"

PRESETS = {  # name: (lon0, lon1, lat0, lat1, ppd, kx_lat)
    "base": (16.0, 42.0, 24.0, 48.5, 280, 36.5),          # identical grid to paul_base.png
    "mesopotamia": (38.0, 50.0, 28.0, 40.0, 280, None),
    "ararat": (38.0, 50.0, 36.0, 43.0, 320, None),
    "ethiopia": (32.0, 48.0, 3.0, 18.0, 260, None),
    "indian_ocean": (30.0, 100.0, -20.0, 30.0, 70, None),
}

# rough river courses (lat, lon) – hand-placed approximations
RIVERS = {
    "nile": [(15.6,32.55),(17.7,33.97),(19.5,33.3),(19.2,30.5),(21.8,31.3),(24.09,32.90),(24.98,32.87),(25.70,32.64),(26.16,32.72),(26.9,31.9),(27.18,31.19),(27.8,30.85),(28.10,30.75),(29.07,31.10),(29.6,31.25),(30.05,31.25),(30.2,31.2)],
    "rosetta": [(30.2,31.2),(30.5,31.0),(31.0,30.8),(31.45,30.40)],
    "damietta": [(30.2,31.2),(30.6,31.4),(31.0,31.45),(31.42,31.75)],
    "jordan": [(33.2,35.62),(32.85,35.6),(32.7,35.57),(32.3,35.55),(31.77,35.55),(31.75,35.5)],
    "orontes": [(34.5,36.5),(35.0,36.4),(35.6,36.3),(36.2,36.35),(36.15,36.0)],
    "euphrates": [(38.7,39.0),(37.6,38.5),(37.03,38.0),(36.82,38.0),(35.95,39.0),(35.33,40.15),(34.45,40.9),(33.64,42.8),(33.42,43.3),(33.35,43.78),(32.5,44.4),(31.05,46.25),(31.0,47.45),(30.5,47.8)],
    "tigris": [(38.4,39.8),(37.9,40.2),(37.33,42.2),(36.34,43.13),(35.3,43.5),(34.2,43.87),(33.3,44.4),(32.5,45.8),(31.85,47.15),(31.0,47.45)],
    "bluenile": [(11.6,37.4),(10.9,37.9),(10.4,37.4),(10.7,36.0),(11.3,35.2)],
}
RIVER_W = {"nile": 1.0, "rosetta": .8, "damietta": .8, "euphrates": .8, "tigris": .8, "jordan": .5, "orontes": .4, "bluenile": .5}
# inland lakes as ellipses (lat, lon, semi-lat, semi-lon)
LAKES = [(38.6,42.95,.22,.45,"van"), (37.7,45.4,.32,.45,"urmia"), (40.3,45.35,.14,.3,"sevan"), (32.82,35.59,.1,.05,"galilee"),
         (12.0,37.3,.2,.2,"tana")]
LAKE_LEVEL = {"van": 1648, "urmia": 1275, "sevan": 1900}
DEAD_SEA_BOX = (30.9, 32.0, 35.2, 35.8)  # dem < -330 → lake
CASPIAN_BOX = (36.0, 47.8, 46.0, 56.0)   # dem < -15 → sea

def chaikin(pts, it=3):
    p = np.array(pts, float)
    for _ in range(it):
        q = 0.75 * p[:-1] + 0.25 * p[1:]; r = 0.25 * p[:-1] + 0.75 * p[1:]
        p = np.vstack([p[:1], np.stack([q, r], 1).reshape(-1, 2), p[-1:]])
    return p

def fbm(shape, scales, weights, seed):
    rng = np.random.default_rng(seed); H, W = shape; acc = np.zeros(shape, np.float32)
    for s, w in zip(scales, weights):
        small = rng.random((H // s + 3, W // s + 3)).astype(np.float32)
        acc += cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC) * w
    return acc / sum(weights)

def lerp_ramp(v, stops):
    xs = np.array([s[0] for s in stops], np.float32); cs = np.array([s[1] for s in stops], np.float32)
    return np.stack([np.interp(v, xs, cs[:, k]) for k in range(3)], -1).astype(np.float32)

def smooth(a, lo, hi):
    t = np.clip((a - lo) / (hi - lo), 0, 1); return t * t * (3 - 2 * t)

def meta_path(name): return A / f"terrain_{name}.json"
def load_meta(name): return json.load(open(meta_path(name)))

def build(name, lon0, lon1, lat0, lat1, ppd=280, kx_lat=None, force=False, zoom=None):
    if meta_path(name).exists() and (A / f"terrain_{name}.png").exists() and not force:
        return load_meta(name)
    kx_lat = kx_lat if kx_lat is not None else (lat0 + lat1) / 2
    KX = math.cos(math.radians(kx_lat)); S0 = ppd
    BW, BH = int((lon1 - lon0) * KX * S0), int((lat1 - lat0) * S0)
    K = S0 / 280.0   # scale factor for all pixel-space radii
    z = zoom or tiles.choose_zoom(S0, (lat0 + lat1) / 2)
    print(f"[{name}] {BW}x{BH}px zoom {z}")
    def wpx(lat, lon): return (lon - lon0) * KX * S0, (lat1 - lat) * S0
    def blur(a, s): return cv2.GaussianBlur(a, (0, 0), max(s * K, .3))

    # ---- DEM reprojection
    xs_, ys_ = tiles.ensure(lon0, lon1, lat0, lat1, z)
    M = np.zeros((len(ys_) * 256, len(xs_) * 256), np.float32)
    for i, x in enumerate(xs_):
        for j, y in enumerate(ys_):
            im = np.asarray(Image.open(tiles.D / f"{z}_{x}_{y}.png").convert("RGB")).astype(np.float32)
            M[j*256:(j+1)*256, i*256:(i+1)*256] = im[..., 0] * 256 + im[..., 1] + im[..., 2] / 256 - 32768
    lon = lon0 + np.arange(BW, dtype=np.float64) / (KX * S0); lat = lat1 - np.arange(BH, dtype=np.float64) / S0
    mx = ((lon + 180) / 360 * 2**z - xs_[0]) * 256
    my = ((1 - np.arcsinh(np.tan(np.radians(lat))) / np.pi) / 2 * 2**z - ys_[0]) * 256
    MX = np.broadcast_to(mx.astype(np.float32)[None, :], (BH, BW)).copy()
    MY = np.broadcast_to(my.astype(np.float32)[:, None], (BH, BW)).copy()
    dem = cv2.remap(M, MX, MY, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE); del M, MX, MY
    latg = np.repeat(lat.astype(np.float32)[:, None], BW, 1); lonn = np.repeat(lon.astype(np.float32)[None, :], BH, 0)

    # ---- land mask (global coastline polygons) + lakes
    land_polys = json.load(open(A / "med.json"))
    im = Image.new("L", (BW, BH), 0); md = ImageDraw.Draw(im)
    for poly in land_polys:
        for ring_i, ring in enumerate(poly):
            pts = [wpx(la, lo) for lo, la in ring]
            md.polygon(pts, fill=255 if ring_i == 0 else 0)
    land = np.asarray(im) > 127
    def box(b, cond):
        la0, la1, lo0, lo1 = b
        m = np.zeros_like(land); m[(latg >= la0) & (latg <= la1) & (lonn >= lo0) & (lonn <= lo1)] = True
        return m & cond
    lake = box(DEAD_SEA_BOX, dem < -330)
    lake = cv2.morphologyEx(lake.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)) > 0
    for la, lo, sla, slo, _n in LAKES:
        cx, cy = wpx(la, lo)
        e = np.zeros((BH, BW), np.uint8)
        if -50 < cx < BW + 50 and -50 < cy < BH + 50:
            lvl = LAKE_LEVEL.get(_n)
            if lvl is not None:   # real shoreline: flat DEM at lake surface level inside a generous ellipse
                cv2.ellipse(e, (int(cx), int(cy)), (int(slo * 1.7 * KX * S0), int(sla * 1.7 * S0)), 0, 0, 360, 1, -1)
                lm_ = (e > 0) & (np.abs(dem - lvl) <= 14)
                lm_ = cv2.morphologyEx(lm_.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
                nlab, lab = cv2.connectedComponents(lm_)
                cl = lab[min(max(int(cy), 0), BH - 1), min(max(int(cx), 0), BW - 1)]
                if cl == 0:
                    ys_c, xs_c = np.nonzero(lm_); 
                    if len(ys_c): cl = lab[ys_c[np.argmin((ys_c - cy) ** 2 + (xs_c - cx) ** 2)], xs_c[np.argmin((ys_c - cy) ** 2 + (xs_c - cx) ** 2)]]
                if cl:
                    lake |= lab == cl; continue
            cv2.ellipse(e, (int(cx), int(cy)), (int(slo * KX * S0), int(sla * S0)), 0, 0, 360, 1, -1)
            lake |= e > 0
    cas = box(CASPIAN_BOX, dem < -15)
    land = (land & ~lake) & ~cas
    water = ~land
    lf = land.astype(np.float32)
    np.save(A / f"terrain_{name}_mask.npy", land); np.save(A / f"terrain_{name}_dem.npy", dem.astype(np.int16))
    elev = np.where(land, np.maximum(dem, 0), 0).astype(np.float32)

    # ---- hillshade
    print("shade...")
    dsm = np.where(land, cv2.GaussianBlur(dem, (0, 0), 1.2), 0).astype(np.float32)
    px_m = 111320 / S0
    ex = 8.0
    gy, gx = np.gradient(dsm * ex / px_m)
    slope = np.arctan(np.hypot(gx, gy)); aspect = np.arctan2(-gx, gy)
    def shade(az, alt):
        az = math.radians(az); al = math.radians(alt)
        return np.clip(np.cos(slope) * math.sin(al) + np.sin(slope) * math.cos(al) * np.cos(az - aspect), 0, 1)
    hs = shade(315, 38) * .5 + shade(270, 45) * .2 + shade(360, 45) * .2 + shade(225, 50) * .1
    hs -= math.sin(math.radians(38)) * .5 + math.sin(math.radians(45)) * .4 + math.sin(math.radians(50)) * .1
    rel = np.clip((dsm - blur(dsm, 14)) / 300, -1, 1)
    sdeg = np.degrees(slope)
    tex = fbm((BH, BW), [max(int(s * K), 2) for s in (96, 24, 6, 2)], [1, .8, .6, .5], 5)
    rng_ = fbm((BH, BW), [max(int(s * K), 2) for s in (48, 14, 5, 2)], [1, .7, .5, .35], 11)

    # ---- rivers / fertility
    print("climate...")
    def river_layer(names, w):
        im = Image.new("L", (BW, BH), 0); d = ImageDraw.Draw(im)
        for n in names:
            d.line([wpx(la, lo) for la, lo in chaikin(RIVERS[n])], fill=255, width=max(int(w * RIVER_W[n] * K), 1), joint="curve")
        return np.asarray(im).astype(np.float32) / 255
    thick = river_layer(RIVERS, 16)
    valley = np.clip(blur(thick, 5) * 1.8 + blur(thick, 22) * 1.6, 0, 1) * lf
    # Nile delta fan
    cx, cy = wpx(31.0, 31.0); dy, dx = np.mgrid[0:BH, 0:BW].astype(np.float32)
    delta = np.exp(-(((dx - cx) / (130 * K)) ** 2 + ((dy - cy) / (95 * K)) ** 2)) * (latg < 31.5)
    valley = np.clip(valley + delta * .9 * lf, 0, 1)
    # generic climate: arid belt around 15-32N (Sahara, Arabia, Iran interior), humid tropics & temperate north
    arid = np.exp(-((latg - 24.5) / 7.0) ** 2)
    arid = np.maximum(arid, smooth(lonn, 37.0, 39.0) * (1 - smooth(latg, 34.5, 37.0)) * smooth(latg, 20, 28) )  # Syrian/Arabian
    arid = np.maximum(arid, smooth(lonn, 40, 44) * (1 - smooth(latg, 36.5, 38.5)) * smooth(latg, 24, 31))     # Mesopotamian plain
    arid = np.maximum(arid, np.exp(-((latg - 17) / 5.0) ** 2) * (1 - smooth(elev, 1200, 2000)) * .7)        # Sahel / Danakil
    arid *= (1 - smooth(blur(elev, 20), 900, 1700) * .8)
    wet = np.clip(1 - arid, 0, 1)
    lev = np.exp(-(((latg - 33.0) / 2.2) ** 2 + ((lonn - 36.0) / 1.2) ** 2)) * smooth(elev, 100, 600)
    wet = np.clip(wet + lev * .8 - .1, 0, 1)
    wet *= 1 - smooth(elev, 1800, 2800)
    green = np.clip(wet * .85 + valley, 0, 1)

    # ---- land colour
    print("land...")
    e = cv2.GaussianBlur(elev, (0, 0), 1.0) + (rng_ - .5) * 50
    col = lerp_ramp(e, [(0, (218, 201, 158)), (150, (211, 190, 140)), (400, (198, 172, 118)), (800, (180, 152, 98)), (1300, (162, 134, 88)),
                        (1900, (172, 148, 112)), (2600, (208, 194, 170)), (3400, (238, 232, 220)), (5000, (252, 250, 246))])
    sand = np.array([232, 210, 150], np.float32); rock = np.array([168, 112, 74], np.float32)
    dm = arid * (1 - smooth(e, 900, 1800)) * (1 - valley)
    col = col * (1 - dm[..., None] * .6) + sand * dm[..., None] * .6
    steep = smooth(sdeg, 5, 26) * arid
    col = col * (1 - steep[..., None] * .5) + rock * steep[..., None] * .5
    gc = lerp_ramp(e, [(0, (146, 160, 86)), (600, (136, 150, 80)), (1500, (118, 132, 76))])
    gm = (green * .62 * (1 - smooth(e, 1800, 2800)))[..., None]
    col = col * (1 - gm) + gc * gm
    vm = (valley ** .75 * .8)[..., None]
    col = col * (1 - vm) + np.array([108, 146, 70], np.float32) * vm
    shade_m = np.clip(1 + hs * 1.9 + rel * .30, .4, 1.5)
    col *= shade_m[..., None]
    sh = np.clip(-hs * 2.0, 0, 1)[..., None]
    col = col * (1 - sh * .15) + np.array([60, 60, 96], np.float32) * sh * .15
    col *= (1 + (tex - .5) * .14)[..., None]
    inner = blur(lf, 12); edge = np.clip((1 - inner) * 1.5, 0, 1) * lf
    col *= (1 - .2 * edge)[..., None]
    col = np.clip(col, 0, 255)

    # ---- sea
    print("sea...")
    depth = np.maximum(cv2.GaussianBlur(np.where(water, -dem, 0).astype(np.float32), (0, 0), 2.0), 0)
    sea = lerp_ramp(depth, [(0, (96, 176, 164)), (40, (66, 150, 152)), (200, (40, 116, 132)), (700, (26, 86, 110)), (1800, (18, 62, 90)), (3500, (12, 42, 70)), (6000, (8, 30, 54))])
    sg = np.gradient(cv2.GaussianBlur(dem, (0, 0), 2.5) * 3.0 / px_m)
    sea *= (1 + np.clip(-(sg[0] + sg[1]) * -.5, -1, 1) * .25 * smooth(depth, 30, 400))[..., None]
    sea *= (.92 + (tex - .5) * .25)[..., None]
    lk = cv2.GaussianBlur(lake.astype(np.float32), (0, 0), 1.5)[..., None]
    sea = sea * (1 - lk) + np.array([60, 128, 134], np.float32) * lk
    dist = cv2.distanceTransform(water.astype(np.uint8), cv2.DIST_L2, 5) / K
    glow = np.exp(-dist / 24.0) * water
    sea += glow[..., None] * np.array([38, 58, 50], np.float32) * .8
    rip = sum(np.exp(-((dist - d0) / 2.2) ** 2) * a for d0, a in ((16, 1.0), (36, .7), (62, .45)))
    sea += (rip * water * 18)[..., None] * np.array([.8, 1.15, 1.15], np.float32)
    sea = np.clip(sea, 0, 255)

    lm = cv2.GaussianBlur(lf, (0, 0), .9)[..., None]
    img = col * lm + sea * (1 - lm)
    rl = blur(river_layer(RIVERS, 2.4), .8) * lf
    img = img * (1 - rl[..., None] * .8) + np.array([70, 132, 132], np.float32) * rl[..., None] * .8

    print("ink...")
    pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
    ov = Image.new("RGBA", pil.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    step = 2 if (lon1 - lon0) < 30 else 10
    for la in range(int(math.floor(lat0 / step) * step), int(lat1) + 1, step):
        y = (lat1 - la) * S0; d.line([(0, y), (BW, y)], fill=(255, 240, 200, 24), width=1)
    for lo in range(int(math.floor(lon0 / step) * step), int(lon1) + 1, step):
        x = (lo - lon0) * KX * S0; d.line([(x, 0), (x, BH)], fill=(255, 240, 200, 24), width=1)
    lw = max(int(round(3 * K)), 2)
    for poly in land_polys:
        for ring in poly:
            pts = [wpx(la, lo) for lo, la in ring]
            if max(p[0] for p in pts) < 0 or min(p[0] for p in pts) > BW or max(p[1] for p in pts) < 0 or min(p[1] for p in pts) > BH: continue
            d.line(pts, fill=(60, 42, 26, 215), width=lw, joint="curve")
    pil = Image.alpha_composite(pil, ov).convert("RGB")
    pil.save(A / f"terrain_{name}.png")
    meta = dict(name=name, lon0=lon0, lon1=lon1, lat0=lat0, lat1=lat1, S0=S0, KX=KX, kx_lat=kx_lat, BW=BW, BH=BH, zoom=z)
    json.dump(meta, open(meta_path(name), "w"), indent=1)
    return meta

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: a = ["base"]
    if a[0] in PRESETS and len(a) == 1:
        p = PRESETS[a[0]]; m = build(a[0], *p[:5], kx_lat=p[5], force=True)
    else:
        nm, lo0, lo1, la0, la1 = a[0], *map(float, a[1:5]); m = build(nm, lo0, lo1, la0, la1, float(a[5]) if len(a) > 5 else 280, force=True)
    print(m)
    out = HERE / "out/mapfx"; out.mkdir(parents=True, exist_ok=True)
    pil = Image.open(A / f"terrain_{m['name']}.png"); w = min(1600, pil.width)
    pil.resize((w, int(w * pil.height / pil.width)), Image.LANCZOS).save(out / f"terrain_{m['name']}_flat_1600.png")
