from abnf.grammars.misc import load_grammar_rules
from abnf.grammars import rfc9110, rfc3986
from abnf import Rule as _Rule
from typing import List, Tuple

rulelist: List[Tuple[str, _Rule]] = [
    ("OWS", rfc9110.Rule("OWS")),
]


@load_grammar_rules(rulelist)
class Rule(_Rule):
    """
    Several headers that Mozilla considers 'experimental' rely on ABNF constructions from RFC 8941: Structured Headers.

    https://datatracker.ietf.org/doc/html/rfc8941
    Also possibly of note: https://datatracker.ietf.org/doc/html/rfc8941#section-4.2
    """

    grammar: List[str] = [
        'sh-list        = list-member *( OWS "," OWS list-member )',
        "list-member    = sh-item / inner-list",
        'inner-list     = "(" *SP [ sh-item *( 1*SP sh-item ) *SP ] ")" *parameter',
        "sh-item        = bare-item parameters",
        "bare-item      = sh-integer / sh-decimal / sh-string / sh-token / sh-binary / sh-boolean",
        'sh-integer     = ["-"] 1*15DIGIT',
        'sh-decimal     = ["-"] 1*12DIGIT "." 1*3DIGIT',
        "sh-string      = DQUOTE *chr DQUOTE",
        "chr            = unescaped / escaped",
        "unescaped      = %x20-21 / %x23-5B / %x5D-7E",
        'escaped        = "\\" ( DQUOTE / "\\" )',
        'sh-token       = ( ALPHA / "*" ) *( tchar / ":" / "/" )',
        'sh-binary      = ":" *(base64) ":"',
        'base64         = ALPHA / DIGIT / "+" / "/" / "="',
        'sh-boolean     = "?" boolean',
        'boolean        = "0" / "1"',
        # Note that parameters are ordered as serialized, and parameter keys cannot contain uppercase letters. A parameter is separated from its Item or Inner List and other parameters by a semicolon.
        'parameters    = *( ";" *SP parameter )',
        'parameter     = param-key [ "=" param-value ]',
        "param-key     = key",
        'key           = ( lcalpha / "*" ) *( lcalpha / DIGIT / "_" / "-" / "." / "*" )',
        "lcalpha       = %x61-7A ; a-z",
        "param-value   = bare-item",
        'sh-dictionary  = dict-member *( OWS "," OWS dict-member )',
        'dict-member    = member-key ( parameters / ( "=" member-value ))',
        "member-key     = key",
        "member-value   = sh-item / inner-list",
    ]
