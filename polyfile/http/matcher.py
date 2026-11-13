from pathlib import Path

from polyfile.ast import Node as ASTNode
from polyfile.fileutils import ExactNamedTempfile, FileStream
from polyfile.magic import MagicMatcher
from polyfile.polyfile import register_parser, Match


Http11RequestGrammar = None

HTTP_MIME_TYPE: str = "message/x-http"
HTTP_11_MIME_TYPE: str = f"{HTTP_MIME_TYPE}; version=1.1"


# Register a magic matcher for a line ending in the HTTP/1.1 token.
with ExactNamedTempfile(b"""0 regex/s \\^[^\\n]*[[:space:]]+HTTP/1.1[[:space:]]*$ HTTP 1.1
!:mime """ + HTTP_11_MIME_TYPE.encode("utf-8") + b"""
>0 string GET GET request header
>0 string POST POST request header
>0 string PUT PUT request header
""", name="HTTP1.1Matcher") as t:
    http_11_matcher = MagicMatcher.DEFAULT_INSTANCE.add(Path(t))[0]


def _use_byte_offsets(root: ASTNode, text: str) -> None:
    """Translate ABNF literal positions before the AST infers container positions.

    ABNF records character offsets only on literal nodes. Their containers infer offsets
    from children or older siblings, so convert the explicit offsets before evaluating any
    inferred positions. UTF-8 values and lengths are already preserved by ASTNode.load().
    """
    byte_offsets = [0]
    for character in text:
        byte_offsets.append(byte_offsets[-1] + len(character.encode("utf-8")))
    stack = [root]
    while stack:
        node = stack.pop()
        if node._offset is not None:
            node._offset = byte_offsets[node._offset]
        stack.extend(node.children)


@register_parser(HTTP_11_MIME_TYPE)
def parse_http_11(file_stream: FileStream, parent: Match):
    offset = file_stream.tell()
    file_stream.seek(0)
    global Http11RequestGrammar
    if Http11RequestGrammar is None:
        # the http_11 module takes a _really_ long time to load/parse the grammar, so do this lazily

        from polyfile.http.http_11 import Http11RequestGrammar as Grammar
        Http11RequestGrammar = Grammar
    text = file_stream.read().decode("utf-8")
    http_ast, _ = Http11RequestGrammar("request").parse(text, start=offset)
    root_node = ASTNode.load(http_ast)
    _use_byte_offsets(root_node, text)
    yield from root_node.to_matches(parent)
