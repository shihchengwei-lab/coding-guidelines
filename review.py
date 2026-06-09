#!/usr/bin/env python3
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

CHECKLIST_BASE = """[簡潔] senior engineer 看 diff 會不會說太複雜？
- 有沒有為單次使用的 code 寫抽象？
- 有沒有加沒被要求的彈性／配置？
- 有沒有處理不可能發生的錯誤？

[範圍] 每一行改動能不能 trace 回去本輪 user 最初的請求？
- 有沒有順手改鄰近 code／註解／格式？
- 有沒有 refactor 沒壞的東西？
- 有沒有刪掉早就存在的 dead code（只該提及，不該刪）？"""

VERIFY_SECTION = """
[驗證] 改了 code 但這一輪沒跑測試或驗證指令。
- 跑相關測試，確認改動沒壞東西。
- 沒有測試覆蓋的部分明說「這段沒測」。"""

FOOTER = "\n\n任一項符合，修掉。"

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
