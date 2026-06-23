# A/B harness for the hooks

Does enabling these hooks actually change how the agent behaves? This harness
answers that empirically: it runs the same batch of prompts twice through
headless Claude Code and compares the two runs.

- **arm `hooks`** — this repo's `UserPromptSubmit` + `Stop` hooks enabled
- **arm `control`** — no hooks (`{"hooks": {}}`)

It is a thin shell around the real `claude` CLI. It does **not** bundle a model;
running real arms spends API tokens and is non-deterministic. The parsing /
signal / report logic is pure and unit-tested (`test_run_ab.py`).

## Requirements

- Python 3 (stdlib only)
- The `claude` CLI on `PATH`, logged in / configured

## Use

Preview the exact commands without spending anything:

```bash
python3 run_ab.py --dry-run
```

Run the full batch (5 cases x 2 arms) and write a report:

```bash
python3 run_ab.py --model sonnet
# -> ab/runs/<timestamp>/report.md  (also printed to stdout)
```

Add the optional LLM judge (extra `claude` calls, extra cost) to score each
transcript against the rules' rubric:

```bash
python3 run_ab.py --model sonnet --judge
```

Useful flags: `--lang en|zh` (which script flavour to test), `--repeat N`
(runs per cell — A/B with n=1 is noisy), `--max-turns`, `--cases <file>`,
`--out <dir>`.

## What it measures

Each run is captured as a `stream-json` transcript. Deterministic signals
(always on):

- **hook injections fired** — whether the known marker strings (`[Inventory]`,
  `[Simplicity]`, `Write tests first`, ...) appear. This confirms the arm `hooks`
  actually injected and arm `control` did not.
- **ran tests** — whether a real test command (`pytest`, `go test`, ...) ran
- **turns / tool calls / files written / cost / error**
- **mentions assumptions** — weak text heuristic, flagged as such

LLM judge (opt-in) scores 0-2 on: stated assumptions, tests first, inventoried
existing, scope discipline, avoided over-engineering.

## Layout

```
cases.jsonl     # the prompt batch (one JSON object per line)
run_ab.py       # runner + pure parse/signal/report functions
test_run_ab.py  # unit tests for the pure functions
runs/           # per-run output: transcripts, signals, report.md (gitignored)
```

## Caveats

- Behavioural signals beyond "did the hook fire" are heuristic; the judge is an
  LLM and itself noisy. Use `--repeat` and read the transcripts, don't trust a
  single number.
- Each cell runs in its own temp working dir so file edits don't cross-
  contaminate, but the arms still share your machine state otherwise.
