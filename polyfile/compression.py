"""Shared streaming-decoder output and recursive-content support."""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

from polyfile.fileutils import FileStream
from polyfile.polyfile import Match, Submatch

CHUNK_SIZE = 64 * 1024


@dataclass(frozen=True)
class RawRegion:
    """A physical encoded-stream region, with offsets relative to that stream."""

    name: str
    offset: int
    length: int
    value: object = None
    children: tuple["RawRegion", ...] = ()

    def matches(self, parent: Match, origin: int = 0) -> Iterator[Submatch]:
        """Yields this region and its children beneath a containing match."""
        match = Submatch(
            self.name,
            self.value,
            relative_offset=self.offset - origin,
            length=self.length,
            parent=parent,
        )
        yield match
        for child in self.children:
            yield from child.matches(match, self.offset)


@dataclass(frozen=True)
class DecodeResult:
    """Validated decoded bytes and their physical framing regions."""

    data: bytes
    regions: tuple[RawRegion, ...] = ()
    member_count: int = 1


class DecodeError(ValueError):
    """An expected invalid, unsupported, or resource-limited decoding result."""

    def __init__(
        self,
        message: str,
        *,
        status: str = "invalid",
        regions: tuple[RawRegion, ...] = (),
    ) -> None:
        super().__init__(message)
        self.status = status
        self.regions = regions


class Decoder(Protocol):
    """A decoder that validates its complete stream before publishing bytes."""

    def __call__(
        self,
        stream: FileStream,
        *,
        max_output: int | None = None,
        max_memory: int | None = None,
        max_members: int | None = None,
    ) -> DecodeResult:
        """Decodes a stream subject to optional output and codec-memory limits."""
        ...


class OutputBuffer:
    """Collects incremental output, checking an optional limit before storage."""

    def __init__(self, max_output: int | None = None) -> None:
        self.max_output = max_output
        self._data = bytearray()

    @property
    def remaining(self) -> int | None:
        """The remaining output allowance, or None when unlimited."""
        if self.max_output is None:
            return None
        return max(self.max_output - len(self._data), 0)

    @property
    def next_size(self) -> int:
        """A bounded output chunk, including one byte to detect limit exhaustion."""
        remaining = self.remaining
        if remaining is None:
            return CHUNK_SIZE
        return min(CHUNK_SIZE, remaining + 1)

    def append(self, data: bytes) -> None:
        """Appends decoded bytes or reports the configured output limit."""
        if (
            self.max_output is not None
            and len(self._data) + len(data) > self.max_output
        ):
            raise DecodeError(
                f"decoded content exceeds the {self.max_output}-byte analysis allowance",
                status="limited",
            )
        self._data.extend(data)

    def finish(self) -> bytes:
        """Returns the validated output as an immutable buffer."""
        return bytes(self._data)


def match_decoded(
    parent: Match, data: bytes, *, member_counted: bool = False
) -> Iterator[Match]:
    """Creates a decoded source and recursively analyzes its complete bytes.

    Args:
        parent: The physical encoded region that produced the decoded buffer.
        data: Complete, validated decoded bytes.
        member_counted: Whether the containing format already counted this member.

    Yields:
        A decoded-content region and its recursively recognized file structure.
    """
    decoded = Submatch(
        "decoded_content",
        None,
        relative_offset=0,
        length=len(data),
        parent=parent,
        source=parent.analysis_context.next_source(),
        decoded=data,
    )
    decoded.analysis_member_counted = member_counted
    yield decoded
    if parent.matcher is not None:
        yield from parent.matcher.match(data, parent=decoded)


def parse_compressed(
    stream: FileStream, parent: Match, decoder: Decoder
) -> Iterator[Match]:
    """Maps a compressed stream and analyzes its validated decoded content.

    Args:
        stream: The encoded input, positioned at its start.
        parent: The match identifying the encoded format.
        decoder: A streaming decoder that reports framing and expected errors.

    Yields:
        Physical framing regions, followed by validated decoded content.
    """
    context = parent.analysis_context
    max_depth = context.limits.max_depth
    if max_depth is not None and parent.analysis_depth >= max_depth:
        parent.analysis_status = "limited"
        parent.analysis_message = (
            f"recursive analysis exceeds the depth limit of {max_depth}"
        )
        return
    try:
        result = decoder(
            stream,
            max_output=context.member_limit,
            max_memory=context.limits.max_codec_memory,
            max_members=context.remaining_members,
        )
    except DecodeError as error:
        parent.analysis_status = error.status
        parent.analysis_message = str(error)
        for region in error.regions:
            yield from region.matches(parent)
        return
    for region in result.regions:
        yield from region.matches(parent)
    for _ in range(result.member_count):
        reason = context.claim_entry()
        if reason is not None:
            parent.analysis_status = "limited"
            parent.analysis_message = reason
            return
    yield from match_decoded(parent, result.data, member_counted=True)
