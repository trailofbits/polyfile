import base64
import json
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


def _leaf_extents(matches, length):
    """Yields the ``(start, end)`` byte extent of every match that has no children.

    A match with children spans all of them, so it says nothing about the bytes its children
    skip. Only childless matches describe bytes.

    Args:
        matches: The top-level SBUD matches to walk.
        length: The length of the analyzed file, in bytes. Extents are clamped to it.

    Yields:
        A ``(start, end)`` pair for each childless match that covers at least one byte.
    """
    stack = list(matches)
    while stack:
        match = stack.pop()
        children = match.get('subEls')
        if children:
            stack.extend(children)
            continue
        start = min(max(match['offset'], 0), length)
        end = min(max(start + match['size'], start), length)
        if end > start:
            yield start, end


def undescribed_regions(matches, length):
    """Finds the byte ranges of a file that no match describes.

    Args:
        matches: The top-level SBUD matches, each with ``offset``, ``size``, and ``subEls`` keys.
        length: The length of the analyzed file, in bytes.

    Returns:
        A list of ``(offset, size)`` pairs, in ascending order of offset, one for each maximal
        run of bytes that no childless match covers.
    """
    regions = []
    position = 0
    for start, end in sorted(_leaf_extents(matches, length)):
        if start > position:
            regions.append((position, start - position))
        position = max(position, end)
    if position < length:
        regions.append((position, length - position))
    return regions


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
    regions = undescribed_regions(matches, input_bytes)
    undescribed_bytes = sum(size for _, size in regions)
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
            decoded_matches=decoded_matches,
            undescribed_regions=json.dumps(regions, separators=(',', ':')),
            undescribed_bytes=undescribed_bytes,
            undescribed_percent=undescribed_bytes * 100.0 / max(input_bytes, 1)
        )


if __name__ == '__main__':
    import sys

    with open(sys.argv[2], 'r') as f:
        print(generate(sys.argv[1], json.load(f)))
