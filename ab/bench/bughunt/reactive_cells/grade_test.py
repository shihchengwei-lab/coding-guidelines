"""Fractional grader for reactive_cells. Prints `SCORE k n`.

Regression checks (a-z direct deps) pass on the buggy seed; the transitive and
diamond-dependency checks only pass once propagation recurses correctly.
"""
import sys

sys.path.insert(0, sys.argv[1])
from sheet import Sheet  # noqa: E402


def main():
    passed = 0
    total = 0

    def chk(cond):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1

    # Regression: a direct dependency updates (works on the seed).
    try:
        s = Sheet()
        s.set_value("a", 1)
        s.set_formula("b", "sum", ["a"])
        chk(s.get("b") == 1)
        s.set_value("a", 5)
        chk(s.get("b") == 5)
    except Exception:
        pass

    # Transitive: a -> b -> c.
    try:
        s = Sheet()
        s.set_value("a", 1)
        s.set_formula("b", "sum", ["a"])
        s.set_formula("c", "sum", ["b"])
        s.set_value("a", 10)
        chk(s.get("b") == 10)
        chk(s.get("c") == 10)
    except Exception:
        pass

    # Diamond: b=a, c=a*a, d=b+c.
    try:
        s = Sheet()
        s.set_value("a", 2)
        s.set_formula("b", "sum", ["a"])
        s.set_formula("c", "product", ["a", "a"])
        s.set_formula("d", "sum", ["b", "c"])
        chk(s.get("d") == 6)
        s.set_value("a", 3)
        chk(s.get("b") == 3)
        chk(s.get("c") == 9)
        chk(s.get("d") == 12)
    except Exception:
        pass

    print(f"SCORE {passed} {total}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
