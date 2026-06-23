"""Parse simple key=value lists."""


def parse_pairs(text):
    """Parse 'k=v;k=v' into a dict. Empty input must return an empty dict."""
    result = {}
    for part in text.split(";"):
        key, value = part.split("=")
        result[key] = value
    return result
