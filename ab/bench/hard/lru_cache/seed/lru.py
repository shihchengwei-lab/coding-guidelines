class LRUCache:
    """A fixed-capacity Least-Recently-Used cache.

    LRUCache(capacity): capacity is an int >= 1.
    get(key): return the value, or None if the key is absent. A successful get
        counts as a use (makes the key most-recently-used).
    put(key, value): insert or update. An update refreshes recency. When the
        cache exceeds capacity, evict the least-recently-used key.
    """

    def __init__(self, capacity):
        raise NotImplementedError

    def get(self, key):
        raise NotImplementedError

    def put(self, key, value):
        raise NotImplementedError
