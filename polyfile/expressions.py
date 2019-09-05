from collections import deque
from enum import Enum
from io import StringIO
import itertools


OPERATORS_BY_NAME = {}


def function_call(obj, function_name):
    raise RuntimeError("TODO: Implement")


def to_int(v, byteorder='big') -> int:
    if isinstance(v, int):
        return v
    elif isinstance(v, bytes) or isinstance(v, str) or isinstance(v, bytearray):
        if len(v) == 0:
            return 0
        elif len(v) == 1:
            return int(v[0])
        else:
            # Assume big endian
            return int.from_bytes(v, byteorder=byteorder)
    raise ValueError(f"Cannot convert {v!r} to an integer")


class Operator(Enum):
    ENUM_ACCESSOR = ('::', 0, lambda a, b: a[b.name], True, 2, False, (True, False))
    MEMBER_ACCESS = ('.', 1, lambda a, b: None, True, 2, False, (True, False))
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
    TERNARY_CONDITIONAL = ('?', 14, lambda a, b: b[bool(a)], False)

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


IDENTIFIER_BYTES = {
    chr(i) for i in range(ord('A'), ord('Z') + 1)
} | {
    chr(i) for i in range(ord('a'), ord('z') + 1)
} | {
    chr(i) for i in range(ord('0'), ord('9') + 1)
} | {
    '-', '_'
}


class Token:
    def __init__(self, raw_text):
        self._raw = raw_text

    @property
    def raw_token(self):
        return self._raw

    def __len__(self):
        return len(self._raw)

    def __repr__(self):
        return f"{self.__class__.__name__}({self._raw!r})"


class Parenthesis(Token):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"{self.__class__.__name__}()"


class OpenParen(Parenthesis):
    def __init__(self):
        super().__init__('(')


class CloseParen(Parenthesis):
    def __init__(self):
        super().__init__(')')


class OperatorToken(Token):
    def __init__(self, op):
        if isinstance(op, str):
            op = OPERATORS_BY_NAME[op]
        super().__init__(op.token)
        self.op: Operator = op

    def __repr__(self):
        return f"{self.__class__.__name__}(op={self.op!r})"


class IdentifierToken(Token):
    def __init__(self, name):
        super().__init__(name)
        self.name = name


class IntegerToken(Token):
    def __init__(self, raw_str, value):
        super().__init__(raw_str)
        self.value = value

    def __int__(self):
        return self.value

    def __repr__(self):
        return f"{self.__class__.__name__}(raw_str={self.raw_token!r}, value={self.value!r})"


class Tokenizer:
    def __init__(self, stream):
        if isinstance(stream, str):
            stream = StringIO(stream)
        self._stream = stream
        self._buffer = deque()
        self._next_token = None
        self.prev_token = None

    def _peek_byte(self, n=1):
        bytes_needed = n - len(self._buffer)
        if bytes_needed > 0:
            b = self._stream.read(bytes_needed)
            self._buffer.extend(b)
        return ''.join(itertools.islice(self._buffer, n))

    def _pop_byte(self, n=1):
        if len(self._buffer) < n:
            return ''.join(self._buffer) + self._stream.read(1)
        else:
            return ''.join(self._buffer.popleft() for _ in range(n))

    def peek(self):
        if self._next_token is not None:
            return self._next_token
        ret = None
        operand = None
        # ignore leading whitespace
        while self._peek_byte() == ' ' or self._peek_byte() == '\t':
            self._pop_byte()
        while ret is None:
            c = self._peek_byte(3)
            if len(c) == 0:
                break
            elif operand is not None:
                if c[0] in IDENTIFIER_BYTES:
                    operand += self._pop_byte()
                else:
                    break
            elif c in OPERATORS_BY_NAME:
                ret = OperatorToken(c)
            elif c[:2] in OPERATORS_BY_NAME:
                ret = OperatorToken(c[:2])
            elif c[0] in OPERATORS_BY_NAME:
                if c[0] == '+':
                    if self.prev_token is None or isinstance(self.prev_token, OperatorToken):
                        ret = OperatorToken(Operator.UNARY_PLUS)
                    else:
                        ret = OperatorToken(Operator.ADDITION)
                elif c[0] == '-':
                    if self.prev_token is None or isinstance(self.prev_token, OperatorToken):
                        ret = OperatorToken(Operator.UNARY_MINUS)
                    else:
                        ret = OperatorToken(Operator.SUBTRACTION)
                else:
                    ret = OperatorToken(c[0])
            elif c[0] == '(':
                ret = OpenParen()
            elif c[0] == ')':
                ret = CloseParen()
            elif c[0] == ' ' or c[0] == '\t':
                break
            else:
                operand = self._pop_byte()
        if operand is not None:
            if operand.startswith('0x'):
                ret = IntegerToken(operand, int(operand, 16))
            elif operand.startswith('0o'):
                ret = IntegerToken(operand, int(operand, 8))
            elif operand.startswith('0b'):
                ret = IntegerToken(operand, int(operand, 2))
            else:
                # Is this an integer?
                try:
                    ret = IntegerToken(operand, int(operand))
                except ValueError:
                    ret = IdentifierToken(operand)
        elif ret is not None:
            self._pop_byte(len(ret))
        return ret

    def has_next(self) -> bool:
        return self.peek() is not None

    def next(self):
        ret = self.peek()
        self.prev_token = ret
        self._next_token = None
        return ret

    def __iter__(self):
        while True:
            ret = self.next()
            if ret is None:
                break
            yield ret


def tokenize(stream_or_str):
    yield from Tokenizer(stream_or_str)


def infix_to_rpn(tokens):
    """Converts an infix expression to reverse Polish notation using the Shunting Yard algorithm"""
    operators = []

    for token in tokens:
        if isinstance(token, OpenParen):
            operators.append(token)
        elif isinstance(token, CloseParen):
            while not isinstance(operators[-1], OpenParen):
                yield operators.pop()
            # TODO: Throw a nice mismatched parenthesis exception here instead of relying on operators[-1]
            # to throw an index out of bounds exception
            if operators and isinstance(operators[-1], OpenParen):
                operators.pop()
        elif isinstance(token, OperatorToken):
            while operators and not isinstance(operators[-1], OpenParen) and \
                    (operators[-1].op.priority < token.op.priority \
                        or \
                    (operators[-1].op.priority == token.op.priority and operators[-1].op.left_associative)):
                yield operators.pop()
            operators.append(token)
        else:
            yield token

    while operators:
        top = operators.pop()
        if isinstance(top, Parenthesis):
            raise RuntimeError("Mismatched parenthesis")
        yield top


class Expression:
    def __init__(self, rpn):
        self.tokens = tuple(rpn)

    @staticmethod
    def get_value(token: Token, assignments: dict):
        if isinstance(token, IntegerToken):
            return token.value
        elif isinstance(token, IdentifierToken):
            if token.name not in assignments:
                raise KeyError(f'Unknown identifier {token.name}')
            return assignments[token.name]
        elif isinstance(token, int) or isinstance(token, str) or isinstance(token, bytes):
            return token
        else:
            raise ValueError(f"Unexpected token {token!r}")

    def interpret(self, assignments=None):
        if assignments is None:
            assignments = {}
        values = []
        for t in self.tokens:
            if isinstance(t, OperatorToken):
                args = []
                for expand, v in zip(t.op.expand, values[-t.op.arity:]):
                    if expand:
                        args.append(self.get_value(v, assignments))
                    else:
                        args.append(v)
                values = values[:-t.op.arity] + [t.op.execute(*args)]
            else:
                values.append(t)
        if len(values) != 1:
            raise RuntimeError(f"Unexpected extra tokens: {values[:-1]}")
        if isinstance(values[0], IdentifierToken):
            return self.get_value(values[0], assignments)
        return values[0]

    def __repr__(self):
        return f"{self.__class__.__name__}(rpn={self.tokens!r})"


def parse(expression_str: str) -> Expression:
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
