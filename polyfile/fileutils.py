from io import BytesIO, SEEK_END, UnsupportedOperation
import mmap
import os
from pathlib import Path
import tempfile as tf
import shutil
import sys
from typing import AnyStr, ContextManager, IO, Iterator, Iterable, List, Optional, TextIO, Union


Streamable = Union[str, Path, IO, "FileStream", bytes]


def make_stream(path_or_stream: Streamable, mode: str = 'rb',
                close_on_exit: Optional[bool] = None) -> "FileStream":
    if isinstance(path_or_stream, FileStream):
        return path_or_stream
    else:
        return FileStream(path_or_stream, mode=mode, close_on_exit=close_on_exit)


class Tempfile:
    def __init__(self, contents: bytes, prefix: Optional[str] = None, suffix: Optional[str] = None):
        self._path: Optional[str] = None
        self._data: bytes = contents
        self._prefix: Optional[str] = prefix
        self._suffix: Optional[str] = suffix

    def __enter__(self) -> str:
        tmp = tf.NamedTemporaryFile(prefix=self._prefix, suffix=self._suffix, delete=False)
        tmp.write(self._data)
        tmp.flush()
        tmp.close()
        self._path = tmp.name
        return tmp.name

    def __exit__(self, type, value, traceback):
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
        if self.path == '-':
            self._tempfile: Optional[ExactNamedTempfile] = ExactNamedTempfile(sys.stdin.buffer.read(), "STDIN")
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


class PathOrStdout(ContextManager[TextIO]):
    def __init__(self, path: str):
        self.path: str = path
        if self.path == '-':
            self._tempfile: Optional[TextIO] = sys.stdout
        else:
            self._tempfile = None

    def __enter__(self) -> TextIO:
        if self._tempfile is None:
            self._tempfile = open(self.path, "w")
        return self._tempfile

    def __exit__(self, *args, **kwargs) -> None:  # type: ignore
        if self._tempfile is not None:
            if self._tempfile is not sys.stdout:
                self._tempfile.close()
                self._tempfile = None
        return None


class FileStream(IO):
    def __init__(
            self,
            path_or_stream: Streamable,
            start: int = 0,
            length: Optional[int] = None,
            mode: str = "rb",
            close_on_exit: Optional[bool] = None
    ):
        if isinstance(path_or_stream, Path):
            path_or_stream = str(path_or_stream)
        if isinstance(path_or_stream, str):
            self._stream: IO = open(path_or_stream, mode)
            if close_on_exit is None:
                close_on_exit = True
        else:
            if isinstance(path_or_stream, bytes):
                path_or_stream = BytesIO(path_or_stream)
                setattr(path_or_stream, "name", "bytes")
            elif not path_or_stream.seekable():
                raise ValueError('FileStream can only wrap streams that are seekable')
            elif not path_or_stream.readable():
                raise ValueError('FileStream can only wrap streams that are readable')
            self._stream = path_or_stream
        if isinstance(path_or_stream, FileStream):
            if length is None:
                self._length = len(path_or_stream) - start
            else:
                self._length = min(length, len(path_or_stream))
        else:
            if isinstance(path_or_stream, BytesIO):
                orig_pos = path_or_stream.tell()
                path_or_stream.seek(0, SEEK_END)
                try:
                    filesize = path_or_stream.tell()
                finally:
                    path_or_stream.seek(orig_pos)
            else:
                filesize = os.path.getsize(self._stream.name)
            if length is None:
                self._length = filesize - start
            else:
                self._length = min(filesize, length) - start
        if close_on_exit is None:
            close_on_exit = False
        self._name = self._stream.name
        self.start = start
        self.close_on_exit = close_on_exit
        self._entries = 0
        self._root = None

    def __len__(self):
        return self._length

    def seekable(self):
        return True

    def writable(self):
        return False

    def readable(self):
        return True

    @property
    def name(self):
        return self._name

    @property
    def root(self):
        if self._root is None:
            if isinstance(self._stream, FileStream):
                self._root = self._stream.root
            else:
                self._root = self._stream
        return self._root

    def save_pos(self):
        f = self

        class SP:
            def __init__(self):
                self.pos = f.root.tell()

            def __enter__(self, *args, **kwargs) -> FileStream:
                return f

            def __exit__(self, *args, **kwargs):
                f.root.seek(self.pos)

        return SP()

    def fileno(self):
        return self._stream.fileno()

    def offset(self):
        if isinstance(self._stream, FileStream):
            return self._stream.offset() + self.start
        else:
            return self.start

    def seek(self, offset, from_what=0):
        if from_what == 1:
            offset = self.tell() + offset
        elif from_what == 2:
            offset = len(self) + offset
        if offset - self.start > self._length:
            raise IndexError(f"{self!r} is {len(self)} bytes long, but seek was requested for byte {offset}")
        self._stream.seek(self.start + offset)

    def tell(self):
        return min(max(self._stream.tell() - self.start, 0), self._length)

    def read(self, n=None) -> bytes:
        if self._stream.tell() - self.start < 0:
            # another context moved the position, so move it back to our zero index:
            self.seek(0)
            pos = 0
        else:
            pos = self.tell()
        ls = len(self)
        if pos >= ls:
            return b''
        elif n is None:
            return self._stream.read()[:ls - pos]
        else:
            return self._stream.read(min(n, ls - pos))

    def contains_all(self, *args):
        if args:
            with mmap.mmap(self.fileno(), 0, access=mmap.ACCESS_READ) as filecontent:
                for string in args:
                    if filecontent.find(string, self.offset(), self.offset() + len(self)) < 0:
                        return False
        return True

    def first_index_of(self, byte_sequence: bytes) -> int:
        with mmap.mmap(self.fileno(), 0, access=mmap.ACCESS_READ) as filecontent:
            start_offset = self.offset()
            end_offset = start_offset + len(self)
            index = filecontent.find(byte_sequence, start_offset, end_offset)
            if start_offset <= index < end_offset:
                return index - start_offset
            else:
                return -1

    @property
    def content(self) -> bytes:
        with self.save_pos():
            self.seek(0)
            return self.read(len(self))

    def __bytes__(self):
        return self.content

    def tempfile(self, prefix=None, suffix=None):
        class FSTempfile:
            def __init__(self, file_stream: FileStream):
                self._temp = None
                self._fs: FileStream = file_stream

            def __enter__(self):
                self._temp = tf.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=False)
                with self._fs.save_pos():
                    self._fs.seek(0)
                    while True:
                        b = self._fs.read(1048576)  # write 1 MiB at a time
                        if not b:
                            break
                        self._temp.write(b)
                self._temp.flush()
                self._temp.close()
                return self._temp.name

            def __exit__(self, type, value, traceback):
                if self._temp is not None:
                    os.unlink(self._temp.name)
                    self._temp = None
        return FSTempfile(self)

    def __getitem__(self, index) -> Union[bytes, "FileStream"]:
        if isinstance(index, int):
            with self.save_pos():
                self.seek(index)
                return self.read(1)
        elif not isinstance(index, slice):
            raise ValueError(f"unexpected argument {index}")
        if index.step is not None and index.step != 1:
            raise ValueError(f"Invalid slice step: {index}")
        length=None
        if index.stop is not None:
            if index.stop < 0 and (
                    (index.stop < index.start and index.start > 0) or (index.stop > index.start and index.start < 0)):
                length = len(self) + index.stop - index.start
            elif index.stop < index.start:
                length = 0
            else:
                length = index.stop - index.start
        return FileStream(self, start=index.start, length=length, close_on_exit=False)

    def __enter__(self) -> "FileStream":
        self._entries += 1
        return self

    def __exit__(self, type, value, traceback):
        self._entries -= 1
        assert self._entries >= 0
        if self._entries == 0 and self.close_on_exit:
            self.close_on_exit = False
            self._stream.close()

    def close(self) -> None:
        if self._entries == 0:
            self._stream.close()

    def flush(self):
        self._stream.flush()

    def isatty(self) -> bool:
        return self._stream.isatty()

    def readline(self, limit: int = ...) -> AnyStr:
        raise UnsupportedOperation()

    def readlines(self, hint: int = ...) -> List[AnyStr]:
        raise UnsupportedOperation()

    def truncate(self, size: int = ...) -> int:
        raise UnsupportedOperation()

    def write(self, s: AnyStr) -> int:
        raise UnsupportedOperation()

    def writelines(self, lines: Iterable[AnyStr]) -> None:
        raise UnsupportedOperation()

    def __next__(self) -> AnyStr:
        raise UnsupportedOperation()

    def __iter__(self) -> Iterator[AnyStr]:
        raise UnsupportedOperation()
