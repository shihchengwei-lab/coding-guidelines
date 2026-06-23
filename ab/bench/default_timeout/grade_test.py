"""Held-out grader for default_timeout. Usage: python3 grade_test.py <ws>."""
import sys

sys.path.insert(0, sys.argv[1])
import client  # noqa: E402


def main():
    assert client.fetch("u") == ("u", 30), "defaults timeout to 30"
    assert client.fetch("u", 5) == ("u", 5), "explicit timeout still honored"
    print("OK")


if __name__ == "__main__":
    main()
