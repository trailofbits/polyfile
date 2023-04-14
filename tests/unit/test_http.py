from unittest import TestCase
from polyfile.http_11 import *
from abnf.parser import Node


class HttpUnitTests(TestCase):
    # Test requests are from https://portswigger.net/web-security/request-smuggling

    def setUp(self) -> None:
        super().setUp()

    def build_and_visit_ast(self, request: str) -> HttpVisitor:
        """Parse the incoming string and apply an HttpVisitor to it."""
        ast, offset = Http11RequestGrammar("request").parse(request, 0)
        visitor: HttpVisitor = HttpVisitor()
        visitor.visit(ast)
        return visitor

    def test_post_body_form_encoded(self):
        """Most HTTP request smuggling vulnerabilities arise because the HTTP specification provides two different ways to specify where a request ends: the Content-Length header and the Transfer-Encoding header.

        The Content-Length header is straightforward: it specifies the length of the message body in bytes. For example:
        """

        request = """POST /search HTTP/1.1\r\nHost: normal-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 11\r\n\r\nq=smuggling"""
        visitor = self.build_and_visit_ast(request)

        assert visitor.method == HttpMethod.POST
        assert visitor.request_target == "/search"
        assert visitor.content_type == "application/x-www-form-urlencoded"
        assert visitor.content_length == 11
        assert "q=smuggling" in visitor.body
        assert len(visitor.body) == visitor.content_length

    def test_post_body_chunked(self):
        """The Transfer-Encoding header can be used to specify that the message body uses chunked encoding. This means that the message body contains one or more chunks of data. Each chunk consists of the chunk size in bytes (expressed in hexadecimal), followed by a newline, followed by the chunk contents. The message is terminated with a chunk of size zero. For example:"""

        request = """POST /search HTTP/1.1\r\nHost: normal-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nTransfer-Encoding: chunked\r\n\r\nb\nq=smuggling\n0"""
        visitor = self.build_and_visit_ast(request)

        assert visitor.method == HttpMethod.POST
        assert visitor.request_target == "/search"
        assert visitor.content_type == "application/x-www-form-urlencoded"
        assert visitor.transfer_encoding == "chunked"
        assert "b" in visitor.body  # chunk content length
        assert visitor.content_length == None
        assert "0" in visitor.body  # 0 chunk terminates

    def test_post_body_chunked_with_smuggling_cl_te(self):
        """Here, the front-end server uses the Content-Length header and the back-end server uses the Transfer-Encoding header. We can perform a simple HTTP request smuggling attack as follows. The front-end server processes the Content-Length header and determines that the request body is 13 bytes long, up to the end of SMUGGLED. This request is forwarded on to the back-end server.

        The back-end server processes the Transfer-Encoding header, and so treats the message body as using chunked encoding. It processes the first chunk, which is stated to be zero length, and so is treated as terminating the request. The following bytes, SMUGGLED, are left unprocessed, and the back-end server will treat these as being the start of the next request in the sequence.
        """

        request = """POST / HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Length: 13\r\nTransfer-Encoding: chunked\r\n\r\n0\nSMUGGLED"""
        visitor = self.build_and_visit_ast(request)

        assert visitor.method == HttpMethod.POST
        assert visitor.content_length == 13
        assert visitor.content_type == None
        assert visitor.transfer_encoding == "chunked"
        assert "SMUGGLED" in visitor.body
