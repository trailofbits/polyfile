import mmap
import os


def make_stream(path_or_stream, mode='rb', close_on_exit=None):
    if isinstance(path_or_stream, FileStream):
        return path_or_stream
    else:
        return FileStream(path_or_stream, mode=mode, close_on_exit=close_on_exit)


class FileStream:
    def __init__(self, path_or_stream, start=0, length=None, mode='rb', close_on_exit=None):
        if isinstance(path_or_stream, str):
            self._stream = open(path_or_stream, mode)
            if close_on_exit is None:
                close_on_exit = True
        else:
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
        self.start = start
        self.close_on_exit = close_on_exit
        self._name = self._stream.name
        self._entries = 0

    def __len__(self):
        return self._length

    @property
    def name(self):
        return self._name

    def fileno(self):
        return self._stream.fileno()

    def offset(self):
        if isinstance(self._stream, FileStream):
            return self._stream.offset() + self.start
        else:
            return self.start

    def seek(self, offset):
        if offset - self.start + 1 > self._length:
            raise IndexError(f"{self!r} is {len(self)} bytes long, but seek was requested for byte {offset}")
        self._stream.seek(self.start + offset)

    def read(self, n):
        return self._stream.read(n)

    def contains_all(self, *args):
        if args:
            with mmap.mmap(self.fileno(), 0, access=mmap.ACCESS_READ) as filecontent:
                for string in args:
                    if filecontent.find(string, self.offset(), self.offset() + len(self)) < 0:
                        return False
        return True

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

    def __enter__(self):
        self._entries += 1
        return self

    def __exit__(self, type, value, traceback):
        self._entries -= 1
        assert self._entries >= 0
        if self._entries == 0 and self.close_on_exit:
            self.close_on_exit = False
            self._stream.close()
