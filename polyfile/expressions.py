"""Parse and evaluate standalone expressions over caller-supplied field values."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from enum import Enum
from io import StringIO
from typing import Literal, TextIO


OPERATORS_BY_NAME: dict[str, Operator] = {}


def to_int(v: object, byteorder: Literal["big", "little"] = "big") -> int:
    """Convert decimal text, unsigned bytes, or an integer for numeric operators."""
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        return int(v) if v else 0
    if isinstance(v, (bytes, bytearray)):
        return int.from_bytes(v, byteorder=byteorder)
    raise ValueError(f"Cannot convert {v!r} to an integer")


def _named_value(record: Mapping[str, object] | type[Enum], field: IdentifierToken) -> object:
    if isinstance(record, Mapping) and field.name not in record:
        raise KeyError(field.name)
    return record[field.name]


def _member_access(record: object, field: IdentifierToken) -> object:
    if not isinstance(record, Mapping):
        raise TypeError(f"Cannot read field {field.name!r} from {type(record).__name__}")
    return _named_value(record, field)


class Operator(Enum):
    ENUM_ACCESSOR = ('::', 0, _named_value, True, 2, False, (True, False))
    MEMBER_ACCESS = ('.', 1, _member_access, True, 2, False, (True, False))
    UNARY_PLUS = ('+', 2, lambda a: a, False, 1, True)
    UNARY_MINUS = ('-', 2, lambda a: -to_int(a), False, 1, True)
    LOGICAL_NOT = ('not', 2, lambda a: not a, False, 1)
    BITWISE_NOT = ('~', 2, lambda a: ~to_int(a), False, 1)
    MULTIPLICATION = ('*', 3, lambda a, b: to_int(a) * to_int(b))
    DIVISION = ('/', 3, lambda a, b: to_int(a) // to_int(b))
    REMAINDER = ('%', 3, lambda a, b: to_int(a) % to_int(b))
    ADDITION = ('+', 4, lambda a, b: a + b)
    SUBTRACTION = ('-', 4, lambda a, b: to_int(a) - to_int(b))
    BITWISE_LEFT_SHIFT = ('<<', 5, lambda a, b: to_int(a) << to_int(b))
    BITWISE_RIGHT_SHIFT = ('>>', 5, lambda a, b: to_int(a) >> to_int(b))
    LESS_THAN = ('<', 6, lambda a, b: a < b)
    GREATER_THAN = ('>', 6, lambda a, b: a > b)
    LESS_THAN_EQUAL = ('<=', 6, lambda a, b: a <= b)
    GREATER_THAN_EQUAL = ('>=', 6, lambda a, b: a >= b)
    EQUALS = ('==', 7, lambda a, b: a == b)
    NOT_EQUAL = ('!=', 7, lambda a, b: a != b)
    BITWISE_AND = ('&', 8, lambda a, b: to_int(a) & to_int(b))
    BITWISE_XOR = ('^', 9, lambda a, b: to_int(a) ^ to_int(b))
    BITWISE_OR = ('|', 10, lambda a, b: to_int(a) | to_int(b))
    LOGICAL_AND = ('and', 11, lambda a, b: a and b)
    LOGICAL_OR = ('or', 12, lambda a, b: a or b)
    TERNARY_ELSE = (':', 13, lambda a, b: (a, b), False)
    TERNARY_CONDITIONAL = ('?', 14, lambda a, b: b[0] if a else b[1], False)

    def __init__(self,
                 token,
                 priority,
                 execute,
                 is_left_associative=True,
                 arity=2,
                 multiple_arity=False,
                 expand=None):
        self.token = token
        self.priority = priority
        self.execute = execute
        self.left_associative = is_left_associative
        self.arity = arity
        self.multiple_arity = multiple_arity
        if expand is None:
            self.expand = (True,) * self.arity
        else:
            self.expand = expand
        if not multiple_arity:
            OPERATORS_BY_NAME[self.token] = self


class Token:
    def __init__(self, raw_text: str):
        self._raw = raw_text

    @property
    def raw_token(self) -> str:
        return self._raw

    def __len__(self):
        return len(self._raw)

    def __repr__(self):
        return f"{self.__class__.__name__}({self._raw!r})"


class Parenthesis(Token):
    def __repr__(self):
        return f"{self.__class__.__name__}()"


class OpenParen(Parenthesis):
    def __init__(self):
        super().__init__('(')


class CloseParen(Parenthesis):
    def __init__(self):
        super().__init__(')')


class OperatorToken(Token):
    def __init__(self, op: Operator | str):
        if isinstance(op, str):
            op = OPERATORS_BY_NAME[op]
        super().__init__(op.token)
        self.op: Operator = op

    def __repr__(self):
        return f"{self.__class__.__name__}(op={self.op!r})"


class IdentifierToken(Token):
    def __init__(self, name: str):
        super().__init__(name)
        self.name = name


class IntegerToken(Token):
    def __init__(self, raw_str: str, value: int):
        super().__init__(raw_str)
        self.value = value

    def __int__(self):
        return self.value

    def __repr__(self):
        return f"{self.__class__.__name__}(raw_str={self.raw_token!r}, value={self.value!r})"


# Match complete words before looking up keyword operators, and longest symbols first.
_SYMBOLS = sorted((op for op in OPERATORS_BY_NAME if not op.isalpha()), key=len, reverse=True)
_LEXEME = re.compile(r"[A-Za-z_0-9]+|" + "|".join(map(re.escape, _SYMBOLS)) + r"|\S")
_ACCESSORS = (Operator.MEMBER_ACCESS, Operator.ENUM_ACCESSOR)


def _read_word(raw: str) -> Token:
    if raw[0].isdigit() and raw.isascii():
        base = 0 if raw.lower().startswith(("0x", "0o", "0b")) else 10
        try:
            return IntegerToken(raw, int(raw, base))
        except ValueError as error:
            raise ValueError(f"Invalid integer literal {raw!r}") from error
    if raw.isascii() and raw.isidentifier():
        return IdentifierToken(raw)
    raise ValueError(f"Unexpected character {raw!r}")


def _read_token(raw: str, previous: Token | None) -> Token:
    if raw == "(":
        return OpenParen()
    if raw == ")":
        return CloseParen()
    if raw not in OPERATORS_BY_NAME:
        return _read_word(raw)
    if raw in ("+", "-") and (previous is None or isinstance(previous, (OperatorToken, OpenParen))):
        return OperatorToken(Operator.UNARY_PLUS if raw == "+" else Operator.UNARY_MINUS)
    return OperatorToken(raw)


class Tokenizer:
    def __init__(self, stream: str | TextIO):
        lines = StringIO(stream) if isinstance(stream, str) else stream
        self._words = (m.group() for line in lines for m in _LEXEME.finditer(line))
        self._next_token: Token | None = None
        self.prev_token: Token | None = None

    def peek(self) -> Token | None:
        """Return the next token without advancing past it."""
        if self._next_token is None and (raw := next(self._words, None)) is not None:
            self._next_token = _read_token(raw, self.prev_token)
        return self._next_token

    def has_next(self) -> bool:
        return self.peek() is not None

    def next(self) -> Token | None:
        self.prev_token = self.peek()
        self._next_token = None
        return self.prev_token

    def __iter__(self) -> Iterator[Token]:
        while (token := self.next()) is not None:
            yield token


def tokenize(stream_or_str: str | TextIO) -> Iterator[Token]:
    """Yield expression tokens from text or a text stream."""
    yield from Tokenizer(stream_or_str)


def _emit(operator: OpenParen | OperatorToken) -> Iterator[OperatorToken]:
    if isinstance(operator, OpenParen):
        raise ValueError("Unmatched '('")
    if operator.op is Operator.TERNARY_CONDITIONAL:
        raise ValueError("Unmatched '?' (expected ':')")
    yield operator
    if operator.op is Operator.TERNARY_ELSE:
        yield OperatorToken(Operator.TERNARY_CONDITIONAL)


def _drain_to(stack: list[OpenParen | OperatorToken], closing: Token) -> Iterator[OperatorToken]:
    while stack:
        top = stack.pop()
        if isinstance(top, OpenParen):
            if isinstance(closing, CloseParen):
                return
            break
        if isinstance(closing, OperatorToken) and top.op is Operator.TERNARY_CONDITIONAL:
            return
        yield from _emit(top)
    raise ValueError(f"Unmatched {closing.raw_token!r}")


def _push_operator(
    stack: list[OpenParen | OperatorToken], token: OperatorToken,
) -> Iterator[OperatorToken]:
    if token.op is Operator.TERNARY_ELSE:
        yield from _drain_to(stack, token)
    else:
        while stack and isinstance(top := stack[-1], OperatorToken):
            if top.op in (Operator.TERNARY_CONDITIONAL, Operator.TERNARY_ELSE):
                break
            if top.op.priority > token.op.priority:
                break
            if top.op.priority == token.op.priority and not token.op.left_associative:
                break
            yield from _emit(stack.pop())
    stack.append(token)


def _operand(source: Iterator[Token], stack: list[OpenParen | OperatorToken]) -> Token:
    for token in source:
        if isinstance(token, (IdentifierToken, IntegerToken)):
            return token
        if isinstance(token, OpenParen) or (
            isinstance(token, OperatorToken) and token.op.arity == 1
        ):
            stack.append(token)
        else:
            raise ValueError(f"Expected operand at {token.raw_token!r}")
    raise ValueError("Expected operand at end of input")


def infix_to_rpn(tokens: Iterable[Token]) -> Iterator[Token]:
    """Validate infix tokens and yield reverse Polish notation in one pass."""
    source = iter(tokens)
    stack: list[OpenParen | OperatorToken] = []
    yield _operand(source, stack)
    for token in source:
        if isinstance(token, CloseParen):
            yield from _drain_to(stack, token)
        elif isinstance(token, OperatorToken) and token.op in _ACCESSORS:
            field = next(source, None)
            if not isinstance(field, IdentifierToken):
                at = "end of input" if field is None else repr(field.raw_token)
                raise ValueError(f"Expected field name after {token.raw_token!r} at {at}")
            yield field
            yield token
        elif isinstance(token, OperatorToken) and token.op.arity == 2:
            yield from _push_operator(stack, token)
            yield _operand(source, stack)
        else:
            raise ValueError(f"Expected binary operator at {token.raw_token!r}")
    while stack:
        yield from _emit(stack.pop())


@dataclass(frozen=True, slots=True)
class _Literal:
    value: object


@dataclass(frozen=True, slots=True)
class _Call:
    op: Operator
    args: tuple[_Node, ...]


_Node = _Literal | IdentifierToken | _Call
_RpnItem = Token | int | str | bytes


def _compile_call(op: Operator, tokens: Iterator[_RpnItem], stack: list[_Node]) -> _Call:
    arity = op.arity
    if op is Operator.TERNARY_ELSE:
        question = next(tokens, None)
        if not isinstance(question, OperatorToken) or (
            question.op is not Operator.TERNARY_CONDITIONAL
        ):
            raise ValueError("Expected '?' after ':' in RPN")
        op, arity = question.op, 3
    elif op is Operator.TERNARY_CONDITIONAL:
        raise ValueError("Expected ':' before '?' in RPN")
    if len(stack) < arity:
        raise ValueError(f"Missing operand for {op.token!r} in RPN")
    args = stack[-arity:]
    del stack[-arity:]
    if op in _ACCESSORS:
        if not isinstance(args[1], IdentifierToken):
            raise ValueError(f"Expected a field name for {op.token!r}")
        args[1] = _Literal(args[1])
    return _Call(op, tuple(args))


def _compile(rpn: tuple[_RpnItem, ...]) -> _Node:
    stack: list[_Node] = []
    tokens = iter(rpn)
    for token in tokens:
        if isinstance(token, IntegerToken):
            stack.append(_Literal(token.value))
        elif isinstance(token, (int, str, bytes)):
            stack.append(_Literal(token))
        elif isinstance(token, IdentifierToken):
            stack.append(token)
        elif isinstance(token, OperatorToken):
            stack.append(_compile_call(token.op, tokens, stack))
        else:
            raise ValueError(f"Unexpected RPN token {token!r}")
    if len(stack) != 1:
        raise ValueError("Expected one expression at end of RPN")
    return stack[0]


@dataclass(frozen=True, slots=True)
class _Branch:
    # A missing arm keeps the condition's value, as required by 'and' and 'or'.
    when_true: _Node | None
    when_false: _Node | None


def _schedule(call: _Call, pending: list[_Node | _Branch | Operator]) -> None:
    op, args = call.op, call.args
    if op is Operator.TERNARY_CONDITIONAL:
        pending.extend((_Branch(args[1], args[2]), args[0]))
    elif op is Operator.LOGICAL_AND:
        pending.extend((_Branch(args[1], None), args[0]))
    elif op is Operator.LOGICAL_OR:
        pending.extend((_Branch(None, args[1]), args[0]))
    else:
        pending.append(op)
        pending.extend(reversed(args))


class Expression:
    def __init__(self, rpn: Iterable[_RpnItem]):
        self.tokens = tuple(rpn)
        self._root = _compile(self.tokens)

    @staticmethod
    def get_value(token: object, assignments: Mapping[str, object]) -> object:
        if isinstance(token, IntegerToken):
            return token.value
        if isinstance(token, IdentifierToken):
            if token.name not in assignments:
                raise KeyError(f"Unknown identifier {token.name}")
            return assignments[token.name]
        if isinstance(token, (int, str, bytes)):
            return token
        raise ValueError(f"Unexpected token {token!r}")

    def interpret(self, assignments: Mapping[str, object] | None = None) -> object:
        """Evaluate the expression using the supplied identifier bindings."""
        if assignments is None:
            assignments = {}
        values: list[object] = []
        pending: list[_Node | _Branch | Operator] = [self._root]
        while pending:
            task = pending.pop()
            if isinstance(task, _Call):
                _schedule(task, pending)
            elif isinstance(task, _Branch):
                selected = task.when_true if values[-1] else task.when_false
                if selected is not None:
                    values.pop()
                    pending.append(selected)
            elif isinstance(task, Operator):
                args = values[-task.arity:]
                del values[-task.arity:]
                values.append(task.execute(*args))
            elif isinstance(task, _Literal):
                values.append(task.value)
            else:
                values.append(self.get_value(task, assignments))
        return values.pop()

    def __repr__(self):
        return f"{self.__class__.__name__}(rpn={self.tokens!r})"


def parse(expression_str: str) -> Expression:
    """Compile expression text for repeated evaluation with Expression.interpret()."""
    return Expression(infix_to_rpn(tokenize(expression_str)))


if __name__ == '__main__':
    assignments = {
        'sampling_factors': 1234,
        'thumbnail_x': 5,
        'thumbnail_y': 7,
        'marker': 1,
        'marker_enum': {
            'soi': 0,
            'eoi': 3
        }
    }
    for s in (
        '(sampling_factors & -0xf0) >> 4',
        'thumbnail_x * thumbnail_y * 3',
        'marker != marker_enum::soi and marker != marker_enum::eoi'
    ):
        print(parse(s).interpret(assignments))
