from collections.abc import Iterable, Iterator
from contextlib import AbstractContextManager
from io import BytesIO, SEEK_CUR, SEEK_END, SEEK_SET, TextIOBase, UnsupportedOperation
import mmap
import os
from pathlib import Path
import tempfile as tf
import shutil
import sys
from types import TracebackType
from typing import BinaryIO, Never, Self, TextIO, cast, overload


Streamable = str | Path | BinaryIO | bytes


def make_stream(
    path_or_stream: Streamable, mode: str = "rb", close_on_exit: bool | None = None
) -> "FileStream":
    """Wrap binary input, returning an existing FileStream without repositioning it.

    Args:
        path_or_stream: A path, binary input stream, or bytes to expose.
        mode: Readable binary mode for a path; ignored for an existing FileStream.
        close_on_exit: Ownership override for a new view; ignored for an existing FileStream.

    Returns:
        The supplied FileStream or a new view positioned at its beginning.
    """
    if isinstance(path_or_stream, FileStream):
        return path_or_stream
    else:
        return FileStream(path_or_stream, mode=mode, close_on_exit=close_on_exit)


class Tempfile:
    def __init__(self, contents: bytes, prefix: str | None = None, suffix: str | None = None):
        self._path: str | None = None
        self._data: bytes = contents
        self._prefix: str | None = prefix
        self._suffix: str | None = suffix

    def __enter__(self) -> str:
        tmp = tf.NamedTemporaryFile(prefix=self._prefix, suffix=self._suffix, delete=False)
        tmp.write(self._data)
        tmp.flush()
        tmp.close()
        self._path = tmp.name
        return tmp.name

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._path is not None:
            os.unlink(self._path)
            self._path = None


class ExactNamedTempfile(Tempfile):
    def __init__(self, contents: bytes, name: str):
        super().__init__(contents)
        self._name: str = name

    def __enter__(self) -> str:
        tmpdir = Path(tf.mkdtemp())
        file_path = tmpdir / self._name
        with open(file_path, "wb") as f:
            f.write(self._data)
        self._path = str(tmpdir)
        return str(file_path)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._path is not None:
            shutil.rmtree(self._path)
            self._path = None


class PathOrStdin:
    def __init__(self, path: str):
        self.path: str = path
        if self.path == "-":
            self._tempfile: ExactNamedTempfile | None = ExactNamedTempfile(
                sys.stdin.buffer.read(), "STDIN"
            )
        elif not Path(path).exists():
            raise FileNotFoundError(path)
        else:
            self._tempfile = None

    def __enter__(self) -> str:
        if self._tempfile is None:
            return self.path
        else:
            return self._tempfile.__enter__()

    def __exit__(self, *args, **kwargs):
        if self._tempfile is not None:
            return self._tempfile.__exit__(*args, **kwargs)


class PathOrStdout(AbstractContextManager[TextIO]):
    def __init__(self, path: str):
        self.path: str = path
        if self.path == "-":
            self._tempfile: TextIO | None = sys.stdout
        else:
            self._tempfile = None

    def __enter__(self) -> TextIO:
        if self._tempfile is None:
            self._tempfile = open(self.path, "w")
        return self._tempfile

    def __exit__(self, *args, **kwargs) -> None:
        if self._tempfile is not None:
            if self._tempfile is not sys.stdout:
                self._tempfile.close()
                self._tempfile = None
        return None


class FileStream(BinaryIO):
    """A read-only, bounded view of a seekable binary input with a shared cursor.

    Constructor ``start`` is relative to the immediate input. ``offset()`` is the fixed
    beginning of this view in the backing root buffer; ``tell()`` and ``seek()`` use positions
    relative to this view. A decoded buffer is its own root: its offsets do not identify byte
    positions in the original compressed file, and this class does not carry analysis source IDs.

    Views keep their parent streams and delegate reads through them, preserving transformations
    implemented by parent subclasses. All related views share the root's cursor. Construction
    and slicing move it; content inspection and integer indexing restore it. A sibling may move
    the cursor outside this view, in which case ``tell()`` clamps to its nearest boundary.

    A path opened here closes when its outermost context exits. Supplied streams and buffers
    created from bytes stay open by default. ``close_on_exit`` overrides that policy. Closing a
    shared backing stream invalidates all its views; the class does not coordinate threads.
    """

    def __init__(
        self,
        path_or_stream: Streamable,
        start: int = 0,
        length: int | None = None,
        mode: str = "rb",
        close_on_exit: bool | None = None,
    ) -> None:
        """Presents a region of a file or stream as a stream in its own right.

        Args:
            path_or_stream: The bytes to read. A path is opened, `bytes` are wrapped in a
                `BytesIO`, and an already-open stream is wrapped in place.
            start: Nonnegative byte offset from the immediate input's beginning. Values beyond
                its EOF clamp to EOF, producing an empty view.
            length: How many bytes this stream holds, counted from `start` rather than from the
                beginning of `path_or_stream`, and clamped to the bytes that remain after
                `start`. Defaults to all of them.
            mode: Readable binary mode for a path, such as ``rb`` or ``r+b``. Text, append,
                create, and truncate modes are rejected before opening a path.
            close_on_exit: Whether leaving this stream's context closes the underlying stream,
                defaulting to True for a path this opened and False for supplied streams or
                buffers created from bytes. Construction seeks the shared cursor to view zero.

        Raises:
            TypeError: If the supplied stream is a text stream.
            ValueError: If start or length is negative, the mode is unsuitable, or the stream
                is not readable and seekable.
            OSError: If the path cannot be opened or the backing stream cannot be positioned.
        """
        if start < 0 or (length is not None and length < 0):
            raise ValueError("FileStream start and length must be nonnegative")
        self._stream, owns_input = self._open_input(path_or_stream, mode)
        if isinstance(self._stream, FileStream):
            stream_length = len(self._stream)
        else:
            orig_pos = self._stream.tell()
            self._stream.seek(0, SEEK_END)
            try:
                stream_length = self._stream.tell()
            finally:
                self._stream.seek(orig_pos)
        start = min(start, stream_length)
        remaining = stream_length - start
        self._length = remaining if length is None else min(length, remaining)
        self._name: str | bytes | int = getattr(self._stream, "name", "bytes")
        self.start = start
        self.close_on_exit = owns_input if close_on_exit is None else close_on_exit
        self._entries = 0
        self._root: BinaryIO | None = None
        self.seek(0)

    @staticmethod
    def _open_input(path_or_stream: Streamable, mode: str) -> tuple[BinaryIO, bool]:
        if isinstance(path_or_stream, (str, Path)):
            if "b" not in mode or any(flag in mode for flag in "wax"):
                raise ValueError("FileStream requires a readable binary, read-only view mode")
            return cast(BinaryIO, open(path_or_stream, mode)), True
        if isinstance(path_or_stream, bytes):
            return BytesIO(path_or_stream), False
        if isinstance(path_or_stream, TextIOBase):
            raise TypeError("FileStream requires binary input, not a text stream")
        if not path_or_stream.seekable():
            raise ValueError("FileStream can only wrap streams that are seekable")
        if not path_or_stream.readable():
            raise ValueError("FileStream can only wrap streams that are readable")
        return path_or_stream, False

    def __len__(self) -> int:
        """Return the fixed byte length of this view without moving the cursor."""
        return self._length

    def seekable(self) -> bool:
        """Return True; view-relative seeks are supported within the view's boundaries."""
        return True

    def writable(self) -> bool:
        """Return False, including when the backing file permits writes."""
        return False

    def readable(self) -> bool:
        """Return True; reads are bounded to this view's remaining bytes."""
        return True

    @property
    def name(self) -> str | bytes | int:
        """The backing stream's name or descriptor, or ``bytes`` for an unnamed buffer.

        This label identifies neither a view nor an analysis source and carries no byte offset.
        """
        return self._name

    def __str__(self) -> str:
        """Return the backing label without reading or repositioning the stream."""
        return str(self._name)

    @property
    def mode(self) -> str:
        """The view's read-only binary mode, regardless of its backing file's open mode."""
        return "rb"

    @property
    def closed(self) -> bool:
        """Whether the immediate backing stream is closed."""
        return self._stream.closed

    @property
    def root(self) -> BinaryIO:
        """The lowest backing stream, whose cursor uses root-buffer coordinates.

        A decoded byte buffer is a separate root from the file that encoded it. This property
        does not follow analysis parents or translate decoded offsets into physical-file offsets.
        """
        if self._root is None:
            if isinstance(self._stream, FileStream):
                self._root = self._stream.root
            else:
                self._root = self._stream
        return self._root

    def save_pos(self) -> AbstractContextManager["FileStream"]:
        """Capture the raw root cursor and return a context that restores it on exit.

        The snapshot happens when this method is called. The context yields this view, permits
        temporary cursor changes through any related view, and restores even positions outside
        this view on normal or exceptional exit. It does not close the stream or suppress errors.
        """
        f = self

        class SavedPosition(AbstractContextManager[FileStream]):
            def __init__(self) -> None:
                self.pos = f.root.tell()

            def __enter__(self) -> FileStream:
                return f

            def __exit__(
                self,
                exc_type: type[BaseException] | None,
                exc_val: BaseException | None,
                exc_tb: TracebackType | None,
            ) -> None:
                f.root.seek(self.pos)

        return SavedPosition()

    def fileno(self) -> int:
        """Return the backing descriptor without translating its root-buffer coordinates.

        Raises:
            UnsupportedOperation: If the backing buffer has no descriptor.
        """
        return self._stream.fileno()

    def offset(self) -> int:
        """Return this view's fixed starting byte in the current backing root buffer.

        The result sums parent-relative origins and never includes the cursor position. For
        decoded buffers, it refers to decoded bytes, not the original compressed file.
        """
        if isinstance(self._stream, FileStream):
            return self._stream.offset() + self.start
        else:
            return self.start

    def seek(self, offset: int, from_what: int = SEEK_SET) -> int:
        """Move the shared cursor to a bounded position relative to this view.

        Args:
            offset: Byte displacement from the origin selected by ``from_what``.
            from_what: ``SEEK_SET`` for view zero, ``SEEK_CUR`` for the clamped local cursor,
                or ``SEEK_END`` for this view's length. The keyword name is retained.

        Returns:
            The resulting position relative to this view; zero and EOF are valid targets.

        Raises:
            ValueError: If ``from_what`` is not a supported origin.
            IndexError: If the resolved local position is outside ``[0, len(self)]``.
        """
        if from_what == SEEK_CUR:
            offset = self.tell() + offset
        elif from_what == SEEK_END:
            offset = len(self) + offset
        elif from_what != SEEK_SET:
            raise ValueError(f"Invalid FileStream seek origin: {from_what}")
        if not 0 <= offset <= self._length:
            raise IndexError(
                f"{self!r} is {len(self)} bytes long, but seek requested byte {offset}"
            )
        self._stream.seek(self.start + offset)
        return offset

    def tell(self) -> int:
        """Return the shared cursor's view-relative position, clamped to this view.

        A sibling can position the root outside this region. Before its beginning this returns
        zero; after its end this returns its length. Calling this method never repositions it.
        """
        return min(max(self._stream.tell() - self.start, 0), self._length)

    def read(self, n: int | None = None) -> bytes:
        """Read at most the remaining bytes of this view and advance the shared cursor.

        Args:
            n: Maximum bytes to read. None or a negative value reads the remaining region.

        Returns:
            Bytes read through the parent stream, preserving its transformations. If a sibling
            moved the cursor before the view, reading resumes at view zero. At or after its EOF,
            the result is empty and the cursor stays unchanged.
        """
        if self._stream.tell() - self.start < 0:
            # another context moved the position, so move it back to our zero index:
            self.seek(0)
            pos = 0
        else:
            pos = self.tell()
        ls = len(self)
        if pos >= ls:
            return b""
        if n is None or n < 0:
            n = ls - pos
        return self._stream.read(min(n, ls - pos))

    def contains_all(self, *args: bytes) -> bool:
        """Check whether every byte sequence occurs within this view, preserving the cursor.

        Descriptor-backed views search root bytes with mmap; memory views inspect their bounded
        content through parent reads. An empty argument list succeeds, as do empty sequences.
        """
        if args:
            try:
                descriptor = self.fileno()
            except UnsupportedOperation:
                data = self.content
                return all(string in data for string in args)
            if not len(self):
                return all(not string for string in args)
            with mmap.mmap(descriptor, 0, access=mmap.ACCESS_READ) as filecontent:
                for string in args:
                    if filecontent.find(string, self.offset(), self.offset() + len(self)) < 0:
                        return False
        return True

    def first_index_of(self, byte_sequence: bytes) -> int:
        """Find a byte sequence within this view without changing the shared cursor.

        Args:
            byte_sequence: Bytes to locate, with an empty sequence matching view zero.

        Returns:
            The first view-relative byte index, or -1 when absent. Descriptor-backed searches
            inspect root bytes with mmap; memory-backed searches use bounded parent reads.
        """
        if not len(self):
            return 0 if not byte_sequence else -1
        try:
            descriptor = self.fileno()
        except UnsupportedOperation:
            return self.content.find(byte_sequence)
        with mmap.mmap(descriptor, 0, access=mmap.ACCESS_READ) as filecontent:
            start_offset = self.offset()
            end_offset = start_offset + len(self)
            index = filecontent.find(byte_sequence, start_offset, end_offset)
            if start_offset <= index < end_offset:
                return index - start_offset
            else:
                return -1

    @property
    def content(self) -> bytes:
        """All bytes in this view, preserving the exact root cursor even outside the view.

        Parent read transformations apply. The whole bounded region is materialized in memory.
        """
        with self.save_pos():
            self.seek(0)
            return self.read(len(self))

    def __bytes__(self) -> bytes:
        """Return the complete bounded content without changing the shared cursor."""
        return self.content

    def tempfile(
        self, prefix: str | None = None, suffix: str | None = None
    ) -> AbstractContextManager[str]:
        """Export this view to a temporary file while preserving the shared cursor.

        Args:
            prefix: Optional temporary filename prefix.
            suffix: Optional temporary filename suffix.

        Returns:
            A context yielding the filename. Entry copies the view through its parent reads
            in bounded chunks; exit removes the file without closing the original stream.
        """

        class FSTempfile(AbstractContextManager[str]):
            def __init__(self, file_stream: FileStream) -> None:
                self._path: str | None = None
                self._fs: FileStream = file_stream

            def __enter__(self) -> str:
                with (
                    tf.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=False) as temporary,
                    self._fs.save_pos(),
                ):
                    self._fs.seek(0)
                    while True:
                        b = self._fs.read(1048576)  # write 1 MiB at a time
                        if not b:
                            break
                        temporary.write(b)
                    self._path = temporary.name
                return self._path

            def __exit__(
                self,
                exc_type: type[BaseException] | None,
                exc_val: BaseException | None,
                exc_tb: TracebackType | None,
            ) -> None:
                if self._path is not None:
                    os.unlink(self._path)
                    self._path = None

        return FSTempfile(self)

    @overload
    def __getitem__(self, index: int) -> bytes: ...

    @overload
    def __getitem__(self, index: slice) -> "FileStream": ...

    def __getitem__(self, index: int | slice) -> "bytes | FileStream":
        """Return one byte or a unit-step subview using Python's indexing bounds.

        Negative integer indexes count from the end, and integer access preserves the root
        cursor. Slices normalize omitted, negative, and excessive bounds like bytes; constructing
        their subview moves the shared cursor to the normalized slice start. Subviews borrow the
        parent and delegate reads through it.

        Args:
            index: A byte index or a slice with step omitted or equal to one.

        Returns:
            A one-byte bytes object for an integer, or a possibly empty FileStream for a slice.

        Raises:
            IndexError: If the integer index does not identify a byte in this view.
            ValueError: If the argument is neither an integer nor a slice, or its step is not one.
        """
        if isinstance(index, int):
            if index < 0:
                index += len(self)
            if not 0 <= index < len(self):
                raise IndexError(f"FileStream byte index {index} is outside its {len(self)} bytes")
            with self.save_pos():
                self.seek(index)
                return self.read(1)
        elif not isinstance(index, slice):
            raise ValueError(f"unexpected argument {index}")
        if index.step is not None and index.step != 1:
            raise ValueError(f"Invalid slice step: {index}")
        start, stop, _ = index.indices(len(self))
        return FileStream(self, start=start, length=max(stop - start, 0), close_on_exit=False)

    def __enter__(self) -> Self:
        """Enter this view without moving the cursor; contexts on one view may nest."""
        self._entries += 1
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit one context and close owned input when this view's outermost context ends.

        Cursor positions are not restored and exceptions are not suppressed. Borrowed input
        remains open unless ``close_on_exit`` was explicitly enabled.
        """
        self._entries -= 1
        assert self._entries >= 0
        if self._entries == 0 and self.close_on_exit:
            self.close_on_exit = False
            self._stream.close()

    def close(self) -> None:
        """Close the immediate backing stream when this view has no active context.

        Explicit closing applies to borrowed input too and can invalidate sibling views. Calls
        inside an active context do nothing; its normal ownership policy still applies on exit.
        """
        if self._entries == 0:
            self._stream.close()

    def flush(self) -> None:
        """Flush the backing stream without changing its cursor."""
        self._stream.flush()

    def isatty(self) -> bool:
        """Return whether the backing stream is attached to a terminal."""
        return self._stream.isatty()

    def readline(self, limit: int = -1) -> Never:
        """Raise UnsupportedOperation; this view supports bounded byte reads only."""
        raise UnsupportedOperation("FileStream does not support line reads")

    def readlines(self, hint: int = -1) -> Never:
        """Raise UnsupportedOperation; this view supports bounded byte reads only."""
        raise UnsupportedOperation("FileStream does not support line reads")

    def truncate(self, size: int | None = None) -> Never:
        """Raise UnsupportedOperation because views never modify backing bytes."""
        raise UnsupportedOperation("FileStream is read-only")

    def write(self, s: object) -> Never:
        """Raise UnsupportedOperation because views never modify backing bytes."""
        raise UnsupportedOperation("FileStream is read-only")

    def writelines(self, lines: Iterable[object]) -> Never:
        """Raise UnsupportedOperation because views never modify backing bytes."""
        raise UnsupportedOperation("FileStream is read-only")

    def __next__(self) -> Never:
        """Raise UnsupportedOperation; use read() or integer indexing instead."""
        raise UnsupportedOperation("FileStream does not support line iteration")

    def __iter__(self) -> Iterator[bytes]:
        """Raise UnsupportedOperation; use read() or integer indexing instead."""
        raise UnsupportedOperation("FileStream does not support line iteration")
