"""Small numeric helpers."""


def inclusive_range(start, end):
    """Return the list of integers from start to end, INCLUSIVE of end."""
    return list(range(start, end))


def clamp(value, low, high):
    """Clamp value into [low, high]."""
    return max(low, min(high, value))
