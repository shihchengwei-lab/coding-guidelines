"""Primary storage: id -> record.

Every record handed out or taken in is copied (see record.copy_record), so the
value returned by get() is a snapshot the caller may freely mutate without
affecting what is stored.
"""
from record import copy_record


class Storage:
    def __init__(self):
        self._rows = {}

    def put(self, rid, record):
        self._rows[rid] = copy_record(record)

    def get(self, rid):
        """Return a COPY of the stored record, or None if absent."""
        return copy_record(self._rows.get(rid))

    def delete(self, rid):
        self._rows.pop(rid, None)

    def exists(self, rid):
        return rid in self._rows

    def all_ids(self):
        return list(self._rows.keys())
