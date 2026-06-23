"""Fractional grader for lru_cache. Prints `SCORE k n`.

Runs the canonical LRU trace; each expected get() is one sub-test.
"""
import sys

sys.path.insert(0, sys.argv[1])
import lru  # noqa: E402


def main():
    passed = 0
    total = 0

    def check(got, expected):
        nonlocal passed, total
        total += 1
        if got == expected:
            passed += 1

    try:
        c = lru.LRUCache(2)
        c.put(1, 1)
        c.put(2, 2)
        check(c.get(1), 1)        # 1 is now most-recent
        c.put(3, 3)               # evicts least-recent (2)
        check(c.get(2), None)
        c.put(4, 4)               # evicts least-recent (1)
        check(c.get(1), None)
        check(c.get(3), 3)
        check(c.get(4), 4)
    except Exception:
        pass

    try:
        d = lru.LRUCache(2)
        d.put(1, 1)
        d.put(2, 2)
        d.put(1, 10)              # update refreshes recency of 1
        d.put(3, 3)               # evicts 2, not 1
        check(d.get(2), None)
        check(d.get(1), 10)
        check(d.get(3), 3)
    except Exception:
        pass

    # Ensure we always emit the full denominator even if construction failed.
    if total < 8:
        total = 8
    print(f"SCORE {passed} {total}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
