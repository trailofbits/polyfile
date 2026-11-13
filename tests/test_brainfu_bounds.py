"""BrainFu matches and failures report absolute physical file coordinates."""

import pytest

from polyfile.languagematcher import BFMatcher
from polyfile.magic import AbsoluteOffset, FailedTest, MagicMatcher, MatchedTest

PROGRAM = b"++++++++[>++++<-]>[<+>-]<."
PREAMBLE = b"comment"


class InheritedBFMatcher(BFMatcher):
    """Exercises full parsing instead of the native matcher's early rejection."""

    AUTO_REGISTER_TEST = False


@pytest.mark.parametrize("matcher_type", [BFMatcher, InheritedBFMatcher])
@pytest.mark.parametrize("offset", [0, 3])
@pytest.mark.parametrize("comments", [False, True])
@pytest.mark.parametrize("reject_noops", [False, True])
def test_matches_include_the_last_command_and_physical_comment_span(
    matcher_type: type[BFMatcher], offset: int, comments: bool, reject_noops: bool
) -> None:
    matcher = matcher_type()
    matcher.reject_arithmetical_noops = reject_noops
    body = b"  ".join(bytes((command,)) for command in PROGRAM) if comments else PROGRAM
    data = b"\xff" * offset + PREAMBLE + body + b"trailer"

    result = matcher.test(data, offset, None)

    assert isinstance(result, MatchedTest)
    assert result.offset == offset + len(PREAMBLE)
    assert result.length == len(body)
    assert result.relative_base == result.offset + len(body)
    assert data[result.offset : result.relative_base] == body
    assert result.value == PROGRAM


@pytest.mark.parametrize("matcher_type", [BFMatcher, InheritedBFMatcher])
@pytest.mark.parametrize("offset", [0, 3])
@pytest.mark.parametrize(
    "body,position,message",
    [
        (b"comment]tail", 7, "unbalanced square brackets"),
        (b"comment[tail", 11, "unbalanced square brackets"),
        (b"comment,[]><+-", 7, "missing commands ."),
        (b"comment[]><+-.", 7, "expected at least 2 BrainFu loops but only found 1"),
        (
            b"comment[][]><+-.",
            7,
            "expected at least 24 BrainFu commands but only found 9",
        ),
        (
            b"comment+-" + PROGRAM,
            7,
            "BrainFu program contains arithmetic that cancels itself out",
        ),
        (PROGRAM + b"]tail", len(PROGRAM), "unbalanced square brackets"),
        (PROGRAM + b"[tail", len(PROGRAM) + 4, "unbalanced square brackets"),
    ],
)
def test_rejections_include_the_slice_base_and_keep_precedence(
    matcher_type: type[BFMatcher], offset: int, body: bytes, position: int, message: str
) -> None:
    matcher = matcher_type()
    matcher.reject_arithmetical_noops = True

    result = matcher.test(b"\xff" * offset + body, offset, None)

    assert isinstance(result, FailedTest)
    assert result.offset == offset + position
    assert result.message == message


@pytest.mark.parametrize("matcher_type", [BFMatcher, InheritedBFMatcher])
@pytest.mark.parametrize("offset", [0, 3])
@pytest.mark.parametrize("body", [b"", PREAMBLE])
def test_missing_commands_without_any_commands_report_the_slice_start(
    matcher_type: type[BFMatcher], offset: int, body: bytes
) -> None:
    result = matcher_type().test(b"\xff" * offset + body, offset, None)

    assert isinstance(result, FailedTest)
    assert result.offset == offset
    assert result.message.startswith("missing commands ")


@pytest.mark.parametrize("reject_noops", [False, True])
def test_normal_matching_and_explanation_use_the_physical_extent(
    reject_noops: bool,
) -> None:
    matcher = BFMatcher()
    matcher.offset = AbsoluteOffset(3)
    matcher.reject_arithmetical_noops = reject_noops
    data = b"\xff" * 3 + PREAMBLE + PROGRAM + b"trailer"

    matches = list(MagicMatcher([matcher]).match(data))

    assert len(matches) == 1
    match = matches[0]
    result = match[0]
    assert isinstance(result, MatchedTest)
    assert result.offset == 3 + len(PREAMBLE)
    assert result.length == len(PROGRAM)
    assert set(match.mimetypes) == {"application/x-brainfuck"}
    assert f"Matched {len(PROGRAM)} bytes at offset {result.offset}" in match.explain(
        file=data, ansi_color=False
    )
