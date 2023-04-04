from abnf.grammars.misc import load_grammar_rules
from abnf.grammars import rfc9110, rfc5322, rfc4647, rfc5646, rfc3986
from abnf import Rule, parser, Node

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

# We recycle the majority of the RFC 9110 rule list here, since the rfc9110.py
# class doesn't make needed the rule substitutions from other specs.
# Note NodeVisitor#visit() replaces all dashes with underscores.
rulelist: List[Tuple[str, Rule]] = [
    ("Accept", rfc9110.Rule("Accept")),
    ("Accept-Charset", rfc9110.Rule("Accept-Charset")),
    ("Accept-Encoding", rfc9110.Rule("Accept-Encoding")),
    ("Accept-Language", rfc9110.Rule("Accept-Language")),
    ("Accept-Ranges", rfc9110.Rule("Accept-Ranges")),
    ("Allow", rfc9110.Rule("Allow")),
    ("Authentication-Info", rfc9110.Rule("Authentication-Info")),
    ("Authorization", rfc9110.Rule("Authorization")),
    ("BWS", rfc9110.Rule("BWS")),
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
    ("OWS", rfc9110.Rule("OWS")),
    ("Proxy-Authenticate", rfc9110.Rule("Proxy-Authenticate")),
    ("Proxy-Authentication-Info", rfc9110.Rule("Proxy-Authentication-Info")),
    ("Proxy-Authorization", rfc9110.Rule("Proxy-Authorization")),
    ("RWS", rfc9110.Rule("RWS")),
    ("Range", rfc9110.Rule("Range")),
    ("Referer", rfc9110.Rule("Referer")),
    ("Retry-After", rfc9110.Rule("Retry-After")),
    ("Server", rfc9110.Rule("Server")),
    ("TE", rfc9110.Rule("TE")),
    ("Trailer", rfc9110.Rule("Trailer")),
    ("URI-reference", rfc3986.Rule("URI-reference")),
    ("Upgrade", rfc9110.Rule("Upgrade")),
    ("User-Agent", rfc9110.Rule("User-Agent")),
    ("Vary", rfc9110.Rule("Vary")),
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
    ("credentials", rfc9110.Rule("credentials")),
    ("ctext", rfc9110.Rule("ctext")),
    ("date1", rfc9110.Rule("date1")),
    ("date2", rfc9110.Rule("date2")),
    ("date3", rfc9110.Rule("date3")),
    ("day", rfc9110.Rule("day")),
    ("day-name", rfc9110.Rule("day-name")),
    ("day-name-l", rfc9110.Rule("day-name-l")),
    ("delay-seconds", rfc9110.Rule("delay-seconds")),
    ("entity-tag", rfc9110.Rule("entity-tag")),
    ("etagc", rfc9110.Rule("etagc")),
    ("expectation", rfc9110.Rule("expectation")),
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
    ("media-type", rfc9110.Rule("method")),
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


@load_grammar_rules(rulelist)
class Grammar(Rule):
    # add rules that cannot be imported here
    grammar: List[str] = [
        "headers = Accept / Accept-Charset / Accept-Encoding / Accept-Language / Accept-Ranges / Allow / Authentication-Info / Authorization / Connection / Content-Encoding / Content-Language / Content-Length / Content-Location / Content-Range / Content-Type / Date / ETag / Expect / From / GMT / HTTP-date / Host / IMF-fixdate / If-Match / If-Modified-Since / If-None-Match / If-Range / If-Unmodified-Since / Last-Modified / Location / Max-Forwards / Proxy-Authenticate / Proxy-Authentication-Info / Proxy-Authorization / Range / Referer / Retry-After / Server / TE / Trailer / Upgrade / User-Agent / Vary / Via / WWW-Authenticate"
    ]


class HttpVisitor(parser.NodeVisitor):
    """The NodeVisitor class requires a visit_Name()
    method which can be called to visit only the section(s) of the AST of interest.
    """

    def __init__(self):
        super().__init__()
        self.content_coding: List[str] = []
        self.content_length: int
        self.transfer_coding: str
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
        self.t_codings = node.value

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
