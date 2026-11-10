"""Bounded incremental liblzma decoding for XZ and LZMA-alone streams."""

from typing import Literal

from polyfile.compression import CHUNK_SIZE, DecodeError, OutputBuffer
from polyfile.fileutils import FileStream


def _decode_error(
    error: Exception, format: str, start: int, max_memory: int | None
) -> DecodeError:
    status = (
        "limited"
        if max_memory is not None and "Memory usage limit" in str(error)
        else "invalid"
    )
    return DecodeError(
        f"{format} stream at byte offset {start}: {error}", status=status
    )


def inflate_lzma(
    stream: FileStream,
    output: OutputBuffer,
    start: int,
    *,
    format: Literal["xz", "alone"],
    max_memory: int | None,
    check_id: int | None = None,
) -> int:
    """Decode one framed liblzma stream with native output and memory limits.

    Args:
        stream: Encoded source bytes.
        output: Aggregate decoded output with an optional byte allowance.
        start: Physical beginning of this stream.
        format: XZ or LZMA-alone framing.
        max_memory: Native decoder memory allowance, or None for unlimited.
        check_id: XZ integrity-check ID to require from the installed backend.

    Returns:
        The physical end offset, leaving the source positioned at that offset.

    Raises:
        DecodeError: If the backend is missing or framing, integrity, or limits fail.
    """
    try:
        import lzma
    except ImportError as error:
        raise DecodeError(
            "LZMA decoding requires Python built with the lzma module",
            status="unsupported",
        ) from error
    if check_id is not None and not lzma.is_check_supported(check_id):
        raise DecodeError(
            f"unsupported XZ integrity check ID {check_id}", status="unsupported"
        )
    framing = lzma.FORMAT_XZ if format == "xz" else lzma.FORMAT_ALONE
    max_memory = None if max_memory is None else min(max_memory, (1 << 64) - 1)
    decoder = lzma.LZMADecompressor(format=framing, memlimit=max_memory)
    stream.seek(start)
    try:
        while not decoder.eof:
            chunk = stream.read(CHUNK_SIZE) if decoder.needs_input else b""
            if decoder.needs_input and not chunk:
                raise DecodeError(f"truncated {format} stream at byte offset {start}")
            output.append(decoder.decompress(chunk, max_length=output.next_size))
    except lzma.LZMAError as error:
        raise _decode_error(error, format, start, max_memory) from error
    end = stream.tell() - len(decoder.unused_data)
    stream.seek(end)
    return end
