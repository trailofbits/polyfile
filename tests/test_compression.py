"""Behavioral tests for shared compressed-content output handling."""

import pytest

from polyfile.compression import DecodeError, OutputBuffer
from polyfile.polyfile import Match, Matcher, Submatch


def test_output_is_unlimited_by_default():
    output = OutputBuffer()
    output.append(b"first")
    output.append(b"second")
    assert output.remaining is None
    assert output.finish() == b"firstsecond"


def test_output_limit_accepts_the_boundary_and_rejects_one_more_byte():
    output = OutputBuffer(5)
    output.append(b"first")
    assert output.remaining == 0
    assert output.next_size == 1
    with pytest.raises(DecodeError, match="5-byte") as error:
        output.append(b"x")
    assert error.value.status == "limited"
    assert output.finish() == b"first"


def test_a_zero_limit_accepts_empty_output():
    output = OutputBuffer(0)
    output.append(b"")
    assert output.finish() == b""


def test_offsets_stop_at_a_source_boundary():
    physical = Match("wrapper", None, relative_offset=100, length=10, matcher=Matcher())
    decoded = Submatch(
        "decoded_content", None, length=20, parent=physical, source="decoded:0"
    )
    child = Submatch("field", None, relative_offset=3, length=2, parent=decoded)
    assert (physical.offset, decoded.offset, child.offset) == (100, 0, 3)
    assert child.source == "decoded:0"
    assert child.root_offset == 3
    assert child.to_obj()["source"] == "decoded:0"


def test_a_decoded_child_does_not_change_a_physical_extent():
    physical = Match("wrapper", None, relative_offset=100, matcher=Matcher())
    Submatch("physical", None, length=10, parent=physical)
    Submatch("decoded_content", None, length=1000, parent=physical, source="decoded:0")
    assert physical.length == 10


def test_failed_concatenation_consumes_shared_frame_budget() -> None:
    import gzip

    from polyfile.analysis import AnalysisLimits
    from polyfile.compression import parse_compressed
    from polyfile.fileutils import FileStream
    from polyfile.gzipmatcher import decode_gzip

    matcher = Matcher(limits=AnalysisLimits(max_members=2))
    first = Match("application/gzip", None, matcher=matcher)
    data = gzip.compress(b"first", mtime=0) + gzip.compress(b"second", mtime=0)[:-2]
    with FileStream(data) as stream:
        list(parse_compressed(stream, first, decode_gzip))
    assert first.analysis_status == "invalid"
    assert first.analysis_context.members == 2

    second = Match(
        "application/gzip",
        None,
        matcher=matcher,
        analysis_context=first.analysis_context,
    )

    def unexpected_decode(*args, **kwargs):
        raise AssertionError("Exhausted shared frame budget still invoked a decoder")

    with FileStream(gzip.compress(b"third", mtime=0)) as stream:
        list(parse_compressed(stream, second, unexpected_decode))
    assert second.analysis_status == "limited"
    assert first.analysis_context.members == 2
