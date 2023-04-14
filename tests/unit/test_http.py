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

    def test_post_body_variant_one(self):
        request = """POST /search HTTP/1.1\r\nHost: normal-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 11\r\n\r\nq=smuggling"""
        ast, offset = Http11RequestGrammar("request").parse(request, 0)
        visitor: HttpVisitor = HttpVisitor()
        visitor.visit(ast)
        # print(ast)

        assert visitor.method == HttpMethod.POST
        assert visitor.request_path == "/search"
        assert visitor.protocol == "HTTP/1.1"
        assert visitor.content_type == "application/x-www-form-urlencoded"
        assert visitor.content_length == 11
        assert "q=smuggling" in visitor.body
        assert len(visitor.body) == visitor.content_length
