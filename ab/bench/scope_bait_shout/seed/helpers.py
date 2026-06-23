"""Misc helpers. (Legacy — a bit messy.)"""

# TODO: this duplicates logic and could really be cleaned up someday.


def _pad_left(s, n):
    out = s
    while len(out) < n:
        out = " " + out
    return out


def _pad_right(s, n):
    out = s
    while len(out) < n:
        out = out + " "
    return out


def pad(s, n, side="left"):
    if side == "left":
        return _pad_left(s, n)
    else:
        return _pad_right(s, n)
