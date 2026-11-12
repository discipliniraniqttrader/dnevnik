"""Script data, narration assembly (Chatterbox per-beat WAVs), word timings for the Noah Short."""
import json, re
from pathlib import Path
import numpy as np, soundfile as sf
from scipy.signal import resample_poly

HERE = Path(__file__).resolve().parent
SR = 24000
SCRIPT = json.load(open(HERE / "script.json"))
BEATS = SCRIPT["beats"]
GAP = 0.08
LEAD = 0.30


def _trim(a, sr):
    env = np.abs(a)
    hop = int(sr * 0.01)
    e = np.sqrt(np.convolve(a ** 2, np.ones(hop) / hop, mode="same"))
    thr = max(np.percentile(e, 98) * 0.035, 1e-4)
    idx = np.nonzero(e > thr)[0]
    i0 = max(0, idx[0] - int(0.03 * sr)); i1 = min(len(a), idx[-1] + int(0.05 * sr))
    return a[i0:i1]


def narrate(cache=HERE / "narration.npz"):
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        return z["voice"], json.loads(str(z["beats"])), float(z["total"])
    clips = []
    for i in range(1, len(BEATS) + 1):
        a, sr = sf.read(HERE / "voice" / "stretch" / f"beat{i:02d}.wav", dtype="float32")
        if a.ndim > 1: a = a.mean(1)
        if sr != SR: a = resample_poly(a, SR, sr).astype(np.float32)
        a = _trim(a, SR)
        # fades to kill clicks
        f = int(0.012 * SR); a[:f] *= np.linspace(0, 1, f); a[-f:] *= np.linspace(1, 0, f)
        clips.append(a)
    # consistent loudness: RMS over active samples -> common target
    tgt = 0.085
    out = []
    for a in clips:
        act = a[np.abs(a) > 0.02 * np.max(np.abs(a))]
        a = a * (tgt / (np.sqrt(np.mean(act ** 2)) + 1e-9))
        a = np.tanh(a / 0.8) * 0.8 if np.max(np.abs(a)) > 0.8 else a      # soft limit
        out.append(a.astype(np.float32))
    beats, t = [], LEAD
    for i, a in enumerate(out):
        dur = len(a) / SR
        hold = (0.2 if i == len(out) - 2 else GAP) if i < len(out) - 1 else 2.2
        beats.append({"t0": t, "speech": dur, "t1": t + dur + hold})
        t += dur + hold
    voice = np.zeros(int(t * SR) + SR, np.float32)
    for b, a in zip(beats, out):
        i = int(b["t0"] * SR); voice[i:i + len(a)] += a
    voice = voice[: int(t * SR)]
    pk = np.max(np.abs(voice)); voice *= 0.89 / pk
    np.savez(cache, voice=voice, beats=json.dumps(beats), total=t)
    return voice, beats, t


def word_times(text, t0, dur, voice=None):
    """Word start/end. Weights by letters, but phrase boundaries (, . : ? ') snap to real pauses in the audio when found."""
    words = text.split()
    w = [len(re.sub(r"[^\w]", "", x)) + 1.2 for x in words]
    brk = [i for i, x in enumerate(words[:-1]) if x[-1] in ",.:;?!"]   # boundary AFTER word i
    bounds = None
    if voice is not None and brk:
        a = voice[int(t0 * SR): int((t0 + dur) * SR)]
        hop = int(0.01 * SR)
        n = len(a) // hop
        e = np.sqrt((a[: n * hop].reshape(n, hop) ** 2).mean(1))
        thr = max(np.percentile(e, 90) * 0.12, 1e-4)
        sil = e < thr
        runs, i = [], 0
        while i < n:
            if sil[i]:
                j = i
                while j < n and sil[j]: j += 1
                if j - i >= 5 and i > 8 and j < n - 4: runs.append((j - i, (i + j) / 2 * 0.01))
                i = j
            else: i += 1
        if len(runs) >= len(brk):
            cw = np.cumsum(w) / np.sum(w)
            chosen, last = [], -1
            for b in brk:
                pk = cw[b] * dur
                best = None
                for ri, (ln, tc) in enumerate(runs):
                    if ri <= last: continue
                    sc = ln * 0.01 - 0.6 * abs(tc - pk)
                    if best is None or sc > best[0]: best = (sc, ri)
                if best is None: chosen = None; break
                chosen.append(runs[best[1]][1]); last = best[1]
            bounds = chosen
    out, ws = [], np.array(w)
    if bounds is None:
        tot = ws.sum(); t = t0
        for x, wt in zip(words, ws):
            d = dur * wt / tot; out.append((x, t, t + d)); t += d
        return out
    edges = [0.0] + bounds + [dur]; ids = [0] + [b + 1 for b in brk] + [len(words)]
    for k in range(len(edges) - 1):
        seg = ws[ids[k]: ids[k + 1]]
        a, b = edges[k], edges[k + 1]
        t = a
        for x, wt in zip(words[ids[k]: ids[k + 1]], seg):
            d = (b - a) * wt / seg.sum(); out.append((x, t0 + t, t0 + t + d)); t += d
    return out


if __name__ == "__main__":
    v, bt, tot = narrate()
    print(tot)
    for i, b in enumerate(bt): print(i + 1, round(b["t0"], 2), round(b["speech"], 2))
