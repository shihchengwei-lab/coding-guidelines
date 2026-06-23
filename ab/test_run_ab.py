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
        return [("csv_to_json", "Build a CSV tool.", by_arm)]

    def test_render_case_has_both_arms(self):
        out = run_ab.render_case(*self._results()[0])
        self.assertIn("csv_to_json", out)
        self.assertIn("hooks", out)
        self.assertIn("control", out)
        self.assertIn("ran tests", out)

    def test_render_report_aggregate(self):
        meta = {"generated": "now", "model": "sonnet", "lang": "en",
                "judge": False}
        out = run_ab.render_report(self._results(), meta)
        self.assertIn("# A/B report", out)
        self.assertIn("Aggregate", out)
        self.assertIn("hook fired rate", out)

    def test_render_with_judge(self):
        results = self._results()
        results[0][2]["hooks"]["judge"] = {
            "stated_assumptions": 2, "tests_first": 2,
            "inventoried_existing": 1, "scope_discipline": 2,
            "avoided_overengineering": 2, "note": "x"}
        out = run_ab.render_case(*results[0])
        self.assertIn("judge dimension", out)
        self.assertIn("stated_assumptions", out)


if __name__ == "__main__":
    unittest.main()
