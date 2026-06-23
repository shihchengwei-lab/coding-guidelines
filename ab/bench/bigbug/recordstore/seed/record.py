"""A record is a plain mapping of field name -> value, plus helpers.

Records are always copied when they cross a boundary so that callers can never
mutate what is held inside the store.
"""


def make_record(fields):
    """Build a record from a dict-like set of fields."""
    return dict(fields)


def copy_record(record):
    """Return an independent copy of a record (or None)."""
    if record is None:
        return None
    return dict(record)


def fields_of(record):
    """Yield (field, value) pairs of a record."""
    return list(record.items())
