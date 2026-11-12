"""MythUnearthed avatar (800x800) and banner (2560x1440) in the map style."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
A = Path("assets"); O = Path("brand"); O.mkdir(exist_ok=True)
base = Image.open(A / "paul_base.png").convert("RGB")
F = lambda n, s: ImageFont.truetype(str(A / n), s)
GOLD, CREAM, INK = (232, 170, 40), (246, 236, 210), (12, 10, 8)
BW, BH = base.size
S0, LON0, LAT1 = 280, 16.0, 48.5
import math
KX = math.cos(math.radians(36.5))
def crop(lat, lon, hdeg, w, h):
    ch = hdeg * S0; cw = ch * w / h
    cx, cy = (lon - LON0) * KX * S0, (LAT1 - lat) * S0
    return base.resize((w, h), Image.LANCZOS, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))

# --- banner: safe area for all devices is the centre 1546x423
b = crop(37.2, 28.5, 8.5, 2560, 1440).convert("RGBA")
shade = Image.new("RGBA", b.size, (8, 12, 16, 0)); d = ImageDraw.Draw(shade)
d.rectangle([0, 470, 2560, 970], fill=(8, 12, 16, 175))
b.alpha_composite(shade.filter(ImageFilter.GaussianBlur(60)))
d = ImageDraw.Draw(b)
d.text((1280, 650), "MYTH UNEARTHED", font=F("serif-bold.ttf", 170), fill=CREAM, anchor="mm", stroke_width=6, stroke_fill=INK)
d.text((1280, 800), "BIBLE HISTORY, MAPPED", font=F("sans-black.ttf", 64), fill=GOLD, anchor="mm", stroke_width=4, stroke_fill=INK)
b.convert("RGB").save(O / "banner_2560x1440.png")

# --- avatar: compass seal on parchment
av = crop(37.8, 26.5, 3.2, 800, 800).convert("RGBA")
m = Image.new("L", (800, 800), 0); md = ImageDraw.Draw(m); md.ellipse([0, 0, 800, 800], fill=255)
dark = Image.new("RGBA", (800, 800), (10, 14, 18, 150)); av.alpha_composite(dark)
d = ImageDraw.Draw(av)
d.ellipse([40, 40, 760, 760], outline=GOLD, width=14)
d.ellipse([78, 78, 722, 722], outline=CREAM + (160,), width=4)
cx = cy = 400
for ang, ln, wd in [(0, 300, 46), (90, 300, 46), (180, 300, 46), (270, 300, 46), (45, 180, 30), (135, 180, 30), (225, 180, 30), (315, 180, 30)]:
    r = math.radians(ang - 90)
    tip = (cx + math.cos(r) * ln, cy + math.sin(r) * ln)
    l = (cx + math.cos(r + math.pi / 2) * wd, cy + math.sin(r + math.pi / 2) * wd)
    rr = (cx + math.cos(r - math.pi / 2) * wd, cy + math.sin(r - math.pi / 2) * wd)
    d.polygon([tip, l, (cx, cy)], fill=GOLD if ln == 300 else CREAM)
    d.polygon([tip, rr, (cx, cy)], fill=(160, 110, 20) if ln == 300 else (190, 180, 150))
d.ellipse([cx - 58, cy - 58, cx + 58, cy + 58], fill=(10, 14, 18), outline=GOLD, width=8)
d.text((cx, cy + 2), "MU", font=F("serif-bold.ttf", 64), fill=CREAM, anchor="mm")
out = Image.new("RGBA", (800, 800), (0, 0, 0, 0)); out.paste(av, (0, 0), m)
out.save(O / "avatar_800.png")
print("ok")
