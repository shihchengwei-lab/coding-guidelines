# A/B harness for the hooks

Does enabling these hooks actually change how the agent behaves — and does it
make the agent **change less code** while still getting the task **right**? This
harness answers that empirically: it runs the same tasks twice through headless
Claude Code and compares the two runs.

- **arm `hooks`** — this repo's `UserPromptSubmit` + `Stop` hooks enabled
- **arm `control`** — no hooks (`{"hooks": {}}`)

It is a thin shell around the real `claude` CLI. It does **not** bundle a model.
On a metered API key, running real arms costs money; on a Max/Pro subscription it
draws down your usage window instead. Either way the parsing / signal / report
logic is pure and unit-tested (`test_run_ab.py`).

## Requirements

- Python 3 (stdlib only) and `git`
- The `claude` CLI on `PATH`, logged in / configured

## Use

Preview the exact commands without spending anything:

```bash
python3 run_ab.py --dry-run
```

Run the benchmark (default: `bench/cases.jsonl`, 3 cases x 2 arms):

```bash
python3 run_ab.py --model sonnet
# -> ab/runs/<timestamp>/report.md  (also printed to stdout)
```

Useful flags: `--lang en|zh` (which script flavour to test), `--repeat N`
(runs per cell — A/B with n=1 is noisy, repeat to average out), `--max-turns`,
`--cases <file>`, `--out <dir>`, `--judge` (opt-in LLM rubric pass, extra cost).

## The benchmark

`bench/cases.jsonl` is a suite of **modification** tasks — the kind where scope
discipline actually shows up. Each case seeds an existing codebase, asks for a
small change, and is graded by a **held-out test the agent never sees**:

```
bench/<case>/seed/        # copied into the agent's git workspace; it edits this
bench/<case>/grade_test.py # run AFTER, against the workspace, to grade correctness
```

Why modification tasks, not "build X from scratch"? On greenfield tasks the
hooks arm usually writes *more* (it adds tests), so "smaller diff" is the wrong
lens. The hooks' scope/simplicity review bites when there's **existing code to
not over-touch** — so that's what the benchmark measures.

You can point `--cases` at any JSONL manifest. Each line is
`{"id", "prompt"}` plus optional `"seed"` and `"grade"` (paths relative to the
manifest). Omit seed/grade for a plain greenfield prompt (see `cases.jsonl`).

## What it measures

Each run executes in a fresh `git` workspace (seed committed as the baseline),
so the diff is ground truth, not a guess.

**Benchmark metrics** (when a case has seed/grade):

- **correct** — did the held-out test pass? (changing less is worthless if wrong)
- **existing files touched** — distinct pre-existing files in the diff → *"did
  it touch fewer files?"*
- **existing-file churn (+/-)** — lines added/removed in pre-existing files →
  *"is the diff smaller?"*
- **new files / new-file churn** — counted **separately**, because the hooks arm
  legitimately adds test files ("write tests first") and that shouldn't be
  conflated with scope creep on existing code.

**Always-on signals** (from the `stream-json` transcript):

- **hook injections fired** — whether the marker strings (`[Inventory]`,
  `[Simplicity]`, `Write tests first`, ...) appear. Confirms arm `hooks` injected
  and arm `control` did not.
- **ran tests**, **turns**, **tool calls**, **cost (USD-equiv)**, **error**

LLM judge (`--judge`, opt-in) scores 0-2 on: stated assumptions, tests first,
inventoried existing, scope discipline, avoided over-engineering.

## Layout

```
bench/          # the modification benchmark (seeds + held-out graders + cases.jsonl)
cases.jsonl     # alternative greenfield prompt batch (no seed/grade)
run_ab.py       # runner + pure parse/signal/diff/report functions
test_run_ab.py  # unit tests for the pure functions
runs/           # per-run output: workspace, transcript, signals, report.md (gitignored)
```

## Caveats

- `cost (USD-equiv)` is what the CLI computes at API rates; on a subscription
  it's a usage-magnitude proxy, not a bill.
- Correctness is ground truth; the diff metrics are ground truth; the judge is an
  LLM and itself noisy. Use `--repeat` and read the transcripts — don't trust a
  single number.
- Each cell runs in its own git workspace so edits don't cross-contaminate, but
  the arms still share your machine state otherwise.
