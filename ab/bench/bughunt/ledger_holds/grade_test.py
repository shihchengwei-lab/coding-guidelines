"""Fractional grader for ledger_holds. Prints `SCORE k n`.

Basic balance/transfer checks pass on the seed; the checks that held funds are
unspendable only pass once withdraw respects available() rather than balance.
"""
import sys

sys.path.insert(0, sys.argv[1])
from accounts import Account, InsufficientFunds  # noqa: E402
from ledger import Ledger  # noqa: E402


def main():
    passed = 0
    total = 0

    def chk(cond):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1

    def raises(fn):
        try:
            fn()
            return False
        except InsufficientFunds:
            return True
        except Exception:
            return False

    # Regression: deposit / withdraw / available without holds.
    try:
        a = Account("a")
        a.deposit(100)
        chk(a.balance == 100)
        a.withdraw(30)
        chk(a.balance == 70)
        chk(a.available() == 70)
    except Exception:
        pass

    # Regression: available reflects holds, overdraft of balance still blocked.
    try:
        a = Account("a")
        a.deposit(100)
        a.place_hold(20)
        chk(a.available() == 80)
        chk(raises(lambda: a.withdraw(200)))
    except Exception:
        pass

    # Bug: a withdrawal larger than available (but <= balance) must be blocked.
    try:
        a = Account("a")
        a.deposit(100)
        a.place_hold(60)            # available now 40
        chk(raises(lambda: a.withdraw(50)))   # 50 > 40 available
        chk(a.balance == 100)                 # nothing was withdrawn
    except Exception:
        pass

    # Bug: transfer must respect available, not balance.
    try:
        lg = Ledger()
        src = lg.open("src")
        lg.open("dst")
        src.deposit(100)
        src.place_hold(70)          # available 30
        chk(raises(lambda: lg.transfer("src", "dst", 50)))
        chk(lg.get("dst").balance == 0)
    except Exception:
        pass

    print(f"SCORE {passed} {total}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
