"""topics/ark_size: 13 beats grouped into 7 scenes (>= 4.5 s each). OV = anchored overlays per beat (t0/t1 relative to beat start)."""
SCENES = [("ark_yard", [1, 2]), ("ark_forearm", [3]), ("ark_field", [4, 5]), ("ark_inside", [6, 7]), ("ark_ships", [8, 9]), ("ark_storm", [10, 11]), ("ark_end", [12, 13])]
OV = {
    1: [dict(k="callout", a="boat", label="CUTE LITTLE BOAT?", box=(0, -420), t0=0.12, t1=1.15), dict(k="cross", a="boat", t0=0.55, t1=1.25), dict(k="callout", a="arkMid", label="NOAH'S ARK", box=(0, 360), t0=1.45, t1=2.09)],
    2: [dict(k="dim", a="L0", b="L1", off=(0, 120), label="300 CUBITS", t0=0.3, d=0.7), dict(k="dim", a="H0", b="H1", off=(150, 0), label="30", t0=1.3, d=0.6), dict(k="dim", a="W0", b="W1", off=(-60, -230), label="50", t0=2.3, d=0.6)],
    3: [dict(k="dim", a="tip", b="elbow", off=(-190, 0), label="45 CM", t0=2.2, d=0.8), dict(k="callout", a="tip", label="1 CUBIT = 1 FOREARM", box=(0, 330), t0=0.4, t1=2.2)],
    4: [dict(k="dim", a="L0", b="L1", off=(0, -110), label="137 M", t0=0.2, d=1.4, counter=(0, 137, " M"))],
    5: [dict(k="dim", a="f0", b="f1", off=(0, 120), label="1 FIELD", t0=0.2, d=0.6), dict(k="dim", a="a0", b="a1", off=(0, -90), label="1.5 FIELDS", t0=1.7, d=0.7), dict(k="callout", a="person", label="YOU", box=(150, -150), t0=0.1, t1=1.4)],
    6: [dict(k="callout", a="d2", label="3 DECKS", box=(-10, -330), t0=0.5, t1=3.0), dict(k="callout", a="door", label="ONE DOOR", box=(120, 260), t0=2.0, t1=3.0), dict(k="callout", a="roof", label="OPENING", box=(-60, -230), t0=2.5, t1=3.05)],
    7: [dict(k="dim", a="P0", b="P1", off=(0, -70), label="6", t0=0.15, d=0.5), dict(k="dim", a="Q0", b="Q1", off=(110, 0), label="1", t0=0.7, d=0.4)],
    8: [dict(k="callout", a="ark", label="ARK  6 : 1", box=(0, -260), t0=0.5, t1=4.0), dict(k="callout", a="cargo", label="CARGO SHIP  6 : 1", box=(0, 280), t0=1.5, t1=4.0)],
    9: [dict(k="dim", a="a0", b="a1", off=(0, 110), label="137 M", t0=0.9, d=0.6), dict(k="dim", a="t0", b="t1", off=(0, -110), label="269 M", t0=1.3, d=0.7)],
    10: [dict(k="callout", a="seam", label="LEAKS!", box=(0, -300), t0=0.5, t1=2.8)],
    11: [dict(k="callout", a="mast6", label="6 MASTS", box=(0, 250), t0=0.4, t1=2.2), dict(k="callout", a="pump", label="PUMPS NON-STOP", box=(0, 280), t0=2.6, t1=4.0)],
    12: [dict(k="callout", a="peak", label="NO TRACE FOUND", box=(0, 330), t0=0.5, t1=2.7)],
    13: [],
}
AUDIO = dict(rain=[(1, 0.6), (10, 0.6), (10.5, 1.0), (12, 1.0), (12.5, 0.55), (14, 0.7)], thunder=[2.6, 6.8, 10.9, 13.3], creaks=[1.2, 1.7, 2.2, 2.7, 4.3, 4.8, 6.3, 6.8, 10.2, 10.7])
