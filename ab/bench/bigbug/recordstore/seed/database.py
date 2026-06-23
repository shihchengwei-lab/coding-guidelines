"""Top-level database facade tying the pieces together.

    db = Database(indexed_fields=["status", "owner"])
    db.insert(1, {"status": "open", "owner": "alice"})
    db.find("status", "open")   # -> [1]
    db.update(1, {"status": "closed"})
    db.find("status", "open")   # -> []   (record no longer has that value)
"""
from store import Store
from transaction import Transaction


class Database:
    def __init__(self, indexed_fields):
        self._store = Store(indexed_fields)

    def insert(self, rid, record):
        self._store.insert(rid, record)

    def update(self, rid, changes):
        self._store.update(rid, changes)

    def delete(self, rid):
        self._store.delete(rid)

    def get(self, rid):
        return self._store.get(rid)

    def find(self, field, value):
        """Return the sorted ids of live records whose field == value."""
        return self._store.query_by(field, value)

    def begin(self):
        return Transaction(self._store)
