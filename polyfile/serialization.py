from enum import Enum
import io
from itertools import chain


def write_int(i:int, stream):
    bits = max(i.bit_length(), 1)
    for bit_group in reversed(range((bits - 1) // 7 + 1)):
        b = (i >> (bit_group * 7)) & 0b01111111
        if bit_group == 0:
            b |= 0b10000000
        stream.write(bytes([b]))


def read_int(stream):
    i = 0
    while True:
        i <<= 7
        b = ord(stream.read(1))
        i |= (b & 0b01111111)
        if b & 0b10000000:
            break
    return i

ENCODINGS_BY_TYPE = {}
ENCODINGS_BY_ID = {}


def encode_int(i, _, stream):
    write_int(i, stream)


def decode_int(_, stream):
    return read_int(stream)


def encode_bytes(s, _, stream):
    write_int(len(s), stream)
    stream.write(s)


def encode_string(s:str, _, stream):
    encode_bytes(s.encode('utf-8'), None, stream)


def decode_bytes(_, stream):
    length = read_int(stream)
    return stream.read(length)


def decode_string(_, stream):
    return decode_bytes(None, stream).decode('utf-8')


def encode_list(lst, obj_ids, stream):
    write_int(len(lst), stream)
    for obj in lst:
        write_int(obj_ids[id(obj)], stream)


encode_tuple = encode_list


encode_set = encode_list


def decode_list(objs, stream):
    length = read_int(stream)
    return [objs[read_int(stream)] for _ in range(length)]


def decode_tuple(*args, **kwargs):
    return tuple(decode_list(*args, **kwargs))


def decode_set(*args, **kwargs):
    return set(decode_list(*args, **kwargs))


def encode_dict(d: dict, obj_ids, stream):
    write_int(len(d), stream)
    for k, v in d.items():
        write_int(obj_ids[id(k)], stream)
        write_int(obj_ids[id(v)], stream)


def decode_dict(objs, stream):
    length = read_int(stream)
    # We can't use a dict comprenension here because the interpreter
    # isn't guaranteed to evaluate the key before the value
    return dict((objs[read_int(stream)], objs[read_int(stream)]) for _ in range(length))


class EncodeTypes(Enum):
    INT = (0, int, encode_int, decode_int, lambda _: ())
    STRING = (1, str, encode_string, decode_string, lambda _: ())
    BYTES = (2, bytes, encode_bytes, decode_bytes, lambda _: ())
    LIST = (3, list, encode_list, decode_list, iter)
    TUPLE = (4, tuple, encode_tuple, decode_tuple, iter)
    DICT = (5, dict, encode_dict, decode_dict, lambda d: chain(d.keys(), d.values()))
    SET = (6, set, None, None, iter)

    def __init__(self, encoding_id, source_type, encoding_function, decoding_function, children):
        self.encoding_id = encoding_id
        self.source_type = source_type
        self.encode = encoding_function
        self.decode = decoding_function
        self.children = children
        ENCODINGS_BY_TYPE[self.source_type] = self
        ENCODINGS_BY_ID[self.encoding_id] = self

    @staticmethod
    def get_by_type(source_type):
        if source_type not in ENCODINGS_BY_TYPE:
            return None
        return ENCODINGS_BY_TYPE[source_type]

    @staticmethod
    def get_by_id(encoding_id):
        if encoding_id not in ENCODINGS_BY_ID:
            return None
        return ENCODINGS_BY_ID[encoding_id]


class EncodingError(RuntimeError):
    def __init__(self, *args):
        super().__init__(*args)


def encode(obj, stream):
    stack = [obj]
    obj_ids = {}
    objs = []

    # Do a DFS traversal to assign IDs
    while stack:
        s = stack.pop()
        encoding = EncodeTypes.get_by_type(type(s))
        if encoding is None:
            raise EncodingError(f"No encoding implemented for objects of type {type(s)}")
        already_expanded = id(s) in obj_ids
        if already_expanded:
            old_id = obj_ids[id(s)]
        new_id = len(objs)
        obj_ids[id(s)] = new_id
        objs.append((s, new_id, encoding))
        if already_expanded:
            objs[old_id] = (None, None, None)
        else:
            stack.extend(encoding.children(s))

    # write the objects to the stream in reverse
    for s, obj_id, encoding in reversed(objs):
        if obj_id is None:
            # This object was referenced twice, and this was a duplicate
            continue
        write_int(obj_id, stream)
        write_int(encoding.encoding_id, stream)
        encoding.encode(s, obj_ids, stream)


def decode(stream):
    objs = {}
    while True:
        b = stream.read(1)
        if b is None or not b:
            break
        stream.seek(-1, 1)
        obj_id = read_int(stream)
        assert obj_id not in objs
        encoding_id = read_int(stream)
        encoding = EncodeTypes.get_by_id(encoding_id)
        if encoding is None:
            raise EncodingError(f"Unexpected encoded object of type #{obj_id}")
        objs[obj_id] = encoding.decode(objs, stream)
    return objs[0]


def dump(obj, stream):
    return encode(obj, stream)


def load(stream):
    return decode(stream)


def dumps(obj):
    stream = io.BytesIO()
    dump(obj, stream)
    return stream.getvalue()


def loads(string:bytes):
    with io.BytesIO(string) as stream:
        return load(stream)


if __name__ == '__main__':
    test_obj = {
        'testing': {
            'foo': 10,
            'bar': [1, 2, 3, b'1234\xFF']
        },
        'baz': [
            'a', 'b', 'c',
            {'d': 5}
        ]
    }
    #print(test_obj)
    #encoded = encode(test_obj)
    #print(encoded)
    #decoded = decode(encoded)
    #print(decoded)
    for i in range(0, 2048):
        assert loads(dumps(i)) == i

    b = b"The quick brown fox jumps over the lazy dog"
    s = b.decode('utf-8')
    assert loads(dumps(b)) == b
    assert loads(dumps(s)) == s

    lst = list(range(1024))
    assert loads(dumps(lst)) == lst

    print(loads(dumps(test_obj)))
