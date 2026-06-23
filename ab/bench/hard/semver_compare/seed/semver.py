def compare(a, b):
    """Compare two semantic versions. Return -1, 0, or 1 (a<b, a==b, a>b).

    Format: MAJOR.MINOR.PATCH, each a non-negative integer, with an optional
    `-prerelease` made of dot-separated identifiers, and optional `+build`
    metadata that is IGNORED for precedence.

    Precedence rules (semver.org):
    - Compare MAJOR, then MINOR, then PATCH numerically.
    - A version WITH a prerelease has LOWER precedence than the same version
      WITHOUT one (1.0.0-alpha < 1.0.0).
    - Compare prerelease identifiers left to right: numeric identifiers compare
      numerically; non-numeric compare lexically (ASCII); a numeric identifier
      has lower precedence than a non-numeric one; a larger set of identifiers
      outranks a smaller one when all preceding are equal.

    Raise ValueError on malformed input.
    """
    raise NotImplementedError
