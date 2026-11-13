import base64
import mimetypes
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

jinja2 = None


TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')
TEMPLATE = None


def assign_ids(sbud):
    i = 0
    matches = deepcopy(sbud['struc'])
    stack = list(matches)
    while stack:
        m = stack.pop()
        assert 'uid' not in m
        m['uid'] = i
        i += 1
        stack += list(m['subEls'])
    return matches


def _leaf_extents(matches, length, source='file'):
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
        children = match.get('subEls', [])
        stack.extend(children)
        if match.get('source', 'file') != source:
            continue
        if any(child.get('source', 'file') == source for child in children):
            continue
        start = min(max(match['offset'], 0), length)
        end = min(max(start + match['size'], start), length)
        if end > start:
            yield start, end


def undescribed_regions(matches, length, source='file'):
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
    for start, end in sorted(_leaf_extents(matches, length, source)):
        if start > position:
            regions.append((position, start - position))
        position = max(position, end)
    if position < length:
        regions.append((position, length - position))
    return regions


def source_buffers(sbud):
    """Collects the encoded bytes and coverage of physical and decoded sources.

    Args:
        sbud: The analyzed file and its source-aware structure.

    Returns:
        A mapping from source identifiers to base64 contents and undescribed extents.
    """
    sources = {'file': sbud['b64contents']}
    stack = list(sbud['struc'])
    while stack:
        match = stack.pop()
        source = match.get('source', 'file')
        if source != 'file' and 'decoded' in match:
            sources[source] = match['decoded']
        stack.extend(reversed(match.get('subEls', [])))
    return {
        source: {
            'encoded': encoded,
            'regions': undescribed_regions(sbud['struc'], len(base64.b64decode(encoded)), source),
        }
        for source, encoded in sources.items()
    }


def encoded_contents(file_path, sbud):
    """Returns the base64 encoding of the input that the hex viewer is built from.

    Args:
        file_path: the path of the analyzed file, used to report which input is missing.
        sbud: the SBuD object describing that file.

    Returns:
        The value of the object's ``b64contents`` key.

    Raises:
        ValueError: if the object has no ``b64contents`` key, which is what
            ``Analyzer.sbud(include_contents=False)`` produces.
    """
    if 'b64contents' not in sbud:
        raise ValueError(f"cannot render a hex viewer for {file_path!r}: the SBuD object has no 'b64contents' key. "
                         "Build it with Analyzer.sbud(include_contents=True), which is the default.")
    return sbud['b64contents']


def _viewer_nodes(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collect source-aware metadata without duplicating embedded byte buffers."""
    nodes = []
    stack = [(match, None) for match in reversed(matches)]
    while stack:
        match, parent = stack.pop()
        nodes.append({
            'uid': match['uid'],
            'parent': parent,
            'source': match.get('source', 'file'),
            'offset': match['offset'],
            'size': match['size'],
            'name': match['name'],
            'type': match['type'],
            'extension': match.get('extension', ''),
            'analysis_status': match.get('analysis_status', ''),
            'analysis_message': match.get('analysis_message', ''),
            'decoded': 'decoded' in match,
            'image': match.get('img_data', ''),
        })
        stack.extend((child, match['uid']) for child in reversed(match.get('subEls', [])))
    return nodes


def _template_asset(name: str) -> str:
    return Path(TEMPLATE_DIR, name).read_text(encoding='utf-8')


def generate(file_path: str, sbud: dict[str, Any]) -> str:
    """Render a standalone HTML viewer from an analysis with embedded contents.

    Args:
        file_path: Original input path, used for its display name and MIME type.
        sbud: Source-aware analysis containing the original and decoded contents.

    Returns:
        A complete HTML document with inline styles, scripts, and one JSON payload.
    """
    encoded_contents(file_path, sbud)
    global TEMPLATE, jinja2
    if jinja2 is None:
        import jinja2 as j2
        jinja2 = j2
    if TEMPLATE is None:
        environment = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR))
        TEMPLATE = environment.get_template('template.html')
    matches = assign_ids(sbud)
    sources = source_buffers(sbud)
    input_bytes = sbud['length']
    undescribed_bytes = sum(size for _, size in sources['file']['regions'])
    filename = os.path.basename(file_path)
    return TEMPLATE.render(
        asset=_template_asset,
        filename=filename,
        matches=matches,
        source_buffers=sources,
        input_bytes=input_bytes,
        undescribed_bytes=undescribed_bytes,
        undescribed_percent=undescribed_bytes * 100.0 / max(input_bytes, 1),
        viewer_data={
            'filename': filename,
            'mime': mimetypes.guess_type(file_path)[0] or 'application/octet-stream',
            'sources': sources,
            'nodes': _viewer_nodes(matches),
        },
    )


if __name__ == '__main__':
    import json
    import sys

    with open(sys.argv[2]) as f:
        print(generate(sys.argv[1], json.load(f)))
