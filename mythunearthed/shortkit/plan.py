"""script + narration timeline -> shot plan (+ Ezra actions, SFX events). Pure data, picklable."""
import math, re
from .common import FPS
from .script import GAZ, ZOOMS, norm, place_mentions, words_to_int, _NUMW
from .voice import word_times
from .common import big_font

NT_BEAT, NT_SUB = 12, 9          # transition length in frames (beat boundary / sub-shot cut)
CORNER_SCENES = ("object", "aerial", "tablet", "birds", "sea_parting", "mountain_storm", "fire_rain", "manna")


def _find_word(words, key, start=0):
    """time of first word (index >= start) whose normalised text starts with key"""
    k = norm(key).strip()
    for i in range(start, len(words)):
        w = re.sub(r"[^a-z0-9\-']", "", norm(words[i][0]))
        if w.startswith(k) and k: return words[i][1], i
    return None, None


SHOT_MIN, SHOT_MAX = 1.2, 2.0       # viral pacing: every shot 1.2-2.0 s
WOW_EVERY = 3                       # every 3rd shot is a "wow" move
EZRA_TARGET = .38                   # aim a little over the 35% minimum
KW_ZOOM = .07                       # soft 6-8% zoom-in at the keyword
CAP_PX, CAP_MAXW = 110, 1000
_STOP = set("because between through though another without about around there their these those which where while being before after still other every really "
            "would could should might something everything nothing anyone anything people always almost already during whether until again".split())
_UNSURE = re.compile(r"not proven|no proof|no evidence|unproven|never proven|unverified|nobody knows|no one knows|cannot be proven|can't be proven|disputed|unclear|"
                     r"no record|not mentioned|never says|never mention|claims?\b|legend|unknown|uncertain|debated")


def _clean(w): return re.sub(r"[^a-z0-9]", "", norm(w))


def pick_keyword(text):
    """no explicit keyword -> first numeric word, else the longest word (>=4 letters, not a filler)"""
    toks = text.split()
    for t in toks:
        if re.search(r"\d", t): return t
    for t in toks:
        if _clean(t) in _NUMW or _clean(t) in ("hundred", "thousand", "million"):
            if _clean(t) not in ("zero", "one", "two", "three") : return t
    best = None
    for t in toks:
        c = _clean(t)
        if len(c) < 4 or c in _STOP: continue
        if best is None or len(c) > len(_clean(best)): best = t
    return best


def match_keyword(words, kw):
    """(first word index, run length) of the keyword (one or several words) in [(text,t0,t1)]; None if absent"""
    ks = [_clean(x) for x in kw.split() if _clean(x)]
    if not ks: return None
    for i in range(len(words)):
        if all(i + j < len(words) and _clean(words[i + j][0]).startswith(k[:max(3, len(k) - 2)] if len(k) > 4 else k) for j, k in enumerate(ks)):
            return i, len(ks)
    return None


def chunk_captions(words, kw_run, beat, first_beat):
    """1-3 words per caption; the keyword always starts its own chunk so the pop lands on the spoken word."""
    out, cur = [], []
    ks, kn = (kw_run if kw_run else (None, 0))
    def width(ws): return big_font(" ".join(w[0] for w in ws).upper(), CAP_PX).getlength(" ".join(w[0] for w in ws).upper())
    def flush():
        nonlocal cur
        if cur: out.append(cur); cur = []
    for i, w in enumerate(words):
        if cur and (len(cur) >= 3 or width([*(c[1] for c in cur), w]) > CAP_MAXW or cur[-1][1][0][-1] in ",.;:?!" or i == ks or (ks is not None and ks <= cur[0][0] < ks + kn and i >= ks + kn)):
            flush()
        cur.append((i, w))
    flush()
    caps = []
    for ci, ch in enumerate(out):
        ws = [c[1] for c in ch]; idx = [c[0] for c in ch]
        txt = [re.sub(r"[.,;:]+$", "", w[0]).upper() for w in ws]
        isk = [ks is not None and ks <= i < ks + kn for i in idx]
        t0 = ws[0][1]; t1 = ws[-1][2] + .12
        if ci + 1 < len(out):
            nt0 = out[ci + 1][0][1][1]
            t1 = nt0 if nt0 - ws[-1][2] < .35 else min(t1, nt0)
        if ci == 0 and first_beat: t0 = 0.0
        caps.append(dict(beat=beat, words=txt, kw=isk, t0=float(t0), t1=float(t1), kt=float(ws[isk.index(True)][1]) if any(isk) else None))
    return caps


def build(S, voice, BT, TOTAL, region):
    beats = S["beats"]; n = len(beats); places = S["places"]
    WORDS = [word_times(b["text"], bt["t0"], bt["speech"], voice) for b, bt in zip(beats, BT)]
    cut = [0.0] + [BT[i]["t0"] - 0.08 for i in range(1, n)] + [TOTAL]          # beat i spans cut[i]..cut[i+1]
    dur = [cut[i + 1] - cut[i] for i in range(n)]
    # ---------------- shots per beat: avg shot <= ~1.9 s (end card is one shot)
    nsub = []
    for i, b in enumerate(beats):
        last_end = (i == n - 1 and b["shot"] == "PRESENTER")
        if last_end: nsub.append(1); continue
        # shots of 1.2-2.0 s: pick the count whose shot length is in range (closest to ~1.6 s when several fit)
        fits = [k for k in range(1, 9) if SHOT_MIN <= dur[i] / k <= SHOT_MAX]
        nsub.append(min(fits, key=lambda k: abs(dur[i] / k - 1.65)) if fits else min(range(1, 9), key=lambda k: abs(dur[i] / k - 1.65) if dur[i] / k >= 1.0 else 9))
    def avg(): return TOTAL / sum(nsub)
    # ---------------- pins
    pin_t, pin_beat, pin_order = {}, {}, []
    for i, b in enumerate(beats):
        if b["shot"] != "MAP": continue
        for k in b["pins"]:
            if k in pin_t: continue
            p = places[k]; cands = [norm(k)] + [w for w in re.findall(r"[a-z]{4,}", norm(p["label"])) if w not in ("mount", "mountain", "site", "river", "city", "lake", "valley")]
            t_ = None
            for c_ in cands:
                tt, _ = _find_word(WORDS[i], c_)
                if tt is not None: t_ = tt if t_ is None else min(t_, tt)
            pin_t[k] = (t_ - .05) if t_ is not None else cut[i] + 0.7
            pin_beat[k] = i; pin_order.append(k)
    # ---------------- callouts / stamps
    def callout_time(i, text):
        toks = [t for t in re.findall(r"[a-z0-9']+", norm(text)) if len(t) > 3 and not t.isdigit()]
        for tok in toks:
            tt, _ = _find_word(WORDS[i], tok[:max(4, len(tok) - 2)])
            if tt is not None: return max(cut[i] + .15, tt - .12)
        return cut[i] + .3
    shots = []; region_bounds = (region["lat0"], region["lat1"], region["lon0"], region["lon1"])
    state = dict(focus=None, vis=None, primary=None, side="right", last_ezra=None)
    vis_of = lambda z: region["vis_wide"] if ZOOMS[z] is None else min(ZOOMS[z], region["vis_wide"])
    for i, b in enumerate(beats):
        a, e = cut[i], cut[i + 1]; ns = nsub[i]; words = WORDS[i]
        # sub boundaries snapped to word starts
        bounds = [a]
        for k in range(1, ns):
            ideal = a + (e - a) * k / ns
            ws = [w[1] for w in words if abs(w[1] - ideal) < .4 and w[1] > bounds[-1] + SHOT_MIN - .1 and w[1] < e - SHOT_MIN + .1]
            bounds.append(min(ws, key=lambda x: abs(x - ideal)) if ws else ideal)
        bounds.append(e)
        co = None; stamp = None
        if b["callout"]:
            co = (b["callout"], callout_time(i, b["callout"]))
            if re.match(r"CASE \d", b["callout"].upper()) and b["shot"] == "MAP" and b["pins"]:
                stamp = (b["callout"].upper(), places[b["pins"][0]]["label"].upper(), a + 0.18)
                co = None
        base = dict(beat=i + 1, ot0=a, odur=e - a, nsub=ns, callout=co, stamp=stamp)
        tm = {}
        if b["shot"] == "TEXT":
            k_ = b["kind"]
            if k_ == "word_shatter":
                tw, wi = _find_word(words, b["display"][:5])
                tw = (tw - a - .05) if tw is not None else .25
                ts = None
                if wi is not None:
                    for j in range(wi, len(words) - 1):
                        if words[j][0][-1] in ".!?": ts = words[j + 1][1] - a; break
                ts = ts if ts is not None else (e - a) * .6
                tm = dict(t_word=max(.1, tw), t_shatter=max(ts, tw + .6), t_quote=max(0, tw - .15)); tm["t_peaks_end"] = tm["t_shatter"] + (e - a - tm["t_shatter"]) * .4
            elif k_ == "glow_word":
                tw, _ = _find_word(words, re.sub(r"[^A-Za-z]", "", b["display"])[:4])
                tm = dict(t_text=max(.1, (tw - a - .9)) if tw is not None else .15)
                tm["t_dis"] = max(tm["t_text"] + 1.6, (tw - a + .1) if tw is not None else (e - a) * .6)
        elif b["shot"] == "EVENT":
            sn = b["scene_name"]
            if sn == "tablet": tm = dict(zoom_at=(e - a) * .5, glow_at=(e - a) * .78)
            elif sn == "birds":
                ks = b["birds"]; rel = {}
                for q, kind in enumerate(ks[:3]):
                    kind_ = kind if kind in ("dove", "swallow", "raven") else ("raven" if q % 2 else "dove")
                    tw, _ = _find_word(words, kind)
                    rel[kind_] = (tw - a - .1) if tw is not None else .15 + q * (e - a) * .5 / max(len(ks), 1)
                tm = dict(rel=rel)
            elif sn == "mountain_storm": tm = dict(flashes=[min(.9, (e - a) * .3), min(1.8, (e - a) * .6)])
        # ---------------- per-sub shots
        if b["shot"] == "MAP":
            F_ = b["focus"]; wide = b["zoom"] == "wide"; vis = vis_of(b["zoom"]); pins_now = [k for k in pin_order if pin_beat[k] <= i]
            labs = []
            nt = norm(b["text"])
            for name, (la, lo, tone) in GAZ.items():
                m = re.search(r"\b" + re.escape(name.lower()) + r"\b", nt)
                if not m or not (region_bounds[0] < la < region_bounds[1] and region_bounds[2] < lo < region_bounds[3]): continue
                if abs(la - F_[0]) > 7 or abs(lo - F_[1]) > 9: continue
                tt, _ = _find_word(words, name.split()[0])
                labs.append((name, la, lo, tone, (tt - .3) if tt is not None else a + .15))
            labs = labs[:3]
            connect = None
            if not wide:
                if len(b["pins"]) >= 2: connect = (b["pins"][0], b["pins"][1])
                else:
                    new = [k for k in b["pins"] if pin_beat.get(k) == i]
                    if len(new) == 1 and state["primary"] and state["primary"] != new[0]:
                        pa, pb = places[state["primary"]], places[new[0]]
                        if math.hypot(pa["lat"] - pb["lat"], (pa["lon"] - pb["lon"]) * .8) < 9: connect = (state["primary"], new[0])
            prev = state["focus"]
            dist = 0 if prev is None else math.hypot(prev[0] - F_[0], (prev[1] - F_[1]) * .8)
            for k in range(ns):
                t0_, t1_ = bounds[k], bounds[k + 1]
                if wide: side = None
                else:
                    state["side"] = "right" if state["side"] == "left" else "left"; side = state["side"]
                tx, ty = (540, 960) if wide else ((650, 700) if side == "left" else (430, 700))
                C = lambda lat, lon, v, tilt, yaw: dict(lat=lat, lon=lon, vis=v, tilt=tilt, yaw=yaw, tx=tx, ty=ty)
                arc = 0
                if k == 0:
                    if wide:
                        A_ = C(*F_, vis * 1.12, .78, 6) if prev is None else C(prev[0], prev[1], max(prev[2], vis * .9), .78, 6); B_ = C(*F_, vis, .8, 0); arc = .1
                    elif prev is None:
                        A_ = C(F_[0] - .55 * vis / 2.5, F_[1] - .9 * vis / 2.5, vis * 2.3, .8, 14); B_ = C(*F_, vis, .88, -4); arc = .2
                    else:
                        A_ = C(prev[0], prev[1], prev[2], .84, 8); B_ = C(*F_, vis, .88, -4); arc = min(.5, .12 + dist * .12)
                else:
                    var = [((.92, .8), (14, -10), (.88, .9)), ((1.12, .95), (-12, 8), (.84, .88)), ((.85, .75), (20, 30), (.86, .9))][(k - 1) % 3]
                    if wide: var = ((1.02, .94), (-8, 6), (.8, .83))
                    A_ = C(*F_, vis * var[0][0], var[2][0], var[1][0]); B_ = C(*F_, vis * var[0][1], var[2][1], var[1][1])
                sh = dict(base, kind="map", t0=t0_, t1=t1_, sub=k, cam=(A_, B_), arc=arc, ezra=side, wide=wide, pins=pins_now, F=tuple(F_), vis0=vis, txy=(tx, ty),
                          connect=connect, labels=labs, stamp=stamp if k == 0 or True else None)
                if wide and len(pins_now) >= 2: sh["path"] = (pins_now, a + .3, e - .6)
                shots.append(sh)
            state["focus"] = (F_[0], F_[1], vis * (.75 if not wide else .94)); state["primary"] = b["pins"][0] if b["pins"] else state["primary"]
        elif b["shot"] == "PRESENTER":
            end = b.get("end")
            for k in range(ns):
                sc0 = 1.0 + .045 * k
                shots.append(dict(base, kind="end" if end else "presenter", t0=bounds[k], t1=bounds[k + 1], sub=k, backdrop=b["backdrop"], variant=(i + k) % 3,
                                  action=b["action"], sc=(sc0, sc0 + .05), ezra=None))
        else:
            kind = "text" if b["shot"] == "TEXT" else "event"
            for k in range(ns):
                shots.append(dict(base, kind=kind, t0=bounds[k], t1=bounds[k + 1], sub=k, tm=tm, ezra=None))
    # transitions
    for j, s in enumerate(shots):
        s["idx"] = j; s["dur"] = s["t1"] - s["t0"]
        first = (j == 0) or shots[j - 1]["beat"] != s["beat"]
        s["trans"] = "none" if j == 0 else ("zoomfade" if first else "fade")
        s["nt"] = NT_BEAT if first else NT_SUB
    # ---------------- keywords + big captions (1-3 words, keyword pops gold)
    caps, kws = [], []
    for i, b in enumerate(beats):
        kw = b.get("keyword") or pick_keyword(b["text"])
        run = match_keyword(WORDS[i], kw) if kw else None
        if run is None and b.get("keyword"):
            alt = pick_keyword(b["text"]); run = match_keyword(WORDS[i], alt) if alt else None
        bc = chunk_captions(WORDS[i], run, i + 1, i == 0)
        caps += bc
        k_ = next((c for c in bc if c["kt"] is not None), None)
        kws.append(dict(beat=i + 1, t=k_["kt"] if k_ else None, word=" ".join(w for w, f in zip(k_["words"], k_["kw"]) if f) if k_ else None))
    # ---------------- wow moves: every 3rd shot (not the end card)
    def numeric_kw(bi):
        # giant number only when the beat's keyword IS the number (nothing else in it)
        w = (kws[bi - 1]["word"] or "").strip().strip(".,'\"!?")
        if re.fullmatch(r"\d[\d,\.]*", w): return w.rstrip(".,")
        n_ = words_to_int(w) if w and not re.search(r"\d", w) else None
        return f"{n_:,}" if n_ else None
    for j, s_ in enumerate(shots):
        s_["wow"] = None
        if j % WOW_EVERY != WOW_EVERY - 1 or s_["kind"] == "end": continue
        bt_ = beats[s_["beat"] - 1]
        if s_["kind"] == "map" and not s_["wide"]:
            F_, v_ = s_["F"], s_["vis0"]; tx, ty = s_["txy"]
            s_["cam"] = (dict(lat=F_[0] - .5 * v_ / 2.5, lon=F_[1] - 1.0 * v_ / 2.5, vis=v_ * 2.4, tilt=.92, yaw=22, tx=tx, ty=ty),
                         dict(lat=F_[0], lon=F_[1], vis=v_ * .8, tilt=.86, yaw=-5, tx=tx, ty=ty))
            s_["arc"] = .12; s_["wow"] = "fly"
        elif s_["kind"] == "event" and bt_["scene_name"] == "object": s_["wow"] = "spot"
        elif s_["kind"] in ("event", "text") and numeric_kw(s_["beat"]) and not bt_.get("callout") and not bt_.get("label") and not bt_.get("display") and not (s_["kind"] == "text" and bt_["kind"] == "big_number") \
                and not (s_["kind"] == "event" and bt_["scene_name"] in ("counter", "icon_grid")):
            s_["wow"] = "number"; s_["giant"] = numeric_kw(s_["beat"])
        else: s_["wow"] = "push"
    # ---------------- Ezra on screen >= 35%: corner panel on whole beats (bottom corner, clear of content/pins/face)
    def share():
        return sum(s["dur"] for s in shots if s["kind"] in ("presenter", "end") or s.get("ezra")) / TOTAL
    cand_beats = [i for i in range(1, n) if beats[i]["shot"] != "PRESENTER" and not any(s_.get("ezra") for s_ in shots if s_["beat"] == i + 1)]
    pri = lambda i: (0 if beats[i].get("reveal") else 1 if beats[i]["shot"] == "EVENT" and beats[i]["scene_name"] in CORNER_SCENES else 2 if beats[i]["shot"] == "TEXT" else 3, i)
    side = "left"
    for i in sorted(cand_beats, key=pri):
        if share() >= EZRA_TARGET: break
        side = "right" if side == "left" else "left"
        for s_ in shots:
            if s_["beat"] == i + 1: s_["ezra"] = side
    for j, s in enumerate(shots):
        s["ezra_slide"] = bool(s.get("ezra") and not (j and shots[j - 1].get("ezra") == s["ezra"] and shots[j - 1]["beat"] == s["beat"]))
        sc = []
        if s.get("stamp"): sc.append((s["stamp"][2], 5, .3))
        if s.get("callout"): sc.append((s["callout"][1], 3, .2))
        if s["kind"] == "text" and beats[s["beat"] - 1].get("kind") == "word_shatter": sc.append((s["ot0"] + s["tm"]["t_shatter"], 5, .4))
        s["shakes"] = sc
    # ---------------- Ezra reactions: given action wins; otherwise mood from the beat
    acts, prev_pt = [], "point_right"
    for i, b in enumerate(beats):
        ss = [s for s in shots if s["beat"] == i + 1]; txt = b["text"]; nt = norm(txt)
        unsure = bool(_UNSURE.search(nt)) or "not proven" in norm(b.get("callout") or "")
        last_q = i == n - 1 and "?" in txt
        if b["shot"] == "PRESENTER":
            if b["action_given"] and b["action"] != "idle": ty = b["action"]
            elif i == 0: ty = "surprised"
            elif unsure: ty = "shrug"
            elif last_q or "?" in txt: ty = "nod"
            elif b.get("reveal") or re.search(r"\d|\b(first|second|third|fourth|here|this|look)\b", nt): prev_pt = "point_left" if prev_pt == "point_right" else "point_right"; ty = prev_pt
            elif re.search(r"\b(but|however|yet|never|nobody|secret|hidden|forbidden|lost|shock)", nt): ty = "surprised"
            else: ty = "nod" if i % 2 else "wave"
            acts.append((cut[i] + .1, dur[i] - .1, ty))
        else:
            side_ = next((s["ezra"] for s in ss if s.get("ezra")), None)
            if side_:
                ty = "shrug" if unsure else ("surprised" if i == 0 else ("point_right" if side_ == "left" else "point_left"))
                acts.append((cut[i] + .15, dur[i] - .15, ty))
    # ---------------- SFX
    ev = {k: [] for k in ("whoosh", "whip", "impact", "pop", "place", "tick", "flap", "birdwhoosh", "shatter", "shimmer", "wind", "ocean", "thunder", "rumble", "kwpop", "softimpact")}
    for s in shots:
        if s["trans"] == "zoomfade": ev["whoosh"].append(s["t0"])
    seen = set()
    for s in shots:
        if s["beat"] in seen: continue
        seen.add(s["beat"]); b = beats[s["beat"] - 1]
        if s.get("callout"): ev["pop"].append(s["callout"][1])
        if s.get("stamp"): ev["impact"].append(s["stamp"][2] + 5 / FPS)
        if s["kind"] == "text" and b["kind"] == "word_shatter":
            ev["shatter"].append(s["ot0"] + s["tm"]["t_shatter"]); ev["impact"].append(s["ot0"] + s["tm"]["t_shatter"]); ev["wind"].append((s["ot0"], s["ot0"] + s["odur"]))
        if s["kind"] == "text" and b["kind"] == "glow_word": ev["shimmer"].append(s["ot0"] + s["tm"]["t_text"])
        if s["kind"] == "text" and b["kind"] == "big_number": ev["tick"] += [s["ot0"] + .1 + q * .06 for q in range(int(min(s["odur"] * .6, 2.2) / .06))]
        if s["kind"] == "map": ev["wind"].append((s["ot0"], s["ot0"] + s["odur"]))
        if s["kind"] == "event":
            sn = b["scene_name"]
            if sn == "tablet": ev["impact"].append(s["ot0"] + .05); ev["tick"] += [s["ot0"] + .4 + q * .075 for q in range(20)]
            if sn == "birds":
                for kd, r in s["tm"]["rel"].items():
                    ev["birdwhoosh"].append(s["ot0"] + r); rate = {"dove": 2.6, "swallow": 4.4, "raven": 1.9}[kd]
                    ev["flap"] += [s["ot0"] + r + q / rate for q in range(int(1.6 * rate))]
            if sn == "sea_parting": ev["ocean"].append((s["ot0"], s["ot0"] + s["odur"]))
            if sn == "mountain_storm":
                ev["wind"].append((s["ot0"], s["ot0"] + s["odur"])); ev["thunder"] += [s["ot0"] + f for f in s["tm"]["flashes"]]
            if sn == "fire_rain": ev["rumble"].append((s["ot0"], s["ot0"] + s["odur"])); ev["impact"].append(s["ot0"] + .1)
            if sn in ("counter", "icon_grid"): ev["tick"] += [s["ot0"] + .2 + q * .07 for q in range(int(min(s["odur"] * .6, 2.4) / .07))]
            if sn in ("object", "split_compare", "crowd"): ev["impact"].append(s["ot0"] + .15)
    for k, t in pin_t.items(): ev["place"].append(t)
    for c in caps:
        if c["kt"] is not None: ev["kwpop"].append(c["kt"] - .02)
    for i, b in enumerate(beats):
        if b.get("reveal"): ev["softimpact"].append(cut[i] + .12)
    for s_ in shots:
        if s_.get("wow") and s_["trans"] != "zoomfade": ev["whoosh"].append(s_["t0"])
    m = []
    for a_, b_ in sorted(ev["wind"]):
        if m and a_ <= m[-1][1] + .05: m[-1] = (m[-1][0], max(m[-1][1], b_))
        else: m.append((a_, b_))
    ev["wind"] = m
    tiles = []
    if beats[-1]["shot"] == "PRESENTER":
        lw = WORDS[-1]; lt_ = norm(beats[-1]["text"])
        for k in place_mentions(beats[-1]["text"], places)[:5]:
            p = places[k]; cands = [norm(k)] + [w for w in re.findall(r"[a-z]{4,}", norm(p["label"])) if w not in ("mount", "mountain", "site", "river", "city", "lake", "valley")]
            for c_ in cands:
                tt, wi = _find_word(lw, c_)
                if tt is not None:
                    tiles.append((re.sub(r"[^\w'-]", "", lw[wi][0]).upper(), k, float(tt))); break
    return dict(tiles=tiles, shots=shots, words=WORDS, cut=cut, total=TOTAL, pin_t={k: float(v) for k, v in pin_t.items()}, pin_order=pin_order, acts=acts, sfx=ev, ezra_share=share(), nsub=nsub,
                caps=caps, kws=kws, kw_times=[c['kt'] for c in caps if c['kt'] is not None], reveals=[(cut[i], cut[i + 1], b['reveal']) for i, b in enumerate(beats) if b.get('reveal')])
