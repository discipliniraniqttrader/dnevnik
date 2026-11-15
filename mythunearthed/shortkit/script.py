"""script.json -> normalized beats (+ places). Accepts the SHOTS.md format and the looser noah/script.json format."""
import json, re, unicodedata
from pathlib import Path

SHOT_TYPES = ("PRESENTER", "MAP", "TEXT", "EVENT")
BACKDROPS = ("desert", "mountain", "city", "night", "sea")
ACTIONS = ("idle", "wave", "point_left", "point_right", "shrug", "surprised", "nod")
TEXT_KINDS = ("quote", "word_shatter", "glow_word", "big_number")
OBJECTS = ("ark_box", "scroll", "jar", "crown", "gold_pile", "ship", "tower", "gate", "fire", "ruins", "whale")
SCENES = ("tablet", "aerial", "birds", "counter", "icon_grid", "object", "split_compare", "sea_parting", "mountain_storm",
          "fire_rain", "crowd", "manna")
ICONS = ("peak", "walls", "temple", "tent", "ship", "ruins", "river", "dot", "waves")
ZOOMS = {"close": 2.3, "mid": 3.5, "out": 5.2, "wide": None}

# keyword -> scene for loose free-text EVENT descriptions (noah/script.json style)
SCENE_WORDS = [
    (("aerial", "mound", "photo", "satellite"), "aerial"), (("tablet", "clay", "cuneiform", "stone slab"), "tablet"),
    (("bird", "dove", "raven", "swallow", "pigeon"), "birds"), (("parting", "red sea", "sea part", "walls of water"), "sea_parting"),
    (("storm", "thunder", "lightning", "sinai"), "mountain_storm"), (("fire rain", "brimstone", "raining fire", "sulfur", "sulphur"), "fire_rain"),
    (("manna", "snowflake", "falling food", "bread from heaven"), "manna"),
    (("crowd", "multitude", "people", "army", "marching", "exodus"), "crowd"), (("counter", "count up", "number grows"), "counter"),
    (("grid", "icons"), "icon_grid"), (("versus", " vs ", "compare", "two versions", "side by side"), "split_compare"),
]

# tiny gazetteer for atlas lettering on map shots: NAME -> (lat, lon, tone)
GAZ = {
    "EGYPT": (27.0, 30.0, "land"), "SINAI": (29.5, 33.9, "land"), "CANAAN": (32.0, 35.2, "land"), "ISRAEL": (31.4, 34.9, "land"),
    "JORDAN": (31.0, 36.6, "land"), "SYRIA": (35.0, 38.5, "land"), "LEBANON": (33.9, 35.9, "land"), "TURKEY": (39.05, 35.5, "land"),
    "ARMENIA": (40.45, 44.75, "land"), "GEORGIA": (42.0, 43.5, "land"), "AZERBAIJAN": (40.4, 47.7, "land"), "IRAN": (33.0, 53.0, "land"),
    "IRAQ": (33.0, 43.7, "land"), "ARABIA": (24.5, 44.0, "land"), "MESOPOTAMIA": (34.0, 43.0, "land"), "BABYLONIA": (32.5, 45.0, "land"),
    "ASSYRIA": (36.3, 43.2, "land"), "PERSIA": (32.5, 53.5, "land"), "GREECE": (39.2, 22.0, "land"), "ITALY": (42.5, 12.5, "land"),
    "ROME": (41.9, 12.5, "land"), "CYPRUS": (35.0, 33.2, "land"), "CRETE": (35.2, 24.9, "land"), "LIBYA": (27.0, 17.0, "land"),
    "SUDAN": (15.5, 30.0, "land"), "ETHIOPIA": (9.0, 39.5, "land"), "YEMEN": (15.5, 47.5, "land"), "KURDISTAN": (36.4, 44.2, "land"),
    "ANATOLIA": (39.0, 33.0, "land"), "JUDAH": (31.6, 35.0, "land"), "SAMARIA": (32.3, 35.2, "land"), "GALILEE": (32.9, 35.4, "land"),
    "MEDITERRANEAN SEA": (34.0, 26.0, "sea"), "RED SEA": (21.0, 38.0, "sea"), "BLACK SEA": (43.0, 34.0, "sea"),
    "CASPIAN SEA": (41.5, 50.5, "sea"), "PERSIAN GULF": (27.5, 51.5, "sea"), "DEAD SEA": (31.5, 35.5, "sea"),
}


def norm(s):
    s = s.replace("ı", "i").replace("İ", "I")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


_NUMW = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_NUMW.update({"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90})


def words_to_int(text):
    """'six hundred thousand' -> 600000 (first run of number words); 0 if none"""
    toks = re.findall(r"[a-z]+", norm(text)); best = 0; i = 0
    while i < len(toks):
        if toks[i] in _NUMW or toks[i] in ("hundred", "thousand", "million"):
            total = cur = 0; started = False
            while i < len(toks) and (toks[i] in _NUMW or toks[i] in ("hundred", "thousand", "million", "and")):
                w = toks[i]
                if w in _NUMW: cur += _NUMW[w]
                elif w == "hundred": cur = max(cur, 1) * 100
                elif w == "thousand": total += max(cur, 1) * 1000; cur = 0
                elif w == "million": total += max(cur, 1) * 1000000; cur = 0
                started = True; i += 1
            if started and total + cur > best: best = total + cur
        else: i += 1
    return best


def parse_number(*sources):
    for s in sources:
        if s is None: continue
        if isinstance(s, (int, float)): return float(s)
        m = re.search(r"\d[\d,\.]*", str(s))
        if m:
            try: return float(m.group(0).replace(",", "").rstrip("."))
            except ValueError: pass
    for s in sources:
        if s and isinstance(s, str):
            n = words_to_int(s)
            if n: return float(n)
    return None


def _quoted(s):
    m = re.findall(r"[\"“‘']([^\"”’']{2,40})[\"”’']", s or "")
    return m


def classify_scene(scene, text):
    s = norm(scene or "")
    for name in SCENES:
        if s.strip() == name: return name
    for ob in OBJECTS:
        if ob in s.replace(" ", "_") or ob.replace("_", " ") in s: return "object"
    for words, name in SCENE_WORDS:
        if any(w in s for w in words): return name
    return None


def load(topic_dir):
    topic_dir = Path(topic_dir)
    raw = json.load(open(topic_dir / "script.json"))
    S = dict(raw)
    S["topic"] = topic_dir.name
    S["title"] = raw.get("title", topic_dir.name)
    places = {}
    for k, v in (raw.get("places") or {}).items():
        lat, lon = float(v[0]), float(v[1])
        places[k] = dict(key=k, lat=lat, lon=lon, label=v[2] if len(v) > 2 else k.title(), icon=(v[3] if len(v) > 3 else "dot"),
                         conf=(v[4] if len(v) > 4 else "solid"))
        if places[k]["icon"] not in ICONS: places[k]["icon"] = "dot"
    S["places"] = places
    tts_over = {}
    p = topic_dir / "tts_text.json"
    if p.exists(): tts_over = json.load(open(p))
    S["chip"] = raw.get("chip") or make_chip(S["title"], topic_dir.name)
    S["default_backdrop"] = raw.get("backdrop", "desert")
    beats, warns = [], []
    for i, b in enumerate(raw["beats"], 1):
        beats.append(norm_beat(b, i, len(raw["beats"]), places, tts_over, S, warns))
    S["beats"] = beats
    rv = [b for b in beats if b["reveal"]]
    for k, b in enumerate(rv, 1):                       # bare "1"/"true" -> "k/total"
        if not re.search(r"\d\s*/\s*\d", b["reveal"]): b["reveal"] = f"{k}/{len(rv)}"
        else: b["reveal"] = re.sub(r"\s+", "", b["reveal"])
    S["improvements"] = [str(x) for x in (raw.get("improvements") or [])]
    S["warnings"] = warns
    return S


def make_chip(title, fallback):
    stop = {"where", "what", "why", "how", "did", "do", "does", "the", "is", "are", "was", "who", "when", "a", "an", "of", "in", "can", "could", "which", "and"}
    toks = [t for t in re.split(r"\s+", title.strip()) if t]
    run = []
    for t in toks:
        core = re.sub(r"[^\w']", "", t)
        if not core: continue
        if not run and core.lower() in stop: continue
        if core[0].isupper() and core.lower() not in stop and not core.isdigit():
            run.append(core)
            if re.search(r"[?!:]$", t) or len(run) == 2: break
        elif run: break
    return (" ".join(run) if run else fallback.replace("_", " ")).upper()[:22]


def place_mentions(text, places):
    """place keys mentioned by name in the narration, in order of appearance"""
    nt = norm(text); found = []
    for k, p in places.items():
        cands = {norm(k)} | {w for w in re.findall(r"[a-z]{4,}", norm(p["label"])) if w not in ("mount", "mountain", "site", "river", "city", "lake", "valley", "land", "near", "holy")}
        pos = [m.start() for c in cands for m in re.finditer(r"\b" + re.escape(c), nt)]
        if pos: found.append((min(pos), k))
    return [k for _, k in sorted(found)]


def norm_beat(b, i, n, places, tts_over, S, warns):
    o = dict(b)
    o["i"] = i
    o["text"] = b["text"].strip()
    shot = str(b.get("shot", "PRESENTER")).upper()
    if shot not in SHOT_TYPES:
        warns.append(f"beat {i}: unknown shot '{shot}' -> PRESENTER"); shot = "PRESENTER"
    o["shot"] = shot
    # voice text: say (string = whole sentence for the voice; dict = word substitutions) > tts_text.json > text
    say = b.get("say"); tts = o["text"]
    if isinstance(say, str) and say.strip(): tts = say.strip()
    elif isinstance(say, dict):
        for a, r in say.items(): tts = tts.replace(a, r)
    elif str(i) in tts_over: tts = tts_over[str(i)]
    o["tts"] = tts; o["used_say"] = bool(say) or (str(i) in tts_over)
    o["callout"] = (b.get("callout") or "").strip() or None
    o["source"] = b.get("source", "-")
    kw = b.get("keyword")
    o["keyword"] = str(kw).strip() if kw and str(kw).strip() else None
    rv = b.get("reveal")
    o["reveal"] = (str(rv).strip() or None) if rv not in (None, False, "") else None      # "2/4" or an int (total filled in load())
    o["action_given"] = b.get("action") in ACTIONS
    last = i == n
    if shot == "PRESENTER":
        a = b.get("action", "idle"); o["action"] = a if a in ACTIONS else "idle"
        bd = b.get("backdrop", S.get("default_backdrop", "desert")); o["backdrop"] = bd if bd in BACKDROPS else "desert"
        o["end"] = last
    elif shot == "MAP":
        if not places: warns.append(f"beat {i}: MAP shot but script has no places -> PRESENTER"); o["shot"] = "PRESENTER"; o["action"] = "point_right"; o["backdrop"] = "desert"; o["end"] = last; return o
        pins = [k for k in (b.get("pins") or []) if k in places]
        focus = b.get("focus")
        if not pins:
            pins = place_mentions(o["text"], places)
            if focus:
                near = [k for k, p in places.items() if abs(p["lat"] - focus[0]) < .06 and abs(p["lon"] - focus[1]) < .06]
                pins = near + [k for k in pins if k not in near] if not pins else pins
                if not pins: pins = near
        zoom = b.get("zoom", "mid")
        if zoom not in ZOOMS: zoom = "mid"
        if not focus:
            if pins: focus = [places[pins[0]]["lat"], places[pins[0]]["lon"]]
            else: zoom = "wide"
        if zoom == "wide" and not pins and not b.get("pins"): pins = list(places)
        o.update(pins=pins, focus=focus, zoom=zoom, explicit_pins=bool(b.get("pins")))
    elif shot == "TEXT":
        scene = b.get("scene", "") or ""
        kind = b.get("kind")
        sl = norm(scene)
        if kind not in TEXT_KINDS:
            if any(w in sl for w in ("split", "shatter", "break", "crack")): kind = "word_shatter"
            elif any(w in sl for w in ("glow", "fade")): kind = "glow_word"
            elif any(w in sl for w in ("number", "count")) or parse_number(b.get("number")) is not None: kind = "big_number"
            elif "quote" in sl or _quoted(o["text"]): kind = "quote"
            else: kind = "quote"
        o["kind"] = kind
        disp = None
        for k in ("display", "word", "screen_text", "big", "on_screen", "title"):
            if b.get(k): disp = str(b[k]); break
        if disp is None:
            q = _quoted(scene); up = re.findall(r"\b[A-Z][A-Z\-']{3,}\b", scene)
            if kind == "word_shatter": disp = (up or q or [o["callout"] or "BREAK"])[0]
            elif kind == "glow_word": disp = (q or up or [o["callout"] or (re.findall(r"[A-Z][\w\-]{3,}", o["text"]) or ["..."])[0]])[0]
            elif kind == "big_number":
                n_ = parse_number(b.get("number"), o["callout"], o["text"]); disp = None
                o["number"] = n_ if n_ is not None else 0.0
            else:
                qq = [x for x in _quoted(o["text"]) if len(x) > 8]
                disp = qq[0] if qq else o["text"]
        o["display"] = disp
        if kind == "big_number" and "number" not in o:
            o["number"] = parse_number(b.get("number"), o["callout"], o["text"]) or 0.0
        o["unit"] = b.get("unit") or b.get("label") or ""
    else:  # EVENT
        scene = b.get("scene", "") or ""
        name = classify_scene(scene, o["text"])
        if name is None:
            name = classify_scene(o["text"], o["text"])
            if name is None:
                name = "object"; warns.append(f"beat {i}: could not classify scene '{scene}' -> object")
        o["scene_name"] = name
        ob = b.get("object")
        if name == "object":
            if ob not in OBJECTS:
                s = norm(scene + " " + o["text"]).replace(" ", "_")
                ob = next((x for x in OBJECTS if x in s or x.replace("_", " ") in norm(scene + " " + o["text"])), None)
                if ob is None:
                    ob = {"ship": "ship", "boat": "ship", "ark": "ark_box", "tower": "tower", "gate": "gate", "crown": "crown", "king": "crown",
                          "gold": "gold_pile", "jar": "jar", "scroll": "scroll", "fire": "fire", "ruin": "ruins", "whale": "whale", "fish": "whale"}.get(
                        next((w for w in re.findall(r"[a-z]+", norm(scene + " " + o["text"])) if w in ("ship", "boat", "ark", "tower", "gate", "crown", "king", "gold", "jar", "scroll", "fire", "ruin", "whale", "fish")), ""), "scroll")
            o["object"] = ob
        o["label"] = b.get("label") or ""
        o["number"] = parse_number(b.get("number"), o["callout"], o["text"]) if name == "counter" else None
        if name == "counter" and not o["number"]: o["number"] = 1000.0
        o["icon"] = b.get("icon", "dot") if b.get("icon", "dot") in ICONS else "dot"
        o["count"] = int(b.get("count") or 12)
        o["left"] = b.get("left", "VERSION A"); o["right"] = b.get("right", "VERSION B")
        o["birds"] = b.get("birds") or ["dove", "swallow", "raven"]
    return o
