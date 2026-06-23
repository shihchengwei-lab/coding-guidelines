"""Secondary index: for each indexed field, value -> set of ids.

The index must stay consistent with primary storage: every (field, value) the
store holds for a live record should map to that record's id, and nothing else.
"""


class Index:
    def __init__(self, fields):
        self._map = {field: {} for field in fields}

    def indexes(self, field):
        """Whether this field is indexed at all."""
        return field in self._map

    def add(self, field, value, rid):
        if field not in self._map:
            return
        self._map[field].setdefault(value, set()).add(rid)

    def remove(self, field, value, rid):
        if field not in self._map:
            return
        bucket = self._map[field].get(value)
        if not bucket:
            return
        bucket.discard(rid)
        if not bucket:
            del self._map[field][value]

    def lookup(self, field, value):
        if field not in self._map:
            return set()
        return set(self._map[field].get(value, set()))
