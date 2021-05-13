import mmap
import os
from pathlib import Path
import tempfile as tf
import sys
from typing import IO, Optional, Union


def make_stream(path_or_stream, mode='rb', close_on_exit=None):
    if isinstance(path_or_stream, FileStream):
        return path_or_stream
    else:
        return FileStream(path_or_stream, mode=mode, close_on_exit=close_on_exit)


class Tempfile:
    def __init__(self, contents, prefix=None, suffix=None):
        self._temp = None
        self._data = contents
        self._prefix = prefix
        self._suffix = suffix

    def __enter__(self):
        self._temp = tf.NamedTemporaryFile(prefix=self._prefix, suffix=self._suffix, delete=False)
        self._temp.write(self._data)
        self._temp.flush()
        self._temp.close()
        return self._temp.name

    def __exit__(self, type, value, traceback):
        if self._temp is not None:
            os.unlink(self._temp.name)
            self._temp = None


class PathOrStdin:
    def __init__(self, path):
        self._path = path
        if self._path == '-':
            self._tempfile = Tempfile(sys.stdin.buffer.read())
        else:
            self._tempfile = None

    def __enter__(self):
        if self._tempfile is None:
            return self._path
        else:
            return self._tempfile.__enter__()

    def __exit__(self, *args, **kwargs):
        if self._tempfile is not None:
            return self._tempfile.__exit__(*args, **kwargs)


class FileStream:
    def __init__(
            self,
            path_or_stream: Union[str, Path, IO, "FileStream"],
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
            if not path_or_stream.seekable():
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
        self._listeners = []
        self._root = None

    def __len__(self):
        return self._length

    def add_listener(self, listener):
        self._listeners.append(listener)

    def remove_listener(self, listener):
        ret = False
        for i in reversed(range(len(self._listeners))):
            if self._listeners[i] == listener:
                del self._listeners[i]
                ret = True
        return ret

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

            def __enter__(self, *args, **kwargs):
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

    def read(self, n=None, update_listeners=True):
        if self._stream.tell() - self.start < 0:
            # another context moved the position, so move it back to our zero index:
            self.seek(0)
            pos = 0
        else:
            pos = self.tell()
        if update_listeners:
            for listener in self._listeners:
                listener(self, pos)
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

    @property
    def content(self) -> bytes:
        with self.save_pos():
            self.seek(0)
            return self.read(len(self))

    def tempfile(self, prefix=None, suffix=None):
        class FSTempfile:
            def __init__(self, file_stream: FileStream):
                self._temp = None
                self._fs: FileStream = file_stream

            def __enter__(self):
                self._temp = tf.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=False)
                self._temp.write(self._fs.content)
                self._temp.flush()
                self._temp.close()
                return self._temp.name

            def __exit__(self, type, value, traceback):
                if self._temp is not None:
                    os.unlink(self._temp.name)
                    self._temp = None
        return FSTempfile(self)

    def __getitem__(self, index):
        if isinstance(index, int):
            self.seek(index)
            return self.read(1)
        elif not isinstance(index, slice):
            raise ValueError(f"unexpected argument {index}")
        if index.step is not None and index.step != 1:
            raise ValueError(f"Invalid slice step: {index}")
        length=None
        if index.stop is not None:
            if index.stop < 0:
                length = len(self) + index.stop - index.start
            else:
                length = len(self) - (index.stop - index.start)
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
