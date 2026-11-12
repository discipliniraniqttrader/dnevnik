#!/usr/bin/env python3
"""The Journeys of Paul — v2 (English, narrated, camera moves, captions, music).

python3 paul_v2.py                 # full render -> out/paul_v2.mp4
python3 paul_v2.py --frames 3,12   # preview PNG frames at these seconds
"""
import json
import math
import multiprocessing as mp
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
A, OUT = HERE / "assets", HERE / "out"
W, H, FPS = 1080, 1920, 30
SR = 24000
VOICE = "am_michael"

# ------------------------------------------------------------------ data
CITIES = {
    "antioch": (36.20, 36.16, "Antioch"), "seleucia": (36.12, 35.92, "Seleucia"), "salamis": (35.18, 33.90, "Salamis"),
    "paphos": (34.76, 32.41, "Paphos"), "perga": (36.96, 30.85, "Perga"), "attalia": (36.89, 30.70, "Attalia"),
    "pisantioch": (38.31, 31.19, "Pisidian Antioch"), "iconium": (37.87, 32.48, "Iconium"), "lystra": (37.58, 32.45, "Lystra"),
    "derbe": (37.35, 33.37, "Derbe"), "tarsus": (36.92, 34.89, "Tarsus"), "troas": (39.75, 26.16, "Troas"),
    "samothrace": (40.48, 25.53, "Samothrace"), "neapolis": (40.94, 24.41, "Neapolis"), "philippi": (41.01, 24.29, "Philippi"),
    "amphipolis": (40.82, 23.85, "Amphipolis"), "thessalonica": (40.64, 22.94, "Thessalonica"), "berea": (40.52, 22.20, "Berea"),
    "athens": (37.98, 23.73, "Athens"), "corinth": (37.91, 22.88, "Corinth"), "cenchreae": (37.88, 22.99, "Cenchreae"),
    "ephesus": (37.94, 27.34, "Ephesus"), "caesarea": (32.50, 34.89, "Caesarea"), "jerusalem": (31.78, 35.23, "Jerusalem"),
    "assos": (39.49, 26.34, "Assos"), "mitylene": (39.11, 26.56, "Mitylene"), "chios": (38.37, 26.14, "Chios"),
    "samos": (37.69, 26.94, "Samos"), "miletus": (37.53, 27.28, "Miletus"), "cos": (36.89, 27.29, "Cos"),
    "rhodes": (36.43, 28.22, "Rhodes"), "patara": (36.26, 29.32, "Patara"), "tyre": (33.27, 35.20, "Tyre"),
    "ptolemais": (32.93, 35.08, "Ptolemais"),
}
LABEL = {"antioch", "salamis", "paphos", "perga", "pisantioch", "iconium", "lystra", "derbe", "tarsus", "troas", "philippi",
         "thessalonica", "berea", "athens", "corinth", "ephesus", "caesarea", "jerusalem", "miletus", "rhodes", "tyre"}
LABEL_SIDE = {"lystra": "left", "paphos": "left", "berea": "below", "corinth": "below", "caesarea": "left", "thessalonica": "above", "jerusalem": "left",
              "rhodes": "left", "derbe": "below", "tarsus": "above", "pisantioch": "above", "perga": "below", "antioch": "left"}
JOURNEYS = [
    {"color": (232, 170, 40), "title": "JOURNEY 1", "meta": "c. AD 46–48 · ACTS 13–14",
     "route": ["antioch", "seleucia", "salamis", "paphos", "perga", "pisantioch", "iconium", "lystra", "derbe",
               "lystra", "iconium", "pisantioch", "perga", "attalia", "antioch"]},
    {"color": (226, 74, 62), "title": "JOURNEY 2", "meta": "c. AD 49–52 · ACTS 15–18",
     "route": ["antioch", "tarsus", "derbe", "lystra", "iconium", "pisantioch", "troas", "samothrace", "neapolis",
               "philippi", "amphipolis", "thessalonica", "berea", "athens", "corinth", "cenchreae", "ephesus",
               "caesarea", "jerusalem", "antioch"]},
    {"color": (70, 140, 230), "title": "JOURNEY 3", "meta": "c. AD 53–57 · ACTS 18–21",
     "route": ["antioch", "tarsus", "derbe", "lystra", "iconium", "pisantioch", "ephesus", "troas", "philippi",
               "corinth", "philippi", "troas", "assos", "mitylene", "chios", "samos", "miletus", "cos", "rhodes",
               "patara", "tyre", "ptolemais", "caesarea", "jerusalem"]},
]
WIDE = (36.4, 29.3, 23.5)
# text, journey, route index to reach, camera (lat, lon, degrees visible vertically), event (city, label)
BEATS = [
    ("One man. Over nine thousand kilometers, on foot and by sea.", None, None, WIDE, None),
    ("Around A.D. 46, Paul sets out from Antioch with Barnabas, and sails for Cyprus.", 0, 3, (35.6, 33.9, 7.5), None),
    ("From there, into the highlands of Galatia.", 0, 6, (37.3, 32.2, 5.5), None),
    ("At Lystra, a mob stones him, and drags him out of the city, leaving him for dead.", 0, 7, (37.6, 32.5, 3.6), ("lystra", "STONED")),
    ("He gets up, and goes back the way he came.", 0, 14, (36.6, 33.3, 9.0), None),
    ("On his second journey, a vision calls him to Macedonia.", 1, 6, (38.3, 31.2, 15.0), None),
    ("For the first time, the gospel crosses into Europe.", 1, 9, (40.3, 25.4, 5.5), None),
    ("In Philippi, he is beaten, and thrown into prison.", 1, 9, (40.95, 24.3, 3.6), ("philippi", "IMPRISONED")),
    ("Then Thessalonica, Athens, and Corinth, where he stays a year and a half.", 1, 14, (39.2, 23.3, 6.5), ("corinth", "18 MONTHS")),
    ("Then back across the sea, home to Antioch.", 1, 19, (35.4, 31.6, 14.0), None),
    ("His third journey leads to Ephesus, where he teaches for nearly three years.", 2, 6, (37.6, 31.5, 15.0), ("ephesus", "3 YEARS")),
    ("Then Macedonia and Greece, once more.", 2, 10, (39.4, 25.0, 7.5), None),
    ("Finally, he sails for Jerusalem, knowing that chains are waiting for him.", 2, 23, (35.2, 32.0, 14.0), ("jerusalem", "CHAINS AWAIT")),
    ("Nine thousand kilometers, as the crow flies. The real road was far longer.", "all", None, WIDE, None),
    ("Which journey should we map next?", "all", None, WIDE, None),
]

# ------------------------------------------------------------------ base map (world space)
LON0, LON1, LAT0, LAT1 = 16.0, 42.0, 24.0, 48.5
KX = math.cos(math.radians(36.5))
S0 = 280  # base pixels per degree of latitude
BW, BH = int((LON1 - LON0) * KX * S0), int((LAT1 - LAT0) * S0)


def wpx(lat, lon):
    return (lon - LON0) * KX * S0, (LAT1 - lat) * S0


def build_base():
    cache = A / "paul_base.png"
    mcache = A / "paul_mask.npy"
    if cache.exists() and mcache.exists():
        return Image.open(cache).convert("RGB"), np.load(mcache)
    land = json.load(open(A / "med.json"))
    mask = Image.new("L", (BW, BH), 0)
    md = ImageDraw.Draw(mask)
    for poly in land:
        md.polygon([wpx(lat, lon) for lon, lat in poly[0]], fill=255)
        for hole in poly[1:]:
            md.polygon([wpx(lat, lon) for lon, lat in hole], fill=0)
    m = np.asarray(mask, dtype=np.float32) / 255
    rng = np.random.default_rng(3)

    def noise(scale, amp):
        small = rng.random((BH // scale + 2, BW // scale + 2)).astype(np.float32)
        return np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((BW, BH), Image.BICUBIC), dtype=np.float32) / 255 * amp

    tex = noise(64, 1) * .5 + noise(16, 1) * .3 + noise(4, 1) * .2
    # parchment land with darker edges toward coast
    inner = np.asarray(mask.filter(ImageFilter.GaussianBlur(14)), dtype=np.float32) / 255
    parch = np.stack([np.full((BH, BW), c, np.float32) for c in (214, 196, 154)], -1)
    parch *= (0.86 + 0.18 * tex)[..., None]
    edge = np.clip((1 - inner) * 1.6, 0, 1) * m
    parch *= (1 - 0.30 * edge)[..., None]
    # sea: deep teal with texture and coastal ripple lines
    sea = np.stack([np.full((BH, BW), c, np.float32) for c in (16, 42, 52)], -1)
    sea *= (0.85 + 0.25 * tex)[..., None]
    outer = np.asarray(mask.filter(ImageFilter.GaussianBlur(22)), dtype=np.float32) / 255
    rip = np.zeros_like(outer)
    for lvl in (0.30, 0.17, 0.08):
        rip += np.exp(-((outer - lvl) / 0.012) ** 2)
    sea += (np.clip(rip, 0, 1) * (1 - m) * 26)[..., None] * np.array([0.8, 1.2, 1.2], np.float32)
    img = parch * m[..., None] + sea * (1 - m[..., None])
    base = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(base)
    # graticule
    for lat in range(28, 46, 2):
        y = (LAT1 - lat) * S0
        d.line([(0, y), (BW, y)], fill=(90, 80, 60), width=1)
    for lon in range(18, 41, 2):
        x = (lon - LON0) * KX * S0
        d.line([(x, 0), (x, BH)], fill=(90, 80, 60), width=1)
    # ink coastline
    for poly in land:
        for ring in poly:
            d.line([wpx(lat, lon) for lon, lat in ring], fill=(70, 52, 34), width=3)
    base.save(cache)
    np.save(mcache, m > 0.5)
    return base, m > 0.5


# ------------------------------------------------------------------ narration + timing
def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def narrate():
    from kokoro_onnx import Kokoro
    k = Kokoro(str(A / "kokoro/model.onnx"), str(A / "kokoro/voices.npz"))
    clips, beats, t = [], [], 0.6
    for i, (text, *_rest) in enumerate(BEATS):
        a, sr = k.create(text, voice=VOICE, speed=1.04, lang="en-us" if VOICE.startswith("a") else "en-gb")
        assert sr == SR
        a = a / (np.max(np.abs(a)) + 1e-6) * 0.89
        dur = len(a) / SR
        hold = 0.25 if i < len(BEATS) - 2 else 0.7
        if i == len(BEATS) - 1:
            hold = 2.2
        beats.append({"t0": t, "speech": dur, "t1": t + dur + hold})
        clips.append((t, a))
        t += dur + hold
    total = t
    voice = np.zeros(int(total * SR) + SR, np.float32)
    for t0, a in clips:
        i = int(t0 * SR)
        voice[i:i + len(a)] += a
    return voice[: int(total * SR)], beats, total


def word_times(text, t0, dur):
    words = text.split()
    weights = [len(w.strip(",.")) + (3 if w.endswith((",", ".")) else 0) + 2 for w in words]
    tot = sum(weights)
    out, t = [], t0
    for w, wt in zip(words, weights):
        d = dur * wt / tot
        out.append((w, t, t + d))
        t += d
    return out


def music(total, sea_spans):
    n = int(total * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    chords = [(146.83, 174.61, 220.0), (116.54, 146.83, 174.61), (130.81, 164.81, 196.0), (110.0, 130.81, 164.81)]  # Dm Bb C Am
    seg = 4.0
    for ci in range(int(total / seg) + 1):
        f = chords[ci % 4]
        s0 = ci * seg
        idx = (t >= s0 - .5) & (t < s0 + seg + 1.5)
        tt = t[idx] - s0
        env = np.clip(tt / 1.2, 0, 1) * np.clip((seg + 1.5 - tt) / 1.6, 0, 1)
        sig = np.zeros_like(tt)
        for fr in f:
            for det in (-0.6, 0.6):
                sig += np.sin(2 * np.pi * (fr + det) * tt) * .5 + np.sin(2 * np.pi * (fr * 2 + det) * tt) * .12
        sig += np.sin(2 * np.pi * f[0] / 2 * tt) * .8
        out[idx] += (sig * env).astype(np.float32)
    out /= np.max(np.abs(out)) + 1e-6
    out *= 0.10
    fade = np.clip(t / 1.5, 0, 1) * np.clip((total - t) / 2.0, 0, 1)
    out *= fade
    # sea: low-passed noise swells during sea crossings
    rng = np.random.default_rng(1)
    nz = rng.standard_normal(n).astype(np.float32)
    k = np.ones(400, np.float32) / 400
    nz = np.convolve(nz, k, mode="same")
    nz /= np.max(np.abs(nz)) + 1e-6
    swell = (0.6 + 0.4 * np.sin(2 * np.pi * t / 3.1)) * 0.07
    gate = np.zeros(n, np.float32)
    for a, b in sea_spans:
        gate += np.clip((t - a) / .6, 0, 1) * np.clip((b - t) / .8, 0, 1)
    out += nz * swell * np.clip(gate, 0, 1)
    return out


# ------------------------------------------------------------------ timeline
def build_timeline(beats, mask):
    """Route progress keyframes per journey + camera keyframes."""
    for j in JOURNEYS:
        pts = [CITIES[c] for c in j["route"]]
        j["seg"] = [math.dist(wpx(*pts[i][:2]), wpx(*pts[i + 1][:2])) for i in range(len(pts) - 1)]
        j["km"] = [haversine(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
        j["cum"] = np.concatenate([[0], np.cumsum(j["seg"])])
        j["sea"] = []
        for i in range(len(pts) - 1):
            a, b = wpx(*pts[i][:2]), wpx(*pts[i + 1][:2])
            samples = [mask[int(a[1] + (b[1] - a[1]) * f), int(a[0] + (b[0] - a[0]) * f)] for f in np.linspace(.15, .85, 15)]
            j["sea"].append(sum(1 for s in samples if not s) > 8)
        j["keys"] = [(0.0, 0.0)]
    cams = []
    sea_spans = []
    for b, (text, jn, idx, cam, ev) in zip(beats, BEATS):
        cams.append((b["t0"], cam))
        if isinstance(jn, int):
            j = JOURNEYS[jn]
            prev_t, prev_d = j["keys"][-1]
            target = j["cum"][idx]
            start = b["t0"] + 0.2
            end = max(start + 1.0, b["t0"] + b["speech"])
            if target > prev_d:
                if prev_t < start:
                    j["keys"].append((start, prev_d))
                j["keys"].append((end, target))
                # sea spans for the ambience
                for si in range(len(j["seg"])):
                    if j["sea"][si] and j["cum"][si + 1] > prev_d and j["cum"][si] < target:
                        fa = (max(j["cum"][si], prev_d) - prev_d) / (target - prev_d)
                        fb = (min(j["cum"][si + 1], target) - prev_d) / (target - prev_d)
                        sea_spans.append((start + fa * (end - start), start + fb * (end - start)))
    return cams, sea_spans


def haversine(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def progress(j, t):
    keys = j["keys"]
    if t <= keys[0][0]:
        return keys[0][1]
    for (ta, da), (tb, db) in zip(keys, keys[1:]):
        if t <= tb:
            return da + (db - da) * ease((t - ta) / (tb - ta) if tb > ta else 1)
    return keys[-1][1]


def camera(cams, t):
    cur = cams[0][1]
    for i, (tc, cam) in enumerate(cams):
        if t < tc:
            break
        prev = cams[i - 1][1] if i else cam
        f = ease((t - tc) / 1.6)
        cur = (prev[0] + (cam[0] - prev[0]) * f, prev[1] + (cam[1] - prev[1]) * f,
               math.exp(math.log(prev[2]) + (math.log(cam[2]) - math.log(prev[2])) * f))
    lat, lon, hdeg = cur
    hdeg *= 1 - 0.035 * math.sin(t * 0.35)  # slow breathing push
    return lat, lon, hdeg


# ------------------------------------------------------------------ drawing
def fonts():
    F = lambda n, s: ImageFont.truetype(str(A / n), s)
    return {"city": F("serif-bold.ttf", 46), "title": F("serif-bold.ttf", 120), "titlesm": F("sans-semi.ttf", 40),
            "chip": F("sans-black.ttf", 38), "meta": F("sans-semi.ttf", 30), "cap": F("sans-black.ttf", 76),
            "event": F("sans-black.ttf", 34), "km": F("sans-black.ttf", 54), "kml": F("sans-semi.ttf", 26),
            "row": F("sans-semi.ttf", 40), "total": F("sans-black.ttf", 60)}


class Renderer:
    def __init__(self, base, cams, beats, total):
        self.base, self.cams, self.beats, self.total = base, cams, beats, total
        self.f = fonts()
        self.words = []
        for b, (text, *_r) in zip(beats, BEATS):
            self.words.append(word_times(text, b["t0"], b["speech"]))
        # vignette + top/bottom shading
        y = np.linspace(-1, 1, H)[:, None]
        x = np.linspace(-1, 1, W)[None, :]
        v = np.clip((x ** 2 * .5 + y ** 2 * .35) - .15, 0, 1) * 200
        top = np.clip(1 - (np.arange(H) / 520), 0, 1)[:, None] ** 1.6 * 210
        bot = np.clip((np.arange(H) - 1250) / 670, 0, 1)[:, None] ** 1.4 * 230
        a = np.clip(np.maximum(np.maximum(v, top), bot), 0, 235).astype(np.uint8)
        a = np.broadcast_to(a, (H, W))
        self.shade = Image.fromarray(np.dstack([np.full((H, W, 3), (8, 12, 16), np.uint8), a]), "RGBA")
        g = np.random.default_rng(9).integers(0, 255, (H // 2, W // 2), dtype=np.uint8)
        self.grain = Image.fromarray(g).resize((W, H), Image.NEAREST)

    def view(self, t):
        lat, lon, hdeg = camera(self.cams, t)
        ch = hdeg * S0
        cw = ch * W / H
        cx, cy = wpx(lat, lon)
        cx = min(max(cx, cw / 2), BW - cw / 2)
        cy = min(max(cy, ch / 2), BH - ch / 2)
        return cx - cw / 2, cy - ch / 2, cw, ch

    def frame(self, t):
        x0, y0, cw, ch = self.view(t)
        img = self.base.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA")
        sc = W / cw

        def S(lat, lon, k=1):
            px, py = wpx(lat, lon)
            return ((px - x0) * sc * k, (py - y0) * sc * k)

        SS = 2
        ov = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        beat_i = max([i for i, b in enumerate(self.beats) if t >= b["t0"]] or [0])
        jn = BEATS[beat_i][1]
        finale = jn == "all"
        heads, visited = [], []
        for k, j in enumerate(JOURNEYS):
            dist = j["cum"][-1] if finale else progress(j, t)
            if dist <= 0:
                continue
            active = (jn == k)
            pts = [CITIES[c] for c in j["route"]]
            line = [S(*pts[0][:2], SS)]
            for i, seg in enumerate(j["seg"]):
                if j["cum"][i + 1] <= dist:
                    line.append(S(*pts[i + 1][:2], SS)); visited.append(j["route"][i + 1])
                else:
                    f = (dist - j["cum"][i]) / seg
                    a, b = pts[i], pts[i + 1]
                    line.append(S(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, SS))
                    heads.append((k, line[-1], j["sea"][i]))
                    break
            visited.append(j["route"][0])
            col = j["color"]
            wdt = 9 if (active or finale) else 6
            alpha = 255 if (active or finale) else 120
            if len(line) > 1:
                od.line(line, fill=(20, 14, 8, int(alpha * .9)), width=(wdt + 6) * SS, joint="curve")
                od.line(line, fill=col + (alpha,), width=wdt * SS, joint="curve")
            if active and len(line) > 1 and not heads or (heads and heads[-1][0] != k and active):
                heads.append((k, line[-1], False))
        img.alpha_composite(ov.resize((W, H), Image.LANCZOS))
        d = ImageDraw.Draw(img)

        # cities
        f = self.f
        for c in dict.fromkeys(visited):
            lat, lon, name = CITIES[c]
            x, y = S(lat, lon)
            if not (-50 < x < W + 50 and -50 < y < H + 50):
                continue
            d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(250, 240, 214), outline=(40, 28, 16), width=3)
            if c in LABEL:
                side = LABEL_SIDE.get(c, "right")
                pos, anc = {"right": ((x + 18, y), "lm"), "left": ((x - 18, y), "rm"),
                            "above": ((x, y - 22), "md"), "below": ((x, y + 22), "ma")}[side]
                d.text(pos, name, font=f["city"], fill=(36, 24, 12), anchor=anc, stroke_width=5, stroke_fill=(246, 236, 210))

        # travelling head: ship at sea, glowing marker on land
        for k, (hx, hy), sea in heads:
            if finale:
                continue
            x, y = hx / SS, hy / SS
            col = JOURNEYS[k]["color"]
            if sea:
                bob = math.sin(t * 6) * 3
                z = 1.7
                d.polygon([(x - 26 * z, y + 6 * z + bob), (x + 26 * z, y + 6 * z + bob), (x + 16 * z, y + 18 * z + bob), (x - 16 * z, y + 18 * z + bob)], fill=(70, 44, 24), outline=(20, 12, 6))
                d.line([(x, y + 6 * z + bob), (x, y - 34 * z + bob)], fill=(40, 26, 14), width=6)
                d.polygon([(x + 2 * z, y - 32 * z + bob), (x + 2 * z, y + 2 * z + bob), (x + 24 * z, y + 2 * z + bob)], fill=(246, 236, 210), outline=(40, 26, 14))
                d.polygon([(x - 2 * z, y - 26 * z + bob), (x - 2 * z, y + 2 * z + bob), (x - 18 * z, y + 2 * z + bob)], fill=col, outline=(40, 26, 14))
            else:
                r = 16 + 7 * (math.sin(t * 7) + 1)
                d.ellipse([x - r, y - r, x + r, y + r], outline=col + (220,), width=5)
                d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=col, outline=(250, 240, 214), width=4)

        # event callout
        ev = BEATS[beat_i][4]
        if ev:
            b = self.beats[beat_i]
            a = ease((t - b["t0"] - max(0.9, b["speech"] * 0.7)) / .4)
            if a > 0:
                lat, lon, _ = CITIES[ev[0]]
                x, y = S(lat, lon)
                r = 30 + 18 * ((t * 1.5) % 1)
                d.ellipse([x - r, y - r, x + r, y + r], outline=(200, 30, 30, int(255 * a)), width=6)
                tw = d.textlength(ev[1], font=f["event"])
                bx, by = min(max(x - tw / 2 - 22, 24), W - tw - 68), y - 120
                d.rounded_rectangle([bx, by, bx + tw + 44, by + 62], 10, fill=(150, 22, 22, int(235 * a)))
                d.polygon([(x - 12, by + 62), (x + 12, by + 62), (x, by + 80)], fill=(150, 22, 22, int(235 * a)))
                d.text((bx + tw / 2 + 22, by + 31), ev[1], font=f["event"], fill=(255, 245, 230, int(255 * a)), anchor="mm")

        img.alpha_composite(self.shade)
        d = ImageDraw.Draw(img)

        # intro title
        if t < 3.4:
            a = int(255 * min(ease(t / .5), ease((3.4 - t) / .6)))
            d.text((W / 2, 300), "THE JOURNEYS", font=f["title"], fill=(246, 236, 210, a), anchor="mm", stroke_width=5, stroke_fill=(10, 8, 6, a))
            d.text((W / 2, 420), "OF PAUL", font=f["title"], fill=(232, 170, 40, a), anchor="mm", stroke_width=5, stroke_fill=(10, 8, 6, a))
            d.text((W / 2, 510), "ACTS 13–21", font=f["titlesm"], fill=(230, 220, 195, a), anchor="mm", stroke_width=4, stroke_fill=(10, 8, 6, a))
        # journey chip + km
        if isinstance(jn, int):
            j = JOURNEYS[jn]
            d.rounded_rectangle([60, 120, 60 + d.textlength(j["title"], font=f["chip"]) + 40, 182], 10, fill=j["color"])
            d.text((80, 151), j["title"], font=f["chip"], fill=(20, 14, 8), anchor="lm")
            d.text((62, 210), j["meta"], font=f["meta"], fill=(225, 215, 190))
            km = sum(kk * min(1, max(0, (progress(j, t) - j["cum"][i]) / j["seg"][i])) for i, kk in enumerate(j["km"]))
            d.text((W - 60, 118), f"{int(km):,} km".replace(",", " "), font=f["km"], fill=(246, 236, 210), anchor="ra")
            d.text((W - 60, 182), "as the crow flies", font=f["kml"], fill=(200, 190, 165), anchor="ra")
        if finale:
            a = ease((t - self.beats[-2]["t0"]) / .6)
            y = 170
            d.rounded_rectangle([60, 140, W - 60, 140 + 3 * 64 + 120], 18, fill=(10, 14, 18, int(200 * a)))
            for j in JOURNEYS:
                tot = sum(j["km"])
                d.rounded_rectangle([90, y + 14, 130, y + 34], 6, fill=j["color"] + (int(255 * a),))
                d.text((150, y), j["title"].title(), font=f["row"], fill=(246, 236, 210, int(255 * a)))
                d.text((W - 90, y), f"{int(tot):,} km".replace(",", " "), font=f["row"], fill=(246, 236, 210, int(255 * a)), anchor="ra")
                y += 64
            d.line([(90, y + 6), (W - 90, y + 6)], fill=(200, 190, 165, int(160 * a)), width=2)
            tot = sum(sum(j["km"]) for j in JOURNEYS)
            d.text((90, y + 22), "Total", font=f["total"], fill=(246, 236, 210, int(255 * a)))
            d.text((W - 90, y + 22), f"{int(tot):,} km".replace(",", " "), font=f["total"], fill=(232, 170, 40, int(255 * a)), anchor="ra")

        # captions: up to 4 words, current word highlighted
        for words in self.words:
            if words and words[0][1] - .05 <= t <= words[-1][2] + .25:
                cur = max([i for i, w in enumerate(words) if w[1] <= t] or [0])
                g0 = (cur // 4) * 4
                chunk = words[g0:g0 + 4]
                line = " ".join(w[0] for w in chunk)
                tw = d.textlength(line, font=f["cap"])
                if tw > W - 120:  # split long chunk on two lines
                    rows = [chunk[:2], chunk[2:]]
                else:
                    rows = [chunk]
                y = 1530 - (len(rows) - 1) * 46
                for row in rows:
                    rw = d.textlength(" ".join(w[0] for w in row), font=f["cap"])
                    x = (W - rw) / 2
                    for w in row:
                        on = w is words[cur]
                        d.text((x, y), w[0], font=f["cap"], fill=(232, 170, 40) if on else (255, 255, 255),
                               stroke_width=7, stroke_fill=(10, 8, 6), anchor="ls")
                        x += d.textlength(w[0] + " ", font=f["cap"])
                    y += 92
                break
        out = img.convert("RGB")
        return Image.blend(out, Image.merge("RGB", [self.grain] * 3), 0.035)


# ------------------------------------------------------------------ main
_R = None


def _init(args):
    global _R
    base, cams, beats, total = args
    _R = Renderer(Image.open(base).convert("RGB"), cams, beats, total)


def _render_chunk(job):
    idx, f0, f1 = job
    path = OUT / f"_chunk{idx}.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                           "-pix_fmt", "yuv420p", str(path)], stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        ff.stdin.write(_R.frame(fi / FPS).tobytes())
    ff.stdin.close(); ff.wait()
    return str(path)


def main():
    OUT.mkdir(exist_ok=True)
    base, mask = build_base()
    voice, beats, total = narrate()
    cams, sea_spans = build_timeline(beats, mask)
    print(f"duration {total:.1f}s, beats {len(beats)}", flush=True)
    if "--frames" in sys.argv:
        r = Renderer(base, cams, beats, total)
        for s in sys.argv[sys.argv.index("--frames") + 1].split(","):
            p = OUT / f"paul_v2_{float(s):05.1f}.png"
            r.frame(float(s)).save(p); print(p)
        return
    audio = voice + music(total, sea_spans)
    audio = np.clip(audio, -1, 1)
    sf.write(OUT / "paul_v2_audio.wav", audio, SR)
    n = int(total * FPS)
    workers = 4
    step = math.ceil(n / workers)
    jobs = [(i, i * step, min(n, (i + 1) * step)) for i in range(workers)]
    with mp.Pool(workers, initializer=_init, initargs=((str(A / "paul_base.png"), cams, beats, total),)) as pool:
        parts = pool.map(_render_chunk, jobs)
    lst = OUT / "_list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    final = OUT / "paul_v2.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(OUT / "paul_v2_audio.wav"),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)], check=True)
    for p in parts:
        Path(p).unlink()
    lst.unlink()
    print(final, f"{total:.1f}s")


if __name__ == "__main__":
    main()
