"""HTTP AST offsets remain relative to the analysis source through stream wrappers."""

import pytest

from polyfile.fileutils import FileStream
from polyfile.http.matcher import HTTP_11_MIME_TYPE, parse_http_11
from polyfile.polyfile import Match, Matcher

REQUEST = b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"

UTF8_REQUESTS = (
    b"GET / HTTP/1.1\r\nUser-Agent: tool (\xc3\xa9)\r\nHost: example.com\r\n\r\n",
    b"POST / HTTP/1.1\r\nHost: example.com\r\nContent-Length: 4\r\n\r\n\xc3\xa9zz",
)


@pytest.mark.parametrize("backing_base", [0, 37])
@pytest.mark.parametrize("source_base", [0, 117])
@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("source", ["file", "decoded:0"])
def test_http_matches_preserve_source_coordinates(
    backing_base: int, source_base: int, nested: bool, source: str
) -> None:
    stream = FileStream(b"x" * backing_base + REQUEST, start=backing_base, length=len(REQUEST))
    if nested:
        stream = FileStream(stream)
    parent = Match(
        HTTP_11_MIME_TYPE,
        None,
        relative_offset=source_base,
        length=len(REQUEST),
        matcher=Matcher(parse=False),
        source=source,
    )
    with stream:
        nodes = list(parse_http_11(stream, parent))
    assert nodes[0].offset == source_base
    assert nodes[0].length == len(REQUEST)
    for node in nodes:
        assert node.source == source
        end = parent.offset + parent.length
        assert source_base <= node.offset <= node.offset + node.length <= end
        if isinstance(node.match, bytes):
            local = node.offset - source_base
            assert REQUEST[local : local + node.length] == node.match


@pytest.mark.parametrize("request_data", UTF8_REQUESTS)
@pytest.mark.parametrize("backing_base", [0, 37])
@pytest.mark.parametrize("source_base", [0, 117])
@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("source", ["file", "decoded:0"])
def test_utf8_http_nodes_map_to_their_original_bytes(
    request_data: bytes, backing_base: int, source_base: int, nested: bool, source: str
) -> None:
    stream = FileStream(
        b"x" * backing_base + request_data, start=backing_base, length=len(request_data)
    )
    if nested:
        stream = FileStream(stream)
    parent = Match(
        HTTP_11_MIME_TYPE,
        None,
        relative_offset=source_base,
        length=len(request_data),
        matcher=Matcher(parse=False),
        source=source,
    )
    with stream:
        nodes = list(parse_http_11(stream, parent))
    assert nodes[0].offset == source_base
    assert nodes[0].length == len(request_data)
    for node in nodes:
        assert node.source == source
        local = node.offset - source_base
        assert 0 <= local <= local + node.length <= len(request_data)
        if isinstance(node.match, bytes):
            assert request_data[local : local + node.length] == node.match


@pytest.mark.parametrize("prefix", [b"skip", "é".encode(), "€".encode(), "😀".encode()])
@pytest.mark.parametrize("source", ["file", "decoded:0"])
def test_http_start_cursor_counts_bytes_after_a_utf8_prefix(prefix: bytes, source: str) -> None:
    data = prefix + UTF8_REQUESTS[0]
    stream = FileStream(FileStream(b"x" * 37 + data, start=37, length=len(data)))
    parent = Match(
        HTTP_11_MIME_TYPE,
        None,
        relative_offset=117,
        length=len(data),
        matcher=Matcher(parse=False),
        source=source,
    )
    with stream:
        stream.seek(len(prefix))
        nodes = list(parse_http_11(stream, parent))
        assert stream.tell() == len(data)
    assert nodes[0].offset == parent.offset + len(prefix)
    assert nodes[0].length == len(UTF8_REQUESTS[0])
    for node in nodes:
        assert node.source == source
        local = node.offset - parent.offset
        if isinstance(node.match, bytes):
            assert data[local : local + node.length] == node.match


@pytest.mark.parametrize("invalid", [b"\xff", b"\xc3", b"\xc3("])
@pytest.mark.parametrize("before_request", [False, True])
def test_http_preserves_strict_utf8_decoding(invalid: bytes, before_request: bool) -> None:
    data = invalid + REQUEST if before_request else REQUEST + invalid
    parent = Match(HTTP_11_MIME_TYPE, None, length=len(data), matcher=Matcher(parse=False))
    with FileStream(data) as stream:
        with pytest.raises(UnicodeDecodeError):
            list(parse_http_11(stream, parent))


def test_http_start_cursor_must_be_at_a_utf8_character_boundary() -> None:
    data = b"\xc3\xa9" + REQUEST
    parent = Match(HTTP_11_MIME_TYPE, None, length=len(data), matcher=Matcher(parse=False))
    with FileStream(data) as stream:
        stream.seek(1)
        with pytest.raises(UnicodeDecodeError):
            list(parse_http_11(stream, parent))
