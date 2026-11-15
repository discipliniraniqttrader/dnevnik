#!/usr/bin/env python3
"""MythUnearthed Short engine: one script.json -> finished 1080x1920 Short.

  python3 make_short.py <topic_dir>                  # full render -> <topic_dir>/out/<topic>.mp4 (+ _9mb.mp4, _sheet.png, report.json)
  python3 make_short.py <topic_dir> --frames 3,12.5  # preview PNGs only -> <topic_dir>/out/frames/
  python3 make_short.py <topic_dir> --no-9mb         # skip the HEVC two-pass encode
  python3 make_short.py <topic_dir> --region noah    # reuse an existing assets/terrain_<name> instead of the auto region

Stages and caches (all under <topic_dir>): voice/ (Chatterbox raw + stretch), cache/ (narration, plan, ezra_<hash>/), assets/terrain_auto_* (shared).
"""
import hashlib, json, math, multiprocessing as mp, os, pickle, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"): print(__doc__); sys.exit(1)
    topic = Path(args[0]).resolve()
    opt = lambda k: args[args.index(k) + 1] if k in args else None
    import numpy as np, soundfile as sf
    from shortkit import script as SC, terrain, voice as VO, plan as PL, ezra as EZ, sfx, compose, encode
    from shortkit.common import FPS
    T = {}; t00 = time.time()
    def stage(name, t0): T[name] = round(time.time() - t0, 1); print(f"[{name}] {T[name]}s", flush=True)

    out = topic / "out"; cache = topic / "cache"; out.mkdir(exist_ok=True); cache.mkdir(exist_ok=True)
    name = topic.name
    t0 = time.time(); S = SC.load(topic); stage("script", t0)
    for w in S["warnings"]: print("WARN", w)
    beats = S["beats"]

    # ---- terrain (overlaps with TTS)
    region, tproc = None, None
    if any(b["shot"] == "MAP" for b in beats):
        region = terrain.plan_region(S["places"])
        if opt("--region"):
            m = json.load(open(ROOT / "assets" / f"terrain_{opt('--region')}.json")); region.update(name=opt("--region"), lat0=m["lat0"], lat1=m["lat1"], lon0=m["lon0"], lon1=m["lon1"])
        tproc = terrain.start_build(region)
    else:
        region = dict(name="", vis_wide=5, lat0=0, lat1=0, lon0=0, lon1=0)

    # ---- voice
    t0 = time.time(); VO.generate(topic, beats, S); stage("voice_tts", t0)
    t0 = time.time(); voice, BT, TOTAL = VO.narrate(topic, beats, cache); stage("narration", t0)
    if tproc is not None:
        t0 = time.time()
        if tproc.wait() != 0: raise SystemExit("terrain build failed")
        stage("terrain_wait", t0)

    # ---- plan
    t0 = time.time(); P = PL.build(S, voice, BT, TOTAL, region); stage("plan", t0)
    nframes = int(math.ceil(TOTAL * FPS))

    # ---- Ezra
    preview = opt("--frames") is not None
    t0 = time.time(); ezra_dir, nz, rendered = EZ.ensure(cache, voice, TOTAL, P["acts"], render=(not preview) or ("--ezra" in args)); stage("ezra" + ("" if rendered else "_cached"), t0)
    D = dict(S=S, plan=P, region=region["name"], ezra_dir=str(ezra_dir), NF=nz, BT=BT, TOTAL=TOTAL)
    pkl = cache / "plan.pkl"; tmpk = cache / "plan.pkl.tmp"; pickle.dump(D, open(tmpk, "wb")); os.replace(tmpk, pkl)

    if preview:
        t0 = time.time()
        for p in compose.render_preview(str(pkl), [float(x) for x in opt("--frames").split(",")], out / "frames"): print(p)
        stage("preview", t0); return

    # ---- audio
    t0 = time.time(); audio = sfx.mix(voice, TOTAL, P["sfx"]); wav = cache / "audio.wav"; sf.write(wav, audio, VO.SR); stage("audio", t0)

    # ---- frames (spawn pool). Resumable: chunks already rendered for THIS plan+code (key) are validated with ffprobe and skipped.
    t0 = time.time()
    step = 75
    key = hashlib.sha1(open(pkl, "rb").read() + b"".join(p_.read_bytes() for p_ in sorted((ROOT / "shortkit").glob("*.py")))
                       + f"{nframes}|{FPS}".encode()).hexdigest()[:16]
    for q in cache.glob("_part*.tmp.mp4"): q.unlink(missing_ok=True)                      # unfinished chunk from a crashed run
    jobs = [(i, f0, min(nframes, f0 + step), str(cache), key) for i, f0 in enumerate(range(0, nframes, step))]
    parts, means, mints, reused = [], [], [], 0
    with mp.get_context("spawn").Pool(4, initializer=compose.init_worker, initargs=(str(pkl),)) as pool:
        for k, (path, mn, mt, skipped) in enumerate(pool.imap(compose.render_chunk, jobs, chunksize=1)):
            parts.append(path); means += mn; mints.append(mt); reused += bool(skipped)
            print(f"  chunk {k + 1}/{len(jobs)}  {time.time() - t0:.0f}s{'  (reused)' if skipped else ''}", flush=True)
    stage("frames", t0)
    t0 = time.time(); final = out / f"{name}.mp4"; tmpf = out / f"{name}.tmp.mp4"; encode.mux(parts, wav, tmpf, cache); os.replace(tmpf, final); stage("mux", t0)

    # ---- guards
    m = np.array(means); jumps = np.abs(np.diff(m)); jmax = float(jumps.max()) if len(jumps) else 0.0; jt = float((int(jumps.argmax()) + 1) / FPS) if len(jumps) else 0.0
    shots = P["shots"]; n_shots = len(shots); warns = list(S["warnings"]); dur_s = nframes / FPS
    avg_shot = TOTAL / n_shots; sd = [s_["dur"] for s_ in shots[:-1]] if n_shots > 1 else []        # the end card holds long on purpose
    off = [round(x, 2) for x in sd if x < 1.15 or x > 2.1]
    min_text = float(min(mints)) if mints else 0.0
    if not (40 <= dur_s <= 50): warns.append(f"DURATION {dur_s:.1f}s outside 40-50s")
    if jmax > 15: warns.append(f"FLICKER max frame-to-frame brightness jump {jmax:.1f} at {jt:.2f}s > 15")
    if avg_shot > 2.0: warns.append(f"avg shot {avg_shot:.2f}s > 2s")
    if P["ezra_share"] < .35: warns.append(f"Ezra on screen only {P['ezra_share'] * 100:.0f}% of the time (<35%)")
    if min_text < 44: warns.append(f"smallest overlay text {min_text:.0f}px < 44px")
    words = sum(len(b["text"].split()) for b in beats)
    if not (100 <= words <= 135): warns.append(f"word count {words} outside 100-135")

    # ---- 9 MB HEVC + sheet
    small = out / f"{name}_9mb.mp4"; size9 = None
    if "--no-9mb" not in args:
        t0 = time.time(); size9, vb = encode.encode_9mb(final, small, TOTAL, cache); stage("encode_9mb", t0)
        if size9 >= 10_000_000: warns.append("9mb file still >= 10 MB")
    t0 = time.time(); encode.contact_sheet(final, out / f"{name}_sheet.png", TOTAL); stage("sheet", t0)
    T["total"] = round(time.time() - t00, 1)
    rep = dict(topic=name, title=S["title"], duration_s=round(nframes / FPS, 2), narration_s=round(TOTAL, 2), shot_count=n_shots, avg_shot_s=round(avg_shot, 2),
               shots_outside_1p2_2p0=off, wow_shots=sum(1 for s_ in shots if s_.get("wow")), keywords=[k_ for k_ in P["kws"] if k_["word"]],
               min_text_px=round(min_text, 1), chunks=len(jobs), chunks_reused=reused, improvements=S.get("improvements", []),
               max_brightness_jump=round(jmax, 2), max_jump_at_s=round(jt, 2), words=words, ezra_share=round(P["ezra_share"], 3),
               say_beats=[b["i"] for b in beats if b["used_say"]], beats=len(beats), region=region["name"], mp4_bytes=final.stat().st_size, mp4_9mb_bytes=size9,
               warnings=warns, stage_seconds=T)
    json.dump(rep, open(out / "report.json", "w"), indent=2)
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
