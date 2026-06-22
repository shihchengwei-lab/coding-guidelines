# Coding Guidelines Hook

> English | [中文](./README.zh-TW.md)

Two-stage hook for Claude Code. **Before each prompt** (UserPromptSubmit): always-on positive rules, plus a keyword-gated reminder that fires only when you're about to build something new. **When the agent tries to stop** (Stop): a self-review checklist. The Stop hook uses `exit 2` so the checklist is forced into the agent's view, and the agent takes one more pass before actually stopping.

No reliance on the LLM reading CLAUDE.md. No external framework — just text fed into Claude Code's built-in hooks.

## What gets injected

**Before each prompt** (`rules.en.py`):

```
1. Break the task down to its most fundamental requirements before writing code, then state assumptions
2. Write tests first, then write code to pass them

Exception: Trivial tasks skip both rules.
```

**Before each prompt, but only when you're about to build something new** (`inventory_gate.en.py`):

```
[Inventory] "Build something new" detected -- inventory outward-in before you build; most "I need a new X" already exists in one of the first 4 layers:

1. Does this even need doing? -- is the task itself redundant? Can the goal be met by "not doing it" or "doing something else"?
2. Built into the language/platform? -- stdlib, shell builtin, OS, or the framework itself may already provide it.
3. Already-installed dependency? -- check package.json / requirements.txt / Cargo.toml / go.mod; don't rewrite what's already a dep.
4. Already in this repo? -- ls/glob the relevant dirs and grep the keywords to see if it's already implemented.
5. None of layers 1-4 cover it -> then build, and note why each prior layer was not enough.

Can extend what exists -> extend it (one less thing to maintain). "Inventory first, then decide whether to build" is the first gate of subtraction discipline.
```

Unlike the always-on rules, this one is keyword-gated: it fires only when the prompt matches "build something new" phrasing (`create a`, `build a`, `implement a`, ...), so it adds no weight to turns that aren't about building.

**Before the agent stops** (`review.en.py`):

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

The review script also does two things beyond printing the checklist:

1. **Doc-only filtering** — if every edit in the turn targets documentation files (`.md`, `.txt`, `.json`, `.yml`, `.yaml`, `.toml`) or paths inside `.claude/`, the checklist is skipped entirely. This avoids false triggers when editing READMEs, config, or hook settings.

2. **Verification check** — when code was edited but no test or verification command was run afterward, a third section is appended:

```
[Verification] Code was edited this turn but no test or verification command was run.
- Run relevant tests to confirm nothing is broken.
- If no test coverage exists, say so explicitly.
```

Read-only commands (`ls`, `cat`, `git status`, `git diff`, `git log`, etc.) don't count as verification — the agent must have actually run something (tests, build, lint, a script) to clear this check.

To customize, edit the scripts.

---

## Installation

See the official Claude Code hook docs:

- Hooks guide: https://docs.claude.com/en/docs/claude-code/hooks-guide
- Hooks reference: https://docs.claude.com/en/docs/claude-code/hooks

This repo provides:

- `rules.py` / `rules.en.py`, `inventory_gate.py` / `inventory_gate.en.py`, `review.py` / `review.en.py` — Python scripts (Chinese / English). Requires Python 3 (any modern version).
- `settings.example.json` — example configuration (UserPromptSubmit + Stop, Linux/macOS path style; points to the Chinese scripts by default — English users: substitute the `.en` variants)

### 1. Place the scripts in a fixed location

Linux / macOS / WSL:

```bash
mkdir -p ~/.claude/scripts
cp rules.en.py inventory_gate.en.py review.en.py ~/.claude/scripts/
```

Windows (PowerShell):

```powershell
New-Item -ItemType Directory -Force -Path $HOME\.claude\scripts
Copy-Item rules.en.py, inventory_gate.en.py, review.en.py $HOME\.claude\scripts\
```

### 2. Configure the Claude Code hooks

Merge the hook entries from `settings.example.json` into `~/.claude/settings.json`. For each event (`UserPromptSubmit`, `Stop`): if you already have that array, append the new hook block to its end; otherwise paste the whole block as-is.

Linux / macOS / WSL — `python3` and the `~` path expansion both work:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/scripts/rules.en.py",
            "timeout": 5
          }
        ]
      },
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/scripts/inventory_gate.en.py",
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
            "command": "python3 ~/.claude/scripts/review.en.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

Windows native — use `python` and an absolute path (Windows hooks don't always expand `~`; replace `YOUR_NAME` with your Windows username):

```json
"command": "python C:/Users/YOUR_NAME/.claude/scripts/rules.en.py"
"command": "python C:/Users/YOUR_NAME/.claude/scripts/inventory_gate.en.py"
"command": "python C:/Users/YOUR_NAME/.claude/scripts/review.en.py"
```

### 3. Restart Claude Code

### 4. Verify

Open a new session and try a clearly **non-trivial** request, e.g.:

> I want to build a small tool that reads a CSV, filters columns, and outputs JSON.

The agent should ask or state assumptions first (CSV encoding? column names? how filter conditions are specified? pretty-print output?) before writing code, rather than diving straight in. If the agent jumps to code without stating assumptions, the hook may not be active — check the script path, permissions, and `settings.json` syntax.

Because that example says "build a", the inventory gate also fires: you should see the agent check whether a similar tool already exists (a quick `ls`/`grep`) before writing a new one, rather than building from scratch unprompted.

> Don't verify with a request like "write a sort function" — under the Trivial Exception, the agent doesn't need to state assumptions for such requests anyway, so you can't tell whether the hook failed or the rule was correctly applied.

When the agent finishes a turn, you should also see it self-check before stopping (the Stop hook injects the simplicity/scope checklist). If no self-check ever appears, the Stop hook may not be active.

---

## Customization

Rules live in `rules.py` and `review.py` (and their `.en` variants). Just edit the strings. The inventory gate (`inventory_gate.py`) also has a `TRIGGER` keyword list you can widen or narrow to control when it fires.

> Non-ASCII users: if you rewrite the rules to contain CJK or other non-ASCII characters, look at `rules.py` — the two lines `import sys; sys.stdout.reconfigure(encoding="utf-8")` at the top are required for Windows native Python (the default stdout uses the system codepage, e.g. cp950, which mangles non-ASCII output). Linux/macOS don't strictly need this, but leaving it in is harmless. `rules.en.py` is pure ASCII and omits those lines.

The rules come in two flavors. Positive ones ("do X before writing") go in the pre-prompt hook, short for high attention every turn. Negative ones ("don't write unnecessary code", "don't touch scope outside the target") go in the pre-stop hook as concrete self-check items, because abstract negatives are too easy to nod through at the top of a turn — concrete questions ("any abstractions for one-shot code?") are harder to evade. The exception covers the boundary the pre-prompt rules don't explicitly address. You can:

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

The rules are drawn from Andrej Karpathy's observations on LLM coding pitfalls. They split naturally by when they fire:

- **Pre-prompt** (positive, before writing): state assumptions, write tests first. These shape *how the agent starts* — short rules stay high-attention every turn. A second pre-prompt hook, the inventory gate, is keyword-gated rather than always-on: it fires only when you're about to build something new, nudging a check for existing assets before reinventing — kept conditional so it doesn't dilute the short always-on rules.
- **Pre-stop** (negative, before finishing): self-check for over-engineering and out-of-scope changes. These are easy to violate mid-stream and easy to skip if stated only as a single abstract negative at the start. Concrete questions ("any abstractions for one-shot code?") are harder to evade than "don't write unnecessary code."

The exception only applies to the pre-prompt rules: for trivial tasks, asking for assumptions and tests is overhead. The pre-stop checklist runs whenever the agent tries to stop, but skips turns that didn't edit code (pure-conversation turns and doc-only turns stay quiet). It also checks whether the agent ran any verification command after the last code edit, and injects an extra `[Verification]` reminder if not.

---

## Credits

The rules are distilled from [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) — derived from Andrej Karpathy's observations on LLM coding pitfalls. The exception is reworded from the original CLAUDE.md preamble's "For trivial tasks, use judgment."

## License

MIT
