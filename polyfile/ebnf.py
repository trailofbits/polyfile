from collections.abc import Sequence

from .fileutils import FileStream
from .polyfile import Submatch


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

    def to_matches(self, parent):
        if self.token_type is None:
            name = 'Token'
        else:
            name = str(self.token_type)
        if isinstance(self.token, bytes):
            obj = self.token
        else:
            obj = str(self.token)
        yield Submatch(
            name=name,
            relative_offset=self.offset - parent.offset,
            length=len(self),
            match_obj=obj,
            parent=parent
        )

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

    def to_matches(self, parent):
        m = next(super().to_matches(parent))
        yield m
        for c in self.token:
            yield from c.to_matches(m)

    def collapse(self):
        if not self.token:
            return self
        new_tokens = []
        for t in self.token:
            if isinstance(t, CompoundToken):
                t = t.collapse()
            if not isinstance(t, CompoundToken) \
                    and new_tokens \
                    and not isinstance(new_tokens[-1], CompoundToken) \
                    and new_tokens[-1].token_type == t.token_type:
                new_tokens[-1].token += t.token
            else:
                new_tokens.append(t)
        assert len(new_tokens) > 0
        if len(new_tokens) == 1:
            if isinstance(new_tokens[0], CompoundToken):
                assert self.offset == new_tokens[0].offset
                if self.token_type == new_tokens[0].token_type:
                    self.token = new_tokens[0].token
                    return self
                else:
                    self.token = new_tokens
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


def named_rule(rule, name):
    rule = make_rule(rule)

    def wrapper(file_stream: FileStream):
        t = rule(file_stream)
        if t is not None:
            if t.token_type == name:
                return t
            elif t.token_type is None:
                t.token_type = name
            else:
                t = CompoundToken([t], token_type=name)
        return t

    return wrapper