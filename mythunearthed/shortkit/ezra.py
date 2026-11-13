"""Ezra (3D presenter) track: timeline from the voice envelope + actions -> presenter/render.js, cached by content hash."""
import hashlib, json, math, subprocess
from pathlib import Path
import numpy as np
from .common import ROOT, FPS
from .voice import SR


def timeline(voice, total, acts):
    n = int(math.ceil(total * FPS)); hop = SR // FPS
    rms = np.array([np.sqrt(np.mean(voice[i * hop:(i + 1) * hop + hop // 2] ** 2) + 1e-12) if i * hop < len(voice) else 0.0 for i in range(n)])
    rms = rms / (np.percentile(rms, 95) + 1e-9)
    m = np.clip(rms, 0, 1); m[rms < 0.06] = 0
    sm = m.copy(); sm[1:] = 0.55 * m[1:] + 0.45 * m[:-1]; sm[sm < 0.05] = 0
    return {"fps": FPS, "duration": n / FPS, "camera": "half", "mouth": [round(float(x), 3) for x in sm],
            "actions": [{"t": round(float(t), 3), "d": round(float(d), 3), "type": ty} for t, d, ty in acts]}, n


def ensure(cache_dir, voice, total, acts, render=True):
    """returns (dir, n_frames). Re-renders only when mouth/actions change."""
    tl, n = timeline(voice, total, acts)
    h = hashlib.sha1(json.dumps(tl, sort_keys=True).encode()).hexdigest()[:12]
    d = Path(cache_dir) / f"ezra_{h}"
    if len(list(d.glob("*.png"))) >= n: return d, n, False
    if not render: return d, n, False
    d.mkdir(parents=True, exist_ok=True)
    tlp = Path(cache_dir) / f"ezra_{h}.json"; json.dump(tl, open(tlp, "w"))
    subprocess.run(["node", str(ROOT / "presenter/render.js"), str(tlp), str(d)], check=True, cwd=str(ROOT / "presenter"))
    return d, n, True
