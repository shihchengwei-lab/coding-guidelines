"""Order pricing helpers."""


def total_price(unit_price, quantity):
    """Return unit_price * quantity.

    quantity must be >= 0. A negative quantity is invalid.
    """
    return unit_price * quantity


def apply_discount(total, pct):
    """Reduce total by pct percent."""
    return total * (1 - pct / 100)
