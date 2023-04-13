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

from typing import List, Tuple

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
    ("Accept", rfc9110.Rule("Accept")),
    ("Accept-Encoding", rfc9110.Rule("Accept-Encoding")),
    ("Accept-Language", rfc9110.Rule("Accept-Language")),
    ("Access-Control-Request-Headers", cors.Rule("Access-Control-Request-Headers")),
    ("Age", rfc9111.Rule("Age")),
    ("Allow", rfc9110.Rule("Allow")),
    ("Authorization", rfc9110.Rule("Authorization")),
    ("BWS", rfc9110.Rule("BWS")),
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
    ("OWS", rfc9110.Rule("OWS")),
    ("Proxy-Authenticate", rfc9110.Rule("Proxy-Authenticate")),
    ("Proxy-Authentication-Info", rfc9110.Rule("Proxy-Authentication-Info")),
    ("Proxy-Authorization", rfc9110.Rule("Proxy-Authorization")),
    ("RWS", rfc9110.Rule("RWS")),
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
    ("cookie-string", rfc6265.Rule("cookie-string")),
    ("defacto-header", defacto.Rule("defacto-header")),
    ("deprecated-header", deprecated.Rule("deprecated-header")),
    ("experimental-header", experimental.Rule("experimental-header")),
    # TODO I think these will be useful for body rules?
    # ("parameter", rfc9110.Rule("parameter")),
    # ("parameter-name", rfc9110.Rule("parameter-name")),
    # ("parameter-value", rfc9110.Rule("parameter-value")),
    # ("parameters", rfc9110.Rule("parameters")),
    ("port", rfc3986.Rule("port")),
    ("protocol", rfc9110.Rule("protocol")),
    ("protocol-name", rfc9110.Rule("protocol-name")),
    ("protocol-version", rfc9110.Rule("protocol-version")),
    ("query", rfc3986.Rule("query")),
    ("sh-boolean", structured_headers.Rule("sh-boolean")),
    ("token", rfc9110.Rule("token")),
    ("token68", rfc9110.Rule("token68")),
    ("transfer-coding", rfc9110.Rule("transfer-coding")),
    ("transfer-parameter", rfc9110.Rule("transfer-parameter")),
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
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Messages
        "request = method SP request-path SP protocol CR LF 1*( header CR LF ) *body",
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
        # 'Service-Worker-Navigation-Preload = "true" / token / quoted-string',
        # https://httpwg.org/specs/rfc9112.html#field.transfer-encoding
        'Transfer-Encoding = transfer-coding *( OWS "," OWS transfer-coding )',
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
        "body = 1*( token / token68 / OWS / CR LF )",
    ]


class HttpVisitor(parser.NodeVisitor):
    """The NodeVisitor class requires a visit_Name()
    method which can be called to visit only the section(s) of the AST of interest.
    """

    def __init__(self):
        super().__init__()
        self.content_encoding: List[str] = []
        self.content_length: int
        self.transfer_encoding: str
        self.uri_host: str
        self.uri_port: int
        self.body: str

    def visit_Content_Encoding(self, node: Node):
        for child in node.children:
            print("Content-Encoding CHILD VALUE" + child.value)
            self.visit(child)

    def visit_content_coding(self, node: Node):
        self.content_encoding = node.value

    def visit_Content_Length(self, node: Node):
        self.content_length = int(node.value)

    def visit_TE(self, node: Node):
        for child in node.children:
            self.visit(child)

    def visit_t_codings(self, node: Node):
        self.t_codings.append(node.value)

    def visit_Host(self, node: Node):
        for child in node.children:
            self.visit(child)

    def visit_uri_host(self, node: Node):
        self.uri_host = node.value

    def visit_port(self, node: Node):
        self.uri_port = node.value

    def visit_body(self, node: Node):
        self.body = node.value
