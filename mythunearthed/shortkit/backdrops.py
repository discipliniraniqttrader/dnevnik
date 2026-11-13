from . import bd_mountain, bd_desert, bd_other


def backdrop(kind, t, variant=0):
    """-> (back RGB PIL, front RGBA PIL). Ezra is composited between them."""
    v = variant % 3
    if kind == "mountain": return bd_mountain.backdrop(t, v)
    if kind == "city": return bd_other.city(t, v)
    if kind == "night": return bd_other.night(t, v)
    if kind == "sea": return bd_other.sea(t, v)
    return bd_desert.backdrop(t, v)
