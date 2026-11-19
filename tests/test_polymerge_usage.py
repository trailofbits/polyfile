"""Check usage errors through the PolyMerge command-line entry point."""

import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "arguments,diagnostic",
    [
        (["a", "b", "c"], "at most two input files"),
        (["one", "--cfg", "cfg.dot", "--type-hierarchy", "types.dot"], "Two input files"),
        (["one", "--cfg", "cfg.dot", "--dataflow", "1:2:3"], "Invalid dataflow range"),
        (["one", "--cfg", "cfg.dot", "--dataflow", "x:2"], "Invalid dataflow range start"),
        (["one", "--cfg", "cfg.dot", "--dataflow", "1:x"], "Invalid dataflow range end"),
        (["one", "--cfg", "cfg.dot", "--dataflow", "2:1"], "must be less than"),
    ],
)
def test_rejected_arguments_report_a_usage_error(arguments: list[str], diagnostic: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "polymerge", "--quiet", *arguments], capture_output=True, text=True
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert diagnostic in result.stderr
