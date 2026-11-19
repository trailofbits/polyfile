"""Compare continuation addresses with the bundled file classifier."""

from pathlib import Path
import subprocess

import pytest

from polyfile.magic import MagicMatcher


@pytest.mark.parametrize(
    "rule,data,marker",
    [
        ("(3.o)", b"123010\0xZ", True),
        ("(3.o)", b"abc010\0xZ", True),
        ("(4.b+(1))", b"HEAD\x08\x03xxxxYZ", True),
        ("(4.b+(1))", b"HEAD\x08\x03xxxZxx", False),
        ("(6.S+(-2))", b"HEAD\x00\x02\x00\x08xxZ", True),
        ("(4.b-(1))", b"HEAD\x0c\x03xxxZxx", True),
        ("(4.b/(1))", b"HEAD\x08\x00xxZxx", True),
        ("(2.o+(1))", b"AA14\0" + b"X" * 19 + b"Z", True),
        ("(4.b+(99))", b"HEAD\x08xxxZ", False),
        ("&-2", b"AxyzZ", False),
        ("&-1", b"Az", True),
        ("&1", b"AxZ", True),
    ],
)
def test_continuation_address(tmp_path: Path, rule: str, data: bytes, marker: bool) -> None:
    # A byte test advances the relative base by one. All operands below are physical addresses.
    value = "65" if rule == "&-1" else "90"
    magic = tmp_path / "offset.magic"
    magic.write_text(f"0\tbyte\tx\tbase\n>{rule}\tbyte\t{value}\tmarker\n")
    descriptions = [str(result) for result in MagicMatcher.parse(magic).match(data)]
    assert any("marker" in description for description in descriptions) == marker
    oracle = Path(__file__).resolve().parents[1] / "file" / "src" / "file"
    if oracle.is_file():
        sample = tmp_path / "sample"
        sample.write_bytes(data)
        description = subprocess.check_output([oracle, "-b", "-m", magic, sample], text=True)
        assert ("marker" in description) == marker


def test_negated_string_before_start_has_no_bytes_to_compare(tmp_path: Path) -> None:
    magic = tmp_path / "relative.magic"
    magic.write_text("0\tbyte\tx\tbase\n>&-2\tstring\t!Z\tmarker\n")
    assert [str(match) for match in MagicMatcher.parse(magic).match(b"AxyzZ")] == ["base marker"]
