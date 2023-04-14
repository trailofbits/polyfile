from unittest import TestCase
from polyfile.http_11 import *
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

    def test_post_body_form_encoded(self):
        request = """POST /search HTTP/1.1\r\nHost: normal-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 11\r\n\r\nq=smuggling"""
        ast, offset = Http11RequestGrammar("request").parse(request, 0)
        visitor: HttpVisitor = HttpVisitor()
        visitor.visit(ast)

        assert visitor.method == HttpMethod.POST
        assert visitor.request_target == "/search"
        assert visitor.content_type == "application/x-www-form-urlencoded"
        assert visitor.content_length == 11
        assert "q=smuggling" in visitor.body
        assert len(visitor.body) == visitor.content_length

    def test_post_body_chunked(self):
        request = """POST /search HTTP/1.1\r\nHost: normal-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nTransfer-Encoding: chunked\r\n\r\nb\nq=smuggling\n0"""
        ast, offset = Http11RequestGrammar("request").parse(request, 0)
        visitor: HttpVisitor = HttpVisitor()
        visitor.visit(ast)

        assert visitor.method == HttpMethod.POST
        assert visitor.request_target == "/search"
        assert visitor.content_type == "application/x-www-form-urlencoded"
        assert visitor.transfer_encoding == "chunked"
        assert "b" in visitor.body  # chunk content length
        assert "0" in visitor.body  # 0 chunk terminates
