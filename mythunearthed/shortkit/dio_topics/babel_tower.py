SCENES = [("bab_site", [1, 2, 3]), ("bab_size", [4, 5, 6, 7, 8, 9]), ("bab_end", [10, 11, 12, 13, 14])]
OV = {
    1: [dict(k="dim", a="H0", b="H1", off=(150, 0), label="91 M", t0=0.9, d=1.0, counter=(0, 91, " M", 0))],
    2: [dict(k="callout", a="brick", label="BAKED BRICKS", box=(0, -300), t0=0.6, t1=3.2)],
    3: [dict(k="callout", a="top", label="ETEMENANKI", box=(0, -300), t0=0.6, t1=3.2)],
    4: [dict(k="dim", a="W0", b="W1", off=(0, 160), label="91 M SQUARE", t0=2.0, d=1.0)],
    5: [dict(k="dim", a="H0", b="H1", off=(160, 0), label="91 M TALL", t0=0.5, d=1.2, counter=(0, 91, " M TALL", 0))],
    6: [dict(k="dim", a="hr0", b="hr1", off=(-170, 0), label="30 FLOORS", t0=0.9, d=1.0)],
    7: [dict(k="callout", a="scaf", label="~600 BC", box=(0, -300), t0=0.6, t1=3.2)],
    8: [dict(k="callout", a="floors", label="FLOOR 30", box=(-120, -200), t0=0.3, t1=3.4, counter=(1, 30, " FLOORS", 0), cd=3.0)],
    9: [dict(k="callout", a="temple", label="7 STAGES", box=(0, -300), t0=0.4, t1=3.4, counter=(0, 7, " STAGES", 0), cd=2.6)],
    10: [dict(k="callout", a="soldier", label="~330 BC", box=(0, -300), t0=0.6, t1=3.2)],
    11: [dict(k="callout", a="stand", label="LANGUAGE CONFUSED", box=(0, -300), t0=0.6, t1=3.4)],
    12: [dict(k="dim", a="pitA", b="pitB", off=(0, 140), label="FOUNDATION PIT", t0=0.8, d=1.0)],
    13: [dict(k="callout", a="fogP", label="NOT PROVEN", box=(0, -300), t0=0.5, t1=3.0)],
    14: [],
}
KW = {}
AUDIO = dict()
GAP = 0.3
TAIL = 0
