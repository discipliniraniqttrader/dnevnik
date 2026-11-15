"""Tilted-terrain MAP shots on an auto region (mapfx): camera, pins, flight lines, atlas labels."""
import math, sys
import numpy as np, cv2
from PIL import Image
from .common import W, H, ROOT, ease, lerp
sys.path.insert(0, str(ROOT / "mapfx"))
import fx as FX


# ---------------------------------------------------------------- extra pin glyphs (ship, ruins, river, dot)
def _ext_icon(kind, size=132):
    base = FX.make_icon("__none__", size)            # disc + pointer, no glyph
    S = 4
    im = Image.fromarray(base).resize((base.shape[1] * S, base.shape[0] * S), Image.LANCZOS)
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    w = size * S; cx, cy, r = w / 2, w * .46, w * .43; u = r / 100.0
    X = lambda v: cx + v * u
    Y = lambda v: cy + v * u
    cream = (247, 233, 200, 255); gold = (240, 196, 98, 255); dark = (50, 40, 32, 255)
    if kind == "ship":
        d.polygon([(X(-62), Y(16)), (X(62), Y(16)), (X(40), Y(46)), (X(-40), Y(46))], fill=cream)
        d.line([(X(0), Y(16)), (X(0), Y(-56))], fill=cream, width=int(6 * u))
        d.polygon([(X(6), Y(-54)), (X(6), Y(6)), (X(50), Y(6))], fill=cream)
        d.polygon([(X(-6), Y(-40)), (X(-6), Y(6)), (X(-34), Y(6))], fill=(206, 190, 158, 255))
        d.line([(X(-70), Y(54)), (X(70), Y(54))], fill=gold, width=int(5 * u))
    elif kind == "ruins":
        d.rectangle([X(-62), Y(36), X(62), Y(46)], fill=cream)
        for x0, h in ((-48, 70), (-8, 44), (30, 60)):
            d.rectangle([X(x0), Y(36 - h), X(x0 + 18), Y(36)], fill=cream)
            d.polygon([(X(x0 - 3), Y(36 - h)), (X(x0 + 6), Y(36 - h - 9)), (X(x0 + 12), Y(36 - h - 3)), (X(x0 + 21), Y(36 - h - 10)), (X(x0 + 21), Y(36 - h))], fill=cream)
        d.rectangle([X(-8), Y(14), X(26), Y(36)], fill=dark)
        d.line([(X(-70), Y(50)), (X(70), Y(50))], fill=gold, width=int(5 * u))
    elif kind == "river":
        for j, off in enumerate((-14, 14)):
            pts = [(X(-56 + k * 4 + off * .2), Y(-50 + k * 3.4 + 16 * math.sin(k / 3.0 + j))) for k in range(30)]
            d.line(pts, fill=cream if j == 0 else gold, width=int(11 * u), joint="curve")
    else:  # dot
        d.ellipse([X(-34), Y(-34), X(34), Y(34)], fill=cream); d.ellipse([X(-18), Y(-18), X(18), Y(18)], fill=gold)
    im = im.resize((base.shape[1], base.shape[0]), Image.LANCZOS)
    return np.asarray(im)


def register_icons():
    for k in ("ship", "ruins", "river", "dot"):
        if k not in FX.Marker._icons: FX.Marker._icons[k] = _ext_icon(k)


class MapKit:
    def __init__(self, region_name, places, pin_times):
        register_icons()
        self.R = FX.Region(region_name)
        self.FIN = FX.Finish(W, H)
        self.places = places
        self.pin_t = pin_times            # key -> absolute time the pin pops in
        self._pins, self._labels = {}, {}
        self.sides = self._label_sides()

    # ---- geometry
    def wxy(self, key):
        p = self.places[key]
        return np.array([float(v) for v in self.R.wpx(p["lat"], p["lon"])])

    def make_view(self, focus, vis, tilt, yaw=0.0, target=(540, 700), cy_frac=.56):
        """View whose camera puts world point `focus` (lat, lon) on screen px `target`."""
        R = self.R
        fx_, fy_ = [float(v) for v in R.wpx(*focus)]
        lat0 = R.lat1 - fy_ / R.S0; lon0 = R.lon0 + fx_ / (R.KX * R.S0)
        v = FX.View(R, lat0, lon0, vis, tilt, W, H, cy_frac=cy_frac, yaw=yaw)
        q = np.linalg.inv(v.T.H3) @ np.array([target[0], target[1], 1.0]); q = q[:2] / q[2]
        cs, sn = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        d = (q - np.array([v.T.cx, v.T.cy])) / v.sc
        Rinv = np.array([[cs, sn], [-sn, cs]])
        c = np.array([fx_, fy_]) - Rinv @ d
        lat = R.lat1 - c[1] / R.S0; lon = R.lon0 + c[0] / (R.KX * R.S0)
        return FX.View(R, lat, lon, vis, tilt, W, H, cy_frac=cy_frac, yaw=yaw)

    def base_frame(self, V, t, haze=.8):
        img, mask = V.render_base()
        wc = V.world_coords(2)
        f = FX.water_shimmer(img, mask, V, t, wc)
        f = FX.cloud_shadows(f, mask, V, t, wc)
        return FX.apply_haze(np.clip(f, 0, 255).astype(np.uint8), V.T, haze)

    # ---- pins
    def _label_sides(self):
        out = {}
        for k, p in self.places.items():
            below = True
            for k2, q in self.places.items():
                if k2 == k: continue
                dla, dlo = q["lat"] - p["lat"], (q["lon"] - p["lon"]) * math.cos(math.radians(p["lat"]))
                if math.hypot(dla, dlo) < 1.3 and dla < 0 and abs(dlo) < abs(dla) * 1.6 + .3: below = False
            out[k] = "below" if below else "above"
        return out

    def ground_ring(self, frame, glow, V, wx, wy, rad, t, dashed, col=(255, 214, 120), width=3, alpha=1.0):
        ang = np.linspace(0, 2 * math.pi, 90)
        ring = V.project(np.c_[wx + rad * np.cos(ang), wy + rad * np.sin(ang)])
        cl = tuple(int(c * alpha) for c in col)
        if not dashed:
            cv2.polylines(frame, [ring.astype(np.int32).reshape(-1, 1, 2)], True, cl, width + 1, cv2.LINE_AA)
            cv2.polylines(glow, [ring.astype(np.int32).reshape(-1, 1, 2)], True, tuple(int(c * .5) for c in cl), width + 5, cv2.LINE_AA)
        else:
            n = 16
            for k in range(n):
                a0 = (k / n) * 2 * math.pi + t * 0.9; a1 = a0 + (2 * math.pi / n) * 0.52
                aa = np.linspace(a0, a1, 7)
                seg = V.project(np.c_[wx + rad * np.cos(aa), wy + rad * np.sin(aa)]).astype(np.int32).reshape(-1, 1, 2)
                cv2.polylines(frame, [seg], False, cl, width + 1, cv2.LINE_AA)
                cv2.polylines(glow, [seg], False, tuple(int(c * .45) for c in cl), width + 5, cv2.LINE_AA)

    def draw_pin(self, key, frame, glow, V, t, glowing=0.0):
        t0 = self.pin_t[key]; dt = t - t0
        if dt < 0: return
        p = self.places[key]; dashed = p["conf"] == "dashed"
        if key not in self._pins:
            self._pins[key] = FX.Marker(self.R, p["lat"], p["lon"], p["icon"], p["label"], t0, label_side=self.sides[key], size=1.3)
        m = self._pins[key]; wx, wy = self.wxy(key)
        self.ground_ring(frame, glow, V, wx, wy, 40 + 6 * glowing, t, dashed, alpha=min(1, dt / .3),
                         col=(255, 214, 120) if not dashed else (255, 232, 190))
        if dashed:
            tmp = frame.copy(); m.draw(tmp, V, t, glow)
            frame[:] = cv2.addWeighted(tmp, .92, frame, .08, 0)
        else:
            m.draw(frame, V, t, glow)
        if glowing > 0:
            sx, sy = V.project([[wx, wy]])[0]
            r = int(70 * (0.8 + 0.2 * math.sin(t * 6)) * glowing)
            cv2.circle(glow, (int(sx), int(sy) - 30), r, (110, 80, 30), -1, cv2.LINE_AA)
            cv2.circle(glow, (int(sx), int(sy) - 30), int(r * .55), (170, 130, 60), -1, cv2.LINE_AA)

    def region_label(self, name, lat, lon, tone, t0):
        k = (name, round(t0, 2))
        if k not in self._labels:
            self._labels[k] = FX.RegionLabel(self.R, lat, lon, name, 54 if len(name) < 12 else 40, tone, t0, .8, 14)
        return self._labels[k]

    def line(self, fr, glow, V, a, b, u, t, thin=False):
        if u <= 0: return
        pts = np.array([a + (b - a) * (k / 40) for k in range(int(40 * u) + 1)])
        if len(pts) < 2: return
        sp = V.project(pts).astype(np.int32).reshape(-1, 1, 2)
        w = 3 if thin else 5
        cv2.polylines(glow, [sp], False, (120, 90, 30), w + 8, cv2.LINE_AA)
        cv2.polylines(fr, [sp], False, (30, 20, 10), w + 3, cv2.LINE_AA)
        cv2.polylines(fr, [sp], False, (255, 214, 110), w, cv2.LINE_AA)
        if u < 1: cv2.circle(fr, tuple(sp[-1, 0]), 11, (255, 250, 232), -1, cv2.LINE_AA)

    # ---- camera
    @staticmethod
    def cam_at(s, t):
        u = ease((t - s["t0"]) / max(s["t1"] - s["t0"], 1e-3))
        a, b = s["cam"]; out = {}
        for k in a:
            out[k] = math.exp(math.log(a[k]) + (math.log(b[k]) - math.log(a[k])) * u) if k == "vis" else a[k] + (b[k] - a[k]) * u
        out["vis"] *= 1 + s.get("arc", 0) * math.sin(math.pi * u)
        return out

    def frame(self, s, t):
        cm = self.cam_at(s, t)
        V = self.make_view((cm["lat"], cm["lon"]), cm["vis"], min(.92, cm["tilt"]), cm["yaw"], (cm["tx"], cm["ty"]))
        fr = self.base_frame(V, t)
        glow = np.zeros_like(fr)
        for name, lat, lon, tone, t0 in s.get("labels", []):
            self.region_label(name, lat, lon, tone, t0).draw(fr, V, t)
        if s.get("connect"):
            a_, b_ = s["connect"]
            u = ease((t - s["ot0"]) / (s["odur"] * .8))
            self.line(fr, glow, V, self.wxy(a_), self.wxy(b_), u, t)
        if s.get("path"):                      # wide shots: sequential route line through the pins
            keys, t0, t1 = s["path"]
            n = len(keys) - 1
            for i in range(n):
                u = 1.0 if t1 <= t0 else ease((t - (t0 + (t1 - t0) * i / n)) / ((t1 - t0) / n + .05))
                self.line(fr, glow, V, self.wxy(keys[i]), self.wxy(keys[i + 1]), u, t, thin=True)
        keys = [k for k in s["pins"] if t >= self.pin_t[k]]
        self.last_pins = [tuple(float(v) for v in V.project([self.wxy(k)])[0]) for k in keys]       # screen xy, for caption nudging
        for k in sorted(keys, key=lambda k: V.project([self.wxy(k)])[0][1]):
            gl = (.8 + .2 * math.sin(t * 4 + hash(k) % 7)) if s.get("wide") else 0.0
            self.draw_pin(k, fr, glow, V, t, gl)
        g = cv2.GaussianBlur(cv2.resize(glow, (W // 2, H // 2), interpolation=cv2.INTER_AREA), (0, 0), 4.5)
        fr = cv2.add(fr, cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR))
        return self.FIN(fr, t, int(t * 30))


def icon_sprite(kind, size=150):
    """RGBA pin badge for any icon kind (used for end-card tiles)"""
    return _ext_icon(kind, size) if kind in ("ship", "ruins", "river", "dot") else FX.make_icon(kind, size)
