from enum import Enum as PyEnum
import glob
import os

import yaml

from kaitaistruct import KaitaiStream, BytesIO

from . import expressions
from . import logger

log = logger.getStatusLogger("Kaitai")

KSY_DIR = os.path.join(os.path.realpath(os.path.dirname(__file__)), 'kaitai_defs')

DEFS = {}


class Endianness(PyEnum):
    BIG = 'be'
    LITTLE = 'le'
    NONE = ''


PRIMITIVE_TYPES_BY_NAME = {}


def to_dict_key(obj):
    if not hasattr(obj, 'uid'):
        if hasattr(obj, 'parent'):
            return f"{to_dict_key(obj.parent)}::{obj!s}"
        else:
            return obj
    if not hasattr(obj, 'parent') or obj.parent is None:
        return obj.uid
    else:
        return f"{to_dict_key(obj.parent)}::{obj.uid}"


class AST:
    def __init__(self, obj, parent=None):
        self.obj = obj
        self.parent = None
        self._children = []
        self._offset = None
        self._length = None
        self._last_parsed = None
        if parent is not None:
            parent.add_child(self)
        self.last_parsed = self
        log.debug(f"Updated AST: {self.root.to_dict()}")

    @property
    def relative_offset(self):
        if self.parent is None:
            return self.offset
        else:
            return self.offset - self.parent.offset

    def to_bytes(self, endianness='big'):
        ret = bytearray()
        for c in self._children:
            if isinstance(c, bytes):
                ret.extend(c)
            elif isinstance(c, int):
                ret.extend(int.to_bytes((self.obj.bit_length() + 7) // 8, endianness))
            elif hasattr(c, 'to_bytes'):
                ret.extend(c.to_bytes(endianness=endianness))
            else:
                ret.extend(bytes(c))
        return bytes(ret)

    def __bytes__(self):
        return self.to_bytes()

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False

    @property
    def left_siblings(self):
        if self.parent is None:
            return
        for c in self.parent.children:
            if c is self:
                break
            yield c

    @property
    def descendants(self):
        for c in self.children:
            yield c
            yield from c.descendants

    @property
    def ancestors(self):
        if self.parent is None:
            return
        found_self = False
        for c in reversed(self.parent.children):
            if found_self:
                yield from reversed(list(c.descendants))
                yield c
            elif c is self:
                found_self = True
        if self.parent.children[0] is self:
            yield self.parent
            yield from self.parent.ancestors

    @property
    def last_parsed(self):
        return self._last_parsed

    @last_parsed.setter
    def last_parsed(self, ast):
        self._last_parsed = ast
        if self.parent is not None:
            self.parent.last_parsed = ast

    def get_member(self, key):
        log.debug(f"{self.obj!s}.get_member({key!r})")

        with log.debug_nesting():
            if key == 'size':
                return len(self.children)

            elif isinstance(self.obj, Attribute):
                try:
                    t = self.obj.parent.get_type(key)
                    if isinstance(t, Instance):
                        # TODO: Change `None` to a stream object once we plumb in support for instance io and pos
                        return t.parse(None, self)
                except KeyError:
                    pass

            elif isinstance(self.obj, Type):
                try:
                    t = self.obj.get_type(key)
                    if isinstance(t, Instance):
                        # TODO: Change `None` to a stream object once we plumb in support for instance io and pos
                        return t.parse(None, self)
                except KeyError:
                    pass

            for c in self.children:
                if hasattr(c.obj, 'uid') and c.obj.uid == key:
                    return c
                for grandchild in c.children:
                    if hasattr(grandchild.obj, 'uid') and grandchild.obj.uid == key:
                        return grandchild

            raise KeyError(key)

    def __getitem__(self, key):
        log.debug(f"{self.obj!s}[{key!r}]")
        with log.debug_nesting():
            if isinstance(key, int) and 0 <= key < len(self.children):
                # Assume this is an index lookup
                return self.children[key]

            elif hasattr(self.obj, 'uid') and self.obj.uid == key:
                return self

            elif key == '_':
                return self.last_parsed

            elif key == '_parent':
                if self.parent is None:
                    return None
                else:
                    return self.parent.parent

            elif key == '_root':
                return self.root

            elif isinstance(self.obj, Attribute):
                try:
                    t = self.obj.parent.get_type(key)
                    if isinstance(t, Enum):
                        return t
                except KeyError:
                    pass

            elif isinstance(self.obj, Type):
                try:
                    t = self.obj.get_type(key)
                    if isinstance(t, Enum):
                        return t
                except KeyError:
                    pass

            for d in self.descendants:
                if hasattr(d.obj, 'uid') and d.obj.uid == key:
                    return d

            for a in self.ancestors:
                if hasattr(a.obj, 'uid') and a.obj.uid == key:
                    return a

            raise KeyError(key)

    @property
    def offset(self):
        if self._offset is None:
            if self._children:
                self._offset = self._children[0].offset
            elif self.parent is not None and self.parent._offset is not None and self.parent._length is not None:
                self._offset = self.parent.offset + self.parent.length
            else:
                self._offset = 0
        return self._offset

    @property
    def length(self):
        if self._length is None:
            if self._children:
                self._length = self._children[-1].offset + self._children[-1].length - self.offset
            else:
                self._length = 0
        return self._length

    def add_sibling(self, sibling):
        if sibling is None:
            return None
        assert self.parent._children[-1] is self
        if sibling.parent is self.parent:
            return sibling
        assert sibling.parent is None
        sibling.parent = self.parent
        self.parent._children.append(sibling)
        self.parent._offset = None
        self.parent._length = None
        return sibling

    def add_child(self, child):
        if child is None:
            return None
        if child.parent is self:
            return child
        assert child.parent is None
        if self._children:
            return self._children[-1].add_sibling(child)
        else:
            self._children = [child]
            child.parent = self
            self._offset = None
            self._length = None
            return child

    @property
    def children(self):
        return self._children

    @property
    def root(self):
        if self.parent is None:
            return self
        else:
            return self.parent.root

    def to_dict(self):
        if len(self.children) == 1:
            return {to_dict_key(self.obj): self.children[0].to_dict()}
        else:
            return {
                to_dict_key(self.obj): [c.to_dict() for c in self.children]
            }

    def __str__(self):
        return f"AST({self.to_dict()!s})"

    def __repr__(self):
        return f"{self.__class__.__name__}(obj={self.obj})"

    def __len__(self):
        return len(self._children)


class IOWrapper:
    def __init__(self, io: KaitaiStream):
        self.io: KaitaiStream = io

    def get_member(self, key):
        return self[key]

    def __getitem__(self, key):
        if key == 'eof':
            return self.io.is_eof()
        else:
            raise NotImplementedError(f"TODO: Implement _io.{key}")


class ASTWithIO:
    def __init__(self, ast: AST, io: KaitaiStream):
        self._ast = ast
        self._io = io

    def __getitem__(self, key):
        if key == '_io':
            return IOWrapper(self._io)
        else:
            return self._ast[key]

    def __contains__(self, key):
        if key == '_io':
            return True
        else:
            return key in self._ast

    def __bytes__(self):
        return bytes(self._ast)

    def __getattr__(self, key):
        return getattr(self._ast, key)

    def __str__(self):
        return str(self._ast)

    def __repr__(self):
        return f"{self.__class__.__name__}(ast={self._ast!r}, io={self._io!r})"

    def __len__(self):
        return len(self._ast)


class RawBytes(AST):
    def __init__(self, raw_bytes, offset, parent: AST=None):
        super().__init__(raw_bytes, parent)
        self._offset = offset
        self._length = len(self.obj)

    def add_sibling(self, sibling):
        if isinstance(sibling, RawBytes):
            self.obj += sibling.obj
            self._length += len(sibling.obj)
            return self
        else:
            return super().add_sibling(sibling)

    def __bytes__(self):
        return self.obj


class Integer(AST):
    def __init__(self, value:int, offset:int, length:int, parent: AST=None):
        super().__init__(value, parent)
        self._offset = offset
        self._length = length

    def to_bytes(self, endianness='big'):
        return self.obj.to_bytes((self.obj.bit_length() + 7) // 8, endianness)

    def __bytes__(self):
        return self.to_bytes()


class IntegerTypes(PyEnum):
    U1 = ('u1', 8, False, Endianness.NONE, 0, 255, KaitaiStream.read_u1)
    U2LE = ('u2le', 16, False, Endianness.LITTLE, 0, 65535, KaitaiStream.read_u2le)
    U2BE = ('u2be', 16, False, Endianness.BIG, 0, 65535, KaitaiStream.read_u2be)
    U4LE = ('u4le', 32, False, Endianness.LITTLE, 0, 4294967295, KaitaiStream.read_u4le)
    U4BE = ('u4be', 32, False, Endianness.BIG, 0, 4294967295, KaitaiStream.read_u4be)
    U8LE = ('u8le', 64, False, Endianness.LITTLE, 0, 18446744073709551615, KaitaiStream.read_u8le)
    U8BE = ('u8be', 64, False, Endianness.BIG, 0, 18446744073709551615, KaitaiStream.read_u8be)
    S1 = ('s1', 8, True, Endianness.NONE, -128, 127, KaitaiStream.read_s1)
    S2LE = ('s2le', 16, False, Endianness.LITTLE, -32768, 32767, KaitaiStream.read_s2le)
    S2BE = ('s2be', 16, False, Endianness.BIG, -32768, 32767, KaitaiStream.read_s2be)
    S4LE = ('s4le', 32, False, Endianness.LITTLE, -2147483648, 2147483647, KaitaiStream.read_s4le)
    S4BE = ('s4be', 32, False, Endianness.BIG, -2147483648, 2147483647, KaitaiStream.read_s4be)
    S8LE = ('s8le', 64, False, Endianness.LITTLE, -9223372036854775808, 9223372036854775807, KaitaiStream.read_s8le)
    S8BE = ('s8be', 64, False, Endianness.BIG, -9223372036854775808, 9223372036854775807, KaitaiStream.read_s8be)

    def parse(self, stream: KaitaiStream, context: AST):
        offset = stream.pos()
        try:
            b = self.reader(stream)
        except EOFError as e:
            print(context.root.to_dict())
            raise e
        return Integer(b, offset, self.bitwidth//8)

    def __init__(self, typename, bitwidth, signed, endianness, min_value, max_value, reader):
        self.typename = typename
        self.bitwidth = bitwidth
        self.signed = signed
        self.endianness = endianness
        self.min_value = min_value
        self.max_value = max_value
        self.reader = reader

        PRIMITIVE_TYPES_BY_NAME[self.typename] = self


class FloatTypes(PyEnum):
    F4LE = ('f4le', 32, Endianness.LITTLE, 24, 8)
    F4BE = ('f4be', 32, Endianness.BIG, 24, 8)
    F8LE = ('f8le', 32, Endianness.LITTLE, 53, 11)
    F8BE = ('f8be', 32, Endianness.BIG, 53, 11)

    def __init__(self, typename, bitwidth, endianness, mantissa_bits, exponent_bits):
        self.typename = typename
        self.bitwidth = bitwidth
        self.endianness = endianness
        self.mantissa_bits = mantissa_bits
        self.exponent_bits = exponent_bits

        PRIMITIVE_TYPES_BY_NAME[self.typename] = self


class Repeat(PyEnum):
    NONE = 'norepeat'
    EXPR = 'expr'
    EOS = 'eos'
    UNTIL = 'until'


def get_primitive_type(type_name: str, endianness: Endianness=None):
    if type_name in PRIMITIVE_TYPES_BY_NAME:
        return PRIMITIVE_TYPES_BY_NAME[type_name]
    elif endianness is not None and type_name + endianness.value in PRIMITIVE_TYPES_BY_NAME:
        return PRIMITIVE_TYPES_BY_NAME[type_name + endianness.value]
    raise KeyError(f'Unknown type "{type_name}"')


def truncate_stream(stream: KaitaiStream, num_bytes: int) -> KaitaiStream:
    class TruncatedStream:
        def __init__(self):
            self._end_byte = stream.pos() + num_bytes

        def read(self, n=None):
            if n is None:
                n = max(0, self._end_byte - stream.pos())
            if stream.pos() + n > self._end_byte:
                return b''
            return stream.read_bytes(n)

        def close(self):
            pass

        def tell(self):
            return stream.pos()

        def __getattr__(self, key):
            return getattr(stream, key)

    ret = KaitaiStream(TruncatedStream())
    ret.bits = stream.bits
    ret.bits_left = stream.bits_left
    return ret


class Expression:
    def __init__(self, expr):
        self.expr = expressions.parse(expr)

    def interpret(self, context):
        #log.debug(f"Interpreting: {self.expr.to_str(context=context)}")
        ret = self.expr.interpret(assignments=context)
        if not isinstance(ret, bytes) and not isinstance(ret, int) and not isinstance(ret, str):
            ret = bytes(ret)
        #log.debug(f"Result: {ret!r}")
        return ret


class ByteMatch:
    def __init__(self, contents):
        if isinstance(contents, bytes):
            self.contents = contents
        elif isinstance(contents, bytearray):
            self.contents = bytes(contents)
        elif isinstance(contents, list):
            arr = bytearray()
            for b in contents:
                if isinstance(b, int):
                    arr.append(b)
                elif isinstance(b, bytes):
                    arr += b
                elif isinstance(b, str):
                    arr += b.encode('utf-8')
            self.contents = bytes(arr)
        elif isinstance(contents, str):
            self.contents = contents.encode('utf-8')
        else:
            raise RuntimeError(f"TODO: Implement support for `contents` of type {type(contents)}")

    def parse(self, stream: KaitaiStream, context: AST):
        offset = stream.pos()
        c = stream.read_bytes(len(self.contents))
        if c != self.contents:
            print(str(context.root.to_dict()).replace("'", '"').replace("b\"", '"').replace('\\', '\\\\'))
            raise RuntimeError(f"File offset {offset}: Expected {self.contents!r} but instead got {c!r}")
        return RawBytes(c, offset)


class SwitchedType:
    def __init__(self, raw_yaml, parent):
        self.parent = parent
        self.switch_on = expressions.parse(raw_yaml['switch-on'])
        self.cases = []
        for k, v in raw_yaml['cases'].items():
            if k == '_':
                self.cases.append(None, v)
            else:
                self.cases.append((k, v))
            # TODO: Test for duplicate cases

    def parse(self, stream: KaitaiStream, context: AST) -> AST:
        default_case = None
        switch_on_value = self.parent.to_bytes(self.switch_on.interpret(context))
        for case, typename in self.cases:
            if case is None:
                default_case = typename
                continue
            if isinstance(case, int):
                case_value = self.parent.to_bytes(case)
            else:
                case_value = expressions.parse(case).interpret(context)
                case_value = self.parent.to_bytes(case_value)
            if switch_on_value == case_value:
                return self.parent.get_type(typename).parse(stream, context)
        if default_case is not None:
            return self.parent.get_type(default_case).parse(stream, context)
        else:
            log.warn(f"Attribute {self.parent.uid} does not contain a case for {switch_on_value}")
            return ByteArray(
                size=self.parent.size,
                size_eos=self.parent.size,
                terminator=self.parent.terminator,
                parent=self.parent
            ).parse(stream, context)


class Enum:
    def __init__(self, mapping, uid, parent, type_binding=None):
        self.parent = parent
        self.uid = uid
        self.values = mapping
        self.binding = type_binding

    def __getitem__(self, key):
        return self.values[key]

    def bind(self, to_type):
        return Enum(self.values, self.uid, self.parent, type_binding=to_type)

    def parse(self, stream: KaitaiStream, context: AST) -> AST:
        if self.binding is None:
            raise RuntimeError(f"Enum {self} is not bound")
        parsed = self.binding.parse(stream, context)
        # TODO: Make sure parsed is in this enum
        value = self.parent.to_bytes(to_int(parsed, self.parent.endianness))
        if value not in self.values.values() and not (value != '\x00' and b'' in self.values.values()):
            log.warn(f"{value} is not in enumeration {self.uid}: {self.values}")
            #raise ValueError(f"{value} is not in enumeration {self.uid}: {self.values}")
        return parsed

    def __repr__(self):
        return f"{self.__class__.__name__}(mapping={self.values!r}, uid={self.uid!r}, parent={self.parent!r}, type_binding={self.binding!r})"

    def __str__(self):
        return f"Enum<{self.uid}>({self.values!r})"


def to_int(int_like, endianness=Endianness.BIG) -> int:
    if isinstance(int_like, int):
        return int_like
    elif isinstance(int_like, bytes):
        return int.from_bytes(int_like, byteorder=['big', 'little'][endianness == Endianness.LITTLE])
    elif isinstance(int_like, Integer):
        return int_like.obj
    else:
        raise ValueError(f"Cannot convert {int_like!r} to an int!")


class ByteArray:
    def __init__(self, size=None, size_eos=False, terminator=None, parent=None):
        if size is None:
            self.size = None
        elif isinstance(size, int):
            self.size = Expression(str(size))
        elif isinstance(size, Expression):
            self.size = size
        else:
            self.size = Expression(size)
        self.size_eos = size_eos
        if terminator is not None:
            terminator = parent.to_bytes(terminator)
        self.terminator = terminator
        self.parent = parent

    def _size_met(self, parsed: bytearray, size: int) -> bool:
        return len(parsed) >= size

    def parse(self, stream: KaitaiStream, context: AST) -> RawBytes:
        offset = stream.pos()
        if self.size is None:
            size = None
        else:
            size = to_int(self.size.interpret(context))#, endianness=self.parent.endianness)
        if size is not None and self.terminator is None:
            ret = stream.read_bytes(size)
        else:
            ret = bytearray()
            while self.size is None or not self._size_met(ret, size):
                try:
                    b = stream.read_bytes(1)
                except EOFError:
                    if self.size_eos:
                        break
                    else:
                        raise RuntimeError("Unexpected end of stream")
                ret.extend(b)
                if self.terminator is not None and b == self.terminator:
                    break
        return RawBytes(bytes(ret), offset)


class String(ByteArray):
    def __init__(self, encoding, *args, **kwargs):
        self.encoding = encoding
        super().__init__(*args, **kwargs)

    def _decoded_length(self, parsed: bytearray) -> int:
        try:
            return len(parsed.decode(self.encoding))
        except Exception:
            return len(parsed)

    def _size_met(self, parsed: bytearray, size: int) -> bool:
        return self._decoded_length(parsed) >= size

    def parse(self, *args, **kwargs) -> RawBytes:
        ret: AST = super().parse(*args, **kwargs)
        # make sure the parsed bytes decode properly:
        try:
            ret.obj.decode(self.encoding)
        except UnicodeDecodeError:
            log.warn(f"\"{ret.obj}\" at file offset {ret.offset} is not a valid {self.encoding} string")
        return ret


class Attribute:
    def __init__(self, raw_yaml, parent, uid=None):
        self.parent = parent
        self.uid = raw_yaml.get('id', uid)
        self.contents = raw_yaml.get('contents', None)
        if self.contents is not None:
            self.contents = ByteMatch(self.contents)
        self._type_name = raw_yaml.get('type', None)
        self._type = None
        if isinstance(self._type_name, dict):
            if 'switch-on' in self._type_name:
                self._type = SwitchedType(self._type_name, parent=self)
            else:
                raise ValueError(f"Unknown type: {self._type_name!r}")
        self.repeat = raw_yaml.get('repeat', 'norepeat')
        for r in Repeat:
            if r.value == self.repeat:
                self.repeat = r
                break
        else:
            self.repeat = Repeat.NONE
        self.repeat_expr = raw_yaml.get('repeat-expr', None)
        if self.repeat_expr is not None:
            self.repeat_expr = Expression(self.repeat_expr)
        self.repeat_until = raw_yaml.get('repeat-until', None)
        if self.repeat_until is not None:
            self.repeat_until = Expression(self.repeat_until)
        self.if_expr = raw_yaml.get('if', None)
        if self.if_expr is not None:
            self.if_expr = Expression(self.if_expr)
        self._encoding = raw_yaml.get('encoding', None)
        self.enum = raw_yaml.get('enum', None)
        self.size = raw_yaml.get('size', None)
        if self.size is not None and isinstance(self.size, str):
            self.size = Expression(self.size)
        self.size_eos = raw_yaml.get('size-eos', False)
        self.terminator = raw_yaml.get('terminator', None)

    @property
    def endianness(self):
        return self.parent.endianness

    @property
    def encoding(self):
        if self._encoding is not None:
            return self._encoding
        return self.parent.encoding

    def to_bytes(self, *args, **kwargs):
        return self.parent.to_bytes(*args, **kwargs)

    def get_type(self, *args, **kwargs):
        return self.parent.get_type(*args, **kwargs)

    @property
    def type(self):
        if self._type is None:
            if self.contents is not None:
                self._type = self.contents
            elif self._type_name is None:
                self._type = ByteArray(size=self.size, size_eos=self.size_eos, terminator=self.terminator, parent=self)
            elif self._type_name == 'str':
                self._type = String(
                    encoding=self.encoding,
                    size=self.size,
                    size_eos=self.size_eos,
                    terminator=self.terminator,
                    parent=self
                )
            elif self._type_name == 'strz':
                self._type = String(
                    encoding=self.encoding,
                    size=self.size,
                    size_eos=self.size_eos,
                    terminator=0,
                    parent=self
                )
            else:
                self._type = self.parent.get_type(self._type_name)
            if self.enum is not None:
                self._type = self.parent.get_type(self.enum).bind(self._type)
            if self._type is None and self._type_name is not None:
                self._type = get_primitive_type(self._type_name, endianness=self.endianness)
        return self._type

    def parse(self, stream: KaitaiStream, context: AST=None) -> AST:
        ast = AST(self, parent=context)
        context = ASTWithIO(context, stream)
        if self.if_expr is not None:
            if not self.if_expr.interpret(context):
                return None
        if self.repeat == Repeat.EOS:
            while not stream.is_eof():
                ast.add_child(self.type.parse(stream, ast))
        elif self.repeat == Repeat.EXPR:
            if self.type == IntegerTypes.U1:
                # Just read this as a bytearray
                ast.add_child(ByteArray(size=self.repeat_expr.interpret(context), parent=self).parse(stream, ast))
            else:
                iterations = to_int(self.repeat_expr.interpret(context), endianness=self.endianness)
                for i in range(iterations):
                    ast.add_child(self.type.parse(stream, ast))
        elif self.repeat == Repeat.UNTIL:
            while True:
                ast.add_child(self.type.parse(stream, ast))
                ast.last_parsed = ast.children[-1]
                if self.repeat_until.interpret(context):
                    break
        elif self.size is not None:
            if hasattr(self.size, 'interpret'):
                num_bytes = to_int(self.size.interpret(context))
            else:
                num_bytes = to_int(self.size)
            with truncate_stream(stream, num_bytes) as s:
                log.debug(f"Truncated stream to {num_bytes} bytes")
                ast.add_child(self.type.parse(s, ast))
        else:
            ast.add_child(self.type.parse(stream, ast))
        return ast

    def __repr__(self):
        raw_yaml = {
            'id': self.uid,
            'contents': self.contents,
            'type': self._type_name
        }
        return f"{self.__class__.__name__}(raw_yaml={raw_yaml!r}, parent={self.parent!r})"


class Instance(Attribute):
    def __init__(self, raw_yaml, parent, uid):
        super().__init__(raw_yaml=raw_yaml, parent=parent, uid=uid)

        self.pos = raw_yaml.get('pos', None)
        self.io = raw_yaml.get('io', None)
        self.raw_expression: str = raw_yaml.get('value', None)

        if self.raw_expression is not None:
            self.value: Expression = Expression(self.raw_expression)

    def parse(self, stream: KaitaiStream, context: AST=None) -> AST:
        if self.raw_expression is not None:
            log.debug(f"Parsing instance {self.raw_expression!r}")
        else:
            log.debug(f"Parsing instance {self!r}")
        with log.debug_nesting():
            if self.pos is not None:
                raise NotImplementedError("TODO: Implement the Instance `pos` spec")
            elif self.io is not None:
                raise NotImplementedError("TODO: Implement the Instance `io` spec")
            if self.value is not None:
                return self.value.interpret(context)
            else:
                return super().parse(stream, context)

    def __repr__(self):
        raw_yaml = {
            'id': self.uid,
            'contents': self.contents,
            'type': self._type_name,
            'pos': self.pos,
            'io': self.io,
            'value': self.value
        }
        return f"{self.__class__.__name__}(raw_yaml={raw_yaml!r}, parent={self.parent!r})"


class Type:
    def __init__(self, raw_yaml, uid=None, parent=None):
        self.parent = parent
        self.meta = raw_yaml.get('meta', {})
        if uid is None:
            uid = self.meta['id']
        self.uid = uid
        self._endianness = self.meta.get('endian', None)
        if self._endianness == 'be':
            self._endianness = Endianness.BIG
        elif self._endianness == 'le':
            self._endianness = Endianness.LITTLE
        else:
            self._endianness = None
        self._encoding = self.meta.get('encoding', None)
        if 'imports' in self.meta:
            self._imports = self.meta['imports']
        else:
            self._imports = []
        self.seq = [Attribute(s, self) for s in raw_yaml.get('seq', ())]
        self.instances = {name: Instance(s, self, name) for name, s in raw_yaml.get('instances', {}).items()}
        self.types = {
            typename: Type(raw_type, uid=typename, parent=self)
            for typename, raw_type in raw_yaml.get('types', {}).items()
        }
        for eid, raw_enum in raw_yaml.get('enums', {}).items():
            self.types[eid] = Enum({v: self.to_bytes(k) for k, v in raw_enum.items()}, uid=eid, parent=self)

    def to_bytes(self, v, force_endianness: str = None):
        if force_endianness is not None:
            e = force_endianness
        elif self.endianness is None or self.endianness == Endianness.BIG:
            e = 'big'
        else:
            e = 'little'
        if isinstance(v, int) or isinstance(v, expressions.IntegerToken):
            if isinstance(v, expressions.IntegerToken):
                v = v.value
            return v.to_bytes((v.bit_length() + 7) // 8, e)
        elif isinstance(v, str):
            if self.encoding is None:
                return v.encode('ascii')
            else:
                return v.encode(self.encoding)
        elif isinstance(v, bytes):
            return v
        elif hasattr(v, 'to_bytes'):
            return v.to_bytes(e)
        else:
            raise RuntimeError(f"No support for converting {v!r} to bytes")

    @property
    def endianness(self):
        if self._endianness is not None:
            return self._endianness
        elif self.parent is not None:
            return self.parent.endianness
        else:
            return None

    @property
    def encoding(self):
        if self._encoding is not None:
            return self._encoding
        elif self.parent is not None:
            return self.parent.encoding
        else:
            return None

    @property
    def imports(self):
        return [DEFS[i] for i in self._imports]

    def get_type(self, type_name, allow_primitive=True):
        if type_name in self.types:
            return self.types[type_name]
        elif type_name in self.instances:
            return self.instances[type_name]
        # see if it is defined in an import
        for t in self.imports:
            try:
                return t.get_type(type_name, allow_primitive=False)
            except KeyError:
                # this import did not have the type
                pass
        if self.parent is not None:
            parent_type = self.parent.get_type(type_name, allow_primitive=False)
            if parent_type is not None:
                return parent_type
        if type_name in DEFS:
            return DEFS[type_name]
        elif allow_primitive:
            return get_primitive_type(type_name, self.endianness)
        else:
            KeyError(f"Unknown type {type_name} at {self.uid}")

    def parse(self, stream: KaitaiStream, context: AST=None) -> AST:
        ast = AST(self, parent=context)
        for attr in self.seq:
            ast.add_child(attr.parse(stream, ast))
        return ast


def parse(typename, bytes_like) -> AST:
    if typename not in DEFS:
        load()
    return DEFS[typename].parse(KaitaiStream(BytesIO(bytes_like)))


def parse_stream(typename, stream) -> AST:
    if typename not in DEFS:
        load()
    return DEFS[typename].parse(KaitaiStream(stream))


def load():
    for ksy_path in glob.glob(os.path.join(KSY_DIR, '*.ksy')):
        log.status(f'Loading KSY file definitions... {os.path.split(ksy_path)[-1]}')
        with open(ksy_path, 'r') as f:
            ksy = Type(yaml.safe_load(f))
            DEFS[ksy.uid] = ksy

    #for t in DEFS.values():
    #    for attr in t.seq:
    #        print(attr, attr.type)


if __name__ == '__main__':
    load()
