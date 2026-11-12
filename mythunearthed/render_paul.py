#!/usr/bin/env python3
"""Шорт 9:16: Трите мисионерски пътувания на апостол Павел (Деяния 13–21).

python3 render_paul.py bg|en [--frame SECONDS]   # --frame пише само един кадър (PNG) за преглед
"""
import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
A = HERE / "assets"
W, H, FPS, SS = 1080, 1920, 30, 2
LANG = sys.argv[1] if len(sys.argv) > 1 else "bg"

# ---------------------------------------------------------------- данни
CITIES = {  # lat, lon, BG, EN, етикет (dx, dy, anchor) или None = само точка
    "antioch":    (36.20, 36.16, "Антиохия", "Antioch", (10, 18, "ra")),
    "seleucia":   (36.12, 35.92, "Селевкия", "Seleucia", None),
    "salamis":    (35.18, 33.90, "Саламин", "Salamis", (14, 10, "lm")),
    "paphos":     (34.76, 32.41, "Пафос", "Paphos", (-14, 12, "rm")),
    "perga":      (36.96, 30.85, "Перге", "Perga", (10, 26, "lm")),
    "attalia":    (36.89, 30.70, "Аталия", "Attalia", None),
    "pisantioch": (38.31, 31.19, "Антиохия Писидийска", "Pisidian Antioch", (0, -26, "mm")),
    "iconium":    (37.87, 32.48, "Иконий", "Iconium", (14, -10, "lm")),
    "lystra":     (37.58, 32.45, "Листра", "Lystra", (-12, 14, "rm")),
    "derbe":      (37.35, 33.37, "Дерве", "Derbe", (0, 30, "mm")),
    "tarsus":     (36.92, 34.89, "Тарс", "Tarsus", (0, -24, "mm")),
    "troas":      (39.75, 26.16, "Троада", "Troas", (14, -6, "lm")),
    "samothrace": (40.48, 25.53, "Самотраки", "Samothrace", None),
    "neapolis":   (40.94, 24.41, "Неапол", "Neapolis", None),
    "philippi":   (41.01, 24.29, "Филипи", "Philippi", (12, -16, "lm")),
    "amphipolis": (40.82, 23.85, "Амфипол", "Amphipolis", None),
    "thessalonica": (40.64, 22.94, "Солун", "Thessalonica", (-12, -14, "rm")),
    "berea":      (40.52, 22.20, "Берия", "Berea", (-12, 12, "rm")),
    "athens":     (37.98, 23.73, "Атина", "Athens", (12, 14, "lm")),
    "corinth":    (37.91, 22.88, "Коринт", "Corinth", (-12, 14, "rm")),
    "cenchreae":  (37.88, 22.99, "Кенхрея", "Cenchreae", None),
    "ephesus":    (37.94, 27.34, "Ефес", "Ephesus", (14, -4, "lm")),
    "caesarea":   (32.50, 34.89, "Кесария", "Caesarea", (-14, 0, "rm")),
    "jerusalem":  (31.78, 35.23, "Йерусалим", "Jerusalem", (14, 8, "lm")),
    "assos":      (39.49, 26.34, "Асос", "Assos", None),
    "mitylene":   (39.11, 26.56, "Митилина", "Mitylene", None),
    "chios":      (38.37, 26.14, "Хиос", "Chios", None),
    "samos":      (37.69, 26.94, "Самос", "Samos", None),
    "miletus":    (37.53, 27.28, "Милит", "Miletus", (12, 10, "lm")),
    "cos":        (36.89, 27.29, "Кос", "Cos", None),
    "rhodes":     (36.43, 28.22, "Родос", "Rhodes", (-10, 18, "rm")),
    "patara":     (36.26, 29.32, "Патара", "Patara", None),
    "tyre":       (33.27, 35.20, "Тир", "Tyre", (14, 0, "lm")),
    "ptolemais":  (32.93, 35.08, "Птолемаида", "Ptolemais", None),
}
JOURNEYS = [
    {"color": (242, 193, 78), "years": "ок. 46–48 г.", "years_en": "c. AD 46–48", "ref": "Деяния 13–14", "ref_en": "Acts 13–14",
     "route": ["antioch", "seleucia", "salamis", "paphos", "perga", "pisantioch", "iconium", "lystra", "derbe",
               "lystra", "iconium", "pisantioch", "perga", "attalia", "antioch"]},
    {"color": (110, 198, 255), "years": "ок. 49–52 г.", "years_en": "c. AD 49–52", "ref": "Деяния 15–18", "ref_en": "Acts 15–18",
     "route": ["antioch", "tarsus", "derbe", "lystra", "iconium", "pisantioch", "troas", "samothrace", "neapolis",
               "philippi", "amphipolis", "thessalonica", "berea", "athens", "corinth", "cenchreae", "ephesus",
               "caesarea", "jerusalem", "antioch"]},
    {"color": (255, 138, 101), "years": "ок. 53–57 г.", "years_en": "c. AD 53–57", "ref": "Деяния 18–21", "ref_en": "Acts 18–21",
     "route": ["antioch", "tarsus", "derbe", "lystra", "iconium", "pisantioch", "ephesus", "troas", "philippi",
               "corinth", "philippi", "troas", "assos", "mitylene", "chios", "samos", "miletus", "cos", "rhodes",
               "patara", "tyre", "ptolemais", "caesarea", "jerusalem"]},
]
T = {
    "bg": {"title": "Пътуванията\nна апостол Павел", "sub": "3 мисии · Деяния 13–21", "n": ["1-во пътуване", "2-ро пътуване", "3-то пътуване"],
           "km": "км по права линия", "total": "Общо", "cta": "Коя карта да направим следващата?", "note": "Част от маршрута е приблизителна"},
    "en": {"title": "The Journeys\nof Paul", "sub": "3 missions · Acts 13–21", "n": ["First journey", "Second journey", "Third journey"],
           "km": "km as the crow flies", "total": "Total", "cta": "Which map should we make next?", "note": "Parts of the route are approximate"},
}[LANG]

# ---------------------------------------------------------------- проекция
LON0, LON1, LAT0, LAT1 = 20.6, 37.4, 30.7, 42.3
MAP_TOP, MAP_H = 470, 1000
KX = math.cos(math.radians(36.5))
scale = min(W / ((LON1 - LON0) * KX), MAP_H / (LAT1 - LAT0))
offx = (W - (LON1 - LON0) * KX * scale) / 2


def proj(lat, lon, s=1):
    return ((offx + (lon - LON0) * KX * scale) * s, (MAP_TOP + (LAT1 - lat) * scale) * s)


def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


for j in JOURNEYS:
    pts = [CITIES[c] for c in j["route"]]
    j["seg"] = [hav(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    j["total"] = sum(j["seg"])

# ---------------------------------------------------------------- шрифтове
F = lambda name, size: ImageFont.truetype(str(A / name), size)
f_title, f_sub = F("serif-bold.ttf", 92), F("sans-semi.ttf", 38)
f_head, f_years = F("sans-black.ttf", 50), F("sans-semi.ttf", 34)
f_city, f_km, f_kml, f_note = F("sans-semi.ttf", 27), F("sans-black.ttf", 84), F("sans-semi.ttf", 30), F("sans-semi.ttf", 24)
CREAM, MUTED = (243, 233, 210), (170, 160, 138)


# ---------------------------------------------------------------- фон
def base_map():
    big = Image.new("RGB", (W * SS, H * SS))
    d = ImageDraw.Draw(big)
    for y in range(0, H * SS, 4):  # тъмно синьо море с вертикален преход
        k = y / (H * SS)
        d.rectangle([0, y, W * SS, y + 4], fill=(int(7 + 5 * k), int(16 + 8 * k), int(30 + 12 * k)))
    land = json.load(open(A / "med.json"))
    for poly in land:
        outer = [proj(lat, lon, SS) for lon, lat in poly[0]]
        d.polygon(outer, fill=(86, 74, 52), outline=(150, 130, 92), width=3)
        for hole in poly[1:]:
            d.polygon([proj(lat, lon, SS) for lon, lat in hole], fill=(9, 20, 36))
    img = big.resize((W, H), Image.LANCZOS)
    # затъмняване горе и долу за текста
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    for y in range(H):
        a = 0
        if y < MAP_TOP + 120: a = int(235 * max(0, 1 - (y - 120) / (MAP_TOP)))
        if y > MAP_TOP + MAP_H - 180: a = max(a, int(235 * min(1, (y - (MAP_TOP + MAP_H - 180)) / 260)))
        sd.line([(0, y), (W, y)], fill=min(235, a))
    dark = Image.new("RGB", (W, H), (8, 14, 24))
    return Image.composite(dark, img, shade)


BASE = base_map()


# ---------------------------------------------------------------- рисуване
def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def route_points(j, progress):
    """Точките на маршрута до даден напредък (0..1) по дължина."""
    pts = [CITIES[c] for c in j["route"]]
    target = progress * j["total"]
    out, done = [pts[0]], 0.0
    reached = [0]
    for i, seg in enumerate(j["seg"]):
        if done + seg <= target:
            out.append(pts[i + 1]); reached.append(i + 1); done += seg
        else:
            f = (target - done) / seg if seg else 0
            a, b = pts[i], pts[i + 1]
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            break
    return out, reached, min(target, j["total"])


def draw_route(layer, j, progress, alpha=255, width=7):
    pts, reached, km = route_points(j, progress)
    d = ImageDraw.Draw(layer)
    xy = [proj(p[0], p[1], SS) for p in pts]
    if len(xy) > 1:
        glow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).line(xy, fill=j["color"] + (int(alpha * .45),), width=width * SS * 3, joint="curve")
        layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6 * SS)))
        d.line(xy, fill=j["color"] + (alpha,), width=width * SS, joint="curve")
    return pts, reached, km


def text(d, xy, s, font, fill, anchor="la", stroke=0):
    d.text(xy, s, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(6, 10, 18))


def fmt(n):
    return f"{int(round(n)):,}".replace(",", " ")


DUR_INTRO, DUR_J, DUR_END = 2.6, 8.6, 5.0
TOTAL = DUR_INTRO + 3 * DUR_J + DUR_END


def frame(t):
    img = BASE.copy().convert("RGBA")
    big = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    labels = []  # градовете, които да се надпишат
    active = None
    for k, j in enumerate(JOURNEYS):
        t0 = DUR_INTRO + k * DUR_J
        if t < t0: break
        p = ease((t - t0) / (DUR_J - 1.4))
        cur = t < t0 + DUR_J
        faded = t >= TOTAL - DUR_END
        alpha = 255 if (cur or faded) else 110
        pts, reached, km = draw_route(big, j, p, alpha, 7 if cur or faded else 5)
        if cur:
            active = (k, j, km, pts[-1])
            for i in reached:
                labels.append(j["route"][i])
    img.alpha_composite(big.resize((W, H), Image.LANCZOS))
    d = ImageDraw.Draw(img)

    # градове
    seen = set()
    for c in labels:
        if c in seen: continue
        seen.add(c)
        lat, lon, bg, en, lab = CITIES[c]
        x, y = proj(lat, lon)
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=CREAM, outline=(6, 10, 18), width=2)
        if lab:
            dx, dy, anc = lab
            text(d, (x + dx, y + dy), bg if LANG == "bg" else en, f_city, CREAM, anc, stroke=4)
    if active:  # пулсираща точка там, където е Павел
        k, j, km, here = active
        x, y = proj(here[0], here[1])
        r = 12 + 6 * (math.sin(t * 8) + 1)
        d.ellipse([x - r, y - r, x + r, y + r], outline=j["color"], width=4)
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=j["color"])

    # заглавие
    a_title = 255 if t < TOTAL - DUR_END else 255
    text(d, (W / 2, 150), T["title"], f_title, CREAM + (a_title,), "ma")
    d.multiline_text  # noqa
    text(d, (W / 2, 385), T["sub"], f_sub, MUTED, "ma")

    # долна лента
    yb = MAP_TOP + MAP_H + 40
    if active:
        k, j, km, _ = active
        text(d, (70, yb), T["n"][k], f_head, j["color"])
        text(d, (70, yb + 66), (j["years"] + " · " + j["ref"]) if LANG == "bg" else (j["years_en"] + " · " + j["ref_en"]), f_years, MUTED)
        text(d, (W - 70, yb - 8), fmt(km), f_km, CREAM, "ra")
        text(d, (W - 70, yb + 86), T["km"], f_kml, MUTED, "ra")
    elif t >= TOTAL - DUR_END:
        for k, j in enumerate(JOURNEYS):
            y = yb - 20 + k * 58
            d.rounded_rectangle([70, y + 12, 104, y + 30], 6, fill=j["color"])
            text(d, (124, y), T["n"][k], f_years, CREAM)
            text(d, (W - 70, y), fmt(j["total"]) + " км" if LANG == "bg" else fmt(j["total"]) + " km", f_years, CREAM, "ra")
        tot = sum(j["total"] for j in JOURNEYS)
        y = yb - 20 + 3 * 58 + 8
        d.line([(70, y), (W - 70, y)], fill=(80, 74, 60), width=2)
        text(d, (70, y + 18), T["total"], f_head, CREAM)
        text(d, (W - 70, y + 18), fmt(tot) + (" км" if LANG == "bg" else " km"), f_head, (242, 193, 78), "ra")
        cta_a = int(255 * ease((t - (TOTAL - DUR_END) - 1.2) / .6))
        text(d, (W / 2, H - 118), T["cta"], f_years, CREAM + (cta_a,), "ma")
    text(d, (W / 2, H - 58), T["note"], f_note, (120, 112, 96), "ma")
    return img.convert("RGB")


def main():
    if "--frame" in sys.argv:
        t = float(sys.argv[sys.argv.index("--frame") + 1])
        out = HERE / "out" / f"paul_{LANG}_{t:.1f}s.png"
        frame(t).save(out)
        print(out)
        return
    out = HERE / "out" / f"paul_{LANG}.mp4"
    n = int(TOTAL * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(frame(i / FPS).tobytes())
        if i % 150 == 0:
            print(f"{i}/{n}", flush=True)
    ff.stdin.close(); ff.wait()
    print(out, f"{TOTAL:.1f}s", [round(j['total']) for j in JOURNEYS])


if __name__ == "__main__":
    main()
