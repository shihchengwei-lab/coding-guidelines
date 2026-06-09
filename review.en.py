#!/usr/bin/env python3
import json
import os
import sys

CHECKLIST_BASE = """[Simplicity] Would a senior engineer call this diff too complex?
- Any abstractions written for one-shot code?
- Any unrequested flexibility/configuration?
- Any handling of errors that can't actually happen?

[Scope] Can every changed line be traced back to the user's original request this turn?
- Any drive-by edits to nearby code / comments / formatting?
- Any refactor of things that weren't broken?
- Any deletion of pre-existing dead code (mention only, don't delete)?"""

VERIFY_SECTION = """
[Verification] Code was edited this turn but no test or verification command was run.
- Run relevant tests to confirm nothing is broken.
- If no test coverage exists, say so explicitly."""

FOOTER = "\n\nIf any apply, fix it before stopping."

EDIT_TOOLS = {"Edit", "Write", "NotebookEdit"}

DOC_EXTENSIONS = frozenset({".md", ".txt", ".json", ".yml", ".yaml", ".toml"})

READ_ONLY_CMDS = frozenset({
    "ls", "dir", "cat", "head", "tail", "type",
    "pwd", "echo", "which", "where", "cd", "wc",
    "find", "grep", "rg",
})

GIT_READ_ONLY = frozenset({
    "status", "diff", "log", "show", "branch", "remote", "tag",
})


def is_doc_only(file_path):
    if not file_path:
        return False
    _, ext = os.path.splitext(file_path)
    if ext.lower() in DOC_EXTENSIONS:
        return True
    normalized = file_path.replace("\\", "/")
    if "/.claude/" in normalized or normalized.startswith(".claude/"):
        return True
    return False


def is_read_only_cmd(cmd):
    stripped = cmd.strip()
    if not stripped:
        return True
    first = stripped.split()[0].lower()
    if first in READ_ONLY_CMDS:
        return True
    if first == "git":
        parts = stripped.split()
        return len(parts) < 2 or parts[1].lower() in GIT_READ_ONLY
    return False


def inject(needs_verify=False):
    checklist = CHECKLIST_BASE
    if needs_verify:
        checklist += VERIFY_SECTION
    checklist += FOOTER
    print(checklist, file=sys.stderr)
    sys.exit(2)


def scan_current_turn(transcript_path):
    with open(transcript_path, encoding="utf-8") as f:
        lines = f.readlines()

    has_code_edit = False
    found_last_code_edit = False
    found_verification = False

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
            break

        if etype != "assistant":
            continue

        content = entry.get("message", {}).get("content")
        if not isinstance(content, list):
            continue

        for block in reversed(content):
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue

            name = block.get("name")

            if name in EDIT_TOOLS:
                file_path = block.get("input", {}).get("file_path", "")
                if not is_doc_only(file_path):
                    has_code_edit = True
                    found_last_code_edit = True

            elif name == "Bash" and not found_last_code_edit:
                cmd = block.get("input", {}).get("command", "")
                if not is_read_only_cmd(cmd):
                    found_verification = True

    return {
        "has_code_edit": has_code_edit,
        "needs_verify": has_code_edit and not found_verification,
    }


try:
    payload = json.load(sys.stdin)
except ValueError:
    payload = {}

if payload.get("stop_hook_active") is True:
    sys.exit(0)

transcript_path = payload.get("transcript_path")
if not transcript_path:
    inject(needs_verify=True)

try:
    result = scan_current_turn(transcript_path)
    if result["has_code_edit"]:
        inject(needs_verify=result["needs_verify"])
except OSError:
    inject(needs_verify=True)

sys.exit(0)
