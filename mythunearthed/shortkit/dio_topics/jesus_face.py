SCENES = [("jes_stage", list(range(1, 13)))]
OV = {
    1: [dict(k="callout", a="paint", label="NOT YOUR PAINTING", box=(0, -300), t0=0.6, t1=3.2)],
    2: [dict(k="callout", a="blank", label="NO DESCRIPTION", box=(0, -300), t0=0.6, t1=3.0)],
    3: [dict(k="callout", a="clayA", label="2001", box=(0, -300), t0=0.6, t1=3.4, counter=(1990, 2001, "", 0), cd=1.0)],
    4: [dict(k="callout", a="skullA", label="1ST-CENTURY SKULL", box=(0, -300), t0=0.6, t1=3.2)],
    5: [dict(k="callout", a="faceA", label="BROAD FACE", box=(0, 340), t0=0.6, t1=3.6)],
    6: [dict(k="callout", a="wellA", label="SHORT HAIR", box=(0, -300), t0=0.8, t1=3.4)],
    7: [dict(k="dim", a="dh", b="dt", off=(-190, 0), label="1.55 M", t0=0.5, d=0.9), dict(k="callout", a="dt", label="50 KG", box=(150, -250), t0=1.8, t1=3.6, counter=(0, 50, " KG", 0), cd=1.0)],
    8: [dict(k="dim", a="mf", b="mh", off=(190, 0), label="TALLER", t0=0.8, d=0.9)],
    9: [dict(k="callout", a="hillA", label="WORDS, NOT LOOKS", box=(0, 330), t0=0.6, t1=3.6)],
    10: [dict(k="callout", a="facesA", label="AVERAGE FACE", box=(0, -300), t0=0.8, t1=3.4)],
    11: [dict(k="callout", a="carA", label="WORKING MAN OF GALILEE", box=(0, -300), t0=0.6, t1=3.6)],
    12: [],
}
KW = {}
AUDIO = dict()
GAP = 0.3
TAIL = 0.9
