"""Held-out grader for add_upper_flag. NOT shown to the agent.

Usage: python3 grade_test.py <workspace_dir>
Exit 0 = correct, non-zero = incorrect.
"""
import io
import os
import sys
import contextlib

sys.path.insert(0, sys.argv[1])
import echo_lines  # noqa: E402


def run_main(args, tmp_lines):
    path = os.path.join(sys.argv[1], "_grade_input.txt")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(tmp_lines))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        echo_lines.main([path] + args)
    os.remove(path)
    return buf.getvalue().splitlines()


def main():
    # transform contract
    assert echo_lines.transform(["ab", "cd"]) == ["ab", "cd"], "default unchanged"
    assert echo_lines.transform(["ab"], upper=True) == ["AB"], "upper works"

    # default behaviour unchanged end-to-end
    assert run_main([], ["hello", "World"]) == ["hello", "World"], "default CLI"
    # --upper flag uppercases
    assert run_main(["--upper"], ["hello", "World"]) == ["HELLO", "WORLD"], "--upper CLI"
    print("OK")


if __name__ == "__main__":
    main()
