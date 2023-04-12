from abnf.grammars.misc import load_grammar_rules
from abnf.grammars import (
    cors,
    rfc9110,
    rfc5322,
    rfc4647,
    rfc5646,
    rfc3986,
    rfc9111,
    rfc6265,
)
from abnf import Rule, parser, Node

from .http import defacto, deprecated, experimental

from .polyfile import register_parser, InvalidMatch, Submatch

from typing import List, Tuple

# Goals: "parse HTTP"
#   - parse HTTP requests from utf-8 text file(s) with abnf
#   - parse HTTP requests (and streams) from pcaps with dpkt.
#   - maybe use this input to feed abnf parser if it's not a dupe step??
#   - maybe: expand from HTTP 1.1 to HTTP 2 (requires parsing HPACK and QPACK, but might be easy with dpkt, scapy, etc?)

# Textual Input
# ???

# PCAP
# Samples from NetReSec: https://www.netresec.com/?page=PcapFiles
# Sample captures from WireShark: https://wiki.wireshark.org/SampleCaptures
# "the ultimate PCAP" https://weberblog.net/the-ultimate-pcap/

# Note that the rfc9110.py class doesn't include all needed rules other specs and is missing HTTP headers used in practice but not defined in spec.
# NodeVisitor#visit() replaces all dashes with underscores.
# RESPONSE headers in RFC 9110 are NOT included here.
request_rulelist: List[Tuple[str, Rule]] = [
    ("Accept", rfc9110.Rule("Accept")),
    ("Accept-Encoding", rfc9110.Rule("Accept-Encoding")),
    ("Accept-Language", rfc9110.Rule("Accept-Language")),
    ("Access-Control-Request-Method", cors.Rule("Access-Control-Request-Method")),
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
    ("GMT", rfc9110.Rule("GMT")),
    ("HTTP-date", rfc9110.Rule("HTTP-date")),
    ("Host", rfc9110.Rule("Host")),
    ("IMF-fixdate", rfc9110.Rule("IMF-fixdate")),
    ("If-Match", rfc9110.Rule("If-Match")),
    ("If-Modified-Since", rfc9110.Rule("If-Modified-Since")),
    ("If-None-Match", rfc9110.Rule("If-None-Match")),
    ("If-Range", rfc9110.Rule("If-Range")),
    ("If-Unmodified-Since", rfc9110.Rule("If-Unmodified-Since")),
    ("Last-Modified", rfc9110.Rule("Last-Modified")),
    ("Location", rfc9110.Rule("Location")),
    ("Max-Forwards", rfc9110.Rule("Max-Forwards")),
    ("Origin", cors.Rule("Origin")),
    ("OWS", rfc9110.Rule("OWS")),
    ("Proxy-Authenticate", rfc9110.Rule("Proxy-Authenticate")),
    ("Proxy-Authentication-Info", rfc9110.Rule("Proxy-Authentication-Info")),
    ("Proxy-Authorization", rfc9110.Rule("Proxy-Authorization")),
    ("RWS", rfc9110.Rule("RWS")),
    ("Range", rfc9110.Rule("Range")),
    ("Referer", rfc9110.Rule("Referer")),
    ("Retry-After", rfc9110.Rule("Retry-After")),
    ("TE", rfc9110.Rule("TE")),
    ("URI-reference", rfc3986.Rule("URI-reference")),
    ("Upgrade", rfc9110.Rule("Upgrade")),
    ("User-Agent", rfc9110.Rule("User-Agent")),
    ("Via", rfc9110.Rule("Via")),
    ("WWW-Authenticate", rfc9110.Rule("WWW-Authenticate")),
    ("absolute-URI", rfc3986.Rule("absolute-URI")),
    ("absolute-path", rfc9110.Rule("absolute-path")),
    ("acceptable-ranges", rfc9110.Rule("acceptable-ranges")),
    ("asctime-date", rfc9110.Rule("asctime-date")),
    ("auth-param", rfc9110.Rule("auth-param")),
    ("auth-scheme", rfc9110.Rule("auth-scheme")),
    ("authority", rfc3986.Rule("authority")),
    ("challenge", rfc9110.Rule("challenge")),
    ("codings", rfc9110.Rule("codings")),
    ("comment", rfc9110.Rule("comment")),
    ("complete-length", rfc9110.Rule("complete-length")),
    ("connection-option", rfc9110.Rule("connection-option")),
    ("content-coding", rfc9110.Rule("content-coding")),
    ("cookie-string", rfc6265.Rule("cookie-string")),
    ("credentials", rfc9110.Rule("credentials")),
    ("ctext", rfc9110.Rule("ctext")),
    ("date1", rfc9110.Rule("date1")),
    ("date2", rfc9110.Rule("date2")),
    ("date3", rfc9110.Rule("date3")),
    ("day", rfc9110.Rule("day")),
    ("day-name", rfc9110.Rule("day-name")),
    ("day-name-l", rfc9110.Rule("day-name-l")),
    ("defacto-header", defacto.Rule("defacto-header")),
    ("deprecated-header", deprecated.Rule("deprecated-header")),
    ("delay-seconds", rfc9110.Rule("delay-seconds")),
    ("entity-tag", rfc9110.Rule("entity-tag")),
    ("etagc", rfc9110.Rule("etagc")),
    ("expectation", rfc9110.Rule("expectation")),
    ("experimental-header", experimental.Rule("experimental-header")),
    ("field-content", rfc9110.Rule("field-content")),
    ("field-name", rfc9110.Rule("field-name")),
    ("field-value", rfc9110.Rule("field-value")),
    ("field-vchar", rfc9110.Rule("field-vchar")),
    ("first-pos", rfc9110.Rule("first-pos")),
    ("hour", rfc9110.Rule("hour")),
    ("http-URI", rfc9110.Rule("http-URI")),
    ("https-URI", rfc9110.Rule("https-URI")),
    ("incl-range", rfc9110.Rule("incl-range")),
    ("int-range", rfc9110.Rule("int-range")),
    ("language-range", rfc4647.Rule("language-range")),
    ("language-tag", rfc5646.Rule("language-tag")),
    ("last-pos", rfc9110.Rule("last-pos")),
    ("mailbox", rfc5322.Rule("mailbox")),
    ("media-range", rfc9110.Rule("media-range")),
    ("media-type", rfc9110.Rule("media-type")),
    ("method", rfc9110.Rule("method")),
    ("minute", rfc9110.Rule("minute")),
    ("month", rfc9110.Rule("month")),
    ("obs-date", rfc9110.Rule("obs-date")),
    ("obs-text", rfc9110.Rule("obs-text")),
    ("opaque-tag", rfc9110.Rule("opaque-tag")),
    ("other-range", rfc9110.Rule("other-range")),
    ("parameter", rfc9110.Rule("parameter")),
    ("parameter-name", rfc9110.Rule("parameter-name")),
    ("parameter-value", rfc9110.Rule("parameter-value")),
    ("parameters", rfc9110.Rule("parameters")),
    ("partial-URI", rfc9110.Rule("partial-URI")),
    ("path-abempty", rfc3986.Rule("path-abempty")),
    ("port", rfc3986.Rule("port")),
    ("product", rfc9110.Rule("product")),
    ("product-version", rfc9110.Rule("product-version")),
    ("protocol", rfc9110.Rule("protocol")),
    ("protocol-name", rfc9110.Rule("protocol-name")),
    ("protocol-version", rfc9110.Rule("protocol-version")),
    ("pseudonym", rfc9110.Rule("pseudonym")),
    ("qdtext", rfc9110.Rule("qdtext")),
    ("query", rfc3986.Rule("query")),
    ("quoted-pair", rfc9110.Rule("quoted-pair")),
    ("quoted-string", rfc9110.Rule("quoted-string")),
    ("qvalue", rfc9110.Rule("qvalue")),
    ("range-resp", rfc9110.Rule("range-resp")),
    ("range-set", rfc9110.Rule("range-set")),
    ("range-spec", rfc9110.Rule("range-spec")),
    ("range-unit", rfc9110.Rule("range-unit")),
    ("ranges-specifier", rfc9110.Rule("ranges-specifier")),
    ("received-by", rfc9110.Rule("received-by")),
    ("received-protocol", rfc9110.Rule("received-protocol")),
    ("relative-part", rfc3986.Rule("relative-part")),
    ("rfc850-date", rfc9110.Rule("rfc850-date")),
    ("second", rfc9110.Rule("second")),
    ("segment", rfc3986.Rule("segment")),
    ("subtype", rfc9110.Rule("subtype")),
    ("suffix-length", rfc9110.Rule("suffix-length")),
    ("suffix-range", rfc9110.Rule("suffix-range")),
    ("t-codings", rfc9110.Rule("t-codings")),
    ("tchar", rfc9110.Rule("tchar")),
    ("time-of-day", rfc9110.Rule("time-of-day")),
    ("token", rfc9110.Rule("token")),
    ("token68", rfc9110.Rule("token68")),
    ("transfer-coding", rfc9110.Rule("transfer-coding")),
    ("transfer-parameter", rfc9110.Rule("transfer-parameter")),
    ("type", rfc9110.Rule("type")),
    ("unsatisfied-range", rfc9110.Rule("unsatisfied-range")),
    ("uri-host", rfc3986.Rule("host")),
    ("weak", rfc9110.Rule("weak")),
    ("weight", rfc9110.Rule("weight")),
    ("year", rfc9110.Rule("year")),
]


@load_grammar_rules(request_rulelist)
class Http11RequestGrammar(Rule):
    # todo ensure no response headers are allowed in the request grammar
    """
     RFC 2616: The following HTTP/1.1 headers are hop-by-hop headers:
       - Connection
       - Keep-Alive
       - Proxy-Authenticate
       - Proxy-Authorization
       - TE
       - Trailers
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
        "request = method SP absolute-path SP protocol CR LF 1*( header CR LF )",
        "header = hop-by-hop-header / end-to-end-header / caching-header / deprecated-header / experimental-header",
        # Added by proxies (forward and reverse) generally; mainly sourced from RFC 9110; not including response headers
        'hop-by-hop-header = "Connection:" OWS Connection OWS / "Forwarded:" OWS Forwarded OWS / "Keep-Alive:" OWS Keep-Alive OWS / "Proxy-Authenticate:" OWS Proxy-Authenticate OWS / "Proxy-Authorization:" OWS Proxy-Authorization OWS / "TE:" OWS TE OWS / "Trailers:" OWS Trailers OWS / "Transfer-Encoding:" OWS Transfer-Encoding OWS / "Upgrade:" OWS Upgrade OWS / "Via:" OWS Via OWS / defacto-header',
        # Mainly sourced from RFC 9110 (but also includes eg RFC 6265 for cookies, and others); not including response headers
        'end-to-end-header = "Accept:" OWS Accept OWS / "Accept-Encoding:" OWS Accept-Encoding OWS / "Accept-Language:" OWS Accept-Language OWS / "Access-Control-Request-Headers:" OWS Access-Control-Request-Headers OWS / Access-Control-Request-Method:" OWS Access-Control-Request-Method OWS / "Authorization:" OWS Authorization OWS /  "Content-Encoding:" OWS Content-Encoding OWS / "Content-Language:" OWS Content-Language OWS / "Content-Length:" OWS Content-Length OWS / "Content-Range:" OWS Content-Range OWS / "Content-Type:" OWS Content-Type OWS / "Cookie:" OWS cookie-string OWS / "Date:" OWS Date OWS / "Expect:" OWS Expect OWS / "From:" OWS From OWS / "Host:" OWS Host OWS / "If-Match:" OWS If-Match OWS / "If-Modified-Since:" OWS If-Modified-Since OWS / "If-None-Match:" OWS If-None-Match OWS / "If-Range:" OWS If-Range OWS / "If-Unmodified-Since:" OWS If-Unmodified-Since OWS / "Location:" OWS Location OWS / "Max-Forwards:" OWS Max-Forwards OWS / "Origin:" OWS Origin OWS / "Proxy-Authentication-Info:" OWS Proxy-Authentication-Info OWS /  / "Range:" OWS Range OWS / "Referer:" OWS Referer OWS / "Retry-After:" OWS Retry-After OWS / "Sec-CH-UA:" OWS Sec-CH-UA OWS / "Sec-Fetch-Dest:" OWS Sec-Fetch-Dest OWS / "Sec-Fetch-Mode:" OWS Sec-Fetch-Mode OWS / "Sec-Fetch-Site:" OWS Sec-Fetch-Site OWS / "Sec-Fetch-User:" OWS Sec-Fetch-User OWS / "Service-Worker-Navigation-Preload:" OWS Service-Worker-Navigation-Preload OWS / "Upgrade-Insecure-Requests:" OWS Upgrade-Insecure-Requests OWS / "User-Agent:" OWS User-Agent OWS / "Want-Digest:" OWS Want-Digest OWS / "WWW-Authenticate:" OWS WWW-Authenticate OWS',
        # rfc 9111 (caching) headers follow
        'caching-header = "Age: " OWS Age OWS / "Cache-Control:" OWS Cache-Control OWS',
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
        "Sec-Fetch-User = ?1",
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Service-Worker-Navigation-Preload
        'Service-Worker-Navigation-Preload = "true" / token / quoted-string',
        # https://httpwg.org/specs/rfc9112.html#field.transfer-encoding
        # TODO express without the '#' if needed
        "Transfer-Encoding = #transfer-coding",
        # https://w3c.github.io/webappsec-upgrade-insecure-requests/#preference
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Upgrade-Insecure-Requests
        'Upgrade-Insecure-Requests = "1"',
        # https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-digest-headers#section-4
        # https://http.dev/want-digest
        # TODO express without the '#' if needed
        "Want-Digest = 1#want-digest-value",
        'want-digest-value = digest-algorithm [ ";" "q" "=" qvalue]',
        'qvalue = ( "0" [ "." 0*1DIGIT ] ) / ( "1" [ "." 0*1( "0" ) ] )',
        # https://www.ietf.org/archive/id/draft-ietf-httpbis-digest-headers-04.html#section-5
        'digest-algorithm = "sha-256" / "sha-512" / "md5" / "sha" / "unixsum" / "unixcksum" / "id-sha-512" / "id-sha-256" / token',
    ]


class HttpVisitor(parser.NodeVisitor):
    """The NodeVisitor class requires a visit_Name()
    method which can be called to visit only the section(s) of the AST of interest.
    """

    def __init__(self):
        super().__init__()
        self.content_coding: List[str] = []
        self.content_length: int
        self.t_codings: List[str] = []
        self.uri_host: str
        self.uri_port: int

    def visit_Content_Encoding(self, node: Node):
        """
        Walks the section of the AST which is defined by the following RFC 9110 ABNF:
        Content-Encoding  = [ content-coding *( OWS "," OWS content-coding ) ]
        content-coding    = token
        token             = 1*tchar
        tchar             = "!" / "#" / "$" / "%" / "&" / "'" / "*" / "+" / "-" / "." / "^" / "_" / "`" / "|" / "~" / DIGIT / ALPHA
        OWS               = *( SP / HTAB )

        SP                =  %x20
        HTAB              =  %x09 ; horizontal tab
        DIGIT             =  %x30-39 ; 0-9
        ALPHA             =  %x41-5A / %x61-7A ; A-Z / a-z
        """
        for child in node.children:
            self.visit(child)

    def visit_content_coding(self, node: Node):
        self.content_coding.append(node.value)

    def visit_Content_Length(self, node: Node):
        """
        Walks the section of the AST which is defined by the following RFC 9110 ABNF:
        Content-Length    = 1*DIGIT
        DIGIT             =  %x30-39 ; 0-9
        """
        self.content_length = int(node.value)

    def visit_TE(self, node: Node):
        """
        Walks the section of the AST which is defined by the following RFC 9110 ABNF:
        TE                 = #t-codings
        t-codings          = "trailers" / ( transfer-coding [ weight ] )
        transfer-coding    = token *( OWS ";" OWS transfer-parameter )
        transfer-parameter = token BWS "=" BWS ( token / quoted-string )
        token             = 1*tchar
        tchar             = "!" / "#" / "$" / "%" / "&" / "'" / "*" / "+" / "-" / "." / "^" / "_" / "`" / "|" / "~" / DIGIT / ALPHA
        weight = OWS ";" OWS "q=" qvalue
        BWS = OWS
        OWS = *( SP / HTAB )
        SP                =  %x20
        HTAB              =  %x09 ; horizontal tab
        DIGIT             =  %x30-39 ; 0-9
        ALPHA             =  %x41-5A / %x61-7A ; A-Z / a-z
        """
        for child in node.children:
            self.visit(child)

    def visit_t_codings(self, node: Node):
        self.t_codings.append(node.value)

    def visit_Host(self, node: Node):
        """
        Walks the section of the AST which 1. is defined by the following RFC 9110 ABNF:
        Host     = uri-host [ ":" port ]
        uri-host = <host, see [URI], Section 3.2.2>
        port     = <port, see [URI], Section 3.2.3>

        (The definitions of "URI-reference", "absolute-URI", "relative-part", "authority", "port", "host", "path-abempty", "segment", and "query" are adopted from the URI generic syntax.)

        and 2. by the following RFC 3986 ABNF:
        host          = IP-literal / IPv4address / reg-name
        IP-literal    = "[" ( IPv6address / IPvFuture  ) "]"
        IPv4address   = dec-octet "." dec-octet "." dec-octet "." dec-octet
        IPvFuture     = "v" 1*HEXDIG "." 1*( unreserved / sub-delims / ":" )
        IPv6address   = 6( h16 ":" ) ls32
                   / "::" 5( h16 ":" ) ls32
                   / [ h16 ] "::" 4( h16 ":" ) ls32
                   / [ *1( h16 ":" ) h16 ] "::" 3( h16 ":" ) ls32
                   / [ *2( h16 ":" ) h16 ] "::" 2( h16 ":" ) ls32
                   / [ *3( h16 ":" ) h16 ] "::" h16 ":" ls32
                   / [ *4( h16 ":" ) h16 ] "::" ls32
                   / [ *5( h16 ":" ) h16 ] "::" h16
                   / [ *6( h16 ":" ) h16 ] "::"
        dec-octet     = DIGIT                 ; 0-9
                   / %x31-39 DIGIT         ; 10-99
                   / "1" 2DIGIT            ; 100-199
                   / "2" %x30-34 DIGIT     ; 200-249
                   / "25" %x30-35          ; 250-255

        reg-name      = *( unreserved / pct-encoded / sub-delims )
        pct-encoded   = "%" HEXDIG HEXDIG

        unreserved    = ALPHA / DIGIT / "-" / "." / "_" / "~"
        sub-delims    = "!" / "$" / "&" / "'" / "(" / ")" / "*" / "+" / "," / ";" / "="
        port  = *DIGIT
        HEXDIG            = DIGIT / "A" / "B" / "C" / "D" / "E" / "F"
        DIGIT             =  %x30-39 ; 0-9
        ALPHA             =  %x41-5A / %x61-7A ; A-Z / a-z
        """
        for child in node.children:
            self.visit(child)

    def visit_uri_host(self, node: Node):
        self.uri_host = node.value

    def visit_port(self, node: Node):
        self.uri_port = node.value
