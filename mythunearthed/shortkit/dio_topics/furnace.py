SCENES = [("fur_night", list(range(1, 13)))]
OV = {
    1: [dict(k="callout", a="flame", label="x7 ?", box=(0, 330), t0=0.4, t1=2.6), dict(k="cross", a="flame", t0=1.0, t1=2.7)],
    2: [dict(k="callout", a="king", label="HEAT IT x7", box=(0, -300), t0=0.8, t1=3.2)],
    3: [dict(k="callout", a="brickS", label="900-1000 C", box=(0, -300), t0=0.6, t1=3.3)],
    4: [dict(k="callout", a="ovenA", label="250 C", box=(0, -300), t0=0.5, t1=3.0, counter=(20, 250, " C", 0), cd=1.5)],
    5: [dict(k="callout", a="colA", label="6,300 C", box=(0, 330), t0=0.6, t1=3.6, counter=(0, 6300, " C", 0), cd=2.2)],
    6: [dict(k="callout", a="thA", label="6,300 C", box=(-60, -280), t0=0.5, t1=3.5), dict(k="callout", a="thB", label="SUN 5,500 C", box=(60, 320), t0=1.2, t1=3.5)],
    7: [dict(k="callout", a="tabA", label="7 = FULL", box=(0, -300), t0=1.0, t1=3.4)],
    8: [dict(k="callout", a="men", label="3 MEN", box=(0, -300), t0=0.6, t1=3.4, counter=(0, 3, " MEN", 0), cd=1.0)],
    9: [dict(k="callout", a="mouth", label="FLAMES KILL THE SOLDIERS", box=(0, -340), t0=0.8, t1=3.4)],
    10: [dict(k="callout", a="four", label="4 MEN WALKING", box=(0, -330), t0=0.6, t1=3.6)],
    11: [dict(k="callout", a="tab2", label="NO RECORD", box=(0, -300), t0=0.6, t1=3.4)],
    12: [],
}
KW = {10: "walking"}
AUDIO = dict()
GAP = 0.3
TAIL = 2.2
