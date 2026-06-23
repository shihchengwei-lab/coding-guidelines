"""A tiny reactive spreadsheet.

A cell is either a literal value (set_value) or a formula computed from other
cells (set_formula). When a cell changes, everything that depends on it should
update so that get() always returns a consistent, up-to-date value.
"""
from formulas import OPS


class Sheet:
    def __init__(self):
        self._values = {}        # name -> current value
        self._formulas = {}      # name -> (op, deps)
        self._dependents = {}    # name -> list of names that depend on it

    def set_value(self, name, value):
        """Set a literal value and refresh anything that depends on it."""
        self._formulas.pop(name, None)
        self._values[name] = value
        self._propagate(name)

    def set_formula(self, name, op, deps):
        """Define name = OPS[op](*deps) and compute it now."""
        if op not in OPS:
            raise ValueError("unknown op: " + op)
        self._formulas[name] = (op, list(deps))
        for dep in deps:
            bucket = self._dependents.setdefault(dep, [])
            if name not in bucket:
                bucket.append(name)
        self._recompute(name)

    def get(self, name):
        return self._values[name]

    def _recompute(self, name):
        op, deps = self._formulas[name]
        self._values[name] = OPS[op](*[self._values[d] for d in deps])

    def _propagate(self, name):
        for dependent in self._dependents.get(name, []):
            self._recompute(dependent)
