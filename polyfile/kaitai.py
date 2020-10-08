from enum import Enum as PyEnum
import glob
import os

import yaml

from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO

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


class AST:
    def __init__(self, obj, parent=None):
        self.obj = obj
        self.parent = None
        self._children = []
        self._offset = None
        self._length = None
        if parent is not None:
            parent.add_child(self)

    @property
    def relative_offset(self):
        if self.parent is None:
            return self.offset
        else:
            return self.offset - self.parent.offset

    def __bytes__(self):
        ret = bytearray()
        for c in self._children:
            if isinstance(c, bytes):
                ret.extend(c)
            elif isinstance(c, int):
                ret.append(c)
            else:
                ret.extend(bytes(c))
        return bytes(ret)

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

    def __getitem__(self, key):
        if hasattr(self.obj, 'uid') and self.obj.uid == key:
            return bytes(self)

        elif isinstance(self.obj, Attribute):
            try:
                t = self.obj.parent.get_type(key)
                if t is not None and isinstance(t, Enum):
                    return t
            except KeyError:
                pass

        elif isinstance(self.obj, Type):
            try:
                t = self.obj.get_type(key)
                if t is not None and isinstance(t, Enum):
                    return t
            except KeyError:
                pass

        for d in self.descendants:
            if hasattr(d.obj, 'uid') and d.obj.uid == key:
                return bytes(d)

        for a in self.ancestors:
            if hasattr(a.obj, 'uid') and a.obj.uid == key:
                return bytes(a)

        raise KeyError(key)

    @property
    def offset(self):
        if self._offset is None:
            if self._children:
                self._offset = self._children[0].offset
            elif self.parent is not None:
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
        if not hasattr(self.obj, 'uid'):
            return self.obj
        elif len(self.children) == 1:
            return {self.obj.uid: self.children[0].to_dict()}
        else:
            return {
                self.obj.uid: [c.to_dict() for c in self.children]
            }

    def __len__(self):
        return len(self._children)


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

    def __bytes__(self):
        return self.obj.to_bytes((self.obj.bit_length() + 7) // 8, 'big')


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


class Expression:
    def __init__(self, expr):
        self.expr = expressions.parse(expr)

    def interpret(self, context):
        return self.expr.interpret(assignments=context)


class ByteMatch:
    def __init__(self, contents):
        if isinstance(contents, bytes):
            self.contents = contents
        elif isinstance(contents, bytearray):
            self.contents = bytes(contents)
        elif isinstance(contents, list):
            self.contents = bytes(contents)
        elif isinstance(contents, str):
            self.contents = contents.encode("utf-8")
        else:
            raise RuntimeError(f"TODO: Implement support for `contents` of type {type(contents)}")

    def parse(self, stream: KaitaiStream, context: AST):
        offset = stream.pos()
        c = stream.read_bytes(len(self.contents))
        if c != self.contents:
            print(context.root.to_dict())
            raise RuntimeError(f"File offset {offset}: Expected {self.contents!r} but instead got {c!r}")
        return RawBytes(c, offset)


class SwitchedType:
    def __init__(self, raw_yaml, parent):
        self.parent = parent
        self.switch_on = expressions.parse(raw_yaml['switch-on'])
        self.cases = []
        for k, v in raw_yaml['cases'].items():
            if isinstance(k, int):
                self.cases.append((str(k), v))
            elif k == '_':
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
            case_value = self.parent.to_bytes(expressions.parse(str(case)).interpret(context))
            if switch_on_value == case_value:
                return self.parent.get_type(typename).parse(stream, context)
        if default_case is not None:
            return self.parent.get_type(default_case).parse(stream, context)
        else:
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
        return parsed


class ByteArray:
    def __init__(self, size=None, size_eos=False, terminator=None, parent=None):
        if size is None:
            self.size = None
        elif isinstance(size, int):
            self.size = Expression(str(size))
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
        ret = bytearray()
        if self.size is None:
            size = None
        else:
            size = int(self.size.interpret(context))
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
        ret = super().parse(*args, **kwargs)
        # make sure the parsed bytes decode properly:
        ret.obj.decode(self.encoding)
        return ret


class Attribute:
    def __init__(self, raw_yaml, parent):
        self.parent = parent
        self.uid = raw_yaml.get('id', None)
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
        return self._type

    def parse(self, stream: KaitaiStream, context: AST=None) -> AST:
        if self.if_expr is not None:
            if not self.if_expr.interpret(context):
                return None
        ast = AST(self, parent=context)
        if self.repeat == Repeat.EOS:
            while not stream.is_eof():
                ast.add_child(self.type.parse(stream, ast))
        elif self.repeat == Repeat.EXPR:
            iterations = int.from_bytes(self.repeat_expr.interpret(context), byteorder='big')
            for i in range(iterations):
                ast.add_child(self.type.parse(stream, ast))
        elif self.repeat == Repeat.UNTIL:
            while not self.repeat_until.interpret(context):
                ast.add_child(self.type.parse(stream, ast))
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
        self.types = {
            typename: Type(raw_type, uid=typename, parent=self)
            for typename, raw_type in raw_yaml.get('types', {}).items()
        }
        for eid, raw_enum in raw_yaml.get('enums', {}).items():
            self.types[eid] = Enum({v: self.to_bytes(k) for k, v in raw_enum.items()}, uid=eid, parent=self)

    def to_bytes(self, v):
        if isinstance(v, int):
            if self.endianness is None or self.endianness == Endianness.BIG:
                e = 'big'
            else:
                e = 'little'
            return v.to_bytes((v.bit_length() + 7) // 8, e)
        elif isinstance(v, str):
            if self.encoding is None:
                return v.encode('ascii')
            else:
                return v.encode(self.encoding)
        elif isinstance(v, bytes):
            return v
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
        if allow_primitive:
            return get_primitive_type(type_name, self.endianness)
        else:
            KeyError(type_name)

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
