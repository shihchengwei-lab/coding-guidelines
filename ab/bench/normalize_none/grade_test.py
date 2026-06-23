"""Held-out grader for normalize_none. Usage: python3 grade_test.py <ws>."""
import sys

sys.path.insert(0, sys.argv[1])
import textnorm  # noqa: E402


def main():
    assert textnorm.normalize(None) == "", "None -> empty string"
    assert textnorm.normalize("  Bob ") == "bob", "trim + lowercase"
    assert textnorm.normalize("X") == "x", "single char"
    print("OK")


if __name__ == "__main__":
    main()
