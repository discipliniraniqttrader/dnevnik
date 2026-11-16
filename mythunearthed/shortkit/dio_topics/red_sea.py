SCENES = [("red_cross", [1, 2, 3]), ("red_plain", [4, 5, 6]), ("red_front", [7, 8, 9]), ("red_reeds", [10, 11, 12])]
OV = {
    1: [dict(k="callout", a="crowd", label="2,000,000", box=(0, -320), t0=0.5, t1=2.6, counter=(0, 2000000, "", 0), cd=1.5)],
    2: [dict(k="callout", a="men", label="600,000 MEN", box=(0, -320), t0=0.6, t1=3.2, counter=(0, 600000, " MEN", 0), cd=1.4)],
    3: [dict(k="callout", a="fam", label="ABOUT 2 MILLION", box=(0, -320), t0=0.8, t1=4.2)],
    4: [dict(k="callout", a="bigGrid", label="80,000 x 25", box=(0, -300), t0=1.0, t1=4.0)],
    5: [dict(k="callout", a="colA", label="10 ABREAST = 200 KM", box=(0, -330), t0=0.8, t1=4.2)],
    6: [dict(k="callout", a="clockA", label="48 HOURS", box=(0, -330), t0=0.6, t1=3.6, counter=(0, 48, " HOURS", 0), cd=2.6)],
    7: [dict(k="dim", a="f0", b="f1", off=(120, 0), label="1 KM WIDE", t0=0.8, d=1.2)],
    8: [dict(k="callout", a="clans", label="600 CLANS", box=(0, -300), t0=0.6, t1=3.6)],
    9: [dict(k="callout", a="bandA", label="A FEW THOUSAND", box=(0, -300), t0=0.8, t1=3.6)],
    10: [dict(k="callout", a="reedA", label="YAM SUPH = SEA OF REEDS", box=(0, 330), t0=0.6, t1=3.4)],
    11: [dict(k="callout", a="prints", label="WHERE? UNKNOWN", box=(0, -330), t0=0.6, t1=3.4)],
    12: [],
}
KW = {}
AUDIO = dict(rain=[(1, 0.0), (13, 0.0)])
GAP = 0.3
TAIL = 1.9
DIPLEN = 1.1
