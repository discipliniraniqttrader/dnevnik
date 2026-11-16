"""Auto-generate <topic>/painted.json from script.json (style "painted"): per-beat image prompt from the beat's "scene", wide-subject detection (landscape image + lateral pan),
overlay specs that need no precise targets (big counter, ratio badge, label badge, choice tags). Hand-edited painted.json is never overwritten (use --force).
  python3 -m shortkit.paintplan topics/<name> [--force]"""
import json, re, sys
from pathlib import Path

STYLE = "cinematic matte painting, dramatic dusk, deep orange sky, black silhouettes, golden rim light, god rays, light rain, painterly, highly detailed"
NEG = ("text, letters, numbers, watermark, logo, signature, blurry, deformed, bad hands, extra fingers, modern buildings, cartoon, daylight, blue sky, white background, "
       "ship in sky, floating ship, duplicate ship, reflection in clouds, dark, murky")
# rules ------------------------------------------------------------------------------------------------------------
META = re.compile(r"\b(counter|label|labels|dimension|graphic|badge|tags?|camera|ticks?|draws? on|text|arrow|number|numbers|slides? (?:in|over)|pulls? back|zooms?)\b", re.I)
WIDE = re.compile(r"\b(ark|ships?|boats?|hull|barge|vessel|schooner|liner|cargo|fleet|convoy|train|bridge|wall|caravan|army|procession|field|stadium|river|skyline|city|ridge|ridges|mountains?|range|coast|shore|desert|road|aqueduct|temple|pyramids?|side view|side by side|horizon)\b", re.I)
TALL = re.compile(r"\b(close-up|portrait|hand|forearm|arm|face|statue|tower|waterfall|top-down|standing person|single tree|door)\b", re.I)
ARK_RULE = dict(prompt="enormous long low rectangular wooden barge, flat roof, side view, extremely long horizontal hull", neg="tower, pagoda, tall, multi-storey, building, castle, sails, masts")
RULES = [  # (regex on scene, extra prompt words, extra negative)
    (re.compile(r"\bfootball|stadium|pitch\b", re.I), "bright warm floodlights, dusk glow, warm light", "green grass, dark"),
    (re.compile(r"\bsearchlight\b", re.I), "bright white searchlight beam cone of light in the sky", "ship, boat"),
    (re.compile(r"\btop-down|bird.?s-eye\b", re.I), "bright golden light reflecting on the water, orange glow", "dark, black"),
    (re.compile(r"\bship|boat|schooner|liner|cargo\b", re.I), "", "ship in sky, floating ship, duplicate ship, reflection in clouds"),
]


def clean_scene(scene):
    sent = [x.strip() for x in re.split(r"[.;]", scene) if x.strip()]; keep = []
    for sn in sent:
        if ":" in sn and len(sn.split(":")[0].split()) <= 3: sn = sn.split(":", 1)[1].strip()
        parts = [c.strip() for c in sn.split(",") if c.strip()]
        for c in parts:
            if META.search(c):
                m = META.search(c); head = c[:m.start()]; head = re.sub(r"\b(with|and|a|the|of)\s*$", "", head.strip(), flags=re.I).strip()
                if len(head.split()) >= 3: keep.append(head)
            else: keep.append(c)
    words = [w for w in " ".join(keep).split() if not re.fullmatch(r"[\d,.:]+", w)]
    return " ".join(words[:30])


def overlays(scene, text):
    ov = []; t0 = 0.6
    m = re.search(r"(?:counter|ticks? up|counts?)[^0-9]*([\d][\d,\.]*)\s*([A-Za-z%]{1,6})?", scene, re.I)
    if m:
        v = float(m.group(1).replace(",", "")); u = (" " + m.group(2)) if m.group(2) else ""
        ov.append(dict(type="counter", **{"from": 0, "to": int(v) if v == int(v) else v}, unit=u, size=230, pos=[540, 640], t0=0.3, d=2.0, sub="")); return ov
    m = re.search(r"(\d+)\s*:\s*(\d+)", scene)
    if m: ov.append(dict(type="badge", text=f"{m.group(1)} : {m.group(2)}", size=170, pos=[540, 640], t0=t0, sub="RATIO")); return ov
    m = re.search(r"([A-Z]{4,}(?:\s*/\s*[A-Z]{4,})+)", scene)
    if m: ov.append(dict(type="tags", labels=[x.strip() for x in m.group(1).split("/")], y=640, t0=1.2)); return ov
    m = re.search(r"labels?\s+(\d[\d,\.]*\s*[A-Za-z%]+)", scene, re.I)
    if m: ov.append(dict(type="badge", text=m.group(1).upper(), size=100, pos=[540, 640], t0=t0, sub="")); return ov
    m = re.search(r"(\d[\d,\.]*(?:\s*,\s*\d[\d,\.]*)+)\s*([A-Za-z]+)", scene)
    if m: ov.append(dict(type="badge", text=" x ".join(x.strip() for x in m.group(1).split(",")) + " " + m.group(2).upper(), size=84, pos=[540, 640], t0=t0, sub="")); return ov
    return ov


def build(topic):
    topic = Path(topic); S = json.load(open(topic / "script.json")); beats = []; w = 0
    covenant = bool(re.search(r"covenant|mercy seat|cherub|gold(?:en)? chest", json.dumps(S), re.I))            # the Ark of the Covenant is a chest, not Noah's barge
    for i, b in enumerate(S["beats"]):
        sc = b.get("scene", b["text"]); subj = clean_scene(sc) or b["text"]; wide = bool(WIDE.search(sc)) and not TALL.search(sc)
        neg = []; add = ""
        if re.search(r"\bark\b", sc, re.I) and not TALL.search(sc) and not covenant:
            subj = ARK_RULE["prompt"] + (", " + subj if len(subj.split()) < 14 else ""); neg.append(ARK_RULE["neg"]); wide = True
        for rx, p, n in RULES:
            if rx.search(sc):
                add += (", " + p) if p else ""; neg.append(n)
        be = dict(prompt=(subj + add).strip(", "), neg=", ".join(x for x in neg if x))
        if wide: be["wide"] = {"fit": 0.52, "center": 0.56}; be["cam"] = dict(type="pan", f0=0.0 if w % 2 == 0 else 1.0, f1=1.0 if w % 2 == 0 else 0.0); w += 1
        ov = overlays(sc, b["text"])
        if ov: be["ov"] = ov
        beats.append(be)
    return dict(auto=True, style=STYLE, negative=NEG, seed=int(sum(map(ord, topic.name))) * 7 % 9000 + 1000, size=[768, 1344], wide_size=[1344, 768], steps=3, beats=beats)


def ensure(topic, force=False):
    p = Path(topic) / "painted.json"
    if p.exists() and not force: return p
    json.dump(build(topic), open(p, "w"), indent=1); print(f"[paintplan] wrote {p} (auto-generated from scenes; edit by hand, re-run with --force to regenerate)"); return p


if __name__ == "__main__":
    ensure(sys.argv[1], "--force" in sys.argv)
