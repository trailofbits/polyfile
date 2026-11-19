import base64
import hashlib
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from polyfile.fileutils import Tempfile
from polyfile.polyfile import Analyzer

CONTENTS = b"hello, PolyFile\n"


def sbud(include_contents: bool = True):
    """Builds an SBuD object for a small file, without running the analysis."""
    with Tempfile(CONTENTS) as path:
        return Analyzer(path).sbud(matches=[], include_contents=include_contents)


class ContentsTests(TestCase):
    """Tests for the `include_contents` argument of `Analyzer.sbud`.

    These tests cover the request in https://github.com/trailofbits/polyfile/issues/3399, where
    the `b64contents` key holds a base64 encoding of the whole input and so dominates the size of
    the JSON output for all but the smallest files.
    """

    def test_the_contents_are_included_by_default(self):
        self.assertEqual(base64.b64encode(CONTENTS).decode("utf-8"), sbud()["b64contents"])

    def test_omitting_the_contents_omits_the_key(self):
        self.assertNotIn("b64contents", sbud(include_contents=False))

    def test_omitting_the_contents_changes_nothing_else(self):
        with Tempfile(CONTENTS) as path:
            analyzer = Analyzer(path)
            with_contents = analyzer.sbud(matches=[])
            without = analyzer.sbud(matches=[], include_contents=False)
        del with_contents["b64contents"]
        self.assertEqual(with_contents, without)

    def test_omitting_the_contents_skips_the_encoding(self):
        """The issue asks for the encoding to be skipped, not computed and then discarded.

        Patching `base64.b64encode` to raise is the only way to tell the two apart from the
        outside: an implementation that encodes the input and then filters the key out of the
        finished object passes every other test in this class but raises here.
        """
        with patch("polyfile.polyfile.base64.b64encode", side_effect=AssertionError("encoded anyway")):
            self.assertNotIn("b64contents", sbud(include_contents=False))


class InputIdentityTests(TestCase):
    def test_cached_matches_and_report_describe_the_same_revision(self):
        original = b"%PDF-1.7\n"
        with Tempfile(original) as path:
            analyzer = Analyzer(path, parse=False)
            matches = list(analyzer.matches())
            Path(path).write_bytes(b"replacement bytes")
            for supplied in (matches, None):
                report = analyzer.sbud(matches=supplied)
                self.assertEqual(report["length"], len(original))
                self.assertEqual(report["SHA256"], hashlib.sha256(original).hexdigest())
                self.assertEqual(base64.b64decode(report["b64contents"]), original)
                self.assertIn("application/pdf", [node["type"] for node in report["struc"]])

    def test_path_inputs_have_json_serializable_names(self):
        with Tempfile(b"data") as path:
            for name in (str(path), Path(path)):
                report = Analyzer(name).sbud(matches=[], include_contents=False)
                self.assertEqual(json.loads(json.dumps(report))["fileName"], str(path))
