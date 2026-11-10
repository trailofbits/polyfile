"""Behavioral tests for opt-in recursive analysis budgets."""

import contextlib
import io
import json
from pathlib import Path

import pytest

from polyfile import AnalysisLimits
from polyfile.__main__ import main
from polyfile.analysis import AnalysisContext
from polyfile.fileutils import FileStream
from polyfile.polyfile import Analyzer, Match, Matcher, Submatch


@pytest.mark.parametrize("name", AnalysisLimits.__dataclass_fields__)
def test_limits_reject_negative_values(name: str) -> None:
    with pytest.raises(ValueError, match=name):
        AnalysisLimits(**{name: -1})


def test_all_limits_default_to_unlimited() -> None:
    context = AnalysisContext(AnalysisLimits())
    assert context.member_limit is None
    assert context.claim_member(10**20, 10**6) is None


@pytest.mark.parametrize(
    ("limits", "size", "depth", "flag"),
    [
        (AnalysisLimits(max_depth=0), 1, 1, "--max-depth"),
        (AnalysisLimits(max_member_bytes=0), 1, 1, "--max-member-bytes"),
        (AnalysisLimits(max_total_bytes=0), 1, 1, "--max-total-bytes"),
        (AnalysisLimits(max_members=0), 1, 1, "--max-members"),
    ],
)
def test_rejected_regions_do_not_consume_budget(
    limits: AnalysisLimits,
    size: int,
    depth: int,
    flag: str,
) -> None:
    context = AnalysisContext(limits)
    assert flag in (context.claim_member(size, depth) or "")
    assert (context.members, context.total_bytes) == (0, 0)


def test_total_allowance_is_shared_across_siblings() -> None:
    context = AnalysisContext(AnalysisLimits(max_member_bytes=8, max_total_bytes=10))
    assert context.member_limit == 8
    assert context.claim_member(6, 1) is None
    assert context.member_limit == 4
    assert context.claim_member(5, 1) is not None
    assert context.claim_member(4, 1) is None
    assert context.member_limit == 0


def test_structural_nodes_do_not_increase_content_depth() -> None:
    matcher = Matcher(parse=False, limits=AnalysisLimits(max_depth=1))
    root = Match("root", None, matcher=matcher)
    header = Submatch("header", None, parent=root)
    payload = Submatch("payload", None, parent=header)
    matches = list(matcher.match(FileStream(b'{"member": true}'), parent=payload))
    assert matches
    assert matches[0].analysis_depth == 1
    assert matches[0].analysis_context is root.analysis_context


def test_limited_content_keeps_its_parent_and_reason() -> None:
    matcher = Matcher(parse=False, limits=AnalysisLimits(max_member_bytes=1))
    payload = Match("payload", None, length=2, matcher=matcher)
    assert list(matcher.match(FileStream(b"{}"), parent=payload)) == []
    assert payload.to_obj()["analysis_status"] == "limited"
    assert "--max-member-bytes" in payload.to_obj()["analysis_message"]


def test_reusing_matcher_starts_a_fresh_analysis() -> None:
    matcher = Matcher(parse=False, limits=AnalysisLimits(max_members=1))
    first = next(matcher.match(FileStream(b"{}")))
    second = next(matcher.match(FileStream(b"{}")))
    assert first.analysis_context is not second.analysis_context
    assert first.analysis_context.claim_member(2, 1) is None
    assert second.analysis_context.claim_member(2, 1) is None


def test_analyzer_forwards_limits(tmp_path: Path) -> None:
    path = tmp_path / "document.json"
    path.write_bytes(b"{}")
    limits = AnalysisLimits(max_depth=0)
    assert Analyzer(path, limits=limits).matcher.limits is limits


@pytest.mark.parametrize(
    "name",
    [
        name
        for name in AnalysisLimits.__dataclass_fields__
        if name not in ("max_codec_memory", "helper_timeout")
    ],
)
def test_cli_accepts_explicit_zero_limits(name: str, tmp_path: Path) -> None:
    path = tmp_path / "document.json"
    path.write_bytes(b"{}")
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        main(
            [
                "polyfile",
                "--quiet",
                "--format",
                "json",
                "--" + name.replace("_", "-"),
                "0",
                str(path),
            ]
        )
    assert json.loads(output.getvalue())["struc"]


@pytest.mark.parametrize("name", AnalysisLimits.__dataclass_fields__)
def test_cli_rejects_negative_limits(name: str) -> None:
    with contextlib.redirect_stderr(io.StringIO()), pytest.raises(SystemExit) as exc:
        main(["polyfile", "--" + name.replace("_", "-"), "-1"])
    assert exc.value.code == 2


def test_container_entries_count_without_content() -> None:
    context = AnalysisContext(AnalysisLimits(max_members=1))
    assert context.claim_entry() is None
    assert context.claim_member(5, 1, count=False) is None
    assert context.members == 1
    assert context.total_bytes == 5
    assert context.claim_entry() is not None


def test_precounted_payload_does_not_consume_another_entry() -> None:
    matcher = Matcher(parse=False, limits=AnalysisLimits(max_members=1))
    payload = Match("payload", None, matcher=matcher)
    assert payload.analysis_context.claim_entry() is None
    payload.analysis_member_counted = True
    assert list(matcher.match(FileStream(b"{}"), parent=payload))
    assert payload.analysis_context.members == 1


def test_codec_memory_limit_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        AnalysisLimits(max_codec_memory=0)
    assert AnalysisLimits(max_codec_memory=1).max_codec_memory == 1


def test_cli_rejects_zero_codec_memory() -> None:
    with contextlib.redirect_stderr(io.StringIO()), pytest.raises(SystemExit) as exc:
        main(["polyfile", "--max-codec-memory", "0"])
    assert exc.value.code == 2


@pytest.mark.parametrize("value", (0, -1, float("nan"), float("inf"), -float("inf")))
def test_helper_timeout_must_be_positive_and_finite(value: float) -> None:
    with pytest.raises(ValueError, match="helper_timeout"):
        AnalysisLimits(helper_timeout=value)


def test_helper_timeout_accepts_fractional_seconds() -> None:
    assert AnalysisLimits(helper_timeout=0.25).helper_timeout == 0.25


@pytest.mark.parametrize("value", ("0", "nan", "inf", "-inf"))
def test_cli_rejects_invalid_helper_timeout(value: str) -> None:
    with contextlib.redirect_stderr(io.StringIO()), pytest.raises(SystemExit) as exc:
        main(["polyfile", "--helper-timeout", value])
    assert exc.value.code == 2
