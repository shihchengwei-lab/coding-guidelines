#!/usr/bin/env python3
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

try:
    payload = json.load(sys.stdin)
except Exception:
    payload = {}

if payload.get("stop_hook_active") is True:
    sys.exit(0)

print(
    """[簡潔] senior engineer 看 diff 會不會說太複雜？
- 有沒有為單次使用的 code 寫抽象？
- 有沒有加沒被要求的彈性／配置？
- 有沒有處理不可能發生的錯誤？

[範圍] 每一行改動能不能 trace 回去本輪 user 最初的請求？
- 有沒有順手改鄰近 code／註解／格式？
- 有沒有 refactor 沒壞的東西？
- 有沒有刪掉早就存在的 dead code（只該提及，不該刪）？

任一項符合，修掉再停。""",
    file=sys.stderr,
)
sys.exit(2)
