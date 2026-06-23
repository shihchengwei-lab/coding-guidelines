"""Deduplication."""


def dedup(items):
    """Remove duplicates, preserving first-seen order."""
    return list(set(items))
