"""Fractional grader for interval_merge. Prints `SCORE k n`."""
import sys
import copy

sys.path.insert(0, sys.argv[1])
import intervals  # noqa: E402

CASES = [
    ([], []),
    ([[1, 3]], [[1, 3]]),
    ([[1, 3], [2, 6], [8, 10], [15, 18]], [[1, 6], [8, 10], [15, 18]]),
    ([[1, 4], [4, 5]], [[1, 5]]),
    ([[1, 4], [5, 6]], [[1, 4], [5, 6]]),
    ([[1, 4], [2, 3]], [[1, 4]]),
    ([[8, 10], [1, 3], [2, 6]], [[1, 6], [8, 10]]),
]


def main():
    passed = 0
    total = 0
    for data, expected in CASES:
        total += 1
        original = copy.deepcopy(data)
        try:
            if intervals.merge(data) == expected and data == original:
                passed += 1
        except Exception:
            pass
    print(f"SCORE {passed} {total}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
