from abnf.grammars.misc import load_grammar_rules
from abnf.grammars import rfc9110, rfc3986, rfc9111
from abnf import Rule as _Rule
from typing import List, Tuple

inherited_rulelist: List[Tuple[str, _Rule]] = [
    ("Accept-Charset", rfc9110.Rule("Accept-Charset")),
    ("Authentication-Info", rfc9110.Rule("Authentication-Info")),
    ("token", rfc9110.Rule("token")),
    ("quoted-string", rfc9110.Rule("quoted-string")),
    ("HTTP-date", rfc9110.Rule("HTTP-date")),
    ("Host", rfc9110.Rule("Host")),
]


@load_grammar_rules(inherited_rulelist)
class Rule(_Rule):
    """
    Request headers which are in general deprecated by modern browsers, but may still be included from spoofed user agents or unusual user agents.
    """

    grammar: List[str] = [
        'deprecated-header = "Accept-Charset:" OWS Accept-Charset OWS / "Authentication-Info:" OWS Authentication-Info OWS / "DNT:" OWS DNT OWS / "DPR:" OWS DPR OWS / "Expect-CT:" OWS Expect-CT OWS / "Pragma:" OWS Pragma OWS / "Viewport-Width:" OWS Viewport-Width OWS / "Warning:" OWS Warning OWS / "Width:" OWS Width OWS',
        # https://www.w3.org/TR/tracking-dnt/#dnt-header-field
        'DNT = ( "0" / "1" ) *DNT-extension',
        # DNT-extension excludes CTL, SP, DQUOTE, comma, backslash
        "DNT-extension = %x21 / %x23-2B / %x2D-5B / %x5D-7E",
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/DPR
        'DPR = 1*DIGIT "." 1*DIGIT',
        # https://www.rfc-editor.org/rfc/rfc9163#section-2.1
        'Expect-CT           = expect-ct-directive *( OWS "," OWS expect-ct-directive )',
        'expect-ct-directive = directive-name [ "=" directive-value ]',
        "directive-name      = token",
        "directive-value     = token / quoted-string",
        # https://httpwg.org/specs/rfc9111.html#field.pragma
        'Pragma = "no-cache"',
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Viewport-Width
        # The width of the user's viewport in CSS pixels, rounded up to the nearest integer.
        "Viewport-Width = 1*DIGIT",
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Warning
        "Warning = warn-code warn-agent warn-text *warn-date",
        # https://www.iana.org/assignments/http-warn-codes/http-warn-codes.xhtml
        'warn-code = "110" / "111" / "112" / "113" / "199" / "214" / "299"',
        "warn-agent = Host / pseudonym",
        "warn-text = quoted-string",
        "warn-date = HTTP-date",
        "pseudonym = token",
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Width
        # The width of the resource in physical pixels, rounded up to the nearest integer.
        "Width = 1*DIGIT",
    ]
