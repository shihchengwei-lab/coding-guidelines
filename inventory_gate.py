#!/usr/bin/env python3
"""inventory_gate — UserPromptSubmit hook。

偵測「要建新東西」的字眼，動手前提醒先盤點現有資產（防造輪子）。
命中觸發詞才把提醒印到 stdout（注入 context）；沒命中不印。
任何錯誤都靜默通過（exit 0），絕不干擾使用者的 prompt。

Windows native Python：stdin 預設用系統編碼（如 cp950/gbk），會把 UTF-8
的中文讀壞，所以這裡讀原始位元組再明確用 UTF-8 解碼。
"""

import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

# 觸發詞：中英「建新東西」的說法。可自行增減。
TRIGGER = re.compile(
    r"建一個|新增|寫一個|做一個|建立|新建"
    r"|新的\s*(?:script|module|hook|工具|功能)"
    r"|create a|build a|add a new|write a new|implement a",
    re.IGNORECASE,
)

REMINDER = """🧰 建新東西偵測 — 動手前由外往內盤點，多數「我需要新 X」前面 4 層其實已經有了：

1. 這件事真的要做嗎？— 任務本身是不是多餘？目標能不能用「不做」或「換做別的」達成？
2. 語言／平台內建？— stdlib、shell builtin、作業系統、framework 本身是不是已經提供？
3. 已安裝的依賴？— 翻 package.json／requirements.txt／Cargo.toml／go.mod 等，已是依賴的東西不要再寫一次。
4. 本 repo 既有？— ls／glob 相關目錄、grep 關鍵詞，看是不是已經有人實作過。
5. 前 4 層都沒有 → 再考慮新建，並說明為什麼前面每一層不夠用。

能擴既有的 → 擴它（少一份要維護的東西）。「先盤點再決定建不建」是減法紀律的第一道關。"""


def should_inject(prompt) -> bool:
    """命中觸發詞回 True；空字串／None 回 False。"""
    if not prompt:
        return False
    return bool(TRIGGER.search(prompt))


def read_prompt() -> str:
    """從 stdin 讀 hook JSON，取 prompt 欄位；讀不到／壞掉回空字串。"""
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
