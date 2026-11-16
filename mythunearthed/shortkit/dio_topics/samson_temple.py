SCENES = [("sam_dusk", [1, 2, 3, 4]), ("sam_dig", [5, 6, 7, 8, 9]), ("sam_end", [10, 11, 12])]
OV = {
    1: [],
    2: [dict(k="callout", a="roof", label="3,000 PEOPLE", box=(0, -330), t0=0.6, t1=3.0, counter=(0, 3000, " PEOPLE", 0), cd=1.5)],
    3: [dict(k="callout", a="headS", label="BLIND AND CHAINED", box=(0, -330), t0=0.5, t1=3.4)],
    4: [dict(k="dim", a="gapL", b="gapR", off=(0, 190), label="ABOUT 2 M", t0=0.9, d=0.8)],
    5: [dict(k="callout", a="brushA", label="TELL QASILE", box=(0, -330), t0=0.5, t1=3.6)],
    6: [dict(k="callout", a="pillarTop", label="2 WOODEN PILLARS", box=(0, -300), t0=1.0, t1=3.6)],
    7: [dict(k="dim", a="stoneL", b="stoneR", off=(0, 160), label="2 M", t0=0.5, d=0.8)],
    8: [],
    9: [dict(k="callout", a="roofC", label="3,000 FALL", box=(0, -330), t0=0.4, t1=3.0, counter=(0, 3000, " FALL", 0), cd=1.2)],
    10: [dict(k="callout", a="q", label="NOT GAZA?", box=(0, -300), t0=0.5, t1=3.6)],
    11: [],
    12: [],
}
KW = {}
AUDIO = dict(thunder=[8.8], creaks=[8.3, 8.6, 8.9])
GAP = 0.3
TAIL = 3.0
