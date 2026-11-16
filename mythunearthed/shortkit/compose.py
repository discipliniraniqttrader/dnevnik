"""Frame compositor: shots -> RGB frames (presenter, corner Ezra, HUD, captions, transitions, shakes)."""
import json, math, os, pickle, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
from .common import W, H, FPS, GOLD, CREAM, INK, F, cap_font, big_font, ease, out_back, KW_GOLD
from .plan import KW_ZOOM, CAP_PX
from . import backdrops, text as TX, events as EV, maps

_R = None
CPANEL = (470, 1300, 640, 416)     # (height, top y, right-panel x0, width): bottom corner, below the caption band


class Renderer:
    def __init__(self, plan_path):
        D = pickle.load(open(plan_path, "rb"))
        self.D = D; self.S = D["S"]; self.P = D["plan"]; self.beats = self.S["beats"]; self.shots = self.P["shots"]
        self.NF = D["NF"]; self.ezra_dir = Path(D["ezra_dir"]); self.BT = D["BT"]; self.TOTAL = D["TOTAL"]
        self.mk = maps.MapKit(D["region"], self.S["places"], self.P["pin_t"]) if any(s["kind"] == "map" for s in self.shots) else None
        self.f = {"chip": F("sans-black.ttf", 44), "meta": F("sans-semi.ttf", 44), "badge": big_font("1/4", 60)}
        self.mt = 9999.0                       # smallest overlay text size drawn (px) -> report guard
        self.pin_xy = {}                       # shot idx -> [(x, y)] of visible map pins (caption auto-nudge)
        self._cs = {}                          # caption word sprites
        self.kwt = list(self.P.get("kw_times", []))
        self.NFR = int(math.ceil(self.TOTAL * FPS))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.spot = np.clip((np.sqrt(((xx - 540) / 1.0) ** 2 + ((yy - 820) / 1.25) ** 2) - 380) / 760, 0, 1) ** 1.3
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
            cols = 1 if n == 1 else 2; bw, bh, gap = (560 if cols == 1 else 488), 124, 14
            rows = int(math.ceil(n / cols)); x0 = (W - (bw * cols + gap * (cols - 1))) / 2; y0 = 1330
            for i, (nm, key, tw) in enumerate(tiles):
                if key not in self._ic: self._ic[key] = Image.fromarray(maps.icon_sprite(self.S["places"][key]["icon"], 150))
                icon = self._ic[key]
                e = out_back((t - (tw - .5)) / .4) if t > tw - .5 else 0
                e = max(e, out_back((lt - (.4 + i * .12)) / .4))
                if lt < .4 + i * .12 and t < tw - .5: e = 0
                if e <= 0: continue
                act = 1 if tw - .05 <= t < tw + .75 else 0
                sc = (.9 + .1 * min(e, 1.2)) * (1.05 if act else 1.0)
                w_, h_ = int(bw * sc), int(bh * sc)
                cx = x0 + bw / 2 + (i % cols) * (bw + gap); cy = y0 + bh / 2 + (i // cols) * (bh + gap)
                panel = Image.new("RGBA", (w_ + 40, h_ + 40), (0, 0, 0, 0)); pd = ImageDraw.Draw(panel)
                pd.rounded_rectangle([20, 20, 20 + w_, 20 + h_], 28, fill=(58, 44, 22, 245) if act else (30, 26, 46, 235),
                                     outline=(232, 170, 40, 255) if act else (200, 160, 80, 230), width=6 if act else 4)
                isz = int(104 * sc); ic = icon.resize((isz, int(icon.height * isz / icon.width)), Image.LANCZOS)
                panel.alpha_composite(ic, (int(20 + 14), int(20 + h_ / 2 - ic.height / 2)))
                rcx, rcy, rr = 20 + 14 + ic.width / 2, 20 + h_ / 2 - ic.height * .08, ic.width * .5
                if self.S["places"][key]["conf"] != "dashed": pd.ellipse([rcx - rr, rcy - rr, rcx + rr, rcy + rr], outline=(255, 214, 120, 200), width=4)
                else:
                    for q in range(14): pd.arc([rcx - rr, rcy - rr, rcx + rr, rcy + rr], q * 360 / 14 + t * 30, q * 360 / 14 + t * 30 + 14, fill=(255, 232, 190, 210), width=4)
                tx0 = 20 + 14 + isz + 18; room = w_ + 20 - tx0 - 16; sz = int(52 * sc)
                while cap_font(nm, sz).getlength(nm) > room and sz > 44: sz -= 2
                nm_ = nm
                while cap_font(nm_, sz).getlength(nm_) > room and len(nm_) > 3: nm_ = nm_[:-2] + "…" if not nm_.endswith("…") else nm_[:-2] + "…"
                self.mt = min(self.mt, sz)
                pd.text((tx0, 20 + h_ / 2), nm_, font=cap_font(nm_, sz), fill=(255, 226, 150, 255) if act else (246, 236, 210, 255), anchor="lm", stroke_width=3, stroke_fill=(10, 8, 6, 255))
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
            by = 880 if n else 760
            self.mt = min(self.mt, 84 * min(1.0, (W - 60) / tw_))
            img.alpha_composite(ban, (int(540 - ban.width / 2), by))
            ay = by + 178 + 8 * math.sin(t * 6)
            d2 = ImageDraw.Draw(img, "RGBA")
            d2.polygon([(540 - 34, ay), (540 + 34, ay), (540, ay + 54)], fill=(255, 226, 150, int(255 * a)), outline=(10, 8, 6, int(255 * a)))

    # ------------------------------------------------------------ stamp / callout / corner Ezra
    def stamp_sprite(self, big, small):
        k = (big, small)
        if k in self._stamps: return self._stamps[k]
        w_, h_ = 760, 300
        im = Image.new("RGBA", (w_ + 60, h_ + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle([30, 70, 30 + w_, 30 + h_], 26, fill=(236, 214, 160, 255), outline=(60, 40, 20, 255), width=6)
        d.rounded_rectangle([30, 22, 346, 100], 20, fill=(236, 214, 160, 255), outline=(60, 40, 20, 255), width=6)
        d.rectangle([34, 80, 342, 104], fill=(236, 214, 160, 255))
        d.text((180, 62), "CASE FILE", font=F("sans-semi.ttf", 44), fill=(90, 60, 30, 255), anchor="mm")
        red = (196, 34, 30, 255)
        size = 168
        while size > 70 and cap_font(big, size).getlength(big) > w_ - 130: size -= 8
        d.rounded_rectangle([70, 112, 30 + w_ - 40, 250], 14, outline=red, width=8)
        d.text((30 + w_ / 2, 183), big, font=cap_font(big, size), fill=red, anchor="mm")
        ss = 50
        while ss > 44 and cap_font(small, ss).getlength(small) > w_ - 60: ss -= 2
        while len(small) > 4 and cap_font(small, ss).getlength(small) > w_ - 60: small = small[:-2].rstrip() + "…"
        d.text((30 + w_ / 2, 266), small, font=cap_font(small, ss), fill=(70, 46, 24, 255), anchor="mm")
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
        self.mt = min(self.mt, 44)
        sp = sp.rotate(-4, Image.BICUBIC, expand=True).resize((int(sp.width * sc), int(sp.height * sc)), Image.LANCZOS)
        if a < 1: sp.putalpha(sp.split()[3].point(lambda v: int(v * a)))
        img.alpha_composite(sp, (int(540 - sp.width / 2), int(450 - sp.height / 2)))
        if 5 <= f < 12:
            e = (f - 5) / 7; ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ov).ellipse([540 - 420 * e, 450 - 200 * e, 540 + 420 * e, 450 + 200 * e], outline=(255, 240, 210, int(200 * (1 - e))), width=6)
            img.alpha_composite(ov)

    def corner(self, img, s, t):
        lt = t - s["t0"]; side = s["ezra"]
        slide = (1 - out_back(lt / 0.35, 1.2)) * 520 if s["ezra_slide"] else 0
        px0, py0, px1, py1 = (CPANEL[2], CPANEL[1], CPANEL[3] + CPANEL[2], CPANEL[1] + CPANEL[0]) if side == "right" else (24, CPANEL[1], 24 + CPANEL[3], CPANEL[1] + CPANEL[0])
        sc = 0.45
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
        while cap_font(text, size).getlength(text) + 20 > 960 and size > 44: size -= 4
        self.mt = min(self.mt, size)
        col = (255, 90, 76) if text.upper().strip("!") in ("NOTHING VERIFIED", "NATURAL?", "NOT PROVEN", "DISPUTED", "UNPROVEN") else (255, 244, 224)
        ft = cap_font(text, size); tw = int(ft.getlength(text)) + 80
        lay = Image.new("RGBA", (tw, 190), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        ld.text((tw / 2, 80), text, font=ft, fill=col, anchor="mm", stroke_width=11, stroke_fill=INK)
        bw = (tw - 80) * ease(f / 8)
        ld.rounded_rectangle([tw / 2 - bw / 2, 140, tw / 2 + bw / 2, 154], 6, fill=(232, 170, 40, 255), outline=INK, width=3)
        lay = lay.resize((int(tw * sc), int(190 * sc)), Image.BICUBIC)
        if a < 1: lay.putalpha(lay.split()[3].point(lambda v: int(v * a)))
        img.alpha_composite(lay, (int(540 - lay.width / 2), int(385 - lay.height * 0.42)))

    # ------------------------------------------------------------ shot -> image
    def shot_img(self, s, t):
        k = s["kind"]; b = self.beats[s["beat"] - 1]
        if k in ("presenter", "end"):
            img = self.presenter(s, t)
        else:
            c = SimpleNamespace(lt=t - s["ot0"], dur=s["odur"], t=t, b=b, sub=s["sub"], nsub=s["nsub"], tm=s.get("tm", {}), slt=t - s["t0"], sdur=s["dur"])
            if k == "map": arr = self.mk.frame(s, t); self.pin_xy[s["idx"]] = list(getattr(self.mk, "last_pins", []))
            elif k == "text": arr = TX.render(c)
            else: arr = EV.render(c)
            img = Image.fromarray(np.asarray(arr)).convert("RGBA")
            img.alpha_composite(self.shade)
        if s.get("ezra"): self.corner(img, s, t)
        if s.get("stamp"): self.stamp(img, s["stamp"], t)
        if s.get("callout"): self.callout(img, s["callout"][0], t - s["callout"][1])
        return img.convert("RGB")

    def kw_bump(self, t):
        """soft 6-8% zoom-in on the shot at each keyword: smooth ramp up (0.2 s), slow release (0.75 s). Never a flash."""
        z = 0.0
        for k in self.kwt:
            u = t - (k - .05)
            if 0 <= u < .95: z = max(z, KW_ZOOM * (ease(u / .2) if u < .2 else 1 - ease((u - .2) / .75)))
        return z

    def giant(self, img, txt, lt):
        f = lt * FPS
        if f < 0: return img
        size = 330
        while big_font(txt, size).getlength(txt) > 940 and size > 120: size -= 10
        self.mt = min(self.mt, size)
        k = (txt, size)
        if k not in self._cs:
            ft = big_font(txt, size); pad = 60; w_ = int(ft.getlength(txt)) + pad * 2; h_ = int(size * 1.5)
            lay = Image.new("RGBA", (w_, h_), (0, 0, 0, 0)); ImageDraw.Draw(lay).text((w_ / 2, h_ / 2 + 10), txt, font=ft, fill=KW_GOLD, anchor="mm", stroke_width=20, stroke_fill=INK)
            sh = Image.new("RGBA", lay.size, (0, 0, 0, 0)); sh.paste((0, 0, 0, 170), (0, 0), lay.split()[3]); sh = sh.filter(ImageFilter.GaussianBlur(14))
            out = Image.new("RGBA", lay.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 12)); out.alpha_composite(lay); self._cs[k] = out
        spr = self._cs[k]; sc = 1.0 + .3 * (1 - out_back(f / 7))
        spr = spr.resize((int(spr.width * sc), int(spr.height * sc)), Image.BICUBIC)
        a = min(1.0, f / 3)
        if a < 1: spr.putalpha(spr.split()[3].point(lambda v: int(v * a)))
        base = img.convert("RGBA"); base.alpha_composite(spr, (int(540 - spr.width / 2), int(700 - spr.height / 2))); return base.convert("RGB")

    def final(self, s, t, extra=1.0):
        img = self.shot_img(s, t)
        sc = extra
        wow = s.get("wow"); p_ = (t - s["t0"]) / max(s["dur"], 1e-3)
        if wow in ("push", "spot", "number"):
            sc *= 1.0 + .14 * ease(p_)                                          # fast-but-smooth push-in
            if wow == "spot":
                st = .5 * ease((t - s["t0"]) / .3)                                # object spotlight: edges fall off, ramped in over 9 frames
                a_ = np.asarray(img, np.float32) * (1 - st * self.spot[..., None]); img = Image.fromarray(np.clip(a_, 0, 255).astype(np.uint8))
            if wow == "number": img = self.giant(img, s["giant"], t - s["t0"] - .04)
        elif s["kind"] != "map":
            sc *= (1.0 + .07 * p_) if s["sub"] % 2 == 0 else (1.07 - .06 * p_)
        sc *= 1.0 + self.kw_bump(t)
        dx = dy = 0.0; shk = 0.0
        for st, amp, dur in s.get("shakes", []):
            d_ = t - st
            if 0 <= d_ < dur: shk = max(shk, min(amp, 5) * math.exp(-4 * d_ / dur))
        if shk > .5:
            r = np.random.default_rng(int(round(t * FPS)))
            dx, dy = r.uniform(-1, 1, 2) * shk; sc *= 1.0 + shk / 230
        if sc == 1.0 and dx == 0: return img
        ax, ay = 540, 960
        return img.transform((W, H), Image.AFFINE, (1 / sc, 0, ax - ax / sc - dx / sc, 0, 1 / sc, ay - ay / sc - dy / sc), Image.BILINEAR)

    # ------------------------------------------------------------ HUD
    # ---- big centered captions
    def _word_sprite(self, txt, size, col):
        k = (txt, size, col)
        if k not in self._cs:
            ft = big_font(txt, size); pad = 40; w_ = int(ft.getlength(txt)) + pad * 2; h_ = int(size * 1.55)
            lay = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
            ImageDraw.Draw(lay).text((w_ / 2, h_ / 2 + size * .04), txt, font=ft, fill=col + (255,), anchor="mm", stroke_width=max(8, int(size * .12)), stroke_fill=INK)
            sh = Image.new("RGBA", lay.size, (0, 0, 0, 0)); sh.paste((0, 0, 0, 150), (0, 0), lay.split()[3]); sh = sh.filter(ImageFilter.GaussianBlur(9))
            out = Image.new("RGBA", lay.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 8)); out.alpha_composite(lay); self._cs[k] = (out, pad)
        return self._cs[k]

    def caption_at(self, t):
        for c in self.P["caps"]:
            if c["t0"] - 1e-3 <= t < c["t1"]: return c
        return None

    def avoid_rects(self, s, t):
        """screen rects the caption must stay off: Ezra's face / corner panel, active map pins, end-card tiles"""
        r = []
        if s["kind"] in ("presenter", "end"):
            end = s["kind"] == "end"; p = (t - s["t0"]) / max(s["dur"], 1e-3)
            sc = .74 if end else s["sc"][0] + (s["sc"][1] - s["sc"][0]) * min(max(p, 0), 1.2)
            x, y = (-60, 300) if end else (int(450 - 310 * sc), int(1520 - 1200 * sc))
            r.append((x + 900 * sc * .2, y, x + 900 * sc * .8, y + 1200 * sc * .42))
        if s.get("ezra"):
            r.append((CPANEL[2] - 10, CPANEL[1] - 12, W, H) if s["ezra"] == "right" else (0, CPANEL[1] - 12, 24 + CPANEL[3] + 10, H))
        for (x, y) in self.pin_xy.get(s["idx"], []): r.append((x - 120, y - 190, x + 120, y + 70))
        return r

    def captions(self, img, t, s):
        c = self.caption_at(t)
        if c is None: return
        rects = self.avoid_rects(s, t)
        i = s["idx"]
        if i and t < s["t0"] + s["nt"] / FPS: rects += self.avoid_rects(self.shots[i - 1], t)
        words = c["words"]; size = CAP_PX
        space = lambda sz: int(sz * .36)
        tw = lambda sz: sum(big_font(w, sz).getlength(w) for w in words) + space(sz) * (len(words) - 1)
        while tw(size) > 1000 and size > 64: size -= 4
        self.mt = min(self.mt, size)
        wtot = tw(size); hh = size * 1.25
        best = None
        for cy in (1200, 1160, 1240, 1120, 1280, 1070, 1340, 1010):
            bx = (540 - wtot / 2 - 20, cy - hh / 2, 540 + wtot / 2 + 20, cy + hh / 2)
            ov = sum(max(0, min(bx[2], r[2]) - max(bx[0], r[0])) * max(0, min(bx[3], r[3]) - max(bx[1], r[1])) for r in rects)
            if best is None or ov < best[0]: best = (ov, cy)
            if ov == 0: break
        cy = best[1]
        f0 = (t - c["t0"]) * FPS
        ent = .9 + .1 * ease(f0 / 3)                                   # tiny settle on every new chunk (no fade, no flash)
        ov_ = Image.new("RGBA", (W, int(size * 1.9)), (0, 0, 0, 0))
        x = 540 - wtot * ent / 2
        for w, isk in zip(words, c["kw"]):
            spr, pad = self._word_sprite(w, size, KW_GOLD if isk else (255, 255, 255))
            wd = big_font(w, size).getlength(w) * ent; sc = ent
            if isk and c["kt"] is not None:
                pf = (t - c["kt"]) * FPS
                if 0 <= pf < 6: sc *= 1 + .12 * math.sin(math.pi * pf / 6)            # 1.0 -> 1.12 -> 1.0 over 6 frames
            sp = spr if abs(sc - 1) < 1e-3 else spr.resize((int(spr.width * sc), int(spr.height * sc)), Image.BICUBIC)
            ov_.alpha_composite(sp, (int(x + wd / 2 - sp.width / 2), int(ov_.height / 2 - sp.height / 2)))
            x += wd + space(size) * ent
        img.paste(ov_.convert("RGB"), (0, int(cy - ov_.height / 2)), ov_.split()[3])

    def hud(self, img, t, s=None):
        d = ImageDraw.Draw(img, "RGBA"); f = self.f
        bi = max([i for i, b in enumerate(self.BT) if t >= b["t0"]] or [0])
        chip = self.S["chip"]
        while d.textlength(chip, font=f["chip"]) > 640 and len(chip) > 3: chip = chip[:-2].rstrip() + "…"
        d.rounded_rectangle([60, 120, 60 + d.textlength(chip, font=f["chip"]) + 40, 190], 10, fill=GOLD)
        d.text((80, 156), chip, font=f["chip"], fill=(20, 14, 8), anchor="lm")
        src = self.beats[bi].get("source", "-")
        if src and src != "-":
            while d.textlength(src, font=f["meta"]) > 800 and len(src) > 6: src = src[:-2].rstrip() + "…"
            d.text((62, 208), src, font=f["meta"], fill=(235, 225, 200), stroke_width=4, stroke_fill=INK)
            self.mt = min(self.mt, 44)
        self.mt = min(self.mt, 44)
        # numbered reveal badge (top-right), slides in over 8 frames and out over 6
        for a0, a1, lab in self.P.get("reveals", []):
            if a0 <= t < a1:
                lt = t - a0; fi = lt * FPS; fo = (a1 - t) * FPS
                off = (1 - out_back(fi / 8, 1.4)) * 330 if fi < 8 else (ease(1 - fo / 6) * 330 if fo < 6 else 0)
                bw = int(d.textlength(lab, font=f["badge"])) + 56
                x1 = W - 48 + off; x0 = x1 - bw
                d.rounded_rectangle([x0, 118, x1, 196], 22, fill=GOLD + (255,), outline=INK + (255,), width=5)
                d.text(((x0 + x1) / 2, 158), lab, font=f["badge"], fill=(20, 14, 8), anchor="mm")
                self.mt = min(self.mt, 60)
        if s is not None: self.captions(img, t, s)
        # thin gold progress bar at the very top
        fr = min(1.0, (t * FPS + 1) / self.NFR)
        d.rectangle([0, 0, W, 5], fill=(0, 0, 0, 90)); d.rectangle([0, 0, int(W * fr), 5], fill=GOLD + (255,))

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
        self.hud(img, t, s)
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


def _probe_frames(path):
    """number of video packets in an mp4 (a truncated/unfinished file has no moov -> ffprobe fails -> -1)"""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(path)],
                           capture_output=True, text=True, timeout=120)
        return int(r.stdout.strip().split()[0]) if r.returncode == 0 and r.stdout.strip() else -1
    except Exception: return -1


def chunk_ok(path, side, n, key):
    """a chunk is reusable when its mp4 decodes to exactly n frames and its sidecar was written for the same plan+code (key)"""
    try:
        if not Path(path).exists() or not Path(side).exists(): return None
        m = json.load(open(side))
        if m.get("key") != key or m.get("frames") != n or len(m.get("means", [])) != n: return None
        return m if _probe_frames(path) == n else None
    except Exception: return None


def render_chunk(job):
    idx, f0, f1, outdir, key = job
    path = Path(outdir) / f"_part{idx:03d}.mp4"; side = Path(outdir) / f"_part{idx:03d}.json"
    n = f1 - f0
    m = chunk_ok(path, side, n, key)
    if m is not None: return str(path), m["means"], m["mintext"], True
    tmp = Path(outdir) / f"_part{idx:03d}.tmp.mp4"
    for q in (tmp, path, side): q.unlink(missing_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)], stdin=subprocess.PIPE)
    means = []; _R.mt = 9999.0
    for fi in range(f0, f1):
        im = _R.frame(fi); a = np.asarray(im)
        means.append(float(a[::8, ::8].mean()))
        ff.stdin.write(a.tobytes())
    ff.stdin.close()
    if ff.wait() != 0: raise RuntimeError(f"ffmpeg failed on chunk {idx}")
    if _probe_frames(tmp) != n: raise RuntimeError(f"chunk {idx}: frame count mismatch")
    mt = float(_R.mt)
    stmp = Path(outdir) / f"_part{idx:03d}.json.tmp"
    json.dump(dict(key=key, frames=n, means=means, mintext=mt), open(stmp, "w")); os.replace(stmp, side)     # atomic: sidecar first, video last
    os.replace(tmp, path)
    return str(path), means, mt, False


def render_preview(plan_path, times, outdir):
    r = Renderer(plan_path); Path(outdir).mkdir(parents=True, exist_ok=True); paths = []
    for sec in times:
        p = Path(outdir) / f"f_{float(sec):06.2f}.png"; r.frame(int(round(float(sec) * FPS))).save(p); paths.append(str(p))
    return paths
