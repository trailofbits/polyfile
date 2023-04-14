from unittest import TestCase
from polyfile.http_11 import *
from abnf.parser import ParseError


class Http11RequestUnitTests(TestCase):
    """Test that the HTTP 1.1 Request grammar does what it says on the tin.

    Test requests are from https://portswigger.net/web-security/request-smuggling and https://portswigger.net/web-security/request-smuggling/finding.
    """

    grammar: Http11RequestGrammar = Http11RequestGrammar("request")

    def setUp(self) -> None:
        super().setUp()

    def build_and_visit_ast(self, request: str) -> HttpVisitor:
        """Parse the incoming string and apply an HttpVisitor to it."""
        ast, offset = self.grammar.parse(request, 0)
        visitor: HttpVisitor = HttpVisitor()
        visitor.visit(ast)
        return visitor

    def test_post_body_form_encoded(self):
        """Most HTTP request smuggling vulnerabilities arise because the HTTP specification provides two different ways to specify where a request ends: the Content-Length header and the Transfer-Encoding header.

        The Content-Length header is straightforward: it specifies the length of the message body in bytes. For example:
        """

        request = """POST /search HTTP/1.1\r\nHost: normal-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 11\r\n\r\nq=smuggling"""
        visitor = self.build_and_visit_ast(request)

        self.assertEqual(visitor.method, HttpMethod.POST)
        self.assertEqual(visitor.request_target, "/search")
        self.assertEqual(visitor.content_type, "application/x-www-form-urlencoded")
        self.assertEqual(visitor.content_length, 11)
        self.assertIn(member="q=smuggling", container=visitor.body_raw)
        self.assertEqual(len(visitor.body_raw), visitor.content_length)

    def test_post_body_chunked(self):
        """The Transfer-Encoding header can be used to specify that the message body uses chunked encoding. This means that the message body contains one or more chunks of data. Each chunk consists of the chunk size in bytes (expressed in hexadecimal), followed by a newline, followed by the chunk contents. The message is terminated with a chunk of size zero. For example:"""

        request = """POST /search HTTP/1.1\r\nHost: normal-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nTransfer-Encoding: chunked\r\n\r\nb\r\nq=smuggling\r\n0"""
        visitor = self.build_and_visit_ast(request)

        self.assertEqual(visitor.method, HttpMethod.POST)
        self.assertEqual(visitor.request_target, "/search")
        self.assertEqual(visitor.content_type, "application/x-www-form-urlencoded")
        self.assertEqual(visitor.transfer_encoding, "chunked")

        # chunk content length
        self.assertIn(member="b", container=visitor.body_raw)
        # chunk terminates with 0
        self.assertIn(member="0", container=visitor.body_raw)
        # no Content-Length header, so member should be None
        self.assertIsNone(visitor.content_length)

    def test_post_body_chunked_with_smuggling_cl_te(self):
        """Here, the front-end server uses the Content-Length header and the back-end server uses the Transfer-Encoding header. We can perform a simple HTTP request smuggling attack as follows. The front-end server processes the Content-Length header and determines that the request body is 13 bytes long, up to the end of SMUGGLED. This request is forwarded on to the back-end server.

        The back-end server processes the Transfer-Encoding header, and so treats the message body as using chunked encoding. It processes the first chunk, which is stated to be zero length, and so is treated as terminating the request. The following bytes, SMUGGLED, are left unprocessed, and the back-end server will treat these as being the start of the next request in the sequence.
        """

        request = """POST / HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Length: 13\r\nTransfer-Encoding: chunked\r\n\r\n0\r\nSMUGGLED"""
        visitor = self.build_and_visit_ast(request)

        self.assertEqual(visitor.method, HttpMethod.POST)
        self.assertEqual(visitor.content_length, 13)
        self.assertIsNone(visitor.content_type)
        self.assertEqual(visitor.transfer_encoding, "chunked")
        self.assertIn(member="SMUGGLED", container=visitor.body_raw)

    def test_post_body_chunked_with_smuggling_cl_te_timing_detection(self):
        """Since the front-end server uses the Content-Length header, if request smuggling is possible, it will forward only part of this request, omitting the X. The back-end server uses the Transfer-Encoding header, processes the first chunk, and then waits for the next chunk to arrive. This will cause an observable time delay."""

        request = """POST / HTTP/1.1\r\nHost: vulnerable-website.com\r\nTransfer-Encoding: chunked\r\nContent-Length: 4\r\n\r\n1\r\nA\r\nX"""
        visitor = self.build_and_visit_ast(request)
        self.assertEqual("1\r\nA\r\nX", visitor.body_raw)

    def test_post_body_chunked_with_smuggling_cl_te_2(self):
        """To confirm a CL.TE vulnerability, you would send an attack request like this. If the attack is successful, then the last two lines of this request are treated by the back-end server as belonging to the next request that is received."""

        request = """POST /search HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 49\r\nTransfer-Encoding: chunked\r\n\r\ne\r\nq=smuggling&x=\r\n0\r\n\r\nGET /404 HTTP/1.1\r\nFoo: x"""
        visitor = self.build_and_visit_ast(request)
        self.assertEqual(
            "e\r\nq=smuggling&x=\r\n0\r\n\r\nGET /404 HTTP/1.1\r\nFoo: x",
            visitor.body_raw,
        )

    def test_post_body_chunked_with_smuggling_te_cl(self):
        """Here, the front-end server uses the Transfer-Encoding header and the back-end server uses the Content-Length header. We can perform a simple HTTP request smuggling attack as follows:"""

        request = """POST / HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Length: 3\r\nTransfer-Encoding: chunked\r\n\r\n8\r\nSMUGGLED\r\n0"""
        visitor = self.build_and_visit_ast(request)

        self.assertEqual(visitor.method, HttpMethod.POST)
        self.assertEqual(visitor.content_length, 3)
        self.assertEqual(visitor.transfer_encoding, "chunked")
        self.assertIn(member="SMUGGLED", container=visitor.body_raw)
        self.assertIn(member="0", container=visitor.body_raw)

    def test_post_body_chunked_with_smuggling_te_cl_timing_detection(self):
        """If an application is vulnerable to the TE.CL variant of request smuggling, then sending a request like the following will often cause a time delay. Since the front-end server uses the Transfer-Encoding header, it will forward only part of this request, omitting the X. The back-end server uses the Content-Length header, expects more content in the message body, and waits for the remaining content to arrive."""

        request = """POST / HTTP/1.1\r\nHost: vulnerable-website.com\r\nTransfer-Encoding: chunked\r\nContent-Length: 6\r\n\r\n0\r\n\r\nX"""
        visitor = self.build_and_visit_ast(request)
        self.assertEqual("0\r\n\r\nX", visitor.body_raw)

    def test_post_body_chunked_with_smuggling_te_cl_2(self):
        """To confirm a TE.CL vulnerability, you would send an attack request like this. If the attack is successful, then everything from GET /404 onwards is treated by the back-end server as belonging to the next request that is received."""

        request = """POST /search HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 4\r\nTransfer-Encoding: chunked\r\n\r\n7c\r\nGET /404 HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 144\r\n\r\nx=\r\n0"""
        visitor = self.build_and_visit_ast(request)
        self.assertEqual(
            "7c\r\nGET /404 HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 144\r\n\r\nx=\r\n0",
            visitor.body_raw,
        )

    def test_post_body_chunked_with_smuggling_te_te(self):
        """Here, the front-end and back-end servers both support the Transfer-Encoding header, but one of the servers can be induced not to process it by obfuscating the header in some way.

        Each of these techniques involves a subtle departure from the HTTP specification. Real-world code that implements a protocol specification rarely adheres to it with absolute precision, and it is common for different implementations to tolerate different variations from the specification. To uncover a TE.TE vulnerability, it is necessary to find some variation of the Transfer-Encoding header such that only one of the front-end or back-end servers processes it, while the other server ignores it.

        Depending on whether it is the front-end or the back-end server that can be induced not to process the obfuscated Transfer-Encoding header, the remainder of the attack will take the same form as for the CL.TE or TE.CL vulnerabilities already described.

        C.f.: https://www.rfc-editor.org/rfc/rfc7230#section-3.3.3
        """

        def transfer_encoding_variant_to_request(transfer_encoding: str) -> str:
            return f"""POST / HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Length: 13\r\n{transfer_encoding}\r\n\r\n0\r\nSMUGGLED"""

        r1 = transfer_encoding_variant_to_request("Transfer-Encoding: xchunked")
        v1 = self.build_and_visit_ast(r1)
        self.assertEqual(v1.transfer_encoding, "xchunked")

        # there is no OWS before a header name, nor after it before the colon
        r2 = transfer_encoding_variant_to_request("Transfer-Encoding : chunked")
        self.assertRaises(ParseError, self.grammar.parse, r2, 0)

        r3 = transfer_encoding_variant_to_request(
            "Transfer-Encoding: chunked\r\nTransfer-Encoding: x"
        )
        v3 = self.build_and_visit_ast(r3)
        self.assertIn(member="Transfer-Encoding: chunked", container=v3.headers)
        self.assertIn(member="Transfer-Encoding: x", container=v3.headers)
        # TODO fold these together into one Visitor member? how do we want to dedupe? I think it depends on header??
        self.assertEqual(v3.transfer_encoding, "x")

        # OWS includes horizontal tab (HTAB aka \t)
        r4 = transfer_encoding_variant_to_request("Transfer-Encoding:\tchunked")
        v4 = self.build_and_visit_ast(r4)
        self.assertEqual(v4.transfer_encoding, "chunked")

        # there is no OWS before a header name, nor after it before the colon
        r5 = transfer_encoding_variant_to_request(" Transfer-Encoding: chunked")
        self.assertRaises(ParseError, self.grammar.parse, r5, 0)

        r6 = transfer_encoding_variant_to_request("X: X[\n]Transfer-Encoding: chunked")
        self.assertRaises(ParseError, self.grammar.parse, r6, 0)

        r7 = transfer_encoding_variant_to_request("Transfer-Encoding\n: chunked")
        self.assertRaises(ParseError, self.grammar.parse, r7, 0)

        r8 = transfer_encoding_variant_to_request("Transfer-Encoding\r\n: chunked")
        self.assertRaises(ParseError, self.grammar.parse, r8, 0)
