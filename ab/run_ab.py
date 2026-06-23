#!/usr/bin/env python3
"""A/B test harness for the coding-guidelines hooks.

Runs the same batch of prompts twice through headless Claude Code:

  arm "hooks"   -> this repo's UserPromptSubmit + Stop hooks enabled
  arm "control" -> no hooks ({"hooks": {}})

For each (case x arm) it captures the full stream-json transcript, extracts
deterministic behavioural signals (cost, turns, tool calls, whether tests ran,
whether the hook injections actually fired), and renders a side-by-side
Markdown comparison report. An optional LLM judge (--judge) scores each
transcript against a rubric derived from the rules.

This file is a thin shell around the real `claude` CLI. The parsing / signal /
report functions are pure and unit-tested in test_run_ab.py; the only impure
part is run_arm(), which shells out to `claude`.

Python 3, stdlib only.
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Static config
# ---------------------------------------------------------------------------

# Hook script filenames in the repo root, by language flavour.
SCRIPTS = {
    "en": {
        "UserPromptSubmit": ["rules.en.py", "inventory_gate.en.py"],
        "Stop": ["review.en.py"],
    },
    "zh": {
        "UserPromptSubmit": ["rules.py", "inventory_gate.py"],
        "Stop": ["review.py"],
    },
}

# Tools the headless agent is allowed to use without prompting.
ALLOWED_TOOLS = "Bash,Read,Write,Edit,Glob,Grep"

# Marker strings each hook injects. Their presence in the raw transcript is the
# robust "this hook actually fired" signal, independent of event schema.
HOOK_MARKERS = {
    "rules": "Write tests first",
    "inventory": "[Inventory]",
    "simplicity": "[Simplicity]",
    "scope": "[Scope]",
    "verification": "[Verification]",
}

# Bash commands that count as actually running a test / verification.
TEST_CMD_RE = re.compile(
    r"\b("
    r"pytest|unittest|python -m pytest|"
    r"npm (run )?test|yarn test|jest|vitest|"
    r"go test|cargo test|"
    r"make test|tox|"
    r"\./[\w/.-]*test[\w/.-]*"
    r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Pure: settings construction
# ---------------------------------------------------------------------------

def build_hook_block(repo_root, lang):
    """Build the UserPromptSubmit + Stop hooks block pointing at repo scripts."""
    scripts = SCRIPTS[lang]
    root = Path(repo_root).resolve()

    def entry(fname):
        path = root / fname
        return {
            "hooks": [
                {
                    "type": "command",
                    "command": f"python3 {shlex.quote(str(path))}",
                    "timeout": 5,
                }
            ]
        }

    block = {}
    for event, fnames in scripts.items():
        block[event] = [entry(f) for f in fnames]
    return block


def build_settings(repo_root, lang, arm):
    """Return the settings dict for an arm.

    arm "hooks"   -> our hooks wired up
    arm "control" -> hooks explicitly emptied (overrides any ambient user hooks)
    """
    if arm == "hooks":
        return {"hooks": build_hook_block(repo_root, lang)}
    if arm == "control":
        return {"hooks": {}}
    raise ValueError(f"unknown arm: {arm}")


# ---------------------------------------------------------------------------
# Pure: command construction
# ---------------------------------------------------------------------------

def build_command(prompt, settings_path, model, max_turns):
    """Build the headless `claude` argv for one run."""
    cmd = [
        "claude",
        "-p",
        prompt,
        "--settings",
        str(settings_path),
        "--permission-mode",
        "acceptEdits",
        "--allowedTools",
        ALLOWED_TOOLS,
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-hook-events",
    ]
    if model:
        cmd += ["--model", model]
    if max_turns:
        cmd += ["--max-turns", str(max_turns)]
    return cmd


# ---------------------------------------------------------------------------
# Pure: stream-json transcript parsing
# ---------------------------------------------------------------------------

def parse_stream(raw):
    """Parse a stream-json transcript (newline-delimited JSON).

    Returns a summary dict. Defensive: tolerates unknown event shapes and
    non-JSON lines (e.g. stray stderr that got merged in).
    """
    events = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    result_text = ""
    cost = None
    num_turns = None
    is_error = None
    tool_calls = []
    assistant_text = []

    for ev in events:
        etype = ev.get("type")
        if etype == "assistant":
            msg = ev.get("message", {})
            for block in msg.get("content", []) or []:
                btype = block.get("type")
                if btype == "tool_use":
                    tool_calls.append(
                        {
                            "name": block.get("name", ""),
                            "input": block.get("input", {}),
                        }
                    )
                elif btype == "text":
                    assistant_text.append(block.get("text", ""))
        elif etype == "result":
            result_text = ev.get("result", "") or result_text
            cost = ev.get("total_cost_usd", cost)
            num_turns = ev.get("num_turns", num_turns)
            is_error = ev.get("is_error", is_error)

    return {
        "result": result_text,
        "total_cost_usd": cost,
        "num_turns": num_turns,
        "is_error": is_error,
        "tool_calls": tool_calls,
        "assistant_text": "\n".join(assistant_text),
        "n_events": len(events),
    }


# ---------------------------------------------------------------------------
# Pure: signal extraction
# ---------------------------------------------------------------------------

def bash_commands(tool_calls):
    """Extract the command strings from Bash tool_use blocks."""
    cmds = []
    for tc in tool_calls:
        if tc.get("name") == "Bash":
            c = tc.get("input", {}).get("command", "")
            if c:
                cmds.append(c)
    return cmds


def parse_numstat(text, seed_files):
    """Parse `git diff --numstat` output, splitting existing vs new files.

    seed_files is the set of paths that existed at baseline. Changes to those
    are the scope-discipline signal; everything else is a newly added file
    (typically a test the agent wrote). Binary files (numstat '-') count as 0
    lines but still count as a touched file.
    """
    seed = set(seed_files)
    r = {
        "existing_files": 0, "existing_add": 0, "existing_del": 0,
        "new_files": 0, "new_add": 0, "new_del": 0,
    }
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        a, d, path = parts
        # Renames render as "old => new" (or "{a => b}"); attribute to new path.
        if "=>" in path:
            path = path.split("=>")[-1].strip().strip("}").strip()
        add = 0 if a == "-" else int(a)
        dele = 0 if d == "-" else int(d)
        if path in seed:
            r["existing_files"] += 1
            r["existing_add"] += add
            r["existing_del"] += dele
        else:
            r["new_files"] += 1
            r["new_add"] += add
            r["new_del"] += dele
    r["total_files"] = r["existing_files"] + r["new_files"]
    return r


def extract_signals(raw, parsed=None):
    """Derive deterministic behavioural signals from a raw transcript."""
    if parsed is None:
        parsed = parse_stream(raw)

    tool_calls = parsed["tool_calls"]
    names = [tc.get("name", "") for tc in tool_calls]
    cmds = bash_commands(tool_calls)

    hooks_fired = {k: (marker in raw) for k, marker in HOOK_MARKERS.items()}
    ran_tests = any(TEST_CMD_RE.search(c) for c in cmds)
    files_written = sum(1 for n in names if n in ("Write", "Edit"))

    # Weak text heuristics (flagged as heuristic in the report).
    text = parsed["assistant_text"].lower()
    mentions_assumptions = ("assum" in text) or ("?" in parsed["assistant_text"])

    return {
        "total_cost_usd": parsed["total_cost_usd"],
        "num_turns": parsed["num_turns"],
        "is_error": parsed["is_error"],
        "n_tool_calls": len(tool_calls),
        "tool_names": names,
        "files_written": files_written,
        "ran_tests": ran_tests,
        "hooks_fired": hooks_fired,
        "any_hook_fired": any(hooks_fired.values()),
        "mentions_assumptions": mentions_assumptions,
    }


# ---------------------------------------------------------------------------
# Pure: LLM-judge prompt + parsing
# ---------------------------------------------------------------------------

JUDGE_DIMENSIONS = [
    "stated_assumptions",
    "tests_first",
    "inventoried_existing",
    "scope_discipline",
    "avoided_overengineering",
]

JUDGE_INSTRUCTIONS = (
    "You are scoring a coding-agent transcript against a rubric. Score each "
    "dimension 0-2 (0=absent, 1=partial, 2=clearly done). Reply with ONLY a "
    "JSON object: {\"stated_assumptions\":n,\"tests_first\":n,"
    "\"inventoried_existing\":n,\"scope_discipline\":n,"
    "\"avoided_overengineering\":n,\"note\":\"one sentence\"}.\n\n"
    "Dimensions:\n"
    "- stated_assumptions: did the agent surface assumptions / ask clarifying "
    "questions before coding?\n"
    "- tests_first: did it write or run tests (ideally before the impl)?\n"
    "- inventoried_existing: did it check for existing assets before building "
    "new?\n"
    "- scope_discipline: did it stay within what was asked (no drive-by "
    "edits)?\n"
    "- avoided_overengineering: did it avoid needless abstraction / config?\n"
)


def parse_grade_output(stdout, returncode):
    """Parse a grader's result into a fractional score.

    Graders may print a line `SCORE k n` (k of n hidden sub-tests passed) for
    resolution; older pass/fail graders just exit 0/non-zero, treated as 1/1.
    """
    m = re.search(r"SCORE\s+(\d+)\s*/?\s*(\d+)", stdout or "")
    if m:
        passed, total = int(m.group(1)), int(m.group(2))
    else:
        passed, total = (1, 1) if returncode == 0 else (0, 1)
    return {
        "passed": passed,
        "total": total,
        "score": (passed / total) if total else None,
        "correct": total > 0 and passed == total,
    }


def build_judge_prompt(transcript_summary):
    """Build the prompt fed to the judge for one transcript."""
    return (
        JUDGE_INSTRUCTIONS
        + "\n--- TRANSCRIPT ---\n"
        + transcript_summary
        + "\n--- END TRANSCRIPT ---\n"
    )


def parse_judge_output(raw):
    """Parse the judge's JSON reply (tolerant of surrounding prose)."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    out = {}
    for dim in JUDGE_DIMENSIONS:
        if dim in data:
            try:
                out[dim] = int(data[dim])
            except (TypeError, ValueError):
                out[dim] = None
    out["note"] = data.get("note", "")
    return out


# ---------------------------------------------------------------------------
# Pure: report rendering
# ---------------------------------------------------------------------------

def _fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.4f}"
    if isinstance(v, bool):
        return "yes" if v else "no"
    return str(v)


def _churn(s):
    """Format existing-file churn as +A/-D, or '-' if not a benchmark run."""
    if "existing_add" not in s:
        return None
    return f"+{s['existing_add']}/-{s['existing_del']}"


def _new_churn(s):
    if "new_add" not in s:
        return None
    return f"+{s['new_add']}/-{s['new_del']}"


def _arms_in(by_arm):
    return [a for a in ("hooks", "control") if a in by_arm]


def render_case(case_id, prompt, by_arm):
    """Render one case's per-arm comparison as a Markdown section."""
    arms = _arms_in(by_arm)
    lines = [f"### {case_id}", "", f"> {prompt}", ""]

    has_bench = any(
        "total_files" in (by_arm.get(a, {}).get("signals") or {}) for a in arms
    )

    rows = []
    if has_bench:
        # The metrics the benchmark is actually about, first.
        rows += [
            ("correct (held-out test)", lambda s: s.get("correct")),
            ("existing files touched", lambda s: s.get("existing_files")),
            ("existing-file churn (+/-)", _churn),
            ("new files (e.g. tests)", lambda s: s.get("new_files")),
            ("new-file churn (+/-)", _new_churn),
        ]
    if has_bench:
        rows.insert(0, ("score (passed/total)",
                        lambda s: (f"{s['passed']}/{s['total']}"
                                   if "passed" in s else None)))
    rows += [
        ("hook injections fired", lambda s: s["any_hook_fired"]),
        ("turns", lambda s: s["num_turns"]),
        ("tool calls", lambda s: s["n_tool_calls"]),
        ("ran tests", lambda s: s["ran_tests"]),
        ("cost (USD-equiv)", lambda s: s["total_cost_usd"]),
        ("error", lambda s: s["is_error"]),
    ]

    lines.append("| signal | " + " | ".join(arms) + " |")
    lines.append("|" + "---|" * (1 + len(arms)))
    for label, getter in rows:
        cells = []
        for arm in arms:
            sig = by_arm.get(arm, {}).get("signals")
            cells.append(_fmt(getter(sig)) if sig else "-")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    # Judge scores, if present.
    if any(by_arm.get(a, {}).get("judge") for a in arms):
        lines += ["", "| judge dimension | " + " | ".join(arms) + " |",
                  "|" + "---|" * (1 + len(arms))]
        for dim in JUDGE_DIMENSIONS:
            cells = [_fmt((by_arm.get(arm, {}).get("judge") or {}).get(dim))
                     for arm in arms]
            lines.append(f"| {dim} | " + " | ".join(cells) + " |")

    lines.append("")
    return "\n".join(lines)


def _headline_metrics(has_bench):
    """The columns shown in the matrix, as (label, getter, kind)."""
    metrics = [("hook%", lambda s: 1 if s["any_hook_fired"] else 0, "rate")]
    if has_bench:
        metrics += [
            # score% is the discrimination metric: mean fraction of hidden
            # sub-tests passed. correct% is the all-or-nothing pass rate.
            ("score%", lambda s: s.get("score"), "rate"),
            ("correct%", lambda s: 1 if s.get("correct") else 0, "rate"),
            ("exist files", lambda s: s.get("existing_files"), "avg"),
            ("exist churn",
             lambda s: s.get("existing_add", 0) + s.get("existing_del", 0),
             "avg"),
            ("new files", lambda s: s.get("new_files"), "avg"),
        ]
    metrics += [
        ("tests%", lambda s: 1 if s["ran_tests"] else 0, "rate"),
        ("turns", lambda s: s["num_turns"], "avg"),
        ("cost$", lambda s: s["total_cost_usd"], "avg"),
    ]
    return metrics


def _agg_cell(rows, arm, getter, kind):
    """Aggregate one metric over rows (each a (model, id, prompt, by_arm))."""
    vals = [
        getter(r[3][arm]["signals"])
        for r in rows
        if r[3].get(arm, {}).get("signals") is not None
        and getter(r[3][arm]["signals"]) is not None
    ]
    if not vals:
        return "-"
    if kind == "rate":
        return f"{sum(vals) / len(vals):.0%}"
    return f"{sum(vals) / len(vals):.3g}"


def render_report(results, meta):
    """Render the matrix report. `results` is a list of
    (model, case_id, prompt, by_arm)."""
    models = []
    for r in results:
        if r[0] not in models:
            models.append(r[0])
    n_cases = len({r[1] for r in results})
    arms_present = [a for a in ("hooks", "control")
                    if any(a in r[3] for r in results)]
    has_bench = any(
        "total_files" in (r[3].get(a, {}).get("signals") or {})
        for r in results for a in ("hooks", "control")
    )
    metrics = _headline_metrics(has_bench)

    lines = [
        "# A/B report: coding-guidelines hooks",
        "",
        f"- generated: {meta.get('generated', '')}",
        f"- models: {', '.join(str(m) for m in models)}",
        f"- lang: {meta.get('lang', '')}",
        f"- cases: {n_cases}",
        f"- judge: {'on' if meta.get('judge') else 'off'}",
        "",
        "Arm **hooks** = this repo's hooks enabled. Arm **control** = no hooks.",
        "",
        "## Matrix (averaged across cases)",
        "",
    ]
    header = "| model | arm | " + " | ".join(m[0] for m in metrics) + " |"
    lines += [header, "|" + "---|" * (2 + len(metrics))]
    for model in models:
        mrows = [r for r in results if r[0] == model]
        for arm in arms_present:
            cells = [_agg_cell(mrows, arm, g, k) for _, g, k in metrics]
            lines.append(f"| {model} | {arm} | " + " | ".join(cells) + " |")

    for model in models:
        lines += ["", f"## Detail: {model}", ""]
        for r in results:
            if r[0] == model:
                lines.append(render_case(r[1], r[2], r[3]))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Impure: running an arm via the real claude CLI
# ---------------------------------------------------------------------------

def load_cases(path):
    """Load cases; resolve optional seed/grade paths relative to the manifest."""
    base = Path(path).resolve().parent
    cases = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            obj = json.loads(line)
            if obj.get("seed"):
                obj["seed_abs"] = str((base / obj["seed"]).resolve())
            if obj.get("grade"):
                obj["grade_abs"] = str((base / obj["grade"]).resolve())
            cases.append(obj)
    return cases


def _git(ws, *args):
    return subprocess.run(
        ["git", "-C", str(ws), *args], capture_output=True, text=True)


# Generated/VCS junk that must never enter the seed baseline or the diff.
COPY_EXCLUDE = {"__pycache__", ".git", ".pytest_cache", ".mypy_cache"}


def copy_seed(seed_dir, ws):
    """Copy seed files into ws, skipping generated/VCS junk.

    Returns the list of seed-relative file paths (the baseline file set), used
    later to tell existing-file edits from newly created files. Pure w.r.t. the
    network; touches only the filesystem.
    """
    ws.mkdir(parents=True, exist_ok=True)
    seed_files = []
    if not seed_dir:
        return seed_files
    seed_root = Path(seed_dir)
    for src in sorted(seed_root.rglob("*")):
        rel = src.relative_to(seed_root)
        if any(part in COPY_EXCLUDE for part in rel.parts) or rel.suffix == ".pyc":
            continue
        if src.is_file():
            dst = ws / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
            seed_files.append(str(rel))
    return seed_files


def prepare_workspace(ws, seed_dir):
    """Copy seed into a fresh git workspace and commit a baseline."""
    seed_files = copy_seed(seed_dir, ws)
    # Keep generated bytecode out of the post-run diff entirely.
    (ws / ".gitignore").write_text(
        "\n".join(sorted(COPY_EXCLUDE)) + "\n*.pyc\n", encoding="utf-8")
    _git(ws, "init", "-q")
    _git(ws, "add", "-A")
    _git(ws, "-c", "user.email=ab@local", "-c", "user.name=ab",
         "commit", "-q", "--allow-empty", "-m", "baseline")
    return seed_files


def diff_numstat(ws):
    """Return `git diff --numstat` of the workspace vs baseline (incl. new files)."""
    _git(ws, "add", "-A")
    return _git(ws, "diff", "--numstat", "--cached", "HEAD").stdout


def run_grade(grade_abs, ws, timeout):
    """Run the held-out grader. Returns a fractional-score dict, or None."""
    if not grade_abs:
        return None
    proc = subprocess.run(
        [sys.executable, str(grade_abs), str(ws)],
        capture_output=True, text=True, timeout=timeout)
    return parse_grade_output(proc.stdout, proc.returncode)


def run_arm(prompt, settings, settings_path, cwd, model, max_turns, timeout):
    """Run one arm; return (raw_transcript, stderr). Impure: shells out."""
    settings_path.write_text(json.dumps(settings), encoding="utf-8")
    cmd = build_command(prompt, settings_path, model, max_turns)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.stdout, proc.stderr


def run_judge(transcript_summary, model, timeout):
    """Run the LLM judge over one transcript. Impure."""
    prompt = build_judge_prompt(transcript_summary)
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--settings",
        '{"hooks": {}}',
    ]
    if model:
        cmd += ["--model", model]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    try:
        payload = json.loads(proc.stdout)
        return parse_judge_output(payload.get("result", ""))
    except json.JSONDecodeError:
        return parse_judge_output(proc.stdout)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent
    ap.add_argument("--cases", default=str(here / "bench" / "cases.jsonl"))
    ap.add_argument("--repo-root", default=str(here.parent))
    ap.add_argument("--lang", choices=["en", "zh"], default="en")
    ap.add_argument("--model", default=None, help="single model, e.g. sonnet")
    ap.add_argument("--models", default=None,
                    help="comma-separated model matrix, e.g. haiku,sonnet,opus")
    ap.add_argument("--max-turns", type=int, default=30)
    ap.add_argument("--timeout", type=int, default=900, help="per-run seconds")
    ap.add_argument("--out", default=str(here / "runs"))
    ap.add_argument("--repeat", type=int, default=1, help="runs per (case,arm)")
    ap.add_argument("--arms", default="hooks,control",
                    help="comma list; use 'control' alone to calibrate")
    ap.add_argument("--judge", action="store_true", help="run LLM judge")
    ap.add_argument("--judge-model", default=None)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="print the commands that would run, execute nothing",
    )
    args = ap.parse_args(argv)

    cases = load_cases(args.cases)
    models = (
        [m.strip() for m in args.models.split(",") if m.strip()]
        if args.models else [args.model]
    )
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_root = Path(args.out) / stamp
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]

    def model_dir(model):
        return model or "default"

    if args.dry_run:
        print(f"# dry-run: {len(models)} model(s) x {len(cases)} cases x "
              f"{len(arms)} arms x {args.repeat} repeat(s)\n")
        for model in models:
            for case in cases:
                for arm in arms:
                    settings = build_settings(args.repo_root, args.lang, arm)
                    cmd = build_command(case["prompt"], "<workdir>/settings.json",
                                        model, args.max_turns)
                    print(f"## [{model_dir(model)}] {case['id']} [{arm}]")
                    if case.get("seed"):
                        print("seed:", case["seed"], "| grade:",
                              case.get("grade"))
                    print("cmd:", " ".join(shlex.quote(c) for c in cmd))
                    print()
        return 0

    out_root.mkdir(parents=True, exist_ok=True)
    results = []

    for model in models:
        for case in cases:
            # Collect per-rep signals for each arm, then emit one result row per
            # rep so the matrix aggregation averages across repetitions (taming
            # single-run noise) instead of keeping only the last.
            per_arm_reps = {arm: [] for arm in arms}
            for arm in arms:
                settings = build_settings(args.repo_root, args.lang, arm)
                for rep in range(args.repeat):
                    workdir = (out_root / model_dir(model) / case["id"]
                               / arm / f"rep{rep}")
                    workdir.mkdir(parents=True, exist_ok=True)
                    ws = workdir / "ws"
                    seed_files = prepare_workspace(ws, case.get("seed_abs"))
                    print(f"[run] {model_dir(model)} {case['id']} {arm} "
                          f"rep{rep} ...", file=sys.stderr)
                    try:
                        raw, err = run_arm(
                            case["prompt"], settings,
                            workdir / "settings.json", ws,
                            model, args.max_turns, args.timeout,
                        )
                    except subprocess.TimeoutExpired:
                        raw, err = "", "TIMEOUT"
                    (workdir / "transcript.jsonl").write_text(
                        raw, encoding="utf-8")
                    (workdir / "stderr.log").write_text(
                        err or "", encoding="utf-8")
                    parsed = parse_stream(raw)
                    signals = extract_signals(raw, parsed)
                    # Ground-truth diff + correctness from the workspace.
                    signals.update(parse_numstat(diff_numstat(ws), seed_files))
                    try:
                        grade = run_grade(
                            case.get("grade_abs"), ws, args.timeout)
                    except subprocess.TimeoutExpired:
                        grade = None
                    if grade:
                        signals.update(grade)
                    (workdir / "signals.json").write_text(
                        json.dumps(signals, indent=2), encoding="utf-8")

                    judge = None
                    if args.judge:
                        summary = parsed["assistant_text"] or parsed["result"]
                        if summary:
                            try:
                                judge = run_judge(
                                    summary, args.judge_model or model,
                                    args.timeout)
                            except subprocess.TimeoutExpired:
                                judge = None
                    per_arm_reps[arm].append(
                        {"signals": signals, "judge": judge})

            for rep in range(args.repeat):
                by_arm = {arm: per_arm_reps[arm][rep] for arm in arms}
                rid = case["id"] if args.repeat == 1 else f"{case['id']}#r{rep}"
                results.append((model_dir(model), rid, case["prompt"], by_arm))

        # Write/refresh the report after each model so partial results survive.
        meta = {"generated": stamp, "lang": args.lang, "judge": args.judge}
        report = render_report(results, meta)
        (out_root / "report.md").write_text(report, encoding="utf-8")

    print(f"\nReport: {out_root / 'report.md'}")
    print(render_report(results, {"generated": stamp, "lang": args.lang,
                                  "judge": args.judge}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
