"""Reference cases for recursive magic descriptions from issue #3603."""

import struct
from collections.abc import Iterable
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from polyfile.magic import (
    AbsoluteOffset,
    MagicMatcher,
    MagicTest,
    Match,
    MatchContext,
    MatchedTest,
)
from polyfile.magic import (
    TestResult as MagicResult,
)
from polyfile.magic import (
    TestType as MagicTestType,
)


def sample() -> bytes:
    """Return a binary with two pointers to independently identified payloads."""
    data = bytearray(48)
    data[:4] = b"MAGI"
    data[8:12] = struct.pack("<I", 24)
    data[12:16] = struct.pack("<I", 32)
    data[24:27] = b"AAA"
    data[32:35] = b"BBB"
    return bytes(data)


def definitions(continuations: Iterable[str], named: Iterable[str] = ()) -> str:
    """Build a root description with named and indirect dispatch targets."""
    return "\n".join(
        (
            *(named or ("0\tname\tblk\tNAMED",)),
            "0\tstring\tMAGI\tbase:",
            *continuations,
            "0\tstring\tAAA\tfirst-nested",
            "0\tstring\tBBB\tsecond-nested",
            "",
        )
    )


def described_match(definition: str, data: bytes = b"") -> Match:
    """Return the root match from a disposable custom definition."""
    with TemporaryDirectory() as directory:
        path = Path(directory) / "messages.magic"
        path.write_text(definition)
        matcher = MagicMatcher.parse(path)
        return next(
            match
            for match in matcher.match(data or sample())
            if match.description().startswith("base:")
        )


@pytest.mark.parametrize(
    ("calls", "expected"),
    (
        ((">(8.l)\tindirect\tx",), "base:first-nested"),
        ((">(8.l)\tindirect\tx", ">(12.l)\tindirect\tx"), "base:first-nested\n- second-nested"),
        ((">4\tuse\tblk",), "base:NAMED"),
        ((">4\tuse\tblk", ">4\tuse\tblk"), "base:NAMEDNAMED"),
        ((">4\tuse\tblk", ">(8.l)\tindirect\tx"), "base:NAMED\n- first-nested"),
        ((">(8.l)\tindirect\tx", ">4\tuse\tblk"), "base:first-nestedNAMED"),
        (
            (">(8.l)\tindirect\tx", ">(12.l)\tindirect\tx", ">4\tuse\tblk"),
            "base:first-nested\n- second-nestedNAMED",
        ),
        ((">0\tstring\tx", ">>(8.l)\tindirect\tx"), "base:first-nested"),
    ),
)
def test_recursive_description_matrix(calls: tuple[str, ...], expected: str) -> None:
    assert described_match(definitions(calls)).description() == expected


def test_indirect_in_a_named_block() -> None:
    named = ("0\tname\tblk\t[", ">(4.l)\tindirect\tx")
    match = described_match(definitions((">4\tuse\tblk",), named))
    assert match.description() == "base:[first-nested"


@pytest.mark.parametrize("message", ("", "\t\\b"))
def test_named_messages_ignore_the_use_nospace_flag(message: str) -> None:
    match = described_match(definitions((f">4\tuse\tblk{message}",)))
    assert match.description() == "base:NAMED"


def test_named_continuations_follow_the_separator_after_the_name() -> None:
    calls = (">4\tuse\tblk", ">4\tuse\tblk")
    named = ("0\tname\tblk\tNAMED", ">0\tstring\tx\tchild")
    match = described_match(definitions(calls, named))
    assert match.description() == "base:NAMED childNAMED\n-  child"


def test_a_use_description_does_not_print_its_literal() -> None:
    match = described_match(definitions((">4\tuse\tblk\tunused literal",)))
    assert match.description() == "base:NAMED "


def test_an_indirect_description_prints_before_its_nested_buffer() -> None:
    match = described_match(definitions((">(8.l)\tindirect\tx\tINDIRECT",)))
    assert match.description() == "base:INDIRECTfirst-nested "


def test_an_empty_named_call_still_finishes_its_printing_frame() -> None:
    named = ("0\tname\tempty", ">0\tstring\tNOMATCH\tnope")
    calls = (">4\tuse\tempty", ">(8.l)\tindirect\tx")
    match = described_match(definitions(calls, named))
    assert match.description() == "base:\n- first-nested"
    assert all(result.test.libmagic_type() != "use" for result in match)


def test_ordinary_continuation_spacing_and_nospace() -> None:
    calls = (">0\tstring\tx\tchild", ">0\tstring\tx\t\\b,next")
    assert described_match(definitions(calls)).description() == "base: child,next"


def test_rendering_is_repeatable_and_keeps_public_results() -> None:
    definition = definitions((">4\tuse\tblk", ">(8.l)\tindirect\tx"))
    match = described_match(definition)
    results = tuple(match)
    for _ in range(3):
        assert match.description() == "base:NAMED\n- first-nested"
        assert tuple(match) == results
        assert all(isinstance(result, MagicResult) for result in match)
    other = described_match(definitions((">(8.l)\tindirect\tx",)))
    assert other.description() == "base:first-nested"


class CountingMagic(MagicTest):
    def __init__(self, events: list[int], parent: MagicTest | None = None):
        super().__init__(
            AbsoluteOffset(0),
            mime="application/x-message-test",
            parent=parent,
            message="root" if parent is None else "child",
        )
        self.events = events

    def subtest_type(self) -> MagicTestType:
        return MagicTestType.BINARY

    def test(
        self, data: bytes, absolute_offset: int, parent_match: MagicResult | None
    ) -> MagicResult:
        self.events.append(self.level)
        return MatchedTest(self, None, absolute_offset, 0, parent_match)


def test_rendering_consumes_each_test_once_and_iteration_stays_lazy() -> None:
    events: list[int] = []
    root = CountingMagic(events)
    CountingMagic(events, root)
    matcher = MagicMatcher((root,))
    match = next(matcher.match(MatchContext(b"\x00\x01")))
    assert events == [0]
    assert match.description() == "root child"
    assert events == [0, 1]
    assert match.description() == "root child"
    assert events == [0, 1]


def universal_macho() -> bytes:
    """Build two Mach-O headers behind a fat header, without platform fixtures."""
    data = bytearray(192)
    data[:8] = struct.pack(">II", 0xCAFEBABE, 2)
    data[8:28] = struct.pack(">5I", 0x01000007, 3, 64, 32, 0)
    data[28:48] = struct.pack(">5I", 0x0100000C, 0x80000002, 128, 32, 0)
    data[64:96] = struct.pack("<8I", 0xFEEDFACF, 0x01000007, 3, 2, 0, 0, 0x200085, 0)
    data[128:160] = struct.pack("<8I", 0xFEEDFACF, 0x0100000C, 0x80000002, 2, 0, 0, 0x200085, 0)
    return bytes(data)


def test_universal_macho_separates_named_and_indirect_architecture_descriptions() -> None:
    expected = (
        "Mach-O universal binary with 2 architectures: [x86_64:\n- "
        "Mach-O 64-bit x86_64 executable, flags:<NOUNDEFS|DYLDLINK|TWOLEVEL|PIE>] "
        "[\n- arm64e (caps: 0x2):\n- Mach-O 64-bit arm64e (caps: PAC00) executable, "
        "flags:<NOUNDEFS|DYLDLINK|TWOLEVEL|PIE>]"
    )
    descriptions = {
        match.description() for match in MagicMatcher.DEFAULT_INSTANCE.match(universal_macho())
    }
    assert expected in descriptions


def test_a_later_nested_match_can_print_from_a_continuation() -> None:
    definition = (
        "0\tstring\tMAGI\tbase:\n>(8.l)\tindirect\tx\n"
        "0\tstring\tAAA\tfirst\n0\tstring\tAA\n>0\tbyte\tx\tsecond\n"
    )
    assert described_match(definition).description() == "base:first\n-  second"
