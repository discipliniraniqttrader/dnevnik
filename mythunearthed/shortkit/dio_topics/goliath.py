SCENES = [("gol_stage", list(range(1, 13)))]
CNT = lambda v, u, d=1: (0, v, u, d)
OV = {
    1: [dict(k="callout", a="headA", label="2.9 M", box=(0, -300), t0=0.4, t1=2.4, counter=CNT(2.9, " M")), dict(k="cross", a="headA", t0=1.3, t1=2.6)],
    2: [dict(k="callout", a="scrollA", label="2.9 M", box=(0, -330), t0=0.5, t1=2.6), dict(k="callout", a="scrollB", label="2.0 M", box=(0, -330), t0=0.9, t1=2.6)],
    3: [dict(k="callout", a="scrollA", label="6.5 CUBITS", box=(0, -330), t0=0.3, t1=3.4, counter=CNT(6.5, " CUBITS"))],
    4: [dict(k="dim", a="footA", b="headA", off=(-180, 0), label="2.9 M", t0=0.3, d=1.0, counter=(0, 2.9, " M", 1))],
    5: [dict(k="callout", a="scrollB", label="4.5 CUBITS", box=(0, -330), t0=0.4, t1=3.4, counter=CNT(4.5, " CUBITS"))],
    6: [dict(k="callout", a="extra", label="SAME: 4.5", box=(0, -300), t0=0.5, t1=3.0)],
    7: [dict(k="dim", a="footB", b="headB", off=(-190, 0), label="2.0 M", t0=0.4, d=1.0, counter=(0, 2.0, " M", 1))],
    8: [dict(k="dim", a="footB", b="headB", off=(190, 0), label="2.0 M", t0=0.4, d=0.8), dict(k="dim", a="footS", b="headS", off=(-170, 0), label="1.6 M", t0=1.5, d=0.8)],
    9: [dict(k="callout", a="armor", label="57 KG", box=(0, -300), t0=0.8, t1=4.0, counter=CNT(57, " KG", 0))],
    10: [dict(k="callout", a="spearhead", label="7 KG", box=(0, -300), t0=0.6, t1=3.5, counter=CNT(7, " KG", 0))],
    11: [dict(k="callout", a="q", label="2.9 M  OR  2.0 M?", box=(0, -260), t0=0.9, t1=4.2)],
    12: [],
}
AUDIO = dict()
KW = {}
TAIL = 2.1
