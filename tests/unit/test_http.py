from unittest import TestCase
from polyfile.http import Grammar, HttpVisitor
from abnf.parser import Node


class HttpUnitTests(TestCase):
    def setUp(self) -> None:
        super().setUp()

    def test_cl_te(self):
        cl_te = """POST / HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Length: 13\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\nSMUGGLED"""

        header_ast: Node = Grammar("headers").parse_all(cl_te)
        visitor: HttpVisitor = HttpVisitor()
        visitor.visit(header_ast)

        assert visitor.t_codings == "chunked"
        assert visitor.content_length == 13
        assert visitor.uri_host == "vulnerable-website.com"
