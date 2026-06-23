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


def render_case(case_id, prompt, by_arm):
    """Render one case's two-arm comparison as a Markdown section."""
    arms = ["hooks", "control"]
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
    rows += [
        ("hook injections fired", lambda s: s["any_hook_fired"]),
        ("turns", lambda s: s["num_turns"]),
        ("tool calls", lambda s: s["n_tool_calls"]),
        ("ran tests", lambda s: s["ran_tests"]),
        ("cost (USD-equiv)", lambda s: s["total_cost_usd"]),
        ("error", lambda s: s["is_error"]),
    ]

    lines.append("| signal | hooks | control |")
    lines.append("|---|---|---|")
    for label, getter in rows:
        cells = []
        for arm in arms:
            sig = by_arm.get(arm, {}).get("signals")
            cells.append(_fmt(getter(sig)) if sig else "-")
        lines.append(f"| {label} | {cells[0]} | {cells[1]} |")

    # Judge scores, if present.
    judged = any(by_arm.get(a, {}).get("judge") for a in arms)
    if judged:
        lines += ["", "| judge dimension | hooks | control |", "|---|---|---|"]
        for dim in JUDGE_DIMENSIONS:
            cells = []
            for arm in arms:
                j = by_arm.get(arm, {}).get("judge") or {}
                cells.append(_fmt(j.get(dim)))
            lines.append(f"| {dim} | {cells[0]} | {cells[1]} |")

    lines.append("")
    return "\n".join(lines)


def render_report(results, meta):
    """Render the full report. `results` is a list of (case_id, prompt, by_arm)."""
    lines = [
        "# A/B report: coding-guidelines hooks",
        "",
        f"- generated: {meta.get('generated', '')}",
        f"- model: {meta.get('model', '')}",
        f"- lang: {meta.get('lang', '')}",
        f"- cases: {len(results)}",
        f"- judge: {'on' if meta.get('judge') else 'off'}",
        "",
        "Arm **hooks** = this repo's hooks enabled. Arm **control** = no hooks.",
        "",
        "## Aggregate",
        "",
    ]

    # Aggregate a few headline numbers across cases.
    def agg(arm, getter):
        vals = [
            getter(c[2][arm]["signals"])
            for c in results
            if c[2].get(arm, {}).get("signals") is not None
            and getter(c[2][arm]["signals"]) is not None
        ]
        return vals

    has_bench = any(
        "total_files" in (c[2].get(a, {}).get("signals") or {})
        for c in results for a in ("hooks", "control")
    )

    lines += ["| metric | hooks | control |", "|---|---|---|"]
    headline = [
        ("hook fired rate", lambda s: 1 if s["any_hook_fired"] else 0, "rate"),
    ]
    if has_bench:
        headline += [
            ("correct rate", lambda s: 1 if s.get("correct") else 0, "rate"),
            ("avg existing files touched",
             lambda s: s.get("existing_files"), "avg"),
            ("avg existing-file churn (lines)",
             lambda s: (s.get("existing_add", 0) + s.get("existing_del", 0)),
             "avg"),
            ("avg new files", lambda s: s.get("new_files"), "avg"),
        ]
    headline += [
        ("ran-tests rate", lambda s: 1 if s["ran_tests"] else 0, "rate"),
        ("avg turns", lambda s: s["num_turns"], "avg"),
        ("avg cost (USD-equiv)", lambda s: s["total_cost_usd"], "avg"),
    ]
    for label, getter, kind in headline:
        cells = []
        for arm in ("hooks", "control"):
            vals = agg(arm, getter)
            if not vals:
                cells.append("-")
            elif kind == "rate":
                cells.append(f"{sum(vals) / len(vals):.0%}")
            else:
                cells.append(f"{sum(vals) / len(vals):.4g}")
        lines.append(f"| {label} | {cells[0]} | {cells[1]} |")

    lines += ["", "## Per case", ""]
    for case_id, prompt, by_arm in results:
        lines.append(render_case(case_id, prompt, by_arm))

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


def prepare_workspace(ws, seed_dir):
    """Copy seed into a fresh git workspace and commit a baseline.

    Returns the list of seed-relative file paths (the baseline file set), used
    later to tell existing-file edits from newly created files.
    """
    ws.mkdir(parents=True, exist_ok=True)
    seed_files = []
    if seed_dir:
        seed_root = Path(seed_dir)
        for src in sorted(seed_root.rglob("*")):
            if src.is_file():
                rel = src.relative_to(seed_root)
                dst = ws / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
                seed_files.append(str(rel))
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
    """Run the held-out grader against the workspace. True=correct, None=no grader."""
    if not grade_abs:
        return None
    proc = subprocess.run(
        [sys.executable, str(grade_abs), str(ws)],
        capture_output=True, text=True, timeout=timeout)
    return proc.returncode == 0


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
    ap.add_argument("--model", default=None, help="e.g. sonnet, opus")
    ap.add_argument("--max-turns", type=int, default=30)
    ap.add_argument("--timeout", type=int, default=900, help="per-run seconds")
    ap.add_argument("--out", default=str(here / "runs"))
    ap.add_argument("--repeat", type=int, default=1, help="runs per (case,arm)")
    ap.add_argument("--judge", action="store_true", help="run LLM judge")
    ap.add_argument("--judge-model", default=None)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="print the commands that would run, execute nothing",
    )
    args = ap.parse_args(argv)

    cases = load_cases(args.cases)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_root = Path(args.out) / stamp
    arms = ["hooks", "control"]

    if args.dry_run:
        print(f"# dry-run: {len(cases)} cases x {len(arms)} arms x "
              f"{args.repeat} repeat(s)\n")
        for case in cases:
            for arm in arms:
                settings = build_settings(args.repo_root, args.lang, arm)
                cmd = build_command(case["prompt"], "<workdir>/settings.json",
                                    args.model, args.max_turns)
                print(f"## {case['id']} [{arm}]")
                if case.get("seed"):
                    print("seed:", case["seed"], "| grade:", case.get("grade"))
                print("settings:", json.dumps(settings))
                print("cmd:", " ".join(shlex.quote(c) for c in cmd))
                print()
        return 0

    out_root.mkdir(parents=True, exist_ok=True)
    results = []

    for case in cases:
        by_arm = {}
        for arm in arms:
            # For repeat>1 we keep the last run's signals but could average;
            # default repeat=1 keeps it simple and honest.
            settings = build_settings(args.repo_root, args.lang, arm)
            last_signals = None
            last_summary = None
            for rep in range(args.repeat):
                workdir = out_root / case["id"] / arm / f"rep{rep}"
                workdir.mkdir(parents=True, exist_ok=True)
                ws = workdir / "ws"
                seed_files = prepare_workspace(ws, case.get("seed_abs"))
                print(f"[run] {case['id']} {arm} rep{rep} ...",
                      file=sys.stderr)
                try:
                    raw, err = run_arm(
                        case["prompt"], settings,
                        workdir / "settings.json", ws,
                        args.model, args.max_turns, args.timeout,
                    )
                except subprocess.TimeoutExpired:
                    raw, err = "", "TIMEOUT"
                (workdir / "transcript.jsonl").write_text(raw, encoding="utf-8")
                (workdir / "stderr.log").write_text(err or "", encoding="utf-8")
                parsed = parse_stream(raw)
                last_signals = extract_signals(raw, parsed)
                # Ground-truth diff + correctness from the workspace.
                last_signals.update(parse_numstat(diff_numstat(ws), seed_files))
                try:
                    last_signals["correct"] = run_grade(
                        case.get("grade_abs"), ws, args.timeout)
                except subprocess.TimeoutExpired:
                    last_signals["correct"] = None
                last_summary = parsed["assistant_text"] or parsed["result"]
                (workdir / "signals.json").write_text(
                    json.dumps(last_signals, indent=2), encoding="utf-8")

            judge = None
            if args.judge and last_summary:
                try:
                    judge = run_judge(
                        last_summary, args.judge_model or args.model,
                        args.timeout)
                except subprocess.TimeoutExpired:
                    judge = None
            by_arm[arm] = {"signals": last_signals, "judge": judge}

        results.append((case["id"], case["prompt"], by_arm))

    meta = {
        "generated": stamp,
        "model": args.model or "(default)",
        "lang": args.lang,
        "judge": args.judge,
    }
    report = render_report(results, meta)
    report_path = out_root / "report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport: {report_path}")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
