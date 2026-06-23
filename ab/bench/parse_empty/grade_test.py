"""Held-out grader for parse_empty. Usage: python3 grade_test.py <ws>."""
import sys

sys.path.insert(0, sys.argv[1])
import pairs  # noqa: E402


def main():
    assert pairs.parse_pairs("") == {}, "empty string -> empty dict"
    assert pairs.parse_pairs("a=1;b=2") == {"a": "1", "b": "2"}, "normal parse"
    assert pairs.parse_pairs("x=9") == {"x": "9"}, "single pair"
    print("OK")


if __name__ == "__main__":
    main()
