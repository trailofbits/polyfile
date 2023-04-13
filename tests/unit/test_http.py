from unittest import TestCase
from polyfile.http_11 import Http11RequestGrammar, HttpVisitor
from abnf.parser import Node


class HttpUnitTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        # from https://portswigger.net/web-security/request-smuggling
        self.test_requests = [
            """POST /search HTTP/1.1\r\nHost: normal-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nTransfer-Encoding: chunked\r\n\r\nb\r\nq=smuggling\r\n0""",
            """POST / HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Length: 13\r\nTransfer-Encoding: chunked\r\n\r\n0\r\nSMUGGLED""",
            """POST / HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Length: 3\r\nTransfer-Encoding: chunked\r\n\r\n8\r\nSMUGGLED\r\n0""",
        ]

    def test_headers(self):
        request = """POST /search HTTP/1.1\r\nHost: normal-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 11\r\n\r\nq=smuggling"""
        ast, offset = Http11RequestGrammar("request").parse(request, 0)
        visitor: HttpVisitor = HttpVisitor()
        visitor.visit(ast)
        print(ast)

        assert visitor.t_codings == "chunked"
        assert visitor.content_length == 11
        assert visitor.uri_host == "vulnerable-website.com"
        assert visitor.uri_port is None
