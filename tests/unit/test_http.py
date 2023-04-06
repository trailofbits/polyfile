from unittest import TestCase
from polyfile.http import Grammar, HttpVisitor
from abnf.parser import Node


class HttpUnitTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        # from https://portswigger.net/web-security/request-smuggling
        self.test_requests = [
            """POST /search HTTP/1.1\r\nHost: normal-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 11\r\n\r\nq=smuggling""",
            """POST /search HTTP/1.1
Host: normal-website.com
Content-Type: application/x-www-form-urlencoded
Transfer-Encoding: chunked

b
q=smuggling
0""",
            """POST / HTTP/1.1
Host: vulnerable-website.com
Content-Length: 13
Transfer-Encoding: chunked

0

SMUGGLED""",
            """POST / HTTP/1.1
Host: vulnerable-website.com
Content-Length: 3
Transfer-Encoding: chunked

8
SMUGGLED
0""",
        ]

    def test_headers(self):
        ast, offset = Grammar("request").parse(self.test_requests[0], 0)
        visitor: HttpVisitor = HttpVisitor()
        visitor.visit(ast)

        print(offset)
        print(ast)
        print(f"t_codings: {visitor.t_codings}")
        print(f"contnet_length: {visitor.content_length}")
        print(f"uri_host: {visitor.uri_host}")
        print(f"uri_port: {visitor.uri_port}")

        assert visitor.t_codings == "chunked"
        assert visitor.content_length == 13
        assert visitor.uri_host == "vulnerable-website.com"
        assert visitor.uri_port is None
