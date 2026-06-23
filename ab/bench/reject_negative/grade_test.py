"""Held-out grader for reject_negative. NOT shown to the agent.

Usage: python3 grade_test.py <workspace_dir>
Exit 0 = correct, non-zero = incorrect.
"""
import sys

sys.path.insert(0, sys.argv[1])
import orders  # noqa: E402


def main():
    assert orders.total_price(2, 3) == 6, "normal"
    assert orders.total_price(5, 0) == 0, "zero quantity allowed"
    raised = False
    try:
        orders.total_price(2, -1)
    except ValueError:
        raised = True
    assert raised, "negative quantity must raise ValueError"
    # apply_discount must remain untouched / working
    assert orders.apply_discount(100, 10) == 90
    print("OK")


if __name__ == "__main__":
    main()
