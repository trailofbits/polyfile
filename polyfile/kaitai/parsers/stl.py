# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
import collections


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Stl(KaitaiStruct):
    """STL files are used to represent simple 3D models, defined using
    triangular 3D faces.
    
    Initially it was introduced as native format for 3D Systems
    Stereolithography CAD system, but due to its extreme simplicity, it
    was adopted by a wide range of 3D modelling, CAD, rapid prototyping
    and 3D printing applications as the simplest 3D model exchange
    format.
    
    STL is extremely bare-bones format: there are no complex headers, no
    texture / color support, no units specifications, no distinct vertex
    arrays. Whole model is specified as a collection of triangular
    faces.
    
    There are two versions of the format (text and binary), this spec
    describes binary version.
    """
    SEQ_FIELDS = ["header", "num_triangles", "triangles"]
    def __init__(self, _io, _parent=None, _root=None):
        super(Stl, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._debug = collections.defaultdict(dict)

    def _read(self):
        self._debug['header']['start'] = self._io.pos()
        self.header = self._io.read_bytes(80)
        self._debug['header']['end'] = self._io.pos()
        self._debug['num_triangles']['start'] = self._io.pos()
        self.num_triangles = self._io.read_u4le()
        self._debug['num_triangles']['end'] = self._io.pos()
        self._debug['triangles']['start'] = self._io.pos()
        self._debug['triangles']['arr'] = []
        self.triangles = []
        for i in range(self.num_triangles):
            self._debug['triangles']['arr'].append({'start': self._io.pos()})
            _t_triangles = Stl.Triangle(self._io, self, self._root)
            try:
                _t_triangles._read()
            finally:
                self.triangles.append(_t_triangles)
            self._debug['triangles']['arr'][i]['end'] = self._io.pos()

        self._debug['triangles']['end'] = self._io.pos()


    def _fetch_instances(self):
        pass
        for i in range(len(self.triangles)):
            pass
            self.triangles[i]._fetch_instances()


    class Triangle(KaitaiStruct):
        """Each STL triangle is defined by its 3 points in 3D space and a
        normal vector, which is generally used to determine where is
        "inside" and "outside" of the model.
        """
        SEQ_FIELDS = ["normal", "vertices", "abr"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Stl.Triangle, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['normal']['start'] = self._io.pos()
            self.normal = Stl.Vec3d(self._io, self, self._root)
            self.normal._read()
            self._debug['normal']['end'] = self._io.pos()
            self._debug['vertices']['start'] = self._io.pos()
            self._debug['vertices']['arr'] = []
            self.vertices = []
            for i in range(3):
                self._debug['vertices']['arr'].append({'start': self._io.pos()})
                _t_vertices = Stl.Vec3d(self._io, self, self._root)
                try:
                    _t_vertices._read()
                finally:
                    self.vertices.append(_t_vertices)
                self._debug['vertices']['arr'][i]['end'] = self._io.pos()

            self._debug['vertices']['end'] = self._io.pos()
            self._debug['abr']['start'] = self._io.pos()
            self.abr = self._io.read_u2le()
            self._debug['abr']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass
            self.normal._fetch_instances()
            for i in range(len(self.vertices)):
                pass
                self.vertices[i]._fetch_instances()



    class Vec3d(KaitaiStruct):
        SEQ_FIELDS = ["x", "y", "z"]
        def __init__(self, _io, _parent=None, _root=None):
            super(Stl.Vec3d, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._debug = collections.defaultdict(dict)

        def _read(self):
            self._debug['x']['start'] = self._io.pos()
            self.x = self._io.read_f4le()
            self._debug['x']['end'] = self._io.pos()
            self._debug['y']['start'] = self._io.pos()
            self.y = self._io.read_f4le()
            self._debug['y']['end'] = self._io.pos()
            self._debug['z']['start'] = self._io.pos()
            self.z = self._io.read_f4le()
            self._debug['z']['end'] = self._io.pos()


        def _fetch_instances(self):
            pass



