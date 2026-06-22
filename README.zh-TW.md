# Coding Guidelines Hook

> [English](./README.md) | 中文

Claude Code 兩階段 hook。**每次 prompt 前**（UserPromptSubmit）：always-on 的正面規則，外加一個只在「要建新東西」時才觸發的 keyword-gated 提醒。**agent 要停下時**（Stop）：自查清單。Stop hook 用 `exit 2` 強迫 agent 把清單讀進視線，再走一輪才能真的停下。

不靠 LLM 自己讀 CLAUDE.md。不建外部 framework——只是把文字餵進 Claude Code 內建 hook。

## 注入什麼

**每次 prompt 前**（`rules.py`）：

```
1. 寫 code 前先把任務拆解成最基本的需求，再講出假設
2. 先寫測試，再寫到通過

例外：Trivial 任務跳過這兩條。
```

**每次 prompt 前，但只在「要建新東西」時**（`inventory_gate.py`）：

```
🧰 建新東西偵測 — 動手前由外往內盤點，多數「我需要新 X」前面 4 層其實已經有了：

1. 這件事真的要做嗎？— 任務本身是不是多餘？目標能不能用「不做」或「換做別的」達成？
2. 語言／平台內建？— stdlib、shell builtin、作業系統、framework 本身是不是已經提供？
3. 已安裝的依賴？— 翻 package.json／requirements.txt／Cargo.toml／go.mod 等，已是依賴的東西不要再寫一次。
4. 本 repo 既有？— ls／glob 相關目錄、grep 關鍵詞，看是不是已經有人實作過。
5. 前 4 層都沒有 → 再考慮新建，並說明為什麼前面每一層不夠用。

能擴既有的 → 擴它（少一份要維護的東西）。「先盤點再決定建不建」是減法紀律的第一道關。
```

跟 always-on 的規則不同，這條是 keyword-gated：只在 prompt 命中「建新東西」的字眼（`建一個`、`新增`、`create a`、`build a` 等）時才觸發，不在每輪都加重量。

**Agent 要停下時**（`review.py`）：

```
[簡潔] senior engineer 看 diff 會不會說太複雜？
- 有沒有為單次使用的 code 寫抽象？
- 有沒有加沒被要求的彈性／配置？
- 有沒有處理不可能發生的錯誤？

[範圍] 每一行改動能不能 trace 回去本輪 user 最初的請求？
- 有沒有順手改鄰近 code／註解／格式？
- 有沒有 refactor 沒壞的東西？
- 有沒有刪掉早就存在的 dead code（只該提及，不該刪）？

任一項符合，修掉。
```

Review 腳本除了印 checklist 之外，還做兩件事：

1. **文件過濾** — 如果這一輪所有編輯都是文件檔（`.md`、`.txt`、`.json`、`.yml`、`.yaml`、`.toml`）或 `.claude/` 底下的路徑，直接跳過 checklist。改 README、設定檔、hook 腳本時不再觸發。

2. **驗證檢查** — 改了 code 但之後沒跑測試或驗證指令時，多加一段：

```
[驗證] 改了 code 但這一輪沒跑測試或驗證指令。
- 跑相關測試，確認改動沒壞東西。
- 沒有測試覆蓋的部分明說「這段沒測」。
```

唯讀指令（`ls`、`cat`、`git status`、`git diff`、`git log` 等）不算驗證——agent 必須實際跑過測試、build、lint 或腳本才能清除這條。

要換成你自己的內容，直接編輯腳本。

---

## 安裝

請參考 Claude Code 官方 hook 文件：

- Hooks guide: https://docs.claude.com/en/docs/claude-code/hooks-guide
- Hooks reference: https://docs.claude.com/en/docs/claude-code/hooks

本 repo 提供：

- `rules.py` / `rules.en.py`、`inventory_gate.py` / `inventory_gate.en.py`、`review.py` / `review.en.py` — Python 腳本（中文版 / 英文版）。需要 Python 3（現代版本都可以）。
- `settings.example.json` — 範例配置（UserPromptSubmit + Stop，Linux/macOS 路徑風格；指向中文版腳本；Windows 看下面第 2 節最後的替換）

### 1. 放 scripts 到固定位置

Linux / macOS / WSL：

```bash
mkdir -p ~/.claude/scripts
cp rules.py inventory_gate.py review.py ~/.claude/scripts/
```

Windows（PowerShell）：

```powershell
New-Item -ItemType Directory -Force -Path $HOME\.claude\scripts
Copy-Item rules.py, inventory_gate.py, review.py $HOME\.claude\scripts\
```

### 2. 配置 Claude Code hooks

把 `settings.example.json` 的 hook 條目合併進 `~/.claude/settings.json`。對每個 event（`UserPromptSubmit`、`Stop`）：如果已經有對應陣列，把新 hook block append 進尾端；沒有就整個 block 照貼。

Linux / macOS / WSL — `python3` 跟 `~` 路徑展開都可用：

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/scripts/rules.py",
            "timeout": 5
          }
        ]
      },
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/scripts/inventory_gate.py",
            "timeout": 5
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/scripts/review.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

Windows native — 用 `python` 加絕對路徑（Windows 的 hook 不一定能展開 `~`；把 `YOUR_NAME` 換成你的 Windows 使用者名稱）：

```json
"command": "python C:/Users/YOUR_NAME/.claude/scripts/rules.py"
"command": "python C:/Users/YOUR_NAME/.claude/scripts/inventory_gate.py"
"command": "python C:/Users/YOUR_NAME/.claude/scripts/review.py"
```

### 3. 重啟 Claude Code

### 4. 驗證

開新 session 試一個明顯**非 trivial** 的請求，例如：

> 我想做一個讀 CSV、過濾欄位、輸出 JSON 的小工具

Agent 應該先問或先列假設（CSV 編碼？欄位名稱？過濾條件怎麼指定？輸出要不要 pretty print？）再動手，而不是直接寫 code。如果 agent 直接動手沒講假設，hook 可能沒生效——檢查 script 路徑、權限、settings.json 語法。

因為這個例子有「做一個」的字眼，盤點關卡也會觸發：你應該看到 agent 先快速 `ls`／`grep` 確認有沒有現成的類似工具，而不是沒問就從零開始造。

> 不要用「寫個排序函數」這類請求驗證——按規則的 Trivial 例外，agent 對這類請求本來就不需要列假設，會分不出是 hook 沒生效還是規則正確套用。

Agent 收尾時，應該也會看到它在停下前自查（Stop hook 注入簡潔／範圍清單）。如果從來沒看到自查，Stop hook 可能沒生效。

---

## 自訂

內容寫在 `rules.py` 跟 `review.py`（以及 `.en` 變體）內。直接編輯字串就行。盤點關卡（`inventory_gate.py`）另有一份 `TRIGGER` 觸發詞清單，可加寬或收窄來控制它何時觸發。

> Windows 使用者注意：`rules.py` 開頭兩行 `import sys; sys.stdout.reconfigure(encoding="utf-8")` 是給 Windows native Python 用的——預設 stdout 用系統編碼（如 cp950），中文會輸出成亂碼。改寫時保留這兩行。Linux/macOS 不嚴格需要但留著無害。`rules.en.py` 純 ASCII 沒這兩行；若你把它改寫成含中日韓等非 ASCII，記得加上。

規則分兩類。正面句（「做 X 之前先做 Y」）放在 pre-prompt hook，維持短讓每輪高 attention。禁止句（「不寫不必要的 code」「不改 scope 外的 code」）放在 pre-stop hook，寫成具體自查項，因為抽象的禁止句太容易在 turn 開頭被點頭應付過去——具體的問題（「有沒有為單次 code 寫抽象？」）比較難 evade。例外是 pre-prompt 規則沒有明講的邊界。你可以：

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

## 為什麼分兩階段

規則來自 Andrej Karpathy 對 LLM coding pitfalls 的觀察。它們按發生作用的時機自然分兩階段：

- **Pre-prompt**（正面句，開始寫之前）：先講假設、先寫測試。塑造 *agent 怎麼起步*——短規則讓每輪都高 attention。第二個 pre-prompt hook——盤點關卡——不是 always-on 而是 keyword-gated：只在要建新東西時才觸發，提醒先檢查有沒有現成資產再造輪子；刻意保持條件式，才不會稀釋 always-on 的短規則。
- **Pre-stop**（禁止句，結束之前）：自查過度設計跟越界改動。這類在寫的過程中很容易犯、又很容易在 turn 開頭被一句抽象的禁止句點頭應付過去。具體問題（「有沒有為單次 code 寫抽象？」）比「不寫不必要的 code」難 evade。

例外只套用在 pre-prompt：trivial 任務要求列假設跟測試是 overhead。pre-stop 清單在 agent 想停時跑，但會跳過沒改 code 的輪次（純對話跟只改文件都不會有噪音）。還會檢查 agent 改完 code 之後有沒有跑驗證指令，沒有的話多加一段 `[驗證]` 提醒。

---

## Credits

規則整理自 [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) — derived from Andrej Karpathy's observations on LLM coding pitfalls。例外改寫自原版 CLAUDE.md preamble 的 "For trivial tasks, use judgment"。

## License

MIT
