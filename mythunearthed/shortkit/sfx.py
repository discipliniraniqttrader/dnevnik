"""Music + SFX mix (primitives from exodus/sfx.py, bird/shatter/shimmer from the Noah Short)."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exodus import sfx as X
from exodus.sfx import SR, add, noise, bp, whoosh, impact, pop, tick, thunder, music, env_noise


def flap():
    n = int(0.16 * SR); x = np.arange(n) / SR
    z = bp(noise(n), 300, 2400) * np.exp(-x * 24) * (np.sin(np.pi * np.clip(x / 0.16, 0, 1)) ** .6)
    return z / (np.max(np.abs(z)) + 1e-6)


def bird_whoosh():
    w = whoosh(0.5); return w * np.linspace(1, .6, len(w))


def shatter():
    n = int(1.4 * SR); x = np.arange(n) / SR
    out = bp(noise(n), 1500, 9000) * np.exp(-x * 7)
    for k in range(26):
        t0 = np.random.default_rng(k).uniform(0, .6); f = np.random.default_rng(k + 50).uniform(2200, 6500)
        i = int(t0 * SR); m = int(.12 * SR); tt = np.arange(m) / SR
        out[i:i + m] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 40) * .5
    return out / (np.max(np.abs(out)) + 1e-6)


def shimmer(d=2.6):
    n = int(d * SR); x = np.arange(n) / SR; out = np.zeros(n, np.float32)
    for f in (523, 659, 784, 1047, 1319): out += np.sin(2 * np.pi * f * x + np.sin(x * 5 + f)) * np.sin(np.pi * x / d) ** 2 / 5
    return out.astype(np.float32)


def mix(voice, total, ev):
    n = int(total * SR)
    v = np.zeros(n, np.float32); v[:min(n, len(voice))] = voice[:n]
    hop = SR // 50
    rms = np.sqrt(np.convolve(v ** 2, np.ones(hop) / hop, mode="same"))
    act = np.clip(rms / 0.03, 0, 1); act = np.convolve(act, np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
    vr = np.sqrt(np.mean(v[rms > 0.02] ** 2))
    mus = music(total); mus = mus / (np.sqrt(np.mean(mus ** 2)) + 1e-9) * vr * 0.1; mus *= 1 - 0.5 * act
    s = np.zeros(n, np.float32); peak = 0.89
    wh, wp, im, th = whoosh(0.28), whoosh(0.42), impact(), thunder()
    for t in ev["whoosh"]: add(s, t - 0.14, wh, peak * 0.14)
    for t in ev["whip"]: add(s, t - 0.22, wp, peak * 0.38)
    for t in ev["impact"]: add(s, t, im, peak * 0.42)
    for t in ev["thunder"]: add(s, t, th, peak * 0.30)
    for t in ev["pop"]: add(s, t, pop(520), peak * 0.30)
    for t in ev["place"]: add(s, t, pop(760), peak * 0.22)
    tk = tick()
    for t in ev["tick"]: add(s, t, tk, peak * 0.16)
    fl = flap()
    for t in ev["flap"]: add(s, t, fl, peak * 0.22)
    bw = bird_whoosh()
    for t in ev["birdwhoosh"]: add(s, t - .05, bw, peak * 0.34)
    sh = shatter()
    for t in ev["shatter"]: add(s, t, sh, peak * 0.34)
    sm = shimmer()
    for t in ev["shimmer"]: add(s, t, sm, peak * 0.22)
    for (a, b) in ev["wind"]: s += env_noise(total, a, b, 250, 1400, 1 / 5.0, 0.55, 1.2) * peak * 0.16
    for (a, b) in ev["ocean"]: s += env_noise(total, a, b, 60, 900, 1 / 3.4, 0.6) * peak * 0.30
    for (a, b) in ev["rumble"]: s += env_noise(total, a, b, 25, 120, 1 / 2.0, 0.4, 0.3) * peak * 0.45
    out = v + mus + s
    out = out / np.max(np.abs(out)) * 0.891
    return out.astype(np.float32)
