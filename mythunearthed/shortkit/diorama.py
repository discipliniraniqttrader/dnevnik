"""STYLE "diorama": procedural three.js toon-3D world (presenter/diorama.html via Playwright) + anchored overlays + captions.

Pipeline: voice -> plan (beat bounds, caption groups) -> node renders 3D frames + projected anchors (JSON) -> Python composes
(dip transition, grade, anchored callouts/dimension lines, captions) -> chunked x264 -> mux -> 9 MB HEVC -> sheet -> report.json
"""
import hashlib, json, math, multiprocessing as mp, os, pickle, subprocess, sys, time
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw
from .common import W, H, FPS, F, ease, MONT_BLACK
from . import silhouette as SIL

ROOT = Path(__file__).resolve().parent.parent
GOLD, CREAM, INKC, YEL = (255, 196, 46), (250, 242, 222), (20, 14, 12), (255, 210, 63)
CAPTOP = 1440                      # overlay boxes must stay above this y (caption pill zone starts ~1465)
DIP, DIPLEN = 0.30, 0.70            # dip depth (min brightness factor) and half-length (s) of the soft transition at beat bounds
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def sstep(x): x = clamp(x); return x * x * (3 - 2 * x)

def load_defs(slug):
    """per-topic scene plan + overlays: shortkit/dio_topics/<slug>.py -> SCENES [(scene_name, [beat numbers 1-based])], OV {beat number: [overlay dicts]}, AUDIO {rain, thunder, creaks}"""
    import importlib
    return importlib.import_module(f"shortkit.dio_topics.{slug}")


def project(view, proj, w):
    v = np.array(view, np.float64).reshape(4, 4).T; p = np.array(proj, np.float64).reshape(4, 4).T
    c = p @ (v @ np.array([w[0], w[1], w[2], 1.0])); n = c[:3] / c[3]
    return ((n[0] * 0.5 + 0.5) * W, (1 - (n[1] * 0.5 + 0.5)) * H)


MIN_SCENE = 4.5                      # owner rule: a scene lasts at least this long (consecutive beats are grouped into one set)


def build_plan(S, voice, BT, TOTAL):
    D = load_defs(S["topic"]); kwm = getattr(D, "KW", {}) or {}               # KW = {beat number: word literally in the text} where the script keyword is not (spoken text stays untouched)
    S = dict(S, beats=[dict(b, keyword=kwm.get(b["i"], b["keyword"])) for b in S["beats"]])
    P = SIL.build_plan(S, voice, BT, TOTAL); bounds = P["bounds"]; nb = len(S["beats"])
    scenes, seen = [], []
    for name, bs in D.SCENES:
        scenes.append(dict(name=name, b0=bs[0] - 1, b1=bs[-1], t0=bounds[bs[0] - 1], t1=bounds[bs[-1]])); seen += list(bs)
    assert seen == list(range(1, nb + 1)), f"SCENES must cover beats 1..{nb} in order, got {seen}"
    P["diplen"] = float(getattr(D, "DIPLEN", DIPLEN)); P["scenes"] = scenes; P["sbounds"] = [scenes[0]["t0"]] + [x["t1"] for x in scenes]
    P["ov"] = {int(k) - 1: v for k, v in D.OV.items()}; P["topic"] = S["topic"]
    au = getattr(D, "AUDIO", {}) or {}
    bt = lambda x: float(np.interp(x - 1, range(nb + 1), bounds))          # beat coordinate (1.0 = start of beat 1, 2.5 = middle of beat 2) -> seconds
    P["creaks"] = [bt(x) for x in au.get("creaks", [])]; P["thunder"] = [bt(x) for x in au.get("thunder", [])]
    rp = au.get("rain", [(1, 0.0), (nb + 1, 0.0)]); P["rain_pts"] = ([bt(x) for x, _ in rp], [v for _, v in rp]); P["whoosh"] = list(P["sbounds"][1:-1])
    P["short_scenes"] = [(x["name"], round(x["t1"] - x["t0"], 2)) for x in scenes if x["t1"] - x["t0"] < MIN_SCENE - 0.05]
    P["fps"] = FPS; return P


def dip_w(t, bounds, L=DIPLEN):
    w = 0.0
    for b in bounds[1:-1]:
        d = abs(t - b)
        if d < L: w = max(w, sstep(1 - d / L))
    return w


def dip_factor(t, bounds):
    f = 1.0
    for b in bounds[1:-1]:
        d = abs(t - b)
        if d < DIPLEN: f = min(f, 1 - (1 - DIP) * sstep(1 - d / DIPLEN))
    return f


class Composer:
    def __init__(s, plan_path):
        s.P = pickle.load(open(plan_path, "rb")); s.dir = Path(s.P["frames_dir"]); s.meta = {}; s.rec = []; s.mt = 9999.0
        for m in s.dir.glob("meta_*.json"): s.meta.update({int(k): v for k, v in json.load(open(m)).items()})
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        s.vig = (1.0 - 0.26 * np.clip(r - 0.5, 0, 1) ** 1.5)[..., None].astype(np.float32); s.rng = np.random.default_rng(3)

    def grade(s, a):
        a = a.astype(np.float32)
        sm = cv2.resize(a, (W // 6, H // 6), interpolation=cv2.INTER_AREA); br = np.clip(sm - 185, 0, 70) * 1.3
        bl = cv2.resize(cv2.GaussianBlur(br, (0, 0), 5), (W, H), interpolation=cv2.INTER_LINEAR)
        a = a * s.vig + bl * 0.5
        g = s.rng.standard_normal((H // 2, W // 2)).astype(np.float32) * 1.6
        a += cv2.resize(g, (W, H), interpolation=cv2.INTER_NEAREST)[..., None]
        return a

    # ---------- overlays
    def box(s, img, cx, cy, txt, size, al, pad=22, fill=(24, 16, 14), edge=GOLD, minw=0):
        f = F(MONT_BLACK, size); tw = f.getlength(txt); bw, bh = max(tw + 2 * pad, minw), size + pad
        x0, y0, x1, y1 = cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2
        im = Image.fromarray(img).convert("RGBA"); lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.rounded_rectangle([x0, y0, x1, y1], radius=int(bh * 0.32), fill=fill + (int(235 * al),), outline=edge + (int(255 * al),), width=4)
        d.text((cx, cy + 2), txt, font=f, fill=CREAM + (int(255 * al),), anchor="mm")
        s.mt = min(s.mt, size); s.rec.append(dict(kind="box", box=(x0, y0, x1, y1)))
        return np.asarray(Image.alpha_composite(im, lay).convert("RGB")), (x0, y0, x1, y1)

    @staticmethod
    def ln(img, p, q, col, th, al):
        if al <= 0.01: return img
        ov = img.copy(); P_ = lambda v: (int(round(v[0] * 16)), int(round(v[1] * 16)))
        cv2.line(ov, P_(p), P_(q), col, th, cv2.LINE_AA, 4); return cv2.addWeighted(ov, al, img, 1 - al, 0)

    @staticmethod
    def dot(img, p, r, col, al):
        ov = img.copy(); P_ = (int(round(p[0] * 16)), int(round(p[1] * 16)))
        cv2.circle(ov, P_, int(r * 16), col, -1, cv2.LINE_AA, 4); cv2.circle(ov, P_, int(r * 16), INKC, 2, cv2.LINE_AA, 4); return cv2.addWeighted(ov, al, img, 1 - al, 0)

    def overlays(s, img, t, fi, bi, ff):
        M = s.meta.get(fi)
        if M is None: return img
        spec = s.P["ov"].get(bi, []); lt = t - s.P["bounds"][bi]; A = M["anchors"]
        fade = clamp((ff - DIP) / (1 - DIP))
        for o in spec:
            t0, d = o["t0"], o.get("d", 0.6); t1 = o.get("t1", s.P["bounds"][bi + 1] - s.P["bounds"][bi] - 0.1)
            al = clamp((lt - t0) / 0.2) * (1 - clamp((lt - t1 + 0.0) / 0.25)) * fade
            if al <= 0.01: continue
            prog = ease((lt - t0) / d); k = o["k"]
            def P(n): return tuple(A[n]["p"])
            def np_(n): return project(M["view"], M["proj"], A[n]["w"])
            if k == "callout":
                tg = P(o["a"]); bo = o["box"]; size = 46; f = F(MONT_BLACK, size); fmt = (lambda v, dec: f"{v:.{dec}f}" if o.get("raw") else f"{v:,.{dec}f}")
                tw = f.getlength(o["label"])
                if "counter" in o: c0_, c1_, un_ = o["counter"][:3]; dec_ = o["counter"][3] if len(o["counter"]) > 3 else 0; tw = max(tw, f.getlength(fmt(c0_, dec_) + un_), f.getlength(fmt(c1_, dec_) + un_))
                bw, bh = tw + 44, size + 22
                bc = (min(max(tg[0] + bo[0], bw / 2 + 30), W - bw / 2 - 30), min(max(tg[1] + bo[1], 150), CAPTOP - bh / 2 - 10))
                dx, dy = tg[0] - bc[0], tg[1] - bc[1]; kx = (bw / 2) / abs(dx) if abs(dx) > 1e-6 else 1e9; ky = (bh / 2) / abs(dy) if abs(dy) > 1e-6 else 1e9; kk = min(kx, ky)
                st = (bc[0] + dx * kk, bc[1] + dy * kk); e = (st[0] + (tg[0] - st[0]) * prog, st[1] + (tg[1] - st[1]) * prog)
                img = s.ln(img, st, e, GOLD, 5, al)
                lab_ = o["label"]
                if "counter" in o: c0, c1, un = o["counter"][:3]; dec = o["counter"][3] if len(o["counter"]) > 3 else 0; v_ = c0 + (c1 - c0) * ease((lt - t0) / o.get("cd", 1.0)); lab_ = fmt(v_, dec) + un
                img, bx = s.box(img, bc[0], bc[1], lab_, size, al, minw=bw)
                if prog > 0.97: img = s.dot(img, tg, 10, GOLD, al)
                tn = np_(o["a"]); s.rec.append(dict(kind="callout", beat=bi + 1, target=tn, drawn=tg if prog > 0.97 else None, start=st, box=bx))
            elif k == "cross":
                c = P(o["a"]); r = 120 * (0.6 + 0.4 * ease((lt - t0) / 0.25)); cc = (60, 50, 235)
                img = s.ln(img, (c[0] - r, c[1] - r), (c[0] + r, c[1] + r), cc, 22, al); img = s.ln(img, (c[0] + r, c[1] - r), (c[0] - r, c[1] + r), cc, 22, al)
            elif k == "dim":
                a, b = np.array(P(o["a"])), np.array(P(o["b"])); off = np.array(o["off"], float); a2, b2 = a + off, b + off
                u = b2 - a2; L = np.hypot(*u) + 1e-6; n = np.array([-u[1], u[0]]) / L; e = a2 + u * prog
                img = s.ln(img, a, a2, CREAM, 3, al * 0.8); img = s.ln(img, b, b2, CREAM, 3, al * 0.8 * (prog > 0.5))
                img = s.ln(img, a2, e, GOLD, 6, al)
                for p_, show in ((a2, True), (b2, prog > 0.98)):
                    if show: img = s.ln(img, p_ - n * 24, p_ + n * 24, GOLD, 6, al)
                img = s.dot(img, a, 9, GOLD, al); img = s.dot(img, b, 9, GOLD, al)
                lab = o["label"]
                if "counter" in o: c0, c1, un = o["counter"][:3]; dec = o["counter"][3] if len(o["counter"]) > 3 else 0; lab = f"{c0 + (c1 - c0) * prog:,.{dec}f}{un}"
                mid = (a2 + b2) / 2; lw = F(MONT_BLACK, 52).getlength(lab) / 2 + 52; mid = np.array([clamp(mid[0], lw + 30, W - lw - 30), clamp(mid[1], 150, CAPTOP - 50)])
                if prog > 0.45 or "counter" in o: img, _ = s.box(img, mid[0], mid[1], lab, 52, al * clamp((prog - 0.4) / 0.3) if "counter" not in o else al)
                for nm, pt in ((o["a"], a), (o["b"], b)): s.rec.append(dict(kind="dim", beat=bi + 1, target=np_(nm), drawn=tuple(pt), tick=tuple(pt)))
        return img

    def captions(s, img, t):
        c = None
        for cc in s.P["caps"]:
            if cc["t0"] - 1e-3 <= t < cc["t1"]: c = cc; break
        if c is None: return img
        size = 54; words = c["words"]
        def width(sz): return sum(F(MONT_BLACK, sz).getlength(w) for w in words) + sz * 0.3 * (len(words) - 1)
        while width(size) > 820 and size > 46: size -= 2
        s.mt = min(s.mt, size); f = F(MONT_BLACK, size); tw = width(size); x = 540 - tw / 2; cy = 1520
        im = Image.fromarray(img).convert("RGBA"); lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.rounded_rectangle([540 - tw / 2 - 40, cy - size * 0.85, 540 + tw / 2 + 40, cy + size * 0.85], radius=int(size * 0.85), fill=(40, 26, 40, 205))
        for w, isk in zip(words, c["kw"]):
            d.text((x, cy + 2), w, font=f, fill=(YEL if isk else (255, 255, 255)) + (255,), anchor="lm"); x += f.getlength(w) + size * 0.3
        return np.asarray(Image.alpha_composite(im, lay).convert("RGB"))

    def frame(s, fi):
        t = fi / FPS; s.rec = []; bi = max(0, min(len(s.P["bounds"]) - 2, int(np.searchsorted(s.P["bounds"], t, side="right") - 1)))
        a = np.asarray(Image.open(s.dir / f"{fi:05d}.jpg").convert("RGB"))
        w = dip_w(t, s.P["sbounds"], s.P.get("diplen", DIPLEN)); a = s.grade(a); mm = float(a[::8, ::8].mean()); g = 1.0 - w * (1.0 - min(1.0, 38.0 / max(mm, 1.0))); ff = max(g, 0.0) if w > 0 else 1.0
        a = np.clip(a * g, 0, 255).astype(np.uint8); ff = clamp((1 - w * 0.7), DIP, 1.0)
        a = s.overlays(a, t, fi, bi, ff); a = s.captions(a, t)
        return a


_R = None
def init_worker(pp):
    global _R; cv2.setNumThreads(1); _R = Composer(pp)


def render_chunk(job):
    idx, f0, f1, outdir, key = job
    path = Path(outdir) / f"_part{idx:03d}.mp4"; side = Path(outdir) / f"_part{idx:03d}.json"; n = f1 - f0
    m = SIL.chunk_ok(path, side, n, key)
    if m is not None: return str(path), m["means"], m["mintext"], m["rec"], True
    tmp = Path(outdir) / f"_part{idx:03d}.tmp.mp4"
    for q in (tmp, path, side): q.unlink(missing_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)], stdin=subprocess.PIPE)
    means, recs = [], []; _R.mt = 9999.0; nbox = viol = 0
    for fi in range(f0, f1):
        a = _R.frame(fi); means.append(float(a[::8, ::8].mean())); ff.stdin.write(a.tobytes())
        for r in _R.rec:
            if r["kind"] == "box":
                x0, y0, x1, y1 = r["box"]; nbox += 1; bad = x0 < 24 or x1 > W - 24 or y0 < 24 or y1 > CAPTOP; viol += int(bad)
                if bad: print(f"VIOL frame {fi} box {x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}", flush=True)
                continue
            if r.get("drawn") is None and r["kind"] == "callout": continue
            sd = 0.0
            if r["kind"] == "callout":
                x0, y0, x1, y1 = r["box"]; sx, sy = r["start"]; sd = min(abs(sx - x0), abs(sx - x1), abs(sy - y0), abs(sy - y1))
            ed = math.hypot(r["drawn"][0] - r["target"][0], r["drawn"][1] - r["target"][1]); td = math.hypot(r["tick"][0] - r["target"][0], r["tick"][1] - r["target"][1]) if "tick" in r else 0.0
            recs.append([sd, ed, td])
    ff.stdin.close()
    if ff.wait() != 0: raise RuntimeError("ffmpeg failed")
    rr = [float(np.max([x[i] for x in recs])) if recs else 0.0 for i in range(3)] + [nbox, viol]
    stmp = Path(outdir) / f"_part{idx:03d}.json.tmp"
    json.dump(dict(key=key, frames=n, means=means, mintext=float(_R.mt), rec=rr), open(stmp, "w")); os.replace(stmp, side); os.replace(tmp, path)
    return str(path), means, float(_R.mt), rr, False


def render_3d(topic, P, nframes, cache):
    fd = cache / "dio_frames"; fd.mkdir(exist_ok=True); P["frames_dir"] = str(fd)
    pj = cache / "dio_plan.json"; json.dump(dict(fps=FPS, total=P["total"], bounds=P["bounds"], scenes=P["scenes"], topic=P["topic"]), open(pj, "w"))
    dd = ROOT / "presenter" / "dio"; own = dd / f"scenes_{P['topic']}.js"
    code = b"".join(p.read_bytes() for p in sorted(dd.glob("*.js")) if not p.name.startswith("scenes_")) + own.read_bytes() + (ROOT / "presenter" / "diorama.html").read_bytes() + json.dumps([P["bounds"], P["scenes"]]).encode()
    key = hashlib.sha1(code).hexdigest()[:12]; kf = fd / "key.txt"
    if not (kf.exists() and kf.read_text() == key):
        for p in fd.glob("*"): p.unlink()
        kf.write_text(key)
    nw = 3; per = math.ceil(nframes / nw); procs = []
    for k in range(nw):
        a, b = k * per, min(nframes, (k + 1) * per)
        if a >= b: continue
        if all((fd / f"{i:05d}.jpg").exists() for i in range(a, b)) and (fd / f"meta_{a}.json").exists(): continue
        procs.append(subprocess.Popen(["node", "diorama_render.js", str(pj), str(fd), f"{a}-{b}"], cwd=ROOT / "presenter"))
    for p in procs:
        if p.wait() != 0: raise SystemExit("3D render failed")


def run(topic, args):
    from . import script as SC, voice as VO, encode
    import soundfile as sf
    opt = lambda k: args[args.index(k) + 1] if k in args else None
    topic = Path(topic); out = topic / "out"; cache = topic / "cache"; out.mkdir(exist_ok=True); cache.mkdir(exist_ok=True); name = topic.name
    T = {}; t00 = time.time()
    def stage(nm, t0): T[nm] = round(time.time() - t0, 1); print(f"[{nm}] {T[nm]}s", flush=True)
    S = SC.load(topic); beats = S["beats"]
    D0 = load_defs(name); VO.GAP = float(getattr(D0, "GAP", VO.GAP))      # topic may breathe a little between sentences (viewer needs time, owner rule)
    if "--fake" in args:                                                  # dev only: fixed 3.3 s per beat, silence (no TTS)
        BT = [dict(t0=0.12 + i * 3.3, speech=3.0, t1=0.12 + (i + 1) * 3.3) for i in range(len(beats))]; TOTAL = BT[-1]["t1"] + 1.6; voice = np.zeros(int(TOTAL * VO.SR), np.float32)
    else:
        t0 = time.time(); VO.generate(topic, beats, S); voice, BT, TOTAL = VO.narrate(topic, beats, cache); stage("voice", t0)
    tail = float(getattr(load_defs(name), "TAIL", 0) or 0)                  # extra hold on the last scene (voice untouched) when the narration alone is < 40 s
    if tail: BT[-1]["t1"] += tail; TOTAL += tail; voice = np.concatenate([voice, np.zeros(int(tail * VO.SR), np.float32)])
    P = build_plan(S, voice, BT, TOTAL); nframes = int(math.ceil(TOTAL * FPS))
    if opt("--frames"):                                   # quick stills: 3D + overlays for the given seconds
        fd = cache / "dio_stills"; fd.mkdir(exist_ok=True); P["frames_dir"] = str(fd); pj = cache / "dio_plan.json"
        json.dump(dict(fps=FPS, total=TOTAL, bounds=P["bounds"], scenes=P["scenes"], topic=P["topic"]), open(pj, "w")); secs = [float(x) for x in opt("--frames").split(",")]; fr = [int(round(x * FPS)) for x in secs]
        for p in fd.glob("*"): p.unlink()
        subprocess.run(["node", "diorama_render.js", str(pj), str(fd), ",".join(map(str, fr))], cwd=ROOT / "presenter", check=True)
        pkl = cache / "plan_dio.pkl"; pickle.dump(P, open(pkl, "wb")); R = Composer(str(pkl)); (out / "frames").mkdir(exist_ok=True)
        for sec, f in zip(secs, fr):
            p = out / "frames" / f"d_{sec:06.2f}.png"; Image.fromarray(R.frame(f)).save(p); print(p)
        return
    t0 = time.time(); render_3d(topic, P, nframes, cache); stage("render3d", t0)
    pkl = cache / "plan_dio.pkl"; pickle.dump(P, open(pkl, "wb"))
    t0 = time.time(); audio = SIL.make_audio(voice, TOTAL, P); wav = cache / "audio.wav"; sf.write(wav, audio, VO.SR); stage("audio", t0)
    t0 = time.time(); step = 75
    key = hashlib.sha1(open(pkl, "rb").read() + Path(__file__).read_bytes() + (cache / "dio_frames" / "key.txt").read_bytes() + f"{nframes}".encode()).hexdigest()[:16]
    for q in cache.glob("_part*.tmp.mp4"): q.unlink(missing_ok=True)
    jobs = [(i, f0, min(nframes, f0 + step), str(cache), key) for i, f0 in enumerate(range(0, nframes, step))]
    parts, means, mints, recs, reused = [], [], [], [], 0
    with mp.get_context("spawn").Pool(4, initializer=init_worker, initargs=(str(pkl),)) as pool:
        for k, (path, mn, mt, rr, sk) in enumerate(pool.imap(render_chunk, jobs, chunksize=1)):
            parts.append(path); means += mn; mints.append(mt); recs.append(rr); reused += bool(sk); print(f"  chunk {k + 1}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
    stage("compose", t0)
    t0 = time.time(); final = out / f"{name}.mp4"; tmpf = out / f"{name}.tmp.mp4"; encode.mux(parts, wav, tmpf, cache); os.replace(tmpf, final); stage("mux", t0)
    m = np.array(means); jumps = np.abs(np.diff(m)); jmax = float(jumps.max()); jt = float((int(jumps.argmax()) + 1) / FPS)
    dur_s = nframes / FPS; warns = list(S["warnings"]); sd, ed, td = [max(r[i] for r in recs) for i in range(3)]; nbox = int(sum(r[3] for r in recs)); viol = int(sum(r[4] for r in recs))
    for nm, d_ in P["short_scenes"]: warns.append(f"SHORT SCENE {nm} {d_}s < {MIN_SCENE}s")
    if not (40 <= dur_s <= 50): warns.append(f"DURATION {dur_s:.1f}s outside 40-50s")
    if jmax > 15: warns.append(f"FLICKER max frame-to-frame brightness jump {jmax:.1f} at {jt:.2f}s > 15")
    if viol: warns.append(f"OVERLAY bounds/caption-overlap violations in {viol} box-frames")
    ok = bool(sd <= 2 and ed <= 2 and td <= 2)
    if not ok: warns.append(f"CALLOUT leader check failed: start {sd:.2f} end {ed:.2f} tick {td:.2f} px")
    small = out / f"{name}_9mb.mp4"; size9 = None
    if "--no-9mb" not in args:
        t0 = time.time(); size9, vb = encode.encode_9mb(final, small, TOTAL, cache); stage("encode_9mb", t0)
        if size9 >= 10_000_000: warns.append("9mb file still >= 10 MB")
    t0 = time.time(); encode.contact_sheet(final, out / f"{name}_sheet.png", TOTAL); stage("sheet", t0)
    T["total"] = round(time.time() - t00, 1)
    rep = dict(topic=name, title=S["title"], style="diorama", duration_s=round(dur_s, 2), narration_s=round(TOTAL, 2), beats=len(beats), min_caption_px=round(min(mints), 1),
               max_brightness_jump=round(jmax, 2), max_jump_at_s=round(jt, 2), mean_brightness_max=round(float(m.max()), 1),
               callout_check=dict(ok=ok, leader_start_on_box_edge_max_px=round(sd, 3), leader_end_vs_projected_target_max_px=round(ed, 3), dim_tick_vs_target_max_px=round(td, 3), limit_px=2.0),
               overlay_bounds_check=dict(ok=viol == 0, box_frames_checked=nbox, violations=viol, rule=f"boxes inside 24px frame margin and above y={CAPTOP} (caption pill zone)"),
               mp4_bytes=final.stat().st_size, mp4_9mb_bytes=size9, warnings=warns, stage_seconds=T)
    json.dump(rep, open(out / "report.json", "w"), indent=2); print(json.dumps(rep, indent=2))
