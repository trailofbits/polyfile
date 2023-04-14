from enum import StrEnum

from abnf.grammars.misc import load_grammar_rules
from abnf.grammars import (
    cors,
    rfc9110,
    rfc5322,
    rfc4647,
    rfc5646,
    rfc3986,
    rfc7230,
    rfc9111,
    rfc6265,
)
from abnf import Rule, parser, Node

from .http import defacto, deprecated, experimental, structured_headers

from .polyfile import register_parser, InvalidMatch, Submatch

from typing import List, Optional, Tuple

# Goals: "parse HTTP"
#   - parse HTTP requests from utf-8 text file(s) with abnf
#   - parse HTTP requests (and streams) from pcaps with dpkt.
#   - maybe use this input to feed abnf parser if it's not a dupe step??
#   - maybe: expand from HTTP 1.1 to HTTP 2 (requires parsing HPACK and QPACK, but might be easy with dpkt, scapy, etc?)

# PCAP
# Samples from NetReSec: https://www.netresec.com/?page=PcapFiles
# Sample captures from WireShark: https://wiki.wireshark.org/SampleCaptures
# "the ultimate PCAP" https://weberblog.net/the-ultimate-pcap/

# The rfc9110.py class doesn't include all needed rules other specs and is missing HTTP headers used in practice but not defined in spec.
# NodeVisitor#visit() replaces all dashes here with underscores.
# RESPONSE headers in RFC 9110 are NOT included here.
# None of these RFCs really define HTTP request body. That is TODO.
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
    ("sh-boolean", structured_headers.Rule("sh-boolean")),
    ("start-line", rfc7230.Rule("start-line")),
    ("token", rfc9110.Rule("token")),
    ("token68", rfc9110.Rule("token68")),
    ("transfer-coding", rfc7230.Rule("transfer-coding")),
]


@load_grammar_rules(request_rulelist)
class Http11RequestGrammar(Rule):
    # todo ensure no response headers are allowed in the request grammar
    # TODO websockets nego headers
    """
     RFC 2616: The following HTTP/1.1 headers are hop-by-hop headers:
       - Connection
       - Keep-Alive
       - Proxy-Authenticate
       - Proxy-Authorization
       - TE
       - Trailer(s)
       - Transfer-Encoding
       - Upgrade

    All other headers defined by HTTP/1.1 are end-to-end headers.

    General References
       - https://http.dev/headers#http-header-categories-and-names (also includes response headers; it is VERY IMPORTANT that response headers not be defined in Http11RequestGrammar and only be defined in TODO Http11ResponseGrammar!)
       - How header fields generally get structured: https://www.rfc-editor.org/rfc/rfc7230#section-3.2
       - Also helpful: https://www.rfc-editor.org/rfc/rfc5234 which describes how ABNF for syntax specifications works
       - And https://www.rfc-editor.org/rfc/rfc9110#section-5.6.1 (pound sign definition for ABNF in e.g. Forwarded header RFC7239)
       - Structured Header rules (even fancier than RFC 7230): https://datatracker.ietf.org/doc/html/rfc8941
    """
    grammar: List[str] = [
        # https://www.rfc-editor.org/rfc/rfc7230
        "request = start-line 1*( header CR LF ) CR LF [ body ]",
        # method is defined as 'token' in rfc9110 but better to be explicit
        'method = "GET" / "HEAD" / "POST" / "PUT" / "PATCH" / "DELETE" / "TRACE" / "CONNECT" / "OPTIONS"',
        'request-path = absolute-path *( "?" query ) / "*"',
        "header = caching-header / deprecated-header / end-to-end-header / hop-by-hop-header / experimental-header / unknown-or-bespoke-header",
        # Added by proxies (forward and reverse) generally; mainly sourced from RFC 9110; not including response headers
        'hop-by-hop-header = "Connection:" OWS Connection OWS / "Forwarded:" OWS Forwarded OWS / "Keep-Alive:" OWS Keep-Alive OWS / "Proxy-Authenticate:" OWS Proxy-Authenticate OWS / "Proxy-Authentication-Info:" OWS Proxy-Authentication-Info OWS / "Proxy-Authorization:" OWS Proxy-Authorization OWS / "TE:" OWS TE OWS / "Trailer:" OWS Trailer OWS / "Transfer-Encoding:" OWS Transfer-Encoding OWS / "Upgrade:" OWS Upgrade OWS / "Via:" OWS Via OWS / defacto-header',
        # Mainly sourced from RFC 9110 (but also includes eg RFC 6265 for cookies, and others); not including response headers
        'end-to-end-header = "Accept:" OWS Accept OWS / "Accept-Encoding:" OWS Accept-Encoding OWS / "Accept-Language:" OWS Accept-Language OWS / "Access-Control-Request-Headers:" OWS Access-Control-Request-Headers OWS / "Access-Control-Request-Method:" OWS Access-Control-Request-Method OWS / "Authorization:" OWS Authorization OWS / "Content-Encoding:" OWS Content-Encoding OWS / "Content-Language:" OWS Content-Language OWS / "Content-Length:" OWS Content-Length OWS / "Content-Range:" OWS Content-Range OWS / "Content-Type:" OWS Content-Type OWS / "Cookie:" OWS cookie-string OWS / "Date:" OWS Date OWS / "Expect:" OWS Expect OWS / "From:" OWS From OWS / "Host:" OWS Host OWS / "If-Match:" OWS If-Match OWS / "If-Modified-Since:" OWS If-Modified-Since OWS / "If-None-Match:" OWS If-None-Match OWS / "If-Range:" OWS If-Range OWS / "If-Unmodified-Since:" OWS If-Unmodified-Since OWS / "Location:" OWS Location OWS / "Max-Forwards:" OWS Max-Forwards OWS / "Range:" OWS Range OWS / "Referer:" OWS Referer OWS / "Retry-After:" OWS Retry-After OWS / "Sec-CH-UA:" OWS Sec-CH-UA OWS / "Sec-Fetch-Dest:" OWS Sec-Fetch-Dest OWS / "Sec-Fetch-Mode:" OWS Sec-Fetch-Mode OWS / "Sec-Fetch-Site:" OWS Sec-Fetch-Site OWS / "Sec-Fetch-User:" OWS Sec-Fetch-User OWS / "Service-Worker-Navigation-Preload:" OWS Service-Worker-Navigation-Preload OWS / "Upgrade-Insecure-Requests:" OWS Upgrade-Insecure-Requests OWS / "User-Agent:" OWS User-Agent OWS / "Want-Digest:" OWS Want-Digest OWS / "WWW-Authenticate:" OWS WWW-Authenticate OWS',
        # rfc 9111 (caching) request headers follow
        'caching-header = "Age:" OWS Age OWS / "Cache-Control:" OWS Cache-Control OWS',
        # TODO kaoudis this is a placeholder for all the other stuff? this might not play nice with responses / if this grammar is used to parse responses, everything responsewise might end up in here
        'unknown-or-bespoke-header = token ":" OWS token OWS',
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods
        "Access-Control-Request-Method = method",
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
        # TODO kaoudis we are pretty dumb about allowed body size now - effectively, all body sizes are allowed for all methods. handle this in the body visitor method.
        # https://www.rfc-editor.org/rfc/rfc7230#section-3.5
        "body = chunked-body / 1*OCTET",
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
    """The NodeVisitor class requires a visit_Name()
    method which can be called to visit only the section(s) of the AST of interest. Add (or edit) additional visitor methods for additional AST sections of interest.
    """

    method: HttpMethod
    request_target: str
    headers: List[str] = []
    content_type: Optional[str] = None
    content_length: Optional[int] = None
    transfer_encoding: Optional[str] = None
    host: Optional[str] = None
    body_raw: Optional[str] = None
    body_parsed: Optional[str] = None

    def __init__(self):
        super().__init__()

    def visit_request(self, node: Node):
        for child in node.children:
            if child.name == "header":
                self.headers.append(child.value)
            if child.name == "body":
                self.body_raw = child.value

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
        """RFC 2616: The following HTTP/1.1 headers are hop-by-hop headers:
        - Connection
        - Keep-Alive
        - Proxy-Authenticate
        - Proxy-Authorization
        - TE
        - Trailer(s)
        - Transfer-Encoding
        - Upgrade
        """
        for child in node.children:
            if child.name == "Connection":
                self.connection = child.value
            elif child.name == "Keep-Alive":
                self.keep_alive = child.value
            elif child.name == "Proxy-Authenticate":
                self.proxy_authenticate = child.value
            elif child.name == "TE":
                self.te = child.value
            elif child.name == "Trailer":
                self.trailer = child.value
            elif child.name == "Transfer-Encoding":
                self.transfer_encoding = child.value
            elif child.name == "Upgrade":
                self.upgrade = child.value

            self.visit(child)

    def visit_body(self, node: Node):
        for child in node.children:
            self.visit(child)
