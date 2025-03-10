import base64
from io import BytesIO

from .fileutils import FileStream, Tempfile
from .polyfile import Match, register_parser, Submatch

from PIL import Image


@register_parser("image/jp2")
def parse_jpeg2000(file_stream: FileStream, parent: Match):
    with Tempfile(file_stream.read(parent.length)) as input_bytes:
        img = Image.open(input_bytes)
        with BytesIO() as img_data:
            img.save(img_data, "PNG")
            b64data = f"data:image/png;base64,{base64.b64encode(img_data).decode('utf-8')}"
    yield Submatch(
        name='ImageData',
        img_data=b64data,
        match_obj="",
        relative_offset=0,
        length=parent.length,
        parent=parent
    )
