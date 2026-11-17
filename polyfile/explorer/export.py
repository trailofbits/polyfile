"""Exact, cancellable extraction of source-qualified explorer ranges."""

from collections.abc import Callable
from contextlib import suppress
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from polyfile.explorer.model import ByteRange, ByteSource
from polyfile.explorer.search import check_cancelled


def _validate_range(source: ByteSource, selection: ByteRange) -> None:
    if selection.source != source.identifier:
        raise ValueError("The selected range belongs to a different analysis source.")
    if selection.start < 0 or selection.length < 0 or selection.end > source.length:
        raise ValueError("The selected range extends beyond its analysis source.")
    if not source.available:
        raise OSError(f"The bytes for analysis source {source.identifier!r} are unavailable.")


def _protect_input(destination: Path, input_path: Path) -> None:
    if destination.resolve() == input_path.resolve():
        raise ValueError("Choose a destination other than the analyzed input file.")
    if destination.exists() and input_path.exists() and destination.samefile(input_path):
        raise ValueError("The destination refers to the analyzed input file.")


def _publish(temporary: Path, destination: Path, *, overwrite: bool) -> None:
    if overwrite:
        os.replace(temporary, destination)
    else:
        os.link(temporary, destination)
        temporary.unlink()


def export_range(
    source: ByteSource, selection: ByteRange, destination: Path, *, input_path: Path,
    overwrite: bool = False, cancelled: Callable[[], bool] | None = None,
) -> None:
    """Atomically export exact bytes, preserving existing files on failure or cancellation.

    Args:
        source: Physical or decoded source containing the selection.
        selection: Byte range within that source; a zero-length range is allowed.
        destination: User-selected output path, never derived from an archive member name.
        input_path: Analyzed input to protect, including its symlinks and hard links.
        overwrite: Whether the user approved replacement of an existing destination.
        cancelled: Optional cooperative cancellation predicate.

    Raises:
        ValueError: If the range is invalid or the destination refers to the input.
        FileExistsError: If replacement was not approved and the destination exists.
        CancelledError: If cancellation occurs before the export is committed.
        OSError: If reading, writing, or publishing the destination fails.
    """
    _validate_range(source, selection)
    _protect_input(destination, input_path)
    check_cancelled(cancelled)
    if not overwrite and (destination.exists() or destination.is_symlink()):
        raise FileExistsError(f"Destination already exists: {destination}")
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(dir=destination.parent, prefix=".polyfile-", delete=False) as out:
            temporary = Path(out.name)
            for _, chunk in source.iter_chunks(selection.start, selection.length):
                check_cancelled(cancelled)
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
        check_cancelled(cancelled)
        _protect_input(destination, input_path)
        _publish(temporary, destination, overwrite=overwrite)
    except OSError as error:
        error.add_note(f"Exporting {source.identifier!r} to {str(destination)!r}")
        raise
    finally:
        if temporary is not None:
            with suppress(FileNotFoundError):
                temporary.unlink()


def selection_hex(
    source: ByteSource, selection: ByteRange, *, cancelled: Callable[[], bool] | None = None,
) -> str:
    """Prepare exact space-separated hex bytes with cooperative cancellation."""
    _validate_range(source, selection)
    pieces = []
    for _, chunk in source.iter_chunks(selection.start, selection.length):
        check_cancelled(cancelled)
        pieces.append(chunk.hex(" "))
    check_cancelled(cancelled)
    return " ".join(pieces)
