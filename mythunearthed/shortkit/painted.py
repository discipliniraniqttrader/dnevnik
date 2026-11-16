"""style "painted": locked SDXL-Turbo illustrated world + 2.5D depth camera + drawn overlays (numbers/leaders are ours, never the image model's).
Per-topic config: <topic>/painted.json (style prefix, negative, seed family, per-beat prompt/camera/overlays). Images + depth cached in <topic>/cache/painted/."""
import hashlib, json, math, multiprocessing as mp, os, pickle, re, subprocess, sys, time
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw
from .common import W, H, FPS, ROOT, F, MONT_BLACK, ease
from . import silhouette as SIL

PYLIB = ROOT / "voice" / "pylib_new"          # diffusers>=0.40 (the venv's 0.29 is incompatible with transformers 5)
VENV_PY = ROOT / "voice" / "venv" / "bin" / "python"


def load_cfg(topic):
    from . import paintplan
    paintplan.ensure(topic)                      # auto-generate from the beats' scenes when the topic has no painted.json yet
    return json.load(open(Path(topic) / "painted.json"))


def beat_job(cfg, i, pdir):
    b = cfg["beats"][i]; w, h = (cfg.get("wide_size", [1344, 768]) if b.get("wide") else cfg.get("size", [768, 1344]))
    if b.get("use"):                                   # pin a specific cached image (chosen by eye); prompt is kept for the record
        base = str(pdir / b["use"]); return dict(key=b["use"], layout=None, wide=None, prompt=b["prompt"], neg="", seed=0, w=w, h=h, steps=0, img=base + ".png", depth=base + "_depth.png")
    prompt = b["prompt"] + ", " + cfg["style"]; neg = cfg["negative"] + (", " + b["neg"] if b.get("neg") else "")
    seed = int(b.get("seed", cfg.get("seed", 4100) + 7 * i)); steps = int(cfg.get("steps", 3))
    lay = b.get("layout"); wide = b.get("wide"); key = hashlib.sha1(f"{prompt}|{neg}|{seed}|{w}x{h}|{steps}|{json.dumps(lay, sort_keys=True)}|{json.dumps(wide)}".encode()).hexdigest()[:12]
    return dict(key=f"b{i + 1:02d}_{key}", layout=lay, wide=wide, prompt=prompt, neg=neg, seed=seed, w=w, h=h, steps=steps, img=str(pdir / f"b{i + 1:02d}_{key}.png"), depth=str(pdir / f"b{i + 1:02d}_{key}_depth.png"))


def ensure_images(topic, cfg, only=None):
    pdir = Path(topic) / "cache" / "painted"; pdir.mkdir(parents=True, exist_ok=True)
    jobs = [beat_job(cfg, i, pdir) for i in range(len(cfg["beats"]))]
    todo = [j for k, j in enumerate(jobs) if (only is None or (k + 1) in only) and not (Path(j["img"]).exists() and Path(j["depth"]).exists())]
    if todo:
        jf = pdir / "_jobs.json"; json.dump(dict(model=cfg.get("model", "stabilityai/sdxl-turbo"), jobs=todo), open(jf, "w"))
        env = dict(os.environ, HF_HUB_DISABLE_XET="1", PYTHONPATH=str(PYLIB))
        t = time.time(); r = subprocess.run([str(VENV_PY), str(Path(__file__).parent / "paintgen.py"), str(jf)], env=env)
        if r.returncode: raise RuntimeError("paintgen failed")
        print(f"[images] {len(todo)} generated in {time.time() - t:.0f}s ({(time.time() - t) / len(todo):.1f}s each incl. load+depth)", flush=True)
    return jobs


# ====================================================================== constants
XF = 0.25                  # crossfade at beat boundaries (s): no ghosting longer than this
OV = 1.5                   # source oversampling vs 1080x1920 canvas
DM = 0.45                  # depth pivot (static plane)
CX, CY = W / 2.0, H / 2.0
KW_YELLOW = SIL.KW_YELLOW
GOLD = (255, 190, 60); CREAM = (250, 238, 214); INKC = (14, 10, 8)      # RGB
CAMS = ["dolly_in", "truck_r", "dolly_out", "truck_l"]


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def sstep(x): x = clamp(x); return x * x * (3 - 2 * x)


def cam_params(cam, u):
    """-> z, pan(px), lateral parallax px (at |depth-DM|=1), radial parallax. u = beat progress (slightly outside 0..1 allowed)."""
    c = cam if isinstance(cam, dict) else dict(type=cam)
    ty = c.get("type", "dolly_in"); k = float(c.get("amp", 1.0))
    if ty == "dolly_in": return 1.04 + 0.12 * u, (0.0, 0.0), (0.0, 0.0), 0.10 * k * (0.2 + u)
    if ty == "dolly_out": return 1.16 - 0.12 * u, (0.0, 0.0), (0.0, 0.0), 0.10 * k * (1.0 - u * 0.8)
    s = 1.0 if ty == "truck_r" else -1.0
    return 1.10 + 0.02 * u, (-s * 50 * (u - 0.5) * k, 0.0), (s * 70 * (u - 0.5) * k, -4 * (u - 0.5) * k), 0.0
    

def bilin(a, x, y):
    h, w = a.shape[:2]; x = min(max(x, 0.0), w - 1.001); y = min(max(y, 0.0), h - 1.001); x0, y0 = int(x), int(y); fx, fy = x - x0, y - y0
    return ((a[y0, x0] * (1 - fx) + a[y0, x0 + 1] * fx) * (1 - fy) + (a[y0 + 1, x0] * (1 - fx) + a[y0 + 1, x0 + 1] * fx) * fy)


class Assets:
    """one beat: oversampled graded image, canvas-res smoothed depth, half-res depth, subject bbox."""
    def __init__(s, job, gain, tone=0.0, wide=None):
        im = Image.open(job["img"]).convert("RGB"); w, h = im.size
        d0 = np.asarray(Image.open(job["depth"])).astype(np.float32) / 65535.0
        if wide:                                       # landscape source: a band of the 1920-high world, sky/sea extended above/below, camera pans along it
            wc = wide if isinstance(wide, dict) else {}
            Hi = int(round(H * float(wc.get("fit", 0.52)))); Wi = int(round(w * Hi / h)); s.WW = max(Wi, W)
            y0 = int(round(float(wc.get("center", 0.56)) * H - Hi / 2)); y0 = max(0, min(H - Hi, y0)); oy = int(y0 * OV)
            imr = np.asarray(im.resize((int(Wi * OV), int(Hi * OV)), Image.LANCZOS)).astype(np.float32); ch, cw = int(H * OV), imr.shape[1]
            cv = np.zeros((ch, cw, 3), np.float32); ov_ = int(50 * OV); strip = int(70 * OV)
            if oy > 0:
                top = cv2.resize(imr[:strip][::-1].copy(), (cw, oy + ov_), interpolation=cv2.INTER_AREA); top = cv2.GaussianBlur(top, (0, 0), 28 * OV)
                top *= np.linspace(0.5, 1.0, oy + ov_)[:, None, None]; cv[:oy + ov_] = top
            bot_h = ch - oy - imr.shape[0]
            if bot_h > 0:
                bot = cv2.resize(imr[-strip:][::-1].copy(), (cw, bot_h + ov_), interpolation=cv2.INTER_AREA); bot = cv2.GaussianBlur(bot, (0, 0), 28 * OV)
                bot *= np.linspace(1.0, 0.45, bot_h + ov_)[:, None, None]; cv[ch - bot_h - ov_:] = bot
            al = np.ones(imr.shape[0], np.float32); al[:ov_] = np.linspace(0, 1, ov_) if oy > 0 else 1; al[-ov_:] = np.minimum(al[-ov_:], np.linspace(1, 0, ov_)) if bot_h > 0 else al[-ov_:]
            reg = cv[oy:oy + imr.shape[0]]; cv[oy:oy + imr.shape[0]] = reg * (1 - al[:, None, None]) + imr * al[:, None, None]
            a = cv
            dw = cv2.resize(d0, (Wi, Hi), interpolation=cv2.INTER_CUBIC); d = np.pad(dw, ((y0, H - y0 - Hi), (0, 0)), mode="edge")
        else:
            cw_ = int(round(h * W / H)); x0 = (w - cw_) // 2; s.WW = W
            im = im.crop((x0, 0, x0 + cw_, h)).resize((int(W * OV), int(H * OV)), Image.LANCZOS); a = np.asarray(im).astype(np.float32)
            d = cv2.resize(d0[:, x0:x0 + cw_], (W, H), interpolation=cv2.INTER_CUBIC)
        bl = cv2.GaussianBlur(a, (0, 0), 2.2); a = np.clip(a + 0.55 * (a - bl), 0, 255)                  # unsharp: restores bite after upscale
        a = a * gain
        if tone > 0:                                   # palette lock for outliers: blend toward a dusk gradient map of the luminance
            l = cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)[..., None] / 255.0
            gm = np.array([8, 5, 4], np.float32) * (1 - l) ** 1 + np.array([255, 160, 70], np.float32) * l ** 0.9
            a = a * (1 - tone) + np.clip(gm * 1.05, 0, 255) * tone
        # locked grade: lift blacks slightly warm, gentle S-curve, shared by every beat
        x = a / 255.0; x = x * x * (3 - 2 * x) * 0.35 + x * 0.65; x = x * np.array([1.02, 0.99, 0.95], np.float32) + np.array([0.012, 0.008, 0.006], np.float32)
        s.img = (np.clip(x, 0, 1) * 255).astype(np.uint8)                                          # RGB
        d = cv2.GaussianBlur(d, (0, 0), 5); s.depth = np.clip(d, 0, 1).astype(np.float32)
        s.dh = cv2.resize(s.depth, (s.WW // 2, H // 2), interpolation=cv2.INTER_AREA)
        g = cv2.cvtColor(cv2.resize(s.img, (s.WW // 2, H // 2), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY); s.luma = g
        s.bb = {}

    def bbox(s, roi, thr, minc=3):
        x0, y0, x1, y1 = [int(v / 2) for v in roi]; m = (s.luma[y0:y1, x0:x1] < thr)
        cols = np.where(m.sum(0) >= minc)[0]; rows = np.where(m.sum(1) >= max(minc, 3))[0]
        if len(cols) == 0 or len(rows) == 0: return None
        return dict(l=2.0 * (x0 + cols[0]), r=2.0 * (x0 + cols[-1] + 1), t=2.0 * (y0 + rows[0]), b=2.0 * (y0 + rows[-1] + 1))


# ====================================================================== plan
def build_plan(S, voice, BT, TOTAL, cfg, jobs, topic):
    from PIL import Image as _I
    P = SIL.build_plan(S, voice, BT, TOTAL)
    means = []
    for j in jobs:
        a = np.asarray(_I.open(j["img"]).convert("L")).astype(np.float32); means.append(float(a.mean()))
    tgt = float(np.median(means)); gains = [float(clamp(tgt / m, 0.82, 1.3)) for m in means]
    P.update(cfg=cfg, jobs=jobs, gains=gains, img_means=means)
    return P


# ====================================================================== renderer
class Renderer:
    def __init__(s, plan_path):
        s.P = pickle.load(open(plan_path, "rb")); s.cfg = s.P["cfg"]; s.cache = {}; s.mt = 9999.0; s.rec = []
        rng = np.random.default_rng(7)
        s.rain = rng.random((170, 5)); s.part = rng.random((46, 5)); s.gr = np.random.default_rng(11)
        yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32); s.gx = (xx + 0.5) * 2; s.gy = (yy + 0.5) * 2
        r = np.sqrt(((xx - W / 4) / (W / 4)) ** 2 + ((yy - H / 4) / (H / 4)) ** 2); s.vig = cv2.resize(np.clip(1.0 - 0.22 * np.clip(r - 0.55, 0, 1) ** 1.6, 0, 1), (W, H))[..., None]

    def assets(s, i):
        if i not in s.cache:
            if len(s.cache) >= 3: s.cache.pop(next(iter(s.cache)))
            s.cache[i] = Assets(s.P["jobs"][i], s.P["gains"][i], s.cfg["beats"][i].get("tone", 0.0), s.cfg["beats"][i].get("wide"))
        return s.cache[i]

    # ---- camera: forward (for anchored overlays) and backward (for pixels)
    def cam_state(s, i, t):
        b = s.P["bounds"]; dur = b[i + 1] - b[i]; u = max(-0.1, min(1.1, (t - b[i]) / dur)); bc = s.cfg["beats"][i]; A = s.assets(i)
        if A.WW > W + 1:                               # lateral pan along a wide world (hull, field, ridge); depth parallax follows the motion
            c = bc.get("cam", {}); c = c if isinstance(c, dict) else {}
            f0 = float(c.get("f0", 0.0)); f1 = float(c.get("f1", 1.0)); sg = 1.0 if f1 >= f0 else -1.0
            return 1.0 + 0.05 * u, (0.0, 0.0), (sg * 60 * (u - 0.5), 0.0), 0.02, W / 2 + (f0 + (f1 - f0) * u) * (A.WW - W)
        z, pan, px, pr = cam_params(bc.get("cam", CAMS[i % len(CAMS)]), u)
        return z, pan, px, pr, W / 2

    def forward(s, A, st, pt):
        z, pan, px, pr, vcx = st; x, y = pt; dd = float(bilin(A.depth, x, y)) - DM
        qx = x + dd * (px[0] + pr * (x - vcx)); qy = y + dd * (px[1] + pr * (y - CY))
        return (CX + z * (qx - vcx) + pan[0], CY + z * (qy - CY) + pan[1])

    def fwd(s, i, A, st, pt):
        """screen position where source pixel `pt` really lands: analytic start, then refined against the actual backward map (exact inverse of what is rendered)."""
        p = list(s.forward(A, st, pt)); mp = s.cur_maps.get(i)
        if mp is None: return tuple(p)
        sx, sy = mp; z = st[0]
        for _ in range(12):
            bx = float(bilin(sx, p[0] / 2 - 0.5, p[1] / 2 - 0.5)); by = float(bilin(sy, p[0] / 2 - 0.5, p[1] / 2 - 0.5))
            ex, ey = pt[0] - bx, pt[1] - by
            if math.hypot(ex, ey) < 0.05: break
            p[0] += ex * z; p[1] += ey * z
        return tuple(p)

    cur_maps = {}

    def backward_maps(s, A, st):
        z, pan, px, pr, vcx = st
        s0x = vcx + (s.gx - pan[0] - CX) / z; s0y = CY + (s.gy - pan[1] - CY) / z; sx, sy = s0x.copy(), s0y.copy()
        for _ in range(4):
            dd = cv2.remap(A.dh, sx / 2 - 0.5, sy / 2 - 0.5, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE) - DM
            sx = (s0x - dd * px[0] + dd * pr * vcx) / (1 + dd * pr); sy = (s0y - dd * px[1] + dd * pr * CY) / (1 + dd * pr)
        return sx, sy

    def beat_frame(s, i, t):
        A = s.assets(i); st = s.cam_state(i, t); sx, sy = s.backward_maps(A, st)
        mx = cv2.resize(sx, (W, H), interpolation=cv2.INTER_LINEAR) * OV - 0.5; my = cv2.resize(sy, (W, H), interpolation=cv2.INTER_LINEAR) * OV - 0.5
        s.cur_maps[i] = (sx, sy)
        return cv2.remap(A.img, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT).astype(np.float32), A, st, (sx, sy)

    def weights(s, t):
        b = s.P["bounds"]; out = []
        for i in range(len(b) - 1):
            lo = b[i] - (XF / 2 if i else 0); hi = b[i + 1] + (XF / 2 if i < len(b) - 2 else 0)
            if lo - 1e-6 <= t <= hi + 1e-6:
                w = 1.0
                if i and t < b[i] + XF / 2: w = sstep((t - (b[i] - XF / 2)) / XF)
                if i < len(b) - 2 and t > b[i + 1] - XF / 2: w = min(w, 1 - sstep((t - (b[i + 1] - XF / 2)) / XF))
                if w > 0.003: out.append((i, w))
        return out or [(0, 1.0)]

    # ---- atmosphere: light rain streaks, drifting embers, flicker
    def atmosphere(s, img, t):
        m = np.zeros((H, W), np.uint8)
        for x0, y0, sp, ln_, a in s.rain:
            y = (y0 * (H + 300) + t * (1700 + 800 * sp)) % (H + 300) - 150; x = x0 * (W + 500) - 0.22 * (y + 150) - 60; l = 30 + 46 * ln_
            cv2.line(m, (int(x * 8), int(y * 8)), (int((x - 0.22 * l) * 8), int((y + l) * 8)), int(60 + 100 * a), 1, cv2.LINE_AA, 3)
        img += (m.astype(np.float32) * (0.20 / 255))[..., None] * np.array([255, 232, 205], np.float32)
        e = np.zeros((H, W), np.uint8)
        for x0, y0, sp, ph, sz in s.part:
            y = H - ((y0 * H + t * (26 + 40 * sp)) % (H + 80)) + 40; x = x0 * W + 22 * math.sin(t * (0.5 + sp) + ph * 6.28) + 10 * t * (sp - 0.5)
            cv2.circle(e, (int(x * 4), int(y * 4)), int((1.4 + 2.2 * sz) * 4), int(150 + 90 * math.sin(t * 2 + ph * 9) ** 2), -1, cv2.LINE_AA, 2)
        e = cv2.GaussianBlur(e, (0, 0), 1.2)
        img += (e.astype(np.float32) * (0.34 / 255))[..., None] * np.array([255, 170, 80], np.float32)
        # light flicker: slow irregular +-2.5% on highlights only (rim lights / lanterns), no frame-to-frame jump
        fl = 0.5 * math.sin(t * 5.3) + 0.3 * math.sin(t * 13.1 + 1) + 0.2 * math.sin(t * 2.1 + 2)
        lum = img.mean(2, keepdims=True) / 255.0; img *= 1 + 0.025 * fl * np.clip((lum - 0.35) * 2.2, 0, 1)
        return img

    # ---- drawn overlays (numbers, measurement graphics, callouts): all ours
    def overlays(s, img, t, wts):
        P = s.P; out = img
        lay = np.zeros((H, W, 3), np.uint8); msk = np.zeros((H, W), np.uint8); texts = []
        for (i, w) in wts:
            spec = s.cfg["beats"][i].get("ov", [])
            if not spec: continue
            lt = t - P["bounds"][i]; A = s.assets(i); st = s.cam_state(i, t)
            if w < 0.98 and lt < 0.5: pass
            fa = w
            for k, o in enumerate(spec):
                s.draw_ov(lay, msk, texts, o, lt, A, st, fa, i, k)
        if msk.any():
            sh = cv2.GaussianBlur(msk, (0, 0), 7).astype(np.float32) / 255.0
            out = out * (1 - 0.45 * np.clip(sh * 1.5, 0, 1))[..., None]
            m = msk.astype(np.float32)[..., None] / 255.0
            out = out * (1 - m) + lay.astype(np.float32)
        if texts:
            im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im, "RGBA")
            for (xy, txt, font, col, al, stroke) in texts:
                d.text(xy, txt, font=font, fill=col + (int(255 * al),), anchor="mm", stroke_width=stroke, stroke_fill=(10, 8, 6, int(255 * al)))
                s.mt = min(s.mt, font.size)
            out = np.asarray(im).astype(np.float32)
        return out

    def pt(s, v, A):
        def one(c, ax):
            if isinstance(c, str):
                k = c.split(".")[1]; bb = A.bb[ax[1]]; return {"cx": (bb["l"] + bb["r"]) / 2, "cy": (bb["t"] + bb["b"]) / 2}.get(k, bb.get(k))
            return float(c)
        return one(v[0], ("x", s.bbname(v[0]))), one(v[1], ("y", s.bbname(v[1])))

    @staticmethod
    def bbname(c): return c.split(".")[0] if isinstance(c, str) else None

    def ensure_bbs(s, A, i):
        for name, bs in s.cfg["beats"][i].get("bbox", {}).items():
            if name not in A.bb: A.bb[name] = A.bbox(bs["roi"], bs.get("thr", 70), bs.get("minc", 3))

    def box_text(s, lay, msk, texts, cx, cy, txt, size, al, fill=(18, 14, 12), edge=GOLD, col=CREAM, pad=20, a=1.0):
        f = F(MONT_BLACK, size); tw = f.getlength(txt); bw, bh = tw + 2 * pad, size * 1.0 + pad
        x0, y0, x1, y1 = int(cx - bw / 2), int(cy - bh / 2), int(cx + bw / 2), int(cy + bh / 2)
        cv2.rectangle(msk, (x0, y0), (x1, y1), int(255 * al), -1)
        cv2.rectangle(lay, (x0, y0), (x1, y1), tuple(int(c * al) for c in fill), -1)
        cv2.rectangle(lay, (x0, y0), (x1, y1), tuple(int(c * al) for c in edge), 3, cv2.LINE_AA)
        texts.append(((cx, cy + 2), txt, f, col, al, 0))
        return (x0, y0, x1, y1)

    def line_aa(s, lay, msk, p, q, col, th, al, dot_end=None):
        P_ = lambda v: (int(round(v[0] * 16)), int(round(v[1] * 16)))
        c = tuple(int(c * al) for c in col)
        cv2.line(lay, P_(p), P_(q), c, th, cv2.LINE_AA, 4); cv2.line(msk, P_(p), P_(q), int(255 * al), th, cv2.LINE_AA, 4)

    def dot(s, lay, msk, p, r, col, al):
        P_ = (int(round(p[0] * 16)), int(round(p[1] * 16)))
        cv2.circle(lay, P_, int(r * 16), tuple(int(c * al) for c in col), -1, cv2.LINE_AA, 4); cv2.circle(msk, P_, int(r * 16), int(255 * al), -1, cv2.LINE_AA, 4)
        cv2.circle(lay, P_, int(r * 16), tuple(int(c * al) for c in INKC), 2, cv2.LINE_AA, 4)

    def draw_ov(s, lay, msk, texts, o, lt, A, st, fa, i, k):
        s.ensure_bbs(A, i)
        t0 = o.get("t0", 0.6); ty = o["type"]; dd = o.get("d", 0.7)
        # leave 0.35 s before the beat ends
        dur = s.P["bounds"][i + 1] - s.P["bounds"][i]; out_al = 1 - sstep((lt - (dur - 0.05)) / 0.3) if lt > dur - 0.35 else 1.0
        al = fa * clamp((lt - t0) / 0.25) * out_al
        if al <= 0.003 and ty != "counter": return
        prog = ease((lt - t0) / dd)
        if ty == "dim":
            a = s.pt(o["a"], A); b = s.pt(o["b"], A); off = o.get("off", [0, 0])
            a = s.fwd(i, A, st, a); b = s.fwd(i, A, st, b); lab = o["label"]
            a2 = (a[0] + off[0], a[1] + off[1]); b2 = (b[0] + off[0], b[1] + off[1])
            ux, uy = b2[0] - a2[0], b2[1] - a2[1]; L = math.hypot(ux, uy) or 1; nx, ny = -uy / L, ux / L
            mid = ((a2[0] + b2[0]) / 2, (a2[1] + b2[1]) / 2)
            e = (a2[0] + ux * prog, a2[1] + uy * prog)
            if off != [0, 0]:
                s.line_aa(lay, msk, a, a2, CREAM, 3, al); s.line_aa(lay, msk, b, b2, CREAM, 3, al)
            s.line_aa(lay, msk, a2, e, GOLD, 5, al)
            for (p_, show) in ((a2, True), (b2, prog > 0.98)):
                if show: s.line_aa(lay, msk, (p_[0] - nx * 22, p_[1] - ny * 22), (p_[0] + nx * 22, p_[1] + ny * 22), GOLD, 5, al)
            s.dot(lay, msk, a, 8, GOLD, al); s.dot(lay, msk, b, 8, GOLD, al)
            if o.get("lab_follow"):
                tt = clamp((CX - a2[0]) / (ux if abs(ux) > 1e-6 else 1e-6), 0.12, 0.88); mid = (a2[0] + ux * tt, a2[1] + uy * tt)
            lx, ly = mid[0] + nx * o.get("lab_off", 62) * (1 if ny > 0 or o.get("lab_flip") else -1), mid[1] + ny * o.get("lab_off", 62) * (1 if ny > 0 or o.get("lab_flip") else -1)
            s.box_text(lay, msk, texts, lx, ly, lab, 48, al * clamp((lt - t0 - dd * 0.6) / 0.25))
            s.rec.append(dict(kind="dim", beat=i + 1, target=a, drawn=a, tick=a)); s.rec.append(dict(kind="dim", beat=i + 1, target=b, drawn=b, tick=b))
            s.anchors.append((i, s.pt(o["a"], A))); s.anchors.append((i, s.pt(o["b"], A)))
        elif ty == "callout":
            tg0 = s.pt(o["target"], A); tg = s.fwd(i, A, st, tg0); bo = o.get("boxoff", [0, -220])
            f = F(MONT_BLACK, 46); tw = f.getlength(o["label"]); bw, bh = tw + 40, 46 + 20
            bc = (tg[0] + bo[0], tg[1] + bo[1]); x0, y0, x1, y1 = bc[0] - bw / 2, bc[1] - bh / 2, bc[0] + bw / 2, bc[1] + bh / 2
            dx, dy = tg[0] - bc[0], tg[1] - bc[1]
            kx = (bw / 2) / abs(dx) if abs(dx) > 1e-6 else 1e9; ky = (bh / 2) / abs(dy) if abs(dy) > 1e-6 else 1e9; kk = min(kx, ky)
            st_p = (bc[0] + dx * kk, bc[1] + dy * kk)
            e = (st_p[0] + (tg[0] - st_p[0]) * prog, st_p[1] + (tg[1] - st_p[1]) * prog)
            s.line_aa(lay, msk, st_p, e, GOLD, 5, al)
            s.box_text(lay, msk, texts, bc[0], bc[1], o["label"], 46, al)
            if prog > 0.97: s.dot(lay, msk, tg, 10, GOLD, al)
            s.rec.append(dict(kind="callout", beat=i + 1, target=tg, drawn=tg, start=st_p, box=(x0, y0, x1, y1)))
            s.anchors.append((i, tg0))
        elif ty == "counter":
            if lt < t0: return
            v = o["from"] + (o["to"] - o["from"]) * ease((lt - t0) / dd); txt = f"{int(round(v))}{o.get('unit', '')}"
            sz = o.get("size", 190); f = F(MONT_BLACK, sz); cx, cy = o.get("pos", [540, 1000])
            a_ = fa * clamp((lt - t0) / 0.2) * out_al
            texts.append(((cx, cy), txt, f, GOLD if lt - t0 > dd else CREAM, a_, 9))
            if o.get("sub"): texts.append(((cx, cy + sz * 0.72), o["sub"], F(MONT_BLACK, 52), CREAM, a_, 4))
        elif ty == "badge":
            sz = o.get("size", 130); cx, cy = o.get("pos", [540, 1000]); pop = 1 + 0.12 * math.sin(clamp((lt - t0) / 0.35) * math.pi)
            f = F(MONT_BLACK, int(sz * pop)); txt = o["text"]
            s.box_text(lay, msk, texts, cx, cy, txt, int(sz * pop), al, pad=int(sz * 0.32))
            if o.get("sub"): texts.append(((cx, cy + sz * 0.95), o["sub"], F(MONT_BLACK, 50), CREAM, al, 5))
        elif ty == "bars":
            x0 = o.get("x", 120); sc = o.get("scale", 3.0); y = o.get("y", 1250); gap = o.get("gap", 130)
            for n_, it in enumerate(o["items"]):
                p_ = ease((lt - t0 - 0.35 * n_) / 0.8); a_ = fa * clamp((lt - t0 - 0.35 * n_) / 0.25) * out_al
                if a_ <= 0.003: continue
                L = it["v"] * sc * p_; yy = y + n_ * gap
                cv2.rectangle(msk, (int(x0), int(yy - 18)), (int(x0 + L), int(yy + 18)), int(255 * a_), -1)
                cv2.rectangle(lay, (int(x0), int(yy - 18)), (int(x0 + L), int(yy + 18)), tuple(int(c * a_) for c in (it.get("col", GOLD))), -1)
                texts.append(((x0 + it["v"] * sc / 2, yy - 56), it["label"], F(MONT_BLACK, 48), CREAM, a_, 4))
        elif ty == "tags":
            n = len(o["labels"]); y = o.get("y", 1120)
            for n_, lab in enumerate(o["labels"]):
                a_ = fa * clamp((lt - t0 - 0.35 * n_) / 0.3) * out_al
                if a_ <= 0.003: continue
                s.box_text(lay, msk, texts, 540, y + n_ * 150, lab, 76, a_, edge=GOLD if n_ == 0 else (230, 90, 60), pad=30)

    anchors = []

    def captions(s, img, t):
        c = None
        for cc in s.P["caps"]:
            if cc["t0"] - 1e-3 <= t < cc["t1"]: c = cc; break
        if c is None: return img
        f0 = (t - c["t0"]) * FPS; k = 0.94 + 0.06 * ease(f0 / 4); size = 64; words = c["words"]
        def width(sz): return sum(F(MONT_BLACK, sz).getlength(w) for w in words) + sz * 0.3 * (len(words) - 1)
        while width(size) > 820 and size > 50: size -= 4
        s.mt = min(s.mt, size); sz = int(size * k); f = F(MONT_BLACK, sz)
        tw = sum(f.getlength(w) for w in words) + sz * 0.3 * (len(words) - 1); x = 540 - tw / 2; cy = 1470
        im = Image.fromarray(img); d = ImageDraw.Draw(im, "RGBA")
        d.rounded_rectangle([540 - tw / 2 - 34, cy - sz * 0.78, 540 + tw / 2 + 34, cy + sz * 0.78], radius=int(sz * 0.5), fill=(8, 6, 6, 150))
        for w, isk in zip(words, c["kw"]):
            col = KW_YELLOW if isk else (255, 255, 255)
            d.text((x, cy + 2), w, font=f, fill=col, anchor="lm", stroke_width=2, stroke_fill=(10, 8, 8))
            x += f.getlength(w) + sz * 0.3
        return np.asarray(im)

    def frame_array(s, fi):
        t = fi / FPS; s.anchors = []; s.rec = []
        wts = s.weights(t); acc = None; first = None
        for (i, w) in wts:
            f, A, st, maps = s.beat_frame(i, t); s.ensure_bbs(A, i)
            acc = f * w if acc is None else acc + f * w
            if first is None or w >= first[0]: first = (w, i, A, st, maps)
        tw_ = sum(w for _, w in wts); acc = acc / tw_
        acc = s.atmosphere(acc, t) * s.vig
        g = s.gr.standard_normal((H // 2, W // 2)).astype(np.float32) * 2.6
        acc += cv2.resize(g, (W, H), interpolation=cv2.INTER_NEAREST)[..., None]
        acc = s.overlays(acc, t, wts)
        s.check_anchors(first)
        return np.clip(acc, 0, 255).astype(np.uint8)

    def check_anchors(s, first):
        """warp consistency: where the drawn target sits on screen vs where the image pixel really lands (backward map at that screen point)."""
        if not s.anchors: return
        w, bi, A, st, (sx, sy) = first
        for (i, pt_) in s.anchors:
            if i != bi: continue
            p = s.fwd(i, A, st, pt_); bx = bilin(sx, p[0] / 2 - 0.5, p[1] / 2 - 0.5); by = bilin(sy, p[0] / 2 - 0.5, p[1] / 2 - 0.5)
            s.warp_err = max(s.warp_err, math.hypot(bx - pt_[0], by - pt_[1]) * st[0])

    warp_err = 0.0

    def frame(s, fi):
        a = s.frame_array(fi); a = s.captions(a, fi / FPS)
        return Image.fromarray(a)


# ====================================================================== chunked render + driver
_R = None


def init_worker(plan_path):
    global _R
    cv2.setNumThreads(1); _R = Renderer(plan_path)


def render_chunk(job):
    idx, f0, f1, outdir, key = job
    path = Path(outdir) / f"_part{idx:03d}.mp4"; side = Path(outdir) / f"_part{idx:03d}.json"; n = f1 - f0
    m = SIL.chunk_ok(path, side, n, key)
    if m is not None: return str(path), m["means"], m["mintext"], True, m.get("warp", 0.0), m.get("rec", [])
    tmp = Path(outdir) / f"_part{idx:03d}.tmp.mp4"
    for q in (tmp, path, side): q.unlink(missing_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)], stdin=subprocess.PIPE)
    means = []; _R.mt = 9999.0; _R.warp_err = 0.0; devs = {}
    for fi in range(f0, f1):
        a = np.asarray(_R.frame(fi)); means.append(float(a[::8, ::8].mean())); ff.stdin.write(a.tobytes())
        for j, r in enumerate(_R.rec):                 # worst-case deviation per drawn callout/dim target over the whole chunk
            d = _leader_dev(r); k = (r["beat"], r["kind"], j); o = devs.get(k)
            devs[k] = d if o is None else (d[0], d[1], max(o[2], d[2]), max(o[3], d[3]), max(o[4], d[4]))
    ff.stdin.close()
    if ff.wait() != 0: raise RuntimeError(f"ffmpeg failed on chunk {idx}")
    if SIL._probe_frames(tmp) != n: raise RuntimeError(f"chunk {idx}: frame count mismatch")
    rec_out = [dict(kind=d[0], beat=d[1], start_dev=d[2], end_dev=d[3], tick_dev=d[4]) for d in devs.values()]
    stmp = Path(outdir) / f"_part{idx:03d}.json.tmp"
    json.dump(dict(key=key, frames=n, means=means, mintext=float(_R.mt), warp=float(_R.warp_err), rec=rec_out), open(stmp, "w")); os.replace(stmp, side); os.replace(tmp, path)
    return str(path), means, float(_R.mt), False, float(_R.warp_err), rec_out


def _leader_dev(r):
    """geometric deviation (px) of what is drawn from what must be: leader start on the label-box edge, leader end / dim tick on the target."""
    sd = 0.0
    if r["kind"] == "callout":
        x0, y0, x1, y1 = r["box"]; sx, sy = r["start"]
        dx = min(abs(sx - x0), abs(sx - x1)) if y0 - 1e-6 <= sy <= y1 + 1e-6 else 1e9; dy = min(abs(sy - y0), abs(sy - y1)) if x0 - 1e-6 <= sx <= x1 + 1e-6 else 1e9
        sd = min(dx, dy)
    ed = math.hypot(r["drawn"][0] - r["target"][0], r["drawn"][1] - r["target"][1])
    td = math.hypot(r["tick"][0] - r["target"][0], r["tick"][1] - r["target"][1]) if "tick" in r else 0.0
    return (r["kind"], r["beat"], sd, ed, td)


def run(topic, args):
    from . import script as SC, voice as VO, encode
    import soundfile as sf
    opt = lambda k: args[args.index(k) + 1] if k in args else None
    topic = Path(topic); out = topic / "out"; cache = topic / "cache"; out.mkdir(exist_ok=True); cache.mkdir(exist_ok=True); name = topic.name
    T = {}; t00 = time.time()
    def stage(nm, t0): T[nm] = round(time.time() - t0, 1); print(f"[{nm}] {T[nm]}s", flush=True)
    t0 = time.time(); S = SC.load(topic); beats = S["beats"]; cfg = load_cfg(topic); stage("script", t0)
    t0 = time.time(); jobs = ensure_images(topic, cfg); stage("images", t0)
    t0 = time.time(); VO.generate(topic, beats, S); stage("voice_tts", t0)
    t0 = time.time(); voice, BT, TOTAL = VO.narrate(topic, beats, cache); stage("narration", t0)
    P = build_plan(S, voice, BT, TOTAL, cfg, jobs, topic); nframes = int(math.ceil(TOTAL * FPS))
    pkl = cache / "plan_painted.pkl"; tmpk = cache / "plan_painted.pkl.tmp"; pickle.dump(P, open(tmpk, "wb")); os.replace(tmpk, pkl)
    if opt("--frames"):
        init_worker(str(pkl)); fd = out / "frames"; fd.mkdir(exist_ok=True)
        for sec in [float(x) for x in opt("--frames").split(",")]:
            p = fd / f"p_{sec:06.2f}.png"; _R.frame(int(round(sec * FPS))).save(p); print(p)
        return
    t0 = time.time(); audio = SIL.make_audio(voice, TOTAL, P); wav = cache / "audio.wav"; sf.write(wav, audio, VO.SR); stage("audio", t0)
    t0 = time.time(); step = 75
    key = hashlib.sha1(open(pkl, "rb").read() + Path(__file__).read_bytes() + f"{nframes}|{FPS}".encode()).hexdigest()[:16]
    for q in cache.glob("_part*.tmp.mp4"): q.unlink(missing_ok=True)
    jobs_ = [(i, f0, min(nframes, f0 + step), str(cache), key) for i, f0 in enumerate(range(0, nframes, step))]
    parts, means, mints, reused, warp, devs = [], [], [], 0, 0.0, []
    with mp.get_context("spawn").Pool(4, initializer=init_worker, initargs=(str(pkl),)) as pool:
        for k, (path, mn, mt, skipped, we, rc) in enumerate(pool.imap(render_chunk, jobs_, chunksize=1)):
            parts.append(path); means += mn; mints.append(mt); reused += bool(skipped); warp = max(warp, we); devs += rc
            print(f"  chunk {k + 1}/{len(jobs_)}  {time.time() - t0:.0f}s{'  (reused)' if skipped else ''}", flush=True)
    stage("frames", t0)
    t0 = time.time(); final = out / f"{name}.mp4"; tmpf = out / f"{name}.tmp.mp4"; encode.mux(parts, wav, tmpf, cache); os.replace(tmpf, final); stage("mux", t0)
    m = np.array(means); jumps = np.abs(np.diff(m)); jmax = float(jumps.max()) if len(jumps) else 0.0; jt = float((int(jumps.argmax()) + 1) / FPS) if len(jumps) else 0.0
    dur_s = nframes / FPS; warns = list(S["warnings"]); min_text = float(min(mints)) if mints else 0.0
    if not (40 <= dur_s <= 50): warns.append(f"DURATION {dur_s:.1f}s outside 40-50s")
    if jmax > 15: warns.append(f"FLICKER max frame-to-frame brightness jump {jmax:.1f} at {jt:.2f}s > 15")
    sdev = max([d["start_dev"] for d in devs] or [0.0]); edev = max([d["end_dev"] for d in devs] or [0.0]); tdev = max([d["tick_dev"] for d in devs] or [0.0])
    callout_ok = bool(sdev <= 2 and edev <= 2 and tdev <= 2 and warp <= 2)
    if not callout_ok: warns.append(f"CALLOUT leader check failed: start {sdev:.2f} end {edev:.2f} tick {tdev:.2f} warp {warp:.2f} px (> 2)")
    small = out / f"{name}_9mb.mp4"; size9 = None
    if "--no-9mb" not in args:
        t0 = time.time(); size9, vb = encode.encode_9mb(final, small, TOTAL, cache); stage("encode_9mb", t0)
        if size9 >= 10_000_000: warns.append("9mb file still >= 10 MB")
    t0 = time.time(); encode.contact_sheet(final, out / f"{name}_sheet.png", TOTAL); stage("sheet", t0)
    T["total"] = round(time.time() - t00, 1)
    nov = sum(len(b.get("ov", [])) for b in cfg["beats"])
    rep = dict(topic=name, title=S["title"], style="painted", model=cfg.get("model", "stabilityai/sdxl-turbo"), image_size=cfg.get("size"), steps=cfg.get("steps"),
               duration_s=round(dur_s, 2), narration_s=round(TOTAL, 2), shot_count=P["n"], avg_shot_s=round(TOTAL / P["n"], 2), crossfade_s=XF,
               min_caption_px=round(min_text, 1), chunks=len(jobs_), chunks_reused=reused, max_brightness_jump=round(jmax, 2), max_jump_at_s=round(jt, 2),
               callout_check=dict(ok=callout_ok, overlays=nov, leader_start_on_box_edge_max_px=round(sdev, 3), leader_end_vs_target_max_px=round(edev, 3),
                                  dim_tick_vs_target_max_px=round(tdev, 3), drawn_vs_rendered_pixel_max_px=round(warp, 3), limit_px=2.0),
               words=sum(len(b["text"].split()) for b in beats), mp4_bytes=final.stat().st_size, mp4_9mb_bytes=size9, warnings=warns, stage_seconds=T)
    json.dump(rep, open(out / "report.json", "w"), indent=2); print(json.dumps(rep, indent=2))
