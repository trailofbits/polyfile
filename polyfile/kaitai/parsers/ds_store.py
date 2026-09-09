# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class DsStore(KaitaiStruct):
    """Apple macOS '.DS_Store' file format.
    
    .. seealso::
       Source - https://en.wikipedia.org/wiki/.DS_Store
    
    
    .. seealso::
       Source - https://metacpan.org/dist/Mac-Finder-DSStore/view/DSStoreFormat.pod
    
    
    .. seealso::
       Source - https://0day.work/parsing-the-ds_store-file-format/
    """
    SEQ_FIELDS = ["alignment_header", "buddy_allocator_header"]
    def __init__(self, _io, _parent=None, _root=None):
        super(DsStore, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['alignment_header']['start'] = self._io.pos()
        self.alignment_header = self._io.read_bytes(4)
        self._debug['alignment_header']['end'] = self._io.pos()
        if not self.alignment_header == b"\x00\x00\x00\x01":
            raise kaitaistruct.ValidationNotEqualError(b"\x00\x00\x00\x01", self.alignment_header, self._io, u"/seq/0")
        self._debug['buddy_allocator_header']['start'] = self._io.pos()
        self.buddy_allocator_header = DsStore.BuddyAllocatorHeader(self._io, self, self._root)
        self.buddy_allocator_header._read()
        self._debug['buddy_allocator_header']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        self.buddy_allocator_header._fetch_instances()
        _ = self.buddy_allocator_body
        if hasattr(self, '_m_buddy_allocator_body'):
            pass
            self._m_buddy_allocator_body._fetch_instances()


    class Block(KaitaiStruct):
        SEQ_FIELDS = ["mode", "counter", "data"]
        def __init__(self, _io, _parent=None, _root=None):
            super(DsStore.Block, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['mode']['start'] = self._io.pos()
            self.mode = self._io.read_u4be()
            self._debug['mode']['end'] = self._io.pos()
            self._debug['counter']['start'] = self._io.pos()
            self.counter = self._io.read_u4be()
            self._debug['counter']['end'] = self._io.pos()
            self._debug['data']['start'] = self._io.pos()
            self._debug['data']['arr'] = []
            self.data = []
            for i in range(self.counter):
                self._debug['data']['arr'].append({'start': self._io.pos()})
                _t_data = DsStore.Block.BlockData(self.mode, self._io, self, self._root)
                try:
                    _t_data._read()
                finally:
                    self.data.append(_t_data)
                self._debug['data']['arr'][i]['end'] = self._io.pos()

            self._debug['data']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.data)):
                pass
                self.data[i]._fetch_instances()

            _ = self.rightmost_block
            if hasattr(self, '_m_rightmost_block'):
                pass
                self._m_rightmost_block._fetch_instances()


        class BlockData(KaitaiStruct):
            SEQ_FIELDS = ["block_id", "record"]
            def __init__(self, mode, _io, _parent=None, _root=None):
                super(DsStore.Block.BlockData, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self.mode = mode
                self._debug = collections.defaultdict(dict)

            def _read(self):
                if self.mode > 0:
                    pass
                    self._debug['block_id']['start'] = self._io.pos()
                    self.block_id = self._io.read_u4be()
                    self._debug['block_id']['end'] = self._io.pos()

                self._debug['record']['start'] = self._io.pos()
                self.record = DsStore.Block.BlockData.Record(self._io, self, self._root)
                self.record._read()
                self._debug['record']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                if self.mode > 0:
                    pass

                self.record._fetch_instances()
                _ = self.block
                if hasattr(self, '_m_block'):
                    pass
                    self._m_block._fetch_instances()


            class Record(KaitaiStruct):
                SEQ_FIELDS = ["filename", "structure_type", "data_type", "value"]
                def __init__(self, _io, _parent=None, _root=None):
                    super(DsStore.Block.BlockData.Record, self).__init__(_io)
                    self._parent = _parent
                    self._root = _root
                    self._debug = collections.defaultdict(dict)

                def _read(self):
                    self._debug['filename']['start'] = self._io.pos()
                    self.filename = DsStore.Block.BlockData.Record.Ustr(self._io, self, self._root)
                    self.filename._read()
                    self._debug['filename']['end'] = self._io.pos()
                    self._debug['structure_type']['start'] = self._io.pos()
                    self.structure_type = DsStore.Block.BlockData.Record.FourCharCode(self._io, self, self._root)
                    self.structure_type._read()
                    self._debug['structure_type']['end'] = self._io.pos()
                    self._debug['data_type']['start'] = self._io.pos()
                    self.data_type = (self._io.read_bytes(4)).decode(u"UTF-8")
                    self._debug['data_type']['end'] = self._io.pos()
                    self._debug['value']['start'] = self._io.pos()
                    _on = self.data_type
                    if _on == u"blob":
                        pass
                        self.value = DsStore.Block.BlockData.Record.RecordBlob(self._io, self, self._root)
                        self.value._read()
                    elif _on == u"bool":
                        pass
                        self.value = self._io.read_u1()
                    elif _on == u"comp":
                        pass
                        self.value = self._io.read_u8be()
                    elif _on == u"dutc":
                        pass
                        self.value = self._io.read_u8be()
                    elif _on == u"long":
                        pass
                        self.value = self._io.read_u4be()
                    elif _on == u"shor":
                        pass
                        self.value = self._io.read_u4be()
                    elif _on == u"type":
                        pass
                        self.value = DsStore.Block.BlockData.Record.FourCharCode(self._io, self, self._root)
                        self.value._read()
                    elif _on == u"ustr":
                        pass
                        self.value = DsStore.Block.BlockData.Record.Ustr(self._io, self, self._root)
                        self.value._read()
                    self._debug['value']['end'] = self._io.pos()


                def _fetch_instances(self):
                    pass
                    self.filename._fetch_instances()
                    self.structure_type._fetch_instances()
                    _on = self.data_type
                    if _on == u"blob":
                        pass
                        self.value._fetch_instances()
                    elif _on == u"bool":
                        pass
                    elif _on == u"comp":
                        pass
                    elif _on == u"dutc":
                        pass
                    elif _on == u"long":
                        pass
                    elif _on == u"shor":
                        pass
                    elif _on == u"type":
                        pass
                        self.value._fetch_instances()
                    elif _on == u"ustr":
                        pass
                        self.value._fetch_instances()

                class FourCharCode(KaitaiStruct):
                    SEQ_FIELDS = ["value"]
                    def __init__(self, _io, _parent=None, _root=None):
                        super(DsStore.Block.BlockData.Record.FourCharCode, self).__init__(_io)
                        self._parent = _parent
                        self._root = _root
                        self._debug = collections.defaultdict(dict)

                    def _read(self):
                        self._debug['value']['start'] = self._io.pos()
                        self.value = (self._io.read_bytes(4)).decode(u"UTF-8")
                        self._debug['value']['end'] = self._io.pos()


                    def _fetch_instances(self):
                        pass


                class RecordBlob(KaitaiStruct):
                    SEQ_FIELDS = ["length", "value"]
                    def __init__(self, _io, _parent=None, _root=None):
                        super(DsStore.Block.BlockData.Record.RecordBlob, self).__init__(_io)
                        self._parent = _parent
                        self._root = _root
                        self._debug = collections.defaultdict(dict)

                    def _read(self):
                        self._debug['length']['start'] = self._io.pos()
                        self.length = self._io.read_u4be()
                        self._debug['length']['end'] = self._io.pos()
                        self._debug['value']['start'] = self._io.pos()
                        self.value = self._io.read_bytes(self.length)
                        self._debug['value']['end'] = self._io.pos()


                    def _fetch_instances(self):
                        pass


                class Ustr(KaitaiStruct):
                    SEQ_FIELDS = ["length", "value"]
                    def __init__(self, _io, _parent=None, _root=None):
                        super(DsStore.Block.BlockData.Record.Ustr, self).__init__(_io)
                        self._parent = _parent
                        self._root = _root
                        self._debug = collections.defaultdict(dict)

                    def _read(self):
                        self._debug['length']['start'] = self._io.pos()
                        self.length = self._io.read_u4be()
                        self._debug['length']['end'] = self._io.pos()
                        self._debug['value']['start'] = self._io.pos()
                        self.value = (self._io.read_bytes(2 * self.length)).decode(u"UTF-16BE")
                        self._debug['value']['end'] = self._io.pos()


                    def _fetch_instances(self):
                        pass



            @property
            def block(self):
                if hasattr(self, '_m_block'):
                    return self._m_block

                if self.mode > 0:
                    pass
                    io = self._root._io
                    _pos = io.pos()
                    io.seek(self._root.buddy_allocator_body.block_addresses[self.block_id].offset)
                    self._debug['_m_block']['start'] = io.pos()
                    self._m_block = DsStore.Block(io, self, self._root)
                    self._m_block._read()
                    self._debug['_m_block']['end'] = io.pos()
                    io.seek(_pos)

                return getattr(self, '_m_block', None)


        @property
        def rightmost_block(self):
            """Rightmost child block pointer."""
            if hasattr(self, '_m_rightmost_block'):
                return self._m_rightmost_block

            if self.mode > 0:
                pass
                io = self._root._io
                _pos = io.pos()
                io.seek(self._root.buddy_allocator_body.block_addresses[self.mode].offset)
                self._debug['_m_rightmost_block']['start'] = io.pos()
                self._m_rightmost_block = DsStore.Block(io, self, self._root)
                self._m_rightmost_block._read()
                self._debug['_m_rightmost_block']['end'] = io.pos()
                io.seek(_pos)

            return getattr(self, '_m_rightmost_block', None)


    class BuddyAllocatorBody(KaitaiStruct):
        SEQ_FIELDS = ["num_blocks", "_unnamed1", "block_addresses", "num_directories", "directory_entries", "free_lists"]
        def __init__(self, _io, _parent=None, _root=None):
            super(DsStore.BuddyAllocatorBody, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['num_blocks']['start'] = self._io.pos()
            self.num_blocks = self._io.read_u4be()
            self._debug['num_blocks']['end'] = self._io.pos()
            self._debug['_unnamed1']['start'] = self._io.pos()
            self._unnamed1 = self._io.read_bytes(4)
            self._debug['_unnamed1']['end'] = self._io.pos()
            self._debug['block_addresses']['start'] = self._io.pos()
            self._debug['block_addresses']['arr'] = []
            self.block_addresses = []
            for i in range(self.num_block_addresses):
                self._debug['block_addresses']['arr'].append({'start': self._io.pos()})
                _t_block_addresses = DsStore.BuddyAllocatorBody.BlockDescriptor(self._io, self, self._root)
                try:
                    _t_block_addresses._read()
                finally:
                    self.block_addresses.append(_t_block_addresses)
                self._debug['block_addresses']['arr'][i]['end'] = self._io.pos()

            self._debug['block_addresses']['end'] = self._io.pos()
            self._debug['num_directories']['start'] = self._io.pos()
            self.num_directories = self._io.read_u4be()
            self._debug['num_directories']['end'] = self._io.pos()
            self._debug['directory_entries']['start'] = self._io.pos()
            self._debug['directory_entries']['arr'] = []
            self.directory_entries = []
            for i in range(self.num_directories):
                self._debug['directory_entries']['arr'].append({'start': self._io.pos()})
                _t_directory_entries = DsStore.BuddyAllocatorBody.DirectoryEntry(self._io, self, self._root)
                try:
                    _t_directory_entries._read()
                finally:
                    self.directory_entries.append(_t_directory_entries)
                self._debug['directory_entries']['arr'][i]['end'] = self._io.pos()

            self._debug['directory_entries']['end'] = self._io.pos()
            self._debug['free_lists']['start'] = self._io.pos()
            self._debug['free_lists']['arr'] = []
            self.free_lists = []
            for i in range(self.num_free_lists):
                self._debug['free_lists']['arr'].append({'start': self._io.pos()})
                _t_free_lists = DsStore.BuddyAllocatorBody.FreeList(self._io, self, self._root)
                try:
                    _t_free_lists._read()
                finally:
                    self.free_lists.append(_t_free_lists)
                self._debug['free_lists']['arr'][i]['end'] = self._io.pos()

            self._debug['free_lists']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            for i in range(len(self.block_addresses)):
                pass
                self.block_addresses[i]._fetch_instances()

            for i in range(len(self.directory_entries)):
                pass
                self.directory_entries[i]._fetch_instances()

            for i in range(len(self.free_lists)):
                pass
                self.free_lists[i]._fetch_instances()

            _ = self.directories
            if hasattr(self, '_m_directories'):
                pass
                for i in range(len(self._m_directories)):
                    pass
                    self._m_directories[i]._fetch_instances()



        class BlockDescriptor(KaitaiStruct):
            SEQ_FIELDS = ["address_raw"]
            def __init__(self, _io, _parent=None, _root=None):
                super(DsStore.BuddyAllocatorBody.BlockDescriptor, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['address_raw']['start'] = self._io.pos()
                self.address_raw = self._io.read_u4be()
                self._debug['address_raw']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass

            @property
            def offset(self):
                if hasattr(self, '_m_offset'):
                    return self._m_offset

                self._m_offset = (self.address_raw & ~(self._root.block_address_mask)) + 4
                return getattr(self, '_m_offset', None)

            @property
            def size(self):
                if hasattr(self, '_m_size'):
                    return self._m_size

                self._m_size = 1 << (self.address_raw & self._root.block_address_mask)
                return getattr(self, '_m_size', None)


        class DirectoryEntry(KaitaiStruct):
            SEQ_FIELDS = ["len_name", "name", "block_id"]
            def __init__(self, _io, _parent=None, _root=None):
                super(DsStore.BuddyAllocatorBody.DirectoryEntry, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['len_name']['start'] = self._io.pos()
                self.len_name = self._io.read_u1()
                self._debug['len_name']['end'] = self._io.pos()
                self._debug['name']['start'] = self._io.pos()
                self.name = (self._io.read_bytes(self.len_name)).decode(u"UTF-8")
                self._debug['name']['end'] = self._io.pos()
                self._debug['block_id']['start'] = self._io.pos()
                self.block_id = self._io.read_u4be()
                self._debug['block_id']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass


        class FreeList(KaitaiStruct):
            SEQ_FIELDS = ["counter", "offsets"]
            def __init__(self, _io, _parent=None, _root=None):
                super(DsStore.BuddyAllocatorBody.FreeList, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['counter']['start'] = self._io.pos()
                self.counter = self._io.read_u4be()
                self._debug['counter']['end'] = self._io.pos()
                self._debug['offsets']['start'] = self._io.pos()
                self._debug['offsets']['arr'] = []
                self.offsets = []
                for i in range(self.counter):
                    self._debug['offsets']['arr'].append({'start': self._io.pos()})
                    self.offsets.append(self._io.read_u4be())
                    self._debug['offsets']['arr'][i]['end'] = self._io.pos()

                self._debug['offsets']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                for i in range(len(self.offsets)):
                    pass



        @property
        def directories(self):
            """Master blocks of the different B-trees."""
            if hasattr(self, '_m_directories'):
                return self._m_directories

            io = self._root._io
            self._debug['_m_directories']['start'] = io.pos()
            self._debug['_m_directories']['arr'] = []
            self._m_directories = []
            for i in range(self.num_directories):
                self._debug['_m_directories']['arr'].append({'start': io.pos()})
                _t__m_directories = DsStore.MasterBlockRef(i, io, self, self._root)
                try:
                    _t__m_directories._read()
                finally:
                    self._m_directories.append(_t__m_directories)
                self._debug['_m_directories']['arr'][i]['end'] = io.pos()

            self._debug['_m_directories']['end'] = io.pos()
            return getattr(self, '_m_directories', None)

        @property
        def num_block_addresses(self):
            if hasattr(self, '_m_num_block_addresses'):
                return self._m_num_block_addresses

            self._m_num_block_addresses = 256
            return getattr(self, '_m_num_block_addresses', None)

        @property
        def num_free_lists(self):
            if hasattr(self, '_m_num_free_lists'):
                return self._m_num_free_lists

            self._m_num_free_lists = 32
            return getattr(self, '_m_num_free_lists', None)


    class BuddyAllocatorHeader(KaitaiStruct):
        SEQ_FIELDS = ["magic", "ofs_bookkeeping_info_block", "len_bookkeeping_info_block", "copy_ofs_bookkeeping_info_block", "_unnamed4"]
        def __init__(self, _io, _parent=None, _root=None):
            super(DsStore.BuddyAllocatorHeader, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['magic']['start'] = self._io.pos()
            self.magic = self._io.read_bytes(4)
            self._debug['magic']['end'] = self._io.pos()
            if not self.magic == b"\x42\x75\x64\x31":
                raise kaitaistruct.ValidationNotEqualError(b"\x42\x75\x64\x31", self.magic, self._io, u"/types/buddy_allocator_header/seq/0")
            self._debug['ofs_bookkeeping_info_block']['start'] = self._io.pos()
            self.ofs_bookkeeping_info_block = self._io.read_u4be()
            self._debug['ofs_bookkeeping_info_block']['end'] = self._io.pos()
            self._debug['len_bookkeeping_info_block']['start'] = self._io.pos()
            self.len_bookkeeping_info_block = self._io.read_u4be()
            self._debug['len_bookkeeping_info_block']['end'] = self._io.pos()
            self._debug['copy_ofs_bookkeeping_info_block']['start'] = self._io.pos()
            self.copy_ofs_bookkeeping_info_block = self._io.read_u4be()
            self._debug['copy_ofs_bookkeeping_info_block']['end'] = self._io.pos()
            self._debug['_unnamed4']['start'] = self._io.pos()
            self._unnamed4 = self._io.read_bytes(16)
            self._debug['_unnamed4']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass


    class MasterBlockRef(KaitaiStruct):
        SEQ_FIELDS = []
        def __init__(self, idx, _io, _parent=None, _root=None):
            super(DsStore.MasterBlockRef, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self.idx = idx
            self._debug = collections.defaultdict(dict)

        def _read(self):
            pass


        def _fetch_instances(self):
            pass
            _ = self.master_block
            if hasattr(self, '_m_master_block'):
                pass
                self._m_master_block._fetch_instances()


        class MasterBlock(KaitaiStruct):
            SEQ_FIELDS = ["block_id", "num_internal_nodes", "num_records", "num_nodes", "_unnamed4"]
            def __init__(self, _io, _parent=None, _root=None):
                super(DsStore.MasterBlockRef.MasterBlock, self).__init__(_io)
                self._parent = _parent
                self._root = _root
                self._debug = collections.defaultdict(dict)

            def _read(self):
                self._debug['block_id']['start'] = self._io.pos()
                self.block_id = self._io.read_u4be()
                self._debug['block_id']['end'] = self._io.pos()
                self._debug['num_internal_nodes']['start'] = self._io.pos()
                self.num_internal_nodes = self._io.read_u4be()
                self._debug['num_internal_nodes']['end'] = self._io.pos()
                self._debug['num_records']['start'] = self._io.pos()
                self.num_records = self._io.read_u4be()
                self._debug['num_records']['end'] = self._io.pos()
                self._debug['num_nodes']['start'] = self._io.pos()
                self.num_nodes = self._io.read_u4be()
                self._debug['num_nodes']['end'] = self._io.pos()
                self._debug['_unnamed4']['start'] = self._io.pos()
                self._unnamed4 = self._io.read_u4be()
                self._debug['_unnamed4']['end'] = self._io.pos()


            def _fetch_instances(self):
                pass
                _ = self.root_block
                if hasattr(self, '_m_root_block'):
                    pass
                    self._m_root_block._fetch_instances()


            @property
            def root_block(self):
                if hasattr(self, '_m_root_block'):
                    return self._m_root_block

                io = self._root._io
                _pos = io.pos()
                io.seek(self._root.buddy_allocator_body.block_addresses[self.block_id].offset)
                self._debug['_m_root_block']['start'] = io.pos()
                self._m_root_block = DsStore.Block(io, self, self._root)
                self._m_root_block._read()
                self._debug['_m_root_block']['end'] = io.pos()
                io.seek(_pos)
                return getattr(self, '_m_root_block', None)


        @property
        def master_block(self):
            if hasattr(self, '_m_master_block'):
                return self._m_master_block

            _pos = self._io.pos()
            self._io.seek(self._parent.block_addresses[self._parent.directory_entries[self.idx].block_id].offset)
            self._debug['_m_master_block']['start'] = self._io.pos()
            self._raw__m_master_block = self._io.read_bytes(self._parent.block_addresses[self._parent.directory_entries[self.idx].block_id].size)
            _io__raw__m_master_block = KaitaiStream(BytesIO(self._raw__m_master_block))
            self._m_master_block = DsStore.MasterBlockRef.MasterBlock(_io__raw__m_master_block, self, self._root)
            self._m_master_block._read()
            self._debug['_m_master_block']['end'] = self._io.pos()
            self._io.seek(_pos)
            return getattr(self, '_m_master_block', None)


    @property
    def block_address_mask(self):
        """Bitmask used to calculate the position and the size of each block
        of the B-tree from the block addresses.
        """
        if hasattr(self, '_m_block_address_mask'):
            return self._m_block_address_mask

        self._m_block_address_mask = 31
        return getattr(self, '_m_block_address_mask', None)

    @property
    def buddy_allocator_body(self):
        if hasattr(self, '_m_buddy_allocator_body'):
            return self._m_buddy_allocator_body

        _pos = self._io.pos()
        self._io.seek(self.buddy_allocator_header.ofs_bookkeeping_info_block + 4)
        self._debug['_m_buddy_allocator_body']['start'] = self._io.pos()
        self._raw__m_buddy_allocator_body = self._io.read_bytes(self.buddy_allocator_header.len_bookkeeping_info_block)
        _io__raw__m_buddy_allocator_body = KaitaiStream(BytesIO(self._raw__m_buddy_allocator_body))
        self._m_buddy_allocator_body = DsStore.BuddyAllocatorBody(_io__raw__m_buddy_allocator_body, self, self._root)
        self._m_buddy_allocator_body._read()
        self._debug['_m_buddy_allocator_body']['end'] = self._io.pos()
        self._io.seek(_pos)
        return getattr(self, '_m_buddy_allocator_body', None)


