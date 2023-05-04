from io import BytesIO
from unittest import TestCase

from abnf.parser import ParseError

from polyfile.fileutils import FileStream, Tempfile
from polyfile.http.http_11 import *
from polyfile.http.matcher import http_11_matcher, HTTP_11_MIME_TYPE
from polyfile.magic import MagicMatcher, MatchedTest


class Http11RequestUnitTests(TestCase):
    """Test that the HTTP 1.1 Request grammar can parse HTTP/1.1 requests.

    Test requests are from https://portswigger.net/web-security/request-smuggling and https://portswigger.net/web-security/request-smuggling/finding.
    """

    def setUp(self) -> None:
        self.request_grammar: Http11RequestGrammar = Http11RequestGrammar("request")
        self.visitor: HttpVisitor = HttpVisitor()
        return super().setUp()

    def tearDown(self) -> None:
        self.visitor = None
        return super().tearDown()

    def test_post_body_form_encoded(self):
        """Most HTTP request smuggling vulnerabilities arise because the HTTP specification provides two different ways to specify where a request ends: the Content-Length header and the Transfer-Encoding header.

        The Content-Length header is straightforward: it specifies the length of the message body in bytes. For example:
        """

        request = """POST /search HTTP/1.1\r\nHost: normal-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 11\r\n\r\nq=smuggling"""
        ast, offset = self.request_grammar.parse(request, 0)
        self.visitor.visit(ast)

        self.assertEqual(self.visitor.method, HttpMethod.POST)
        self.assertEqual(self.visitor.request_target, "/search")
        self.assertEqual(self.visitor.content_type, "application/x-www-form-urlencoded")
        self.assertEqual(self.visitor.content_length, 11)
        self.assertIn(member="q=smuggling", container=self.visitor.body_raw)
        self.assertEqual(len(self.visitor.body_raw), self.visitor.content_length)
        self.assertEqual(len(self.visitor.body_parsed), self.visitor.content_length)
        self.assertEqual(self.visitor.body_raw, "".join(self.visitor.body_parsed))

    def test_post_body_chunked(self):
        """The Transfer-Encoding header can be used to specify that the message body uses chunked encoding. This means that the message body contains one or more chunks of data. Each chunk consists of the chunk size in bytes (expressed in hexadecimal), followed by a newline, followed by the chunk contents. The message is terminated with a chunk of size zero. For example:"""

        request = """POST /search HTTP/1.1\r\nHost: normal-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nTransfer-Encoding: chunked\r\n\r\nb\r\nq=smuggling\r\n0\r\n"""
        ast, offset = self.request_grammar.parse(request, 0)
        self.visitor.visit(ast)

        self.assertEqual(self.visitor.method, HttpMethod.POST)
        self.assertEqual(self.visitor.request_target, "/search")
        self.assertEqual(self.visitor.content_type, "application/x-www-form-urlencoded")
        self.assertEqual(self.visitor.transfer_encoding, "chunked")
        # we have processed the encoding and removed it from the message, effectively
        self.assertNotIn("Transfer-Encoding", self.visitor.headers)

        # chunk content length
        self.assertIn(member="b", container=self.visitor.body_raw)
        # chunk terminates with 0
        self.assertIn(member="0", container=self.visitor.body_raw)

        # parsed body should be chunked and should contain b octets (11 in decimal)
        self.assertEqual(int("b", 16), len(self.visitor.body_parsed))
        self.assertEqual("q=smuggling", "".join(self.visitor.body_parsed))
        self.assertEqual(self.visitor.content_length, 11)

    def test_post_body_chunked_with_smuggling_cl_te(self):
        """Here, the front-end server uses the Content-Length header and the back-end server uses the Transfer-Encoding header. We can perform a simple HTTP request smuggling attack as follows. The front-end server processes the Content-Length header and determines that the request body is 13 bytes long, up to the end of SMUGGLED. This request is forwarded on to the back-end server.

        The back-end server processes the Transfer-Encoding header, and so treats the message body as using chunked encoding. It processes the first chunk, which is stated to be zero length, and so is treated as terminating the request. The following bytes, SMUGGLED, are left unprocessed, and the back-end server will treat these as being the start of the next request in the sequence.

        What should actually happen is defined in RFC 7230 https://www.rfc-editor.org/rfc/rfc7230: since there is a Transfer-Encoding header, we should replace the Content-Length, and should follow the Transfer-Encoding scheme to understand the body.
        """

        request = """POST / HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Length: 13\r\nTransfer-Encoding: chunked\r\n\r\n0\r\nSMUGGLED\r\n"""
        ast, offset = self.request_grammar.parse(request, 0)
        self.visitor.visit(ast)

        self.assertEqual(self.visitor.method, HttpMethod.POST)
        self.assertIsNone(self.visitor.content_type)
        self.assertEqual(self.visitor.transfer_encoding, "chunked")
        self.assertIn(member="SMUGGLED", container=self.visitor.body_raw)
        self.assertNotIn(member="SMUGGLED", container=self.visitor.body_parsed)
        self.assertNotEqual(self.visitor.content_length, 13)
        self.assertEqual(self.visitor.content_length, 0)
        self.assertEqual("".join(self.visitor.body_parsed), "")

    def test_post_body_chunked_with_smuggling_cl_te_timing_detection(self):
        """Since the front-end server uses the Content-Length header, if request smuggling is possible, it will forward only part of this request, omitting the X. The back-end server uses the Transfer-Encoding header, processes the first chunk, and then waits for the next chunk to arrive. This will cause an observable time delay.

        If we are to parse this request correctly according to RFC7230, we replace the content length of 4 with 1 (the chunked length specified), which means we would expect a ending chunk of 0, which never happens.

        TODO kaoudis I'm not sure if we should make the parser *not* wait for the 0\r\n ending chunk... that would be going against spec, but the specs here often conflict... if we were a web server, I'd think we should just fully throw away the 'to be smuggled' request bytes and not 'pass them on'
        """

        request = """POST / HTTP/1.1\r\nHost: vulnerable-website.com\r\nTransfer-Encoding: chunked\r\nContent-Length: 4\r\n\r\n1\r\nA\r\nX"""
        ast, offset = self.request_grammar.parse(request, 0)
        self.visitor.visit(ast)
        self.assertEqual("1\r\nA\r\nX", self.visitor.body_raw)
        self.assertEqual(self.visitor.transfer_encoding, "chunked")
        self.assertNotEqual(self.visitor.content_length, 4)
        self.assertEqual(self.visitor.content_length, 1)
        self.assertEqual("".join(self.visitor.body_parsed), "A")

    def test_post_body_chunked_with_smuggling_cl_te_2(self):
        """To confirm a CL.TE vulnerability, you would send an attack request like this. If the attack is successful, then the last two lines of this request are treated by the back-end server as belonging to the next request that is received.

        TODO kaoudis I'm not sure if we should make the parser *not* wait for the 0\r\n ending chunk... that would be going against spec, but the specs here often conflict... if we were a web server, I'd think we should just fully throw away the 'to be smuggled' request bytes and not 'pass them on'
        """

        request = """POST /search HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 49\r\nTransfer-Encoding: chunked\r\n\r\ne\r\nq=smuggling&x=\r\n0\r\n\r\nGET /404 HTTP/1.1\r\nFoo: x"""
        ast, offset = self.request_grammar.parse(request, 0)
        self.visitor.visit(ast)
        self.assertEqual(
            "e\r\nq=smuggling&x=\r\n0\r\n\r\nGET /404 HTTP/1.1\r\nFoo: x",
            self.visitor.body_raw,
        )
        self.assertEqual(self.visitor.transfer_encoding, "chunked")
        self.assertNotEqual(self.visitor.content_length, 49)
        self.assertEqual(self.visitor.content_length, int("e", 16))

    def test_post_body_chunked_with_smuggling_te_cl(self):
        """Here, the front-end server uses the Transfer-Encoding header and the back-end server uses the Content-Length header. We can perform a simple HTTP request smuggling attack as follows:

        What should happen here as above is the chunked length in the body should supersede the content-length. So SMUGGLED shouldn't be smuggled.
        """

        request = """POST / HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Length: 3\r\nTransfer-Encoding: chunked\r\n\r\n8\r\nSMUGGLED\r\n0\r\n"""
        ast, offset = self.request_grammar.parse(request, 0)
        self.visitor.visit(ast)

        self.assertEqual(self.visitor.method, HttpMethod.POST)
        self.assertNotEqual(self.visitor.content_length, 3)
        self.assertEqual(self.visitor.content_length, 8)
        self.assertEqual(self.visitor.transfer_encoding, "chunked")
        self.assertIn(member="SMUGGLED", container=self.visitor.body_raw)
        self.assertIn(member="0", container=self.visitor.body_raw)
        self.assertEqual("".join(self.visitor.body_parsed), "SMUGGLED")

    def test_post_body_chunked_with_smuggling_te_cl_timing_detection(self):
        """If an application is vulnerable to the TE.CL variant of request smuggling, then sending a request like the following will often cause a time delay. Since the front-end server uses the Transfer-Encoding header, it will forward only part of this request, omitting the X. The back-end server uses the Content-Length header, expects more content in the message body, and waits for the remaining content to arrive.

        We want to completely drop the trailing \r\nX since it doesn't count as an acceptable trailer, and follows the 0\r\n that should end a chunked transmission.
        """

        request = """POST / HTTP/1.1\r\nHost: vulnerable-website.com\r\nTransfer-Encoding: chunked\r\nContent-Length: 6\r\n\r\n0\r\n\r\nX"""
        ast, offset = self.request_grammar.parse(request, 0)
        self.visitor.visit(ast)
        self.assertEqual("0\r\n\r\nX", self.visitor.body_raw)
        self.assertEqual(self.visitor.content_length, 0)
        self.assertNotIn("X", container=self.visitor.body_parsed)

    def test_post_body_chunked_with_smuggling_te_cl_2(self):
        """To confirm a TE.CL vulnerability, you would send an attack request like this. If the attack is successful, then everything from GET /404 onwards is treated by the back-end server as belonging to the next request that is received."""

        request = """POST /search HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 4\r\nTransfer-Encoding: chunked\r\n\r\n7c\r\nGET /404 HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 144\r\n\r\nx=\r\n0"""
        ast, offset = self.request_grammar.parse(request, 0)
        self.visitor.visit(ast)

        self.assertEqual(
            "7c\r\nGET /404 HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 144\r\n\r\nx=\r\n0",
            self.visitor.body_raw,
        )
        self.assertNotEqual(self.visitor.content_length, 144)
        expected_length: int = int("7c", 16)
        self.assertEqual(self.visitor.content_length, expected_length)
        self.assertEqual(len(self.visitor.body_parsed), expected_length)

    def transfer_encoding_variant_to_request(self, transfer_encoding: str) -> str:
        """Here, the front-end and back-end servers both support the Transfer-Encoding header, but one of the servers can be induced not to process it by obfuscating the header in some way.

        Each of these techniques involves a subtle departure from the HTTP specification.

        Real-world code that implements a protocol specification rarely adheres to it with absolute precision, and it is common for different implementations to tolerate different variations from the specification.

        To uncover a TE.TE vulnerability, it is necessary to find some variation of the Transfer-Encoding header such that only one of the front-end or back-end servers processes it, while the other server ignores it. Depending on whether it is the front-end or the back-end server that can be induced not to process the obfuscated Transfer-Encoding header, the remainder of the attack will take the same form as for the CL.TE or TE.CL vulnerabilities already described.

        C.f.: https://www.rfc-editor.org/rfc/rfc7230#section-3.3.3"""

        return f"""POST / HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Length: 13\r\n{transfer_encoding}\r\n\r\n0\r\nSMUGGLED"""

    def test_post_body_chunked_with_smuggling_te_te_xchunked(self):
        request = self.transfer_encoding_variant_to_request(
            "Transfer-Encoding: xchunked"
        )
        ast, offset = self.request_grammar.parse(request, 0)
        self.visitor.visit(ast)
        self.assertEqual(self.visitor.transfer_encoding, "xchunked")

    def test_post_body_chunked_with_smuggling_te_te_spaces(self):
        # there is no OWS before a header name, nor after it before the colon
        request = self.transfer_encoding_variant_to_request(
            "Transfer-Encoding : chunked"
        )
        self.assertRaises(ParseError, self.request_grammar.parse, request, 0)

    def test_post_body_chunked_with_smuggling_te_te_one_real_one_unrecognised(self):
        request = self.transfer_encoding_variant_to_request(
            "Transfer-Encoding: chunked\r\nTransfer-Encoding: x"
        )
        ast, offset = self.request_grammar.parse(request, 0)
        self.visitor.visit(ast)
        self.assertIn(member="Transfer-Encoding", container=self.visitor.headers)
        self.assertEqual(self.visitor.headers["Transfer-Encoding"], "x")
        # TODO kaoudis should these Transfer-Encoding headers be deduped. by spec?
        self.assertEqual(self.visitor.transfer_encoding, "x")

    def test_post_body_chunked_with_smuggling_te_te_one_htab(self):
        # OWS includes horizontal tab (HTAB aka \t)
        request = self.transfer_encoding_variant_to_request(
            "Transfer-Encoding:\tchunked"
        )
        ast, offset = self.request_grammar.parse(request, 0)
        self.visitor.visit(ast)
        self.assertEqual(self.visitor.transfer_encoding, "chunked")

    def test_post_body_chunked_with_smuggling_te_te_extra_ows(self):
        # there is no OWS before a header name, nor after it before the colon
        request = self.transfer_encoding_variant_to_request(
            " Transfer-Encoding: chunked"
        )
        self.assertRaises(ParseError, self.request_grammar.parse, request, 0)

    def test_post_body_chunked_with_smuggling_te_te_with_a_garbage_value(self):
        request = self.transfer_encoding_variant_to_request(
            "X: X[\n]Transfer-Encoding: chunked"
        )
        self.assertRaises(ParseError, self.request_grammar.parse, request, 0)

    def test_post_body_chunked_with_smuggling_te_te_with_newline(self):
        request = self.transfer_encoding_variant_to_request(
            "Transfer-Encoding\n: chunked"
        )
        self.assertRaises(ParseError, self.request_grammar.parse, request, 0)

    def test_post_body_chunked_with_smuggling_te_te_yolo_crlf(self):
        request = self.transfer_encoding_variant_to_request(
            "Transfer-Encoding\r\n: chunked"
        )
        self.assertRaises(ParseError, self.request_grammar.parse, request, 0)

    def test_multichunk_no_trailer(self):
        """This is an example of a chunked-encoding request followed by multiple chunks and terminated correctly."""
        request = """HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nTransfer-Encoding: chunked\r\n\r\n7\r\nMozilla\r\n9\r\nDeveloper\r\n7\r\nNetwork\r\n0\r\n"""
        ast, offset = self.request_grammar.parse(request, 0)
        self.visitor.visit(ast)

        self.assertEqual(self.visitor.transfer_encoding, "chunked")
        self.assertFalse(hasattr(self.visitor, "trailer"))
        self.assertEqual(
            self.visitor.body_raw,
            "7\r\nMozilla\r\n9\r\nDeveloper\r\n7\r\nNetwork\r\n0\r\n",
        )
        self.assertEqual("".join(self.visitor.body_parsed), "MozillaDeveloperNetwork")

    def test_trailer_header_with_no_trailer(self):
        """We should fail to parse the request body if a trailer is indicated, the encoding is chunked, and there is no trailer."""
        request = """HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nTransfer-Encoding: chunked\r\nTrailer: Bar\r\n\r\n7\r\nMozilla\r\n9\r\nDeveloper\r\n7\r\nNetwork\r\n0\r\n"""
        ast, offset = self.request_grammar.parse(request, 0)
        self.visitor.visit(ast)

        self.assertEqual(self.visitor.transfer_encoding, "chunked")
        self.assertTrue(hasattr(self.visitor, "trailer"))
        self.assertFalse(hasattr(self, "bar"))

    def test_disallowed_trailer(self):
        """Some headers are not allowed to be included as trailers. This means when we parse teh actual trailer field, this should fail."""
        request = """HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nTransfer-Encoding: chunked\r\nTrailer: Trailer\r\n\r\n7\r\nMozilla\r\n9\r\nDeveloper\r\n7\r\nNetwork\r\n0\r\nTrailer: coolstuff\r\n\r\n"""
        ast, offset = self.request_grammar.parse(request, 0)
        self.visitor.visit(ast)

        self.assertEqual(self.visitor.transfer_encoding, "chunked")
        self.assertTrue(hasattr(self.visitor, "trailer"))
        self.assertIn("Trailer", container=self.visitor.headers)
        self.assertEqual(self.visitor.headers["Trailer"], "Trailer")

    def test_chunked_with_trailer_header(self):
        """In this example, the Expires header is used at the end of the chunked message and serves as a trailing header.

        https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Trailer"""
        request = """HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nTransfer-Encoding: chunked\r\nTrailer: Expires\r\n\r\n7\r\nMozilla\r\n9\r\nDeveloper\r\n7\r\nNetwork\r\n0\r\nExpires: Wed, 21 Oct 2015 07:28:00 GMT\r\n\r\n"""
        ast, offset = self.request_grammar.parse(request, 0)
        self.visitor.visit(ast)

        self.assertEqual(self.visitor.transfer_encoding, "chunked")
        self.assertEqual(
            self.visitor.body_raw,
            "7\r\nMozilla\r\n9\r\nDeveloper\r\n7\r\nNetwork\r\n0\r\nExpires: Wed, 21 Oct 2015 07:28:00 GMT\r\n\r\n",
        )
        self.assertEqual("".join(self.visitor.body_parsed), "MozillaDeveloperNetwork")
        self.assertEqual(self.visitor.trailer, "Expires")
        self.assertTrue(hasattr(self.visitor, "expires"))
        self.assertIn(
            "Expires",
            container=self.visitor.headers,
        )
        self.assertEqual(
            self.visitor.headers["Expires"], "Wed, 21 Oct 2015 07:28:00 GMT"
        )

    def test_matching(self):
        matcher = MagicMatcher.DEFAULT_INSTANCE
        self.assertIn(HTTP_11_MIME_TYPE, matcher.tests_by_mime)
        tests = matcher.tests_by_mime[HTTP_11_MIME_TYPE]
        self.assertGreaterEqual(len(tests), 1)
        test = next(iter(tests))
        matches = tuple(test.match(b"POST /search HTTP/1.1\r\nHost: normal-website.com\r\nContent-Type: "
                                   b"application/x-www-form-urlencoded\r\nContent-Length: 11\r\n\r\nq=smuggling"))
        self.assertGreaterEqual(len(matches), 1)
        match = matches[0]
        self.assertIsInstance(match, MatchedTest)
        self.assertEqual(match.offset, 0)
        self.assertEqual(match.length, 22)
        self.assertEqual(match.value, "POST /search HTTP/1.1\r")
