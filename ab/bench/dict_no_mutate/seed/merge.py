"""Config merging."""


def merge_defaults(config, defaults):
    """Return config with any keys missing from it filled in from defaults.

    Must NOT modify the caller's config dict.
    """
    for key, value in defaults.items():
        config.setdefault(key, value)
    return config
