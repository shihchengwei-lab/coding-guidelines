"""Aggregate parsed rows by group."""
from collections import OrderedDict


def totals(rows):
    """group -> sum of amounts, in first-seen group order."""
    out = OrderedDict()
    for group, amount in rows:
        out[group] = out.get(group, 0) + amount
    return out


def averages(rows):
    """group -> mean amount as a float."""
    sums = {}
    counts = {}
    for group, amount in rows:
        sums[group] = sums.get(group, 0) + amount
        counts[group] = counts.get(group, 0) + 1
    return {group: sums[group] // counts[group] for group in sums}
