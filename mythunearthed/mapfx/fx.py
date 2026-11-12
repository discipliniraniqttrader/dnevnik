"""MythUnearthed map FX engine.

Everything works in *world pixels* of a terrain region (see build_terrain.py): x=(lon-lon0)*KX*S0, y=(lat1-lat)*S0.

Core objects
    Region(name)                    terrain image + land mask + projection (+ mip pyramid)
    View(region, lat, lon, vis, tilt, ...)   camera: world px -> screen px as ONE homography (pan/zoom/yaw/pitch)
        .project(world_pts) / .project_latlon(lat, lon)   -> screen px (same transform as the warped map)
        .render_base()               warps terrain straight from the world (true far field, no flat-frame limits)
    tilt(frame, amount) / tilt_points(pts, size, amount)    stand-alone 2.5D tilt for any already-flat frame
    water_shimmer, cloud_shadows, haze_and_dof                 map-space effects (noise is sampled in world coords)
    Route                           glowing trail, light particles, bright head, footprints (land) / wake (sea)
    Marker, Label, make_icon        pin icons (tent, walls, peak, temple, waves) with overshoot pop + sliding labels
    finish(frame, t)                grade + vignette + film grain
"""
import json, math
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

A = Path(__file__).resolve().parent.parent / "assets"
FONT_SERIF = str(A / "serif-bold.ttf")
FONT_SANS = str(A / "sans-semi.ttf")
FONT_BLACK = str(A / "sans-black.ttf")


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, np.float32) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def ease_out_back(x, k=1.9):
    x = min(max(x, 0.0), 1.0) - 1
    return 1 + (k + 1) * x ** 3 + k * x ** 2


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ====================================================================== region
class Region:
    def __init__(self, name="base", levels=4):
        self.name = name
        m = json.load(open(A / f"terrain_{name}.json"))
        self.__dict__.update(m)
        img = cv2.cvtColor(cv2.imread(str(A / f"terrain_{name}.png")), cv2.COLOR_BGR2RGB)
        mask = np.load(A / f"terrain_{name}_mask.npy").astype(np.uint8) * 255
        self.img, self.mask = [img], [mask]
        for _ in range(levels - 1):
            self.img.append(cv2.pyrDown(self.img[-1])); self.mask.append(cv2.pyrDown(self.mask[-1]))

    def wpx(self, lat, lon):
        return (np.asarray(lon) - self.lon0) * self.KX * self.S0, (self.lat1 - np.asarray(lat)) * self.S0

    def is_land(self, x, y):
        xi = np.clip(np.asarray(x).astype(int), 0, self.BW - 1); yi = np.clip(np.asarray(y).astype(int), 0, self.BH - 1)
        return self.mask[0][yi, xi] > 127


# ====================================================================== perspective tilt
class Tilt:
    """Pinhole pitch of the map plane. amount 0..1 -> 0..38 degrees. Maps flat-frame pixels -> tilted screen pixels."""
    MAX_DEG = 38.0

    def __init__(self, W, H, amount=.6, cy_frac=.56, dist=1.7):
        self.W, self.H, self.amount = W, H, amount
        self.th = math.radians(self.MAX_DEG * amount)
        self.d = dist * H
        self.cx, self.cy = W / 2, cy_frac * H
        s, c, d, cx, cy = math.sin(self.th), math.cos(self.th), self.d, self.cx, self.cy
        Hh = np.array([[d, -cx * s, cx * d], [0, d * c - cy * s, cy * d], [0, -s, d]], np.float64)
        self.H3 = Hh @ np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1]], np.float64)

    def scale_at(self, sy):
        """horizontal scale factor (vs. screen centre) at screen row sy; <1 = receding."""
        return 1 + (np.asarray(sy) - self.cy) * math.tan(self.th) / self.d

    def project(self, pts):
        p = np.asarray(pts, np.float64).reshape(-1, 2)
        q = np.c_[p, np.ones(len(p))] @ self.H3.T
        return q[:, :2] / q[:, 2:3]

    def haze_rows(self, strength=.6):
        sy = np.arange(self.H, dtype=np.float32)
        k = self.scale_at(sy); ktop = float(self.scale_at(0))
        if ktop >= .999: return np.zeros(self.H, np.float32)
        return (np.clip((1 - k) / (1 - ktop), 0, 1) ** 1.25 * strength).astype(np.float32)


HAZE = np.array([176, 192, 190], np.float32)


def tilt(frame_rgb, amount=.6, cy_frac=.56, haze=True, haze_strength=.55):
    """2.5D tilt of an already-flat map frame (top recedes) + atmospheric haze toward the top.
    Draw routes/labels on the flat frame BEFORE this, or use tilt_points() to place them afterwards.
    NB: the frame's own borders become visible when tilted; render it oversized, or use View.render_base() instead."""
    h, w = frame_rgb.shape[:2]
    T = Tilt(w, h, amount, cy_frac)
    out = cv2.warpPerspective(frame_rgb, T.H3, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    if haze:
        out = apply_haze(out, T, haze_strength)
    return out


def tilt_points(pts, size, amount=.6, cy_frac=.56):
    """Project flat-frame pixel points (N,2) through the same tilt as tilt(). size=(W,H)."""
    return Tilt(size[0], size[1], amount, cy_frac).project(pts)


def apply_haze(img, T, strength=.55):
    a = T.haze_rows(strength)
    n = int((a > 0.002).sum())
    if n == 0: return img
    top = img[:n].astype(np.float32)
    # depth-of-field: cheap blur that fades in with distance
    small = cv2.resize(top, (max(img.shape[1] // 3, 1), max(n // 3, 1)), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), 2.2)
    blur = cv2.resize(small, (img.shape[1], n), interpolation=cv2.INTER_LINEAR)
    aa = a[:n, None, None]
    top = top * (1 - aa * 0.9) + blur * (aa * 0.9)
    top = top * (1 - aa) + HAZE * aa
    img = img.copy(); img[:n] = np.clip(top, 0, 255).astype(np.uint8)
    return img


# ====================================================================== camera over a region
class View:
    def __init__(self, region, lat, lon, vis=6.0, tilt=.6, W=1080, H=1920, cy_frac=.56, yaw=0.0):
        self.R, self.W, self.H = region, W, H
        self.x0, self.y0 = [float(v) for v in region.wpx(lat, lon)]
        self.sc = H / (vis * region.S0)       # screen px per world px at screen centre
        self.T = Tilt(W, H, tilt, cy_frac)
        cs, sn = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        sc = self.sc
        self.Flat = np.array([[sc * cs, -sc * sn, self.T.cx - sc * (cs * self.x0 - sn * self.y0)],
                              [sc * sn, sc * cs, self.T.cy - sc * (sn * self.x0 + cs * self.y0)], [0, 0, 1]], np.float64)
        self.M = self.T.H3 @ self.Flat
        self.Minv = np.linalg.inv(self.M)

    def project(self, wpts):
        p = np.asarray(wpts, np.float64).reshape(-1, 2)
        q = np.c_[p, np.ones(len(p))] @ self.M.T
        return q[:, :2] / q[:, 2:3]

    def project_latlon(self, lat, lon):
        x, y = self.R.wpx(lat, lon)
        return self.project(np.c_[np.atleast_1d(x), np.atleast_1d(y)])

    def scale_at(self, sy):  # screen px per world px (horizontal) at a screen row
        return self.sc * self.T.scale_at(sy)

    def _level(self):
        top = self.sc * float(self.T.scale_at(0)); lvl = int(max(0, min(len(self.R.img) - 1, math.floor(-math.log2(max(top, 1e-3)) + .55))))
        return lvl

    def render_base(self):
        L = self._level(); k = 2.0 ** -L
        M = np.diag([k, k, 1]) @ np.eye(3)  # world -> level px
        ML = self.M @ np.linalg.inv(M)      # level px -> screen
        img = cv2.warpPerspective(self.R.img[L], ML, (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        mask = cv2.warpPerspective(self.R.mask[L], ML, (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return img, mask

    def world_coords(self, ds=2):
        """world px for every ds-th screen pixel (for sampling map-space noise)."""
        w, h = self.W // ds, self.H // ds
        u, v = np.meshgrid((np.arange(w, dtype=np.float64) + .5) * ds, (np.arange(h, dtype=np.float64) + .5) * ds)
        q = np.stack([u, v, np.ones_like(u)], -1) @ self.Minv.T
        return (q[..., 0] / q[..., 2]).astype(np.float32), (q[..., 1] / q[..., 2]).astype(np.float32)


# ====================================================================== animated textures (map-space)
_NOISE = {}


def tile_noise(n=256, sigma=3.0, seed=1):
    key = (n, sigma, seed)
    if key not in _NOISE:
        r = np.random.default_rng(seed).random((n, n)).astype(np.float32)
        r3 = np.tile(r, (3, 3)); r3 = cv2.GaussianBlur(r3, (0, 0), sigma)[n:2 * n, n:2 * n]
        lo, hi = np.percentile(r3, [2, 98]); _NOISE[key] = np.clip((r3 - lo) / (hi - lo), 0, 1).astype(np.float32)
    return _NOISE[key]


def sample_noise(tex, wx, wy, texel, ox=0.0, oy=0.0):
    n = tex.shape[0]
    mx = ((wx + ox) / texel) % n; my = ((wy + oy) / texel) % n
    return cv2.remap(tex, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)


def _up(a, W, H): return cv2.resize(a, (W, H), interpolation=cv2.INTER_LINEAR)


def water_shimmer(img, mask, view, t, wc=None, strength=1.0):
    """Scrolling-noise brightness modulation + sparse sun glints on sea pixels (cheap, half-res noise)."""
    wx, wy = wc or view.world_coords(2)
    n1 = sample_noise(tile_noise(256, 1.4, 1), wx, wy, 2.4, t * 9, t * 3)
    n2 = sample_noise(tile_noise(256, 1.9, 2), wx, wy, 3.6, -t * 6, t * 8)
    broad = sample_noise(tile_noise(256, 9, 3), wx, wy, 14, t * 3, 0)
    s = n1 * n2
    glint = np.clip((s - .52) * 5.0, 0, 1) ** 1.5
    gain = 1 + (n1 - .5) * .16 * strength + (n2 - .5) * .10 + (broad - .5) * .16
    H, W = img.shape[:2]
    sea = 1 - mask.astype(np.float32) / 255
    sea = cv2.GaussianBlur(sea, (0, 0), 1.2)
    g = _up(gain, W, H); gl = _up(glint, W, H)
    k = (sea * strength)[..., None]
    f = img.astype(np.float32)
    f = f * (1 + (g - 1)[..., None] * k)
    f += (gl[..., None] * k) * np.array([54, 76, 74], np.float32)
    return f


def cloud_shadows(f, mask, view, t, wc=None, strength=.34):
    """Soft drifting cloud shadows over land (f: float32 image)."""
    wx, wy = wc or view.world_coords(2)
    a = sample_noise(tile_noise(256, 12, 7), wx, wy, 22, t * 14, t * 5)
    b = sample_noise(tile_noise(256, 5, 8), wx, wy, 9, t * 18, t * 7)
    c = smoothstep(.48, .78, a * .8 + b * .2)
    H, W = f.shape[:2]
    land = cv2.GaussianBlur(mask.astype(np.float32) / 255, (0, 0), 3)
    k = (_up(c, W, H) * land * strength)[..., None]
    return f * (1 - k) + np.array([20, 40, 70], np.float32) * k * .35 - 0 * k


# ====================================================================== sprites: icons + labels
def _font(path, size): return ImageFont.truetype(path, size)


def make_icon(kind, size=132):
    """Pin badge (dark disc, gold rim, cream glyph). Anchor = bottom tip. Returns RGBA uint8 (size, size*1.28)."""
    S = 4; w = size * S; h = int(size * 1.3) * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy, r = w / 2, w * .46, w * .43
    # pointer
    d.polygon([(cx - r * .32, cy + r * .86), (cx + r * .32, cy + r * .86), (cx, h - 4 * S)], fill=(232, 186, 90, 255))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(232, 186, 90, 255))
    d.ellipse([cx - r * .9, cy - r * .9, cx + r * .9, cy + r * .9], fill=(34, 27, 22, 255))
    d.ellipse([cx - r * .82, cy - r * .82, cx + r * .82, cy + r * .82], fill=(50, 40, 32, 255))
    cream = (247, 233, 200, 255); gold = (240, 196, 98, 255); u = r / 100.0
    X = lambda v: cx + v * u
    Y = lambda v: cy + v * u
    if kind == "tent":
        d.polygon([(X(-58), Y(40)), (X(0), Y(-48)), (X(58), Y(40))], fill=cream)
        d.polygon([(X(-12), Y(40)), (X(0), Y(-8)), (X(12), Y(40))], fill=(50, 40, 32, 255))
        d.line([(X(0), Y(-48)), (X(0), Y(-64))], fill=gold, width=int(4 * u))
        d.polygon([(X(0), Y(-64)), (X(22), Y(-58)), (X(0), Y(-52))], fill=gold)
        d.line([(X(-70), Y(44)), (X(70), Y(44))], fill=gold, width=int(5 * u))
    elif kind == "walls":
        for x0 in (-62, 36):
            d.rectangle([X(x0), Y(-30), X(x0 + 26), Y(44)], fill=cream)
            for k in range(3): d.rectangle([X(x0 + k * 10 - 1), Y(-46), X(x0 + k * 10 + 6), Y(-30)], fill=cream)
        d.rectangle([X(-38), Y(-6), X(38), Y(44)], fill=cream)
        for k in range(5): d.rectangle([X(-38 + k * 17), Y(-20), X(-38 + k * 17 + 10), Y(-6)], fill=cream)
        d.pieslice([X(-17), Y(8), X(17), Y(60)], 180, 360, fill=(50, 40, 32, 255)); d.rectangle([X(-17), Y(34), X(17), Y(44)], fill=(50, 40, 32, 255))
        d.line([(X(-70), Y(46)), (X(70), Y(46))], fill=gold, width=int(5 * u))
    elif kind == "peak":
        d.polygon([(X(-66), Y(46)), (X(-14), Y(-44)), (X(18), Y(6)), (X(34), Y(-20)), (X(70), Y(46))], fill=cream)
        d.polygon([(X(-14), Y(-44)), (X(-30), Y(-14)), (X(-20), Y(-20)), (X(-12), Y(-8)), (X(-2), Y(-22)), (X(6), Y(-12)) ], fill=(120, 176, 190, 255))
        d.polygon([(X(-14), Y(-44)), (X(-14), Y(46)), (X(-66), Y(46))], fill=(206, 190, 158, 255))
        d.polygon([(X(-14), Y(-44)), (X(-30), Y(-14)), (X(-20), Y(-20)), (X(-12), Y(-8)), (X(-2), Y(-22)), (X(6), Y(-12))], fill=(255, 255, 255, 255))
        d.line([(X(-70), Y(48)), (X(72), Y(48))], fill=gold, width=int(5 * u))
    elif kind == "temple":
        d.polygon([(X(-62), Y(-14)), (X(0), Y(-52)), (X(62), Y(-14))], fill=cream)
        d.rectangle([X(-56), Y(-10), X(56), Y(-2)], fill=cream)
        for k in range(4): d.rectangle([X(-48 + k * 31), Y(2), X(-36 + k * 31), Y(38)], fill=cream)
        d.rectangle([X(-62), Y(40), X(62), Y(50)], fill=cream)
        d.ellipse([X(-6), Y(-34), X(6), Y(-22)], fill=gold)
    elif kind == "waves":
        for j, yy in enumerate((-30, -2, 26)):
            pts = [(X(-62 + k * 4), Y(yy + 11 * math.sin(k / 3.2 + j))) for k in range(32)]
            d.line(pts, fill=cream if j != 1 else gold, width=int(9 * u), joint="curve")
    im = im.resize((w // S, h // S), Image.LANCZOS)
    return np.asarray(im)


def make_label(text, size=44, color=(250, 240, 214), stroke=(30, 22, 16), spacing=2, font=FONT_SERIF, sub=None, subsize=None, shadow=True):
    f = _font(font, size)
    def width(t):
        return sum(f.getlength(ch) + spacing for ch in t) - spacing
    pad = 14
    subsize = subsize or int(size * .5); fs = _font(FONT_SANS, subsize)
    sw = (sum(fs.getlength(ch) + 2 for ch in sub) if sub else 0)
    W = int(max(width(text), sw)) + pad * 2 + 10; Hh = size + (subsize + 10 if sub else 0) + pad * 2 + 10
    im = Image.new("RGBA", (W, Hh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    def put(t, fo, y, col, sp, sk):
        tw = sum(fo.getlength(ch) + sp for ch in t) - sp; x = (W - tw) / 2
        for ch in t:
            d.text((x, y), ch, font=fo, fill=col, stroke_width=sk, stroke_fill=stroke + (255,)); x += fo.getlength(ch) + sp
    if shadow:
        sh = Image.new("RGBA", (W, Hh), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
        x = (W - width(text)) / 2
        for ch in text:
            sd.text((x, pad + 4), ch, font=f, fill=(0, 0, 0, 170), stroke_width=4, stroke_fill=(0, 0, 0, 170)); x += f.getlength(ch) + spacing
        sh = sh.filter(ImageFilter.GaussianBlur(5)); im.alpha_composite(sh)
    put(text, f, pad, color + (255,), spacing, max(2, size // 14))
    if sub: put(sub, fs, pad + size + 8, (236, 214, 150), 2, 2)
    return np.asarray(im)


def blit(frame, spr, cx, cy, scale=1.0, alpha=1.0, anchor=(.5, .5)):
    """Alpha-blend an RGBA sprite onto uint8 frame, anchored at (cx,cy); anchor given as fraction of sprite size."""
    if alpha <= 0.003 or scale <= 0.01: return
    h0, w0 = spr.shape[:2]
    w, h = max(int(w0 * scale), 1), max(int(h0 * scale), 1)
    s = cv2.resize(spr, (w, h), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    x0 = int(round(cx - anchor[0] * w)); y0 = int(round(cy - anchor[1] * h))
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, frame.shape[1]), min(y0 + h, frame.shape[0])
    if X0 >= X1 or Y0 >= Y1: return
    s = s[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
    a = (s[..., 3:4].astype(np.float32) / 255) * alpha
    roi = frame[Y0:Y1, X0:X1].astype(np.float32)
    frame[Y0:Y1, X0:X1] = (roi * (1 - a) + s[..., :3].astype(np.float32) * a).astype(np.uint8)


class Marker:
    """Pin icon + label. Pops in (overshoot) at t0; label fades/slides in shortly after."""
    _icons = {}

    def __init__(self, region, lat, lon, kind, text, t0, sub=None, label_side="below", size=1.0):
        self.x, self.y = [float(v) for v in region.wpx(lat, lon)]
        self.kind, self.t0, self.size, self.side = kind, t0, size, label_side
        if kind not in Marker._icons: Marker._icons[kind] = make_icon(kind)
        self.icon = Marker._icons[kind]
        self.label = make_label(text, 40, sub=sub) if text else None

    def draw(self, frame, view, t, glow=None):
        dt = t - self.t0
        if dt < 0: return
        sx, sy = view.project([[self.x, self.y]])[0]
        k = float(view.T.scale_at(sy)) ** .6
        base = .62 * k * self.size
        e = ease_out_back(dt / .5)
        a = min(1.0, dt / .14)
        # ground ring pulse in map space (projected ellipse)
        if glow is not None and dt < 1.0:
            rr = (14 + 90 * ease_io(dt / 1.0)) ; ang = np.linspace(0, 2 * math.pi, 40)
            ring = view.project(np.c_[self.x + rr * np.cos(ang), self.y + rr * np.sin(ang)]).astype(np.int32)
            cv2.polylines(glow, [ring.reshape(-1, 1, 2)], True, (int(255 * (1 - dt)), int(210 * (1 - dt)), int(120 * (1 - dt))), 3, cv2.LINE_AA)
        # ground shadow
        cv2.ellipse(frame, (int(sx), int(sy)), (int(12 * base * min(e, 1)), int(4 * base * min(e, 1))), 0, 0, 360, (84, 70, 50), -1, cv2.LINE_AA) if dt > .05 else None
        blit(frame, self.icon, sx, sy, base * e, a, anchor=(.5, 1.0))
        if self.label is not None:
            ld = dt - .22
            if ld > 0:
                la = ease_io(ld / .35); slide = (1 - la) * 14 * k
                ih = self.icon.shape[0] * base
                sc_ = .72 * k * self.size; lw, lh = self.label.shape[1] * sc_, self.label.shape[0] * sc_
                if self.side == "below": blit(frame, self.label, sx, sy + 4 + lh * .5 + slide * -1, sc_, la)
                elif self.side == "above": blit(frame, self.label, sx, sy - ih - 2 - lh * .5 + slide, sc_, la)
                elif self.side == "left": blit(frame, self.label, sx - 26 * base * 1.0 - lw * .5 + slide, sy - ih * .42, sc_, la)
                else: blit(frame, self.label, sx + 26 * base * 1.0 + lw * .5 - slide, sy - ih * .42, sc_, la)


class RegionLabel:
    """Big, spaced-out atlas lettering (billboard). tone 'land' = dark ink, 'sea' = cream."""
    def __init__(self, region, lat, lon, text, size=46, tone="land", t0=0.0, alpha=.7, spacing=10):
        self.x, self.y = [float(v) for v in region.wpx(lat, lon)]
        col, st = ((92, 66, 40), (232, 218, 176)) if tone == "land" else ((214, 234, 232), (14, 44, 58))
        self.spr = make_label(text, size, color=col, stroke=st, spacing=spacing, shadow=False)
        self.t0, self.alpha = t0, alpha

    def draw(self, frame, view, t):
        dt = t - self.t0
        if dt < 0: return
        sx, sy = view.project([[self.x, self.y]])[0]
        k = float(view.T.scale_at(sy)) * (view.sc / .85) ** .55
        half = self.spr.shape[1] * k * .8 / 2
        edge = float(np.clip((min(sx - half, view.W - sx - half) + 10) / 50, 0, 1))
        blit(frame, self.spr, sx, sy, k * .8, self.alpha * ease_io(dt / .8) * float(np.clip(1.6 - k * .6, .15, 1)) * edge)


# ====================================================================== route trail
def catmull(pts, n=24, alpha=.5):
    P = np.asarray(pts, np.float64)
    if len(P) < 3: return P
    P = np.vstack([P[0] * 2 - P[1], P, P[-1] * 2 - P[-2]]); out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t0 = 0; t1 = t0 + np.linalg.norm(p1 - p0) ** alpha + 1e-6; t2 = t1 + np.linalg.norm(p2 - p1) ** alpha + 1e-6; t3 = t2 + np.linalg.norm(p3 - p2) ** alpha + 1e-6
        for t in np.linspace(t1, t2, n, endpoint=False):
            A1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1; A2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            A3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            B1 = (t2 - t) / (t2 - t0) * A1 + (t - t0) / (t2 - t0) * A2; B2 = (t3 - t) / (t3 - t1) * A2 + (t - t1) / (t3 - t1) * A3
            out.append((t2 - t) / (t2 - t1) * B1 + (t - t1) / (t2 - t1) * B2)
    out.append(P[-2]); return np.array(out)


class Route:
    def __init__(self, region, waypoints, smooth=True, sea_zones=(), color=(255, 150, 48)):
        self.R = region; self.color = color
        wp = np.array([[float(region.wpx(la, lo)[0]), float(region.wpx(la, lo)[1])] for la, lo in waypoints])
        self.pts = catmull(wp) if smooth else wp
        seg = np.linalg.norm(np.diff(self.pts, axis=0), axis=1)
        self.cum = np.r_[0, np.cumsum(seg)]; self.total = self.cum[-1]
        self.wp_s = [float(self.cum[np.argmin(np.linalg.norm(self.pts - w, axis=1))]) for w in wp]
        self.sea = region.is_land(self.pts[:, 0], self.pts[:, 1]) == False
        for wi, rad in sea_zones:
            c = self.wp_s[wi]; self.sea |= np.abs(self.cum - c) < rad

    def at(self, s):
        s = min(max(s, 0), self.total)
        i = min(int(np.searchsorted(self.cum, s, side="right")) - 1, len(self.pts) - 2)
        f = (s - self.cum[i]) / max(self.cum[i + 1] - self.cum[i], 1e-6)
        return self.pts[i] * (1 - f) + self.pts[i + 1] * f, i

    def draw(self, frame, view, s_head, t, glow):
        """frame: uint8 RGB drawn in place; glow: uint8 additive layer (half-res handled by caller: pass full-res, blurred later)."""
        if s_head <= 0: return
        H, W = frame.shape[:2]
        m = np.searchsorted(self.cum, s_head, side="right")
        head, hi = self.at(s_head)
        P = np.vstack([self.pts[:m], head]); S = np.r_[self.cum[:m], s_head]
        sp = view.project(P)
        wscale = view.scale_at(sp[:, 1]) / view.sc  # perspective factor along the path
        base_w = 8.0 * view.sc ** .3
        casing = np.zeros((H, W), np.uint8); body = np.zeros((H, W, 3), np.uint8); ba = np.zeros((H, W), np.uint8)
        # dark casing + coloured body with travelling pulse
        col = np.array(self.color, np.float32)
        step = max(1, len(sp) // 400)
        for i in range(0, len(sp) - 1, step):
            j = min(i + step, len(sp) - 1)
            w = base_w * float(wscale[i]) * 1.25
            a, b = tuple(int(round(v * 16)) for v in sp[i]), tuple(int(round(v * 16)) for v in sp[j])
            cv2.line(casing, a, b, 255, int(round(w + 5)), cv2.LINE_AA, 4)
            pulse = .78 + .22 * math.sin(S[i] * .06 - t * 9)
            c = tuple(int(min(255, v * pulse)) for v in col)
            cv2.line(body, a, b, c, int(round(w)), cv2.LINE_AA, 4)
            cv2.line(ba, a, b, 255, int(round(w)), cv2.LINE_AA, 4)
            cv2.line(glow, a, b, tuple(int(v * .30) for v in col), int(round(w * 2.4)), cv2.LINE_AA, 4)
        casing = cv2.GaussianBlur(casing, (0, 0), 1.4)
        # hot core
        core = np.zeros((H, W), np.uint8)
        for i in range(0, len(sp) - 1, step):
            j = min(i + step, len(sp) - 1)
            w = base_w * float(wscale[i]) * .42
            cv2.line(core, tuple(int(round(v * 16)) for v in sp[i]), tuple(int(round(v * 16)) for v in sp[j]), 255, max(int(round(w)), 1), cv2.LINE_AA, 4)
        ys, xs = np.nonzero(casing[:, :] > 0)
        if len(ys):
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            f = frame[y0:y1, x0:x1].astype(np.float32)
            cs = casing[y0:y1, x0:x1, None].astype(np.float32) / 255
            f = f * (1 - cs * .62)
            bal = ba[y0:y1, x0:x1, None].astype(np.float32) / 255
            f = f * (1 - bal) + body[y0:y1, x0:x1].astype(np.float32) * bal
            cr = core[y0:y1, x0:x1, None].astype(np.float32) / 255
            f = f * (1 - cr * .8) + np.array([255, 244, 214], np.float32) * cr * .8
            frame[y0:y1, x0:x1] = np.clip(f, 0, 255).astype(np.uint8)
        # light particles drifting along the drawn path
        npart = max(3, int(s_head / 38))
        sc_ = view.sc
        for k in range(npart):
            sk = (k * 38 + t * 70) % max(s_head, 1)
            if sk > s_head - 1: continue
            p, _ = self.at(sk); q = view.project([p])[0]; ps = float(view.scale_at(q[1]) / view.sc)
            tw = .5 + .5 * math.sin(t * 7 + k * 1.7)
            r = (2.2 + 1.6 * tw) * ps * sc_ ** .3
            cv2.circle(glow, (int(q[0]), int(q[1])), int(r * 3.4), (int(150 * tw + 40), int(130 * tw + 30), int(60 * tw)), -1, cv2.LINE_AA)
            cv2.circle(frame, (int(q[0] * 16), int(q[1] * 16)), int(max(r, 1.2) * 16), (255, 252, 236), -1, cv2.LINE_AA, 4)
        # footprints on land, wake on sea
        sp_step = 26
        for sk in np.arange(sp_step, s_head, sp_step):
            idx = min(int(np.searchsorted(self.cum, sk)), len(self.pts) - 2)
            if self.sea[idx]: continue
            p, i2 = self.at(sk); p2, _ = self.at(sk + 3)
            q = view.project([p, p2]); d = q[1] - q[0]; n = np.linalg.norm(d)
            if n < 1e-6: continue
            d /= n; perp = np.array([-d[1], d[0]]); ps = float(view.scale_at(q[0][1]) / view.sc)
            side = 1 if int(sk / sp_step) % 2 else -1
            c = q[0] + perp * side * (base_w * ps * 1.6 + 8 * ps)
            age = s_head - sk; al = float(min(1, (age) / 30)) * (1 if age < 700 else .55)
            ang = math.degrees(math.atan2(d[1], d[0]))
            cv2.ellipse(frame, (int(c[0]), int(c[1])), (max(int(5 * ps * view.sc ** .3), 1), max(int(2.6 * ps * view.sc ** .3), 1)), ang, 0, 360,
                        (250, 242, 220), -1, cv2.LINE_AA)
        # wake (when head is at sea)
        if self.sea[min(hi, len(self.sea) - 1)]:
            for j in range(1, 9):
                p, _ = self.at(s_head - j * 7); q = view.project([p])[0]; p2, _ = self.at(s_head - j * 7 + 2); q2 = view.project([p2])[0]
                d = q2 - q; n = np.linalg.norm(d) + 1e-6; d /= n; perp = np.array([-d[1], d[0]]); ps = float(view.scale_at(q[1]) / view.sc)
                off = (3 + j * 2.6) * ps * view.sc ** .5; a = (1 - j / 9.0)
                for sgn in (-1, 1):
                    pp = q + perp * sgn * off
                    cv2.circle(glow, (int(pp[0]), int(pp[1])), max(int(2.2 * ps), 1), (int(200 * a), int(230 * a), int(235 * a)), -1, cv2.LINE_AA)
        # bright head
        hq = view.project([head])[0]; hp = float(view.scale_at(hq[1]) / view.sc); pulse = .5 + .5 * math.sin(t * 8)
        hr = (6.5 + 1.5 * pulse) * hp * view.sc ** .3
        cv2.circle(glow, (int(hq[0]), int(hq[1])), int(hr * 3.0), (96, 70, 30), -1, cv2.LINE_AA)
        cv2.circle(glow, (int(hq[0]), int(hq[1])), int(hr * 1.8), (150, 110, 60), -1, cv2.LINE_AA)
        cv2.circle(frame, (int(hq[0] * 16), int(hq[1] * 16)), int((hr + 2.5) * 16), (255, 122, 40), -1, cv2.LINE_AA, 4)
        cv2.circle(frame, (int(hq[0] * 16), int(hq[1] * 16)), int(hr * 16), (255, 250, 232), -1, cv2.LINE_AA, 4)
        ph = (t * 1.3) % 1.0
        cv2.circle(glow, (int(hq[0]), int(hq[1])), int((hr + 40 * ph) * 1.0), (int(160 * (1 - ph)), int(120 * (1 - ph)), int(50 * (1 - ph))), 2, cv2.LINE_AA)

    def draw_ahead(self, glow, view, s_head, t):
        """faint dotted preview of the path still to come."""
        for sk in np.arange(max(s_head, 0) + 10, self.total, 15):
            p, _ = self.at(sk); q = view.project([p])[0]; ps = float(view.scale_at(q[1]) / view.sc)
            cv2.circle(glow, (int(q[0]), int(q[1])), max(int(2.0 * ps * view.sc ** .3), 1), (88, 82, 70), -1, cv2.LINE_AA)


# ====================================================================== finishing
class Finish:
    def __init__(self, W, H, seed=3):
        y = np.linspace(-1, 1, H, dtype=np.float32)[:, None]; x = np.linspace(-1, 1, W, dtype=np.float32)[None, :]
        r2 = x ** 2 * .9 + (y * .75) ** 2 * 1.0
        self.vig = (1 - np.clip((r2 - .22) / 1.05, 0, 1) ** 1.35 * .40)[..., None].astype(np.float32)
        self.vig *= (1 - np.clip((-y - .55) / .45, 0, 1)[..., None] ** 1.5 * .30).astype(np.float32)   # top falloff
        rng = np.random.default_rng(seed)
        self.grain = [cv2.resize(rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR) for _ in range(6)]
        self.W, self.H = W, H

    def __call__(self, frame, t, fi=0, grain=5.5):
        f = frame.astype(np.float32)
        # gentle grade: warm highlights, teal shadows, mild S-curve
        f = f / 255
        f = f + (f - .5) * (1 - np.abs(f - .5) * 2) * .16
        f = f * 1.05 * np.array([1.03, 1.0, .965], np.float32) + np.array([-.006, .004, .012], np.float32) * (1 - f)
        f *= self.vig
        f = f * 255 + self.grain[fi % 6][..., None] * grain
        return np.clip(f, 0, 255).astype(np.uint8)
