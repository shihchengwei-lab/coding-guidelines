"""Fractional grader for eval_expr. Prints `SCORE k n`."""
import sys

sys.path.insert(0, sys.argv[1])
import calc  # noqa: E402

RAISES = object()
CASES = [
    ("1+1", 2),
    ("2+3*4", 14),
    ("(2+3)*4", 20),
    ("10-2-3", 5),
    ("2*3+4*5", 26),
    (" 7 / 2 ", 3),
    ("-7/2", -3),
    ("7/-2", -3),
    ("-(3+4)", -7),
    ("2*-3", -6),
    ("((1+2)*(3+4))", 21),
    ("100/(2+3)/2", 10),
    ("1+", RAISES),
    ("(1+2", RAISES),
    ("3+abc", RAISES),
    ("", RAISES),
]


def main():
    passed = 0
    for expr, expected in CASES:
        try:
            got = calc.evaluate(expr)
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
