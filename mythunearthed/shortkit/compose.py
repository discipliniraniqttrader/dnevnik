"""Frame compositor: shots -> RGB frames (presenter, corner Ezra, HUD, captions, transitions, shakes)."""
import math, pickle, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
from .common import W, H, FPS, GOLD, CREAM, INK, F, cap_font, ease, out_back
from . import backdrops, text as TX, events as EV, maps

_R = None


class Renderer:
    def __init__(self, plan_path):
        D = pickle.load(open(plan_path, "rb"))
        self.D = D; self.S = D["S"]; self.P = D["plan"]; self.beats = self.S["beats"]; self.shots = self.P["shots"]
        self.NF = D["NF"]; self.ezra_dir = Path(D["ezra_dir"]); self.BT = D["BT"]; self.TOTAL = D["TOTAL"]
        self.mk = maps.MapKit(D["region"], self.S["places"], self.P["pin_t"]) if any(s["kind"] == "map" for s in self.shots) else None
        self.f = {"chip": F("sans-black.ttf", 38), "meta": F("sans-semi.ttf", 30)}
        g = np.random.default_rng(9).integers(0, 255, (H // 2, W // 2), dtype=np.uint8)
        self.grain = Image.fromarray(g).resize((W, H), Image.NEAREST)
        y = np.linspace(-1, 1, H)[:, None]; x = np.linspace(-1, 1, W)[None, :]
        v = np.clip((x ** 2 * .5 + y ** 2 * .35) - .15, 0, 1) * 200
        bot = np.clip((np.arange(H) - 1250) / 670, 0, 1)[:, None] ** 1.4 * 230
        a = (np.clip(np.maximum(v, bot), 0, 235) * 0.7).astype(np.uint8)
        self.shade = Image.fromarray(np.dstack([np.full((H, W, 3), (8, 10, 18), np.uint8), np.broadcast_to(a, (H, W))]), "RGBA")
        self._stamps = {}; self._ic = {}
        self._fallback = None

    # ------------------------------------------------------------ Ezra
    def ezra(self, t):
        i = min(int(t * FPS), self.NF - 1)
        fp = self.ezra_dir / f"{i:05d}.png"
        if not fp.exists():                                   # preview before the Ezra track is rendered
            alts = sorted(self.ezra_dir.glob("*.png")) or sorted((Path(__file__).resolve().parent.parent / "noah/ezra").glob("0010*.png"))
            if alts: fp = alts[0]
            else: return Image.new("RGBA", (900, 1200), (0, 0, 0, 0))
        im = Image.open(fp).convert("RGBA")
        r, g, b_, a = im.split()
        return Image.merge("RGBA", (r.point(lambda v: int(v * .96)), g.point(lambda v: int(v * .92)), b_.point(lambda v: int(v * .94)), a))

    # ------------------------------------------------------------ presenter / end card
    def presenter(self, s, t):
        back, front = backdrops.backdrop(s["backdrop"], t, s["variant"])
        lt = t - s["ot0"]; end = s["kind"] == "end"
        p = (t - s["t0"]) / max(s["dur"], 1e-3)
        sc = .74 if end else s["sc"][0] + (s["sc"][1] - s["sc"][0]) * min(max(p, 0), 1.2)
        ez = self.ezra(t).resize((int(900 * sc), int(1200 * sc)), Image.BICUBIC)
        back = back.convert("RGBA")
        x, y = (-60, 300) if end else (int(450 - 310 * sc), int(1520 - 1200 * sc))
        back.alpha_composite(ez, (x, y)); back.alpha_composite(front); back.alpha_composite(self.shade)
        img = back
        b = self.beats[s["beat"] - 1]
        if b.get("icon") and b.get("count") and not end: self.icon_row(img, lt, b["icon"], min(int(b["count"]), 5))
        if end: self.end_card(img, s, t)
        return img

    def icon_row(self, img, lt, kind, n):
        if kind not in self._ic: self._ic[kind] = maps.icon_sprite(kind, 150)
        ic = self._ic[kind]
        for i in range(n):
            dt = lt - (0.9 + i * 0.32)
            if dt < 0: continue
            e = out_back(dt / .35)
            spr = Image.fromarray(ic).resize((int(150 * .55 * e) + 1, int(ic.shape[0] * .55 * e) + 1), Image.LANCZOS)
            step = 250 if n <= 4 else 200
            img.alpha_composite(spr, (int(540 - (n - 1) * step / 2 + i * step - spr.width / 2), int(450 - spr.height / 2)))

    def end_card(self, img, s, t):
        lt = t - s["ot0"]; tiles = self.P["tiles"]; n = len(tiles)
        d = ImageDraw.Draw(img, "RGBA")
        if n:
            gap = 12; bw = min(240, int((W - 84 - gap * (n - 1)) / n)); bh = 250; x0 = (W - (bw * n + gap * (n - 1))) / 2; y0 = 1160
            for i, (nm, key, tw) in enumerate(tiles):
                if key not in self._ic: self._ic[key] = Image.fromarray(maps.icon_sprite(self.S["places"][key]["icon"], 150))
                icon = self._ic[key]
                e = out_back((t - (tw - .5)) / .4) if t > tw - .5 else 0
                e = max(e, out_back((lt - (.4 + i * .12)) / .4))
                if lt < .4 + i * .12 and t < tw - .5: e = 0
                if e <= 0: continue
                act = 1 if tw - .05 <= t < tw + .75 else 0
                sc = (.9 + .1 * min(e, 1.2)) * (1.08 if act else 1.0)
                w_, h_ = bw * sc, bh * sc
                cx = x0 + bw / 2 + i * (bw + gap); cy = y0 + bh / 2
                panel = Image.new("RGBA", (int(w_) + 40, int(h_) + 40), (0, 0, 0, 0)); pd = ImageDraw.Draw(panel)
                pd.rounded_rectangle([20, 20, 20 + w_, 20 + h_], 30, fill=(58, 44, 22, 245) if act else (30, 26, 46, 235),
                                     outline=(232, 170, 40, 255) if act else (200, 160, 80, 230), width=6 if act else 4)
                ic = icon.resize((int(130 * sc), int(icon.height * 130 / 150 * sc)), Image.LANCZOS)
                panel.alpha_composite(ic, (int(20 + w_ / 2 - ic.width / 2), 34))
                rcx, rcy, rr = 20 + w_ / 2, 20 + 34 + ic.height * .42, ic.width * .58
                if self.S["places"][key]["conf"] != "dashed": pd.ellipse([rcx - rr, rcy - rr, rcx + rr, rcy + rr], outline=(255, 214, 120, 200), width=4)
                else:
                    for q in range(14): pd.arc([rcx - rr, rcy - rr, rcx + rr, rcy + rr], q * 360 / 14 + t * 30, q * 360 / 14 + t * 30 + 14, fill=(255, 232, 190, 210), width=4)
                ft = cap_font(nm, int((34 if len(nm) < 8 else 29 if len(nm) < 11 else 24) * sc))
                pd.text((20 + w_ / 2, 20 + h_ - 46 * sc), nm, font=ft, fill=(255, 226, 150, 255) if act else (246, 236, 210, 255), anchor="mm", stroke_width=3, stroke_fill=(10, 8, 6, 255))
                if act:
                    gl = panel.filter(ImageFilter.GaussianBlur(14)); gl.putalpha(gl.split()[3].point(lambda v: int(v * .7)))
                    img.alpha_composite(gl, (int(cx - panel.width / 2), int(cy - panel.height / 2)))
                img.alpha_composite(panel, (int(cx - panel.width / 2), int(cy - panel.height / 2)))
        a = ease((lt - 1.2) / .4)
        if a > 0:
            pulse = 1 + .03 * math.sin(t * 6)
            ft = F("sans-black.ttf", 84); txt = (self.S.get("outro") or "COMMENT YOUR PICK").upper()
            tw_ = int(ft.getlength(txt)) + 90
            ban = Image.new("RGBA", (tw_, 190), (0, 0, 0, 0)); bd = ImageDraw.Draw(ban)
            bd.rounded_rectangle([10, 30, tw_ - 10, 170], 28, fill=(232, 170, 40, 255), outline=(10, 8, 6, 255), width=7)
            bd.text((tw_ / 2, 100), txt, font=ft, fill=(20, 12, 6, 255), anchor="mm")
            sc = min(1.0, (W - 60) / tw_) * pulse * (1.25 - .25 * out_back((lt - 1.2) / .35))
            ban = ban.rotate(-2.5, Image.BICUBIC, expand=True).resize((int(ban.width * sc), int(ban.height * sc)), Image.LANCZOS)
            if a < 1: ban.putalpha(ban.split()[3].point(lambda v: int(v * a)))
            by = 905 if n else 760
            img.alpha_composite(ban, (int(540 - ban.width / 2), by))
            ay = by + 185 + 8 * math.sin(t * 6)
            d2 = ImageDraw.Draw(img, "RGBA")
            d2.polygon([(540 - 34, ay), (540 + 34, ay), (540, ay + 54)], fill=(255, 226, 150, int(255 * a)), outline=(10, 8, 6, int(255 * a)))

    # ------------------------------------------------------------ stamp / callout / corner Ezra
    def stamp_sprite(self, big, small):
        k = (big, small)
        if k in self._stamps: return self._stamps[k]
        w_, h_ = 760, 300
        im = Image.new("RGBA", (w_ + 60, h_ + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle([30, 70, 30 + w_, 30 + h_], 26, fill=(236, 214, 160, 255), outline=(60, 40, 20, 255), width=6)
        d.rounded_rectangle([30, 30, 330, 100], 20, fill=(236, 214, 160, 255), outline=(60, 40, 20, 255), width=6)
        d.rectangle([34, 80, 326, 104], fill=(236, 214, 160, 255))
        d.text((180, 62), "CASE FILE", font=F("sans-semi.ttf", 30), fill=(90, 60, 30, 255), anchor="mm")
        red = (196, 34, 30, 255)
        size = 168
        while size > 70 and cap_font(big, size).getlength(big) > w_ - 130: size -= 8
        d.rounded_rectangle([70, 112, 30 + w_ - 40, 250], 14, outline=red, width=8)
        d.text((30 + w_ / 2, 183), big, font=cap_font(big, size), fill=red, anchor="mm")
        ss = 34
        while ss > 18 and cap_font(small, ss).getlength(small) > w_ - 60: ss -= 2
        d.text((30 + w_ / 2, 272), small, font=cap_font(small, ss), fill=(70, 46, 24, 255), anchor="mm")
        a = np.asarray(im).copy()
        rn = np.random.default_rng(len(big) * 7 + ord(big[-1]))
        spk = cv2.GaussianBlur(rn.random(a.shape[:2]).astype(np.float32), (0, 0), 1.3)
        mk = (spk < np.percentile(spk, 9)); isred = (a[..., 0] > 150) & (a[..., 1] < 80)
        a[mk & isred] = (236, 214, 160, 255)
        im = Image.fromarray(a)
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.paste((0, 0, 0, 140), (0, 0), im.split()[3]); sh = sh.filter(ImageFilter.GaussianBlur(10))
        out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(sh, (10, 14)); out.alpha_composite(im)
        self._stamps[k] = out
        return out

    def stamp(self, img, st, t):
        big, small, t0 = st
        f = (t - t0) * FPS
        if f < 0: return
        sp = self.stamp_sprite(big, small)
        sc = 1.0 + 1.1 * (1 - ease(f / 5.0)) if f < 5 else 1.0
        a = min(1, f / 2) * (1 - ease((f / FPS - 2.6) / .4))
        if a <= 0: return
        sp = sp.rotate(-4, Image.BICUBIC, expand=True).resize((int(sp.width * sc * .9), int(sp.height * sc * .9)), Image.LANCZOS)
        if a < 1: sp.putalpha(sp.split()[3].point(lambda v: int(v * a)))
        img.alpha_composite(sp, (int(540 - sp.width / 2), int(450 - sp.height / 2)))
        if 5 <= f < 12:
            e = (f - 5) / 7; ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ov).ellipse([540 - 420 * e, 450 - 200 * e, 540 + 420 * e, 450 + 200 * e], outline=(255, 240, 210, int(200 * (1 - e))), width=6)
            img.alpha_composite(ov)

    def corner(self, img, s, t):
        lt = t - s["t0"]; side = s["ezra"]
        slide = (1 - out_back(lt / 0.35, 1.2)) * 520 if s["ezra_slide"] else 0
        px0, py0, px1, py1 = (634, 940, 1056, 1420) if side == "right" else (24, 940, 446, 1420)
        sc = 0.46
        ez = self.ezra(t).resize((int(900 * sc), int(1200 * sc)), Image.BICUBIC)
        pw, ph = px1 - px0, py1 - py0
        gr = np.linspace(0, 1, ph)[:, None, None]
        col = (np.array([60, 48, 96]) * (1 - gr) + np.array([24, 20, 44]) * gr)
        bgp = Image.fromarray(np.broadcast_to(col, (ph, pw, 3)).astype(np.uint8)).convert("RGBA")
        m = Image.new("L", (pw, ph), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, pw - 1, ph - 1], 28, fill=225)
        panel = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); panel.paste(bgp, (0, 0), m)
        panel.alpha_composite(ez, (6 if side == "left" else pw - ez.width - 6, ph - ez.height))
        a = np.asarray(panel.split()[3], np.float32) * (np.asarray(m, np.float32) > 0)
        panel.putalpha(Image.fromarray(a.astype(np.uint8)))
        ImageDraw.Draw(panel).rounded_rectangle([1, 1, pw - 2, ph - 2], 28, outline=(232, 170, 40, 255), width=4)
        if side == "right": img.alpha_composite(panel, (int(px0 + slide * .9), py0))
        else: img.alpha_composite(panel, (px0, int(py0 + slide)))

    def callout(self, img, text, dt):
        f = dt * FPS
        if f < 0: return
        a = min(1, f / 3); sc = 1.4 - 0.4 * out_back(f / 6)
        size = 100
        while cap_font(text, size).getlength(text) + 20 > 960 and size > 40: size -= 4
        col = (255, 90, 76) if text.upper().strip("!") in ("NOTHING VERIFIED", "NATURAL?", "NOT PROVEN", "DISPUTED", "UNPROVEN") else (255, 244, 224)
        ft = cap_font(text, size); tw = int(ft.getlength(text)) + 80
        lay = Image.new("RGBA", (tw, 190), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        ld.text((tw / 2, 80), text, font=ft, fill=col, anchor="mm", stroke_width=11, stroke_fill=INK)
        bw = (tw - 80) * ease(f / 8)
        ld.rounded_rectangle([tw / 2 - bw / 2, 140, tw / 2 + bw / 2, 154], 6, fill=(232, 170, 40, 255), outline=INK, width=3)
        lay = lay.resize((int(tw * sc), int(190 * sc)), Image.BICUBIC)
        if a < 1: lay.putalpha(lay.split()[3].point(lambda v: int(v * a)))
        img.alpha_composite(lay, (int(540 - lay.width / 2), int(345 - lay.height * 0.42)))

    # ------------------------------------------------------------ shot -> image
    def shot_img(self, s, t):
        k = s["kind"]; b = self.beats[s["beat"] - 1]
        if k in ("presenter", "end"):
            img = self.presenter(s, t)
        else:
            c = SimpleNamespace(lt=t - s["ot0"], dur=s["odur"], t=t, b=b, sub=s["sub"], nsub=s["nsub"], tm=s.get("tm", {}), slt=t - s["t0"], sdur=s["dur"])
            if k == "map": arr = self.mk.frame(s, t)
            elif k == "text": arr = TX.render(c)
            else: arr = EV.render(c)
            img = Image.fromarray(np.asarray(arr)).convert("RGBA")
            img.alpha_composite(self.shade)
        if s.get("ezra"): self.corner(img, s, t)
        if s.get("stamp"): self.stamp(img, s["stamp"], t)
        if s.get("callout"): self.callout(img, s["callout"][0], t - s["callout"][1])
        return img.convert("RGB")

    def final(self, s, t, extra=1.0):
        img = self.shot_img(s, t)
        sc = extra
        if s["kind"] != "map":
            p_ = (t - s["t0"]) / max(s["dur"], 1e-3)
            sc *= (1.0 + .07 * p_) if s["sub"] % 2 == 0 else (1.07 - .06 * p_)
        dx = dy = 0.0; shk = 0.0
        for st, amp, dur in s.get("shakes", []):
            d_ = t - st
            if 0 <= d_ < dur: shk = max(shk, amp * math.exp(-4 * d_ / dur))
        if shk > .5:
            r = np.random.default_rng(int(round(t * FPS)))
            dx, dy = r.uniform(-1, 1, 2) * shk; sc *= 1.0 + shk / 230
        if sc == 1.0 and dx == 0: return img
        ax, ay = 540, 960
        return img.transform((W, H), Image.AFFINE, (1 / sc, 0, ax - ax / sc - dx / sc, 0, 1 / sc, ay - ay / sc - dy / sc), Image.BILINEAR)

    # ------------------------------------------------------------ HUD
    def hud(self, img, t):
        d = ImageDraw.Draw(img, "RGBA"); f = self.f
        bi = max([i for i, b in enumerate(self.BT) if t >= b["t0"]] or [0])
        chip = self.S["chip"]
        d.rounded_rectangle([60, 120, 60 + d.textlength(chip, font=f["chip"]) + 40, 182], 10, fill=GOLD)
        d.text((80, 151), chip, font=f["chip"], fill=(20, 14, 8), anchor="lm")
        src = self.beats[bi].get("source", "-")
        if src and src != "-":
            d.text((62, 210), src, font=f["meta"], fill=(235, 225, 200), stroke_width=4, stroke_fill=INK)
        for words in self.P["words"]:
            if words and words[0][1] - .05 <= t <= words[-1][2] + .25:
                cur = max([i for i, w in enumerate(words) if w[1] <= t] or [0])
                g0 = (cur // 4) * 4; chunk = words[g0:g0 + 4]
                wl = lambda ws: sum(d.textlength(w[0] + " ", font=cap_font(w[0])) for w in ws)
                rows = [chunk[:2], chunk[2:]] if wl(chunk) > W - 100 else [chunk]
                y = 1530 - (len(rows) - 1) * 46
                for row in rows:
                    if not row: continue
                    x = (W - wl(row) + d.textlength(" ", font=cap_font("a"))) / 2
                    for w in row:
                        ft = cap_font(w[0])
                        d.text((x, y), w[0], font=ft, fill=GOLD if w is words[cur] else (255, 255, 255), stroke_width=7, stroke_fill=INK, anchor="ls")
                        x += d.textlength(w[0] + " ", font=ft)
                    y += 92
                break

    # ------------------------------------------------------------ compose
    def shot_at(self, t):
        for s in self.shots:
            if t < s["t1"]: return s
        return self.shots[-1]

    def frame(self, fi):
        t = fi / FPS
        s = self.shot_at(t); i = s["idx"]
        fin = fi - int(round(s["t0"] * FPS))
        img = self.final(s, t)
        if i and fin < s["nt"] and s["trans"] != "none":
            prev = self.final(self.shots[i - 1], t)
            p = (fin + 1) / s["nt"]; e = ease(p)
            if s["trans"] == "fade": img = Image.blend(prev, img, e)
            else: img = self.zoomfade(prev, img, p)
        self.hud(img, t)
        return Image.blend(img, Image.merge("RGB", [self.grain] * 3), 0.03)

    @staticmethod
    def zoomfade(prev, img, p):
        e = ease(p)
        A = np.asarray(prev, np.float32); B = np.asarray(img, np.float32)
        sa = 1 + .10 * e
        Az = cv2.warpAffine(A, np.array([[sa, 0, 540 - 540 * sa], [0, sa, 960 - 960 * sa]], np.float32), (W, H), flags=cv2.INTER_LINEAR)
        sb = .94 + .06 * e
        Bz = cv2.warpAffine(B, np.array([[sb, 0, 540 - 540 * sb], [0, sb, 960 - 960 * sb]], np.float32), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return Image.fromarray(np.clip(Az * (1 - e) + Bz * e, 0, 255).astype(np.uint8))


# ------------------------------------------------------------------ multiprocessing workers (spawn)
def init_worker(plan_path):
    global _R
    cv2.setNumThreads(1)
    _R = Renderer(plan_path)


def render_chunk(job):
    idx, f0, f1, outdir = job
    path = Path(outdir) / f"_part{idx:03d}.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", str(path)], stdin=subprocess.PIPE)
    means = []
    for fi in range(f0, f1):
        im = _R.frame(fi); a = np.asarray(im)
        means.append(float(a[::8, ::8].mean()))
        ff.stdin.write(a.tobytes())
    ff.stdin.close(); ff.wait()
    return str(path), means


def render_preview(plan_path, times, outdir):
    r = Renderer(plan_path); Path(outdir).mkdir(parents=True, exist_ok=True); paths = []
    for sec in times:
        p = Path(outdir) / f"f_{float(sec):06.2f}.png"; r.frame(int(round(float(sec) * FPS))).save(p); paths.append(str(p))
    return paths
