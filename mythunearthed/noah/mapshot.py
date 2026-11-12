"""Tilted-terrain map frames for the Noah Short (uses mapfx)."""
import math, sys
from pathlib import Path
import numpy as np, cv2
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "mapfx"))
from fx import *

W, H = 1080, 1920
R = Region("noah")
FIN = Finish(W, H)
PLACES = {  # lat, lon, label, kind, confidence (from script.json)
    "ararat": (39.70, 44.30, "Mount Ararat", "peak", "solid"),
    "durupinar": (39.44, 44.23, "Durupınar site", "peak", "dashed"),
    "tushpa": (38.50, 43.34, "Tushpa (Van)", "walls", "solid"),
    "judi": (37.37, 42.47, "Mount Judi", "peak", "dashed"),
    "gudrun": (35.6, 45.3, "Pir Omar Gudrun", "peak", "dashed"),
}


def wxy(k):
    return np.array([float(v) for v in R.wpx(PLACES[k][0], PLACES[k][1])])


def make_view(focus, vis, tilt, yaw=0.0, target=(540, 700), cy_frac=.56):
    """View whose camera is placed so world point `focus` (lat, lon) lands on screen px `target`."""
    fx_, fy_ = [float(v) for v in R.wpx(*focus)]
    lat0 = R.lat1 - fy_ / R.S0; lon0 = R.lon0 + fx_ / (R.KX * R.S0)
    v = View(R, lat0, lon0, vis, tilt, W, H, cy_frac=cy_frac, yaw=yaw)
    q = np.linalg.inv(v.T.H3) @ np.array([target[0], target[1], 1.0]); q = q[:2] / q[2]
    # Flat = sc * Rot * (p - c) + (cx, cy);  want Flat(focus) = q
    cs, sn = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    d = (q - np.array([v.T.cx, v.T.cy])) / v.sc
    Rinv = np.array([[cs, sn], [-sn, cs]])
    c = np.array([fx_, fy_]) - Rinv @ d
    lat = R.lat1 - c[1] / R.S0; lon = R.lon0 + c[0] / (R.KX * R.S0)
    return View(R, lat, lon, vis, tilt, W, H, cy_frac=cy_frac, yaw=yaw)


def base_frame(V, t, haze=.8):
    img, mask = V.render_base()
    wc = V.world_coords(2)
    f = water_shimmer(img, mask, V, t, wc)
    f = cloud_shadows(f, mask, V, t, wc)
    return apply_haze(np.clip(f, 0, 255).astype(np.uint8), V.T, haze)


def ground_ring(frame, glow, V, wx, wy, rad, t, dashed, col=(255, 214, 120), width=3, alpha=1.0):
    ang = np.linspace(0, 2 * math.pi, 90)
    ring = V.project(np.c_[wx + rad * np.cos(ang), wy + rad * np.sin(ang)])
    cl = tuple(int(c * alpha) for c in col)
    if not dashed:
        cv2.polylines(frame, [ring.astype(np.int32).reshape(-1, 1, 2)], True, cl, width + 1, cv2.LINE_AA)
        cv2.polylines(glow, [ring.astype(np.int32).reshape(-1, 1, 2)], True, tuple(int(c * .5) for c in cl), width + 5, cv2.LINE_AA)
    else:
        n = 16
        for k in range(n):
            a0 = (k / n) * 2 * math.pi + t * 0.9
            a1 = a0 + (2 * math.pi / n) * 0.52
            aa = np.linspace(a0, a1, 7)
            seg = V.project(np.c_[wx + rad * np.cos(aa), wy + rad * np.sin(aa)]).astype(np.int32).reshape(-1, 1, 2)
            cv2.polylines(frame, [seg], False, cl, width + 1, cv2.LINE_AA)
            cv2.polylines(glow, [seg], False, tuple(int(c * .45) for c in cl), width + 5, cv2.LINE_AA)


class Pin:
    def __init__(self, key, t0, side="below", size=1.0, label=True, ring=True):
        la, lo, name, kind, conf = PLACES[key]
        self.key, self.t0, self.dashed = key, t0, conf == "dashed"
        self.wx, self.wy = wxy(key)
        self.m = Marker(R, la, lo, kind, name if label else None, t0, label_side=side, size=size)
        self.ring = ring
        self.sub = None

    def draw(self, frame, glow, V, t, glowing=0.0):
        dt = t - self.t0
        if dt < 0:
            return
        if self.ring:
            rr = 6.0 * min(1, dt / .5) + 2 * glowing + 5
            sc = 1.0 / (V.sc / 0.5) ** .4
            rad = (46 + 8 * math.sin(t * 3)) * min(1, dt / .5) * (0.6 + .4 * 1) * 1.0
            ground_ring(frame, glow, V, self.wx, self.wy, 40 + 6 * glowing, t, self.dashed, alpha=min(1, dt / .3),
                        col=(255, 214, 120) if not self.dashed else (255, 232, 190))
        if self.dashed:
            # pin drawn slightly see-through: "approximate position"
            tmp = frame.copy(); self.m.draw(tmp, V, t, glow)
            frame[:] = cv2.addWeighted(tmp, .92, frame, .08, 0)
        else:
            self.m.draw(frame, V, t, glow)
        if glowing > 0:
            sx, sy = V.project([[self.wx, self.wy]])[0]
            r = int(70 * (0.8 + 0.2 * math.sin(t * 6)) * glowing)
            cv2.circle(glow, (int(sx), int(sy) - 30), r, (110, 80, 30), -1, cv2.LINE_AA)
            cv2.circle(glow, (int(sx), int(sy) - 30), int(r * .55), (170, 130, 60), -1, cv2.LINE_AA)


def add_glow(frame, glow):
    g = cv2.GaussianBlur(cv2.resize(glow, (W // 2, H // 2), interpolation=cv2.INTER_AREA), (0, 0), 4.5)
    return cv2.add(frame, cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR))


if __name__ == "__main__":
    import time
    t0 = time.time()
    V = make_view((39.7, 44.3), 3.2, .85, 0, (540, 700))
    fr = base_frame(V, 1.0)
    glow = np.zeros_like(fr)
    p = Pin("ararat", 0.0); p.draw(fr, glow, V, 1.0)
    p2 = Pin("durupinar", 0.0, side="right"); p2.draw(fr, glow, V, 1.0)
    fr = FIN(add_glow(fr, glow), 1.0)
    print(time.time() - t0)
    cv2.imwrite(str(HERE / "test/m1.png"), cv2.cvtColor(fr, cv2.COLOR_RGB2BGR))
    V = make_view((38.5, 43.4), 7.5, .85, 0, (540, 760))
    fr = base_frame(V, 1.0); glow = np.zeros_like(fr)
    for k in PLACES:
        Pin(k, 0).draw(fr, glow, V, 1.0, 1.0)
    fr = FIN(add_glow(fr, glow), 1.0)
    cv2.imwrite(str(HERE / "test/m2.png"), cv2.cvtColor(fr, cv2.COLOR_RGB2BGR))
