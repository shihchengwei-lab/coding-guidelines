"""Text normalization."""


def normalize(name):
    """Trim surrounding whitespace and lowercase. None must become ''."""
    return name.strip().lower()
