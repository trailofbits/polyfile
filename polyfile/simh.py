"""Identify and map SIMH tape records without assuming tape records are files."""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal

from polyfile.fileutils import FileStream
from polyfile.magic import (
    AbsoluteOffset,
    FailedTest,
    MagicMatcher,
    MagicTest,
    MatchedTest,
    TestResult,
    TestType,
)
from polyfile.polyfile import Match, Submatch, register_parser

MIME_TYPE = "application/SIMH-tape-data"
END_OF_MEDIUM = 0xFFFFFFFF
LENGTH_MASK = 0x00FFFFFF


def _length(word: int) -> int:
    if word == END_OF_MEDIUM:
        return word
    if word & 0x0F000000:
        raise ValueError("SIMH record length uses reserved bits 24 through 27")
    length = word & LENGTH_MASK
    return length + (length & 1)


def _accepts(data: bytes) -> bool:
    """Apply the native libmagic probe, including its ten-tape-mark stopping point."""
    offset = records = marks = 0
    while offset + 4 <= len(data):
        word = int.from_bytes(data[offset : offset + 4], "little")
        offset += 4
        try:
            length = _length(word)
        except ValueError:
            return False
        if length == END_OF_MEDIUM:
            break
        if length == 0:
            marks += 1
            if marks == 10:
                break
            continue
        offset += length
        if offset + 4 > len(data):
            break
        try:
            trailer = _length(int.from_bytes(data[offset : offset + 4], "little"))
        except ValueError:
            return False
        offset += 4
        if length != trailer:
            return False
        records += 1
    return records > 0


class SIMHTest(MagicTest):
    """Recognize native SIMH record framing ahead of soft magic."""

    def __init__(self) -> None:
        super().__init__(
            offset=AbsoluteOffset(0),
            mime=MIME_TYPE,
            extensions=("tap",),
            message="SIMH tape data",
        )

    @property
    def precedes_soft_magic(self) -> bool:
        return True

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(
        self, data: bytes, absolute_offset: int, parent_match: TestResult | None
    ) -> TestResult:
        if _accepts(data[absolute_offset:]):
            return MatchedTest(
                self,
                value=None,
                offset=absolute_offset,
                length=len(data) - absolute_offset,
                parent=parent_match,
            )
        return FailedTest(
            self,
            offset=absolute_offset,
            parent=parent_match,
            message="no complete SIMH record sequence",
        )


@dataclass(frozen=True, kw_only=True)
class TapeRecord:
    """Describe one physical tape record or marker."""

    offset: int
    word: int
    kind: Literal["record", "tape_mark", "end_of_medium"]
    length: int = 0
    trailer: int = 0
    padding: bytes = b""

    @property
    def size(self) -> int:
        if self.kind != "record":
            return 4
        return self.length + len(self.padding) + 8


class TapeError(ValueError):
    """Report an invalid physical tape record."""


def _read_record(stream: FileStream, offset: int) -> TapeRecord:
    stream.seek(offset)
    header = stream.read(4)
    if len(header) != 4:
        raise TapeError("truncated four-byte record header")
    word = int.from_bytes(header, "little")
    if word == END_OF_MEDIUM:
        return TapeRecord(offset=offset, word=word, kind="end_of_medium")
    try:
        padded = _length(word)
    except ValueError as error:
        raise TapeError(str(error)) from error
    length = word & LENGTH_MASK
    if length == 0:
        return TapeRecord(offset=offset, word=word, kind="tape_mark")
    if offset + padded + 8 > len(stream):
        raise TapeError(
            f"truncated record: {length} payload bytes and trailer required"
        )
    stream.seek(offset + 4 + length)
    padding = stream.read(padded - length)
    trailer = int.from_bytes(stream.read(4), "little")
    try:
        _length(trailer)
    except ValueError as error:
        raise TapeError(f"invalid trailer: {error}") from error
    if trailer == END_OF_MEDIUM or trailer & LENGTH_MASK != length:
        raise TapeError(
            f"record length {length} disagrees with trailer {trailer & LENGTH_MASK}"
        )
    return TapeRecord(
        offset=offset,
        word=word,
        kind="record",
        length=length,
        trailer=trailer,
        padding=padding,
    )


def _map_record(record: TapeRecord, parent: Match) -> Iterator[Submatch]:
    node = Submatch(
        record.kind,
        None,
        relative_offset=record.offset,
        length=record.size,
        parent=parent,
    )
    yield node
    yield Submatch("record_word", record.word, length=4, parent=node)
    if record.kind != "record":
        return
    yield Submatch("record_flags", record.word >> 28, length=4, parent=node)
    payload = Submatch(
        "record_payload", None, relative_offset=4, length=record.length, parent=node
    )
    payload.analysis_member_counted = True
    if record.word & 0x80000000:
        payload.analysis_status = "invalid"
        payload.analysis_message = "SIMH record carries the tape record error flag"
    yield payload
    if record.padding:
        yield Submatch(
            "word_padding",
            record.padding,
            relative_offset=4 + record.length,
            length=1,
            parent=node,
        )
    yield Submatch(
        "record_trailer",
        record.trailer,
        relative_offset=record.size - 4,
        length=4,
        parent=node,
    )


def _scan_payload(stream: FileStream, node: Submatch, offset: int) -> Iterator[Match]:
    if node.length == 0 or node.analysis_status is not None:
        return
    matcher = node.matcher
    if matcher is None:
        raise ValueError("SIMH payload recursion requires its parent matcher")
    with (
        stream.save_pos(),
        FileStream(stream, start=offset, length=node.length) as payload,
    ):
        yield from matcher.match(payload, parent=node)


@register_parser(MIME_TYPE)
def parse_simh(stream: FileStream, parent: Match) -> Iterator[Match]:
    """Map tape framing and inspect record payload bytes without joining records.

    Args:
        stream: Tape bytes, starting at the beginning of the SIMH image.
        parent: The recognized SIMH image.

    Yields:
        Physical records and fields, plus any independently recognizable payload contents.
    """
    offset = 0
    while offset < len(stream):
        reason = parent.analysis_context.claim_entry()
        if reason is not None:
            parent.analysis_status = "limited"
            parent.analysis_message = reason
            return
        try:
            record = _read_record(stream, offset)
        except TapeError as error:
            parent.analysis_status = "invalid"
            parent.analysis_message = f"SIMH record at offset {offset}: {error}"
            yield Submatch(
                "invalid_record",
                None,
                relative_offset=offset,
                length=len(stream) - offset,
                parent=parent,
            )
            return
        for node in _map_record(record, parent):
            yield node
            if node.name == "record_payload":
                yield from _scan_payload(stream, node, offset + 4)
        offset += record.size
        if record.kind == "end_of_medium":
            if offset < len(stream):
                yield Submatch(
                    "trailing_data",
                    None,
                    relative_offset=offset,
                    length=len(stream) - offset,
                    parent=parent,
                )
            return


MagicMatcher.DEFAULT_INSTANCE.add(SIMHTest())
