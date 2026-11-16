SCENES = [("whale_sea", [1, 2]), ("whale_breath", [3, 4]), ("whale_inside", [5, 6]), ("whale_ship", [7, 8]), ("whale_end", [9, 10, 11, 12])]
OV = {
    1: [dict(k="callout", a="fishHead", label="WHALE", box=(0, -330), t0=0.4, t1=2.2), dict(k="cross", a="fishHead", t0=1.0, t1=2.3)],
    2: [dict(k="callout", a="shadow", label="DAG GADOL = GREAT FISH", box=(0, -350), t0=0.5, t1=2.6)],
    3: [dict(k="callout", a="watch", label="30 S", box=(0, -320), t0=0.3, t1=3.0, counter=(0, 30, " S", 0), cd=2.6)],
    4: [dict(k="callout", a="watch", label="60 S", box=(0, -320), t0=0.2, t1=3.2, counter=(30, 60, " S", 0), cd=2.4)],
    5: [dict(k="callout", a="gauge", label="OXYGEN: LOW", box=(0, 330), t0=0.8, t1=3.3)],
    6: [dict(k="callout", a="pool", label="ACID", box=(0, -300), t0=0.4, t1=3.2)],
    7: [dict(k="callout", a="whale", label="1891", box=(0, -300), t0=0.5, t1=3.2, counter=(1800, 1891, "", 0), cd=1.2, raw=True)],
    8: [dict(k="callout", a="sailor", label="3 DAYS", box=(0, -300), t0=0.6, t1=3.4, counter=(0, 3, " DAYS", 0), cd=1.5)],
    9: [dict(k="callout", a="log", label="NO RECORD", box=(0, -300), t0=0.5, t1=3.0)],
    10: [dict(k="callout", a="lone", label="MIRACLE OR PARABLE?", box=(0, -300), t0=0.5, t1=3.6)],
    11: [dict(k="callout", a="scroll", label="LARGE SEA CREATURE", box=(0, -300), t0=0.5, t1=3.6)],
    12: [],
}
KW = {}
AUDIO = dict(rain=[(1, 0.9), (3, 0.5), (3.1, 0.0), (9, 0.0), (10, 0.0), (13, 0.0)], thunder=[1.3])
GAP = 0.3
TAIL = 0.5
