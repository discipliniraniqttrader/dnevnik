"""Script data + narration for the Exodus Short."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
SR = 24000
VOICE = "am_michael"

# text, camera focus (lat, lon), callout, passage
BEATS = [
    ("Six hundred thousand men on foot walked out of Egypt. So where did they go?", (30.8, 31.8), "600,000 MEN", "Exodus 12:37"),
    ("The journey begins at Rameses, in Egypt's eastern Nile Delta.", (30.80, 31.83), "RAMESES", "Num 33:3"),
    ("They head east to Succoth, then camp at Etham, on the wilderness edge.", (30.5, 32.2), None, "Num 33:5–6"),
    ("Pharaoh's chariots close in as they camp by Pi-hahiroth, near the sea.", (30.10, 32.50), "CHARIOTS", "Exodus 14:9"),
    ("The text says the waters divide, and Israel crosses on dry ground.", (29.95, 32.55), "SEA CROSSING", "Exodus 14:21–22"),
    ("The exact route is debated, so every marker here is approximate.", (29.0, 33.3), "ROUTE DEBATED", None),
    ("Three days on, the water at Marah is too bitter to drink.", (29.15, 32.95), "BITTER WATER", "Exodus 15:22–23"),
    ("Then Elim, with twelve springs and seventy palm trees.", (28.95, 33.05), "12 SPRINGS · 70 PALMS", "Exodus 15:27"),
    ("In the Wilderness of Sin, the people are starving, and manna appears.", (28.65, 33.45), "MANNA", "Exodus 16:1–15"),
    ("At Rephidim, they fight Amalek.", (28.70, 33.60), "AMALEK", "Exodus 17:8"),
    ("In the third month, they camp before the mountain.", (28.54, 33.97), "MOUNT SINAI", "Exodus 19:1–2"),
    ("Tradition places it at Jebel Musa, though other sites are proposed.", (28.54, 33.97), "TRADITIONAL SITE", None),
    ("Forty years later, Israel reaches the plains of Moab, by the Jordan.", (31.80, 35.55), "40 YEARS", "Num 33:48–49"),
    ("Where do you think the real Mount Sinai is?", None, "COMMENT BELOW", None),
]


def narrate(cache=HERE / "narration.npz"):
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        return z["voice"], json.loads(str(z["beats"])), float(z["total"])
    from kokoro_onnx import Kokoro
    A = HERE.parent / "assets"
    k = Kokoro(str(A / "kokoro/model.onnx"), str(A / "kokoro/voices.npz"))
    clips, beats, t = [], [], 0.5
    for i, b in enumerate(BEATS):
        a, sr = k.create(b[0], voice=VOICE, speed=1.04, lang="en-us")
        assert sr == SR
        a = a / (np.max(np.abs(a)) + 1e-6) * 0.89
        dur = len(a) / SR
        hold = 0.12 if i < len(BEATS) - 1 else 1.6
        beats.append({"t0": t, "speech": dur, "t1": t + dur + hold})
        clips.append((t, a))
        t += dur + hold
    voice = np.zeros(int(t * SR) + SR, np.float32)
    for t0, a in clips:
        i = int(t0 * SR)
        voice[i:i + len(a)] += a
    voice = voice[: int(t * SR)]
    np.savez(cache, voice=voice, beats=json.dumps(beats), total=t)
    return voice, beats, t


# Ezra actions (global time)
ACTIONS = [
    (0.0, 3.6, "idle"), (3.6, 1.8, "shrug"),
    (5.57, 4.2, "point_right"), (9.76, 4.3, "point_right"), (14.07, 4.5, "point_right"),
    (18.56, 4.6, "surprised"), (23.16, 2.4, "shrug"), (25.6, 1.84, "point_right"),
    (27.44, 3.5, "point_right"), (30.93, 3.5, "point_right"), (34.46, 3.9, "point_right"),
    (38.36, 2.04, "point_right"), (40.4, 2.83, "surprised"),
    (43.23, 2.2, "point_right"), (45.45, 2.3, "shrug"),
    (47.72, 4.86, "point_right"), (52.58, 2.0, "shrug"), (54.6, 2.2, "wave"),
]


def ezra_timeline(voice, total, path):
    n = int(np.ceil(total * 30))
    hop = SR // 30
    rms = np.array([np.sqrt(np.mean(voice[i * hop:(i + 1) * hop + hop // 2] ** 2) + 1e-12) for i in range(n)])
    rms = rms / (np.percentile(rms, 95) + 1e-9)
    m = np.clip(rms, 0, 1)
    m[rms < 0.06] = 0
    sm = m.copy()
    sm[1:] = 0.55 * m[1:] + 0.45 * m[:-1]
    sm[sm < 0.05] = 0
    tl = {"fps": 30, "duration": total, "camera": "half", "mouth": [round(float(x), 3) for x in sm],
          "actions": [{"t": t, "d": d, "type": ty} for t, d, ty in ACTIONS]}
    json.dump(tl, open(path, "w"))
    return n
