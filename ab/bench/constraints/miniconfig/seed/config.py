def parse_config(text):
    """Parse a small custom config format into a dict. Follow EVERY rule below.

    Lines are separated by '\\n' and processed independently.

    Comments:
    - An unquoted '#' starts a comment running to end of line; strip it off.
    - A '#' inside a double-quoted string is a literal character, NOT a comment.
    - After comment removal, surrounding whitespace is trimmed.
    - A line that is empty after that is skipped (so blank and comment-only
      lines produce nothing).

    Key/value:
    - Each remaining line is 'key = value', split on the FIRST unquoted '='.
    - A line with no unquoted '=' raises ValueError.
    - The key is trimmed; it is a dot-separated path of segments
      ('a.b.c'). Every segment must match [A-Za-z_][A-Za-z0-9_]* or it is a
      ValueError. A dotted key creates nested dicts: 'a.b = 1' -> {'a':{'b':1}}.
    - A later assignment to the same key overwrites the earlier one.

    Value parsing (the value is trimmed first):
    - '' (empty) -> the empty string ''.
    - A value wrapped in '[' ... ']' is a list. Split the inside on top-level
      commas (commas inside quotes do not split), trim each element, and parse
      each element as a SCALAR (below). '[]' -> []. Lists do not nest.
    - Otherwise the value is a SCALAR.

    Scalars:
    - A double-quoted "..." is a string. It must end with an unescaped '"';
      otherwise ValueError. Inside, '\\"' is a literal '"' and '\\\\' is a literal
      backslash. The surrounding quotes are removed.
    - The bareword 'true' -> True, 'false' -> False.
    - An integer matching -?(0|[1-9][0-9]*) -> int. (So '007' is NOT an int;
      leading zeros stay a string.)
    - A float matching -?[0-9]+\\.[0-9]+ -> float. (So '1e3' and '3.' are NOT
      floats.)
    - Anything else is kept as the trimmed string as-is.

    Return the resulting dict.
    """
    raise NotImplementedError
