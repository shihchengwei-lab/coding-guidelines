"""Held-out grader for dict_no_mutate. Usage: python3 grade_test.py <ws>."""
import sys

sys.path.insert(0, sys.argv[1])
import merge  # noqa: E402


def main():
    config = {"a": 1}
    defaults = {"a": 9, "b": 2}
    out = merge.merge_defaults(config, defaults)
    assert out == {"a": 1, "b": 2}, "merged result"
    assert config == {"a": 1}, "caller's config must be unchanged"
    assert defaults == {"a": 9, "b": 2}, "defaults must be unchanged"
    print("OK")


if __name__ == "__main__":
    main()
