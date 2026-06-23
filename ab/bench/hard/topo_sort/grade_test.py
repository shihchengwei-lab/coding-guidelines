"""Fractional grader for topo_sort. Prints `SCORE k n`."""
import sys

sys.path.insert(0, sys.argv[1])
import topo  # noqa: E402

RAISES = object()
CASES = [
    ({}, []),
    ({"a": []}, ["a"]),
    ({"a": [], "b": ["a"]}, ["a", "b"]),
    ({"b": ["a"], "a": [], "c": ["a"]}, ["a", "b", "c"]),
    ({"a": [], "b": ["a"], "c": ["b"], "d": ["a"]}, ["a", "b", "c", "d"]),
    ({"a": ["b"], "b": ["a"]}, RAISES),
    ({"a": ["a"]}, RAISES),
]


def main():
    passed = 0
    for graph, expected in CASES:
        try:
            got = topo.topo_sort(graph)
            ok = expected is not RAISES and got == expected
        except ValueError:
            ok = expected is RAISES
        except Exception:
            ok = False
        if ok:
            passed += 1
    print(f"SCORE {passed} {len(CASES)}")
    sys.exit(0 if passed == len(CASES) else 1)


if __name__ == "__main__":
    main()
