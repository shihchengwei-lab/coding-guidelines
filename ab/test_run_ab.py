#!/usr/bin/env python3
"""Unit tests for the pure functions in run_ab.py.

These cover everything that does NOT shell out to `claude`: settings/command
construction, stream-json parsing, signal extraction, judge prompt/parse, and
report rendering. Run: python3 -m unittest ab.test_run_ab  (or run this file).
"""

import json
import os
import sys
import unittest

# Work whether invoked from inside ab/ or as `python3 -m unittest ab.test_run_ab`
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_ab


def stream(*events):
    return "\n".join(json.dumps(e) for e in events)


# A minimal but realistic stream-json transcript: the agent asks/states
# assumptions, writes a file, runs pytest, then a result event.
HOOKS_TRANSCRIPT = stream(
    {"type": "system", "subtype": "hook_user_prompt_submit",
     "content": "Write tests first, then write code to pass them"},
    {"type": "assistant", "message": {"content": [
        {"type": "text",
         "text": "Before I build: what CSV encoding and which columns? "
                 "I'll assume utf-8."}]}},
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Write",
         "input": {"file_path": "tool.py", "content": "..."}}]}},
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Bash",
         "input": {"command": "python -m pytest -q"}}]}},
    {"type": "result", "result": "Done.", "total_cost_usd": 0.12,
     "num_turns": 5, "is_error": False},
)

# Control: dives straight into writing, no tests, no hook markers.
CONTROL_TRANSCRIPT = stream(
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Write",
         "input": {"file_path": "tool.py", "content": "..."}}]}},
    {"type": "result", "result": "Done.", "total_cost_usd": 0.05,
     "num_turns": 2, "is_error": False},
)


class TestSettings(unittest.TestCase):
    def test_hooks_arm_wires_three_scripts(self):
        s = run_ab.build_settings("/repo", "en", "hooks")
        ups = s["hooks"]["UserPromptSubmit"]
        stop = s["hooks"]["Stop"]
        self.assertEqual(len(ups), 2)
        self.assertEqual(len(stop), 1)
        cmds = [h["hooks"][0]["command"] for h in ups]
        self.assertTrue(any("rules.en.py" in c for c in cmds))
        self.assertTrue(any("inventory_gate.en.py" in c for c in cmds))
        self.assertIn("review.en.py", stop[0]["hooks"][0]["command"])
        # absolute path baked in
        self.assertIn("/repo/rules.en.py", cmds[0])

    def test_zh_uses_non_en_filenames(self):
        s = run_ab.build_settings("/repo", "zh", "hooks")
        c = s["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        self.assertIn("rules.py", c)
        self.assertNotIn("rules.en.py", c)

    def test_control_arm_is_empty_hooks(self):
        s = run_ab.build_settings("/repo", "en", "control")
        self.assertEqual(s, {"hooks": {}})

    def test_unknown_arm_raises(self):
        with self.assertRaises(ValueError):
            run_ab.build_settings("/repo", "en", "bogus")


class TestCommand(unittest.TestCase):
    def test_command_has_required_flags(self):
        cmd = run_ab.build_command("hi", "/x/settings.json", "sonnet", 10)
        self.assertEqual(cmd[:3], ["claude", "-p", "hi"])
        self.assertIn("--settings", cmd)
        self.assertIn("stream-json", cmd)
        self.assertIn("--include-hook-events", cmd)
        self.assertIn("--model", cmd)
        self.assertIn("sonnet", cmd)
        self.assertIn("--max-turns", cmd)
        self.assertIn("acceptEdits", cmd)

    def test_optional_flags_omitted(self):
        cmd = run_ab.build_command("hi", "/x/s.json", None, None)
        self.assertNotIn("--model", cmd)
        self.assertNotIn("--max-turns", cmd)


class TestParse(unittest.TestCase):
    def test_parse_extracts_result_and_tools(self):
        p = run_ab.parse_stream(HOOKS_TRANSCRIPT)
        self.assertEqual(p["result"], "Done.")
        self.assertEqual(p["total_cost_usd"], 0.12)
        self.assertEqual(p["num_turns"], 5)
        self.assertFalse(p["is_error"])
        names = [tc["name"] for tc in p["tool_calls"]]
        self.assertEqual(names, ["Write", "Bash"])
        self.assertIn("utf-8", p["assistant_text"])

    def test_parse_tolerates_junk_lines(self):
        raw = "not json\n" + HOOKS_TRANSCRIPT + "\nalso not json"
        p = run_ab.parse_stream(raw)
        self.assertEqual(p["result"], "Done.")

    def test_parse_empty(self):
        p = run_ab.parse_stream("")
        self.assertEqual(p["tool_calls"], [])
        self.assertEqual(p["n_events"], 0)


class TestSignals(unittest.TestCase):
    def test_hooks_arm_signals(self):
        s = run_ab.extract_signals(HOOKS_TRANSCRIPT)
        self.assertTrue(s["any_hook_fired"])
        self.assertTrue(s["hooks_fired"]["rules"])
        self.assertTrue(s["ran_tests"])
        self.assertEqual(s["files_written"], 1)
        self.assertTrue(s["mentions_assumptions"])
        self.assertEqual(s["num_turns"], 5)

    def test_control_arm_signals(self):
        s = run_ab.extract_signals(CONTROL_TRANSCRIPT)
        self.assertFalse(s["any_hook_fired"])
        self.assertFalse(s["ran_tests"])
        self.assertFalse(s["mentions_assumptions"])

    def test_test_cmd_detection_variants(self):
        for cmd in ["pytest", "npm test", "go test ./...", "cargo test",
                    "python -m pytest -q", "make test"]:
            raw = stream({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Bash",
                 "input": {"command": cmd}}]}})
            self.assertTrue(run_ab.extract_signals(raw)["ran_tests"], cmd)

    def test_non_test_bash_not_counted(self):
        raw = stream({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash",
             "input": {"command": "ls -la"}}]}})
        self.assertFalse(run_ab.extract_signals(raw)["ran_tests"])


class TestNumstat(unittest.TestCase):
    def test_splits_existing_vs_new(self):
        # ranges.py existed at baseline; test_ranges.py is new.
        text = "1\t1\tranges.py\n40\t0\ttest_ranges.py\n"
        r = run_ab.parse_numstat(text, ["ranges.py"])
        self.assertEqual(r["existing_files"], 1)
        self.assertEqual(r["existing_add"], 1)
        self.assertEqual(r["existing_del"], 1)
        self.assertEqual(r["new_files"], 1)
        self.assertEqual(r["new_add"], 40)
        self.assertEqual(r["total_files"], 2)

    def test_binary_counts_as_file_zero_lines(self):
        text = "-\t-\tlogo.png\n"
        r = run_ab.parse_numstat(text, ["ranges.py"])
        self.assertEqual(r["new_files"], 1)
        self.assertEqual(r["new_add"], 0)

    def test_rename_attributed_to_new_path(self):
        text = "0\t0\told.py => new.py\n"
        r = run_ab.parse_numstat(text, ["old.py"])
        # new.py is not in seed set -> counts as new
        self.assertEqual(r["new_files"], 1)
        self.assertEqual(r["existing_files"], 0)

    def test_empty_diff(self):
        r = run_ab.parse_numstat("", ["ranges.py"])
        self.assertEqual(r["total_files"], 0)


class TestCopySeed(unittest.TestCase):
    def test_excludes_pycache_and_pyc(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            seed = Path(tmp) / "seed"
            (seed / "__pycache__").mkdir(parents=True)
            (seed / "mod.py").write_text("x = 1")
            (seed / "__pycache__" / "mod.pyc").write_text("junk")
            (seed / "stray.pyc").write_text("junk")
            ws = Path(tmp) / "ws"
            files = run_ab.copy_seed(str(seed), ws)
            self.assertEqual(files, ["mod.py"])
            self.assertTrue((ws / "mod.py").exists())
            self.assertFalse((ws / "__pycache__").exists())
            self.assertFalse((ws / "stray.pyc").exists())

    def test_no_seed_returns_empty(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run_ab.copy_seed(None, Path(tmp) / "ws"), [])


class TestJudge(unittest.TestCase):
    def test_build_prompt_contains_transcript(self):
        p = run_ab.build_judge_prompt("THE TRANSCRIPT")
        self.assertIn("THE TRANSCRIPT", p)
        self.assertIn("stated_assumptions", p)

    def test_parse_clean_json(self):
        raw = ('{"stated_assumptions":2,"tests_first":1,'
               '"inventoried_existing":0,"scope_discipline":2,'
               '"avoided_overengineering":2,"note":"ok"}')
        out = run_ab.parse_judge_output(raw)
        self.assertEqual(out["stated_assumptions"], 2)
        self.assertEqual(out["note"], "ok")

    def test_parse_json_with_surrounding_prose(self):
        raw = 'Here are the scores:\n{"tests_first":2}\nThanks!'
        out = run_ab.parse_judge_output(raw)
        self.assertEqual(out["tests_first"], 2)

    def test_parse_garbage_returns_none(self):
        self.assertIsNone(run_ab.parse_judge_output("no json here"))


class TestReport(unittest.TestCase):
    def _results(self):
        by_arm = {
            "hooks": {"signals": run_ab.extract_signals(HOOKS_TRANSCRIPT),
                      "judge": None},
            "control": {"signals": run_ab.extract_signals(CONTROL_TRANSCRIPT),
                        "judge": None},
        }
        return [("sonnet", "csv_to_json", "Build a CSV tool.", by_arm)]

    def test_render_case_has_both_arms(self):
        _model, cid, prompt, by_arm = self._results()[0]
        out = run_ab.render_case(cid, prompt, by_arm)
        self.assertIn("csv_to_json", out)
        self.assertIn("hooks", out)
        self.assertIn("control", out)
        self.assertIn("ran tests", out)

    def test_render_report_matrix(self):
        meta = {"generated": "now", "lang": "en", "judge": False}
        out = run_ab.render_report(self._results(), meta)
        self.assertIn("# A/B report", out)
        self.assertIn("Matrix", out)
        self.assertIn("hook%", out)
        self.assertIn("| sonnet | hooks |", out)

    def test_render_report_multi_model_matrix(self):
        base = self._results()[0][3]
        results = [("haiku", "c1", "p", base), ("sonnet", "c1", "p", base)]
        out = run_ab.render_report(results, {"generated": "n", "lang": "en"})
        self.assertIn("| haiku | hooks |", out)
        self.assertIn("| sonnet | control |", out)
        self.assertIn("## Detail: haiku", out)

    def _bench_results(self):
        # hooks: minimal correct edit (1 existing file, small churn) + a test file
        h = run_ab.extract_signals(HOOKS_TRANSCRIPT)
        h.update({"existing_files": 1, "existing_add": 1, "existing_del": 1,
                  "new_files": 1, "new_add": 20, "new_del": 0,
                  "total_files": 2, "correct": True})
        # control: correct but sloppy — touched 2 existing files, bigger churn
        c = run_ab.extract_signals(CONTROL_TRANSCRIPT)
        c.update({"existing_files": 2, "existing_add": 18, "existing_del": 9,
                  "new_files": 0, "new_add": 0, "new_del": 0,
                  "total_files": 2, "correct": True})
        return [("sonnet", "bugfix", "Fix the bug.",
                 {"hooks": {"signals": h, "judge": None},
                  "control": {"signals": c, "judge": None}})]

    def test_bench_rows_render(self):
        _model, cid, prompt, by_arm = self._bench_results()[0]
        out = run_ab.render_case(cid, prompt, by_arm)
        self.assertIn("correct (held-out test)", out)
        self.assertIn("existing files touched", out)
        self.assertIn("existing-file churn", out)
        self.assertIn("new files", out)

    def test_bench_matrix_has_bench_columns(self):
        meta = {"generated": "n", "lang": "en", "judge": False}
        out = run_ab.render_report(self._bench_results(), meta)
        self.assertIn("correct%", out)
        self.assertIn("exist files", out)
        self.assertIn("exist churn", out)

    def test_render_with_judge(self):
        _model, cid, prompt, by_arm = self._results()[0]
        by_arm["hooks"]["judge"] = {
            "stated_assumptions": 2, "tests_first": 2,
            "inventoried_existing": 1, "scope_discipline": 2,
            "avoided_overengineering": 2, "note": "x"}
        out = run_ab.render_case(cid, prompt, by_arm)
        self.assertIn("judge dimension", out)
        self.assertIn("stated_assumptions", out)


if __name__ == "__main__":
    unittest.main()
