from collections.abc import Iterator
from pathlib import Path

from polyfile.ast import Node as ASTNode
from polyfile.fileutils import ExactNamedTempfile, FileStream
from polyfile.magic import MagicMatcher
from polyfile.polyfile import register_parser, Match, Submatch


Http11RequestGrammar = None

HTTP_MIME_TYPE: str = "message/x-http"
HTTP_11_MIME_TYPE: str = f"{HTTP_MIME_TYPE}; version=1.1"


# Register a magic matcher for a line ending in the HTTP/1.1 token.
with ExactNamedTempfile(b"""0 regex/stb \\^[^\\n]*[[:space:]]+HTTP/1[.]1[[:space:]]*$ HTTP 1.1
!:mime """ + HTTP_11_MIME_TYPE.encode("utf-8") + b"""
>0 string GET GET request header
>0 string POST POST request header
>0 string PUT PUT request header
""", name="HTTP1.1Matcher") as t:
    http_11_matcher = MagicMatcher.DEFAULT_INSTANCE.add(Path(t))[0]


@register_parser(HTTP_11_MIME_TYPE)
def parse_http_11(file_stream: FileStream, parent: Match) -> Iterator[Submatch]:
    """Map one HTTP request's UTF-8 headers and binary body into its analysis source.

    Args:
        file_stream: A bounded view whose current byte cursor identifies the request start.
            Parsing reads the complete view and leaves the shared cursor at its EOF.
        parent: The match whose analysis-source position identifies view byte zero. Its source
            can be physical or decoded, independently of the backing buffer's byte origin.

    Yields:
        HTTP nodes whose offsets and lengths select their original encoded bytes.

    Raises:
        UnicodeDecodeError: If the prefix or headers contain invalid UTF-8.
    """
    offset = file_stream.tell()
    file_stream.seek(0)
    global Http11RequestGrammar
    if Http11RequestGrammar is None:
        # the http_11 module takes a _really_ long time to load/parse the grammar, so do this lazily

        from polyfile.http.http_11 import Http11RequestGrammar as Grammar
        Http11RequestGrammar = Grammar
    data = file_stream.read()
    header_end = data.find(b"\r\n\r\n", offset)
    data[:offset].decode("utf-8")
    data[offset:header_end if header_end >= 0 else None].decode("utf-8")
    # ABNF accepts text. Latin-1 maps every octet to a single character and back.
    http_ast, _ = Http11RequestGrammar("request").parse(data.decode("latin-1"), start=offset)
    root_node = ASTNode.load(http_ast, encoding="latin-1")
    yield from root_node.to_matches(parent)
