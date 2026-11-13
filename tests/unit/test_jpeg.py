import base64
from io import BytesIO

from PIL import Image, features
import pytest

from polyfile.fileutils import FileStream
from polyfile.jpeg import parse_jpeg2000
from polyfile.polyfile import Match, Matcher


@pytest.mark.skipif(
    not features.check_codec("jpg_2000"), reason="Pillow JPEG2000 codec is unavailable"
)
def test_jpeg2000_preview_contains_png_bytes() -> None:
    with Image.new("RGB", (3, 2), (12, 34, 56)) as image, BytesIO() as encoded:
        image.save(encoded, format="JPEG2000")
        data = encoded.getvalue()
    parent = Match("JPEG2000", data, length=len(data), matcher=Matcher())

    with FileStream(data) as stream:
        matches = list(parse_jpeg2000(stream, parent))

    assert len(matches) == 1
    preview = matches[0]
    assert preview.parent is parent
    assert preview.offset == 0
    assert preview.length == len(data)
    assert preview.img_data is not None
    prefix, payload = preview.img_data.split(",", 1)
    assert prefix == "data:image/png;base64"
    with Image.open(BytesIO(base64.b64decode(payload, validate=True))) as decoded:
        assert decoded.format == "PNG"
        assert decoded.size == (3, 2)
        assert decoded.getpixel((0, 0)) == (12, 34, 56)
