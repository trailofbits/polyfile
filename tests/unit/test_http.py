from unittest import TestCase
from polyfile.http import HttpStringParser


class HttpUnitTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.http_parser = HttpStringParser()

    def test_cl_te(self):
        cl_te = """POST / HTTP/1.1\r\nHost: vulnerable-website.com\r\nContent-Length: 13\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\nSMUGGLED"""

        assert self.http_parser.parse(cl_te)
