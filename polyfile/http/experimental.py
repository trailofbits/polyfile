from abnf.grammars.misc import load_grammar_rules
from abnf.grammars import rfc9110, rfc3986
from . import structured_headers
from abnf import Rule as _Rule
from typing import List, Tuple

rulelist: List[Tuple[str, _Rule]] = [
    ("OWS", rfc9110.Rule("OWS")),
    ("sh-list", structured_headers.Rule("sh-list")),
    ("sh-string", structured_headers.Rule("sh-string")),
    ("sh-decimal", structured_headers.Rule("sh-decimal")),
    ("sh-boolean", structured_headers.Rule("sh-boolean")),
]


@load_grammar_rules(rulelist)
class Rule(_Rule):
    """Request headers defined as 'experimental' by the Mozilla developer documentation, which have partial cross browser support.

    Many of these headers convey client hints (indicated by the CH segment in some, but not all, related header names).

    Most of these also require only simple ABNF to string together the values, so they are collected here for brevity.
    """

    grammar: List[str] = [
        'experimental-header = "Device-Memory:" OWS Device-Memory OWS / "Downlink:" OWS Downlink OWS / "Early-Data:" OWS Early-Data OWS / "ECT:" OWS ECT OWS / "RTT:" OWS RTT OWS / "Save-Data:" OWS Save-Data OWS / "Sec-CH-UA-Arch:" OWS Sec-CH-UA-Arch OWS / "Sec-CH-UA-Bitness:" OWS Sec-CH-UA-Bitness OWS / "Sec-CH-UA-Form-Factor:" OWS Sec-CH-UA-Form-Factor / "Sec-CH-UA-Full-Version:" OWS Sec-CH-UA-Full-Version OWS / "Sec-CH-UA-Full-Version-List:" OWS Sec-CH-UA-Full-Version-List OWS / "Sec-CH-UA-Mobile:" OWS Sec-CH-UA-Mobile OWS / "Sec-CH-UA-Model:" OWS Sec-CH-UA-Model OWS / "Sec-CH-UA-Platform:" OWS Sec-CH-UA-Platform OWS / "Sec-CH-UA-Platform-Version:" OWS Sec-CH-UA-Platform-Version OWS / "Sec-GPC:" OWS Sec-GPC OWS / "Sec-CH-Prefers-Reduced-Motion:" OWS Sec-CH-Prefers-Reduced-Motion OWS',
        # https://www.w3.org/TR/device-memory/#iana-device-memory
        'Device-Memory = "0.25" / "0.5" / "1" / "2" / "4" / "8"',
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Downlink
        # https://wicg.github.io/netinfo/#dom-networkinformation-downlink
        "Downlink = sh-decimal",
        # https://httpwg.org/specs/rfc8470.html#header
        'Early-Data = "1"',
        # https://wicg.github.io/netinfo/#ect-request-header-field
        'ECT = "2g" / "3g" / "4g" / "slow-2g"',
        # https://wicg.github.io/netinfo/#rtt-request-header-field
        "RTT = 1*DIGIT",
        # https://wicg.github.io/savedata/#save-data-request-header-field TODO Structured Headers RFC for sh-list
        'Save-Data = "on" / sh-list',
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Sec-CH-UA
        # TODO sf-list vs sh-list
        "Sec-CH-UA = sh-list",
        # https://wicg.github.io/ua-client-hints/#sec-ch-ua-arch
        "Sec-CH-UA-Arch = sh-string",
        # https://wicg.github.io/ua-client-hints/#sec-ch-ua-bitness
        "Sec-CH-UA-Bitness = sh-string",
        # https://wicg.github.io/ua-client-hints/#sec-ch-ua-form-factor
        "Sec-CH-UA-Form-Factor = sh-string",
        # https://wicg.github.io/ua-client-hints/#sec-ch-ua-full-version
        "Sec-CH-UA-Full-Version = sh-string",
        # https://wicg.github.io/ua-client-hints/#sec-ch-ua-full-version-list
        "Sec-CH-UA-Full-Version-List = sh-list",
        # https://wicg.github.io/ua-client-hints/#sec-ch-ua-mobile
        "Sec-CH-UA-Mobile = sh-boolean",
        # https://wicg.github.io/ua-client-hints/#sec-ch-ua-model
        "Sec-CH-UA-Model = sh-string",
        # https://wicg.github.io/ua-client-hints/#sec-ch-ua-platform
        "Sec-CH-UA-Platform = sh-string",
        # https://wicg.github.io/ua-client-hints/#sec-ch-ua-platform-version
        "Sec-CH-UA-Platform-Version = sh-string",
        # https://wicg.github.io/ua-client-hints/#sec-ch-ua-wow64
        "Sec-CH-UA-WoW64 = sh-boolean",
        # https://privacycg.github.io/gpc-spec/#the-sec-gpc-header-field-for-http-requests
        'Sec-GPC = "1"',
        # https://wicg.github.io/user-preference-media-features-headers/#sec-ch-prefers-reduced-motion
        'Sec-CH-Prefers-Reduced-Motion = "no-preference" / "reduce"',
    ]
