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

REMINDER = """[Inventory] "Build something new" detected -- inventory before you build (most "I need a new X" is really "I didn't find the existing X"):

1. ls/glob the relevant dirs for something with the same name/function
2. grep the keywords to see if it is already implemented
3. Ask: can I extend what exists instead of building new?
   Can extend -> extend it (one less thing to maintain)
   Genuinely absent -> then build, and note why the existing one was not enough

"Inventory first, then decide whether to build" is the first gate of subtraction discipline."""


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
