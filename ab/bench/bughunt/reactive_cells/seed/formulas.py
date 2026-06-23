"""Named operations usable in Sheet formulas."""

OPS = {
    "sum": lambda *args: sum(args),
    "diff": lambda a, b: a - b,
    "product": lambda *args: _product(args),
    "max": lambda *args: max(args),
}


def _product(args):
    result = 1
    for value in args:
        result *= value
    return result
