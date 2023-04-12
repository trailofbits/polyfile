from abnf.grammars.misc import load_grammar_rules
from abnf.grammars import rfc9110, rfc3986
from abnf import Rule as _Rule
from typing import List, Tuple

inherited_rulelist: List[Tuple[str, _Rule]] = []


@load_grammar_rules(inherited_rulelist)
class Rule(_Rule):
    """
    Several headers that Mozilla considers 'experimental' rely on ABNF constructions from the Structured Headers draft.
    https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-header-structure-11
    """

    grammar: List[str] = []
