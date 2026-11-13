"""Optional arithmetic filtering must keep valid BrainFu programs detectable."""

import pytest

from polyfile.languagematcher import BFMatcher
from polyfile.magic import FailedTest, MagicMatcher, MatchedTest

PROGRAM = b"++++++++[>++++<-]>[<+>-]<."


@pytest.mark.parametrize("reject_noops", [False, True])
@pytest.mark.parametrize(
    ("prefix", "commands"),
    [(b"", b""), (b"+comment-comment", b"+-"), (b"-comment+comment", b"-+")],
)
def test_accepted_program_retains_offsets_and_value(
    reject_noops: bool, prefix: bytes, commands: bytes
) -> None:
    matcher = BFMatcher()
    matcher.reject_arithmetical_noops = reject_noops

    result = matcher.test(b"preamble" + prefix + PROGRAM + b"trailer", 0, None)

    assert isinstance(result, MatchedTest)
    assert result.offset == len(b"preamble")
    assert result.length == len(prefix) + len(PROGRAM)
    assert result.value == commands + PROGRAM


def test_enabled_filter_keeps_the_program_in_normal_detection() -> None:
    matcher = BFMatcher()
    matcher.reject_arithmetical_noops = True

    matches = list(MagicMatcher([matcher]).match(PROGRAM))

    assert {mime for match in matches for mime in match.mimetypes} == {
        "application/x-brainfuck"
    }


@pytest.mark.parametrize("cancellation", [b"+-", b"-+"])
def test_adjacent_cancellation_is_rejected_at_its_first_command(
    cancellation: bytes,
) -> None:
    matcher = BFMatcher()
    matcher.reject_arithmetical_noops = True

    result = matcher.test(b"preamble" + cancellation + PROGRAM, 0, None)

    assert isinstance(result, FailedTest)
    assert result.offset == len(b"preamble")
    assert (
        result.message == "BrainFu program contains arithmetic that cancels itself out"
    )


@pytest.mark.parametrize("cancellation", [b"+-", b"-+"])
def test_default_matcher_accepts_adjacent_cancellation(cancellation: bytes) -> None:
    result = BFMatcher().test(cancellation + PROGRAM, 0, None)

    assert isinstance(result, MatchedTest)
    assert result.value == cancellation + PROGRAM


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"]+-" + PROGRAM, "unbalanced square brackets"),
        (b"[]><+-", "missing commands ."),
        (b"[]><+-.", "expected at least 2 BrainFu loops but only found 1"),
        (b"[][]><+-.", "expected at least 24 BrainFu commands but only found 9"),
    ],
)
def test_earlier_rejections_keep_precedence(data: bytes, message: str) -> None:
    matcher = BFMatcher()
    matcher.reject_arithmetical_noops = True

    result = matcher.test(data, 0, None)

    assert isinstance(result, FailedTest)
    assert result.offset == 0
    assert result.message == message
