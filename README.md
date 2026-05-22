# Coding Guidelines Hook

> English | [中文](./README.zh-TW.md)

Two-stage hook for Claude Code: positive rules injected before each prompt (UserPromptSubmit), a self-review checklist injected when the agent tries to stop (Stop).

No reliance on the LLM reading CLAUDE.md. No enforcement framework. Just rules pasted into context at the moments they matter.

## What gets injected

**Before each prompt** (`rules.en.sh` / `rules.en.py`):

```
1. State assumptions before writing code
2. Write tests first, then write code to pass them

Exception: Trivial tasks skip both rules.
```

**Before the agent stops** (`review.en.sh` / `review.en.py`):

```
[Simplicity] Would a senior engineer call this diff too complex?
- Any abstractions written for one-shot code?
- Any unrequested flexibility/configuration?
- Any handling of errors that can't actually happen?

[Scope] Can every changed line be traced back to the user's original request this turn?
- Any drive-by edits to nearby code / comments / formatting?
- Any refactor of things that weren't broken?
- Any deletion of pre-existing dead code (mention only, don't delete)?

If any apply, fix it before stopping.
```

To customize, edit the scripts.

---

## Installation

See the official Claude Code hook docs:

- Hooks guide: https://docs.claude.com/en/docs/claude-code/hooks-guide
- Hooks reference: https://docs.claude.com/en/docs/claude-code/hooks

This repo provides:

- `rules.sh` / `rules.en.sh`, `review.sh` / `review.en.sh` — POSIX shell scripts (Chinese / English, for Linux / macOS / WSL / Git Bash)
- `rules.py` / `rules.en.py`, `review.py` / `review.en.py` — Python alternatives (Chinese / English, recommended for Windows native)
- `settings.example.json` — example configuration (UserPromptSubmit + Stop, Linux/macOS path style; points to the Chinese scripts by default — English users: substitute the `.en` variants)

### 1. Place the scripts in a fixed location

Linux / macOS / WSL / Git Bash:

```bash
mkdir -p ~/.claude/scripts
cp rules.en.sh review.en.sh ~/.claude/scripts/
chmod +x ~/.claude/scripts/rules.en.sh ~/.claude/scripts/review.en.sh
```

Windows (PowerShell):

```powershell
New-Item -ItemType Directory -Force -Path $HOME\.claude\scripts
Copy-Item rules.en.py, review.en.py $HOME\.claude\scripts\
```

### 2. Configure the Claude Code hooks

Merge the hook entries from `settings.example.json` into `~/.claude/settings.json`. For each event (`UserPromptSubmit`, `Stop`): if you already have that array, append the new hook block to its end; otherwise paste the whole block as-is.

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
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/scripts/review.en.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

Windows native: change each `command` to (replace `YOUR_NAME` with your Windows username):

```json
"command": "python C:/Users/YOUR_NAME/.claude/scripts/rules.en.py"
"command": "python C:/Users/YOUR_NAME/.claude/scripts/review.en.py"
```

Note: Windows native hooks don't always expand `~`, so use an absolute path here.

### 3. Restart Claude Code

### 4. Verify

Open a new session and try a clearly **non-trivial** request, e.g.:

> I want to build a small tool that reads a CSV, filters columns, and outputs JSON.

The agent should ask or state assumptions first (CSV encoding? column names? how filter conditions are specified? pretty-print output?) before writing code, rather than diving straight in. If the agent jumps to code without stating assumptions, the hook may not be active — check the script path, permissions, and `settings.json` syntax.

> Don't verify with a request like "write a sort function" — under the Trivial Exception, the agent doesn't need to state assumptions for such requests anyway, so you can't tell whether the hook failed or the rule was correctly applied.

When the agent finishes a turn, you should also see it self-check before stopping (the Stop hook injects the simplicity/scope checklist). If no self-check ever appears, the Stop hook may not be active.

---

## Customization

Rules live in `rules.sh` / `rules.py` and `review.sh` / `review.py` (and their `.en` variants). Just edit the strings.

> Non-ASCII users: if you rewrite the rules to contain CJK or other non-ASCII characters, look at `rules.py` — the two lines `import sys; sys.stdout.reconfigure(encoding="utf-8")` at the top are required for Windows native Python (the default stdout uses the system codepage, e.g. cp950, which mangles non-ASCII output). Add them to your script. Bash on Linux/macOS doesn't need this. `rules.en.py` is pure ASCII and omits those lines.

All four original rules are still present — split by stage. The pre-prompt hook keeps the two positive rules short (high attention every turn). The pre-stop hook takes the two negative rules ("don't write unnecessary code", "don't touch scope outside the target") and expands each into a 3-item self-check, because abstract negatives are too easy to declare compliance with at the top of a turn. The exception covers the boundary the pre-prompt rules don't explicitly address. You can:

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

## Why two stages

All four rules come from Andrej Karpathy's observations on LLM coding pitfalls. The split mirrors when each rule actually fires:

- **Pre-prompt** (positive, before writing): state assumptions, write tests first. These shape *how the agent starts*. Kept to 2 rules to stay short and high-attention every turn.
- **Pre-stop** (negative, before finishing): self-check for over-engineering and out-of-scope changes. These are easy to violate while writing and easy to skip if stated only at the top of a turn. Expanded into 3-item checklists each, because a single abstract negative ("don't write unnecessary code") is too easy to nod through — concrete questions ("any abstractions for one-shot code?") are harder to evade.

The exception only applies to the pre-prompt rules: for trivial tasks, asking for assumptions and tests is overhead. The pre-stop checklist always runs — over-engineering and scope creep are concerns regardless of task size.

---

## Credits

The rules are distilled from [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) — derived from Andrej Karpathy's observations on LLM coding pitfalls. The exception is reworded from the original CLAUDE.md preamble's "For trivial tasks, use judgment."

## License

MIT
