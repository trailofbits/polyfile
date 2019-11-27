from .ebnf import char_rule, Token, CompoundToken, star, plus, minus, named_rule, optional, rule_sequence, star_until, reject_if, production, string_match
from .fileutils import FileStream
from .polyfile import InvalidMatch, Match, submatcher
from .logger import getStatusLogger

log = getStatusLogger("XML")


def whitespace(file_stream: FileStream):
    start = file_stream.tell()
    token = bytearray()
    while file_stream.peek(1) in (b'\x20', b'\x09', b'\x0D', b'\x0A'):
        token.append(file_stream.read(1)[0])
    if token:
        return Token(token, start)
    else:
        return None


@char_rule
def char(b: int):
    return (0x1 <= b <= 0xD7FF) or (0xE000 <= b <= 0xFFFD) or (0x10000 <= b <= 0x10FFFF)


@char_rule
def ascii_char(b: int):
    return (ord('A') <= b <= ord('Z')) or (ord('a') <= b <= ord('c'))


@char_rule
def encoding_char(b: int):
    return (ord('A') <= b <= ord('Z')) or (ord('a') <= b <= ord('z')) or (ord('0') <= b <= ord('9')) \
           or b == ord('.') or b == ord('_')


@char_rule
def restricted_char(b: int):
    return (0x1 <= b <= 0x8) or (0xB <= b <= 0xC) or (0xE <= b <= 0x1F) or (0x7F <= b <= 0x84) or (0x86 <= b <= 0x9F)


def name_start_char_predicate(b: int):
    return b == ord(':') or (ord('A') <= b <= ord('Z')) or b == ord('_') or (ord('a') <= b <= ord('z')) \
        or (0xC0 <= b <= 0xD6) or (0xD8 <= b <= 0xF6) or (0xF8 <= b <= 0x2FF) or (0x370 <= b <= 0x37D) \
        or (0x37F <= b <= 0x1FFF) or (0x200C <= b <= 0x200D) or (0x2070 <= b <= 0x218F) or (0x2C00 <= b <= 0x2FEF) \
        or (0x3001 <= b <= 0xD7FF) or (0xF900 <= b <= 0xFDCF) or (0xFDF0 <= b <= 0xFFFD) or (0x10000 <= b <= 0xEFFFF)


@char_rule
def name_start_char(b: int):
    return name_start_char_predicate(b)


@char_rule
def name_char(b: int):
    return name_start_char_predicate(b) or b in (ord('-'), ord('.'), 0xB7) or (ord('0') <= b <= ord('9')) \
        or (0x0300 <= b <= 0x036F) or (0x203F <= b <= 0x2040)


@char_rule
def space(b: int):
    return b == 0x20


@char_rule
def digit(b: int):
    return ord('0') <= b <= ord('9')


@char_rule
def hex_digit(b: int):
    return (ord('0') <= b <= ord('9')) or (ord('a') <= b <= ord('f')) or (ord('A') <= b <= ord('F'))


@char_rule
def operator(b: int):
    return b in b"-'()+,./:=?;!*#@$_%"


name = rule_sequence(name_start_char, star(name_char), token_type='Name')
names = rule_sequence(name, star(rule_sequence(space, name)), token_type='Names')
nm_token = plus(name_char, token_type='Nmtoken')
nm_tokens = rule_sequence(nm_token, star(rule_sequence(space, name)), token_type='Nmtokens')

# CharRef	   ::=   	'&#' [0-9]+ ';' | '&#x' [0-9a-fA-F]+ ';'
char_ref = production(
    ['&#', plus(digit), ';'],
    ['&#x', plus(hex_digit), ';'],
    token_type='CharRef'
)
# EntityRef	   ::=   	'&' Name ';'
entity_ref = rule_sequence('&', name, ';', token_type='EntityRef')
reference = production(char_ref, entity_ref, token_type='EntityRef')
pe_reference = rule_sequence('%', name, ';', token_type='PEReference')

# EntityValue	   ::=   	'"' ([^%&"] | PEReference | Reference)* '"'
# |  "'" ([^%&'] | PEReference | Reference)* "'"
entity_value = production(
    ['"', star(production("^%&", pe_reference, reference)), '"'],
    ["'", star(production("^%&", pe_reference, reference)), "'"],
    token_type='EntityValue'
)
# AttValue	   ::=   	'"' ([^<&"] | Reference)* '"'
# |  "'" ([^<&'] | Reference)* "'"
att_value = production(
    ['"', star(production("^<&", reference)), '"'],
    ["'", star(production("^<&", reference)), "'"],
    token_type='AttValue'
)
# SystemLiteral	   ::=   	('"' [^"]* '"') | ("'" [^']* "'")
system_literal = production(
    ['"', star('^"'), '"'],
    ["'", star("^'"), "'"],
    token_type='SystemLiteral'
)
# PubidChar	   ::=   	#x20 | #xD | #xA | [a-zA-Z0-9] | [-'()+,./:=?;!*#@$_%]
pubid_char = production(
    space,
    '\x0D',
    '\x0A',
    hex_digit,
    operator
)
# PubidLiteral	   ::=   	'"' PubidChar* '"' | "'" (PubidChar - "'")* "'"
pubid_literal = production(
    ['"', star(pubid_char), '"'],
    ["'", star(minus(pubid_char, "'")), "'"],
    token_type='PubidLiteral'
)
# CharData	   ::=   	[^<&]* - ([^<&]* ']]>' [^<&]*)
char_data = rule_sequence(
    reject_if(
        star('^<&'),
        lambda t: b']]>' in t.text
    )
)


# Comment	   ::=   	'<!--' ((Char - '-') | ('-' (Char - '-')))* '-->'
def comment(file_stream: FileStream):
    start = file_stream.tell()
    if file_stream.read(4) != b'<!--':
        file_stream.seek(start)
        return None
    contents = bytearray()
    while True:
        b = file_stream.read(1)
        if len(b) == 0:
            break
        contents.append(b[0])
        if bytes(contents[-3:]) == b'-->' and (len(contents) == 3 or contents[-4] != ord('-')):
            break
    return Token(b'<!--' + bytes(contents), start, token_type='Comment')


# PITarget	   ::=   	Name - (('X' | 'x') ('M' | 'm') ('L' | 'l'))
pi_target = minus(name, [production('X', 'x'), production('M', 'm'), production('L', 'l')])
# PI	   ::=   	'<?' PITarget (S (Char* - (Char* '?>' Char*)))? '?>'
pi = rule_sequence(
    '<?',
    pi_target,
    optional([
        whitespace,
        star_until(char, '?>')
    ]),
    '?>',
    token_type='PI'
)

cd_end = string_match(']]>')
c_data = star_until(char, ']]>')
cd_start = string_match('<![CDATA[')
cd_sect = rule_sequence(cd_start, c_data, cd_end, token_type='CDSect')

misc = production(comment, pi, whitespace)
version_num = rule_sequence(plus(digit), optional(['.', plus(digit)]), 'VersionNum')
eq = rule_sequence(optional(whitespace), '=', optional(whitespace))
version_info = rule_sequence(whitespace, 'version', eq, production(
    ["'", version_num, "'"],
    ['"', version_num, '"'],
), token_type='VersionInfo')

# EncName	   ::=   	[A-Za-z] ([A-Za-z0-9._] | '-')*
enc_name = rule_sequence(
    ascii_char,
    star(
        production(
            encoding_char,
            '-'
        )
    ),
    token_type='EncName'
)
# EncodingDecl	   ::=   	S 'encoding' Eq ('"' EncName '"' | "'" EncName "'" )
encoding_decl = rule_sequence(
    whitespace,
    'encoding',
    eq,
    production(
        ['"', enc_name, '"'],
        ["'", enc_name, "'"]
    ),
    token_type='EncodingDecl'
)

# SDDecl	   ::=   	S 'standalone' Eq (("'" ('yes' | 'no') "'") | ('"' ('yes' | 'no') '"'))
sd_decl = rule_sequence(
    whitespace,
    'standalone',
    eq,
    production(
        ["'", production('yes', 'no'), "'"],
        ['"', production('yes', 'no'), '"']
    ),
    token_type='SDDecl'
)

xml_decl = rule_sequence(
    '<?xml',
    version_info,
    optional(encoding_decl),
    optional(sd_decl),
    optional(whitespace),
    '?>',
    token_type='XMLDecl'
)

# DeclSep	   ::=   	PEReference | S
decl_sep = production(pe_reference, whitespace, token_type='decl_sep')


def cp_ref(*args, **kwargs):
    global cp
    cp(*args, **kwargs)


# choice	   ::=   	'(' S? cp ( S? '|' S? cp )+ S? ')'
choice = rule_sequence(
    '(',
    optional(whitespace),
    cp_ref,
    plus(production(optional(whitespace), [optional(whitespace), cp_ref])),
    optional(whitespace),
    ')',
    token_type='choice'
)

# seq	   ::=   	'(' S? cp ( S? ',' S? cp )* S? ')'
seq = rule_sequence(
    '(',
    optional(whitespace),
    cp_ref,
    star(production(optional(whitespace), '?', optional(whitespace), cp_ref)),
    optional(whitespace),
    ')',
    token_type='seq'
)

# cp	   ::=   	(Name | choice | seq) ('?' | '*' | '+')?
cp = rule_sequence(
    production(name, choice, seq),
    optional(production('?', '*', '+'))
)

# children	   ::=   	(choice | seq) ('?' | '*' | '+')?
children = rule_sequence(
    production(choice, seq),
    optional(['?', '*', '+']),
    token_type='children'
)

# Mixed	   ::=   	'(' S? '#PCDATA' (S? '|' S? Name)* S? ')*' | '(' S? '#PCDATA' S? ')'
mixed = production(
    [
        '(', optional(whitespace), '#PCDATA', star([optional(whitespace), '|', optional(whitespace), name]),
        optional(whitespace), ')*'
    ], [
        '(', optional(whitespace), '#PCDATA', optional(whitespace), ')'
    ],
    token_type='Mixed'
)

# contentspec	   ::=   	'EMPTY' | 'ANY' | Mixed | children
contentspec = production(
    'EMPTY',
    'ANY',
    mixed,
    children,
    token_type='contentspec'
)

# elementdecl	   ::=   	'<!ELEMENT' S Name S contentspec S? '>'
elementdecl = rule_sequence(
    '<!ELEMENT',
    whitespace,
    name,
    whitespace,
    contentspec,
    optional(whitespace),
    '>',
    token_type='elementdecl'
)

string_type = string_match('CDATA')

tokenized_type = production(
    'ID',
    'IDREF',
    'IDREFS',
    'ENTITY',
    'ENTITIES',
    'NMTOKEN',
    'NMTOKENS',
    token_type='TokenizedType'
)

# NotationType	   ::=   	'NOTATION' S '(' S? Name (S? '|' S? Name)* S? ')'
notation_type = rule_sequence(
    'NOTATION',
    whitespace,
    '(',
    optional(whitespace),
    name,
    star([
        optional(whitespace),
        '|',
        optional(whitespace),
        name
    ]),
    ')',
    token_type='NotationType'
)

# Enumeration	   ::=   	'(' S? Nmtoken (S? '|' S? Nmtoken)* S? ')'
enumeration = rule_sequence(
    '(',
    optional(whitespace),
    nm_token,
    star([
        optional(whitespace),
        '|',
        optional(whitespace),
        nm_token
    ]),
    optional(whitespace),
    ')',
    token_type='Enumeration'
)

# DefaultDecl	   ::=   	'#REQUIRED' | '#IMPLIED'
# | (('#FIXED' S)? AttValue)
default_decl = production(
    '#REQUIRED',
    '#IMPLIED',
    [
        optional(['#FIXED', whitespace]),
        att_value
    ],
    token_type='DefaultDecl'
)

# EnumeratedType	   ::=   	NotationType | Enumeration
enumerated_type = production(
    notation_type,
    enumeration
)

# AttType	   ::=   	StringType | TokenizedType | EnumeratedType
att_type = production(
    string_type,
    tokenized_type,
    enumerated_type,
    token_type='AttType'
)

# AttDef	   ::=   	S Name S AttType S DefaultDecl
att_def = rule_sequence(
    whitespace,
    name,
    whitespace,
    att_type,
    whitespace,
    default_decl,
    token_type='AttDef'
)

# AttlistDecl	   ::=   	'<!ATTLIST' S Name AttDef* S? '>'
attlist_decl = rule_sequence(
    '<!ATTLIST',
    whitespace,
    name,
    star(att_def),
    optional(whitespace),
    '>',
    token_type='AttlistDecl'
)

# ExternalID	   ::=   	'SYSTEM' S SystemLiteral
# | 'PUBLIC' S PubidLiteral S SystemLiteral
external_id = production(
    [
        'SYSTEM',
        whitespace,
        system_literal
    ], [
        'PUBLIC',
        whitespace,
        pubid_literal,
        whitespace,
        system_literal
    ],
    token_type='external_id'
)

# NDataDecl	   ::=   	S 'NDATA' S Name
n_data_decl = rule_sequence(
    whitespace,
    'NDATA',
    whitespace,
    name,
    token_type='NDataDecl'
)

# PEDef	   ::=   	EntityValue | ExternalID
pe_def = production(entity_value, external_id)

# EntityDef	   ::=   	EntityValue | (ExternalID NDataDecl?)
entity_def = production(
    entity_value,
    [external_id, optional(n_data_decl)],
    token_type='EntityDef'
)

# PEDecl	   ::=   	'<!ENTITY' S '%' S Name S PEDef S? '>'
pe_decl = rule_sequence(
    '<!ENTITY',
    whitespace,
    '%',
    whitespace,
    name,
    whitespace,
    pe_def,
    optional(whitespace),
    '>',
    token_type='PEDecl'
)

# GEDecl	   ::=   	'<!ENTITY' S Name S EntityDef S? '>'
ge_decl = rule_sequence(
    '<!ENTITY',
    whitespace,
    name,
    whitespace,
    entity_def,
    optional(whitespace),
    '>',
    token_type='GEDecl'
)

# PublicID	   ::=   	'PUBLIC' S PubidLiteral
public_id = rule_sequence('PUBLIC', whitespace, pubid_literal)

# NotationDecl	   ::=   	'<!NOTATION' S Name S (ExternalID | PublicID) S? '>'
notation_decl = rule_sequence(
    '<!NOTATION',
    whitespace,
    name,
    whitespace,
    production(external_id, public_id),
    optional(whitespace),
    '>',
    token_type='NotationDecl'
)

entity_decl = production(ge_decl, pe_decl)

# markupdecl	   ::=   	elementdecl | AttlistDecl | EntityDecl | NotationDecl | PI | Comment
markupdecl = production(
    elementdecl,
    attlist_decl,
    entity_decl,
    notation_decl,
    pi,
    comment,
    token_type='markupdecl'
)

# intSubset	   ::=   	(markupdecl | DeclSep)*
int_subset = star(markupdecl, decl_sep)

# doctypedecl	   ::=   	'<!DOCTYPE' S Name (S ExternalID)? S? ('[' intSubset ']' S?)? '>'
doctypedecl = rule_sequence(
    '<!DOCTYPE',
    whitespace,
    name,
    optional([whitespace, external_id]),
    optional(whitespace),
    optional(['[', int_subset, ']', optional(whitespace)]),
    '>',
    token_type='doctypedecl'
)

prolog = rule_sequence(
    xml_decl,
    star(misc),
    optional([doctypedecl, star(misc)])
)

# Attribute	   ::=   	Name Eq AttValue
attribute = rule_sequence(name, eq, att_value)

# EmptyElemTag	   ::=   	'<' Name (S Attribute)* S? '/>'
empty_elem_tag = rule_sequence(
    '<', name, star([whitespace, attribute]), optional(whitespace), '/>',
    token_type='EmptyElemTag'
)

# STag	   ::=   	'<' Name (S Attribute)* S? '>'
stag = rule_sequence('<', name, star(whitespace, attribute), optional(whitespace), '>', token_type='STag')

# ETag	   ::=   	'</' Name S? '>'
etag = rule_sequence('</', name, optional(whitespace), '>', token_type='ETag')

content = None


def element(file_stream: FileStream, optional_etag=False):
    # content	   ::=   	CharData? ((element | Reference | CDSect | PI | Comment) CharData?)*
    global content
    if content is None:
        content = rule_sequence(
            optional(char_data),
            star(
                production(
                    element, reference, cd_sect, pi, comment
                ),
                optional(char_data)
            )
        )

    start = file_stream.tell()
    t = empty_elem_tag(file_stream)
    if t is not None:
        return t
    else:
        end = file_stream.tell()
        s = stag(file_stream)
        if s is None:
            file_stream.seek(end)
            return None
        c = content(file_stream)
        if c is None:
            file_stream.seek(end)
            return None
        e = etag(file_stream)
        if e is None:
            if optional_etag:
                return CompoundToken([s, c], start, token_type='malformed_element')
            file_stream.seek(end)
            return None
        return CompoundToken([s, c, e], start, token_type='element')


def unterminated_element(file_stream: FileStream):
    return element(file_stream, optional_etag=True)


def parse_permissive(file_stream: FileStream):
    start_pos = file_stream.tell()

    class Listener:
        percent = 0.0

        def __call__(self, _, pos):
            p = (((pos - start_pos) * 1000)//(len(file_stream) - start_pos)) / 10.0
            if p > self.percent:
                self.percent = p
                log.status(f"Parsing HTML at offset 0x{file_stream.offset():x}: {self.percent:.1f}%")

    listener = Listener()

    file_stream.add_listener(listener)
    try:
        return star(production(
            prolog,
            unterminated_element,
            doctypedecl,
            misc,
            etag,  # Allow malformed elements that have misplaced end tags
            named_rule(plus(restricted_char), name='RestrictedChar'),
            char
        ))(file_stream)
    finally:
        file_stream.remove_listener(listener)
        log.clear_status()


@submatcher('xml.trid.xml')
@submatcher('html.trid.xml')
class XMLMatcher(Match):
    def submatch(self, file_stream):
        parsed = parse_permissive(file_stream)
        if parsed is None:
            raise InvalidMatch()
        yield from parsed.to_matches(parent=self)


# if __name__ == '__main__':
#     from .fileutils import make_stream, Tempfile
#
#     with Tempfile(b'<a>foo</r>asf') as tmpfile:
#         print(repr(parse_permissive(make_stream(tmpfile))))
