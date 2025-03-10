# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections
from enum import Enum


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class JavaClass(KaitaiStruct):
    """
    .. seealso::
       Source - https://docs.oracle.com/javase/specs/jvms/se19/html/jvms-4.html
    
    
    .. seealso::
       Source - https://docs.oracle.com/javase/specs/jls/se6/jls3.pdf
    
    
    .. seealso::
       Source - https://github.com/openjdk/jdk/blob/jdk-21%2B14/src/jdk.hotspot.agent/share/classes/sun/jvm/hotspot/runtime/ClassConstants.java
    
    
    .. seealso::
       Source - https://github.com/openjdk/jdk/blob/jdk-21%2B14/src/java.base/share/native/include/classfile_constants.h.template
    
    
    .. seealso::
       Source - https://github.com/openjdk/jdk/blob/jdk-21%2B14/src/hotspot/share/classfile/classFileParser.cpp
    """
    SEQ_FIELDS = ["magic", "version_minor", "version_major", "constant_pool_count", "constant_pool", "access_flags", "this_class", "super_class", "interfaces_count", "interfaces", "fields_count", "fields", "methods_count", "methods", "attributes_count", "attributes"]
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['magic']['start'] = self._io.pos()
        self.magic = self._io.read_bytes(4)
        self._debug['magic']['end'] = self._io.pos()
        if not self.magic == b"\xCA\xFE\xBA\xBE":
            raise kaitaistruct.ValidationNotEqualError(b"\xCA\xFE\xBA\xBE", self.magic, self._io, u"/seq/0")
        self._debug['version_minor']['start'] = self._io.pos()
        self.version_minor = self._io.read_u2be()
        self._debug['version_minor']['end'] = self._io.pos()
        self._debug['version_major']['start'] = self._io.pos()
        self.version_major = self._io.read_u2be()
        self._debug['version_major']['end'] = self._io.pos()
        if not self.version_major >= 43:
            raise kaitaistruct.ValidationLessThanError(43, self.version_major, self._io, u"/seq/2")
        self._debug['constant_pool_count']['start'] = self._io.pos()
        self.constant_pool_count = self._io.read_u2be()
        self._debug['constant_pool_count']['end'] = self._io.pos()
        self._debug['constant_pool']['start'] = self._io.pos()
        self.constant_pool = [None] * ((self.constant_pool_count - 1))
        for i in range((self.constant_pool_count - 1)):
            if not 'arr' in self._debug['constant_pool']:
                self._debug['constant_pool']['arr'] = []
            self._debug['constant_pool']['arr'].append({'start': self._io.pos()})
            _t_constant_pool = JavaClass.ConstantPoolEntry((self.constant_pool[(i - 1)].is_two_entries if i != 0 else False), self._io, self, self._root)
            _t_constant_pool._read()
            self.constant_pool[i] = _t_constant_pool
            self._debug['constant_pool']['arr'][i]['end'] = self._io.pos()

        self._debug['constant_pool']['end'] = self._io.pos()
        self._debug['access_flags']['start'] = self._io.pos()
        self.access_flags = self._io.read_u2be()
        self._debug['access_flags']['end'] = self._io.pos()
        self._debug['this_class']['start'] = self._io.pos()
        self.this_class = self._io.read_u2be()
        self._debug['this_class']['end'] = self._io.pos()
        self._debug['super_class']['start'] = self._io.pos()
        self.super_class = self._io.read_u2be()
        self._debug['super_class']['end'] = self._io.pos()
        self._debug['interfaces_count']['start'] = self._io.pos()
        self.interfaces_count = self._io.read_u2be()
        self._debug['interfaces_count']['end'] = self._io.pos()
        self._debug['interfaces']['start'] = self._io.pos()
        self.interfaces = [None] * (self.interfaces_count)
        for i in range(self.interfaces_count):
            if not 'arr' in self._debug['interfaces']:
                self._debug['interfaces']['arr'] = []
            self._debug['interfaces']['arr'].append({'start': self._io.pos()})
            self.interfaces[i] = self._io.read_u2be()
            self._debug['interfaces']['arr'][i]['end'] = self._io.pos()

        self._debug['interfaces']['end'] = self._io.pos()
        self._debug['fields_count']['start'] = self._io.pos()
        self.fields_count = self._io.read_u2be()
        self._debug['fields_count']['end'] = self._io.pos()
        self._debug['fields']['start'] = self._io.pos()
        self.fields = [None] * (self.fields_count)
        for i in range(self.fields_count):
            if not 'arr' in self._debug['fields']:
                self._debug['fields']['arr'] = []
            self._debug['fields']['arr'].append({'start': self._io.pos()})
            _t_fields = JavaClass.FieldInfo(self._io, self, self._root)
            _t_fields._read()
            self.fields[i] = _t_fields
            self._debug['fields']['arr'][i]['end'] = self._io.pos()

        self._debug['fields']['end'] = self._io.pos()
        self._debug['methods_count']['start'] = self._io.pos()
        self.methods_count = self._io.read_u2be()
        self._debug['methods_count']['end'] = self._io.pos()
        self._debug['methods']['start'] = self._io.pos()
        self.methods = [None] * (self.methods_count)
        for i in range(self.methods_count):
            if not 'arr' in self._debug['methods']:
                self._debug['methods']['arr'] = []
            self._debug['methods']['arr'].append({'start': self._io.pos()})
            _t_methods = JavaClass.MethodInfo(self._io, self, self._root)
            _t_methods._read()
            self.methods[i] = _t_methods
            self._debug['methods']['arr'][i]['end'] = self._io.pos()

        self._debug['methods']['end'] = self._io.pos()
        self._debug['attributes_count']['start'] = self._io.pos()
        self.attributes_count = self._io.read_u2be()
        self._debug['attributes_count']['end'] = self._io.pos()
        self._debug['attributes']['start'] = self._io.pos()
        self.attributes = [None] * (self.attributes_count)
        for i in range(self.attributes_count):
            if not 'arr' in self._debug['attributes']:
                self._debug['attributes']['arr'] = []
            self._debug['attributes']['arr'].append({'start': self._io.pos()})
            _t_attributes = JavaClass.AttributeInfo(self._io, self, self._root)
            _t_attributes._read()
            self.attributes[i] = _t_attributes
            self._debug['attributes']['arr'][i]['end'] = self._io.pos()

        self._debug['attributes']['end'] = self._io.pos()

    class VersionGuard(KaitaiStruct):
        """`class` file format version 45.3 (appeared in the very first publicly
        known release of Java SE AND JDK 1.0.2, released 23th January 1996) is so
        ancient that it's taken for granted. Earlier formats seem to be
        undocumented. Changes of `version_minor` don't change `class` format.
        Earlier `version_major`s likely belong to Oak programming language, the
        proprietary predecessor of Java.
        
        .. seealso::
           James Gosling, Bill Joy and Guy Steele. The Java Language Specification. English. Ed. by Lisa Friendly. Addison-Wesley, Aug. 1996, p. 825. ISBN: 0-201-63451-1.
        
        
        .. seealso::
           Frank Yellin and Tim Lindholm. The Java Virtual Machine Specification. English. Ed. by Lisa Friendly. Addison-Wesley, Sept. 1996, p. 475. ISBN: 0-201-63452-X.
        """
        SEQ_FIELDS = ["_unnamed0"]
        def __init__(self, major, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.major = major
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['_unnamed0']['start'] = self._io.pos()
            self._unnamed0 = self._io.read_bytes(0)
            self._debug['_unnamed0']['end'] = self._io.pos()
            _ = self.unnamed_0
            if not self._root.version_major >= self.major:
                raise kaitaistruct.ValidationExprError(self.unnamed_0, self._io, u"/types/version_guard/seq/0")


    class FloatCpInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4.5
        """
        SEQ_FIELDS = ["value"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['value']['start'] = self._io.pos()
            self.value = self._io.read_f4be()
            self._debug['value']['end'] = self._io.pos()


    class AttributeInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.7
        """
        SEQ_FIELDS = ["name_index", "attribute_length", "info"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['name_index']['start'] = self._io.pos()
            self.name_index = self._io.read_u2be()
            self._debug['name_index']['end'] = self._io.pos()
            self._debug['attribute_length']['start'] = self._io.pos()
            self.attribute_length = self._io.read_u4be()
            self._debug['attribute_length']['end'] = self._io.pos()
            self._debug['info']['start'] = self._io.pos()
            _on = self.name_as_str
            if _on == u"SourceFile":
                self._raw_info = self._io.read_bytes(self.attribute_length)
                _io__raw_info = KaitaiStream(BytesIO(self._raw_info))
                self.info = JavaClass.AttributeInfo.AttrBodySourceFile(_io__raw_info, self, self._root)
                self.info._read()
            elif _on == u"LineNumberTable":
                self._raw_info = self._io.read_bytes(self.attribute_length)
                _io__raw_info = KaitaiStream(BytesIO(self._raw_info))
                self.info = JavaClass.AttributeInfo.AttrBodyLineNumberTable(_io__raw_info, self, self._root)
                self.info._read()
            elif _on == u"Exceptions":
                self._raw_info = self._io.read_bytes(self.attribute_length)
                _io__raw_info = KaitaiStream(BytesIO(self._raw_info))
                self.info = JavaClass.AttributeInfo.AttrBodyExceptions(_io__raw_info, self, self._root)
                self.info._read()
            elif _on == u"Code":
                self._raw_info = self._io.read_bytes(self.attribute_length)
                _io__raw_info = KaitaiStream(BytesIO(self._raw_info))
                self.info = JavaClass.AttributeInfo.AttrBodyCode(_io__raw_info, self, self._root)
                self.info._read()
            else:
                self.info = self._io.read_bytes(self.attribute_length)
            self._debug['info']['end'] = self._io.pos()

        class AttrBodyCode(KaitaiStruct):
            """
            .. seealso::
               Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.7.3
            """
            SEQ_FIELDS = ["max_stack", "max_locals", "code_length", "code", "exception_table_length", "exception_table", "attributes_count", "attributes"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['max_stack']['start'] = self._io.pos()
                self.max_stack = self._io.read_u2be()
                self._debug['max_stack']['end'] = self._io.pos()
                self._debug['max_locals']['start'] = self._io.pos()
                self.max_locals = self._io.read_u2be()
                self._debug['max_locals']['end'] = self._io.pos()
                self._debug['code_length']['start'] = self._io.pos()
                self.code_length = self._io.read_u4be()
                self._debug['code_length']['end'] = self._io.pos()
                self._debug['code']['start'] = self._io.pos()
                self.code = self._io.read_bytes(self.code_length)
                self._debug['code']['end'] = self._io.pos()
                self._debug['exception_table_length']['start'] = self._io.pos()
                self.exception_table_length = self._io.read_u2be()
                self._debug['exception_table_length']['end'] = self._io.pos()
                self._debug['exception_table']['start'] = self._io.pos()
                self.exception_table = [None] * (self.exception_table_length)
                for i in range(self.exception_table_length):
                    if not 'arr' in self._debug['exception_table']:
                        self._debug['exception_table']['arr'] = []
                    self._debug['exception_table']['arr'].append({'start': self._io.pos()})
                    _t_exception_table = JavaClass.AttributeInfo.AttrBodyCode.ExceptionEntry(self._io, self, self._root)
                    _t_exception_table._read()
                    self.exception_table[i] = _t_exception_table
                    self._debug['exception_table']['arr'][i]['end'] = self._io.pos()

                self._debug['exception_table']['end'] = self._io.pos()
                self._debug['attributes_count']['start'] = self._io.pos()
                self.attributes_count = self._io.read_u2be()
                self._debug['attributes_count']['end'] = self._io.pos()
                self._debug['attributes']['start'] = self._io.pos()
                self.attributes = [None] * (self.attributes_count)
                for i in range(self.attributes_count):
                    if not 'arr' in self._debug['attributes']:
                        self._debug['attributes']['arr'] = []
                    self._debug['attributes']['arr'].append({'start': self._io.pos()})
                    _t_attributes = JavaClass.AttributeInfo(self._io, self, self._root)
                    _t_attributes._read()
                    self.attributes[i] = _t_attributes
                    self._debug['attributes']['arr'][i]['end'] = self._io.pos()

                self._debug['attributes']['end'] = self._io.pos()

            class ExceptionEntry(KaitaiStruct):
                """
                .. seealso::
                   Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.7.3
                """
                SEQ_FIELDS = ["start_pc", "end_pc", "handler_pc", "catch_type"]
                def __init__(self, _io, _parent=None, _root=None):
                    self._io = _io
                    self._parent = _parent
                    self._root = _root if _root else self
                    self._debug = collections.defaultdict(dict)

                def _read(self):
                    self._debug['start_pc']['start'] = self._io.pos()
                    self.start_pc = self._io.read_u2be()
                    self._debug['start_pc']['end'] = self._io.pos()
                    self._debug['end_pc']['start'] = self._io.pos()
                    self.end_pc = self._io.read_u2be()
                    self._debug['end_pc']['end'] = self._io.pos()
                    self._debug['handler_pc']['start'] = self._io.pos()
                    self.handler_pc = self._io.read_u2be()
                    self._debug['handler_pc']['end'] = self._io.pos()
                    self._debug['catch_type']['start'] = self._io.pos()
                    self.catch_type = self._io.read_u2be()
                    self._debug['catch_type']['end'] = self._io.pos()

                @property
                def catch_exception(self):
                    if hasattr(self, '_m_catch_exception'):
                        return self._m_catch_exception if hasattr(self, '_m_catch_exception') else None

                    if self.catch_type != 0:
                        self._m_catch_exception = self._root.constant_pool[(self.catch_type - 1)]

                    return self._m_catch_exception if hasattr(self, '_m_catch_exception') else None



        class AttrBodyExceptions(KaitaiStruct):
            """
            .. seealso::
               Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.7.5
            """
            SEQ_FIELDS = ["number_of_exceptions", "exceptions"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['number_of_exceptions']['start'] = self._io.pos()
                self.number_of_exceptions = self._io.read_u2be()
                self._debug['number_of_exceptions']['end'] = self._io.pos()
                self._debug['exceptions']['start'] = self._io.pos()
                self.exceptions = [None] * (self.number_of_exceptions)
                for i in range(self.number_of_exceptions):
                    if not 'arr' in self._debug['exceptions']:
                        self._debug['exceptions']['arr'] = []
                    self._debug['exceptions']['arr'].append({'start': self._io.pos()})
                    _t_exceptions = JavaClass.AttributeInfo.AttrBodyExceptions.ExceptionTableEntry(self._io, self, self._root)
                    _t_exceptions._read()
                    self.exceptions[i] = _t_exceptions
                    self._debug['exceptions']['arr'][i]['end'] = self._io.pos()

                self._debug['exceptions']['end'] = self._io.pos()

            class ExceptionTableEntry(KaitaiStruct):
                SEQ_FIELDS = ["index"]
                def __init__(self, _io, _parent=None, _root=None):
                    self._io = _io
                    self._parent = _parent
                    self._root = _root if _root else self
                    self._debug = collections.defaultdict(dict)

                def _read(self):
                    self._debug['index']['start'] = self._io.pos()
                    self.index = self._io.read_u2be()
                    self._debug['index']['end'] = self._io.pos()

                @property
                def as_info(self):
                    if hasattr(self, '_m_as_info'):
                        return self._m_as_info if hasattr(self, '_m_as_info') else None

                    self._m_as_info = self._root.constant_pool[(self.index - 1)].cp_info
                    return self._m_as_info if hasattr(self, '_m_as_info') else None

                @property
                def name_as_str(self):
                    if hasattr(self, '_m_name_as_str'):
                        return self._m_name_as_str if hasattr(self, '_m_name_as_str') else None

                    self._m_name_as_str = self.as_info.name_as_str
                    return self._m_name_as_str if hasattr(self, '_m_name_as_str') else None



        class AttrBodySourceFile(KaitaiStruct):
            """
            .. seealso::
               Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.7.10
            """
            SEQ_FIELDS = ["sourcefile_index"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['sourcefile_index']['start'] = self._io.pos()
                self.sourcefile_index = self._io.read_u2be()
                self._debug['sourcefile_index']['end'] = self._io.pos()

            @property
            def sourcefile_as_str(self):
                if hasattr(self, '_m_sourcefile_as_str'):
                    return self._m_sourcefile_as_str if hasattr(self, '_m_sourcefile_as_str') else None

                self._m_sourcefile_as_str = self._root.constant_pool[(self.sourcefile_index - 1)].cp_info.value
                return self._m_sourcefile_as_str if hasattr(self, '_m_sourcefile_as_str') else None


        class AttrBodyLineNumberTable(KaitaiStruct):
            """
            .. seealso::
               Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.7.12
            """
            SEQ_FIELDS = ["line_number_table_length", "line_number_table"]
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['line_number_table_length']['start'] = self._io.pos()
                self.line_number_table_length = self._io.read_u2be()
                self._debug['line_number_table_length']['end'] = self._io.pos()
                self._debug['line_number_table']['start'] = self._io.pos()
                self.line_number_table = [None] * (self.line_number_table_length)
                for i in range(self.line_number_table_length):
                    if not 'arr' in self._debug['line_number_table']:
                        self._debug['line_number_table']['arr'] = []
                    self._debug['line_number_table']['arr'].append({'start': self._io.pos()})
                    _t_line_number_table = JavaClass.AttributeInfo.AttrBodyLineNumberTable.LineNumberTableEntry(self._io, self, self._root)
                    _t_line_number_table._read()
                    self.line_number_table[i] = _t_line_number_table
                    self._debug['line_number_table']['arr'][i]['end'] = self._io.pos()

                self._debug['line_number_table']['end'] = self._io.pos()

            class LineNumberTableEntry(KaitaiStruct):
                SEQ_FIELDS = ["start_pc", "line_number"]
                def __init__(self, _io, _parent=None, _root=None):
                    self._io = _io
                    self._parent = _parent
                    self._root = _root if _root else self
                    self._debug = collections.defaultdict(dict)

                def _read(self):
                    self._debug['start_pc']['start'] = self._io.pos()
                    self.start_pc = self._io.read_u2be()
                    self._debug['start_pc']['end'] = self._io.pos()
                    self._debug['line_number']['start'] = self._io.pos()
                    self.line_number = self._io.read_u2be()
                    self._debug['line_number']['end'] = self._io.pos()



        @property
        def name_as_str(self):
            if hasattr(self, '_m_name_as_str'):
                return self._m_name_as_str if hasattr(self, '_m_name_as_str') else None

            self._m_name_as_str = self._root.constant_pool[(self.name_index - 1)].cp_info.value
            return self._m_name_as_str if hasattr(self, '_m_name_as_str') else None


    class MethodRefCpInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4.2
        """
        SEQ_FIELDS = ["class_index", "name_and_type_index"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['class_index']['start'] = self._io.pos()
            self.class_index = self._io.read_u2be()
            self._debug['class_index']['end'] = self._io.pos()
            self._debug['name_and_type_index']['start'] = self._io.pos()
            self.name_and_type_index = self._io.read_u2be()
            self._debug['name_and_type_index']['end'] = self._io.pos()

        @property
        def class_as_info(self):
            if hasattr(self, '_m_class_as_info'):
                return self._m_class_as_info if hasattr(self, '_m_class_as_info') else None

            self._m_class_as_info = self._root.constant_pool[(self.class_index - 1)].cp_info
            return self._m_class_as_info if hasattr(self, '_m_class_as_info') else None

        @property
        def name_and_type_as_info(self):
            if hasattr(self, '_m_name_and_type_as_info'):
                return self._m_name_and_type_as_info if hasattr(self, '_m_name_and_type_as_info') else None

            self._m_name_and_type_as_info = self._root.constant_pool[(self.name_and_type_index - 1)].cp_info
            return self._m_name_and_type_as_info if hasattr(self, '_m_name_and_type_as_info') else None


    class FieldInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.5
        """
        SEQ_FIELDS = ["access_flags", "name_index", "descriptor_index", "attributes_count", "attributes"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['access_flags']['start'] = self._io.pos()
            self.access_flags = self._io.read_u2be()
            self._debug['access_flags']['end'] = self._io.pos()
            self._debug['name_index']['start'] = self._io.pos()
            self.name_index = self._io.read_u2be()
            self._debug['name_index']['end'] = self._io.pos()
            self._debug['descriptor_index']['start'] = self._io.pos()
            self.descriptor_index = self._io.read_u2be()
            self._debug['descriptor_index']['end'] = self._io.pos()
            self._debug['attributes_count']['start'] = self._io.pos()
            self.attributes_count = self._io.read_u2be()
            self._debug['attributes_count']['end'] = self._io.pos()
            self._debug['attributes']['start'] = self._io.pos()
            self.attributes = [None] * (self.attributes_count)
            for i in range(self.attributes_count):
                if not 'arr' in self._debug['attributes']:
                    self._debug['attributes']['arr'] = []
                self._debug['attributes']['arr'].append({'start': self._io.pos()})
                _t_attributes = JavaClass.AttributeInfo(self._io, self, self._root)
                _t_attributes._read()
                self.attributes[i] = _t_attributes
                self._debug['attributes']['arr'][i]['end'] = self._io.pos()

            self._debug['attributes']['end'] = self._io.pos()

        @property
        def name_as_str(self):
            if hasattr(self, '_m_name_as_str'):
                return self._m_name_as_str if hasattr(self, '_m_name_as_str') else None

            self._m_name_as_str = self._root.constant_pool[(self.name_index - 1)].cp_info.value
            return self._m_name_as_str if hasattr(self, '_m_name_as_str') else None


    class DoubleCpInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4.6
        """
        SEQ_FIELDS = ["value"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['value']['start'] = self._io.pos()
            self.value = self._io.read_f8be()
            self._debug['value']['end'] = self._io.pos()


    class DynamicCpInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se19/html/jvms-4.html#jvms-4.4.10
        """
        SEQ_FIELDS = ["_unnamed0", "bootstrap_method_attr_index", "name_and_type_index"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['_unnamed0']['start'] = self._io.pos()
            self._unnamed0 = JavaClass.VersionGuard(55, self._io, self, self._root)
            self._unnamed0._read()
            self._debug['_unnamed0']['end'] = self._io.pos()
            self._debug['bootstrap_method_attr_index']['start'] = self._io.pos()
            self.bootstrap_method_attr_index = self._io.read_u2be()
            self._debug['bootstrap_method_attr_index']['end'] = self._io.pos()
            self._debug['name_and_type_index']['start'] = self._io.pos()
            self.name_and_type_index = self._io.read_u2be()
            self._debug['name_and_type_index']['end'] = self._io.pos()


    class LongCpInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4.5
        """
        SEQ_FIELDS = ["value"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['value']['start'] = self._io.pos()
            self.value = self._io.read_u8be()
            self._debug['value']['end'] = self._io.pos()


    class InvokeDynamicCpInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4.10
        """
        SEQ_FIELDS = ["_unnamed0", "bootstrap_method_attr_index", "name_and_type_index"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['_unnamed0']['start'] = self._io.pos()
            self._unnamed0 = JavaClass.VersionGuard(51, self._io, self, self._root)
            self._unnamed0._read()
            self._debug['_unnamed0']['end'] = self._io.pos()
            self._debug['bootstrap_method_attr_index']['start'] = self._io.pos()
            self.bootstrap_method_attr_index = self._io.read_u2be()
            self._debug['bootstrap_method_attr_index']['end'] = self._io.pos()
            self._debug['name_and_type_index']['start'] = self._io.pos()
            self.name_and_type_index = self._io.read_u2be()
            self._debug['name_and_type_index']['end'] = self._io.pos()


    class MethodHandleCpInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4.8
        """

        class ReferenceKindEnum(Enum):
            get_field = 1
            get_static = 2
            put_field = 3
            put_static = 4
            invoke_virtual = 5
            invoke_static = 6
            invoke_special = 7
            new_invoke_special = 8
            invoke_interface = 9
        SEQ_FIELDS = ["_unnamed0", "reference_kind", "reference_index"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['_unnamed0']['start'] = self._io.pos()
            self._unnamed0 = JavaClass.VersionGuard(51, self._io, self, self._root)
            self._unnamed0._read()
            self._debug['_unnamed0']['end'] = self._io.pos()
            self._debug['reference_kind']['start'] = self._io.pos()
            self.reference_kind = KaitaiStream.resolve_enum(JavaClass.MethodHandleCpInfo.ReferenceKindEnum, self._io.read_u1())
            self._debug['reference_kind']['end'] = self._io.pos()
            self._debug['reference_index']['start'] = self._io.pos()
            self.reference_index = self._io.read_u2be()
            self._debug['reference_index']['end'] = self._io.pos()


    class ModulePackageCpInfo(KaitaiStruct):
        """Project Jigsaw modules introduced in Java 9
        
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se19/html/jvms-3.html#jvms-3.16
        
        
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se19/html/jvms-4.html#jvms-4.4.11
        
        
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se19/html/jvms-4.html#jvms-4.4.12
        """
        SEQ_FIELDS = ["_unnamed0", "name_index"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['_unnamed0']['start'] = self._io.pos()
            self._unnamed0 = JavaClass.VersionGuard(53, self._io, self, self._root)
            self._unnamed0._read()
            self._debug['_unnamed0']['end'] = self._io.pos()
            self._debug['name_index']['start'] = self._io.pos()
            self.name_index = self._io.read_u2be()
            self._debug['name_index']['end'] = self._io.pos()

        @property
        def name_as_info(self):
            if hasattr(self, '_m_name_as_info'):
                return self._m_name_as_info if hasattr(self, '_m_name_as_info') else None

            self._m_name_as_info = self._root.constant_pool[(self.name_index - 1)].cp_info
            return self._m_name_as_info if hasattr(self, '_m_name_as_info') else None

        @property
        def name_as_str(self):
            if hasattr(self, '_m_name_as_str'):
                return self._m_name_as_str if hasattr(self, '_m_name_as_str') else None

            self._m_name_as_str = self.name_as_info.value
            return self._m_name_as_str if hasattr(self, '_m_name_as_str') else None


    class NameAndTypeCpInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4.6
        """
        SEQ_FIELDS = ["name_index", "descriptor_index"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['name_index']['start'] = self._io.pos()
            self.name_index = self._io.read_u2be()
            self._debug['name_index']['end'] = self._io.pos()
            self._debug['descriptor_index']['start'] = self._io.pos()
            self.descriptor_index = self._io.read_u2be()
            self._debug['descriptor_index']['end'] = self._io.pos()

        @property
        def name_as_info(self):
            if hasattr(self, '_m_name_as_info'):
                return self._m_name_as_info if hasattr(self, '_m_name_as_info') else None

            self._m_name_as_info = self._root.constant_pool[(self.name_index - 1)].cp_info
            return self._m_name_as_info if hasattr(self, '_m_name_as_info') else None

        @property
        def name_as_str(self):
            if hasattr(self, '_m_name_as_str'):
                return self._m_name_as_str if hasattr(self, '_m_name_as_str') else None

            self._m_name_as_str = self.name_as_info.value
            return self._m_name_as_str if hasattr(self, '_m_name_as_str') else None

        @property
        def descriptor_as_info(self):
            if hasattr(self, '_m_descriptor_as_info'):
                return self._m_descriptor_as_info if hasattr(self, '_m_descriptor_as_info') else None

            self._m_descriptor_as_info = self._root.constant_pool[(self.descriptor_index - 1)].cp_info
            return self._m_descriptor_as_info if hasattr(self, '_m_descriptor_as_info') else None

        @property
        def descriptor_as_str(self):
            if hasattr(self, '_m_descriptor_as_str'):
                return self._m_descriptor_as_str if hasattr(self, '_m_descriptor_as_str') else None

            self._m_descriptor_as_str = self.descriptor_as_info.value
            return self._m_descriptor_as_str if hasattr(self, '_m_descriptor_as_str') else None


    class Utf8CpInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4.7
        """
        SEQ_FIELDS = ["str_len", "value"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['str_len']['start'] = self._io.pos()
            self.str_len = self._io.read_u2be()
            self._debug['str_len']['end'] = self._io.pos()
            self._debug['value']['start'] = self._io.pos()
            self.value = (self._io.read_bytes(self.str_len)).decode(u"UTF-8")
            self._debug['value']['end'] = self._io.pos()


    class StringCpInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4.3
        """
        SEQ_FIELDS = ["string_index"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['string_index']['start'] = self._io.pos()
            self.string_index = self._io.read_u2be()
            self._debug['string_index']['end'] = self._io.pos()


    class MethodTypeCpInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4.9
        """
        SEQ_FIELDS = ["_unnamed0", "descriptor_index"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['_unnamed0']['start'] = self._io.pos()
            self._unnamed0 = JavaClass.VersionGuard(51, self._io, self, self._root)
            self._unnamed0._read()
            self._debug['_unnamed0']['end'] = self._io.pos()
            self._debug['descriptor_index']['start'] = self._io.pos()
            self.descriptor_index = self._io.read_u2be()
            self._debug['descriptor_index']['end'] = self._io.pos()


    class InterfaceMethodRefCpInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4.2
        """
        SEQ_FIELDS = ["class_index", "name_and_type_index"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['class_index']['start'] = self._io.pos()
            self.class_index = self._io.read_u2be()
            self._debug['class_index']['end'] = self._io.pos()
            self._debug['name_and_type_index']['start'] = self._io.pos()
            self.name_and_type_index = self._io.read_u2be()
            self._debug['name_and_type_index']['end'] = self._io.pos()

        @property
        def class_as_info(self):
            if hasattr(self, '_m_class_as_info'):
                return self._m_class_as_info if hasattr(self, '_m_class_as_info') else None

            self._m_class_as_info = self._root.constant_pool[(self.class_index - 1)].cp_info
            return self._m_class_as_info if hasattr(self, '_m_class_as_info') else None

        @property
        def name_and_type_as_info(self):
            if hasattr(self, '_m_name_and_type_as_info'):
                return self._m_name_and_type_as_info if hasattr(self, '_m_name_and_type_as_info') else None

            self._m_name_and_type_as_info = self._root.constant_pool[(self.name_and_type_index - 1)].cp_info
            return self._m_name_and_type_as_info if hasattr(self, '_m_name_and_type_as_info') else None


    class ClassCpInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4.1
        """
        SEQ_FIELDS = ["name_index"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['name_index']['start'] = self._io.pos()
            self.name_index = self._io.read_u2be()
            self._debug['name_index']['end'] = self._io.pos()

        @property
        def name_as_info(self):
            if hasattr(self, '_m_name_as_info'):
                return self._m_name_as_info if hasattr(self, '_m_name_as_info') else None

            self._m_name_as_info = self._root.constant_pool[(self.name_index - 1)].cp_info
            return self._m_name_as_info if hasattr(self, '_m_name_as_info') else None

        @property
        def name_as_str(self):
            if hasattr(self, '_m_name_as_str'):
                return self._m_name_as_str if hasattr(self, '_m_name_as_str') else None

            self._m_name_as_str = self.name_as_info.value
            return self._m_name_as_str if hasattr(self, '_m_name_as_str') else None


    class ConstantPoolEntry(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4
        """

        class TagEnum(Enum):
            utf8 = 1
            integer = 3
            float = 4
            long = 5
            double = 6
            class_type = 7
            string = 8
            field_ref = 9
            method_ref = 10
            interface_method_ref = 11
            name_and_type = 12
            method_handle = 15
            method_type = 16
            dynamic = 17
            invoke_dynamic = 18
            module = 19
            package = 20
        SEQ_FIELDS = ["tag", "cp_info"]
        def __init__(self, is_prev_two_entries, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.is_prev_two_entries = is_prev_two_entries
            self._debug = collections.defaultdict(dict)

        def _read(self):
            if not (self.is_prev_two_entries):
                self._debug['tag']['start'] = self._io.pos()
                self.tag = KaitaiStream.resolve_enum(JavaClass.ConstantPoolEntry.TagEnum, self._io.read_u1())
                self._debug['tag']['end'] = self._io.pos()

            if not (self.is_prev_two_entries):
                self._debug['cp_info']['start'] = self._io.pos()
                _on = self.tag
                if _on == JavaClass.ConstantPoolEntry.TagEnum.interface_method_ref:
                    self.cp_info = JavaClass.InterfaceMethodRefCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.class_type:
                    self.cp_info = JavaClass.ClassCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.dynamic:
                    self.cp_info = JavaClass.DynamicCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.utf8:
                    self.cp_info = JavaClass.Utf8CpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.method_type:
                    self.cp_info = JavaClass.MethodTypeCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.integer:
                    self.cp_info = JavaClass.IntegerCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.string:
                    self.cp_info = JavaClass.StringCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.float:
                    self.cp_info = JavaClass.FloatCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.module:
                    self.cp_info = JavaClass.ModulePackageCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.long:
                    self.cp_info = JavaClass.LongCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.method_ref:
                    self.cp_info = JavaClass.MethodRefCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.double:
                    self.cp_info = JavaClass.DoubleCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.invoke_dynamic:
                    self.cp_info = JavaClass.InvokeDynamicCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.field_ref:
                    self.cp_info = JavaClass.FieldRefCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.method_handle:
                    self.cp_info = JavaClass.MethodHandleCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.package:
                    self.cp_info = JavaClass.ModulePackageCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                elif _on == JavaClass.ConstantPoolEntry.TagEnum.name_and_type:
                    self.cp_info = JavaClass.NameAndTypeCpInfo(self._io, self, self._root)
                    self.cp_info._read()
                self._debug['cp_info']['end'] = self._io.pos()


        @property
        def is_two_entries(self):
            if hasattr(self, '_m_is_two_entries'):
                return self._m_is_two_entries if hasattr(self, '_m_is_two_entries') else None

            self._m_is_two_entries = (False if self.is_prev_two_entries else  ((self.tag == JavaClass.ConstantPoolEntry.TagEnum.long) or (self.tag == JavaClass.ConstantPoolEntry.TagEnum.double)) )
            return self._m_is_two_entries if hasattr(self, '_m_is_two_entries') else None


    class MethodInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.6
        """
        SEQ_FIELDS = ["access_flags", "name_index", "descriptor_index", "attributes_count", "attributes"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['access_flags']['start'] = self._io.pos()
            self.access_flags = self._io.read_u2be()
            self._debug['access_flags']['end'] = self._io.pos()
            self._debug['name_index']['start'] = self._io.pos()
            self.name_index = self._io.read_u2be()
            self._debug['name_index']['end'] = self._io.pos()
            self._debug['descriptor_index']['start'] = self._io.pos()
            self.descriptor_index = self._io.read_u2be()
            self._debug['descriptor_index']['end'] = self._io.pos()
            self._debug['attributes_count']['start'] = self._io.pos()
            self.attributes_count = self._io.read_u2be()
            self._debug['attributes_count']['end'] = self._io.pos()
            self._debug['attributes']['start'] = self._io.pos()
            self.attributes = [None] * (self.attributes_count)
            for i in range(self.attributes_count):
                if not 'arr' in self._debug['attributes']:
                    self._debug['attributes']['arr'] = []
                self._debug['attributes']['arr'].append({'start': self._io.pos()})
                _t_attributes = JavaClass.AttributeInfo(self._io, self, self._root)
                _t_attributes._read()
                self.attributes[i] = _t_attributes
                self._debug['attributes']['arr'][i]['end'] = self._io.pos()

            self._debug['attributes']['end'] = self._io.pos()

        @property
        def name_as_str(self):
            if hasattr(self, '_m_name_as_str'):
                return self._m_name_as_str if hasattr(self, '_m_name_as_str') else None

            self._m_name_as_str = self._root.constant_pool[(self.name_index - 1)].cp_info.value
            return self._m_name_as_str if hasattr(self, '_m_name_as_str') else None


    class IntegerCpInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4.4
        """
        SEQ_FIELDS = ["value"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['value']['start'] = self._io.pos()
            self.value = self._io.read_u4be()
            self._debug['value']['end'] = self._io.pos()


    class FieldRefCpInfo(KaitaiStruct):
        """
        .. seealso::
           Source - https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.4.2
        """
        SEQ_FIELDS = ["class_index", "name_and_type_index"]
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['class_index']['start'] = self._io.pos()
            self.class_index = self._io.read_u2be()
            self._debug['class_index']['end'] = self._io.pos()
            self._debug['name_and_type_index']['start'] = self._io.pos()
            self.name_and_type_index = self._io.read_u2be()
            self._debug['name_and_type_index']['end'] = self._io.pos()

        @property
        def class_as_info(self):
            if hasattr(self, '_m_class_as_info'):
                return self._m_class_as_info if hasattr(self, '_m_class_as_info') else None

            self._m_class_as_info = self._root.constant_pool[(self.class_index - 1)].cp_info
            return self._m_class_as_info if hasattr(self, '_m_class_as_info') else None

        @property
        def name_and_type_as_info(self):
            if hasattr(self, '_m_name_and_type_as_info'):
                return self._m_name_and_type_as_info if hasattr(self, '_m_name_and_type_as_info') else None

            self._m_name_and_type_as_info = self._root.constant_pool[(self.name_and_type_index - 1)].cp_info
            return self._m_name_and_type_as_info if hasattr(self, '_m_name_and_type_as_info') else None



