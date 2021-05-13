import base64
import math
import mimetypes
import os
import unicodedata

jinja2 = None


TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')
TEMPLATE = None


def assign_ids(sbud):
    i = 0
    matches = list(sbud['struc'])
    stack = list(matches)
    while stack:
        m = stack.pop()
        assert 'uid' not in m
        m['uid'] = i
        i += 1
        stack += list(m['subEls'])
    return matches


def generate(file_path, sbud):
    global TEMPLATE, jinja2
    if jinja2 is None:
        # Dynamically load jinja2 at runtime so it is not an installation dependency for setup.py
        import jinja2 as j2
        jinja2 = j2

    if TEMPLATE is None:
        TEMPLATE = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR)).get_template('template.html')

    matches = assign_ids(sbud)

    input_bytes = sbud['length']
    with open(file_path, 'rb') as input_file:
        class ReadUnicode():
            def __init__(self):
                self.reset = False

            def tell(self):
                if not self.reset:
                    return 0
                else:
                    return input_file.tell()

            def translate(self, b, monospace=True):
                if b is None or len(b) == 0 or b == b' ':
                    return '&nbsp;'
                elif b == b'\n':
                    if monospace:
                        return '\u2424'
                    else:
                        return '\u2424</span><br /><span>'
                elif b == b'\t':
                    if monospace:
                        return b'\xE2\xAD\xBE'
                    else:
                        return '\t'
                elif b == b'\r':
                    return '\u240d'
                try:
                    u = b.decode('utf-8')
                    if unicodedata.category(u) == 'Cc':
                        # This is a control character
                        return '\ufffd'
                    else:
                        return u
                except UnicodeDecodeError:
                    return '\ufffd'

            def __iter__(self):
                input_file.seek(0)
                i = 0
                while True:
                    b = input_file.read(1)
                    if b is None or len(b) < 1:
                        break
                    yield i, self.translate(b, monospace=False)
                    i += 1

            def __call__(self):
                if not self.reset:
                    input_file.seek(0)
                    self.reset = True
                b = input_file.read(1)
                return self.translate(b)

        mime_type = mimetypes.guess_type(file_path)[0]
        if mime_type is None:
            mime_type = 'application/octet-stream'

        def _decoded_matches(m=None):
            if m is None:
                return
            if 'decoded' in m:
                decoded = ''
                for b in base64.b64decode(m['decoded']).replace(b'\r\n', b'<br />') \
                        .replace(b'\n', b'<br />').replace(b'\r', b'\xE2\x8F\x8E'):
                    try:
                        decoded += bytes([b]).decode('utf-8')
                    except UnicodeDecodeError:
                        decoded += f"\\x{int(b)}"
                yield m, decoded
            if 'subEls' in m:
                for a in m['subEls']:
                    yield from _decoded_matches(a)

        def decoded_matches():
            for m in matches:
                yield from _decoded_matches(m)

        return TEMPLATE.render(
            filename=os.path.split(file_path)[-1],
            encoded=sbud['b64contents'],
            matches=matches,
            input_file=input_file,
            input_bytes=input_bytes,
            math=math,
            read_unicode=ReadUnicode(),
            mime_type=mime_type,
            decoded_matches=decoded_matches
        )


if __name__ == '__main__':
    import json
    import sys

    with open(sys.argv[2], 'r') as f:
        print(generate(sys.argv[1], json.load(f)))
