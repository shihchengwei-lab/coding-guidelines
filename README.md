# Coding Guidelines Hook

> English | [中文](./README.zh-TW.md)

Inject four coding rules plus one exception into every Claude Code conversation via the UserPromptSubmit hook. The model sees these rules before processing each of your prompts.

No reliance on the LLM reading CLAUDE.md. No enforcement framework. Just rules pasted into every turn's context.

## The Four Rules + Trivial Exception

```
1. State assumptions before writing code
2. Don't write unnecessary code
3. Don't modify lines outside the target
4. Write tests first, then write code to pass them

Exception: Trivial tasks only apply rules 2 and 3.
```

To use your own rules, edit `rules.en.sh` (or `rules.en.py`).

---

## Installation

See the official Claude Code hook docs:

- Hooks guide: https://docs.claude.com/en/docs/claude-code/hooks-guide
- Hooks reference: https://docs.claude.com/en/docs/claude-code/hooks

This repo provides:

- `rules.sh` / `rules.en.sh` — POSIX shell script (Chinese / English, for Linux / macOS / WSL / Git Bash)
- `rules.py` / `rules.en.py` — Python alternative (Chinese / English, recommended for Windows native)
- `settings.example.json` — example configuration (`UserPromptSubmit` event, Linux/macOS path style; points to the Chinese `rules.sh` by default — English users: substitute `rules.en.sh`)

### 1. Place the script in a fixed location

Linux / macOS / WSL / Git Bash:

```bash
mkdir -p ~/.claude/scripts
cp rules.en.sh ~/.claude/scripts/
chmod +x ~/.claude/scripts/rules.en.sh
```

Windows (PowerShell):

```powershell
New-Item -ItemType Directory -Force -Path $HOME\.claude\scripts
Copy-Item rules.en.py $HOME\.claude\scripts\
```

### 2. Configure the Claude Code hook

Merge the hook entry from `settings.example.json` into `~/.claude/settings.json`. If you already have a `UserPromptSubmit` array, append the new hook block to its end; otherwise paste the entire `UserPromptSubmit` block as-is.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/scripts/rules.en.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

Windows native: change `command` to (replace `YOUR_NAME` with your Windows username):

```json
"command": "python C:/Users/YOUR_NAME/.claude/scripts/rules.en.py"
```

Note: Windows native hooks don't always expand `~`, so use an absolute path here.

### 3. Restart Claude Code

### 4. Verify

Open a new session and try a clearly **non-trivial** request, e.g.:

> I want to build a small tool that reads a CSV, filters columns, and outputs JSON.

The agent should ask or state assumptions first (CSV encoding? column names? how filter conditions are specified? pretty-print output?) before writing code, rather than diving straight in. If the agent jumps to code without stating assumptions, the hook may not be active — check the script path, permissions, and `settings.json` syntax.

> Don't verify with a request like "write a sort function" — under the Trivial Exception, the agent doesn't need to state assumptions for such requests anyway, so you can't tell whether the hook failed or the rule was correctly applied.

---

## Customization

Rules live in `rules.sh` / `rules.py` (and their `.en` variants). Just edit the strings.

> Non-ASCII users: if you rewrite the rules to contain CJK or other non-ASCII characters, look at `rules.py` — the two lines `import sys; sys.stdout.reconfigure(encoding="utf-8")` at the top are required for Windows native Python (the default stdout uses the system codepage, e.g. cp950, which mangles non-ASCII output). Add them to your script. Bash on Linux/macOS doesn't need this. `rules.en.py` is pure ASCII and omits those lines.

The four rules are Karpathy's general minimal set; the exception covers the boundary the rules don't explicitly address. You can:

- Swap in domain-specific rules (frontend, data engineering, research code, a particular stack)
- Swap in team conventions
- Swap in personal style preferences
- Distill versions more precise for your own workflow

### Rule Design Trade-offs

A few trade-offs:

- **Length**: short rules save tokens and stay visually clean, but grounding is weaker and the model has more interpretive latitude; long rules give stronger compliance but pay a per-turn token cost, and attention to repeated content decays
- **Count**: fewer rules each get attended to, but coverage is narrower; more rules cover more ground, but later ones tend to get ignored
- **Specificity**: abstract rules ("don't write unnecessary code") apply broadly but leave interpretive room; specific rules ("don't add unrequested features, don't write abstractions for one-shot code") leave less room but only cover the shapes you list
- **Channel contrast**: CLAUDE.md is read once at session start, with distance decay in long sessions; hooks inject every turn with high weight and no decay, but pay token cost every turn

There's no single right version. The sweet spot depends on your session length distribution, token cost tolerance, workflow sensitivity to compliance, and review window. Run a few experiments yourself.

---

## Why These Four + the Exception

The four rules come from Andrej Karpathy's observations on LLM coding pitfalls — they target common failure modes:

- Rule 1 prevents: skipping confirmation, hiding assumptions in code, picking interpretations unilaterally
- Rule 2 prevents: over-engineering, adding unrequested features, premature abstraction
- Rule 3 prevents: drive-by refactors, formatting changes, modifying out-of-scope code
- Rule 4 prevents: writing implementation first and backfilling tests (goodharting)

Rules 1 and 4 are positive (what to do); rules 2 and 3 are negative (what not to do) — matching each rule's intrinsic direction.

The exception covers what the rules don't explicitly address. The original places it in a preamble ("For trivial tasks, use judgment"); this repo rewords it as "Exception: Trivial tasks only apply rules 2 and 3." — for a hook that repeats every turn, a more stable default is needed.

---

## Credits

The four rules are distilled from [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) — derived from Andrej Karpathy's observations on LLM coding pitfalls. The exception is reworded from the original CLAUDE.md preamble's "For trivial tasks, use judgment."

## License

MIT
