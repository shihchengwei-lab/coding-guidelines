"""Held-out grader for bugfix_offbyone. NOT shown to the agent.

Usage: python3 grade_test.py <workspace_dir>
Exit 0 = correct, non-zero = incorrect.
"""
import sys

sys.path.insert(0, sys.argv[1])
import ranges  # noqa: E402


def main():
    assert ranges.inclusive_range(1, 3) == [1, 2, 3], "1..3 inclusive"
    assert ranges.inclusive_range(5, 5) == [5], "single element"
    assert ranges.inclusive_range(0, 0) == [0], "zero..zero"
    assert ranges.inclusive_range(-2, 1) == [-2, -1, 0, 1], "negatives"
    # clamp must remain untouched / working
    assert ranges.clamp(5, 0, 10) == 5
    assert ranges.clamp(-1, 0, 10) == 0
    print("OK")


if __name__ == "__main__":
    main()
