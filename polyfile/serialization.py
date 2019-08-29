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
CUSTOM_ENCODINGS = {}
CUSTOM_ENCODINGS_BY_ID = {}


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
    for obj in lst:
        write_int(obj_ids[id(obj)], stream)
    write_int(EncodeTypes.END.encoding_id, stream)


encode_tuple = encode_list


encode_set = encode_list


encode_frozenset = encode_list


def _decode_to_end(stream):
    while True:
        i = read_int(stream)
        if i == EncodeTypes.END.encoding_id:
            break
        yield i


def pairwise(iterable):
    while True:
        try:
            a, b = next(iterable), next(iterable)
        except StopIteration:
            break
        yield a, b


def decode_list(objs, stream):
    return [objs[i] for i in _decode_to_end(stream)]


def decode_tuple(*args, **kwargs):
    return tuple(decode_list(*args, **kwargs))


def decode_set(*args, **kwargs):
    return set(decode_list(*args, **kwargs))


def decode_frozenset(*args, **kwargs):
    return frozenset(decode_list(*args, **kwargs))


def encode_dict(d: dict, obj_ids, stream):
    for k, v in d.items():
        write_int(obj_ids[id(k)], stream)
        write_int(obj_ids[id(v)], stream)
    write_int(EncodeTypes.END.encoding_id, stream)


def decode_dict(objs, stream):
    return {objs[k]: objs[v] for k, v in pairwise(_decode_to_end(stream))}


def encode_none(*args, **kwargs):
    pass


def decode_none(*args, **kwargs):
    return None


def encode_bool(b: bool, _, stream):
    write_int(int(b), stream)


def decode_bool(_, stream):
    return bool(read_int(stream))


def encode_custom(c, obj_ids, stream):
    write_int(CUSTOM_ENCODINGS[type(c)], stream)
    encode_list(c.serialize(), obj_ids, stream)


def decode_custom(objs, stream):
    custom_type = CUSTOM_ENCODINGS_BY_ID[read_int(stream)]
    args = decode_list(objs, stream)
    return custom_type(*args)


class _EndObject:
    pass


class _CustomObject:
    pass


def serializable(SerializableClass):
    if not hasattr(SerializableClass, 'serialize'):
        raise ValueError(f'Serializable class {SerializableClass} must implement the `serialize` member function')
    new_id = len(CUSTOM_ENCODINGS)
    CUSTOM_ENCODINGS[SerializableClass] = new_id
    CUSTOM_ENCODINGS_BY_ID[new_id] = SerializableClass
    return SerializableClass


class EncodeTypes(Enum):
    END = (0, _EndObject, None, None, None)
    NONE = (1, type(None), encode_none, decode_none, lambda _: ())
    BOOL = (2, bool, encode_bool, decode_bool, lambda _: ())
    INT = (3, int, encode_int, decode_int, lambda _: ())
    STRING = (4, str, encode_string, decode_string, lambda _: ())
    BYTES = (5, bytes, encode_bytes, decode_bytes, lambda _: ())
    LIST = (6, list, encode_list, decode_list, iter)
    TUPLE = (7, tuple, encode_tuple, decode_tuple, iter)
    DICT = (8, dict, encode_dict, decode_dict, lambda d: chain(d.keys(), d.values()))
    SET = (9, set, encode_set, decode_set, iter)
    FROZENSET = (10, frozenset, encode_frozenset, decode_frozenset, iter)
    CUSTOM = (11, _CustomObject, encode_custom, decode_custom, lambda c: c.serialize())

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
    # Object ID 0 is reserved
    obj_ids = {
        0: None
    }
    objs = [
        (None, None)
    ]

    # Do a DFS traversal to assign IDs
    while stack:
        s = stack.pop()
        encoding = EncodeTypes.get_by_type(type(s))
        if encoding is None:
            # See if there is a custom encoding:
            if type(s) in CUSTOM_ENCODINGS:
                encoding = EncodeTypes.CUSTOM
            else:
                raise EncodingError(f"No encoding implemented for objects of type {type(s)}")
        already_expanded = id(s) in obj_ids
        if already_expanded:
            old_id = obj_ids[id(s)]
        # We add one to new_id here because obj_id zero is reserved
        new_id = len(objs)
        obj_ids[id(s)] = new_id
        objs.append((s, encoding))
        if already_expanded:
            objs[old_id] = (None, None)
            # Remove all of the dependencies, since they now need to be added after:
            # TODO: eventually do cycle detection here, and throw an error instead of livelock
            for child in encoding.children(s):
                if id(child) in obj_ids:
                    objs[obj_ids[id(child)]] = (None, None)
                    del obj_ids[id(child)]
        stack.extend(encoding.children(s))

    # write the objects to the stream in reverse
    n = len(objs)
    for i, (s, encoding) in enumerate(reversed(objs)):
        obj_id = n - i - 1
        if encoding is None:
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
    return objs[1]


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
    ref = ["list", "used", "twice"]
    test_obj = {
        'testing': {
            'foo': {10},
            'bar': [1, 2, 3, b'1234\xFF', True, False],
            'ref': ref
        },
        'baz': [
            'a', ('b',), 'c',
            {'d': 5},
            None,
            frozenset([1, 1, 2, 3, 5, 8])
        ],
        'ref': ref
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

    encoded = dumps(test_obj)
    print(f"Encoded bytes: {len(encoded)}")

    print(loads(encoded))
