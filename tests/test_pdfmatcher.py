"""PDF identification is independent of structural-parser imports."""

from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
from zipfile import ZipFile

import pytest


IDENTIFY_SCRIPT = """
import json
import sys

if sys.argv[2] == "blocked":
    sys.modules["pdfminer"] = None

from polyfile.magic import MagicMatcher, MatchContext

data = sys.stdin.buffer.read()
matcher = MagicMatcher.DEFAULT_INSTANCE
if sys.argv[1] == "selected":
    matcher = matcher.only_match(mimetypes=["application/pdf"])

def identify():
    context = MatchContext(data, only_match_mime=sys.argv[1] == "mime")
    return sorted(mime for match in matcher.match(context) for mime in match.mimetypes)

before = identify()
pdf_loaded = "polyfile.pdf" in sys.modules
pdfminer_loaded = any(name.startswith("pdfminer") and module is not None
                      for name, module in sys.modules.items())
if sys.argv[1] == "warm":
    from polyfile import pdf
print(json.dumps({"before": before, "after": identify(), "pdf_loaded": pdf_loaded,
                  "pdfminer_loaded": pdfminer_loaded}))
"""


def identify_in_fresh_process(
    data: bytes, mode: str = "default", *, block_pdfminer: bool = False,
) -> dict[str, Any]:
    """Identify bytes without test collection importing the PDF parser first.

    Args:
        data: Input bytes to identify.
        mode: Matching mode or an instruction to import the parser between scans.
        block_pdfminer: Whether to make PDFminer unavailable to the subprocess.

    Returns:
        Classifications before and after parser loading, plus initial import state.
    """
    result = subprocess.run(
        [sys.executable, "-c", IDENTIFY_SCRIPT, mode, "blocked" if block_pdfminer else "normal"],
        input=data, capture_output=True, check=True, timeout=10,
    )
    return json.loads(result.stdout)


def polyglot() -> bytes:
    """Build an iNES header, PDF signature, and ZIP archive in one byte buffer.

    Returns:
        Bytes with independently recognizable NES, PDF, and ZIP signatures.
    """
    stream = BytesIO()
    stream.write(b"NES\x1a" + b"\x00" * 12 + b"%PDF-1.7\n%%EOF\n")
    with ZipFile(stream, "w") as archive:
        archive.writestr("hello.txt", "Hello\n")
    return stream.getvalue()


@pytest.mark.parametrize("offset", [0, 16, 2048])
@pytest.mark.parametrize("block_pdfminer", [False, True])
def test_pdf_identification_stays_lazy(offset: int, block_pdfminer: bool) -> None:
    result = identify_in_fresh_process(
        b"\x00" * offset + b"%PDF-1.7\n%%EOF\n", block_pdfminer=block_pdfminer,
    )
    assert "application/pdf" in result["before"]
    assert not result["pdf_loaded"]
    assert not result["pdfminer_loaded"]


@pytest.mark.parametrize("mode", ["default", "mime"])
def test_pdf_nes_zip_polyglot(mode: str) -> None:
    result = identify_in_fresh_process(polyglot(), mode)
    assert {"application/pdf", "application/x-nes-rom", "application/zip"} <= set(result["before"])


def test_pdf_filetype_filter_includes_relaxed_matcher() -> None:
    result = identify_in_fresh_process(polyglot(), "selected")
    assert result["before"] == ["application/pdf"]


def test_loading_parser_does_not_change_identification() -> None:
    result = identify_in_fresh_process(polyglot(), "warm")
    assert "application/pdf" in result["before"]
    assert result["before"] == result["after"]


@pytest.mark.parametrize("data", [b"", b"plain data", b"%PDF", b"\x00" * 16 + b"%PDF"])
def test_missing_pdf_signature_is_not_a_pdf(data: bytes) -> None:
    result = identify_in_fresh_process(data)
    assert "application/pdf" not in result["before"]


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ([], ("NES ROM image", "Zip archive", "Malformed PDF")),
        (["--only-match-mime"], ("application/pdf", "application/x-nes-rom", "application/zip")),
        (["--only-match-mime", "--filetype", "application/pdf"], ("application/pdf",)),
    ],
)
def test_cli_identifies_pdf_in_polyglot(
    tmp_path: Path, options: list[str], expected: tuple[str, ...],
) -> None:
    path = tmp_path / "polyglot.bin"
    path.write_bytes(polyglot())
    result = subprocess.run(
        [sys.executable, "-c", "from polyfile.__main__ import main; main()", str(path), *options],
        capture_output=True, text=True, check=True, timeout=10,
    )
    for description in expected:
        assert description in result.stdout
