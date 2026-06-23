def slugify(text):
    """Turn a title into a URL slug: lowercase, spaces become hyphens."""
    return text.lower().replace(" ", "-")
