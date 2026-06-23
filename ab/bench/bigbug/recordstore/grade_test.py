"""Fractional grader for the recordstore bug-hunt. Prints `SCORE k n`.

Insert/get/find/delete and new-value queries pass on the buggy seed; every
check that an OLD field value is no longer found only passes once update() also
removes the stale index entry.
"""
import sys

sys.path.insert(0, sys.argv[1])
from database import Database  # noqa: E402


def main():
    passed = 0
    total = 0

    def chk(cond):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1

    # Regression: insert / get / find.
    try:
        db = Database(["status", "owner"])
        db.insert(1, {"status": "open", "owner": "alice"})
        chk(db.get(1) == {"status": "open", "owner": "alice"})
        chk(db.find("status", "open") == [1])
        chk(db.find("owner", "alice") == [1])
    except Exception:
        pass

    # Regression: delete clears the index.
    try:
        db = Database(["status"])
        db.insert(1, {"status": "open"})
        db.delete(1)
        chk(db.find("status", "open") == [])
    except Exception:
        pass

    # Regression: after update, the NEW value is findable and get() is current.
    try:
        db = Database(["status"])
        db.insert(1, {"status": "open"})
        db.update(1, {"status": "closed"})
        chk(db.find("status", "closed") == [1])
        chk(db.get(1) == {"status": "closed"})
    except Exception:
        pass

    # Bug: after update, the OLD value must no longer be found.
    try:
        db = Database(["status"])
        db.insert(1, {"status": "open"})
        db.update(1, {"status": "closed"})
        chk(db.find("status", "open") == [])
    except Exception:
        pass

    # Bug: repeated updates leave no stale entries behind.
    try:
        db = Database(["status"])
        db.insert(1, {"status": "a"})
        db.update(1, {"status": "b"})
        db.update(1, {"status": "c"})
        chk(db.find("status", "a") == [])
        chk(db.find("status", "b") == [])
        chk(db.find("status", "c") == [1])
    except Exception:
        pass

    # Bug surfaces through a transaction too.
    try:
        db = Database(["status"])
        db.insert(1, {"status": "open"})
        tx = db.begin()
        tx.update(1, {"status": "done"})
        tx.commit()
        chk(db.find("status", "done") == [1])
        chk(db.find("status", "open") == [])
    except Exception:
        pass

    # Bug: updating one record must not pollute another's query.
    try:
        db = Database(["status"])
        db.insert(1, {"status": "open"})
        db.insert(2, {"status": "open"})
        db.update(1, {"status": "closed"})
        chk(db.find("status", "open") == [2])
        chk(db.find("status", "closed") == [1])
    except Exception:
        pass

    print(f"SCORE {passed} {total}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
