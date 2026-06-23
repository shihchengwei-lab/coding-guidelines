"""Exceptions raised by the record store."""


class DuplicateId(KeyError):
    """Raised when inserting an id that already exists."""


class MissingId(KeyError):
    """Raised when updating an id that does not exist."""
