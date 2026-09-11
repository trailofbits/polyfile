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
