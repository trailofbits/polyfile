import base64
import json


def encode(obj):
    stack = [(0, obj)]
    ret = {
        'b64': []
    }
    num_ids = 1
    while stack:
        uid, i = stack.pop()
        assert uid not in ret
        if isinstance(i, dict):
            ret[uid] = {k: j + num_ids for j, k in enumerate(i.keys())}
            stack.extend((j + num_ids, v) for j, v in enumerate(i.values()))
            num_ids += len(i)
        elif isinstance(i, list):
            ret[uid] = [num_ids + j for j, _ in enumerate(i)]
            stack.extend((num_ids + j, v) for j, v in enumerate(i))
            num_ids += len(i)
        elif isinstance(i, bytes):
            ret[uid] = base64.b64encode(i).decode('utf-8')
            ret['b64'].append(uid)
        else:
            ret[uid] = i
    return ret


def decode(obj):
    for uid in obj['b64']:
        obj[uid] = base64.b64decode(obj[uid])
    stack = [obj[0]]
    while stack:
        i = stack.pop()
        if isinstance(i, dict):
            for k, v in i.items():
                i[k] = obj[v]
                stack.append(obj[v])
        elif isinstance(i, list):
            stack.extend(list(i))
            for j in range(len(i)):
                i[j] = obj[i[j]]
    return obj[0]


def dump(obj, stream):
    return json.dump(encode(obj), stream)


def load(*args, **kwargs):
    return decode(json.load(*args, **kwargs))


def dumps(string):
    return json.dumps(encode(string))


def loads(string):
    return decode(json.loads(string))


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
    print(test_obj)
    encoded = encode(test_obj)
    print(encoded)
    decoded = decode(encoded)
    print(decoded)
