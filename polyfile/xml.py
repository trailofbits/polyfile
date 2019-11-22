from .ebnf import char_rule, Token, CompoundToken, star, plus, minus, optional, rule_sequence, star_until, reject_if, production, string_match
from .fileutils import FileStream


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
# xml_decl = rule_sequence('<?xml', version_info, optional(encoding_decl), optional(sd_decl), optional(whitespace), '?>')

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


def element(file_stream: FileStream):
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
            file_stream.seek(end)
            return None
        return CompoundToken([s, c, e], start, token_type='element')


parse_permissive = star(production(
    element,
    misc,
    minus(char, restricted_char)
))


if __name__ == '__main__':
    from .fileutils import make_stream, Tempfile

    with Tempfile(b'<a>foo</r>asf') as tmpfile:
        print(repr(parse_permissive(make_stream(tmpfile))))
