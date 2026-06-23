"""Fractional grader for csv_aggregate. Prints `SCORE k n`.

Totals and integer-valued averages pass on the seed; fractional averages only
pass once the integer division (//) is corrected to true division.
"""
import sys

sys.path.insert(0, sys.argv[1])
import parse  # noqa: E402
import aggregate  # noqa: E402


def main():
    passed = 0
    total = 0

    def chk(cond):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1

    # Regression: parsing and totals.
    try:
        rows = parse.parse_rows("a, 1\nb, 2\na, 3\n\n b , 4 ")
        chk(rows == [("a", 1), ("b", 2), ("a", 3), ("b", 4)])
        chk(dict(aggregate.totals(rows)) == {"a": 4, "b": 6})
    except Exception:
        pass

    # Regression: an average that happens to be an integer.
    try:
        rows = parse.parse_rows("g,10\ng,20\ng,30")
        chk(aggregate.averages(rows) == {"g": 20})
    except Exception:
        pass

    # Bug: fractional averages must be floats, not floored ints.
    try:
        rows = parse.parse_rows("a,1\na,2\nb,5\nb,2")
        avg = aggregate.averages(rows)
        chk(abs(avg["a"] - 1.5) < 1e-9)
        chk(abs(avg["b"] - 3.5) < 1e-9)
    except Exception:
        pass

    print(f"SCORE {passed} {total}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
