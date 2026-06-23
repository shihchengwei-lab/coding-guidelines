"""Fractional grader for wildcard_match. Prints `SCORE k n`."""
import sys

sys.path.insert(0, sys.argv[1])
import glob_match  # noqa: E402

CASES = [
    (("", ""), True),
    (("", "*"), True),
    (("", "?"), False),
    (("a", ""), False),
    (("a", "a"), True),
    (("a", "?"), True),
    (("a", "*"), True),
    (("aa", "a"), False),
    (("aa", "*"), True),
    (("aa", "a*"), True),
    (("ab", "?*"), True),
    (("aab", "c*a*b"), False),
    (("mississippi", "m*iss*iss*p*i"), True),
    (("mississippi", "m*xss*"), False),
    (("mississippi", "m*iss*iss*i"), True),
    (("adceb", "*a*b"), True),
    (("acdcb", "a*c?b"), False),
    (("abcabczzzde", "*abc???de*"), True),
]


def main():
    passed = 0
    for args, expected in CASES:
        try:
            if glob_match.is_match(*args) == expected:
                passed += 1
        except Exception:
            pass
    print(f"SCORE {passed} {len(CASES)}")
    sys.exit(0 if passed == len(CASES) else 1)


if __name__ == "__main__":
    main()
