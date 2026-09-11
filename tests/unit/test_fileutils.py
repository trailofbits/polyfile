from io import BytesIO
from unittest import TestCase

from polyfile.fileutils import FileStream

DATA = b"0123456789"


class TestFileStreamStart(TestCase):
    """Regression tests for the stream positioning half of #3463.

    `FileStream` wraps a stream it is handed rather than reopening it, so it inherits whatever
    position that stream is already at. Callers pass `start` to slice a region out of a larger
    file and then read from the beginning of the slice, which only works if construction moves
    the stream to `start`.
    """

    def stream_at_end(self) -> BytesIO:
        stream = BytesIO(DATA)
        setattr(stream, "name", "bytes")
        stream.seek(0, 2)
        return stream

    def test_read_from_start_of_slice(self):
        with FileStream(self.stream_at_end(), start=4) as f:
            self.assertEqual(b"456789", f.read())

    def test_read_whole_stream_that_is_at_its_end(self):
        with FileStream(self.stream_at_end()) as f:
            self.assertEqual(DATA, f.read())

    def test_nested_slice_reads_from_its_start(self):
        with FileStream(self.stream_at_end()) as outer:
            outer.read()
            with FileStream(outer, start=2, length=4) as inner:
                self.assertEqual(b"2345", inner.read())


class TestFileStreamLength(TestCase):
    """Regression tests for the two readings of `length` in `FileStream.__init__`.

    The branch for a nested `FileStream` read `length` as a count of bytes from `start`, while
    the branch for a raw stream or a path read it as an offset from the beginning of the
    underlying stream and then subtracted `start` from it. The two therefore disagreed about
    every slice taken at a non-zero `start`, and the second could return a negative length,
    which made `__len__` raise `ValueError: __len__() should return >= 0` on the first read.
    """

    def raw(self, start: int = 0, length=None) -> FileStream:
        stream = BytesIO(DATA)
        setattr(stream, "name", "bytes")
        return FileStream(stream, start=start, length=length)

    def nested(self, start: int = 0, length=None) -> FileStream:
        outer = BytesIO(DATA)
        setattr(outer, "name", "bytes")
        return FileStream(FileStream(outer), start=start, length=length)

    def test_length_counts_bytes_from_start(self):
        for start, length, expected in ((4, 3, b"456"), (0, 3, b"012"), (8, 5, b"89"),
                                        (4, None, b"456789")):
            with self.subTest(start=start, length=length):
                self.assertEqual(expected, self.raw(start, length).read())
                self.assertEqual(expected, self.nested(start, length).read())

    def test_both_branches_agree(self):
        for start in range(len(DATA) + 1):
            for length in (None, 0, 1, 4, len(DATA), len(DATA) * 2):
                with self.subTest(start=start, length=length):
                    raw = self.raw(start, length)
                    nested = self.nested(start, length)
                    self.assertEqual(len(raw), len(nested))
                    self.assertEqual(raw.read(), nested.read())

    def test_length_is_never_negative(self):
        for start, length in ((4, 3), (len(DATA) + 5, None), (len(DATA) + 5, 2)):
            with self.subTest(start=start, length=length):
                stream = self.raw(start, length)
                self.assertLessEqual(0, len(stream))
                self.assertEqual(len(stream), len(stream.read()))
