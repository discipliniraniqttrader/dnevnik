"""EVENT shots dispatcher -> uint8 RGB array (H, W, 3)."""
import numpy as np
from PIL import Image
from . import ev_noah as EN, ev_exodus as EX, ev_new as NW, objects as OB, text as TX


def _arr(x):
    return np.asarray(x.convert("RGB")) if isinstance(x, Image.Image) else x


def render(c):
    b = c.b; n = b["scene_name"]; lt, dur, t = c.lt, c.dur, c.t
    if n == "aerial":
        if c.sub == 0 and c.nsub > 1: z, f, ring, q = (1.0, 1.3), (0.52, 0.5), .5, None
        elif c.nsub == 1: z, f, ring, q = (1.0, 2.2), (0.52 + .2 * min(1, lt / max(dur, .1)), 0.5 + .2 * min(1, lt / max(dur, .1))), .5, .6 * dur
        else: z, f, ring, q = (2.0, 2.5), (880 / 1620, 1500 / 2880), 0.0, .35
        return _arr(EN.aerial_scene(c.slt if c.nsub > 1 else lt, c.sdur if c.nsub > 1 else dur, t, z, f, q, ring, b.get("label") or "AERIAL SURVEY"))
    if n == "tablet":
        return _arr(EN.tablet_scene(lt, dur, t, .3, c.tm["zoom_at"], c.tm["glow_at"], b.get("label", "")))
    if n == "birds":
        return _arr(EN.birds_scene(lt, t, c.tm["rel"]))
    if n == "counter":
        return _arr(EX.counter_scene(lt, dur, t, int(b["number"]), b.get("label") or b.get("unit") or ""))
    if n == "icon_grid":
        return _arr(NW.icon_grid_scene(lt, dur, t, b["icon"], b["count"], b.get("label", "")))
    if n == "object":
        return OB.object_scene(lt, dur, t, b["object"], c.sub, b.get("label", ""))
    if n == "split_compare":
        return _arr(NW.split_scene(lt, dur, t, b["left"], b["right"], c.sub))
    if n == "sea_parting":
        return _arr(EX.sea_top(lt, dur, t) if c.sub % 2 == 0 else EX.sea_corridor(lt, dur, t))
    if n == "mountain_storm":
        return _arr(EX.mountain_scene(lt, t, c.tm["flashes"]))
    if n == "fire_rain":
        return _arr(NW.fire_rain_scene(lt, dur, t))
    if n == "crowd":
        return _arr(NW.crowd_scene(lt, dur, t, b.get("label", "")))
    if n == "manna":
        return _arr(EX.manna_scene(lt, t))
    return _arr(OB.object_scene(lt, dur, t, "scroll", c.sub, b.get("label", "")))
