"""Held-out grader for stable_dedup. Usage: python3 grade_test.py <ws>."""
import sys

sys.path.insert(0, sys.argv[1])
import dedup  # noqa: E402


def main():
    assert dedup.dedup([3, 1, 3, 2, 1]) == [3, 1, 2], "first-seen order kept"
    assert dedup.dedup([]) == [], "empty"
    assert dedup.dedup(["b", "a", "b"]) == ["b", "a"], "strings"
    print("OK")


if __name__ == "__main__":
    main()
