"""script + narration timeline -> shot plan (+ Ezra actions, SFX events). Pure data, picklable."""
import math, re
from .common import FPS
from .script import GAZ, ZOOMS, norm, place_mentions
from .voice import word_times

NT_BEAT, NT_SUB = 12, 9          # transition length in frames (beat boundary / sub-shot cut)
CORNER_SCENES = ("object", "aerial", "tablet", "birds", "sea_parting", "mountain_storm", "fire_rain", "manna")


def _find_word(words, key, start=0):
    """time of first word (index >= start) whose normalised text starts with key"""
    k = norm(key).strip()
    for i in range(start, len(words)):
        w = re.sub(r"[^a-z0-9\-']", "", norm(words[i][0]))
        if w.startswith(k) and k: return words[i][1], i
    return None, None


def build(S, voice, BT, TOTAL, region):
    beats = S["beats"]; n = len(beats); places = S["places"]
    WORDS = [word_times(b["text"], bt["t0"], bt["speech"], voice) for b, bt in zip(beats, BT)]
    cut = [0.0] + [BT[i]["t0"] - 0.08 for i in range(1, n)] + [TOTAL]          # beat i spans cut[i]..cut[i+1]
    dur = [cut[i + 1] - cut[i] for i in range(n)]
    # ---------------- shots per beat: avg shot <= ~1.9 s (end card is one shot)
    nsub = []
    for i, b in enumerate(beats):
        last_end = (i == n - 1 and b["shot"] == "PRESENTER")
        nsub.append(1 if (last_end or dur[i] <= 2.3) else int(math.ceil(dur[i] / 2.1)))
    def avg(): return TOTAL / sum(nsub)
    guard = 0
    while avg() > 1.9 and guard < 200:
        guard += 1
        cand = [(dur[i] / nsub[i], i) for i in range(n) if nsub[i] < 4 and not (i == n - 1 and beats[i]["shot"] == "PRESENTER") and dur[i] / nsub[i] > 1.3]
        if not cand: break
        nsub[max(cand)[1]] += 1
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
            ws = [w[1] for w in words if abs(w[1] - ideal) < .4 and w[1] > bounds[-1] + .9 and w[1] < e - .9]
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
                sh = dict(base, kind="map", t0=t0_, t1=t1_, sub=k, cam=(A_, B_), arc=arc, ezra=side, wide=wide, pins=pins_now,
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
    # ---------------- Ezra share (>=30%): add corner Ezra on suitable event shots
    def share():
        return sum(s["dur"] for s in shots if s["kind"] in ("presenter", "end") or s.get("ezra")) / TOTAL
    if share() < .32:
        side = "left"
        for s in shots:
            if share() >= .32: break
            if s["kind"] == "event" and beats[s["beat"] - 1]["scene_name"] in CORNER_SCENES and s["beat"] > 1:
                side = "right" if side == "left" else "left"; s["ezra"] = side
    for j, s in enumerate(shots):
        s["ezra_slide"] = bool(s.get("ezra") and not (j and shots[j - 1].get("ezra") == s["ezra"] and shots[j - 1]["beat"] == s["beat"]))
        sc = []
        if s.get("stamp"): sc.append((s["stamp"][2], 5, .3))
        if s.get("callout"): sc.append((s["callout"][1], 3, .2))
        if s["kind"] == "text" and beats[s["beat"] - 1].get("kind") == "word_shatter": sc.append((s["ot0"] + s["tm"]["t_shatter"], 7, .4))
        s["shakes"] = sc
    # ---------------- Ezra actions
    acts = []
    for i, b in enumerate(beats):
        ss = [s for s in shots if s["beat"] == i + 1]
        if b["shot"] == "PRESENTER": acts.append((cut[i] + .1, dur[i] - .1, b["action"]))
        else:
            side = next((s["ezra"] for s in ss if s.get("ezra")), None)
            if side: acts.append((cut[i] + .15, dur[i] - .15, "point_right" if side == "left" else "point_left"))
    # ---------------- SFX
    ev = {k: [] for k in ("whoosh", "whip", "impact", "pop", "place", "tick", "flap", "birdwhoosh", "shatter", "shimmer", "wind", "ocean", "thunder", "rumble")}
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
    return dict(tiles=tiles, shots=shots, words=WORDS, cut=cut, total=TOTAL, pin_t={k: float(v) for k, v in pin_t.items()}, pin_order=pin_order, acts=acts, sfx=ev, ezra_share=share(), nsub=nsub)
