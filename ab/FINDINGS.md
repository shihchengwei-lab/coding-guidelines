# Findings: does the coding-guidelines hook actually help?

A/B harness experiments comparing the repo's hooks **on** vs **off**, headless,
across haiku / sonnet / opus. Date: 2026-06. n is small (repeat 3); read these
as direction, not decimals.

## TL;DR

- **On every task we could build, correctness was already 100% without the
  hook.** Across five escalating benchmark designs, no model — not even haiku —
  ever shipped a wrong answer on a well-specified task. So the hook had no
  mistakes to catch and could not improve outcomes.
- **The hook works as designed**: it reliably changes behavior, pushing
  test-writing from 0% (control) to 67–100% (hooks).
- **Its cost is modest on real-sized tasks** (+8% haiku, +15% sonnet, +64% opus
  on the 27-rule parser), but large on tiny tasks (~2.5–3×) — the overhead is
  relative to task size.
- **The Stop hook's anti-over-engineering effect is real but weak.** On
  open-ended "make it production-ready" prompts the arms finally diverge: the
  hook trims implementation bloat by ~10% on average (clear win on "robustify"
  framing, a consistent *reversal* on "make it flexible" framing). But it also
  adds tests, so total output is *larger* with the hook, not smaller.
- **Verdict**: on clean, solvable, well-specified tasks the hook is insurance
  with no payoff — the models don't make the mistakes it would catch. On
  open-ended tasks it nudges toward less bloat but inconsistently, and never
  makes the *total* diff smaller. Whether it's worth it depends on the
  messy/ambiguous/large-real-codebase regime, which a synthetic benchmark
  **cannot fairly measure**.

## What we tried (and why each round failed to discriminate)

The goal was a benchmark that (a) separates model strength and (b) leaves room
for the hook to help. To do (b) the control arm must sometimes fail. It never did.

| round | task design | result |
|---|---|---|
| 1 | easy edits (off-by-one, add flag, …) | all models 100%, identical diffs |
| 2 | canonical algorithms (wildcard DP, semver, LRU, topo, …) | all 100% — memorized |
| 3 | small multi-file bug-hunt (2 files) | all 100% |
| 4 | large cross-file bug-hunt (7 files, ~210 lines) | all 100%; only *turns* differed |
| 5 | 27-rule high-constraint parser (adversarial edge cases) | all 100% |

The structural lesson: **if a task can be specified precisely enough to grade
objectively, a 2026 frontier model can solve it.** Correctness is therefore the
wrong yardstick for this hook — it saturates.

(The model-strength gap is real and documented in large real-world evals; our
hand-rolled tasks simply never reached the difficulty where it shows. The one
hint we saw was effort: on the hardest task, turns-to-solve ordered
opus < sonnet < haiku — but n=1, treat as suggestive only.)

## Final A/B (27-rule parser, repeat 3)

| model | arm | score% | tests-written | turns | cost$ |
|---|---|---|---|---|---|
| haiku | hooks | 100% | 67% | 9.0 | 0.170 |
| haiku | control | 100% | 0% | 7.7 | 0.158 |
| sonnet | hooks | 100% | 100% | 9.7 | 0.513 |
| sonnet | control | 100% | 0% | 6.0 | 0.445 |
| opus | hooks | 100% | 100% | 8.0 | 0.767 |
| opus | control | 100% | 0% | 5.7 | 0.468 |

Same correctness in both arms; the hook's measurable effect is purely
behavioral (test-writing) and a modest cost increase.

## Over-engineering probe (the Stop hook's other job)

The Stop hook also reviews for over-engineering / scope creep. To test that, we
used tiny working seeds with deliberately open-ended prompts ("make it more
robust / flexible / production-ready") and no grader — the outcome is the diff
itself. Existing-file churn is the bloat signal; test/new-file churn is reported
separately. Repeat 3 (noisy).

Implementation churn (existing-file lines changed), averaged across 4 tasks:

| model | hooks | control | total churn incl. tests (hooks / control) |
|---|---|---|---|
| haiku | 67 | 78 | 159 / 134 |
| sonnet | 23 | 25 | 94 / 25 |
| opus | 30 | 34 | 91 / 34 |

- The hook trims implementation bloat ~10% on average — the first arm-difference
  in *output* seen anywhere in this project.
- It is task-dependent: a clear win on `tempconv` (control gold-plates to 127
  lines; hooks stays ~37), but a consistent *reversal* on `settings_get` (the
  "be flexible" framing makes the hook arm build *more*). Slugify / retry ≈ even.
- Total output is always *larger* with the hook, because it adds test files.
- Confound: on open-ended prompts the control arm sometimes barely engages
  (one settings_get rep changed 0 lines), which looks disciplined but is just
  non-engagement.

So the Stop hook does restrain over-engineering — weakly, inconsistently, and
without shrinking the overall diff.

## Honest limits

- We could not construct a fair, objectively-gradable task where the control
  arm fails, so we could not demonstrate the hook *improving* an outcome.
- The hook is designed for the regime we can't synthesize: ambiguous specs
  (where "state assumptions" helps), large unfamiliar codebases (where
  verification catches regressions), production code (where a silent wrong
  answer is expensive). We have **no evidence either way** for that regime.
- The only valid test of the regime that matters is to run hooks-on vs
  hooks-off **on your own real PRs/tasks** and judge the outcomes — synthetic
  benchmarks like this one structurally cannot.

## Reproduce

```bash
cd ab
# calibrate: does the control arm ever drop below 100%?
python3 run_ab.py --cases bench/constraints/cases.jsonl \
  --models haiku,sonnet,opus --arms control --repeat 3
# full A/B once a task has headroom
python3 run_ab.py --cases bench/constraints/cases.jsonl \
  --models haiku,sonnet,opus --arms hooks,control --repeat 3
```
