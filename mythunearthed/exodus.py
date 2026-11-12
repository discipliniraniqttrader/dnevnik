#!/usr/bin/env python3
"""MythUnearthed Short: "The Exodus route on the map".

python3 exodus.py                     # full render -> out/exodus.mp4 (+ preview PNGs)
python3 exodus.py --frames 3,12.5     # preview PNGs at these seconds -> out/exodus_frames/
"""
import math, multiprocessing as mp, subprocess, sys, time, json
from pathlib import Path
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from exodus import scenes as SC
from exodus import base as B
from exodus.script import BEATS, narrate, ezra_timeline, SR
from exodus.scenes import ease, out_back, F
import paul_v2 as P            # reuse caption timing + shading look

W, H, FPS = 1080, 1920, 30
OUT = HERE / "out"
EZ = HERE / "exodus" / "ezra"
GOLD, CREAM, INK = (232, 170, 40), (246, 236, 210), (10, 8, 6)
S0 = B.S0

# ------------------------------------------------------------------ timing
VOICE, BT, TOTAL = narrate()
NF = int(math.ceil(TOTAL * FPS))
WORDS = [P.word_times(b[0], bt["t0"], bt["speech"]) for b, bt in zip(BEATS, BT)]


def T(beat, key):
    """start time of the first word of beat (1-based) beginning with key"""
    for w, a, b in WORDS[beat - 1]:
        if w.lower().strip(",.?'\"").startswith(key.lower()):
            return a
    raise KeyError(key)


def beat_of(t):
    return max([i for i, b in enumerate(BT) if t >= b["t0"]] or [0])


# ------------------------------------------------------------------ geography / route
_BASE, _MASK = B.build_base()
SNAP = B.snapped_places(_MASK)


def crom(pts, n=14):
    p = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = map(np.array, (p[i - 1], p[i], p[i + 1], p[i + 2]))
        for k in range(n):
            s = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s * s + (-p0 + 3 * p1 - 3 * p2 + p3) * s ** 3))
    out.append(np.array(p[-2]))
    return np.array(out)


NODES = [SNAP[k] for k in B.ROUTE]
PATH = crom(NODES)
_seg = np.r_[0, np.cumsum(np.hypot(*np.diff(PATH, axis=0).T))]
NODE_ARC = [_seg[min(i * 14, len(_seg) - 1)] for i in range(len(NODES))]
MOAB = np.array(SNAP["moab"])

# route progress keys (time, p) ; p in 0..9 along the solid route, 9..10 = dashed leg to Moab
RKEYS = [(0, 0), (10.0, 0), (11.2, 1), (11.6, 1), (12.9, 2), (14.5, 2), (16.5, 3), (18.7, 3), (21.0, 4), (27.6, 4), (29.8, 5),
         (31.0, 5), (32.3, 6), (34.6, 6), (36.2, 7), (38.5, 7), (39.8, 8), (40.6, 8), (42.8, 9), (999, 9)]


def prog(t):
    for (ta, pa), (tb, pb) in zip(RKEYS, RKEYS[1:]):
        if t <= tb:
            return pa + (pb - pa) * ease((t - ta) / (tb - ta)) if tb > ta else pb
    return 10.0


def arc_at(p):
    i = min(int(p), len(NODES) - 2)
    return NODE_ARC[i] + (NODE_ARC[i + 1] - NODE_ARC[i]) * (p - i)


def head_pos(t):
    p = prog(t)
    a = arc_at(p)
    return np.array([np.interp(a, _seg, PATH[:, 0]), np.interp(a, _seg, PATH[:, 1])])


def appear_times():
    ap = {"rameses": T(2, "Rameses"), "crossing": 0}
    ts = np.arange(0, 60, 1 / 30)
    for i, k in enumerate(B.ROUTE):
        if k in ap:
            continue
        ap[k] = next(t for t in ts if prog(t) >= i - 0.03)
    ap["crossing"] = next(t for t in ts if prog(t) >= 3.9)
    ap["moab"] = T(13, "plains")
    return ap


APPEAR = appear_times()
JEBEL_T = T(12, "Tradition")

# ------------------------------------------------------------------ shot list
def PT(name, h):
    return (SNAP[name][0], SNAP[name][1], h)


def LL(lat, lon, h):
    x, y = B.wpx(lat, lon); return (x, y, h)


HEAD = lambda h: ("head", h)
SHOTS = []


def shot(kind, t0, t1, beat, trans="cut", **kw):
    SHOTS.append(dict(kind=kind, t0=t0, t1=t1, beat=beat, trans=trans, **kw))


b = lambda n: BT[n - 1]
shot("counter", 0.0, T(1, "So") - 0.15, 1)
shot("presenter", T(1, "So") - 0.15, b(2)["t0"], 1, "whip", variant=0)
shot("map", b(2)["t0"], 7.5, 2, "whip", cam=(LL(31.0, 32.2, 5.0), PT("rameses", 3.0)), ezra=True)
shot("map", 7.5, b(3)["t0"], 2, "punch", cam=(PT("rameses", 2.6), LL(30.7, 32.0, 2.3)), ezra=True)
shot("map", b(3)["t0"], 12.0, 3, "cut", cam=(HEAD(2.6), HEAD(2.2)), ezra=True)
shot("map", 12.0, b(4)["t0"], 3, "punch", cam=(HEAD(2.0), HEAD(1.9)), ezra=True)
shot("army", b(4)["t0"], 16.5, 4, "whip", cam=(PT("pihahiroth", 2.7), PT("pihahiroth", 2.0)), ezra=False)
shot("map", 16.5, b(5)["t0"], 4, "punch", cam=(HEAD(1.7), PT("crossing", 1.5)), ezra=True)
shot("seatop", b(5)["t0"], 21.2, 5, "flash", push=(1.0, 1.14))
shot("sealc", 21.2, b(6)["t0"], 5, "punch", push=(1.0, 1.12))
shot("presenter", b(6)["t0"], 25.6, 6, "whip", variant=1)
shot("map", 25.6, b(7)["t0"], 6, "punch", cam=(LL(29.0, 33.3, 4.8), LL(29.0, 33.3, 4.2)), ezra=True)
shot("map", b(7)["t0"], 29.2, 7, "whip", cam=(HEAD(3.0), HEAD(2.4)), ezra=True)
shot("map", 29.2, b(8)["t0"], 7, "cut", cam=(HEAD(1.8), PT("marah", 1.6)), ezra=True)
shot("map", b(8)["t0"], T(8, "twelve") - 0.1, 8, "punch", cam=(HEAD(2.0), HEAD(1.8)), ezra=True)
shot("icons", T(8, "twelve") - 0.1, b(9)["t0"], 8, "whip")
shot("map", b(9)["t0"], T(9, "starving") - 0.05, 9, "punch", cam=(HEAD(2.5), HEAD(2.0)), ezra=True)
shot("manna", T(9, "starving") - 0.05, b(10)["t0"], 9, "whip")
shot("map", b(10)["t0"], b(11)["t0"], 10, "punch", cam=(HEAD(2.0), HEAD(1.7)), ezra=True)
shot("mount", b(11)["t0"], b(12)["t0"], 11, "flash")
shot("map", b(12)["t0"], 45.45, 12, "whip", cam=(PT("sinai", 2.3), PT("sinai", 1.7)), ezra=True)
shot("presenter", 45.45, b(13)["t0"], 12, "punch", variant=2)
WIDE13 = (30.335, 35.48)
shot("map", b(13)["t0"], 50.4, 13, "whip", cam=(PT("sinai", 2.3), LL(*WIDE13, 5.74)), ezra=True, side="right")
shot("map", 50.4, b(14)["t0"], 13, "cut", cam=(LL(*WIDE13, 5.74), LL(*WIDE13, 5.5)), ezra=True, side="right")
shot("map", b(14)["t0"], 54.5, 14, "whip", cam=(LL(30.5, 33.6, 7.0), LL(30.5, 33.6, 6.4)), ezra=False)
shot("presenter", 54.5, TOTAL, 14, "punch", variant=0)

CALLOUTS = {2: ("RAMESES", "Rameses"), 4: ("CHARIOTS", "chariots"), 5: ("SEA CROSSING", "divide"), 6: ("ROUTE DEBATED", "debated"),
            7: ("BITTER WATER", "bitter"), 8: ("12 SPRINGS · 70 PALMS", "twelve"), 9: ("MANNA", "manna"), 10: ("AMALEK", "Amalek"),
            11: ("MOUNT SINAI", "mountain"), 12: ("TRADITIONAL SITE", "Tradition"), 13: ("40 YEARS", "Forty"), 14: ("COMMENT BELOW", "think")}
RINGS = {2: "rameses", 4: "pihahiroth", 7: "marah", 10: "rephidim", 12: "sinai"}
RED = {"CHARIOTS", "AMALEK"}
for i, s in enumerate(SHOTS):
    s["idx"], s["dur"] = i, s["t1"] - s["t0"]
    s["ezra_slide"] = bool(s.get("ezra") and not (i and SHOTS[i - 1].get("ezra")))
    s["dir"] = 1 if i % 2 else -1
for bn, (txt, key) in CALLOUTS.items():
    tk = T(bn, key)
    cands = [s for s in SHOTS if s["beat"] == bn and s["kind"] != "counter"]
    s = next((c for c in cands if c["t0"] <= tk < c["t1"]), cands[-1])
    if bn == 14:
        s = cands[-1]; tk = s["t0"] + 0.15
    s["callout"] = (txt, min(max(tk, s["t0"] + 0.15), s["t1"] - 0.6))
    if s["kind"] == "mount":
        s["callout"] = (txt, s["t0"] + 1.3)

    if s["kind"] in ("map", "army") and bn in RINGS:
        s["ring"] = RINGS[bn]
for s in SHOTS:
    if s["kind"] == "icons":
        s["springs_at"], s["palms_at"] = 0.12, T(8, "seventy") - s["t0"] - 0.05
    if s["kind"] == "army":
        s["hit"] = s["callout"][1] + 0.1
    if "callout" in s:
        s.setdefault("shakes", []).append((s["callout"][1], 9, 0.27))
    if s["kind"] == "army":
        s["shakes"].append((s["hit"], 26, 0.55))
    if s["kind"] == "mount":
        s["shakes"] = [(s["t0"] + SC.FLASHES[0], 16, 0.4), (s["t0"] + SC.FLASHES[1], 16, 0.4)] + [x for x in s.get("shakes", [])]
    if s["kind"] == "seatop":
        s.setdefault("shakes", []).append((s["t0"], 14, 0.4))


def shot_at(t):
    for s in SHOTS:
        if t < s["t1"]:
            return s
    return SHOTS[-1]


# ------------------------------------------------------------------ renderer
class Renderer:
    def __init__(self):
        self.base = _BASE
        self.f = {"city": F("serif-bold.ttf", 46), "city_s": F("serif-bold.ttf", 38), "chip": F("sans-black.ttf", 38), "meta": F("sans-semi.ttf", 30),
                  "cap": F("sans-black.ttf", 76), "pill": F("sans-semi.ttf", 32)}
        y = np.linspace(-1, 1, H)[:, None]; x = np.linspace(-1, 1, W)[None, :]
        v = np.clip((x ** 2 * .5 + y ** 2 * .35) - .15, 0, 1) * 200
        top = np.clip(1 - (np.arange(H) / 520), 0, 1)[:, None] ** 1.6 * 210
        bot = np.clip((np.arange(H) - 1250) / 670, 0, 1)[:, None] ** 1.4 * 230
        a = (np.clip(np.maximum(np.maximum(v, top), bot), 0, 235) * 0.8).astype(np.uint8)
        self.shade = Image.fromarray(np.dstack([np.full((H, W, 3), (8, 12, 16), np.uint8), np.broadcast_to(a, (H, W))]), "RGBA")
        g = np.random.default_rng(9).integers(0, 255, (H // 2, W // 2), dtype=np.uint8)
        self.grain = Image.fromarray(g).resize((W, H), Image.NEAREST)
        self.ezf = {}

    # ---- Ezra
    def ezra(self, t):
        i = min(int(t * FPS), 1700)
        im = Image.open(EZ / f"{i:05d}.png").convert("RGBA")
        r, g, b_, a = im.split()
        r = r.point(lambda v: int(v * 1.0)); g = g.point(lambda v: int(v * 0.94)); b_ = b_.point(lambda v: int(v * 0.86))
        return Image.merge("RGBA", (r, g, b_, a))

    # ---- camera
    def cam_at(self, s, t):
        u = ease((t - s["t0"]) / max(s["dur"], 1e-3))
        out = []
        for c in s["cam"]:
            if c[0] == "head":
                hx, hy = head_pos(t); out.append((hx, hy, c[1]))
            else:
                out.append(c)
        a, b_ = out
        h = math.exp(math.log(a[2]) + (math.log(b_[2]) - math.log(a[2])) * u)
        return a[0] + (b_[0] - a[0]) * u, a[1] + (b_[1] - a[1]) * u, h

    # ---- map shot
    def map_frame(self, s, t, ax=560, ay=800):
        tx, ty, hdeg = self.cam_at(s, t)
        ch = hdeg * S0; cw = ch * W / H; sc = H / ch
        x0 = min(max(tx - ax / sc, 0), B.BW - cw); y0 = min(max(ty - ay / sc, 0), B.BH - ch)
        img = self.base.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA")
        S = lambda px, py, k=1: ((px - x0) * sc * k, (py - y0) * sc * k)
        SS = 2
        ov = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        p = prog(t)
        ps = min(p, 9)
        a = arc_at(ps) if ps > 0 else 0
        n = int(np.searchsorted(_seg, a))
        if n > 0:
            pts = [S(*PATH[i], SS) for i in range(n)] + [S(*head_pos(t) if p <= 9 else NODES[-1], SS)]
            od.line(pts, fill=(20, 14, 8, 230), width=int(17 * SS), joint="curve")
            od.line(pts, fill=(240, 188, 60, 255), width=int(10 * SS), joint="curve")
            # marching highlight
            hl = [S(*PATH[i], SS) for i in range(max(0, n - 1))]
        # army arrow (event scene)
        if s["kind"] == "army":
            self.army(od, s, t, S, SS)
        img.alpha_composite(ov.resize((W, H), Image.LANCZOS))
        d = ImageDraw.Draw(img)
        # places
        fnt = self.f["city"] if hdeg < 4 else self.f["city_s"]
        for k in B.PLACES:
            ta = APPEAR[k]
            if t < ta:
                continue
            _, _, name, solid, side = B.PLACES[k]
            if k == "sinai" and t >= JEBEL_T:
                solid, name = True, "Jebel Musa"
            x, y = S(*SNAP[k])
            if not (-120 < x < W + 120 and -120 < y < H + 120):
                continue
            pa = out_back((t - ta) / 0.3) if k != "sinai" or t < JEBEL_T else out_back((t - JEBEL_T) / 0.3)
            r = 1.0 * pa
            if solid:
                pk = 1.0 if hdeg < 4 else 0.62
                rr = 22 * r * pk
                d.polygon([(x - rr * .8, y - 40 * r * pk + rr * .55), (x + rr * .8, y - 40 * r * pk + rr * .55), (x, y)], fill=(176, 34, 32), outline=(246, 236, 210))
                d.ellipse([x - rr, y - 40 * r * pk - rr, x + rr, y - 40 * r * pk + rr], fill=(190, 40, 36), outline=(246, 236, 210), width=3)
                d.ellipse([x - rr * .4, y - 40 * r * pk - rr * .4, x + rr * .4, y - 40 * r * pk + rr * .4], fill=(255, 244, 226))
            else:  # soft dashed circle = approximate position
                rad = 24 * r
                d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=(246, 236, 210, 70))
                for q in range(10):
                    a0 = q * 36 + t * 14
                    d.arc([x - rad, y - rad, x + rad, y + rad], a0, a0 + 20, fill=(60, 40, 22, 235), width=5)
            if name and r > 0.6:
                off = 48 if not solid else 66
                if solid:
                    y2 = y - 40 * pk
                else:
                    y2 = y
                if side == "right" and x + off + d.textlength(name, font=fnt) > W - 16:
                    side = "left"
                elif side == "left" and x - off - d.textlength(name, font=fnt) < 16:
                    side = "right"
                pos, anc = {"right": ((x + off, y2), "lm"), "left": ((x - off, y2), "rm"), "below": ((x, y + (14 if solid else 40)), "ma")}[side]
                d.text(pos, name, font=fnt, fill=(36, 24, 12), anchor=anc, stroke_width=5, stroke_fill=(246, 236, 210))
                if k == "moab" and r > 0.9:
                    note = "route not traced"
                    nf = self.f["city_s"]
                    tw_ = int(d.textlength(note, font=nf)) + 40
                    lay = Image.new("RGBA", (tw_, 70), (0, 0, 0, 0))
                    ImageDraw.Draw(lay).text((12, 40), note, font=nf, fill=(70, 46, 24, 255), anchor="lm", stroke_width=4, stroke_fill=(246, 236, 210))
                    lay = lay.transform(lay.size, Image.AFFINE, (1, 0.28, -10, 0, 1, 0), Image.BICUBIC)  # fake italic
                    al_ = ease((t - ta - 0.25) / 0.3)
                    lay.putalpha(lay.split()[3].point(lambda v: int(v * al_)))
                    nx = int(x + off - 20) if side == "right" else int(x - off - lay.width + 20)
                    img.alpha_composite(lay, (nx, int(y2 + 30)))
        d = ImageDraw.Draw(img)
        # head marker
        hx, hy = S(*head_pos(t))
        if t > APPEAR["rameses"] - 0.2:
            rr = 17 + 7 * (math.sin(t * 7) + 1)
            d.ellipse([hx - rr, hy - rr, hx + rr, hy + rr], outline=(240, 188, 60, 220), width=5)
            d.ellipse([hx - 13, hy - 13, hx + 13, hy + 13], fill=(240, 188, 60), outline=(250, 240, 214), width=4)
        # place ring (callout focus)
        if "ring" in s and "callout" in s and t >= s["callout"][1]:
            x, y = S(*SNAP[s["ring"]])
            rr = 40 + 22 * ((t * 1.4) % 1)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=(214, 40, 36, int(255 * (1 - ((t * 1.4) % 1) * .7))), width=7)
        if s["kind"] == "army":
            hit = s["hit"]
            if 0 <= t - hit < 0.5:
                al = int(110 * (1 - (t - hit) / .5))
                img.alpha_composite(Image.new("RGBA", (W, H), (230, 30, 20, al)))
        return img.convert("RGB")

    def army(self, od, s, t, S, SS):
        camp = np.array(SNAP["pihahiroth"], float)
        p0 = camp + np.array([-1650, -330]); p2 = camp + np.array([-85, 6]); p1 = camp + np.array([-900, -520])
        bez = lambda u: (1 - u) ** 2 * p0 + 2 * (1 - u) * u * p1 + u * u * p2
        prog_ = ease((t - s["t0"]) / max(s["hit"] - s["t0"], 0.4))
        fade = 1 - ease((t - s["hit"] - 0.5) / 0.6)
        if prog_ <= 0 or fade <= 0:
            return
        tail = max(0, prog_ - 0.6)
        us = np.linspace(tail, prog_, 40)
        pts = [S(*bez(u), SS) for u in us]
        al = int(235 * fade)
        for off, w in ((-1, 10), (0, 20), (1, 10)):
            nrm = np.array([0.35, 1.0]); nrm /= np.linalg.norm(nrm)
            pp = [(x + off * 46 * SS * nrm[0], y + off * 46 * SS * nrm[1]) for x, y in pts]
            od.line(pp, fill=(40, 6, 6, al), width=(w + 8) * SS, joint="curve")
            od.line(pp, fill=(214, 40, 34, al), width=w * SS, joint="curve")
        # chevrons along the body
        for k in range(10):
            u = tail + ((k / 10 + t * 1.6) % 1.0) * (prog_ - tail)
            if u > prog_ - 0.01:
                continue
            c = np.array(S(*bez(u), SS)); c2 = np.array(S(*bez(min(1, u + 0.01)), SS))
            dv = c2 - c; dv /= (np.linalg.norm(dv) + 1e-6); nv = np.array([-dv[1], dv[0]])
            sz = 30 * SS
            od.line([tuple(c - dv * sz + nv * sz), tuple(c + dv * sz * .4), tuple(c - dv * sz - nv * sz)], fill=(255, 226, 200, al), width=8 * SS, joint="curve")
        # head
        c = np.array(S(*bez(prog_), SS)); c2 = np.array(S(*bez(min(1, prog_ + 0.01)), SS))
        dv = c2 - c; dv /= (np.linalg.norm(dv) + 1e-6); nv = np.array([-dv[1], dv[0]])
        sz = 62 * SS
        od.polygon([tuple(c + dv * sz * 1.3), tuple(c - dv * sz * .3 + nv * sz), tuple(c - dv * sz * .3 - nv * sz)], fill=(214, 40, 34, al), outline=(40, 6, 6, al))

    # ---- shot dispatcher
    def shot_img(self, s, t):
        lt = t - s["t0"]
        k = s["kind"]
        if k == "map":
            img = self.map_frame(s, t)
        elif k == "army":
            img = self.map_frame(s, t)
        elif k == "counter":
            img = SC.counter_scene(max(lt, 0), s["dur"], t)
        elif k == "presenter":
            img = self.presenter(s, t)
        elif k == "seatop":
            img = SC.sea_top(lt, s["dur"], t)
        elif k == "sealc":
            img = SC.sea_corridor(lt, s["dur"], t)
        elif k == "icons":
            img = SC.icons_scene(lt, t, s["springs_at"], s["palms_at"])
        elif k == "manna":
            img = SC.manna_scene(lt, t)
        elif k == "mount":
            img = SC.mountain_scene(lt, t)
        img = img.convert("RGBA")
        if k != "presenter":
            img.alpha_composite(self.shade)
        if s.get("ezra"):
            self.corner(img, s, t)
        if "callout" in s:
            self.callout(img, s["callout"][0], t - s["callout"][1])
        return img.convert("RGB")

    def presenter(self, s, t):
        back, front = SC.backdrop(t, s["variant"])
        lt = t - s["t0"]
        sc = 1.00 + 0.06 * (lt / max(s["dur"], 1e-3))
        ez = self.ezra(t)
        ez = ez.resize((int(900 * sc), int(1200 * sc)), Image.BICUBIC)
        # soft contact glow so he sits in the scene
        back = back.convert("RGBA")
        x = int(450 - 310 * sc); y = int(1520 - 1200 * sc)
        back.alpha_composite(ez, (x, y))
        back.alpha_composite(front)
        back.alpha_composite(self.shade)
        return back.convert("RGB")

    def corner(self, img, s, t):
        lt = t - s["t0"]
        slide = (1 - out_back(lt / 0.35, 1.2)) * 520 if s["ezra_slide"] else 0
        px0, py0, px1, py1 = (634, 940, 1056, 1420) if s.get("side") == "right" else (24, 940, 446, 1420)
        ez = self.ezra(t)
        sc = 0.46
        ez = ez.resize((int(900 * sc), int(1200 * sc)), Image.BICUBIC)
        panel = Image.new("RGBA", (px1 - px0, py1 - py0), (0, 0, 0, 0))
        pd = ImageDraw.Draw(panel)
        gr = np.linspace(0, 1, py1 - py0)[:, None, None]
        col = (np.array([70, 40, 56]) * (1 - gr) + np.array([30, 18, 28]) * gr)
        ga = np.broadcast_to(col, (py1 - py0, px1 - px0, 3)).astype(np.uint8)
        bgp = Image.fromarray(ga).convert("RGBA")
        m = Image.new("L", panel.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, panel.width - 1, panel.height - 1], 28, fill=215)
        panel.paste(bgp, (0, 0), m)
        # sun glow in the panel
        panel.alpha_composite(ez, (6, py1 - py0 - ez.height))
        # clip everything to the rounded rect
        a = np.asarray(panel.split()[3], np.float32) * (np.asarray(m, np.float32) > 0)
        panel.putalpha(Image.fromarray(a.astype(np.uint8)))
        ImageDraw.Draw(panel).rounded_rectangle([1, 1, panel.width - 2, panel.height - 2], 28, outline=(232, 170, 40, 255), width=4)
        if s.get("side") == "right":
            img.alpha_composite(panel, (int(px0 + slide * 0.9), py0))
        else:
            img.alpha_composite(panel, (px0, int(py0 + slide)))

    def callout(self, img, text, dt):
        f = dt * FPS
        if f < 0:
            return
        a = min(1, f / 3)
        sc = 1.4 - 0.4 * out_back(f / 6)
        size = 100
        while self.fontw(size, text) > 960 and size > 40:
            size -= 4
        col = (255, 90, 76) if text in RED else (255, 244, 224)
        ft = F("sans-black.ttf", size)
        tw = int(ft.getlength(text)) + 80
        lay = Image.new("RGBA", (tw, 190), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        ld.text((tw / 2, 80), text, font=ft, fill=col, anchor="mm", stroke_width=11, stroke_fill=INK)
        bw = (tw - 80) * ease(f / 8)
        ld.rounded_rectangle([tw / 2 - bw / 2, 140, tw / 2 + bw / 2, 154], 6, fill=(232, 170, 40, 255), outline=INK, width=3)
        lay = lay.resize((int(tw * sc), int(190 * sc)), Image.BICUBIC)
        if a < 1:
            lay.putalpha(lay.split()[3].point(lambda v: int(v * a)))
        img.alpha_composite(lay, (int(540 - lay.width / 2), int(345 - lay.height * 0.42)))

    def fontw(self, size, text):
        return F("sans-black.ttf", size).getlength(text) + 20

    # ---- post (zoom / shake) for one shot
    def final(self, s, t, extra_scale=1.0):
        img = self.shot_img(s, t)
        lt = t - s["t0"]
        sc = extra_scale
        if "push" in s:
            sc *= s["push"][0] + (s["push"][1] - s["push"][0]) * min(1, lt / s["dur"])
        dx = dy = 0.0
        shk = 0.0
        for st, amp, dur in s.get("shakes", []):
            d_ = t - st
            if 0 <= d_ < dur:
                shk = max(shk, amp * math.exp(-4 * d_ / dur))
        if shk > 0.5:
            r = np.random.default_rng(int(round(t * FPS)))
            dx, dy = r.uniform(-1, 1, 2) * shk
            sc *= 1.0 + shk / 700
        if sc == 1.0 and dx == 0:
            return img
        ax, ay = 540, 960
        return img.transform((W, H), Image.AFFINE, (1 / sc, 0, ax - ax / sc - dx / sc, 0, 1 / sc, ay - ay / sc - dy / sc), Image.BILINEAR)

    # ---- HUD + captions
    def hud(self, img, t):
        d = ImageDraw.Draw(img, "RGBA")
        f = self.f
        bi = beat_of(t)
        d.rounded_rectangle([60, 120, 60 + d.textlength("EXODUS 12–19", font=f["chip"]) + 40, 182], 10, fill=GOLD)
        d.text((80, 151), "EXODUS 12–19", font=f["chip"], fill=(20, 14, 8), anchor="lm")
        ref = BEATS[bi][3]
        if ref:
            d.text((62, 210), ref, font=f["meta"], fill=(235, 225, 200), stroke_width=4, stroke_fill=INK)
        for words in WORDS:
            if words and words[0][1] - .05 <= t <= words[-1][2] + .25:
                cur = max([i for i, w in enumerate(words) if w[1] <= t] or [0])
                g0 = (cur // 4) * 4
                chunk = words[g0:g0 + 4]
                tw = d.textlength(" ".join(w[0] for w in chunk), font=f["cap"])
                rows = [chunk[:2], chunk[2:]] if tw > W - 120 else [chunk]
                y = 1530 - (len(rows) - 1) * 46
                for row in rows:
                    rw = d.textlength(" ".join(w[0] for w in row), font=f["cap"])
                    x = (W - rw) / 2
                    for w in row:
                        d.text((x, y), w[0], font=f["cap"], fill=GOLD if w is words[cur] else (255, 255, 255), stroke_width=7, stroke_fill=INK, anchor="ls")
                        x += d.textlength(w[0] + " ", font=f["cap"])
                    y += 92
                break

    # ---- compose one output frame
    def frame(self, fi):
        t = fi / FPS
        s = shot_at(t)
        i = s["idx"]
        fin = fi - int(round(s["t0"] * FPS))
        punch = 1.0
        if s["trans"] in ("punch", "flash") and i and fin < 6:
            punch = 1 + 0.12 * (1 - ease(fin / 5.0))
        img = self.final(s, t, punch)
        if s["trans"] == "whip" and i and fin < 5:
            prev = self.final(SHOTS[i - 1], t)
            p = (fin + 1) / 6.0
            e = ease(p)
            d = s["dir"]
            canvas = Image.new("RGB", (2 * W, H))
            canvas.paste(prev, (0, 0)); canvas.paste(img, (W, 0))
            if d < 0:
                canvas = Image.new("RGB", (2 * W, H)); canvas.paste(img, (0, 0)); canvas.paste(prev, (W, 0))
                off = W * (1 - e)
            else:
                off = W * e
            blur = int(60 * math.sin(math.pi * p)) + 1
            acc = None
            for k in range(-3, 4):
                crop = np.asarray(canvas.crop((int(off + k * blur / 3), 0, int(off + k * blur / 3) + W, H)) if 0 <= int(off + k * blur / 3) <= W else canvas.crop((int(min(max(off + k * blur / 3, 0), W)), 0, int(min(max(off + k * blur / 3, 0), W)) + W, H)), np.float32)
                acc = crop if acc is None else acc + crop
            img = Image.fromarray((acc / 7).astype(np.uint8))
        wh = 0.0
        if s["trans"] == "flash" and fin == 0:
            wh = 0.65
        elif s["trans"] == "flash" and fin == 1:
            wh = 0.3
        nxt = SHOTS[i + 1] if i + 1 < len(SHOTS) else None
        if nxt and nxt["trans"] == "flash":
            fb = int(round(nxt["t0"] * FPS))
            if fi == fb - 2:
                wh = 0.5
            elif fi == fb - 1:
                wh = 1.0
        if wh:
            img = Image.blend(img, Image.new("RGB", (W, H), (255, 250, 240)), wh)
        self.hud(img, t)
        return Image.blend(img, Image.merge("RGB", [self.grain] * 3), 0.03)


# ------------------------------------------------------------------ audio events (consumed by exodus.sfx)
def sfx_events():
    ev = {"whoosh": [], "whip": [], "impact": [], "pop": [], "tick": [], "thunder": [], "place": []}
    for s in SHOTS[1:]:
        (ev["whip"] if s["trans"] == "whip" else ev["whoosh"]).append(s["t0"])
    for s in SHOTS:
        if "callout" in s:
            ev["pop"].append(s["callout"][1])
        if s["kind"] == "army":
            ev["impact"].append(s["hit"])
        if s["kind"] == "seatop":
            ev["impact"].append(s["t0"] - 0.02)
        if s["kind"] == "mount":
            ev["impact"].append(s["t0"])
            ev["thunder"] += [s["t0"] + f for f in SC.FLASHES]
        if s["kind"] == "icons":
            ev["pop"] += [s["t0"] + s["springs_at"], s["t0"] + s["palms_at"]]
    ev["ocean"] = [(BT[4]["t0"], BT[5]["t0"])]
    ev["wind"] = [(BT[6]["t0"], BT[9]["t0"])]
    ev["rumble"] = [(BT[10]["t0"], BT[11]["t0"] + 1.0)]
    ev["place"] = [t for k, t in APPEAR.items() if k != "crossing"]
    ev["tick"] = [0.05 + i * 0.045 for i in range(int(SHOTS[0]["dur"] * 0.86 / 0.045))]
    return ev


# ------------------------------------------------------------------ main
_R = None


def _init():
    global _R
    _R = Renderer()


def _chunk(job):
    idx, f0, f1 = job
    path = OUT / f"_exo{idx:03d}.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", str(path)], stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        ff.stdin.write(_R.frame(fi).tobytes())
    ff.stdin.close(); ff.wait()
    return str(path)


def main():
    OUT.mkdir(exist_ok=True)
    if "--frames" in sys.argv:
        r = Renderer()
        d = OUT / "exodus_frames"; d.mkdir(exist_ok=True)
        for sec in sys.argv[sys.argv.index("--frames") + 1].split(","):
            p = d / f"f_{float(sec):06.2f}.png"
            r.frame(int(round(float(sec) * FPS))).save(p); print(p, flush=True)
        return
    t0 = time.time()
    from exodus import sfx
    audio = sfx.mix(VOICE, TOTAL, sfx_events())
    sf.write(OUT / "exodus_audio.wav", audio, SR)
    print("audio done", flush=True)
    n = 24
    step = math.ceil(NF / n)
    jobs = [(i, i * step, min(NF, (i + 1) * step)) for i in range(n) if i * step < NF]
    with mp.Pool(4, initializer=_init) as pool:
        parts = pool.map(_chunk, jobs, chunksize=1)
    lst = OUT / "_exo_list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    final = OUT / "exodus.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(OUT / "exodus_audio.wav"),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)], check=True)
    for p in parts:
        Path(p).unlink()
    lst.unlink()
    print(final, f"{TOTAL:.1f}s", f"render {time.time() - t0:.0f}s")
    pv = OUT / "exodus_preview"; pv.mkdir(exist_ok=True)
    for i, sec in enumerate([0.8, 6.9, 15.5, 19.8, 22.3, 24.5, 33.5, 41.8, 46.5, 51.5, 56.3]):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(sec), "-i", str(final), "-frames:v", "1", str(pv / f"p{i:02d}_{sec:05.1f}s.png")])


if __name__ == "__main__":
    main()
