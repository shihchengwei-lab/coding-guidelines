def get_setting(config, key, default=None):
    """Return config[key] if present, otherwise default."""
    return config.get(key, default)
