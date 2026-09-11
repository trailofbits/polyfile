"""
Unit tests for PDF parsing functionality, particularly edge cases with empty lists
and malformed dictionary values that were causing crashes (issue #12), the byte-provenance
guards that keep a malformed PDF from truncating the match tree (issue #3464), and the
cross-reference row cells that were never parsed (issue #3542).
"""
import base64
import logging
import unittest
from tempfile import NamedTemporaryFile
from typing import List, Tuple
from unittest.mock import MagicMock, patch
from polyfile.pdf import PDFList, parse_object, PDFDict
from polyfile.polyfile import Match, Matcher


WELL_FORMED_PDF: bytes = base64.b64decode(
    "JVBERi0xLjcKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5k"
    "b2JqCjIgMCBvYmoKPDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFtdIC9Db3VudCAwID4+CmVuZG9i"
    "agp4cmVmCjAgMwowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMDkgMDAwMDAgbiAKMDAw"
    "MDAwMDA1OCAwMDAwMCBuIAp0cmFpbGVyCjw8IC9TaXplIDMgL1Jvb3QgMSAwIFIgPj4Kc3Rh"
    "cnR4cmVmCjExMAolJUVPRgo="
)
"""A two-object PDF with a correct cross-reference table, used as the control."""

EMPTY_TRAILER_PDF: bytes = base64.b64decode(
    "JVBERi0xLjcKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5k"
    "b2JqCjIgMCBvYmoKPDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFtdIC9Db3VudCAwID4+CmVuZG9i"
    "agp4cmVmCjAgMwowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMDkgMDAwMDAgbiAKMDAw"
    "MDAwMDA1OCAwMDAwMCBuIAp0cmFpbGVyCjw8Pj4Kc3RhcnR4cmVmCjExMAolJUVPRgo="
)
"""`WELL_FORMED_PDF` with an empty trailer, so pdfminer finds no `/Root`."""

RECONSTRUCTED_XREF_PDF: bytes = base64.b64decode(
    "JVBERi0xLjcKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5k"
    "b2JqCjIgMCBvYmoKPDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFtdIC9Db3VudCAwID4+CmVuZG9i"
    "agp4cmVmCjAgMwowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMDkgMDAwMDAgbiAKMDAw"
    "MDAwMDA1OCAwMDAwMCBuIAp0cmFpbGVyCjw8IC9TaXplIDMgL1Jvb3QgMSAwIFIgPj4Kc3Rh"
    "cnR4cmVmCjAKJSVFT0YK"
)
"""`WELL_FORMED_PDF` with a `startxref` of 0, so pdfminer rebuilds the table with
`PDFXRefFallback`."""

INTEGER_KEY_PDF: bytes = base64.b64decode(
    "JVBERi0xLjcKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgL0JhZCAz"
    "IDAgUiA+PgplbmRvYmoKMiAwIG9iago8PCAvVHlwZSAvUGFnZXMgL0tpZHMgW10gL0NvdW50"
    "IDAgPj4KZW5kb2JqCjMgMCBvYmoKPDwgNDIgKHZhbHVlKSA+PgplbmRvYmoKeHJlZgowIDQK"
    "MDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNjkgMDAw"
    "MDAgbiAKMDAwMDAwMDEyMSAwMDAwMCBuIAp0cmFpbGVyCjw8IC9TaXplIDQgL1Jvb3QgMSAw"
    "IFIgPj4Kc3RhcnR4cmVmCjE1MwolJUVPRgo="
)
"""A PDF whose object 3 is `<< 42 (value) >>`; pdfminer names that key with `literal_name`,
which returns a plain `str` for a key that is not a literal."""


class TestPDFList(unittest.TestCase):
    """Test cases for PDFList.load() method"""

    def test_empty_list(self):
        """Test that empty lists return a zero-length wrapper without crashing"""
        result = PDFList.load([])
        self.assertIsInstance(result, PDFList)
        self.assertEqual(len(result), 0)
        self.assertEqual(result.pdf_offset, 0)
        self.assertEqual(result.pdf_bytes, 0)

    def test_list_with_offsets(self):
        """Test that lists with proper offset information calculate bounds correctly"""
        # Create mock items with pdf_offset and pdf_bytes
        item1 = MagicMock()
        item1.pdf_offset = 100
        item1.pdf_bytes = 10

        item2 = MagicMock()
        item2.pdf_offset = 120
        item2.pdf_bytes = 15

        item3 = MagicMock()
        item3.pdf_offset = 110
        item3.pdf_bytes = 8

        result = PDFList.load([item1, item2, item3])

        # Should span from earliest offset (100) to end of latest item (120 + 15 = 135)
        self.assertEqual(result.pdf_offset, 100)
        self.assertEqual(result.pdf_bytes, 35)  # 135 - 100
        self.assertEqual(len(result), 3)

    def test_list_mixed_offsets(self):
        """Test lists with mix of items with/without offset information"""
        # Items with offsets
        item1 = MagicMock()
        item1.pdf_offset = 100
        item1.pdf_bytes = 10

        item2 = MagicMock()
        item2.pdf_offset = 150
        item2.pdf_bytes = 20

        # Item without offsets
        item3 = MagicMock()
        del item3.pdf_offset  # Ensure it doesn't have the attribute
        del item3.pdf_bytes

        result = PDFList.load([item1, item3, item2])

        # Should only consider items with offsets
        self.assertEqual(result.pdf_offset, 100)
        self.assertEqual(result.pdf_bytes, 70)  # 170 - 100
        self.assertEqual(len(result), 3)  # All items should still be in the list

    @patch('polyfile.pdf.log')
    def test_list_no_offsets(self, mock_log):
        """Test that lists where no items have offsets log a warning and return safe default"""
        # Create items without offset information
        item1 = MagicMock()
        del item1.pdf_offset
        del item1.pdf_bytes

        item2 = MagicMock()
        del item2.pdf_offset
        del item2.pdf_bytes

        result = PDFList.load([item1, item2])

        # Should return safe defaults
        self.assertEqual(result.pdf_offset, 0)
        self.assertEqual(result.pdf_bytes, 0)
        self.assertEqual(len(result), 2)

        # Should have logged a warning
        mock_log.warning.assert_called_once()
        warning_call = mock_log.warning.call_args[0][0]
        self.assertIn("none have offset information", warning_call)


class TestPDFDictionaryParsing(unittest.TestCase):
    """Test cases for parse_object() handling of dictionary values"""

    def setUp(self):
        """Set up common test fixtures"""
        self.mock_matcher = MagicMock()
        # Create a real Match object for the parent
        self.mock_parent = Match(
            name="TestParent",
            match_obj=b"test",
            relative_offset=0,
            length=100,
            matcher=self.mock_matcher
        )

    @patch('polyfile.pdf.log')
    def test_dict_with_empty_list(self, mock_log):
        """Test that dictionaries containing empty lists don't crash"""
        # Create a PDFDict with an empty list value
        key = MagicMock()
        key.pdf_offset = 10
        key.pdf_bytes = 5

        test_dict = PDFDict({key: []}, pdf_offset=10, pdf_bytes=20)

        # This should not raise an exception
        results = list(parse_object(test_dict, self.mock_matcher, self.mock_parent))

        # Should have logged a debug message about skipping empty list
        mock_log.debug.assert_called()
        debug_call = str(mock_log.debug.call_args)
        self.assertIn("empty list", debug_call.lower())

    @patch('polyfile.pdf.log')
    def test_dict_with_unexpected_value(self, mock_log):
        """Test that unexpected dictionary values are skipped with a warning"""
        # Create a PDFDict with an unexpected value type (not list, no offsets)
        key = MagicMock()
        key.pdf_offset = 10
        key.pdf_bytes = 5

        unexpected_value = "unexpected_string_value"

        test_dict = PDFDict({key: unexpected_value}, pdf_offset=10, pdf_bytes=20)

        # This should not raise an exception
        results = list(parse_object(test_dict, self.mock_matcher, self.mock_parent))

        # Should have logged a warning
        mock_log.warning.assert_called()
        warning_call = str(mock_log.warning.call_args)
        self.assertIn("unexpected", warning_call.lower())

    def test_dict_with_valid_values(self):
        """Test that dictionaries with valid values parse correctly"""
        # Create a PDFDict with proper values
        key = MagicMock()
        key.pdf_offset = 10
        key.pdf_bytes = 5

        value = MagicMock()
        value.pdf_offset = 20
        value.pdf_bytes = 10

        test_dict = PDFDict({key: value}, pdf_offset=10, pdf_bytes=50)

        # This should work without issues
        results = list(parse_object(test_dict, self.mock_matcher, self.mock_parent))

        # Should have yielded at least the dict object and key-value pair
        self.assertGreater(len(results), 0)

    def test_dict_preserves_falsy_values(self):
        """Test that falsy but valid values (0, False) are not skipped"""
        # Create items that have proper offsets but falsy values
        key1 = MagicMock()
        key1.pdf_offset = 10
        key1.pdf_bytes = 5

        # Value that is falsy (0) but has proper offset info
        value1 = MagicMock()
        value1.pdf_offset = 20
        value1.pdf_bytes = 1
        value1.__bool__ = lambda self: False  # Make it falsy

        key2 = MagicMock()
        key2.pdf_offset = 30
        key2.pdf_bytes = 5

        # Another falsy value with offsets
        value2 = MagicMock()
        value2.pdf_offset = 40
        value2.pdf_bytes = 1
        value2.__bool__ = lambda self: False

        test_dict = PDFDict({key1: value1, key2: value2}, pdf_offset=10, pdf_bytes=50)

        # Should parse both values since they have proper offset info
        results = list(parse_object(test_dict, self.mock_matcher, self.mock_parent))

        # Should have processed both key-value pairs
        # (at minimum: dict_obj, 2x KeyValuePair, 2x Key, 2x Value)
        self.assertGreater(len(results), 5)


class CapturedWarnings(logging.Handler):
    """Collects the warnings PolyFile's loggers emit while a file is matched."""

    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.records: List[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def messages(self, logger_name: str) -> List[str]:
        """Returns the messages one logger emitted.

        Args:
            logger_name: The name the logger was created with, such as "PDF".

        Returns:
            Every warning that logger emitted, in the order it emitted them.
        """
        return [r.getMessage() for r in self.records if r.name == logger_name]


class TestMalformedPDFMatchTree(unittest.TestCase):
    """Regression tests for the byte-provenance guards in issue #3464.

    `Matcher.handle_mimetype` catches every exception a parser raises and logs a warning, so an
    unguarded dereference never reaches the user as a traceback: it abandons the rest of the match
    tree instead. These tests therefore assert on the tree and on the warnings, not on exceptions.
    """

    def match(self, data: bytes) -> Tuple[List[str], CapturedWarnings]:
        """Runs the full matcher over a PDF held in memory.

        Args:
            data: The contents of the PDF to match.

        Returns:
            The name of every match, in the order PolyFile produced them, and the warnings that
            were logged while it did.
        """
        handler = CapturedWarnings()
        root = logging.getLogger()
        previous_level = root.level
        root.addHandler(handler)
        root.setLevel(logging.WARNING)
        try:
            with NamedTemporaryFile(suffix=".pdf") as f:
                f.write(data)
                f.flush()
                return [m.name for m in Matcher(parse=True).match(f.name)], handler
        finally:
            root.removeHandler(handler)
            root.setLevel(previous_level)

    def assertParserFinished(self, warnings: CapturedWarnings):
        """Asserts that no parser abandoned its match tree part way through."""
        aborted = [m for m in warnings.messages("polyfile") if "raised an exception" in m]
        self.assertEqual([], aborted)

    def test_well_formed_pdf_is_mapped_completely(self):
        """Every structure of an undamaged PDF is mapped, with nothing logged."""
        names, warnings = self.match(WELL_FORMED_PDF)
        self.assertParserFinished(warnings)
        self.assertEqual([], warnings.messages("PDF"))
        self.assertEqual(2, names.count("PDFObject"))
        self.assertEqual(1, names.count("Trailer"))
        self.assertEqual(1, names.count("XRefTable"))
        self.assertEqual(2, names.count("XRefRow"))

    def test_empty_trailer_still_maps_the_xref_table(self):
        """An empty trailer no longer costs the cross-reference table.

        `min()` over the trailer's keys raised `ValueError: min() arg is an empty sequence`, which
        abandoned the match tree before any of the `XRefTable` submatches were produced.
        """
        names, warnings = self.match(EMPTY_TRAILER_PDF)
        self.assertParserFinished(warnings)
        self.assertEqual(2, names.count("PDFObject"))
        self.assertEqual(0, names.count("Trailer"))
        self.assertEqual(1, names.count("XRefTable"))
        self.assertEqual(2, names.count("XRefRow"))

    def test_reconstructed_xref_rows_are_skipped(self):
        """A rebuilt cross-reference table is reported, not fatal.

        `PDFXRefFallback` stores plain integer positions, so `c.pdf_offset` raised
        `AttributeError: 'int' object has no attribute 'pdf_offset'` and discarded the rest of
        the match tree.
        """
        names, warnings = self.match(RECONSTRUCTED_XREF_PDF)
        self.assertParserFinished(warnings)
        self.assertEqual(2, names.count("PDFObject"))
        self.assertEqual(1, names.count("Trailer"))
        self.assertEqual(0, names.count("XRefTable"))
        skipped = [m for m in warnings.messages("PDF") if "PDFXRefFallback" in m]
        self.assertEqual(1, len(skipped))
        self.assertIn("Skipping 2 rows", skipped[0])

    def test_dictionary_key_without_provenance_is_skipped(self):
        """One unmappable dictionary key costs that key, not the rest of the file.

        `key.pdf_offset` raised `AttributeError: 'str' object has no attribute 'pdf_offset'` for a
        key that pdfminer named with `literal_name`, which abandoned the match tree before the
        trailer and the cross-reference table were mapped.
        """
        names, warnings = self.match(INTEGER_KEY_PDF)
        self.assertParserFinished(warnings)
        self.assertEqual(3, names.count("PDFObject"))
        self.assertEqual(1, names.count("Trailer"))
        self.assertEqual(1, names.count("XRefTable"))
        self.assertEqual(3, names.count("XRefRow"))
        self.assertEqual(
            ["Skipping PDF dictionary key '42' because it has no byte provenance"],
            warnings.messages("PDF")
        )


class TestXRefRowCells(unittest.TestCase):
    """Regression tests for the cross-reference row cells in issue #3542."""

    def match(self, data: bytes) -> List[Match]:
        """Runs the full matcher over a PDF held in memory.

        Args:
            data: The contents of the PDF to match.

        Returns:
            Every match PolyFile produced, in the order it produced them. The list has to be
            materialized before the tree is walked, because a match's children are appended as
            the parser yields them.
        """
        with NamedTemporaryFile(suffix=".pdf") as f:
            f.write(data)
            f.flush()
            return list(Matcher(parse=True).match(f.name))

    def test_row_cells_map_the_integers_they_hold(self):
        """Every cell of a cross-reference row parses its contents.

        `parse_object` was handed the `Submatch` that had just been created for the cell instead
        of the cell itself. A `Submatch` carries no `pdf_offset`, so the call fell through every
        branch and yielded nothing: `Position` and `Generation` were leaves, and the offsets the
        table records never reached the output.
        """
        cells = [m for m in self.match(WELL_FORMED_PDF) if m.name in ("Position", "Generation")]
        self.assertEqual(4, len(cells))
        for cell in cells:
            self.assertEqual(["PSInt"], [c.name for c in cell.children])
            self.assertEqual(cell.offset, cell.children[0].offset)
            self.assertEqual(cell.length, cell.children[0].length)
        # object 1 is at byte 9 and object 2 at byte 58, both of generation 0
        self.assertEqual([9, 0, 58, 0], [cell.children[0].match for cell in cells])

    def test_reconstructed_xref_yields_no_cells(self):
        """A rebuilt table maps to nothing rather than dereferencing its plain integers.

        `PDFXRefFallback` stores positions as `int`, which `parse_object` has to skip. The rows
        are dropped before `parse_xref_row` sees them, so no cell reaches the tree at all.
        """
        matches = self.match(RECONSTRUCTED_XREF_PDF)
        self.assertEqual([], [m.name for m in matches if m.name in ("Position", "Generation")])


if __name__ == '__main__':
    unittest.main()
