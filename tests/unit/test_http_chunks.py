"""Chunk decoding retains available bytes from complete and partial HTTP bodies."""

import pytest

from polyfile.http.http_11 import Http11RequestGrammar, HttpVisitor


def visit_body(body: str, trailer: str = "") -> HttpVisitor:
    """Parse a chunked request through its grammar and visitor."""
    headers = "POST / HTTP/1.1\r\nHost: example.com\r\nTransfer-Encoding: chunked\r\n"
    if trailer:
        headers += f"Trailer: {trailer}\r\n"
    request = headers + "\r\n" + body
    tree, _ = Http11RequestGrammar("request").parse(request, 0)
    visitor = HttpVisitor()
    visitor.visit(tree)
    return visitor


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("", ""),
        ("10\r\nABCDEFGHIJKLMNOP\r\n0\r\n\r\n", "ABCDEFGHIJKLMNOP"),
        ("0a\r\nabcdefghij\r\n0\r\n\r\n", "abcdefghij"),
        ("1;foo=bar\r\nA\r\n0\r\n\r\n", "A"),
        ('1;foo="bar;baz"\r\nA\r\n0\r\n\r\n', "A"),
        ("2\r\nAB\r\n3\r\nCDE\r\n0\r\n\r\n", "ABCDE"),
        ("2\r\nA", "A"),
        ("2\r\nAB", "AB"),
        ("1\r\nA\r\nX", "A"),
        ("1\r\nA\r\nz\r\n", "A"),
        ("a", ""),
        ("2\r", ""),
        ("-1\r\nA\r\n0\r\n\r\n", ""),
        ("0\r\n\r\nignored", ""),
    ],
)
def test_chunked_body_counts_available_decoded_bytes(body: str, expected: str) -> None:
    visitor = visit_body(body)
    assert visitor.body_parsed is not None
    assert visitor.headers is not None
    assert "".join(visitor.body_parsed) == expected
    assert visitor.content_length == len(expected)
    assert visitor.body_raw == body
    assert "Transfer-Encoding" not in visitor.headers


def test_multiple_chunks_count_each_byte_once() -> None:
    visitor = visit_body("1\r\nA\r\n" * 100 + "0\r\n\r\n")
    assert visitor.body_parsed is not None
    assert "".join(visitor.body_parsed) == "A" * 100
    assert visitor.content_length == 100


def test_incomplete_trailer_keeps_decoded_body_and_ignores_incomplete_field() -> None:
    body = "1\r\nA\r\n0\r\nBroken\r\nExpires: tomorrow\r\n\r\n"
    visitor = visit_body(body, "Expires")
    assert visitor.body_parsed is not None
    assert visitor.headers is not None
    assert "".join(visitor.body_parsed) == "A"
    assert visitor.content_length == 1
    assert visitor.headers["Expires"] == "tomorrow"


@pytest.mark.parametrize("initial_trailer", ["", "Expires: legitimate\r\n"])
@pytest.mark.parametrize(
    "following_data",
    [
        "Expires: attack\r\n",
        "\r\nExpires: attack\r\n",
        "GET /next HTTP/1.1\r\nHost: next.example\r\nExpires: attack\r\n\r\n",
    ],
)
def test_trailers_stop_at_the_first_empty_line(initial_trailer: str, following_data: str) -> None:
    body = "1\r\nA\r\n0\r\n" + initial_trailer + "\r\n" + following_data
    visitor = visit_body(body, "Expires")
    assert visitor.body_parsed is not None
    assert visitor.headers is not None
    assert "".join(visitor.body_parsed) == "A"
    assert visitor.content_length == 1
    assert visitor.body_raw == body
    assert visitor.headers["Host"] == "example.com"
    assert "Transfer-Encoding" not in visitor.headers
    if initial_trailer:
        assert visitor.headers["Expires"] == "legitimate"
    else:
        assert "Expires" not in visitor.headers
        assert not hasattr(visitor, "expires")


def test_trailer_boundary_preserves_declared_and_forbidden_fields() -> None:
    body = (
        "1\r\nA\r\n0\r\nHost: attacker.example\r\nContent-Length: 999\r\n"
        "Expires: tomorrow\r\nIgnored: undeclared\r\n\r\nExpires: attack\r\n"
    )
    visitor = visit_body(body, "Host,Content-Length,Expires")
    assert visitor.body_parsed is not None
    assert visitor.headers is not None
    assert "".join(visitor.body_parsed) == "A"
    assert visitor.content_length == 1
    assert visitor.headers["Host"] == "example.com"
    assert visitor.headers["Expires"] == "tomorrow"
    assert "Content-Length" not in visitor.headers
    assert "Ignored" not in visitor.headers
