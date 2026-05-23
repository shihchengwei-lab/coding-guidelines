#!/usr/bin/env python3
import json
import sys

CHECKLIST = """[Simplicity] Would a senior engineer call this diff too complex?
- Any abstractions written for one-shot code?
- Any unrequested flexibility/configuration?
- Any handling of errors that can't actually happen?

[Scope] Can every changed line be traced back to the user's original request this turn?
- Any drive-by edits to nearby code / comments / formatting?
- Any refactor of things that weren't broken?
- Any deletion of pre-existing dead code (mention only, don't delete)?

If any apply, fix it before stopping."""

EDIT_TOOLS = {"Edit", "Write", "NotebookEdit"}


def inject():
    print(CHECKLIST, file=sys.stderr)
    sys.exit(2)


def turn_has_edit(transcript_path: str) -> bool:
    with open(transcript_path, encoding="utf-8") as f:
        lines = f.readlines()
    for raw in reversed(lines):
        line = raw.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        etype = entry.get("type")
        if etype == "user":
            content = entry.get("message", {}).get("content")
            if isinstance(content, list) and any(
                isinstance(b, dict) and b.get("type") == "tool_result"
                for b in content
            ):
                continue
            return False
        if etype != "assistant":
            continue
        content = entry.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("name") in EDIT_TOOLS
            ):
                return True
    return False


try:
    payload = json.load(sys.stdin)
except ValueError:
    payload = {}

if payload.get("stop_hook_active") is True:
    sys.exit(0)

transcript_path = payload.get("transcript_path")
if not transcript_path:
    inject()

try:
    if turn_has_edit(transcript_path):
        inject()
except OSError:
    inject()

sys.exit(0)
