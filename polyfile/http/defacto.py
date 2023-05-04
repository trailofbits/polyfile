from abnf.grammars.misc import load_grammar_rules
from abnf.grammars import rfc9110, rfc3986
from abnf import Rule as _Rule
from typing import List, Tuple

inherited_rulelist: List[Tuple[str, _Rule]] = [
    ("ipv4", rfc3986.Rule("IPv4address")),
    ("ipv6", rfc3986.Rule("IPv6address")),
    ("uri-host", rfc9110.Rule("uri-host")),
]


@load_grammar_rules(inherited_rulelist)
class Rule(_Rule):
    """A place to define *hop-by-hop* headers which do not have an RFC or other standard, but are in common use. As linked, these definitions are primarily based on Mozilla documentation for now.

    These are highly worth parsing and examining since they can be spoofed and are untrustworthy if not added by a reverse proxy on a hop-by-hop request path.

    There are several variants on X-Forwarded-Proto header included.
    """

    grammar: List[str] = [
        'defacto-header = "X-Forwarded-For:" OWS X-Forwarded-For OWS / "X-Forwarded-Host:" OWS X-Forwarded-Host OWS / "X-Forwarded-Proto:" OWS X-Forwarded-Proto OWS / "Front-End-Https:" OWS Front-End-Https OWS / "X-Forwarded-Protocol:" OWS X-Forwarded-Protocol OWS / "X-Forwarded-Ssl:" OWS X-Forwarded-Ssl OWS / "X-Url-Scheme:" OWS X-Url-Scheme OWS',
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For
        'X-Forwarded-For = xff-client *( 0*1SP "," 0*1SP xff-proxy )',
        "xff-client = ipv4 / ipv6",
        "xff-proxy = ipv4 / ipv6",
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-Host - value should be the domain name of the forwarded server
        "X-Forwarded-Host = uri-host",
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-Proto
        'proto = "http" / "https"',
        "X-Forwarded-Proto = proto",
        'Front-End-Https = "on"',
        "X-Forwarded-Protocol = proto",
        'X-Forwarded-Ssl = "on"',
        "X-Url-Scheme = proto",
    ]
