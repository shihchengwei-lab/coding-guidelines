"""Parse simple 'group,amount' lines."""


def parse_rows(text):
    """Parse lines of the form 'group,amount' into (group, int amount) tuples.

    Blank lines are skipped. Surrounding whitespace is ignored.
    """
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        group, amount = line.split(",")
        rows.append((group.strip(), int(amount)))
    return rows
