#!/usr/bin/env python3
"""MapFX demo: Exodus Rameses -> Jebel Musa.   python3 mapfx/demo.py [--stills-only] [--bench]"""
import math, subprocess, sys, time
import multiprocessing as mp
from pathlib import Path
import numpy as np, cv2
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fx import *

OUT = Path(__file__).resolve().parent.parent / "out/mapfx"; OUT.mkdir(parents=True, exist_ok=True)
W, H, FPS, DUR = 1080, 1920, 30, 9.5
R = Region("base")
WP = [(30.80, 31.83), (30.55, 32.10), (29.95, 32.55), (29.15, 32.95), (28.54, 33.97)]
ARR = [1.0, 2.9, 4.7, 6.4, 8.6]       # arrival times at each waypoint
route = Route(R, WP, sea_zones=[(2, 55)])
MK = [Marker(R, 30.13, 31.30, "temple", "HELIOPOLIS", .45, size=.8),
      Marker(R, 30.80, 31.83, "walls", "RAMESES", .7, label_side="left"),
      Marker(R, 30.55, 32.10, "tent", "SUCCOTH", ARR[1] - .15, label_side="right"),
      Marker(R, 29.95, 32.55, "waves", "THE CROSSING", ARR[2] - .15),
      Marker(R, 29.15, 32.95, "tent", "MARAH", ARR[3] - .15, label_side="right"),
      Marker(R, 28.54, 33.97, "peak", "JEBEL MUSA", ARR[4] - .2, sub="MOUNT SINAI", size=1.15)]
RL = [RegionLabel(R, 29.2, 29.9, "EGYPT", 54, "land", 0.2), RegionLabel(R, 32.7, 32.6, "MEDITERRANEAN SEA", 36, "sea", .3, .6, 7),
      RegionLabel(R, 30.0, 34.1, "SINAI", 50, "land", .3, .6), RegionLabel(R, 31.0, 35.1, "CANAAN", 44, "land", .3, .6),
      RegionLabel(R, 27.3, 34.6, "RED SEA", 38, "sea", .3, .6, 7)]
TITLE = make_label("THE ROAD OUT OF EGYPT", 50, spacing=5, sub="RAMESES TO MOUNT SINAI", subsize=30)
FIN = Finish(W, H)


def head_s(t):
    if t <= ARR[0]: return 0.0
    if t >= ARR[-1]: return route.total
    for i in range(len(ARR) - 1):
        if t < ARR[i + 1]:
            u = (t - ARR[i]) / (ARR[i + 1] - ARR[i]); u = .45 * u + .55 * ease_io(u)
            return route.wp_s[i] + (route.wp_s[i + 1] - route.wp_s[i]) * u


def camera(t):
    k = ease_io(t / DUR)
    hs = head_s(t); hp, _ = route.at(hs)
    hlat = R.lat1 - hp[1] / R.S0; hlon = R.lon0 + hp[0] / (R.KX * R.S0)
    wlat, wlon = 30.0 + (hlat - 30.0) * 0, 33.0
    f = .7 * k
    lat = 30.35 + (hlat - 30.35) * f; lon = 32.95 + (hlon - 32.95) * f
    vis = 9.4 + (4.9 - 9.4) * k ** .9
    return lat, lon, vis, .95 - .25 * k, 4.0 - 8.0 * k


def frame(fi):
    t = fi / FPS
    lat, lon, vis, tl, yaw = camera(t)
    V = View(R, lat, lon, vis, tl, W, H, yaw=yaw)
    img, mask = V.render_base()
    wc = V.world_coords(2)
    f = water_shimmer(img, mask, V, t, wc); f = cloud_shadows(f, mask, V, t, wc)
    fr = apply_haze(np.clip(f, 0, 255).astype(np.uint8), V.T, .8)
    glow = np.zeros((H, W, 3), np.uint8)
    s = head_s(t)
    route.draw_ahead(glow, V, s, t)
    for rl in RL: rl.draw(fr, V, t)
    route.draw(fr, V, s, t, glow)
    g = cv2.GaussianBlur(cv2.resize(glow, (W // 2, H // 2), interpolation=cv2.INTER_AREA), (0, 0), 4.5)
    fr = cv2.add(fr, cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR) * 1)
    ring = np.zeros_like(fr)
    ys = [(m, V.project([[m.x, m.y]])[0][1]) for m in MK]
    for m, _ in sorted(ys, key=lambda a: a[1]): m.draw(fr, V, t, ring)
    fr = cv2.add(fr, ring)
    ta = ease_io((t - .3) / .7) * (1 - ease_io((t - 4.2) / .8))
    blit(fr, TITLE, W / 2, 250, 1.0, ta)
    return FIN(fr, t, fi)


def save(fr, p): cv2.imwrite(str(p), cv2.cvtColor(fr, cv2.COLOR_RGB2BGR))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    N = int(DUR * FPS)
    if mode == "--bench":
        t0 = time.time()
        for fi in (30, 90, 150, 240): frame(fi)
        print("per-frame (1 core):", (time.time() - t0) / 4); sys.exit()
    stills = [(0.5, "demo_still_1_wide"), (3.2, "demo_still_2_succoth"), (5.6, "demo_still_3_crossing"), (8.9, "demo_still_4_sinai")]
    if mode == "--stills-only":
        for t, n in stills: save(frame(int(t * FPS)), OUT / f"{n}.png")
        sys.exit()
    t0 = time.time()
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT / "demo.mp4")], stdin=subprocess.PIPE)
    keep = {int(t * FPS): n for t, n in stills}
    with mp.get_context("fork").Pool(4) as pool:
        for fi, fr in enumerate(pool.imap(frame, range(N), chunksize=2)):
            ff.stdin.write(fr.tobytes())
            if fi in keep: save(fr, OUT / f"{keep[fi]}.png")
    ff.stdin.close(); ff.wait()
    print(f"rendered {N} frames in {time.time()-t0:.1f}s  ({(time.time()-t0)/N*4:.3f}s CPU/frame, {(time.time()-t0)/N:.3f}s wall/frame)")
