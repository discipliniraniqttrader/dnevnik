SCENES = [("dur_flood", [1, 2, 3, 4]), ("dur_land", [5, 6, 7, 8, 9]), ("dur_window", [10, 11, 12])]
OV = {
    1: [dict(k="callout", a="arkMid", label="40 DAYS", box=(0, -300), t0=0.3, t1=2.6), dict(k="cross", a="arkMid", t0=1.2, t1=2.6)],
    2: [dict(k="callout", a="cal", label="RAINED 40 DAYS", box=(0, -300), t0=0.4, t1=3.0, counter=(0, 40, " DAYS", 0))],
    3: [dict(k="callout", a="day47", label="MONTH 2  DAY 17", box=(0, -300), t0=0.5, t1=3.6)],
    4: [dict(k="callout", a="calMid", label="150 DAYS", box=(0, -320), t0=0.4, t1=3.6, counter=(0, 150, " DAYS", 0), cd=2.2)],
    5: [],
    6: [dict(k="callout", a="raven", label="1  RAVEN", box=(0, -300), t0=0.5, t1=3.0)],
    7: [dict(k="callout", a="dove", label="DOVE  x3", box=(0, -300), t0=0.5, t1=3.2)],
    8: [dict(k="callout", a="ground", label="MONTH 2  DAY 27", box=(0, -320), t0=0.5, t1=3.4)],
    9: [dict(k="callout", a="ark", label="1 YEAR + 10 DAYS", box=(0, -320), t0=0.8, t1=3.5)],
    10: [dict(k="callout", a="person", label="365 DAYS", box=(0, -260), t0=1.2, t1=4.0, counter=(0, 365, " DAYS", 0), cd=1.8)],
    11: [dict(k="callout", a="ridge", label="GLOBAL OR LOCAL?", box=(0, 330), t0=0.5, t1=3.4)],
    12: [],
}
KW = {}
AUDIO = dict(rain=[(1, 1.0), (4.5, 0.9), (5.5, 0.15), (10, 0.0), (10.1, 0.9), (11.5, 0.5), (13, 0.0)], thunder=[1.5, 2.6])
GAP = 0.3
TAIL = 1.0
