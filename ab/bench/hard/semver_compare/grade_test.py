"""Fractional grader for semver_compare. Prints `SCORE k n`."""
import sys

sys.path.insert(0, sys.argv[1])
import semver  # noqa: E402

RAISES = object()
CASES = [
    (("1.0.0", "1.0.0"), 0),
    (("1.0.0", "2.0.0"), -1),
    (("2.0.0", "1.9.9"), 1),
    (("1.0.0", "1.1.0"), -1),
    (("1.0.1", "1.0.0"), 1),
    (("1.0.0-alpha", "1.0.0"), -1),
    (("1.0.0", "1.0.0-alpha"), 1),
    (("1.0.0-alpha", "1.0.0-alpha.1"), -1),
    (("1.0.0-alpha.1", "1.0.0-alpha.beta"), -1),
    (("1.0.0-alpha.beta", "1.0.0-beta"), -1),
    (("1.0.0-beta", "1.0.0-beta.2"), -1),
    (("1.0.0-beta.2", "1.0.0-beta.11"), -1),
    (("1.0.0-beta.11", "1.0.0-rc.1"), -1),
    (("1.0.0-rc.1", "1.0.0"), -1),
    (("1.0.0+build", "1.0.0"), 0),
    (("1.0.0+a", "1.0.0+b"), 0),
    (("1.0", "2.0.0"), RAISES),
    (("1.0.0", "x.y.z"), RAISES),
]


def main():
    passed = 0
    for args, expected in CASES:
        try:
            got = semver.compare(*args)
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
