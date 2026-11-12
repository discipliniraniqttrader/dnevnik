"""Synthesised music + sound effects, mixed under the narration."""
import numpy as np

SR = 24000
RNG = np.random.default_rng(42)


def noise(n):
    return RNG.standard_normal(n).astype(np.float32)


def bp(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.clip((f - lo) / (lo * 0.3 + 1), 0, 1) * np.clip((hi - f) / (hi * 0.3 + 1), 0, 1)
    return np.fft.irfft(X * m, len(x)).astype(np.float32)


def add(buf, t, snd, gain=1.0):
    i = int(t * SR)
    if i >= len(buf) or i + len(snd) <= 0:
        return
    a = max(0, -i); e = min(len(snd), len(buf) - i)
    buf[i + a:i + e] += snd[a:e] * gain


def whoosh(dur=0.3):
    n = int(dur * SR); x = np.linspace(0, 1, n)
    z = noise(n)
    lo, mid, hi = bp(z, 120, 700), bp(z, 600, 2500), bp(z, 2000, 9000)
    sw = np.exp(-((x - 0.25) / 0.2) ** 2) * lo * .6 + np.exp(-((x - 0.5) / 0.22) ** 2) * mid + np.exp(-((x - 0.75) / 0.2) ** 2) * hi * .8
    sw *= np.sin(np.pi * x) ** 1.3
    return sw / (np.max(np.abs(sw)) + 1e-6)


def impact():
    n = int(1.2 * SR); x = np.arange(n) / SR
    f = 38 + 110 * np.exp(-x * 9)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-x * 3.2)
    nz = bp(noise(n), 40, 2400) * np.exp(-x * 14)
    out = s + 0.8 * nz
    return out / np.max(np.abs(out))


def pop(f0=520):
    n = int(0.14 * SR); x = np.arange(n) / SR
    s = np.sin(2 * np.pi * (f0 * 0.6 + f0 * .5 * np.exp(-x * 40)) * x) * np.exp(-x * 32)
    s[:20] += 0.3 * noise(20)
    return s.astype(np.float32)


def tick():
    n = int(0.012 * SR)
    return bp(noise(n * 3), 1500, 6000)[:n] * np.exp(-np.arange(n) / (n / 4))


def thunder():
    n = int(2.6 * SR); x = np.arange(n) / SR
    crack = bp(noise(n), 200, 8000) * np.exp(-x * 40)
    roll = bp(noise(n), 30, 260) * np.exp(-x * 1.5) * (0.6 + 0.4 * np.sin(2 * np.pi * x * 5.5 + 1))
    out = crack * 1.0 + roll * 2.2
    return out / np.max(np.abs(out))


def music(total):
    n = int(total * SR); t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    chords = [(146.83, 174.61, 220.0), (116.54, 146.83, 174.61), (130.81, 164.81, 196.0), (110.0, 130.81, 164.81)]
    seg = 4.0
    for ci in range(int(total / seg) + 1):
        f = chords[ci % 4]; s0 = ci * seg
        idx = (t >= s0 - .5) & (t < s0 + seg + 1.5); tt = t[idx] - s0
        env = np.clip(tt / 1.0, 0, 1) * np.clip((seg + 1.5 - tt) / 1.6, 0, 1)
        sig = np.zeros_like(tt)
        for fr in f:
            for det in (-0.6, 0.6):
                sig += np.sin(2 * np.pi * (fr + det) * tt) * .5 + np.sin(2 * np.pi * (fr * 2 + det) * tt) * .14
        sig += np.sin(2 * np.pi * f[0] / 2 * tt) * .8
        out[idx] += (sig * env).astype(np.float32)
    out /= np.max(np.abs(out)) + 1e-6
    # pulse: soft low thump at 100 bpm, light off-beat tick
    beat = 60 / 100
    kick = np.zeros(n, np.float32)
    kn = int(0.28 * SR); kx = np.arange(kn) / SR
    k = np.sin(2 * np.pi * np.cumsum(48 + 60 * np.exp(-kx * 22)) / SR) * np.exp(-kx * 11)
    ht = bp(noise(int(0.05 * SR)), 5000, 10000) * np.exp(-np.arange(int(0.05 * SR)) / (0.012 * SR))
    for i in range(int(total / beat)):
        add(kick, 0.4 + i * beat, k.astype(np.float32), 1.0)
        add(kick, 0.4 + i * beat + beat / 2, ht.astype(np.float32), 0.10)
    out = out * 0.55 + kick * 0.9
    out *= np.clip(t / 1.2, 0, 1) * np.clip((total - t) / 1.8, 0, 1)
    return out


def env_noise(total, a, b, lo, hi, mod_hz, depth, fade=0.7):
    n = int(total * SR); t = np.arange(n) / SR
    i0, i1 = int(a * SR), int(min(b, total) * SR)
    z = bp(noise(i1 - i0), lo, hi)
    z /= np.max(np.abs(z)) + 1e-6
    tt = t[i0:i1]
    g = (1 - depth + depth * (0.5 + 0.5 * np.sin(2 * np.pi * mod_hz * (tt - a)))) * np.clip((tt - a) / fade, 0, 1) * np.clip((b - tt) / fade, 0, 1)
    out = np.zeros(n, np.float32); out[i0:i1] = z * g
    return out


def mix(voice, total, ev):
    n = int(total * SR)
    v = np.zeros(n, np.float32); v[:min(n, len(voice))] = voice[:n]
    # voice activity envelope (for ducking)
    hop = SR // 50
    rms = np.sqrt(np.convolve(v ** 2, np.ones(hop) / hop, mode="same"))
    act = np.clip(rms / 0.03, 0, 1)
    act = np.convolve(act, np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
    vr = np.sqrt(np.mean(v[rms > 0.02] ** 2))
    mus = music(total)
    mus = mus / (np.sqrt(np.mean(mus ** 2)) + 1e-9) * vr * 0.1       # about -20 dB under the voice
    mus *= 1 - 0.5 * act                                              # duck under speech
    s = np.zeros(n, np.float32)
    peak = 0.89
    wh, wp, im, th = whoosh(0.28), whoosh(0.42), impact(), thunder()
    for t in ev["whoosh"]:
        add(s, t - 0.14, wh, peak * 0.30)
    for t in ev["whip"]:
        add(s, t - 0.22, wp, peak * 0.38)
    for t in ev["impact"]:
        add(s, t, im, peak * 0.42)
    for t in ev["thunder"]:
        add(s, t, th, peak * 0.40)
    for t in ev["pop"]:
        add(s, t, pop(520), peak * 0.30)
    for t in ev["place"]:
        add(s, t, pop(760), peak * 0.22)
    tk = tick()
    for i, t in enumerate(ev["tick"]):
        add(s, t, tk, peak * 0.16)
    for (a, b) in ev.get("ocean", []):
        s += env_noise(total, a, b, 60, 900, 1 / 3.4, 0.6) * peak * 0.30
    for (a, b) in ev.get("wind", []):
        s += env_noise(total, a, b, 250, 1400, 1 / 5.0, 0.55, 1.2) * peak * 0.16
    for (a, b) in ev.get("rumble", []):
        s += env_noise(total, a, b, 25, 120, 1 / 2.0, 0.4, 0.3) * peak * 0.55
    out = v + mus + s
    pk = np.max(np.abs(out))
    out = out / pk * 0.891
    return out.astype(np.float32)
