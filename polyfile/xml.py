from .fileutils import FileStream


class Token:
    def __init__(self, token, offset):
        self.token = token
        self.offset = offset

    def __len__(self):
        return len(self.token)

    def __repr__(self):
        return f"{self.__class__.__name__!s}(token={self.token!r}, offset={self.offset!r})"


def whitespace(file_stream: FileStream):
    start = file_stream.tell()
    token = bytearray()
    while file_stream.peek(1) in (b'\x20', b'\x09', b'\x0D', b'\x0A'):
        token.append(file_stream.read(1)[0])
    if token:
        return Token(token, start)
    else:
        return None


def char(file_stream: FileStream):
    byte = file_stream.peek(1)
    if len(byte) == 0:
        return None
    b = byte[0]
    if (0x1 <= b <= 0xD7FF) or (0xE000 <= b <= 0xFFFD) or (0x10000 <= b <= 0x10FFFF):
        start = file_stream.tell()
        file_stream.read(1)
        return Token(byte, start)
    return None


if __name__ == '__main__':
    from .fileutils import make_stream, Tempfile

    with Tempfile(b'    ') as t:
        print(whitespace(make_stream(t)))
