# Coding Guidelines Hook

> [English](./README.md) | 中文

把四條 coding rules + 一條例外，透過 Claude Code 的 UserPromptSubmit hook 注入每次對話。模型每次處理你的 prompt 前，會先看到這些內容。

不靠 LLM 自己讀 CLAUDE.md。不建 enforcement framework。只是把規則貼進每次 context。

## 四條規則 + Trivial 例外

```
1. 寫 code 前先講假設
2. 不寫不必要的 code
3. 不改目標以外的行
4. 先寫測試，再寫到通過

例外：Trivial 任務只套用第 2、3 條。
```

要換成你自己的規則，編輯 `rules.sh`（或 `rules.py`）。

---

## 安裝

請參考 Claude Code 官方 hook 文件：

- Hooks guide: https://docs.claude.com/en/docs/claude-code/hooks-guide
- Hooks reference: https://docs.claude.com/en/docs/claude-code/hooks

本 repo 提供：

- `rules.sh` / `rules.en.sh` — POSIX shell script（中文版 / 英文版，Linux / macOS / WSL / Git Bash 用）
- `rules.py` / `rules.en.py` — Python alternative（中文版 / 英文版，Windows native 推薦）
- `settings.example.json` — 範例配置（`UserPromptSubmit` event，Linux/macOS 路徑風格；指向中文版 `rules.sh`；Windows 看下面第 2 節最後的替換）

### 1. 放 script 到固定位置

Linux / macOS / WSL / Git Bash：

```bash
mkdir -p ~/.claude/scripts
cp rules.sh ~/.claude/scripts/
chmod +x ~/.claude/scripts/rules.sh
```

Windows（PowerShell）：

```powershell
New-Item -ItemType Directory -Force -Path $HOME\.claude\scripts
Copy-Item rules.py $HOME\.claude\scripts\
```

### 2. 配置 Claude Code hook

把 `settings.example.json` 的 hook 條目合併進 `~/.claude/settings.json`。如果你已經有 `UserPromptSubmit` 陣列，把新的 hook block append 進陣列尾端；如果沒有，整個 `UserPromptSubmit` 區塊照貼即可。

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/scripts/rules.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

Windows native 把 `command` 改成（把 `YOUR_NAME` 換成你的 Windows 使用者名稱）：

```json
"command": "python C:/Users/YOUR_NAME/.claude/scripts/rules.py"
```

注意：Windows native 的 hook 不一定能展開 `~`，所以這裡用絕對路徑。

### 3. 重啟 Claude Code

### 4. 驗證

開新 session 試一個明顯**非 trivial** 的請求，例如：

> 我想做一個讀 CSV、過濾欄位、輸出 JSON 的小工具

Agent 應該先問或先列假設（CSV 編碼？欄位名稱？過濾條件怎麼指定？輸出要不要 pretty print？）再動手，而不是直接寫 code。如果 agent 直接動手沒講假設，hook 可能沒生效——檢查 script 路徑、權限、settings.json 語法。

> 不要用「寫個排序函數」這類請求驗證——按規則的 Trivial 例外，agent 對這類請求本來就不需要列假設，會分不出是 hook 沒生效還是規則正確套用。

---

## 自訂

規則寫在 `rules.sh` / `rules.py`（以及 `.en` 變體）內。直接編輯字串就行。

> Windows 使用者注意：`rules.py` 開頭兩行 `import sys; sys.stdout.reconfigure(encoding="utf-8")` 是給 Windows native Python 用的——預設 stdout 用系統編碼（如 cp950），中文會輸出成亂碼。改寫時保留這兩行。Linux/macOS 不需要。`rules.en.py` 純 ASCII 沒這兩行；若你把它改寫成含中日韓等非 ASCII，記得加上。

四條規則是 Karpathy 的通用最小集合，例外是規則沒有明講的邊界。你可以：

- 換成領域特定規則（前端、資料工程、研究 code、特定 stack）
- 換成團隊規範
- 換成個人風格偏好
- 蒸餾出對你工作流更精準的版本

### 規則設計的取捨

幾個 trade-off：

- **長度**：短的省 token、視覺乾淨，但 grounding 力弱、模型對抽象規則解讀空間大；長的 compliance 強，但每輪重複付 token 成本，且模型對重複內容的 attention 會衰減
- **數量**：少的每條都被 attend，但覆蓋面小；多的覆蓋廣，但後幾條容易被忽略
- **具體度**：抽象規則（「不寫不必要的 code」）適用範圍廣但解讀空間大；具體規則（「不加沒被要求的 feature、不為單次 code 寫抽象」）解讀空間小但只覆蓋你列出的形態
- **通道對比**：CLAUDE.md 在 session 開頭讀一次，對長 session 有距離衰減；hook 每輪注入，權重高不衰減，但每輪付 token cost

沒有 single 對的版本。甜蜜點取決於你的 session 長度分布、token cost 容忍度、工作流對 compliance 的敏感度、review window。自己跑幾次測。

---

## 為什麼這四條 + 例外

四條規則來自 Andrej Karpathy 對 LLM coding pitfalls 的觀察——對應常見失控形態：

- 第 1 條防：跳過確認、假設藏在 code 裡、單方面挑解讀
- 第 2 條防：過度設計、加沒被要求的 feature、抽象先行
- 第 3 條防：順手 refactor、改 formatting、動 scope 外的 code
- 第 4 條防：先寫實作再補測試（goodharting）

第 1、4 條是正面句（該做什麼），第 2、3 條是禁止句（不做什麼）——對應每條規則本質的方向性。

例外是規則沒有明講的邊界。原版放在 preamble（"For trivial tasks, use judgment"），本 repo 改寫為「例外：Trivial 任務只套用第 2、3 條。」——hook 每輪重複需要更穩定的 default。

---

## Credits

四條規則整理自 [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) — derived from Andrej Karpathy's observations on LLM coding pitfalls。例外改寫自原版 CLAUDE.md preamble 的 "For trivial tasks, use judgment"。

## License

MIT
