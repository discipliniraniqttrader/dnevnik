"""Terrarium elevation tile cache (fetch once, max 4 parallel)."""
import math, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
D = Path(__file__).resolve().parent.parent / "assets" / "terrain_tiles"
URL = "https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png"

def tx(lon, z): return (lon + 180) / 360 * 2**z
def ty(lat, z): return (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * 2**z

def choose_zoom(ppd, lat_mid):
    """Zoom whose ground resolution is closest to the requested pixel size (metres per output px)."""
    mpp = 111320 / ppd
    z = round(math.log2(156543.03 * math.cos(math.radians(lat_mid)) / mpp))
    return int(min(max(z, 3), 10))

def needed(lon0, lon1, lat0, lat1, z):
    n = 2**z
    xs = range(max(0, int(tx(lon0, z))), min(n - 1, int(tx(lon1, z))) + 1)
    ys = range(max(0, int(ty(lat1, z))), min(n - 1, int(ty(lat0, z))) + 1)
    return list(xs), list(ys)

def _fetch(a):
    z, x, y = a; p = D / f"{z}_{x}_{y}.png"
    if p.exists() and p.stat().st_size > 100: return
    for _ in range(3):
        if subprocess.run(["curl", "-sf", "-o", str(p), URL.format(z=z, x=x, y=y)]).returncode == 0: return
    p.unlink(missing_ok=True); print("fetch failed", a)

def ensure(lon0, lon1, lat0, lat1, z):
    D.mkdir(parents=True, exist_ok=True)
    xs, ys = needed(lon0, lon1, lat0, lat1, z)
    jobs = [(z, x, y) for x in xs for y in ys]
    with ThreadPoolExecutor(4) as ex: list(ex.map(_fetch, jobs))
    return xs, ys
