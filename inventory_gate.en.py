#!/usr/bin/env python3
"""inventory_gate (English) - UserPromptSubmit hook.

Detects "building something new" phrasing and, before you start, reminds you to
inventory existing assets first (don't reinvent the wheel). Prints the reminder
to stdout (injected as context) only on a match; silent otherwise. Any error
exits 0 so it never disrupts the user's prompt.
"""

import json
import re
import sys

# Trigger phrases for "build something new". Edit to taste.
TRIGGER = re.compile(
    r"create a|build a|add a new|write a new|implement a",
    re.IGNORECASE,
)

REMINDER = """[Inventory] "Build something new" detected -- inventory outward-in before you build; most "I need a new X" already exists in one of the first 4 layers:

1. Does this even need doing? -- is the task itself redundant? Can the goal be met by "not doing it" or "doing something else"?
2. Built into the language/platform? -- stdlib, shell builtin, OS, or the framework itself may already provide it.
3. Already-installed dependency? -- check package.json / requirements.txt / Cargo.toml / go.mod; don't rewrite what's already a dep.
4. Already in this repo? -- ls/glob the relevant dirs and grep the keywords to see if it's already implemented.
5. None of layers 1-4 cover it -> then build, and note why each prior layer was not enough.

Can extend what exists -> extend it (one less thing to maintain). "Inventory first, then decide whether to build" is the first gate of subtraction discipline."""


def should_inject(prompt) -> bool:
    if not prompt:
        return False
    return bool(TRIGGER.search(prompt))


def read_prompt() -> str:
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    except Exception:
        return ""
    if not raw or not raw.strip():
        return ""
    try:
        data = json.loads(raw)
    except Exception:
        return ""
    return data.get("prompt", "") or ""


def main() -> None:
    if should_inject(read_prompt()):
        print(REMINDER)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
