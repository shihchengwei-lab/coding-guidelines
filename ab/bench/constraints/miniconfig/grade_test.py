"""Fractional grader for miniconfig. Prints `SCORE k n`.

27 independent constraints. A correct reference implementation passes all 27;
the stub passes none. Weaker attempts tend to drop individual rules (inline
comment vs quoted '#', escaped quotes, quoted commas in lists, leading-zero
ints, scientific notation not being a float, dotted nested keys), so the score
is a smooth gradient rather than all-or-nothing.
"""
import sys

sys.path.insert(0, sys.argv[1])
import config  # noqa: E402

R = object()  # sentinel: expect ValueError
CASES = [
    ("a = 1", {"a": 1}),
    ("a = 1.5", {"a": 1.5}),
    ("a = true\nb = false", {"a": True, "b": False}),
    ("name = hello world", {"name": "hello world"}),
    ('greeting = "hello world"', {"greeting": "hello world"}),
    ("x = -42", {"x": -42}),
    ("# comment\na = 1", {"a": 1}),
    ("a = 1 # inline", {"a": 1}),
    ('msg = "a # b"', {"msg": "a # b"}),
    ("a = 1\nb = 2\n\n  \nc = 3", {"a": 1, "b": 2, "c": 3}),
    ("a.b = 1\na.c = 2", {"a": {"b": 1, "c": 2}}),
    ("k = 1\nk = 2", {"k": 2}),
    ("nums = [1, 2, 3]", {"nums": [1, 2, 3]}),
    ("mix = [1, true, hi]", {"mix": [1, True, "hi"]}),
    ("empty = []", {"empty": []}),
    ('tags = ["a,b", c]', {"tags": ["a,b", "c"]}),
    ("blank =", {"blank": ""}),
    (r'esc = "a\"b"', {"esc": 'a"b'}),
    ("noequals", R),
    ("1bad = 2", R),
    ('bad = "unterminated', R),
    ("a.b.c = 1", {"a": {"b": {"c": 1}}}),
    (r'path = "C:\\x"', {"path": "C:\\x"}),
    ("f = 3.0", {"f": 3.0}),
    ("neg = -2.5", {"neg": -2.5}),
    ("s = 007", {"s": "007"}),
    ("v = 1e3", {"v": "1e3"}),
]


def main():
    passed = 0
    for text, expected in CASES:
        try:
            got = config.parse_config(text)
            ok = expected is not R and got == expected
        except ValueError:
            ok = expected is R
        except Exception:
            ok = False
        if ok:
            passed += 1
    print(f"SCORE {passed} {len(CASES)}")
    sys.exit(0 if passed == len(CASES) else 1)


if __name__ == "__main__":
    main()
