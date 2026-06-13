#!/usr/bin/env bash
# inventory_gate — UserPromptSubmit：偵測「建新東西」字眼，動手前提醒先盤點現有資產（防造輪子）。
# advisory：命中才把提醒印到 stdout（注入 context），永遠 exit 0。
# 注意：shell 版用 grep 掃整個 payload（不靠 jq）；Python 版只取 .prompt，較精準。
payload=$(cat)
if printf '%s' "$payload" | grep -Eqi '建一個|新增|寫一個|做一個|建立|新建|新的[[:space:]]*(script|module|hook|工具|功能)|create a|build a|add a new|write a new|implement a'; then
  cat <<'INNER'
🧰 建新東西偵測 — 動手前先盤點（多數「我需要新 X」其實是「我沒找到已有的 X」）：

1. ls/glob 相關目錄，看有沒有同名／同功能的東西
2. grep 關鍵詞，看這個功能是不是已經有人實作過
3. 問：能不能「擴既有的」而不是「建新的」？
   能擴 → 擴它（少一份要維護的東西）
   真的沒有 → 再建，並說明為什麼既有的不夠用

「先盤點再決定建不建」是減法紀律的第一道關。
INNER
fi
exit 0
