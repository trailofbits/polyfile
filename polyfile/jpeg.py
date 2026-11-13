import base64
from collections.abc import Iterator
from io import BytesIO

from polyfile.fileutils import FileStream, Tempfile
from polyfile.polyfile import Match, register_parser, Submatch


def _get_pil_image():
    """Lazy import PIL.Image only when needed (for JPEG2000 parsing)."""
    from PIL import Image
    return Image


@register_parser("image/jp2")
def parse_jpeg2000(file_stream: FileStream, parent: Match) -> Iterator[Submatch]:
    """Yields a PNG preview for the image while retaining its source span."""
    Image = _get_pil_image()
    with Tempfile(file_stream.read(parent.length)) as input_bytes:
        with Image.open(input_bytes) as img, BytesIO() as img_data:
            img.save(img_data, "PNG")
            png_data = base64.b64encode(img_data.getvalue()).decode("ascii")
            b64data = f"data:image/png;base64,{png_data}"
    yield Submatch(
        name='ImageData',
        img_data=b64data,
        match_obj="",
        relative_offset=0,
        length=parent.length,
        parent=parent
    )
