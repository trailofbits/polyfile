"""Bound PDF filter expansion before a decoded buffer can be retained."""

import base64
from io import BytesIO
import re
import zlib

from polyfile._pdfminer_adapter import (
    LITERALS_ASCII85_DECODE,
    LITERALS_ASCIIHEX_DECODE,
    LITERALS_DCT_DECODE,
    LITERALS_FLATE_DECODE,
    LITERALS_JBIG2_DECODE,
    LITERALS_LZW_DECODE,
    LITERALS_RUNLENGTH_DECODE,
    LIT,
    LZWDecoder,
    PDFNotImplementedError,
)
from polyfile.compression import CHUNK_SIZE, DecodeError, OutputBuffer


class PDFDecodeLimit(PDFNotImplementedError):
    """A stream cannot be decoded within the requested analysis policy."""

    def __init__(self, message: str, *, status: str = "limited") -> None:
        super().__init__(message)
        self.status = status


def _flate(data: bytes, limit: int) -> bytes:
    decoder = zlib.decompressobj()
    output = OutputBuffer(limit)
    for start in range(0, len(data), CHUNK_SIZE):
        end = start + CHUNK_SIZE
        pending = data[start:end]
        while pending:
            output.append(decoder.decompress(pending, output.next_size))
            pending = decoder.unconsumed_tail
    if not decoder.eof:
        raise zlib.error("incomplete or truncated PDF Flate stream")
    return output.finish()


def _ascii85(data: bytes, limit: int) -> bytes:
    data = re.sub(rb"^\s*<?\s*~\s*", b"", data)
    data = re.sub(rb"\s*~\s*>?\s*$", b"", data)
    output = OutputBuffer(limit)
    group = bytearray()
    for value in data:
        if value in b" \t\n\r\v":
            continue
        group.append(value)
        if len(group) == 5 or value == ord("z"):
            _append_ascii85(output, bytes(group))
            group.clear()
    if group:
        _append_ascii85(output, bytes(group))
    return output.finish()


def _append_ascii85(output: OutputBuffer, group: bytes) -> None:
    size = 4 if group == b"z" else len(group) - 1
    _check_size(output, size)
    output.append(base64.a85decode(group))


def _check_size(output: OutputBuffer, size: int) -> None:
    if output.remaining is not None and size > output.remaining:
        raise DecodeError(
            f"PDF filter output exceeds the {output.max_output}-byte analysis allowance",
            status="limited",
        )


def _asciihex(data: bytes, limit: int) -> bytes:
    output = OutputBuffer(limit)
    high = None
    for value in data:
        if value in b" \t\n\r\v\f":
            continue
        if value == ord(">"):
            if high is not None:
                output.append(bytes([high * 16]))
            return output.finish()
        digit = int(chr(value), 16)
        if high is None:
            high = digit
        else:
            output.append(bytes([high * 16 + digit]))
            high = None
    if high is not None:
        raise ValueError("Odd-length PDF ASCIIHex data without an end marker")
    return output.finish()


def _runlength(data: bytes, limit: int) -> bytes:
    output = OutputBuffer(limit)
    position = 0
    while position < len(data):
        control = data[position]
        position += 1
        if control == 128:
            break
        size = control + 1 if control < 128 else 257 - control
        consumed = size if control < 128 else 1
        if position + consumed > len(data):
            raise ValueError("Truncated PDF RunLength data")
        _check_size(output, size)
        end = position + size
        chunk = data[position:end] if control < 128 else bytes([data[position]]) * size
        output.append(chunk)
        position += consumed
    return output.finish()


class _BoundedLZW(LZWDecoder):
    def __init__(self, data: bytes, limit: int) -> None:
        super().__init__(BytesIO(data))
        self.output = OutputBuffer(limit)

    def feed(self, code: int) -> bytes:
        if code not in (256, 257):
            if code < len(self.table):
                value = self.table[code]
                if value is not None:
                    _check_size(self.output, len(value))
            elif code == len(self.table) and self.prevbuf is not None:
                _check_size(self.output, len(self.prevbuf) + 1)
        return super().feed(code)

    def decode(self) -> bytes:
        for chunk in self.run():
            self.output.append(chunk)
        return self.output.finish()


def decode_bounded_filter(filter_name: object, data: bytes, limit: int) -> bytes | None:
    """Decode one filter without constructing more than its output allowance.

    Args:
        filter_name: PDFminer literal naming the stream filter.
        data: Complete encoded bytes for this filter stage.
        limit: Maximum decoded bytes allowed for this stage.

    Returns:
        Decoded bytes, or None for an image filter that passes bytes through.

    Raises:
        PDFDecodeLimit: If expansion exceeds the allowance or cannot be bounded.
    """
    try:
        return _bounded_filter(filter_name, data, limit)
    except DecodeError as error:
        raise PDFDecodeLimit(str(error), status=error.status) from error


def _bounded_filter(filter_name: object, data: bytes, limit: int) -> bytes | None:
    decoders = (
        (LITERALS_FLATE_DECODE, _flate),
        (LITERALS_ASCII85_DECODE, _ascii85),
        (LITERALS_ASCIIHEX_DECODE, _asciihex),
        (LITERALS_RUNLENGTH_DECODE, _runlength),
    )
    for names, decoder in decoders:
        if filter_name in names:
            return decoder(data, limit)
    if filter_name in LITERALS_LZW_DECODE:
        return _BoundedLZW(data, limit).decode()
    if filter_name in LITERALS_DCT_DECODE or filter_name in LITERALS_JBIG2_DECODE:
        return None
    if filter_name == LIT("JPXDecode"):
        return None
    raise PDFDecodeLimit(
        f"PDF filter {filter_name!r} cannot honor a decoded-byte allowance",
        status="unsupported",
    )
