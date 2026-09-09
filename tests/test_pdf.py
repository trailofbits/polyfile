"""
Unit tests for PDF parsing functionality, particularly edge cases with empty lists
and malformed dictionary values that were causing crashes (issue #12).
"""
import unittest
from unittest.mock import MagicMock, patch
from polyfile.pdf import PDFList, parse_object, PDFDict
from polyfile.polyfile import Match


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


if __name__ == '__main__':
    unittest.main()
