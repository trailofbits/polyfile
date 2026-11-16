"""Isolated py7zr adapter; input and output paths are never archive-controlled."""

import json
import io
import shutil
import sys
import tempfile
import zlib
from importlib.metadata import version
from typing import BinaryIO, cast

try:
    if version("py7zr") != "1.1.4":
        raise ImportError("the 7z adapter requires py7zr==1.1.4")
    import py7zr
    from py7zr import archiveinfo
    from py7zr.exceptions import Bad7zFile, PasswordRequired, UnsupportedCompressionMethodError
    from py7zr.io import Py7zIO, WriterFactory
except ImportError as error:
    print(f"unsupported: install py7zr==1.1.4 and its dependencies: {error}", file=sys.stderr)
    raise SystemExit(2) from error


class _Failure(ValueError):
    def __init__(self, status: str, message: str) -> None:
        super().__init__(message)
        self.status = status


class _Sink(Py7zIO):
    def __init__(self, stream: BinaryIO, start: int, size: int) -> None:
        self.stream = stream
        self.start = start
        self.position = 0
        self.expected = size
        self.written = 0

    def write(self, s: bytes | bytearray) -> int:
        if self.position + len(s) > self.expected:
            raise _Failure("invalid", "7z member exceeds its declared decoded size")
        self.stream.seek(self.start + self.position)
        self.position += len(s)
        self.written = max(self.written, self.position)
        return self.stream.write(s)

    def read(self, size: int | None = None) -> bytes:
        length = self.expected - self.position
        if size is not None and size >= 0:
            length = min(length, size)
        self.stream.seek(self.start + self.position)
        data = self.stream.read(length)
        self.position += len(data)
        return data

    def seek(self, offset: int, whence: int = 0) -> int:
        origins = (0, self.position, self.expected)
        position = origins[whence] + offset
        if not 0 <= position <= self.expected:
            raise _Failure("invalid", "7z decoder sought outside a member's decoded range")
        self.position = position
        return position

    def flush(self) -> None:
        self.stream.flush()

    def size(self) -> int:
        return self.written


class _Factory(WriterFactory):
    def __init__(self, sinks: dict[str, _Sink]) -> None:
        self.sinks = sinks

    def create(self, filename: str) -> Py7zIO:
        return self.sinks[filename]


def _optional(value: str) -> int | None:
    return None if value == "none" else int(value)


def _members(archive: py7zr.SevenZipFile) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for member in archive.files:
        result.append(
            {
                "name": member.filename,
                "size": member.uncompressed,
                "directory": member.is_directory,
                "special": not (member.is_file or member.is_directory),
                "crc": member.crc32,
            }
        )
    return result


def _admit(members: list[dict[str, object]], limits: list[int | None]) -> int:
    count, per_member, total = limits
    if count is not None and len(members) > count:
        raise _Failure("limited", f"7z member count exceeds the remaining allowance of {count}")
    size = 0
    for member in members:
        length = cast(int, member["size"])
        if length < 0:
            raise _Failure("invalid", "7z member has a negative decoded size")
        if member["directory"]:
            if length:
                raise _Failure("invalid", "7z directory contains a nonempty stream")
            continue
        if per_member is not None and length > per_member:
            raise _Failure("limited", f"7z member exceeds the {per_member}-byte allowance")
        size += length
        if total is not None and size > total:
            raise _Failure("limited", f"7z decoded contents exceed the {total}-byte allowance")
    return size


def _ranges(
    archive: py7zr.SevenZipFile,
    info: archiveinfo.PackInfo,
    end: int,
) -> list[list[int]]:
    offset = archive.afterheader + info.packpos
    packed: list[list[int]] = []
    crc_index = 0
    for index, size in enumerate(info.packsizes):
        if offset < archive.afterheader or size > end - offset:
            raise _Failure("invalid", "7z packed stream lies outside the archive")
        if info.digestdefined and info.digestdefined[index]:
            archive.fp.seek(offset)
            remaining, checksum = size, 0
            while remaining:
                chunk = archive.fp.read(min(remaining, 64 * 1024))
                if not chunk:
                    raise _Failure("invalid", "7z packed stream is truncated")
                checksum = zlib.crc32(chunk, checksum)
                remaining -= len(chunk)
            if checksum != info.crcs[crc_index]:
                raise _Failure("invalid", "7z packed-stream checksum mismatch")
            crc_index += 1
        packed.append([offset, size])
        offset += size
    return packed


def _structure(archive: py7zr.SevenZipFile) -> dict[str, list[list[int]]]:
    offset = archive.afterheader + archive.sig_header.nextheaderofs
    archive.fp.seek(offset)
    next_header = io.BytesIO(archive.fp.read(archive.sig_header.nextheadersize))
    packed_header: list[list[int]] = []
    if next_header.read(1) == b"\x17":
        streams = archiveinfo.HeaderStreamsInfo.retrieve(next_header)
        packed_header = _ranges(archive, streams.packinfo, offset)
    streams = archive.header.main_streams
    packed = [] if streams is None else _ranges(archive, streams.packinfo, offset)
    end = max((start + size for start, size in packed), default=HEADER_SIZE)
    if any(start < end for start, _ in packed_header):
        raise _Failure("invalid", "7z encoded header overlaps packed member data")
    return {"packed": packed, "packed_header": packed_header}


HEADER_SIZE = 32

_UNSUPPORTED_HEADERS = {
    "end id expected but b'\\x02' found": "archive properties",
    "end id expected but b'\\x03' found": "additional metadata streams",
    "invalid type b'\\x10'": "anti-file entries",
}


def _extract(archive: py7zr.SevenZipFile, members: list[dict[str, object]]) -> None:
    with tempfile.TemporaryFile() as output:
        sinks: dict[str, _Sink] = {}
        offset = 0
        for index, (entry, member) in enumerate(zip(archive.files, members, strict=True)):
            name = f"entry-{index}"
            entry.file_properties()["filename"] = name
            if member["directory"]:
                continue
            if member["special"]:
                raise _Failure("unsupported", "7z special-file entries are not decoded")
            size = cast(int, member["size"])
            sinks[name] = _Sink(output, offset, size)
            offset += size
        streams = archive.header.main_streams
        if streams is not None:
            archive.worker.src_start = archive.afterheader + streams.packinfo.packpos
        archive.extractall(factory=_Factory(sinks))
        for sink in sinks.values():
            if sink.written != sink.expected:
                raise _Failure("invalid", "7z member does not match its declared decoded size")
        output.seek(0)
        shutil.copyfileobj(output, sys.stdout.buffer, 64 * 1024)


def _run() -> None:
    operation, *arguments = sys.argv[1:]
    limits = [_optional(argument) for argument in arguments]
    if limits[0] is not None:
        setattr(archiveinfo, "MAX_NUMFILES", min(archiveinfo.MAX_NUMFILES, limits[0]))
    with tempfile.TemporaryFile() as stream:
        shutil.copyfileobj(sys.stdin.buffer, stream, 64 * 1024)
        stream.seek(0)
        with py7zr.SevenZipFile(stream, "r") as archive:
            if archive.needs_password():
                raise _Failure("unsupported", "encrypted 7z archives require a password")
            members = _members(archive)
            _admit(members, limits)
            structure = _structure(archive)
            if operation == "metadata":
                metadata = {"members": members, **structure}
                sys.stdout.buffer.write(json.dumps(metadata, ensure_ascii=True).encode("ascii"))
            else:
                _extract(archive, members)


def _failure(error: Exception) -> _Failure:
    if isinstance(error, _Failure):
        return error
    if isinstance(error, (PasswordRequired, UnsupportedCompressionMethodError)):
        return _Failure("unsupported", str(error))
    if isinstance(error, MemoryError):
        return _Failure("limited", "7z decoder exhausted its memory allowance")
    if not isinstance(error, Bad7zFile):
        return _Failure("invalid", f"cannot decode 7z archive: {error}")
    feature = _UNSUPPORTED_HEADERS.get(str(error))
    if feature is not None:
        return _Failure("unsupported", f"the 7z backend does not support {feature}")
    limited = str(error).startswith("numfiles value") and sys.argv[2] != "none"
    return _Failure("limited" if limited else "invalid", f"cannot decode 7z archive: {error}")


def main() -> None:
    """Run the fixed adapter operation and report expected failures without a traceback."""
    try:
        _run()
    except Exception as error:
        failure = _failure(error)
        print(f"{failure.status}: {failure}", file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
