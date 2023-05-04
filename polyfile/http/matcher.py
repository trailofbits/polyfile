from pathlib import Path

from ..ast import Node as ASTNode
from ..fileutils import ExactNamedTempfile, FileStream
from ..magic import MagicMatcher
from ..polyfile import register_parser, Match


Http11RequestGrammar = None

HTTP_MIME_TYPE: str = "message/x-http"
HTTP_11_MIME_TYPE: str = f"{HTTP_MIME_TYPE}; version=1.1"


# Register a magic matcher for HTTP 1.1 headers:
with ExactNamedTempfile(b"""0 regex/s [^\\\\n]*?\\\\s+HTTP/1.1\\\\s*$ HTTP 1.1
!:mime """ + HTTP_11_MIME_TYPE.encode("utf-8") + b"""
>0 string GET GET request header
>0 string POST POST request header
>0 string PUT PUT request header
""", name="HTTP1.1Matcher") as t:
    http_11_matcher = MagicMatcher.DEFAULT_INSTANCE.add(Path(t))[0]


@register_parser(HTTP_11_MIME_TYPE)
def parse_http_11(file_stream: FileStream, parent: Match):
    offset = file_stream.tell()
    file_stream.seek(0)
    global Http11RequestGrammar
    if Http11RequestGrammar is None:
        # the http_11 module takes a _really_ long time to load/parse the grammar, so do this lazily

        from .http_11 import Http11RequestGrammar as Grammar
        Http11RequestGrammar = Grammar
    http_ast, _ = Http11RequestGrammar("request").parse(file_stream.read().decode("utf-8"), start=offset)
    root_node = ASTNode.load(http_ast)
    yield from root_node.to_matches(parent)
