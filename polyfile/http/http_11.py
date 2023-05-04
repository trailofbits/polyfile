import importlib
from string import whitespace
import sys

from abnf.grammars.misc import load_grammar_rules

from ..logger import getStatusLogger

if sys.version_info < (3, 11):
    # StrEnum is only available in Python 3.11 or newer
    from enum import Enum
    class StrEnum(str, Enum):
        pass
else:
    from enum import StrEnum


log = getStatusLogger("HTTP/1.1")

# loading the following modules is _really_ slow, so log its status!
for i, modname in enumerate(log.range((
    "cors",
    "rfc9110",
    "rfc5322",
    #"rfc4647",
    #"rfc5646",
    "rfc3986",
    "rfc7230",
    "rfc9111",
    "rfc6265",
), desc="Importing HTTP/1.1", unit=" grammars")):
    mod = importlib.import_module(f".{modname}", package="abnf.grammars")
    if i == 0:
        cors = mod
    elif i == 1:
        rfc9110 = mod
    elif i == 2:
        rfc5322 = mod
    elif i == 3:
        rfc3986 = mod
    elif i == 4:
        rfc7230 = mod
    elif i == 5:
        rfc9111 = mod
    elif i == 6:
        rfc6265 = mod
    else:
        raise NotImplementedError()
    log.debug(f"Loaded grammar for {modname}")
del mod
del modname
del i
log.clear_status()

from abnf import Rule, parser, Node

from . import defacto, deprecated, experimental, structured_headers

from typing import Dict, List, Optional, Set, Tuple

# The overall goal of this parser is to take in utf-8 textual representations
# of http requests, and make sense of the headers, then make sense of the
# body/ies according to the headers.

#   - TODO: support lowercase header names such as 'content-length' instead of only 'Content-Length' (currently case sensitive)
#   - TODO: create a similar parser for HTTP/2 requests (requires parsing HPACK and QPACK)
#   - TODO: websockets upgrade negotiation headers
#   - TODO: RFC9112 I think supersedes RFC9110 and should be accounted for here

# Response headers are not included here, since this parser is intended to parse valid http/1.1 requests. If the header can be used in either a request or a response, or only in a request, it should/can be included here.
# NB: the rfc9110.py class doesn't include all needed rules other specs and is missing HTTP headers used in practice but not defined in spec.
# NB: NodeVisitor#visit() replaces all dashes here with underscores.
request_rulelist: List[Tuple[str, Rule]] = [
    ("BWS", rfc9110.Rule("BWS")),
    ("OWS", rfc9110.Rule("OWS")),
    ("RWS", rfc9110.Rule("RWS")),
    ("Accept", rfc9110.Rule("Accept")),
    ("Accept-Encoding", rfc9110.Rule("Accept-Encoding")),
    ("Accept-Language", rfc9110.Rule("Accept-Language")),
    ("Access-Control-Request-Headers", cors.Rule("Access-Control-Request-Headers")),
    ("Age", rfc9111.Rule("Age")),
    ("Allow", rfc9110.Rule("Allow")),
    ("Authorization", rfc9110.Rule("Authorization")),
    ("Cache-Control", rfc9111.Rule("Cache-Control")),
    ("Connection", rfc9110.Rule("Connection")),
    ("Content-Encoding", rfc9110.Rule("Content-Encoding")),
    ("Content-Language", rfc9110.Rule("Content-Language")),
    ("Content-Length", rfc9110.Rule("Content-Length")),
    ("Content-Location", rfc9110.Rule("Content-Location")),
    ("Content-Range", rfc9110.Rule("Content-Range")),
    ("Content-Type", rfc9110.Rule("Content-Type")),
    ("Date", rfc9110.Rule("Date")),
    ("ETag", rfc9110.Rule("ETag")),
    ("Expect", rfc9110.Rule("Expect")),
    ("From", rfc5322.Rule("mailbox")),
    ("HTTP-date", rfc9110.Rule("HTTP-date")),
    ("Host", rfc9110.Rule("Host")),
    ("If-Match", rfc9110.Rule("If-Match")),
    ("If-Modified-Since", rfc9110.Rule("If-Modified-Since")),
    ("If-None-Match", rfc9110.Rule("If-None-Match")),
    ("If-Range", rfc9110.Rule("If-Range")),
    ("If-Unmodified-Since", rfc9110.Rule("If-Unmodified-Since")),
    ("Last-Modified", rfc9110.Rule("Last-Modified")),
    ("Location", rfc9110.Rule("Location")),
    ("Max-Forwards", rfc9110.Rule("Max-Forwards")),
    ("Proxy-Authenticate", rfc9110.Rule("Proxy-Authenticate")),
    ("Proxy-Authentication-Info", rfc9110.Rule("Proxy-Authentication-Info")),
    ("Proxy-Authorization", rfc9110.Rule("Proxy-Authorization")),
    ("Range", rfc9110.Rule("Range")),
    ("Referer", rfc9110.Rule("Referer")),
    ("Retry-After", rfc9110.Rule("Retry-After")),
    ("TE", rfc9110.Rule("TE")),
    ("Trailer", rfc9110.Rule("Trailer")),
    ("Upgrade", rfc9110.Rule("Upgrade")),
    ("User-Agent", rfc9110.Rule("User-Agent")),
    ("Via", rfc9110.Rule("Via")),
    ("WWW-Authenticate", rfc9110.Rule("WWW-Authenticate")),
    ("absolute-URI", rfc3986.Rule("absolute-URI")),
    ("absolute-path", rfc9110.Rule("absolute-path")),
    ("chunked-body", rfc7230.Rule("chunked-body")),
    ("cookie-string", rfc6265.Rule("cookie-string")),
    ("defacto-header", defacto.Rule("defacto-header")),
    ("deprecated-header", deprecated.Rule("deprecated-header")),
    ("experimental-header", experimental.Rule("experimental-header")),
    ("port", rfc3986.Rule("port")),
    ("protocol", rfc9110.Rule("protocol")),
    ("protocol-name", rfc9110.Rule("protocol-name")),
    ("protocol-version", rfc9110.Rule("protocol-version")),
    ("query", rfc3986.Rule("query")),
    ("quoted-string", rfc9110.Rule("quoted-string")),
    ("sh-boolean", structured_headers.Rule("sh-boolean")),
    ("start-line", rfc7230.Rule("start-line")),
    ("token", rfc9110.Rule("token")),
    ("token68", rfc9110.Rule("token68")),
    ("transfer-coding", rfc7230.Rule("transfer-coding")),
]


@load_grammar_rules(request_rulelist)
class Http11RequestGrammar(Rule):
    """
    An HTTP/1.1 request grammar, which is applied in the HttpVisitor below as demonstrated in the associated unit test suite.

    General References
       - https://http.dev/headers#http-header-categories-and-names (also includes response headers; it is VERY IMPORTANT that response headers not be defined in Http11RequestGrammar and only be defined in TODO Http11ResponseGrammar!)
       - How header fields generally get structured: https://www.rfc-editor.org/rfc/rfc7230#section-3.2
       - Also helpful: https://www.rfc-editor.org/rfc/rfc5234 which describes how ABNF for syntax specifications works
       - And https://www.rfc-editor.org/rfc/rfc9110#section-5.6.1 (pound sign definition for ABNF in e.g. Forwarded header RFC7239)
       - Structured Header rules (even fancier than RFC 7230): https://datatracker.ietf.org/doc/html/rfc8941
    """

    grammar: List[str] = [
        # https://www.rfc-editor.org/rfc/rfc7230 defines start-line and request.
        "request = start-line 1*( header CR LF ) CR LF [ body ]",
        'request-path = absolute-path *( "?" query ) / "*"',
        "header = caching-header / deprecated-header / end-to-end-header / hop-by-hop-header / experimental-header / unknown-or-bespoke-header",
        # Added by proxies (forward and reverse) generally; mainly sourced from RFC 9110; not including response headers
        'hop-by-hop-header = "Connection:" OWS Connection OWS / "Forwarded:" OWS Forwarded OWS / "Keep-Alive:" OWS Keep-Alive OWS / "Proxy-Authenticate:" OWS Proxy-Authenticate OWS / "Proxy-Authentication-Info:" OWS Proxy-Authentication-Info OWS / "Proxy-Authorization:" OWS Proxy-Authorization OWS / "TE:" OWS TE OWS / "Trailer:" OWS Trailer OWS / "Transfer-Encoding:" OWS Transfer-Encoding OWS / "Upgrade:" OWS Upgrade OWS / "Via:" OWS Via OWS / defacto-header',
        # Mainly sourced from RFC 9110 (but also includes eg RFC 6265 for cookies, and others); not including response headers
        'end-to-end-header = "Accept:" OWS Accept OWS / "Accept-Encoding:" OWS Accept-Encoding OWS / "Accept-Language:" OWS Accept-Language OWS / "Access-Control-Request-Headers:" OWS Access-Control-Request-Headers OWS / "Access-Control-Request-Method:" OWS Access-Control-Request-Method OWS / "Authorization:" OWS Authorization OWS / "Content-Encoding:" OWS Content-Encoding OWS / "Content-Language:" OWS Content-Language OWS / "Content-Length:" OWS Content-Length OWS / "Content-Range:" OWS Content-Range OWS / "Content-Type:" OWS Content-Type OWS / "Cookie:" OWS cookie-string OWS / "Date:" OWS Date OWS / "Expect:" OWS Expect OWS / "From:" OWS From OWS / "Host:" OWS Host OWS / "If-Match:" OWS If-Match OWS / "If-Modified-Since:" OWS If-Modified-Since OWS / "If-None-Match:" OWS If-None-Match OWS / "If-Range:" OWS If-Range OWS / "If-Unmodified-Since:" OWS If-Unmodified-Since OWS / "Location:" OWS Location OWS / "Max-Forwards:" OWS Max-Forwards OWS / "Range:" OWS Range OWS / "Referer:" OWS Referer OWS / "Retry-After:" OWS Retry-After OWS / "Sec-CH-UA:" OWS Sec-CH-UA OWS / "Sec-Fetch-Dest:" OWS Sec-Fetch-Dest OWS / "Sec-Fetch-Mode:" OWS Sec-Fetch-Mode OWS / "Sec-Fetch-Site:" OWS Sec-Fetch-Site OWS / "Sec-Fetch-User:" OWS Sec-Fetch-User OWS / "Service-Worker-Navigation-Preload:" OWS Service-Worker-Navigation-Preload OWS / "Upgrade-Insecure-Requests:" OWS Upgrade-Insecure-Requests OWS / "User-Agent:" OWS User-Agent OWS / "Want-Digest:" OWS Want-Digest OWS / "WWW-Authenticate:" OWS WWW-Authenticate OWS',
        # rfc 9111 (caching) request headers follow
        'caching-header = "Age:" OWS Age OWS / "Cache-Control:" OWS Cache-Control OWS',
        # TODO kaoudis this is a placeholder for all the other headers... should be a better way to do this
        'unknown-or-bespoke-header = token ":" OWS token OWS',
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods
        "Access-Control-Request-Method = method",
        # method is defined as 'token' in rfc9110 but better to be explicit...
        'method = "GET" / "HEAD" / "POST" / "PUT" / "PATCH" / "DELETE" / "TRACE" / "CONNECT" / "OPTIONS"',
        # https://www.rfc-editor.org/rfc/rfc7239#section-4
        'Forwarded = forwarded-element *( OWS "," OWS forwarded-element )',
        'forwarded-element = [ forwarded-pair ] *( ";" [ forwarded-pair ] )',
        'forwarded-pair = token "=" value',
        "value          = token / quoted-string",
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Keep-Alive
        # https://httpwg.org/specs/rfc9112.html#compatibility.with.http.1.0.persistent.connections
        # https://www.rfc-editor.org/rfc/rfc2068.html#section-19.7.1
        'Keep-Alive = keepalive-param *( OWS "," OWS keepalive-param )',
        'keepalive-param = param-name "=" value',
        # param-name is a best guess, it doesn't seem to be explicitly defined
        "param-name = token / quoted-string",
        # https://w3c.github.io/webappsec-fetch-metadata/#sec-fetch-dest-header
        'Sec-Fetch-Dest = "audio" / "audioworklet" / "document" / "embed" / "empty" / "font" / "frame" / "iframe" / "image" / "manifest" / "object" / "paintworklet" / "report" / "script" / "serviceworker" / "sharedworker" / "style" / "track" / "video" / "worker" / "xslt"',
        # https://w3c.github.io/webappsec-fetch-metadata/#sec-fetch-mode-header
        'Sec-Fetch-Mode = "cors" / "navigate" / "no-cors" / "same-origin" / "websocket"',
        # https://w3c.github.io/webappsec-fetch-metadata/#sec-fetch-site-header
        'Sec-Fetch-Site = "cross-site" / "same-origin" / "same-site" / "none"',
        # https://w3c.github.io/webappsec-fetch-metadata/#sec-fetch-user-header
        # https://docs.w3cub.com/http/headers/sec-fetch-user.html
        "Sec-Fetch-User = sh-boolean",
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Service-Worker-Navigation-Preload
        'Service-Worker-Navigation-Preload = "true" / token / quoted-string',
        # https://www.rfc-editor.org/rfc/rfc7230#section-4 this is a better defn of transfer-encoding than the rfc9112, which is less clear. Also c.f. https://www.rfc-editor.org/rfc/rfc7230#section-4.2.3
        'Transfer-Encoding = *( "," OWS ) transfer-coding-plus-x-gzip *( OWS "," [ OWS transfer-coding-plus-x-gzip ] )',
        'transfer-coding-plus-x-gzip = transfer-coding / "x-gzip"',
        # https://w3c.github.io/webappsec-upgrade-insecure-requests/#preference
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Upgrade-Insecure-Requests
        'Upgrade-Insecure-Requests = "1"',
        # https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-digest-headers#section-4
        # https://http.dev/want-digest
        'Want-Digest = want-digest-value *( OWS "," OWS want-digest-value )',
        'want-digest-value = digest-algorithm [ ";" "q" "=" want-digest-qvalue]',
        'want-digest-qvalue = ( "0" [ "." 0*1DIGIT ] ) / ( "1" [ "." 0*1( "0" ) ] )',
        # https://www.ietf.org/archive/id/draft-ietf-httpbis-digest-headers-04.html#section-5
        'digest-algorithm = "sha-256" / "sha-512" / "md5" / "sha" / "unixsum" / "unixcksum" / "id-sha-512" / "id-sha-256" / token',
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Messages
        # https://www.rfc-editor.org/rfc/rfc7230#section-3.3
        # https://www.rfc-editor.org/rfc/rfc7230#section-3.5
        "body = 1*OCTET",
    ]


class HttpMethod(StrEnum):
    GET = "GET"
    HEAD = "HEAD"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    TRACE = "TRACE"
    CONNECT = "CONNECT"
    OPTIONS = "OPTIONS"


class HttpVisitor(parser.NodeVisitor):
    """Interprets information parsed into an AST using the abnf-powered
    HTTP 1.1 request grammar.

    NB: The NodeVisitor class requires a visit_Name()
    method which can be called to visit only the section(s) of the AST of interest. Add (or edit) additional visitor methods for additional AST sections of interest.
    """

    _hex_without_zero = [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
        "A",
        "B",
        "C",
        "D",
        "E",
    ]

    # start-line
    method: HttpMethod
    request_target: str

    # unprocessed headers (global)
    headers: Dict[str, str] = None

    # headers (specific)
    content_type: Optional[str] = None
    content_length: Optional[int] = None
    host: Optional[str] = None

    # body
    body_raw: str = None
    body_parsed: List[str] = None

    def __init__(self):
        super().__init__()

    def _remove_header(self, name: str) -> None:
        """Required by RFC to support Transfer-Encoding and TE headers. Once the transfer encoding no longer applies to the message, it must be removed."""
        if name in self.headers:
            self.headers.pop(name)

    def visit_request(self, node: Node):
        for child in node.children:
            if child.name == "header":
                if self.headers is None:
                    # prevents weird reuse between instances in unittest.
                    # TODO kaoudis find out why? maybe bad test config?
                    self.headers = dict()
                header_name, header_value = child.value.strip(whitespace).split(":", 1)
                self.headers[header_name] = header_value.strip(whitespace)
            if child.name == "body":
                self.body_raw = child.value
                if self.body_parsed is None:
                    self.body_parsed = list()

            self.visit(child)

    def visit_start_line(self, node: Node):
        for child in node.children:
            self.visit(child)

    def visit_request_line(self, node: Node):
        for child in node.children:
            self.visit(child)

    def visit_method(self, node: Node):
        self.method = HttpMethod(node.value)

    def visit_request_target(self, node: Node):
        self.request_target = node.value

    def visit_header(self, node: Node):
        for child in node.children:
            self.visit(child)

    def visit_end_to_end_header(self, node: Node):
        for child in node.children:
            if child.name == "Content-Length":
                self.content_length = int(child.value)
            elif child.name == "Content-Type":
                self.content_type = child.value
            elif child.name == "Host":
                self.host = child.value

            self.visit(child)

    def visit_hop_by_hop_header(self, node: Node):
        """RFC2616 and RFC7230 hop-by-hop headers."""
        for child in node.children:
            if child.name == "Connection":
                self.connection = child.value
            elif child.name == "Forwarded":
                self.forwarded = child.value
            elif child.name == "Keep-Alive":
                self.keep_alive = child.value
            elif child.name == "Proxy-Authenticate":
                self.proxy_authenticate = child.value
            elif child.name == "Proxy-Authentication-Info":
                self.proxy_authentication_info = child.value
            elif child.name == "Proxy-Authorization":
                self.proxy_authorization = child.value
            elif child.name == "TE":
                self.te = child.value
            elif child.name == "Trailer":
                self.trailer = child.value
            elif child.name == "Transfer-Encoding":
                self.transfer_encoding = child.value
            elif child.name == "Upgrade":
                self.upgrade = child.value
            elif child.name == "Via":
                self.via = child.value

            self.visit(child)

    def visit_body(self, node: Node):
        if (
            self.content_length is not None
            and self.content_length > 0
            and not hasattr(self, "transfer_encoding")
            and not hasattr(self, "te")
        ):
            octet_counter = self.content_length
            for child in node.children:
                # Append octets up to content-length if the body is not chunked encoding; the rest are still in the AST and may refer to various kinds of trailer(s) but should be ignored for purposes of content-length based body processing.
                if octet_counter > 0 and child.name == "OCTET":
                    octet_counter -= 1
                    self.body_parsed.append(child.value)

                self.visit(child)
        elif (
            hasattr(self, "transfer_encoding") and self.transfer_encoding == "chunked"
        ) or (hasattr(self, "te") and self.te == "chunked"):
            # this is a hack following the rfc parsing definition
            # c.f. https://www.rfc-editor.org/rfc/rfc7230#section-4.1.3
            # since abnf parses everything all at once and I really want
            # it to be incremental to more sensibly follow the rfc defn
            self.visit_chunked_body(node)
        else:
            return  # do nothing

    def _chunk_size(self, node_children: List[Node]) -> Tuple[int, int]:
        """There is no max chunk size defined in spec. Therefore, read until the semicolon which would start a chunk extension, or until CR (for CR LF). The index returned is either the index of the first extension field semicolon, or the CR of the CR LF which indicates hte chunk body starts next. If there are trailers, we'll return the index of the first trailer, and chunk_size of 0."""
        chunk_size_acc: List[str] = []
        for child in node_children:
            # https://stackoverflow.com/a/7058854
            if child.value in self._hex_without_zero:
                chunk_size_acc.append(child.value)
            elif child.value == "0":
                return (0, 1)
            elif child.value == "\r":
                # the chunk size and the index of the first non-chunk-size thing
                return (int("".join(chunk_size_acc), 16), node_children.index(child))
            else:
                return (0, node_children.index(child))

    def _accumulate_chunk_extensions(
        self, node_children: List[Node], starting_index: int
    ) -> Tuple[List[str], int]:
        """Returns the chunk extensions and the first index after the following CRLF.
        TODO kaoudis: handle chunk extensions more better according to RFC."""
        chunk_ext: List[str] = []
        for child in node_children[starting_index:]:
            if child.value != "\r":
                chunk_ext.append(child.value)
            else:
                index = node_children.index(child)
                if len(node_children) >= index + 2 and node_children[index + 1] == "\n":
                    return (chunk_ext, index + 2)

    def _accumulate_trailers(self, node_children: List[Node]):
        """
        Following https://www.rfc-editor.org/rfc/rfc7230#section-4.4,
        we use the Trailer header to figure out what will be in the chunked transfer coding trailer(s) and add these additional headers to the Visitor instance's header list.

        See also: https://www.rfc-editor.org/rfc/rfc7230#section-4.1.2, https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Trailer

        The trailer fields are identical to header fields, except
        they are sent in a chunked trailer instead of the message's header
        section.

        A sender MUST NOT generate a trailer that contains a field necessary
        for message framing (e.g., Transfer-Encoding and Content-Length),
        routing (e.g., Host), request modifiers (e.g., controls and
        conditionals in Section 5 of [RFC7231]), authentication (e.g., see
        [RFC7235] and [RFC6265]), response control data (e.g., see Section
        7.1 of [RFC7231]), or determining how to process the payload (e.g.,
        Content-Encoding, Content-Type, Content-Range, and Trailer).

        When a chunked message containing a non-empty trailer is received,
        the recipient MAY process the fields (aside from those forbidden
        above) as if they were appended to the message's header section.  A
        recipient MUST ignore (or consider as an error) any fields that are
        forbidden to be sent in a trailer, since processing them as if they
        were present in the header section might bypass external security
        filters.
        """

        if hasattr(self, "trailer"):
            disallowed_fields: Set = {
                "Transfer-Encoding",
                "Content-Length",
                "Host",
                "Cache-Control",
                "Max-Forwards",
                "TE",
                "Authorization",
                "Set-Cookie",
                "Content-Encoding",
                "Content-Type",
                "Content-Range",
                "Trailer",
            }

            trailer_field_names: Set = set(self.trailer.split(","))
            allowed_trailer_field_names: Set = trailer_field_names - disallowed_fields
            trailer_headers_string = []

            for node in node_children:
                trailer_headers_string.append(node.value)

            # TODO kaoudis this is utterly ridiculous, clean it up
            trailer_headers: List[str] = list(
                filter(None, "".join(trailer_headers_string).split("\r\n"))
            )

            for header in trailer_headers:
                name, value = header.strip(whitespace).split(":", 1)
                if name in allowed_trailer_field_names:
                    # A recipient that retains a received trailer field MUST
                    # either store/forward the trailer field separately from
                    # the received header fields or merge the received trailer
                    # field into the header section. A recipient MUST NOT merge
                    # a received trailer field into the header section unless
                    # its corresponding header field definition explicitly
                    # permits and instructs how the trailer field value can be
                    # safely merged.
                    self.headers[name] = value.strip(whitespace)
                    self.__setattr__(name.lower(), value)

    def _accumulate_chunks(self, node_children: List[Node], length: int = 0) -> int:
        """An utterly hideous yet hopefully fairly close interpretation of the chunk accumulation algorithm from rfc7230 and rfc9112."""

        # read chunk-size, chunk-ext (if any), and CR LF
        (chunk_size, next_index) = self._chunk_size(node_children)
        length += chunk_size

        # node_children[1] = CR; node_children[2] = LF if no chunk-ext
        # https://www.rfc-editor.org/rfc/rfc7230#section-4.1.1
        # a recipient must ignore unrecognized chunk-extensions!
        if chunk_size > 0:
            if (
                node_children[next_index].value != ";"
                and len(node_children) >= next_index + 2
            ):
                starting_index: int = next_index + 2
            else:
                # in theory chunk extensions should start with ';'
                (self.chunk_ext, starting_index) = self._accumulate_chunk_extensions(
                    node_children, next_index
                )
        elif not hasattr(self, "trailer"):
            # chunk size is 0 and no trailer, so we are done
            return chunk_size

        for child in node_children[starting_index:]:
            index = node_children.index(child)

            if chunk_size > 0:
                # just blindly trust the number lol
                self.body_parsed.append(child.value)
                chunk_size -= 1
            elif (
                index + 3 <= len(node_children)
                and child.value == "\r"
                and node_children[index + 1].value == "\n"
                and node_children[index + 2].value in self._hex_without_zero
            ):
                # If not 0 and all octets are accounted for, the next thing should be the next chunk size. Keep adding data to body_parsed.
                slice_index = index + 2
                length += self._accumulate_chunks(node_children[slice_index:], length)
            elif (
                # hasattr 'trailer' means there was a Trailer header
                hasattr(self, "trailer")
                # '\r\n0\r\n' where our current index is the first '\r'
                and index + 5 <= len(node_children)
                and child.value == "\r"
                # ending chunks w/ '0\r\n'
                and node_children[index + 2].value == "0"
            ):
                trailer_starting_index = index + 5
                self._accumulate_trailers(node_children[trailer_starting_index:])
                return length
            else:
                return length

            self.visit(child)

    def visit_chunked_body(self, node: Node):
        """Defined in RFC 7230 Sec. 4.1.3
         c.f. https://www.rfc-editor.org/rfc/rfc7230#section-4.1.3 and repeated! in https://www.rfc-editor.org/rfc/rfc9112#section-7.1.3

         If a message is received with both a Transfer-Encoding and a
        Content-Length header field, the Transfer-Encoding overrides the
        Content-Length.  Such a message might indicate an attempt to
        perform request smuggling (Section 9.5) or response splitting
        (Section 9.4) and ought to be handled as an error.  A sender MUST
        remove the received Content-Length field prior to forwarding such
        a message downstream.
        """
        self.content_length = self._accumulate_chunks(node_children=node.children)
        self._remove_header("Transfer-Encoding")
