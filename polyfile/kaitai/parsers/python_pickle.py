# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import IntEnum
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class PythonPickle(KaitaiStruct):
    """Python Pickle format serializes Python objects to a byte stream, as a sequence
    of operations to run on the Pickle Virtual Machine.
    
    The format is mostly implementation defined, there is no formal specification.
    Pickle data types are closely coupled to the Python object model.
    Python singletons, and most builtin types (e.g. `None`, `int`,`dict`, `list`)
    are serialised using dedicated Pickle opcodes.
    Other builtin types, and all classes  (e.g. `set`, `datetime.datetime`) are
    serialised by encoding the name of a constructor callable.
    They are deserialised by importing that constructor, and calling it.
    So, unpickling an arbitrary pickle, using the Python's stdlib pickle module
    can cause arbitrary code execution.
    
    Pickle format has evolved with Python, later protocols add opcodes & types.
    Later Python releases can pickle to or unpickle from any earlier protocol.
    
    * Protocol 0: ASCII clean, no explicit version, fields are '\n' terminated.
    * Protocol 1: Binary, no explicit version, first length prefixed types.
    * Protocol 2 ([PEP 307](https://peps.python.org/pep-0307/)): Python 2.3+.
      Explicit versioning, more length prefixed types.
    * Protocol 3: Python 3.0+. Dedicated opcodes for `bytes` objects.
    * Protocol 4 ([PEP 3154](https://peps.python.org/pep-3154/)): Python 3.4+.
      Opcodes for 64 bit strings, framing, `set`.
    * Protocol 5 ([PEP 574](https://peps.python.org/pep-0574/)): Python 3.8+:
    Opcodes for `bytearray` and out of band data
    
    .. seealso::
       Source - https://github.com/python/cpython/blob/v3.8.1/Lib/pickletools.py
    """

    class Opcode(IntEnum):
        mark = 40
        empty_tuple = 41
        stop = 46
        pop = 48
        pop_mark = 49
        dup = 50
        binbytes = 66
        short_binbytes = 67
        float = 70
        binfloat = 71
        int = 73
        binint = 74
        binint1 = 75
        long = 76
        binint2 = 77
        none = 78
        persid = 80
        binpersid = 81
        reduce = 82
        string = 83
        binstring = 84
        short_binstring = 85
        unicode = 86
        binunicode = 88
        empty_list = 93
        append = 97
        build = 98
        global_opcode = 99
        dict = 100
        appends = 101
        get = 103
        binget = 104
        inst = 105
        long_binget = 106
        list = 108
        obj = 111
        put = 112
        binput = 113
        long_binput = 114
        setitem = 115
        tuple = 116
        setitems = 117
        empty_dict = 125
        proto = 128
        newobj = 129
        ext1 = 130
        ext2 = 131
        ext4 = 132
        tuple1 = 133
        tuple2 = 134
        tuple3 = 135
        newtrue = 136
        newfalse = 137
        long1 = 138
        long4 = 139
        short_binunicode = 140
        binunicode8 = 141
        binbytes8 = 142
        empty_set = 143
        additems = 144
        frozenset = 145
        newobj_ex = 146
        stack_global = 147
        memoize = 148
        frame = 149
        bytearray8 = 150
        next_buffer = 151
        readonly_buffer = 152
    SEQ_FIELDS = ["ops"]
    def __init__(self, _io, _parent=None, _root=None):
        super(PythonPickle, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['ops']['start'] = self._io.pos()
        self._debug['ops']['arr'] = []
        self.ops = []
        i = 0
        while True:
            self._debug['ops']['arr'].append({'start': self._io.pos()})
            _t_ops = PythonPickle.Op(self._io, self, self._root)
            try:
                _t_ops._read()
            finally:
                _ = _t_ops
                self.ops.append(_)
            self._debug['ops']['arr'][len(self.ops) - 1]['end'] = self._io.pos()
            if _.code == PythonPickle.Opcode.stop:
                break
            i += 1
        self._debug['ops']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.ops)):
            pass
            self.ops[i]._fetch_instances()


    class Bytearray8(KaitaiStruct):
        """Length prefixed string, between 0 and 2**64-1 bytes long.
        
        The contents are deserialised into a `bytearray` object.
        """
        SEQ_FIELDS = ["len", "val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.Bytearray8, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u8le()
            self._debug['len']['end'] = self._io.pos()
            self._debug['val']['start'] = self._io.pos()
            self.val = self._io.read_bytes(self.len)
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Bytes1(KaitaiStruct):
        """Length prefixed byte string, between 0 and 255 bytes long."""
        SEQ_FIELDS = ["len", "val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.Bytes1, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u1()
            self._debug['len']['end'] = self._io.pos()
            self._debug['val']['start'] = self._io.pos()
            self.val = self._io.read_bytes(self.len)
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Bytes4(KaitaiStruct):
        """Length prefixed string, between 0 and 2**32-1 bytes long."""
        SEQ_FIELDS = ["len", "val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.Bytes4, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u4le()
            self._debug['len']['end'] = self._io.pos()
            self._debug['val']['start'] = self._io.pos()
            self.val = self._io.read_bytes(self.len)
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Bytes8(KaitaiStruct):
        """Length prefixed string, between 0 and 2**64-1 bytes long.
        
        Only a 64-bit build of Python would produce a pickle containing strings
        large enough to need this type. Such a pickle could not be unpickled on
        a 32-bit build of Python, because the string would be larger than
        `sys.maxsize`.
        """
        SEQ_FIELDS = ["len", "val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.Bytes8, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u8le()
            self._debug['len']['end'] = self._io.pos()
            self._debug['val']['start'] = self._io.pos()
            self.val = self._io.read_bytes(self.len)
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class DecimalnlLong(KaitaiStruct):
        """Integer, encoded with the ASCII characters [0-9-], followed by 'L'."""
        SEQ_FIELDS = ["val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.DecimalnlLong, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['val']['start'] = self._io.pos()
            self.val = (self._io.read_bytes_term(10, False, True, True)).decode(u"ASCII")
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class DecimalnlShort(KaitaiStruct):
        """Integer or boolean, encoded with the ASCII characters [0-9-].
        
        The values '00' and '01' encode the Python values `False` and `True`.
        Normally a value would not contain leading '0' characters.
        """
        SEQ_FIELDS = ["val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.DecimalnlShort, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['val']['start'] = self._io.pos()
            self.val = (self._io.read_bytes_term(10, False, True, True)).decode(u"ASCII")
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Floatnl(KaitaiStruct):
        """Double float, encoded with the ASCII characters [0-9.e+-], '-inf', 'inf',
        or 'nan'.
        """
        SEQ_FIELDS = ["val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.Floatnl, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['val']['start'] = self._io.pos()
            self.val = (self._io.read_bytes_term(10, False, True, True)).decode(u"ASCII")
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Long1(KaitaiStruct):
        """Large signed integer, in the range -2**(8*255-1) to 2**(8*255-1)-1,
        encoded as two's complement.
        """
        SEQ_FIELDS = ["len", "val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.Long1, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u1()
            self._debug['len']['end'] = self._io.pos()
            self._debug['val']['start'] = self._io.pos()
            self.val = self._io.read_bytes(self.len)
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Long4(KaitaiStruct):
        """Large signed integer, in the range -2**(8*2**32-1) to 2**(8*2**32-1)-1,
        encoded as two's complement.
        """
        SEQ_FIELDS = ["len", "val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.Long4, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u4le()
            self._debug['len']['end'] = self._io.pos()
            self._debug['val']['start'] = self._io.pos()
            self.val = self._io.read_bytes(self.len)
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class NoArg(KaitaiStruct):
        """Some opcodes take no argument, this empty type is used for them."""
        SEQ_FIELDS = []
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.NoArg, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            pass


        def _fetch_instances(self):
            pass


    class Op(KaitaiStruct):
        SEQ_FIELDS = ["code", "arg"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.Op, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['code']['start'] = self._io.pos()
            self.code = KaitaiStream.resolve_enum(PythonPickle.Opcode, self._io.read_u1())
            self._debug['code']['end'] = self._io.pos()
            self._debug['arg']['start'] = self._io.pos()
            _on = self.code
            if _on == PythonPickle.Opcode.additems:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.append:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.appends:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.binbytes:
                pass
                self.arg = PythonPickle.Bytes4(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.binbytes8:
                pass
                self.arg = PythonPickle.Bytes8(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.binfloat:
                pass
                self.arg = self._io.read_f8be()
            elif _on == PythonPickle.Opcode.binget:
                pass
                self.arg = self._io.read_u1()
            elif _on == PythonPickle.Opcode.binint:
                pass
                self.arg = self._io.read_s4le()
            elif _on == PythonPickle.Opcode.binint1:
                pass
                self.arg = self._io.read_u1()
            elif _on == PythonPickle.Opcode.binint2:
                pass
                self.arg = self._io.read_u2le()
            elif _on == PythonPickle.Opcode.binpersid:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.binput:
                pass
                self.arg = self._io.read_u1()
            elif _on == PythonPickle.Opcode.binstring:
                pass
                self.arg = PythonPickle.String4(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.binunicode:
                pass
                self.arg = PythonPickle.Unicodestring4(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.binunicode8:
                pass
                self.arg = PythonPickle.Unicodestring8(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.build:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.bytearray8:
                pass
                self.arg = PythonPickle.Bytearray8(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.dict:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.dup:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.empty_dict:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.empty_list:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.empty_set:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.empty_tuple:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.ext1:
                pass
                self.arg = self._io.read_u1()
            elif _on == PythonPickle.Opcode.ext2:
                pass
                self.arg = self._io.read_u2le()
            elif _on == PythonPickle.Opcode.ext4:
                pass
                self.arg = self._io.read_u4le()
            elif _on == PythonPickle.Opcode.float:
                pass
                self.arg = PythonPickle.Floatnl(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.frame:
                pass
                self.arg = self._io.read_u8le()
            elif _on == PythonPickle.Opcode.frozenset:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.get:
                pass
                self.arg = PythonPickle.DecimalnlShort(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.global_opcode:
                pass
                self.arg = PythonPickle.StringnlNoescapePair(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.inst:
                pass
                self.arg = PythonPickle.StringnlNoescapePair(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.int:
                pass
                self.arg = PythonPickle.DecimalnlShort(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.list:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.long:
                pass
                self.arg = PythonPickle.DecimalnlLong(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.long1:
                pass
                self.arg = PythonPickle.Long1(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.long4:
                pass
                self.arg = PythonPickle.Long4(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.long_binget:
                pass
                self.arg = self._io.read_u4le()
            elif _on == PythonPickle.Opcode.long_binput:
                pass
                self.arg = self._io.read_u4le()
            elif _on == PythonPickle.Opcode.mark:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.memoize:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.newfalse:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.newobj:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.newobj_ex:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.newtrue:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.next_buffer:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.none:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.obj:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.persid:
                pass
                self.arg = PythonPickle.StringnlNoescape(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.pop:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.pop_mark:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.proto:
                pass
                self.arg = self._io.read_u1()
            elif _on == PythonPickle.Opcode.put:
                pass
                self.arg = PythonPickle.DecimalnlShort(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.readonly_buffer:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.reduce:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.setitem:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.setitems:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.short_binbytes:
                pass
                self.arg = PythonPickle.Bytes1(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.short_binstring:
                pass
                self.arg = PythonPickle.String1(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.short_binunicode:
                pass
                self.arg = PythonPickle.Unicodestring1(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.stack_global:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.stop:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.string:
                pass
                self.arg = PythonPickle.Stringnl(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.tuple:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.tuple1:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.tuple2:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.tuple3:
                pass
                self.arg = PythonPickle.NoArg(self._io, self, self._root)
                self.arg._read()
            elif _on == PythonPickle.Opcode.unicode:
                pass
                self.arg = PythonPickle.Unicodestringnl(self._io, self, self._root)
                self.arg._read()
            self._debug['arg']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            _on = self.code
            if _on == PythonPickle.Opcode.additems:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.append:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.appends:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.binbytes:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.binbytes8:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.binfloat:
                pass
            elif _on == PythonPickle.Opcode.binget:
                pass
            elif _on == PythonPickle.Opcode.binint:
                pass
            elif _on == PythonPickle.Opcode.binint1:
                pass
            elif _on == PythonPickle.Opcode.binint2:
                pass
            elif _on == PythonPickle.Opcode.binpersid:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.binput:
                pass
            elif _on == PythonPickle.Opcode.binstring:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.binunicode:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.binunicode8:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.build:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.bytearray8:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.dict:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.dup:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.empty_dict:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.empty_list:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.empty_set:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.empty_tuple:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.ext1:
                pass
            elif _on == PythonPickle.Opcode.ext2:
                pass
            elif _on == PythonPickle.Opcode.ext4:
                pass
            elif _on == PythonPickle.Opcode.float:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.frame:
                pass
            elif _on == PythonPickle.Opcode.frozenset:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.get:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.global_opcode:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.inst:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.int:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.list:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.long:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.long1:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.long4:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.long_binget:
                pass
            elif _on == PythonPickle.Opcode.long_binput:
                pass
            elif _on == PythonPickle.Opcode.mark:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.memoize:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.newfalse:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.newobj:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.newobj_ex:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.newtrue:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.next_buffer:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.none:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.obj:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.persid:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.pop:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.pop_mark:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.proto:
                pass
            elif _on == PythonPickle.Opcode.put:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.readonly_buffer:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.reduce:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.setitem:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.setitems:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.short_binbytes:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.short_binstring:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.short_binunicode:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.stack_global:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.stop:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.string:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.tuple:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.tuple1:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.tuple2:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.tuple3:
                pass
                self.arg._fetch_instances()
            elif _on == PythonPickle.Opcode.unicode:
                pass
                self.arg._fetch_instances()


    class String1(KaitaiStruct):
        """Length prefixed string, between 0 and 255 bytes long. Encoding is
        unspecified.
        
        The default Python 2.x string type (`str`) is a sequence of bytes.
        These are pickled as `string1` or `string4`, when protocol == 2.
        The bytes are written directly, no explicit encoding is performed.
        
        Python 3.x will not pickle an object as `string1` or `string4`.
        Instead, opcodes and types with a known encoding are used.
        When unpickling
        
        - `pickle.Unpickler` objects default to ASCII, which can be overridden
        - `pickletools.dis` uses latin1, and cannot be overridden
        
        .. seealso::
           Source - https://github.com/python/cpython/blob/bb8071a4cae/Lib/pickle.py#L486-L495
        """
        SEQ_FIELDS = ["len", "val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.String1, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u1()
            self._debug['len']['end'] = self._io.pos()
            self._debug['val']['start'] = self._io.pos()
            self.val = self._io.read_bytes(self.len)
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class String4(KaitaiStruct):
        """Length prefixed string, between 0 and 2**31-1 bytes long. Encoding is
        unspecified.
        
        Although the len field is signed, any length < 0 will raise an exception
        during unpickling.
        
        See the documentation for `string1` for further detail about encodings.
        
        .. seealso::
           Source - https://github.com/python/cpython/blob/bb8071a4cae/Lib/pickle.py#L486-L495
        """
        SEQ_FIELDS = ["len", "val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.String4, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_s4le()
            self._debug['len']['end'] = self._io.pos()
            self._debug['val']['start'] = self._io.pos()
            self.val = self._io.read_bytes(self.len)
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Stringnl(KaitaiStruct):
        """Quoted string, possibly containing Python string escapes."""
        SEQ_FIELDS = ["val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.Stringnl, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['val']['start'] = self._io.pos()
            self.val = (self._io.read_bytes_term(10, False, True, True)).decode(u"ASCII")
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class StringnlNoescape(KaitaiStruct):
        """Unquoted string, does not contain string escapes."""
        SEQ_FIELDS = ["val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.StringnlNoescape, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['val']['start'] = self._io.pos()
            self.val = (self._io.read_bytes_term(10, False, True, True)).decode(u"ASCII")
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class StringnlNoescapePair(KaitaiStruct):
        """Pair of unquoted, unescaped strings."""
        SEQ_FIELDS = ["val1", "val2"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.StringnlNoescapePair, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['val1']['start'] = self._io.pos()
            self.val1 = PythonPickle.StringnlNoescape(self._io, self, self._root)
            self.val1._read()
            self._debug['val1']['end'] = self._io.pos()
            self._debug['val2']['start'] = self._io.pos()
            self.val2 = PythonPickle.StringnlNoescape(self._io, self, self._root)
            self.val2._read()
            self._debug['val2']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.val1._fetch_instances()
            self.val2._fetch_instances()


    class Unicodestring1(KaitaiStruct):
        """Length prefixed string, between 0 and 255 bytes long."""
        SEQ_FIELDS = ["len", "val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.Unicodestring1, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u1()
            self._debug['len']['end'] = self._io.pos()
            self._debug['val']['start'] = self._io.pos()
            self.val = (self._io.read_bytes(self.len)).decode(u"UTF-8")
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Unicodestring4(KaitaiStruct):
        """Length prefixed string, between 0 and 2**32-1 bytes long."""
        SEQ_FIELDS = ["len", "val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.Unicodestring4, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u4le()
            self._debug['len']['end'] = self._io.pos()
            self._debug['val']['start'] = self._io.pos()
            self.val = (self._io.read_bytes(self.len)).decode(u"UTF-8")
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Unicodestring8(KaitaiStruct):
        """Length prefixed string, between 0 and 2**64-1 bytes long.
        
        Only a 64-bit build of Python would produce a pickle containing strings
        large enough to need this type. Such a pickle could not be unpickled on
        a 32-bit build of Python, because the string would be larger than
        `sys.maxsize`.
        """
        SEQ_FIELDS = ["len", "val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.Unicodestring8, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['len']['start'] = self._io.pos()
            self.len = self._io.read_u8le()
            self._debug['len']['end'] = self._io.pos()
            self._debug['val']['start'] = self._io.pos()
            self.val = (self._io.read_bytes(self.len)).decode(u"UTF-8")
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class Unicodestringnl(KaitaiStruct):
        """Unquoted string, containing Python Unicode escapes."""
        SEQ_FIELDS = ["val"]
        def __init__(self, _io, _parent=None, _root=None):
            super(PythonPickle.Unicodestringnl, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['val']['start'] = self._io.pos()
            self.val = (self._io.read_bytes_term(10, False, True, True)).decode(u"ASCII")
            self._debug['val']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass



