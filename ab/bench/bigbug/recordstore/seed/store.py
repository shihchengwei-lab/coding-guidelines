"""Store: keeps primary storage and the secondary index consistent.

insert / delete maintain the index; update must too, so that querying by an old
field value never returns a record that has since changed.
"""
from storage import Storage
from index import Index
from errors import DuplicateId, MissingId


class Store:
    def __init__(self, indexed_fields):
        self.storage = Storage()
        self.index = Index(indexed_fields)

    def insert(self, rid, record):
        if self.storage.exists(rid):
            raise DuplicateId(rid)
        self.storage.put(rid, record)
        for field, value in record.items():
            if self.index.indexes(field):
                self.index.add(field, value, rid)

    def update(self, rid, changes):
        record = self.storage.get(rid)
        if record is None:
            raise MissingId(rid)
        for field, value in changes.items():
            if self.index.indexes(field):
                self.index.add(field, value, rid)
            record[field] = value
        self.storage.put(rid, record)

    def delete(self, rid):
        record = self.storage.get(rid)
        if record is None:
            return
        for field, value in record.items():
            if self.index.indexes(field):
                self.index.remove(field, value, rid)
        self.storage.delete(rid)

    def get(self, rid):
        return self.storage.get(rid)

    def query_by(self, field, value):
        return sorted(self.index.lookup(field, value))
