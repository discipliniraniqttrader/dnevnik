"""Auto terrain region from the places' bounds (+margin), built once and cached in assets/ (mapfx/build_terrain.py)."""
import json, math, subprocess, sys
from pathlib import Path
from .common import ROOT, ASSETS, W, H

RATIO = W / H      # portrait: visible width / height


def plan_region(places):
    """-> dict(name, lon0, lon1, lat0, lat1, ppd, vis_wide, center)"""
    lats = [p["lat"] for p in places.values()]; lons = [p["lon"] for p in places.values()]
    la0, la1, lo0, lo1 = min(lats), max(lats), min(lons), max(lons)
    clat, clon = (la0 + la1) / 2, (lo0 + lo1) / 2
    kx = math.cos(math.radians(clat))
    lat_span, lon_span = la1 - la0, (lo1 - lo0) * kx            # both in lat-degree units
    vis_wide = max(lat_span * 1.45, lon_span * 1.45 / RATIO, 4.2)
    h_deg = max(10.0, vis_wide * 1.7)                           # region height (lat degrees)
    w_deg = max(7.5, lon_span * 1.3 + 4.0, h_deg * 0.78)        # region width in lat-degree units
    lat0, lat1 = clat - h_deg / 2, clat + h_deg / 2
    lat0, lat1 = max(lat0, -70), min(lat1, 78)
    lon0, lon1 = clon - w_deg / kx / 2, clon + w_deg / kx / 2
    r = lambda v: round(v * 2) / 2                              # snap to 0.5 deg so nearby topics share a cache
    lat0, lat1, lon0, lon1 = math.floor(lat0 * 2) / 2, math.ceil(lat1 * 2) / 2, math.floor(lon0 * 2) / 2, math.ceil(lon1 * 2) / 2
    kxm = math.cos(math.radians((lat0 + lat1) / 2))
    area = (lat1 - lat0) * (lon1 - lon0) * kxm
    ppd = int(max(110, min(320, math.sqrt(9.5e6 / max(area, 1e-6)))))
    name = "auto_" + "_".join(f"{v:g}".replace("-", "m").replace(".", "p") for v in (lat0, lat1, lon0, lon1))
    return dict(name=name, lon0=lon0, lon1=lon1, lat0=lat0, lat1=lat1, ppd=ppd, vis_wide=float(min(vis_wide, h_deg * 0.72)), center=(clat, clon))


def have(name): return (ASSETS / f"terrain_{name}.json").exists() and (ASSETS / f"terrain_{name}.png").exists()


def start_build(reg):
    """Popen the builder (so it can overlap with the TTS stage). returns Popen or None when cached."""
    if have(reg["name"]): return None
    code = ("import sys; sys.path.insert(0, %r); import build_terrain as B; B.build(%r, %r, %r, %r, %r, float(%r), force=False)"
            % (str(ROOT / "mapfx"), reg["name"], reg["lon0"], reg["lon1"], reg["lat0"], reg["lat1"], reg["ppd"]))
    return subprocess.Popen([sys.executable, "-c", code])
