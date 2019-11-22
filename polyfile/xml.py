from collections.abc import Sequence

from .fileutils import FileStream


class Token:
    def __init__(self, token, offset, token_type=None):
        self.token = token
        self.offset = offset
        self.token_type = token_type

    def __len__(self):
        return len(self.token)

    @property
    def text(self):
        return self.token

    def __str__(self):
        if self.token_type is not None:
            token_name = self.token_type
        else:
            token_name = self.__class__.__name__
        return f"{token_name!s}({self.text!r})@{self.offset!s}"

    def __repr__(self):
        return f"{self.__class__.__name__!s}(token={self.token!r}, offset={self.offset!r}, token_type={self.token_type!r})"


class CompoundToken(Token):
    def __init__(self, tokens, offset, **kwargs):
        if not isinstance(tokens, Sequence):
            raise ValueError(f"A {self.__class__.__name__} must be instantiated with a sequence of tokens, not {tokens!r}")
        super().__init__([t for t in tokens if len(t) > 0], offset, **kwargs)

    def collapse(self):
        new_tokens = []
        for t in self.token:
            if isinstance(t, CompoundToken):
                t = t.collapse()
            if not isinstance(t, CompoundToken) and new_tokens and not isinstance(new_tokens[-1], CompoundToken):
                new_tokens[-1].token += t.token
            else:
                new_tokens.append(t)
        assert len(new_tokens) > 0
        if len(new_tokens) == 1:
            if isinstance(new_tokens[0], CompoundToken):
                assert self.offset == new_tokens[0].offset
                self.token = new_tokens[0].token
                return self
            else:
                if new_tokens[0].token_type is None and self.token_type is not None:
                    new_tokens[0].token_type = self.token_type
                return new_tokens[0]
        else:
            self.token = new_tokens
            return self

    @property
    def text(self):
        return b''.join(t.text for t in self.token)

    def __len__(self):
        return sum(map(len, self.token))

    def __iter__(self):
        return iter(self.token)


def whitespace(file_stream: FileStream):
    start = file_stream.tell()
    token = bytearray()
    while file_stream.peek(1) in (b'\x20', b'\x09', b'\x0D', b'\x0A'):
        token.append(file_stream.read(1)[0])
    if token:
        return Token(token, start)
    else:
        return None


def char_rule(predicate):
    def wrapper(file_stream: FileStream):
        byte = file_stream.peek(1)
        if len(byte) == 0:
            return None
        b = byte[0]
        if predicate(b):
            start = file_stream.tell()
            file_stream.read(1)
            return Token(byte, start)
        return None
    return wrapper


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


def char_match(c):
    if not isinstance(c, int):
        if len(c) != 1:
            raise ValueError('the character must be an int or single-character string or byte sequence')
        elif isinstance(c[0], int):
            c = c[0]
        else:
            c = ord(c[0])

    @char_rule
    def wrapper(b: int):
        return b == c

    return wrapper


def not_char(char_set):
    if isinstance(char_set, str):
        char_set = frozenset(ord(c) for c in char_set)
    else:
        char_set = frozenset(char_set)

    @char_rule
    def wrapper(b: int):
        return b not in char_set

    return wrapper


def star(rule, token_type=None):
    rule = make_rule(rule)

    def wrapper(file_stream: FileStream):
        start = file_stream.tell()
        toks = []
        while True:
            t = rule(file_stream)
            if t is None:
                break
            toks.append(t)
        return CompoundToken(toks, start, token_type=token_type).collapse()

    return wrapper


def star_until(rule, stop_rule, token_type=None):
    rule = make_rule(rule)
    stop_rule = make_rule(stop_rule)

    def wrapper(file_stream: FileStream):
        start = file_stream.tell()
        toks = []
        while True:
            end = file_stream.tell()
            sr = stop_rule(file_stream)
            if sr is not None:
                file_stream.seek(end)
                break
            t = rule(file_stream)
            if t is None:
                break
            toks.append(t)
        return CompoundToken(toks, start, token_type=token_type).collapse()

    return wrapper


def plus(rule, token_type=None):
    def wrapper(file_stream: FileStream):
        start = file_stream.tell()
        toks = []
        while True:
            t = rule(file_stream)
            if t is None:
                break
            toks.append(t)
        if not toks:
            file_stream.seek(start)
            return None
        return CompoundToken(toks, start, token_type=token_type).collapse()
    return wrapper


def make_rule(rule):
    if isinstance(rule, str) or isinstance(rule, bytes):
        if not rule:
            raise ValueError(f"Rule {rule!r} must be at least one character long!")
        if rule[0] == '^' or rule[0] == ord('^'):
            return not_char(rule[1:])
        elif len(rule) == 1:
            return char_match(rule)
        else:
            return string_match(rule)
    elif isinstance(rule, Sequence):
        return rule_sequence(*rule)
    else:
        return rule


def rule_sequence(*rules, token_type=None):
    mapped_rules = [make_rule(rule) for rule in rules]

    def wrapper(file_stream: FileStream):
        start = file_stream.tell()
        toks = []
        for rule in mapped_rules:
            t = rule(file_stream)
            if t is None:
                file_stream.seek(start)
                return None
            toks.append(t)
        return CompoundToken(toks, start, token_type=token_type).collapse()
    return wrapper


def production(*possibilities, token_type=None):
    mapped_rules = [make_rule(rule) for rule in possibilities]

    def wrapper(file_stream: FileStream):
        for possibility in mapped_rules:
            t = possibility(file_stream)
            if t is not None:
                if token_type is not None:
                    t.token_type = token_type
                return t
        return None
    return wrapper


def string_match(sequence):
    if isinstance(sequence, str):
        sequence = sequence.encode('utf-8')

    def wrapper(file_stream: FileStream):
        start = file_stream.tell()
        for b in sequence:
            byte = file_stream.read(1)
            if len(byte) == 0 or b != byte[0]:
                file_stream.seek(start)
                return None
        return Token(sequence, start)

    return wrapper


def minus(rule, minus_rule):
    rule = make_rule(rule)
    minus_rule = make_rule(minus_rule)

    def wrapper(file_stream: FileStream):
        start = file_stream.tell()
        t = rule(file_stream)
        if t is None:
            return None
        # see if the negative rule was triggered
        end = file_stream.tell()
        with FileStream(file_stream, length=start + len(t.text) + 1) as fs:
            fs.seek(start)
            neg_t = minus_rule(fs)
        if neg_t is not None:
            # The negative rule matched inside t
            file_stream.seek(start)
            return None
        file_stream.seek(end)
        return t

    return wrapper


def reject_if(rule, predicate):
    rule = make_rule(rule)

    def wrapper(file_stream: FileStream):
        start = file_stream.tell()
        t = rule(file_stream)
        if t is None:
            return None
        if predicate(t):
            file_stream.seek(start)
            return None
        return t

    return wrapper


def optional(rule):
    rule = make_rule(rule)

    def wrapper(file_stream: FileStream):
        t = rule(file_stream)
        if t is None:
            t = Token(b'', file_stream.tell())
        return t

    return wrapper


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
xml_decl = rule_sequence('<?xml', version_info, optional(encoding_decl), optional(sd_decl), optional(whitespace), '?>')

if __name__ == '__main__':
    from .fileutils import make_stream, Tempfile

    with Tempfile(b'<?foo asdf?>?>') as tmpfile:
        print(pi(make_stream(tmpfile)))
