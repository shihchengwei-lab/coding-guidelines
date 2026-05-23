#!/usr/bin/env python3
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

CHECKLIST = """[簡潔] senior engineer 看 diff 會不會說太複雜？
- 有沒有為單次使用的 code 寫抽象？
- 有沒有加沒被要求的彈性／配置？
- 有沒有處理不可能發生的錯誤？

[範圍] 每一行改動能不能 trace 回去本輪 user 最初的請求？
- 有沒有順手改鄰近 code／註解／格式？
- 有沒有 refactor 沒壞的東西？
- 有沒有刪掉早就存在的 dead code（只該提及，不該刪）？

任一項符合，修掉再停。"""

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
