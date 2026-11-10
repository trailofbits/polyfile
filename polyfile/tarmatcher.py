"""Native TAR detection and physical member structure without filesystem extraction."""

import tarfile
from collections.abc import Iterator
from copy import copy
from dataclasses import dataclass, field

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

BLOCK_SIZE = 512
ZERO_BLOCK = bytes(BLOCK_SIZE)
TAR_MIME_TYPES = (
    "application/x-tar",
    "application/x-ustar",
    "application/x-gtar",
    "application/vnd.gentoo.gpkg",
)
EXTENSION_TYPES = (
    tarfile.XHDTYPE,
    tarfile.XGLTYPE,
    tarfile.GNUTYPE_LONGNAME,
    tarfile.GNUTYPE_LONGLINK,
)
HEADER_FIELDS = (
    ("name", 0, 100),
    ("mode", 100, 108),
    ("uid", 108, 116),
    ("gid", 116, 124),
    ("size", 124, 136),
    ("mtime", 136, 148),
    ("checksum", 148, 156),
    ("typeflag", 156, 157),
    ("linkname", 157, 257),
    ("magic", 257, 263),
    ("version", 263, 265),
    ("uname", 265, 297),
    ("gname", 297, 329),
    ("devmajor", 329, 337),
    ("devminor", 337, 345),
    ("prefix", 345, 500),
    ("reserved", 500, 512),
)


def _native_checksum(field_bytes: bytes) -> int:
    value = field_bytes.lstrip(b" \t\n\r\v\f")
    if not value:
        return -1
    end = 0
    while end < len(value) and 48 <= value[end] <= 55:
        end += 1
    if end < len(value) and value[end] not in b"\0 \t\n\r\v\f":
        return -1
    return int(value[:end], 8) if end else 0


def _tar_variant(header: bytes) -> str | None:
    if len(header) != BLOCK_SIZE:
        return None
    name, separator, _ = header[:100].partition(b"\0")
    if separator and len(name) >= 8 and name.endswith(b"/gpkg-1"):
        return None
    expected = _native_checksum(header[148:156])
    if sum(header[:148]) + sum(header[156:]) + 8 * 32 != expected:
        return None
    if header[257:263] == b"ustar ":
        return "GNU"
    if header[257:263] == b"ustar\0":
        return "POSIX"
    return "V7"


class TarMatcher(MagicTest):
    """Identify one TAR variant using libmagic's native first-header checksum check."""

    def __init__(self, variant: str):
        descriptions = {
            "V7": "tar archive",
            "POSIX": "POSIX tar archive",
            "GNU": "POSIX tar archive (GNU)",
        }
        super().__init__(
            offset=AbsoluteOffset(0),
            mime="application/x-tar",
            extensions=("tar",),
            message=descriptions[variant],
        )
        self.variant = variant

    @property
    def precedes_soft_magic(self) -> bool:
        return True

    def subtest_type(self) -> TestType:
        return TestType.BINARY

    def test(
        self, data: bytes, absolute_offset: int, parent_match: TestResult | None
    ) -> TestResult:
        """Validate the checksum and variant without suppressing other file matches."""
        end = absolute_offset + BLOCK_SIZE
        header = data[absolute_offset:end]
        if _tar_variant(header) != self.variant:
            return FailedTest(
                self, offset=absolute_offset, message="TAR header does not validate"
            )
        return MatchedTest(
            self,
            value=header,
            offset=absolute_offset,
            length=BLOCK_SIZE,
            parent=parent_match,
        )


for _variant in ("V7", "POSIX", "GNU"):
    MagicMatcher.DEFAULT_INSTANCE.add(TarMatcher(_variant))


def _pax_values(data: bytes) -> dict[str, str]:
    values: dict[str, str] = {}
    offset = 0
    while offset < len(data):
        space = data.find(b" ", offset)
        digits = data[offset:space]
        if space < 0 or not digits or not digits.isdigit():
            raise ValueError("PAX record has an invalid length")
        length = int(digits)
        end = offset + length
        if length < 5 or end > len(data) or data[end - 1] != 10:
            raise ValueError("PAX record is truncated or has invalid framing")
        start, stop = space + 1, end - 1
        key, separator, value = data[start:stop].partition(b"=")
        if not separator or not key:
            raise ValueError("PAX record must contain a nonempty key and '='")
        values[key.decode("utf-8")] = value.decode("utf-8", "surrogateescape")
        offset = end
    return values


@dataclass
class _TarNames:
    global_values: dict[str, str] = field(default_factory=dict)
    local_values: dict[str, str] = field(default_factory=dict)
    long_name: str | None = None
    long_link: str | None = None

    def extension(self, kind: bytes, data: bytes) -> None:
        if kind in (tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_LONGLINK):
            value = data.partition(b"\0")[0].decode("utf-8", "surrogateescape")
            if kind == tarfile.GNUTYPE_LONGNAME:
                self.long_name = value
            else:
                self.long_link = value
            return
        values = _pax_values(data)
        target = self.global_values if kind == tarfile.XGLTYPE else self.local_values
        target.update(values)

    def apply(self, info: tarfile.TarInfo) -> tuple[tarfile.TarInfo, bool]:
        info = copy(info)
        values = self.global_values | self.local_values
        if self.long_name is not None:
            info.name = self.long_name
        if self.long_link is not None:
            info.linkname = self.long_link
        for name, attribute in (("path", "name"), ("linkpath", "linkname")):
            if values.get(name):
                setattr(info, attribute, values[name])
        if values.get("size"):
            size = values["size"]
            if not size.isascii() or not size.isdigit():
                raise ValueError("PAX size must be a nonnegative decimal integer")
            info.size = int(size)
        sparse = info.type == tarfile.GNUTYPE_SPARSE or any(
            name.startswith("GNU.sparse.") for name in values
        )
        self.local_values.clear()
        self.long_name = self.long_link = None
        return info, sparse


class _TarReader:
    def __init__(self, stream: FileStream, parent: Match):
        self.stream = stream
        self.parent = parent
        self.names = _TarNames()

    def failure(self, status: str, message: str, offset: int) -> Iterator[Match]:
        self.parent.analysis_status = status
        self.parent.analysis_message = f"TAR at byte {offset}: {message}"
        remaining = max(0, len(self.stream) - offset)
        region = Submatch("unparsed", None, offset, remaining, parent=self.parent)
        region.analysis_status = status
        region.analysis_message = self.parent.analysis_message
        yield region

    def finish(self, offset: int) -> Iterator[Match]:
        if self.names.local_values or self.names.long_name or self.names.long_link:
            yield from self.failure(
                "invalid", "extension has no following member", offset
            )
            return
        self.stream.seek(offset)
        trailer = self.stream.read(2 * BLOCK_SIZE)
        if trailer != 2 * ZERO_BLOCK:
            yield from self.failure(
                "invalid", "expected two zero end-marker blocks", offset
            )
            return
        yield Submatch("end_markers", None, offset, len(trailer), parent=self.parent)
        rest = len(self.stream) - offset - len(trailer)
        if rest:
            yield Submatch(
                "trailing_data", None, offset + len(trailer), rest, parent=self.parent
            )

    def header_fields(self, header: bytes, member: Match) -> Iterator[Match]:
        region = Submatch("TarHeader", None, 0, BLOCK_SIZE, parent=member)
        yield region
        for name, start, end in HEADER_FIELDS:
            yield Submatch(name, header[start:end], start, end - start, parent=region)

    def member(
        self, info: tarfile.TarInfo, header: bytes, offset: int, size: int
    ) -> Iterator[Match]:
        padded = (size + BLOCK_SIZE - 1) // BLOCK_SIZE * BLOCK_SIZE
        available = min(padded, len(self.stream) - offset - BLOCK_SIZE)
        member = Submatch(
            "TarMember",
            repr(info.name),
            offset,
            BLOCK_SIZE + available,
            parent=self.parent,
            display_name=repr(info.name),
        )
        yield member
        yield from self.header_fields(header, member)
        if info.islnk() or info.issym():
            yield Submatch(
                "effective_linkname", repr(info.linkname), 0, 0, parent=member
            )
        data = Submatch("data", None, BLOCK_SIZE, min(size, available), parent=member)
        data.analysis_member_counted = True
        yield data
        if available < size:
            yield from self.failure(
                "invalid", "truncated member payload", offset + BLOCK_SIZE
            )
            return
        yield from self.contents(info, data, offset + BLOCK_SIZE, size)
        if available > size:
            yield Submatch(
                "padding", None, BLOCK_SIZE + size, available - size, parent=member
            )
        if available < padded:
            yield from self.failure(
                "invalid", "truncated member padding", offset + BLOCK_SIZE + size
            )

    def contents(
        self, info: tarfile.TarInfo, data: Match, offset: int, size: int
    ) -> Iterator[Match]:
        if info.type in EXTENSION_TYPES:
            self.stream.seek(offset)
            try:
                self.names.extension(info.type, self.stream.read(size))
            except (ValueError, UnicodeError) as error:
                yield from self.failure("invalid", str(error), offset)
        elif info.isreg():
            assert self.parent.matcher is not None
            with FileStream(self.stream, start=offset, length=size) as content:
                yield from self.parent.matcher.match(content, parent=data)

    def read_header(self, header: bytes) -> tuple[tarfile.TarInfo, bool]:
        info = tarfile.TarInfo.frombuf(header, "utf-8", "surrogateescape")
        sparse = False
        if info.type not in EXTENSION_TYPES:
            info, sparse = self.names.apply(info)
        if info.size < 0:
            raise ValueError("negative member size")
        if (
            info.type not in EXTENSION_TYPES
            and not info.isreg()
            and info.size
            and not sparse
        ):
            raise ValueError("non-file member declares a payload")
        return info, sparse

    def sparse_member(
        self, info: tarfile.TarInfo, header: bytes, offset: int
    ) -> Iterator[Match]:
        member = Submatch(
            "TarMember", repr(info.name), offset, BLOCK_SIZE, parent=self.parent
        )
        yield member
        yield from self.header_fields(header, member)
        yield from self.failure(
            "unsupported", "sparse members are not reconstructed", offset
        )

    def records(self) -> Iterator[Match]:
        offset = 0
        while offset < len(self.stream):
            self.stream.seek(offset)
            header = self.stream.read(BLOCK_SIZE)
            if header == ZERO_BLOCK:
                yield from self.finish(offset)
                return
            try:
                info, sparse = self.read_header(header)
            except (tarfile.HeaderError, ValueError, UnicodeError) as error:
                yield from self.failure("invalid", str(error), offset)
                return
            reason = self.parent.analysis_context.claim_entry()
            if reason is not None:
                yield from self.failure("limited", reason, offset)
                return
            if sparse:
                yield from self.sparse_member(info, header, offset)
                return
            yield from self.member(info, header, offset, info.size)
            if self.parent.analysis_status in ("invalid", "unsupported"):
                return
            offset += (
                BLOCK_SIZE + (info.size + BLOCK_SIZE - 1) // BLOCK_SIZE * BLOCK_SIZE
            )
        yield from self.failure("invalid", "missing end markers", offset)


@register_parser(*TAR_MIME_TYPES)
def parse_tar(file_stream: FileStream, parent: Match) -> Iterator[Match]:
    """Map plain TAR records and recursively analyze complete regular-file members.

    Args:
        file_stream: Archive bytes in the current content buffer.
        parent: The match representing this TAR archive.

    Yields:
        Physical header fields, member data, padding, end markers, and nested file matches.
    """
    yield from _TarReader(file_stream, parent).records()
