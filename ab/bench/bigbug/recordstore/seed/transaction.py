"""Transactions buffer operations and apply them atomically on commit.

A transaction records the operations requested against it and replays them
through the store when committed; rollback simply discards them.
"""


class Transaction:
    def __init__(self, store):
        self._store = store
        self._ops = []
        self._open = True

    def insert(self, rid, record):
        self._ops.append(("insert", rid, dict(record)))

    def update(self, rid, changes):
        self._ops.append(("update", rid, dict(changes)))

    def delete(self, rid):
        self._ops.append(("delete", rid, None))

    def commit(self):
        if not self._open:
            raise RuntimeError("transaction already closed")
        for kind, rid, payload in self._ops:
            if kind == "insert":
                self._store.insert(rid, payload)
            elif kind == "update":
                self._store.update(rid, payload)
            elif kind == "delete":
                self._store.delete(rid)
        self._open = False

    def rollback(self):
        self._ops = []
        self._open = False
