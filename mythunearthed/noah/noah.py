#!/usr/bin/env python3
"""MythUnearthed Short: "Where Did Noah's Ark Land? 4 Answers"  (1080x1920, 30 fps)

python3 noah/noah.py --ezra                 # render Ezra track (node) -> noah/ezra/
python3 noah/noah.py --frames 3,12.5        # preview PNGs -> out/noah_frames/
python3 noah/noah.py                        # full render -> out/noah.mp4 (+ previews)
"""
import math, multiprocessing as mp, subprocess, sys, time, json
from pathlib import Path
import numpy as np, cv2, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT))
import nscript as NS
import mapshot as MS
import scn_dusk as DK
import scn_events as EV
from scn_events import ease, out_back, F
from mapfx import fx as FX

W, H, FPS = 1080, 1920, 30
OUT = ROOT / "out"
EZ = HERE / "ezra"
GOLD, CREAM, INK = (232, 170, 40), (246, 236, 210), (10, 8, 6)
BEATS = NS.BEATS
VOICE, BT, TOTAL = NS.narrate()
NF = int(math.ceil(TOTAL * FPS))
WORDS = [NS.word_times(b["text"], bt["t0"], bt["speech"], VOICE) for b, bt in zip(BEATS, BT)]
CHIP = "NOAH'S ARK"


def T(beat, key):
    for w, a, b in WORDS[beat - 1]:
        if w.lower().strip(",.?:'\"").startswith(key.lower()):
            return float(a)
    raise KeyError(key)


def bs(n):   # cut point = a hair before beat n starts
    return BT[n - 1]["t0"] - 0.08


def fr(n, f):
    a = bs(n); b = bs(n + 1) if n < 16 else TOTAL
    return a + f * (b - a)


# ------------------------------------------------------------------ camera helpers
def cam(lat, lon, vis, tilt=.85, yaw=0.0, tx=540, ty=700):
    return dict(lat=lat, lon=lon, vis=vis, tilt=tilt, yaw=yaw, tx=tx, ty=ty)


P = MS.PLACES
AR, DU, TU, JU, GU = (P[k][:2] for k in ("ararat", "durupinar", "tushpa", "judi", "gudrun"))
PIN_T = {}          # absolute pop-in time per pin (set below)
SHOTS = []


def shot(kind, t0, t1, beat, trans="cut", **kw):
    SHOTS.append(dict(kind=kind, t0=t0, t1=t1, beat=beat, trans=trans, **kw))


# pins: first appearance
PIN_T["ararat"] = bs(2) + 0.7
PIN_T["durupinar"] = T(4, "near") + 0.1
PIN_T["tushpa"] = T(7, "Tushpa") - 0.25
PIN_T["judi"] = T(9, "Mount") + 0.1
PIN_T["gudrun"] = T(11, "Pir") + 0.1

# --- beat 1 (hook)
shot("presenter", 0.0, bs(2), 1, "cut", variant=0, action="surprised", callout=("FOUR CLAIMS", 0.45))
# --- beat 2: CASE 1
shot("map", bs(2), fr(2, .5), 2, "whip", cam=(cam(38.9, 43.2, 6.0, .8, 14, 650, 700), cam(*AR, 2.5, .88, -4, 650, 690)), arc=.25, ezra="left",
     stamp=("CASE 1", "MOUNT ARARAT", bs(2) + 0.18), labels=["TURKEY"])
shot("map", fr(2, .5), bs(3), 2, "punch", cam=(cam(*AR, 2.5, .88, -4, 650, 690), cam(*AR, 2.0, .9, -26, 650, 690)), ezra="left", labels=[])
# --- beat 3
shot("map", bs(3), fr(3, .5), 3, "zoom", cam=(cam(*AR, 2.1, .9, -26, 430, 700), cam(39.9, 44.4, 3.6, .84, -8, 430, 760)), ezra="right",
     callout=("5,137 M", bs(3) + 0.25), labels=["TURKEY"])
shot("map", fr(3, .5), bs(4), 3, "whip", cam=(cam(39.9, 44.4, 3.6, .84, -8, 430, 760), cam(40.0, 44.9, 4.6, .8, 10, 430, 780)), ezra="right",
     labels=["TURKEY", "ARMENIA", "IRAN"], label_at={"ARMENIA": T(3, "Armenia") - .3, "IRAN": T(3, "Iran") - .3, "TURKEY": 0})
# --- beat 4: CASE 2
shot("map", bs(4), fr(4, .37), 4, "vwhip", cam=(cam(*AR, 2.4, .86, 0, 650, 700), cam(*DU, 2.4, .88, 8, 650, 700)), arc=.3, ezra="left",
     stamp=("CASE 2", "DURUPINAR SITE", bs(4) + 0.18), connect=("ararat", "durupinar"), labels=[])
shot("map", fr(4, .37), fr(4, .7), 4, "punch", cam=(cam(*DU, 2.3, .88, 8, 650, 700), cam(*DU, 2.0, .9, 20, 650, 700)), ezra="left", labels=[])
shot("map", fr(4, .7), bs(5), 4, "glitch", cam=(cam(*DU, 2.6, .8, -30, 430, 720), cam(*DU, 2.2, .86, -42, 430, 720)), ezra="right",
     labels=[])
# --- beat 5 aerial photo
shot("aerial", bs(5), fr(5, .5), 5, "flash", zoom=(1.0, 1.3), focus=(0.52, 0.5), ring_at=0.5, qmark=None)
shot("aerial", fr(5, .5), bs(6), 5, "punch", zoom=(2.0, 2.5), focus=(880 / 1620, 1500 / 2880), ring_at=0.0, qmark=0.35,
     callout=("NATURAL?", T(5, "geologists") - 0.2))
# --- beat 6 kinetic
shot("shatter", bs(6), bs(7), 6, "glitch", t_quote=T(6, "Genesis") - bs(6) - .15, t_word=T(6, "mountains") - bs(6) - .05,
     t_shatter=T(6, "Plural") - bs(6), t_peaks_end=T(6, "one") - bs(6) + .3, callout=("PLURAL!", T(6, "Plural") + 0.1))
# --- beat 7: Urartu / Tushpa
shot("map", bs(7), fr(7, .5), 7, "whip", cam=(cam(*AR, 3.0, .84, 0, 430, 700), cam(*TU, 3.0, .86, 6, 430, 700)), arc=.45, ezra="right",
     callout=("URARTU", T(7, "Urartu") - 0.05), connect=("ararat", "tushpa"), labels=[])
shot("map", fr(7, .5), bs(8), 7, "iris", cam=(cam(*TU, 2.7, .88, 6, 430, 690), cam(*TU, 2.2, .9, -14, 430, 690)), ezra="right", labels=["URARTU"])
# --- beat 8: a region
shot("map", bs(8), bs(9), 8, "zoom", cam=(cam(38.6, 43.4, 3.6, .84, -10, 430, 700), cam(39.4, 44.4, 6.2, .78, 4, 430, 800)), ezra="right",
     callout=("A REGION", T(8, "highland") - 0.1), region=True, labels=["URARTU"])
# --- beat 9: CASE 3
shot("map", bs(9), fr(9, .48), 9, "whip", cam=(cam(*TU, 3.2, .84, 0, 430, 700), cam(*JU, 2.6, .88, -10, 430, 700)), arc=.4, ezra="right",
     stamp=("CASE 3", "MOUNT JUDI", bs(9) + 0.18), connect=("tushpa", "judi"), labels=[])
shot("map", fr(9, .48), fr(9, .78), 9, "punch", cam=(cam(*JU, 2.4, .88, -10, 430, 700), cam(*JU, 2.1, .9, 6, 430, 700)), ezra="right", labels=[])
shot("map", fr(9, .78), bs(10), 9, "vwhip", cam=(cam(*JU, 3.4, .8, 24, 650, 720), cam(*JU, 2.6, .85, 34, 650, 720)), ezra="left", labels=[])
# --- beat 10: al-Judi
shot("judi", bs(10), bs(11), 10, "flash", t_text=T(10, "ship") - bs(10) - 1.0, t_dis=T(10, "al-Judi") - bs(10) + .1,
     callout=("HUD 11:44", T(10, "Hud") + 0.05), mapcam=cam(*JU, 2.3, .88, 6, 540, 760))
# --- beat 11: CASE 4
shot("map", bs(11), fr(11, .4), 11, "zoom", cam=(cam(*JU, 2.3, .88, 6, 650, 700), cam(*GU, 2.8, .86, -10, 650, 700)), arc=.5, ezra="left",
     stamp=("CASE 4", "PIR OMAR GUDRUN", bs(11) + 0.18), connect=("judi", "gudrun"), labels=[])
shot("map", fr(11, .4), fr(11, .7), 11, "punch", cam=(cam(*GU, 2.6, .86, -10, 430, 700), cam(*GU, 2.1, .9, -26, 430, 700)), ezra="right", labels=["KURDISTAN"])
shot("map", fr(11, .7), bs(12), 11, "glitch", cam=(cam(*GU, 2.9, .8, 20, 650, 700), cam(*GU, 2.3, .86, 34, 650, 700)), ezra="left", labels=["KURDISTAN"])
# --- beat 12: tablet
shot("tablet", bs(12), fr(12, .55), 12, "iris", t_marks=0.3, zoom_at=99, glow_at=99)
shot("tablet", fr(12, .55), bs(13), 12, "punch", t_marks=-9, zoom_at=0.05, glow_at=T(12, "only") - fr(12, .55) - .2, callout=("ONLY PROPOSED", T(12, "only") - 0.2))
# --- beat 13: birds
shot("birds", bs(13), bs(14), 13, "whip", rel={"dove": T(13, "dove") - bs(13) - .1, "swallow": T(13, "swallow") - bs(13) - .1, "raven": T(13, "raven") - bs(13) - .1},
     callout=("3 BIRDS", T(13, "sends")))
# --- beat 14
shot("presenter", bs(14), bs(15), 14, "flash", variant=1, action="shrug", callout=("NOTHING VERIFIED", bs(14) + 0.35))
# --- beat 15: wide, 4 peaks
WIDE = (37.4, 44.0)
shot("map", bs(15), fr(15, .5), 15, "zoom", cam=(cam(*WIDE, 7.2, .8, 0, 540, 960), cam(*WIDE, 6.6, .82, 0, 540, 960)), ezra=None, wide=True,
     callout=("4 PEAKS", bs(15) + 0.25), labels=[], lines_t=(T(15, "peaks"), T(15, "traditions") + .4))
shot("map", fr(15, .5), bs(16), 15, "punch", cam=(cam(*WIDE, 6.4, .82, 0, 540, 960), cam(*WIDE, 6.0, .85, -8, 540, 960)), ezra=None, wide=True, labels=[],
     lines_t=(0, 0))
# --- beat 16: end card
shot("end", bs(16), TOTAL, 16, "whip", variant=2, action="point_right")

ORIG = list(SHOTS)
# owner feedback: flashes/glitches/whips flicker -> calm set
CALM = {"flash": "fade", "glitch": "fade", "iris": "fade", "whip": "fade", "vwhip": "fade", "punch": "fade"}
TRANS_CYC = ["zoom", "punch", "whip", "punch", "vwhip", "zoom", "glitch", "punch", "whip"]
_new = []
for s in SHOTS:
    dur = s["t1"] - s["t0"]
    n = 1 if dur <= 2.3 else int(math.ceil(dur / 2.2))
    for k in range(n):
        sub = dict(s)
        sub["ot0"], sub["odur"] = s["t0"], dur
        sub["t0"] = s["t0"] + k * dur / n; sub["t1"] = s["t0"] + (k + 1) * dur / n
        sub["sub"], sub["nsub"] = k, n
        if k > 0: sub["trans"] = TRANS_CYC[(len(_new) + k) % len(TRANS_CYC)]
        _new.append(sub)
SHOTS[:] = _new
for i, s in enumerate(SHOTS):
    s["idx"], s["dur"] = i, s["t1"] - s["t0"]
    s["ezra_slide"] = bool(s.get("ezra") and not (i and SHOTS[i - 1].get("ezra") == s.get("ezra")))
    s["dir"] = 1 if i % 2 else -1
    sc = []
    if "stamp" in s: sc.append((s["stamp"][2], 5, .3))
    if "callout" in s: sc.append((s["callout"][1], 3, .2))
    if s["kind"] == "shatter": sc.append((s["ot0"] + s["t_shatter"], 7, .4))
    s["shakes"] = sc
for s in SHOTS:
    if s["kind"] == "map": s.setdefault("labels", [])


def shot_at(t):
    for s in SHOTS:
        if t < s["t1"]: return s
    return SHOTS[-1]


# ------------------------------------------------------------------ Ezra actions
def ezra_actions():
    acts = []
    for s in ORIG:
        if s["kind"] in ("presenter", "end"): acts.append((s["t0"] + .1, s["t1"] - s["t0"] - .1, s["action"]))
        elif s.get("ezra"): acts.append((s["t0"] + .15, s["t1"] - s["t0"] - .15, "point_right" if s["ezra"] == "left" else "point_left"))
        elif s["kind"] == "map": pass
    return acts


def ezra_timeline(path):
    n = int(math.ceil(TOTAL * 30)); hop = NS.SR // 30
    rms = np.array([np.sqrt(np.mean(VOICE[i * hop:(i + 1) * hop + hop // 2] ** 2) + 1e-12) for i in range(n)])
    rms = rms / (np.percentile(rms, 95) + 1e-9)
    m = np.clip(rms, 0, 1); m[rms < 0.06] = 0
    sm = m.copy(); sm[1:] = 0.55 * m[1:] + 0.45 * m[:-1]; sm[sm < 0.05] = 0
    tl = {"fps": 30, "duration": TOTAL, "camera": "half", "mouth": [round(float(x), 3) for x in sm],
          "actions": [{"t": t, "d": d, "type": ty} for t, d, ty in ezra_actions()]}
    json.dump(tl, open(path, "w"))
    return n


# ------------------------------------------------------------------ pins / region data
RLABELS = {"TURKEY": (39.05, 41.9, "land"), "ARMENIA": (40.45, 44.75, "land"), "IRAN": (38.7, 45.9, "land"), "IRAQ": (36.2, 43.4, "land"),
           "URARTU": (39.15, 43.6, "land"), "KURDISTAN": (36.2, 44.9, "land")}
URARTU_POLY = [(40.6, 43.0), (40.5, 45.5), (39.4, 46.1), (37.7, 45.8), (37.3, 44.5), (37.9, 42.7), (38.9, 41.7), (39.9, 41.9)]
SIDE = {"ararat": "above", "durupinar": "below", "tushpa": "below", "judi": "below", "gudrun": "below"}
_cache = {}


def region_label(key, t0):
    k = (key, round(t0, 2))
    if k not in _cache:
        la, lo, tone = RLABELS[key]
        _cache[k] = FX.RegionLabel(MS.R, la, lo, key, 54 if key != "KURDISTAN" else 46, tone, t0, .8, 14)
    return _cache[k]


def pin_obj(key):
    k = ("pin", key)
    if k not in _cache:
        _cache[k] = MS.Pin(key, PIN_T[key], side=SIDE[key], size=1.3)
    return _cache[k]


def wxy(key): return MS.wxy(key)


# ------------------------------------------------------------------ renderer
class Renderer:
    def __init__(self):
        self.f = {"chip": F("sans-black.ttf", 38), "meta": F("sans-semi.ttf", 30), "cap": F("sans-black.ttf", 76)}
        self.fb = {}
        self.dk = {}
        g = np.random.default_rng(9).integers(0, 255, (H // 2, W // 2), dtype=np.uint8)
        self.grain = Image.fromarray(g).resize((W, H), Image.NEAREST)
        y = np.linspace(-1, 1, H)[:, None]; x = np.linspace(-1, 1, W)[None, :]
        v = np.clip((x ** 2 * .5 + y ** 2 * .35) - .15, 0, 1) * 200
        bot = np.clip((np.arange(H) - 1250) / 670, 0, 1)[:, None] ** 1.4 * 230
        a = (np.clip(np.maximum(v, bot), 0, 235) * 0.7).astype(np.uint8)
        self.shade = Image.fromarray(np.dstack([np.full((H, W, 3), (8, 10, 18), np.uint8), np.broadcast_to(a, (H, W))]), "RGBA")
        self._ez = {}

    # ---- Ezra
    def ezra(self, t):
        i = min(int(t * FPS), NF - 1)
        fp = EZ / f"{i:05d}.png"
        if not fp.exists(): fp = EZ / "00100.png"      # preview only: Ezra track not rendered that far yet
        im = Image.open(fp).convert("RGBA")
        r, g, b_, a = im.split()
        return Image.merge("RGBA", (r.point(lambda v: int(v * .96)), g.point(lambda v: int(v * .92)), b_.point(lambda v: int(v * .94)), a))

    # ---- map shot
    def cam_at(self, s, t):
        u = ease((t - s["ot0"]) / max(s["odur"], 1e-3))
        a, b = s["cam"]
        out = {}
        for k in a:
            if k == "vis":
                out[k] = math.exp(math.log(a[k]) + (math.log(b[k]) - math.log(a[k])) * u)
            else:
                out[k] = a[k] + (b[k] - a[k]) * u
        out["vis"] *= 1 + s.get("arc", 0) * math.sin(math.pi * u)
        k = s.get("sub", 0) if s.get("nsub", 1) > 1 else 0
        out["vis"] *= [1.0, .8, 1.12, .88, 1.06][k % 5]
        out["yaw"] += [0, 14, -12, 8, -6][k % 5]
        out["tilt"] = min(.92, out["tilt"] + [0, .04, -.03, .05, 0][k % 5])
        return out

    def map_frame(self, cm, t, s):
        V = MS.make_view((cm["lat"], cm["lon"]), cm["vis"], cm["tilt"], cm["yaw"], (cm["tx"], cm["ty"]))
        fr = MS.base_frame(V, t)
        glow = np.zeros_like(fr)
        # region highlight (beat 8)
        if s.get("region"):
            al = ease((t - s["ot0"] - .2) / .8) * .62
            pts = np.array([[float(v) for v in MS.R.wpx(la, lo)] for la, lo in URARTU_POLY]).T
            sp = V.project(np.c_[pts[0], pts[1]]).astype(np.int32)
            ov = fr.copy()
            cv2.fillPoly(ov, [sp.reshape(-1, 1, 2)], (255, 196, 72))
            fr = cv2.addWeighted(ov, .22 * al, fr, 1 - .22 * al, 0)
            n = len(sp)
            for i in range(n):
                a_, b_ = sp[i], sp[(i + 1) % n]
                L = np.hypot(*(b_ - a_)); k = max(int(L / 26), 1)
                for q in range(k):
                    if q % 2 == 0:
                        p0 = a_ + (b_ - a_) * (q / k); p1 = a_ + (b_ - a_) * min((q + .6) / k, 1)
                        cv2.line(fr, tuple(p0.astype(int)), tuple(p1.astype(int)), (255, 226, 150), 5, cv2.LINE_AA)
                        cv2.line(glow, tuple(p0.astype(int)), tuple(p1.astype(int)), (90, 70, 20), 12, cv2.LINE_AA)
        for key in s.get("labels", []):
            t0 = s["ot0"] + .15
            if key in s.get("label_at", {}): t0 = s["label_at"][key]
            region_label(key, t0).draw(fr, V, t)
        # connectors: flight line between sites
        if s.get("connect"):
            a_, b_ = s["connect"]
            u = ease((t - s["ot0"]) / (s["odur"] * .8))
            self.line(fr, glow, V, wxy(a_), wxy(b_), u, t)
        if s.get("wide") and s.get("lines_t") is not None:
            order = ["ararat", "durupinar", "judi", "gudrun", "ararat"]
            t0, t1 = s["lines_t"]
            for i in range(4):
                if t1 == 0: u = 1.0
                else: u = ease((t - (t0 + (t1 - t0) * i / 4)) / ((t1 - t0) / 4 + .05))
                self.line(fr, glow, V, wxy(order[i]), wxy(order[i + 1]), u, t, thin=True)
        pins = [k for k in PIN_T if t >= PIN_T[k] and (k != "tushpa" or True)]
        if s["beat"] <= 3: pins = [k for k in pins if k == "ararat"]
        ys = sorted(pins, key=lambda k: V.project([wxy(k)])[0][1])
        for k in ys:
            pin = pin_obj(k)
            gl = 0.0
            if s.get("wide"):
                gl = .8 + .2 * math.sin(t * 4 + hash(k) % 7)
            pin.draw(fr, glow, V, t, gl)
        fr = MS.add_glow(fr, glow)
        fr = MS.FIN(fr, t, int(t * 30))
        return fr

    def line(self, fr, glow, V, a, b, u, t, thin=False):
        if u <= 0: return
        pts = np.array([a + (b - a) * (k / 40) for k in range(int(40 * u) + 1)])
        if len(pts) < 2: return
        sp = V.project(pts).astype(np.int32).reshape(-1, 1, 2)
        w = 3 if thin else 5
        cv2.polylines(glow, [sp], False, (120, 90, 30), w + 8, cv2.LINE_AA)
        cv2.polylines(fr, [sp], False, (30, 20, 10), w + 3, cv2.LINE_AA)
        cv2.polylines(fr, [sp], False, (255, 214, 110), w, cv2.LINE_AA)
        h = sp[-1, 0]
        if u < 1: cv2.circle(fr, tuple(h), 11, (255, 250, 232), -1, cv2.LINE_AA)

    # ---- presenter / end card
    def presenter(self, s, t):
        back, front = DK.backdrop(t, s["variant"])
        lt = t - s["ot0"]
        end = s["kind"] == "end"
        sc = 1.0 + 0.06 * (lt / max(s["odur"], 1e-3)) if not end else .74
        ez = self.ezra(t).resize((int(900 * sc), int(1200 * sc)), Image.BICUBIC)
        back = back.convert("RGBA")
        if end:
            x = int(-60); y = 300
        else:
            x = int(450 - 310 * sc); y = int(1520 - 1200 * sc)
        back.alpha_composite(ez, (x, y))
        back.alpha_composite(front)
        back.alpha_composite(self.shade)
        img = back
        if s["beat"] == 1: self.four_icons(img, lt)
        if end: self.end_card(img, s, t)
        return img.convert("RGB")

    def four_icons(self, img, lt):
        if not hasattr(self, "_ic"): self._ic = FX.make_icon("peak", 150)
        for i in range(4):
            dt = lt - (0.9 + i * 0.32)
            if dt < 0: continue
            e = out_back(dt / .35)
            spr = Image.fromarray(self._ic).resize((int(150 * .55 * e) + 1, int(self._ic.shape[0] * .55 * e) + 1), Image.LANCZOS)
            img.alpha_composite(spr, (int(150 + i * 250 - spr.width / 2 + 40), int(450 - spr.height / 2)))

    def end_card(self, img, s, t):
        lt = t - s["ot0"]
        names = [("ARARAT", "ararat", T(16, "Ararat")), ("DURUPINAR", "durupinar", T(16, "Durupınar")), ("JUDI", "judi", T(16, "Judi")), ("GUDRUN", "gudrun", T(16, "Gudrun"))]
        bw, bh, gap, x0, y0 = 240, 250, 12, 42, 1160
        if not hasattr(self, "_ic2"): self._ic2 = Image.fromarray(FX.make_icon("peak", 150))
        d = ImageDraw.Draw(img, "RGBA")
        for i, (nm, key, tw) in enumerate(names):
            e = out_back((t - (tw - 0.5 + 0.0)) / .4) if t > tw - .5 else 0
            if lt < .4 + i * .12: e = 0
            e = max(e, out_back((lt - (.4 + i * .12)) / .4))
            if e <= 0: continue
            act = 1 if tw - .05 <= t < tw + .75 else 0
            sc = (.9 + .1 * min(e, 1.2)) * (1.08 if act else 1.0)
            w_, h_ = bw * sc, bh * sc
            cx = x0 + bw / 2 + i * (bw + gap); cy = y0 + bh / 2
            panel = Image.new("RGBA", (int(w_) + 40, int(h_) + 40), (0, 0, 0, 0)); pd = ImageDraw.Draw(panel)
            fillc = (58, 44, 22, 245) if act else (30, 26, 46, 235)
            pd.rounded_rectangle([20, 20, 20 + w_, 20 + h_], 30, fill=fillc, outline=(232, 170, 40, 255) if act else (200, 160, 80, 230), width=6 if act else 4)
            solid = (key == "ararat")
            ic = self._ic2.resize((int(130 * sc), int(self._ic2.height * 130 / 150 * sc)), Image.LANCZOS)
            panel.alpha_composite(ic, (int(20 + w_ / 2 - ic.width / 2), int(34)))
            # ring style: solid for the confident one, dashed for disputed
            rcx, rcy, rr = 20 + w_ / 2, 20 + 34 + ic.height * .42, ic.width * .58
            if solid: pd.ellipse([rcx - rr, rcy - rr, rcx + rr, rcy + rr], outline=(255, 214, 120, 200), width=4)
            else:
                for q in range(14):
                    pd.arc([rcx - rr, rcy - rr, rcx + rr, rcy + rr], q * 360 / 14 + t * 30, q * 360 / 14 + t * 30 + 14, fill=(255, 232, 190, 210), width=4)
            ft = F("sans-black.ttf", int((34 if len(nm) < 8 else 29) * sc))
            pd.text((20 + w_ / 2, 20 + h_ - 46 * sc), nm, font=ft, fill=(255, 226, 150, 255) if act else (246, 236, 210, 255), anchor="mm", stroke_width=3, stroke_fill=(10, 8, 6, 255))
            if act:
                gl = panel.filter(ImageFilter.GaussianBlur(14)); gl.putalpha(gl.split()[3].point(lambda v: int(v * .7)))
                img.alpha_composite(gl, (int(cx - panel.width / 2), int(cy - panel.height / 2)))
            img.alpha_composite(panel, (int(cx - panel.width / 2), int(cy - panel.height / 2)))
        # COMMENT YOUR PICK banner
        a = ease((lt - 1.2) / .4)
        if a > 0:
            pulse = 1 + .03 * math.sin(t * 6) if t > names[-1][2] + .9 else 1
            ft = F("sans-black.ttf", 84)
            txt = "COMMENT YOUR PICK"
            tw_ = int(ft.getlength(txt)) + 90
            ban = Image.new("RGBA", (tw_, 190), (0, 0, 0, 0)); bd = ImageDraw.Draw(ban)
            bd.rounded_rectangle([10, 30, tw_ - 10, 170], 28, fill=(232, 170, 40, 255), outline=(10, 8, 6, 255), width=7)
            bd.text((tw_ / 2, 100), txt, font=ft, fill=(20, 12, 6, 255), anchor="mm")
            sc = min(1.0, (W - 60) / tw_) * pulse * (1.25 - .25 * out_back((lt - 1.2) / .35))
            ban = ban.rotate(-2.5, Image.BICUBIC, expand=True).resize((int(ban.width * sc), int(ban.height * sc)), Image.LANCZOS)
            if a < 1: ban.putalpha(ban.split()[3].point(lambda v: int(v * a)))
            img.alpha_composite(ban, (int(540 - ban.width / 2), 905))
            # down arrow
            ad = ImageDraw.Draw(img, "RGBA")
            ay = 1090 + 8 * math.sin(t * 6)
            ad.polygon([(540 - 34, ay), (540 + 34, ay), (540, ay + 54)], fill=(255, 226, 150, int(255 * a)), outline=(10, 8, 6, int(255 * a)))

    # ---- stamp / callout / panel
    _stamps = {}

    def stamp_sprite(self, big, small):
        k = (big, small)
        if k in self._stamps: return self._stamps[k]
        w_, h_ = 760, 300
        im = Image.new("RGBA", (w_ + 60, h_ + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        # manila tag
        d.rounded_rectangle([30, 70, 30 + w_, 30 + h_], 26, fill=(236, 214, 160, 255), outline=(60, 40, 20, 255), width=6)
        d.rounded_rectangle([30, 30, 330, 100], 20, fill=(236, 214, 160, 255), outline=(60, 40, 20, 255), width=6)
        d.rectangle([34, 80, 326, 104], fill=(236, 214, 160, 255))
        d.text((180, 62), "CASE FILE", font=F("sans-semi.ttf", 30), fill=(90, 60, 30, 255), anchor="mm")
        red = (196, 34, 30, 255)
        ft = F("sans-black.ttf", 168)
        d.rounded_rectangle([70, 112, 30 + w_ - 40, 250], 14, outline=red, width=8)
        d.text((30 + w_ / 2, 183), big, font=ft, fill=red, anchor="mm")
        d.text((30 + w_ / 2, 282 - 10), small, font=F("sans-semi.ttf", 34), fill=(70, 46, 24, 255), anchor="mm")
        # ink distress: knock out specks in red areas
        a = np.asarray(im).copy()
        rn = np.random.default_rng(len(big) * 7 + ord(big[-1]))
        spk = cv2.GaussianBlur(rn.random(a.shape[:2]).astype(np.float32), (0, 0), 1.3)
        mk = (spk < np.percentile(spk, 9))
        isred = (a[..., 0] > 150) & (a[..., 1] < 80)
        a[mk & isred] = (236, 214, 160, 255)
        im = Image.fromarray(a)
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.paste((0, 0, 0, 140), (0, 0), im.split()[3]); sh = sh.filter(ImageFilter.GaussianBlur(10))
        out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(sh, (10, 14)); out.alpha_composite(im)
        self._stamps[k] = out
        return out

    def stamp(self, img, st, t):
        big, small, t0 = st
        f = (t - t0) * FPS
        if f < 0: return
        sp = self.stamp_sprite(big, small)
        sc = 1.0 + 1.1 * (1 - ease(f / 5.0)) if f < 5 else 1.0
        a = min(1, f / 2) * (1 - ease((f / FPS - 2.6) / .4))
        if a <= 0: return
        sp = sp.rotate(-4, Image.BICUBIC, expand=True)
        sp = sp.resize((int(sp.width * sc * .9), int(sp.height * sc * .9)), Image.LANCZOS)
        if a < 1: sp.putalpha(sp.split()[3].point(lambda v: int(v * a)))
        img.alpha_composite(sp, (int(540 - sp.width / 2), int(450 - sp.height / 2)))
        if 5 <= f < 12:     # impact ring
            e = (f - 5) / 7
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ov).ellipse([540 - 420 * e, 450 - 200 * e, 540 + 420 * e, 450 + 200 * e], outline=(255, 240, 210, int(200 * (1 - e))), width=6)
            img.alpha_composite(ov)

    def corner(self, img, s, t):
        lt = t - s["t0"]
        side = s["ezra"]
        slide = (1 - out_back(lt / 0.35, 1.2)) * 520 if s["ezra_slide"] else 0
        px0, py0, px1, py1 = (634, 940, 1056, 1420) if side == "right" else (24, 940, 446, 1420)
        ez = self.ezra(t)
        sc = 0.46
        ez = ez.resize((int(900 * sc), int(1200 * sc)), Image.BICUBIC)
        pw, ph = px1 - px0, py1 - py0
        gr = np.linspace(0, 1, ph)[:, None, None]
        col = (np.array([60, 48, 96]) * (1 - gr) + np.array([24, 20, 44]) * gr)
        bgp = Image.fromarray(np.broadcast_to(col, (ph, pw, 3)).astype(np.uint8)).convert("RGBA")
        m = Image.new("L", (pw, ph), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, pw - 1, ph - 1], 28, fill=225)
        panel = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); panel.paste(bgp, (0, 0), m)
        panel.alpha_composite(ez, (6 if side == "left" else pw - ez.width - 6, ph - ez.height))
        a = np.asarray(panel.split()[3], np.float32) * (np.asarray(m, np.float32) > 0)
        panel.putalpha(Image.fromarray(a.astype(np.uint8)))
        ImageDraw.Draw(panel).rounded_rectangle([1, 1, pw - 2, ph - 2], 28, outline=(232, 170, 40, 255), width=4)
        if side == "right": img.alpha_composite(panel, (int(px0 + slide * .9), py0))
        else: img.alpha_composite(panel, (px0, int(py0 + slide)))

    def callout(self, img, text, dt):
        f = dt * FPS
        if f < 0: return
        a = min(1, f / 3)
        sc = 1.4 - 0.4 * out_back(f / 6)
        size = 100
        while F("sans-black.ttf", size).getlength(text) + 20 > 960 and size > 40: size -= 4
        col = (255, 90, 76) if text in ("NOTHING VERIFIED", "NATURAL?") else (255, 244, 224)
        ft = F("sans-black.ttf", size)
        tw = int(ft.getlength(text)) + 80
        lay = Image.new("RGBA", (tw, 190), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        ld.text((tw / 2, 80), text, font=ft, fill=col, anchor="mm", stroke_width=11, stroke_fill=INK)
        bw = (tw - 80) * ease(f / 8)
        ld.rounded_rectangle([tw / 2 - bw / 2, 140, tw / 2 + bw / 2, 154], 6, fill=(232, 170, 40, 255), outline=INK, width=3)
        lay = lay.resize((int(tw * sc), int(190 * sc)), Image.BICUBIC)
        if a < 1: lay.putalpha(lay.split()[3].point(lambda v: int(v * a)))
        img.alpha_composite(lay, (int(540 - lay.width / 2), int(345 - lay.height * 0.42)))

    # ---- shot dispatcher
    def shot_img(self, s, t):
        lt = t - s["ot0"]; k = s["kind"]
        s = dict(s, dur=s["odur"], t0=s["ot0"]) if False else s
        if k == "map":
            cm = self.cam_at(s, t); arr = self.map_frame(cm, t, s)
        elif k == "aerial":
            arr = EV.aerial_scene(lt, s["odur"], t, s["zoom"], s["focus"], s.get("qmark"), s["ring_at"])
        elif k == "shatter":
            arr = EV.shatter_scene(lt, t, s["t_quote"], s["t_word"], s["t_shatter"], s["t_peaks_end"])
        elif k == "judi":
            mf = None
            if lt > s["t_dis"] - .1:
                s2 = dict(s, labels=[], kind="map")
                mf = self.map_frame(s["mapcam"], t, s2)
            arr = EV.judi_scene(lt, s["odur"], t, s["t_text"], s["t_dis"], mf)
        elif k == "tablet":
            arr = EV.tablet_scene(lt, s["odur"], t, s["t_marks"] + 0 if s["t_marks"] > -5 else -9, s["zoom_at"], s["glow_at"])
        elif k == "birds":
            arr = EV.birds_scene(lt, t, s["rel"])
        elif k in ("presenter", "end"):
            return self.presenter(s, t).convert("RGBA") if False else self.finish_rgba(self.presenter(s, t), s, t)
        img = Image.fromarray(arr).convert("RGBA")
        return self.finish_rgba(img, s, t)

    def finish_rgba(self, img, s, t):
        img = img.convert("RGBA")
        if s["kind"] not in ("presenter", "end", "aerial", "judi", "tablet"):
            img.alpha_composite(self.shade)
        elif s["kind"] in ("judi", "tablet", "aerial"):
            img.alpha_composite(self.shade.point(lambda v: int(v * .6)) if False else self.shade)
        if s.get("ezra"): self.corner(img, s, t)
        if "stamp" in s: self.stamp(img, s["stamp"], t)
        if "callout" in s: self.callout(img, s["callout"][0], t - s["callout"][1])
        return img.convert("RGB")

    def final(self, s, t, extra=1.0):
        img = self.shot_img(s, t)
        lt = t - s["t0"]
        sc = extra
        if s["kind"] != "map":
            p_ = lt / max(s["dur"], 1e-3); k_ = s.get("sub", 0)
            sc *= (1.0 + .08 * p_) if k_ % 2 == 0 else (1.12 - .08 * p_)
        dx = dy = 0.0; shk = 0.0
        for st, amp, dur in s.get("shakes", []):
            d_ = t - st
            if 0 <= d_ < dur: shk = max(shk, amp * math.exp(-4 * d_ / dur))
        if shk > .5:
            r = np.random.default_rng(int(round(t * FPS)))
            dx, dy = r.uniform(-1, 1, 2) * shk; sc *= 1.0 + shk / 230
        if sc == 1.0 and dx == 0: return img
        ax, ay = 540, 960
        return img.transform((W, H), Image.AFFINE, (1 / sc, 0, ax - ax / sc - dx / sc, 0, 1 / sc, ay - ay / sc - dy / sc), Image.BILINEAR)

    # ---- HUD
    def capfont(self, w):
        return F("sans-black.ttf", 76) if not any(c in w for c in "ğĞşŞİ") else _inter(76)

    def hud(self, img, t):
        d = ImageDraw.Draw(img, "RGBA")
        f = self.f
        bi = max([i for i, b in enumerate(BT) if t >= b["t0"]] or [0])
        d.rounded_rectangle([60, 120, 60 + d.textlength(CHIP, font=f["chip"]) + 40, 182], 10, fill=GOLD)
        d.text((80, 151), CHIP, font=f["chip"], fill=(20, 14, 8), anchor="lm")
        src = BEATS[bi].get("source", "-")
        if src and src != "-":
            d.text((62, 210), "SOURCE: " + src.upper() if False else src, font=f["meta"], fill=(235, 225, 200), stroke_width=4, stroke_fill=INK)
        for words in WORDS:
            if words and words[0][1] - .05 <= t <= words[-1][2] + .25:
                cur = max([i for i, w in enumerate(words) if w[1] <= t] or [0])
                g0 = (cur // 4) * 4
                chunk = words[g0:g0 + 4]
                wl = lambda ws: sum(d.textlength(w[0] + " ", font=self.capfont(w[0])) for w in ws)
                rows = [chunk[:2], chunk[2:]] if wl(chunk) > W - 100 else [chunk]
                y = 1530 - (len(rows) - 1) * 46
                for row in rows:
                    x = (W - wl(row) + d.textlength(" ", font=f["cap"])) / 2
                    for w in row:
                        ft = self.capfont(w[0])
                        d.text((x, y), w[0], font=ft, fill=GOLD if w is words[cur] else (255, 255, 255), stroke_width=7, stroke_fill=INK, anchor="ls")
                        x += d.textlength(w[0] + " ", font=ft)
                    y += 92
                break

    # ---- compose
    def frame(self, fi):
        t = fi / FPS
        s = shot_at(t); i = s["idx"]
        fin = fi - int(round(s["t0"] * FPS))
        tr = CALM.get(s["trans"], s["trans"])
        punch = 1.0
        if tr in ("punch", "flash") and i and fin < 6:
            punch = 1 + 0.04 * (1 - ease(fin / 5.0))
        img = self.final(s, t, punch)
        if i and fin < 8 and tr in ("zoom", "fade"):
            prev = self.final(SHOTS[i - 1], t)
            img = self.transition(tr, prev, img, fin, s["dir"])
        # no white flashes (owner: flashing is unpleasant to watch)
        self.hud(img, t)
        return Image.blend(img, Image.merge("RGB", [self.grain] * 3), 0.03)

    def transition(self, tr, prev, img, fin, d):
        p = (fin + 1) / 8.0; e = ease(p)
        if tr == "fade":
            return Image.blend(prev, img, e)
        A = np.asarray(prev, np.float32); B = np.asarray(img, np.float32)
        if tr in ("whip", "vwhip"):
            vert = tr == "vwhip"
            canvas = np.concatenate([A, B], 0 if vert else 1) if d > 0 else np.concatenate([B, A], 0 if vert else 1)
            span = H if vert else W
            off = int(span * (e if d > 0 else 1 - e))
            blur = int(60 * math.sin(math.pi * p)) + 1
            acc = np.zeros_like(A)
            for k in range(-3, 4):
                o = int(min(max(off + k * blur / 3, 0), span))
                acc += canvas[o:o + H] if vert else canvas[:, o:o + W]
            return Image.fromarray((acc / 7).astype(np.uint8))
        if tr == "zoom":
            sc = 1 + 0.25 * e
            M = np.array([[sc, 0, 540 - 540 * sc], [0, sc, 960 - 960 * sc]], np.float32)
            Az = cv2.warpAffine(A, M, (W, H), flags=cv2.INTER_LINEAR)
            Az = cv2.GaussianBlur(Az, (0, 0), 1.5 * math.sin(math.pi * p) + .1)
            s2 = 0.92 + 0.08 * e
            M2 = np.array([[s2, 0, 540 - 540 * s2], [0, s2, 960 - 960 * s2]], np.float32)
            Bz = cv2.warpAffine(B, M2, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            a = ease(min(1, p * 1.4))
            return Image.fromarray(np.clip(Az * (1 - a) + Bz * a, 0, 255).astype(np.uint8))
        if tr == "glitch":
            out = (A if p < .5 else B).copy()
            r = np.random.default_rng(fin * 31 + 5)
            for _ in range(9):
                y0 = int(r.integers(0, H - 80)); hh = int(r.integers(20, 160)); sh = int(r.integers(-120, 120))
                src = A if r.random() < .5 else B
                out[y0:y0 + hh] = np.roll(src[y0:y0 + hh], sh, 1)
            amt = int(18 * math.sin(math.pi * p)) + 2
            out[..., 0] = np.roll(out[..., 0], amt, 1); out[..., 2] = np.roll(out[..., 2], -amt, 1)
            return Image.fromarray(out.astype(np.uint8))
        if tr == "iris":
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            r = np.sqrt((xx - 540) ** 2 + ((yy - 960) * .7) ** 2)
            R = e * 1250
            m = np.clip((R - r) / 40, 0, 1)[..., None]
            ring = np.clip(1 - np.abs(r - R) / 14, 0, 1)[..., None] * np.array([255, 214, 120], np.float32) * .8
            return Image.fromarray(np.clip(A * (1 - m) + B * m + ring * (p < 1), 0, 255).astype(np.uint8))
        return img


_ifonts = {}


def _inter(size):
    if size not in _ifonts: _ifonts[size] = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Black.otf", size)
    return _ifonts[size]


# ------------------------------------------------------------------ audio events
def sfx_events():
    ev = {k: [] for k in ("whoosh", "whip", "impact", "pop", "place", "tick", "flap", "birdwhoosh", "shatter", "shimmer", "wind")}
    for s in SHOTS[1:]:
        if CALM.get(s["trans"], s["trans"]) == "zoom": ev["whoosh"].append(s["t0"])  # soft whoosh only on zoom cuts
    for s in ORIG:
        if "callout" in s: ev["pop"].append(s["callout"][1])
        if "stamp" in s: ev["impact"].append(s["stamp"][2] + 5 / FPS)
        if s["kind"] == "shatter":
            ev["shatter"].append(s["t0"] + s["t_shatter"]); ev["impact"].append(s["t0"] + s["t_shatter"])
            ev["wind"].append((s["t0"], s["t1"]))
        if s["kind"] == "map": ev["wind"].append((s["t0"], s["t1"]))
        if s["kind"] == "judi": ev["shimmer"].append(s["t0"] + s["t_text"])
        if s["kind"] == "tablet" and s["t_marks"] > -5:
            ev["impact"].append(s["t0"] + .05)
            ev["tick"] += [s["t0"] + s["t_marks"] + .1 + i * .075 for i in range(20)]
        if s["kind"] == "birds":
            for k, r in s["rel"].items():
                a = s["t0"] + r
                ev["birdwhoosh"].append(a)
                rate = {"dove": 2.6, "swallow": 4.4, "raven": 1.9}[k]
                ev["flap"] += [a + q / rate for q in range(int(1.6 * rate))]
    for k, t in PIN_T.items(): ev["place"].append(t)
    # merge adjacent wind spans
    sp = sorted(ev["wind"]); m = []
    for a, b in sp:
        if m and a <= m[-1][1] + .05: m[-1] = (m[-1][0], max(m[-1][1], b))
        else: m.append((a, b))
    ev["wind"] = m
    return ev


# ------------------------------------------------------------------ main
_R = None


def _init():
    global _R
    cv2.setNumThreads(1)
    _R = Renderer()


def _chunk(job):
    idx, f0, f1 = job
    path = OUT / f"_noah{idx:03d}.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", str(path)], stdin=subprocess.PIPE)
    for fi in range(f0, f1): ff.stdin.write(_R.frame(fi).tobytes())
    ff.stdin.close(); ff.wait()
    return str(path)


def main():
    OUT.mkdir(exist_ok=True)
    if "--ezra" in sys.argv:
        tlp = HERE / "ezra_timeline.json"; ezra_timeline(tlp)
        subprocess.run(["node", str(ROOT / "presenter/render.js"), str(tlp), str(EZ)], check=True, cwd=str(ROOT / "presenter"))
        return
    if "--frames" in sys.argv:
        r = Renderer(); d = OUT / "noah_frames"; d.mkdir(exist_ok=True)
        for sec in sys.argv[sys.argv.index("--frames") + 1].split(","):
            p = d / f"f_{float(sec):06.2f}.png"; r.frame(int(round(float(sec) * FPS))).save(p); print(p, flush=True)
        return
    t0 = time.time()
    import nsfx
    audio = nsfx.mix(VOICE, TOTAL, sfx_events())
    sf.write(OUT / "noah_audio.wav", audio, NS.SR)
    print("audio done", flush=True)
    n = 24; step = math.ceil(NF / n)
    jobs = [(i, i * step, min(NF, (i + 1) * step)) for i in range(n) if i * step < NF]
    with mp.get_context("spawn").Pool(4, initializer=_init) as pool:
        parts = pool.map(_chunk, jobs, chunksize=1)
    lst = OUT / "_noah_list.txt"; lst.write_text("".join(f"file '{p}'\n" for p in parts))
    final = OUT / "noah.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(OUT / "noah_audio.wav"),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)], check=True)
    for p in parts: Path(p).unlink()
    lst.unlink()
    print(final, f"{TOTAL:.1f}s render {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
