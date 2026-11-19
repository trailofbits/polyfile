import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest import TestCase

from PIL import Image

from polyfile.magic import MagicMatcher
from polyfile.polyfile import Analyzer

from tests.test_zipmatcher import MEMBERS, build_zip, temporary_file


def node_count(element: dict[str, Any]) -> int:
    """Counts an SBuD element and everything nested under it."""
    return 1 + sum(node_count(child) for child in (element.get("subEls") or ()))


def tree_size(sbud: dict[str, Any]) -> int:
    """Counts every element in an SBuD object's structure."""
    return sum(node_count(element) for element in sbud["struc"])


class AnalyzerSbudTest(TestCase):
    """`Analyzer.sbud` describes the whole match tree however the caller supplies the matches.

    `Analyzer.matches` yields a top-level match as soon as it is found and attaches that match's
    children as the analysis continues, so rendering one before the analysis finishes describes a
    node that has not got its children yet. `sbud` used to bind the generator and drain it inside
    the comprehension that builds `struc`, which is exactly that: it returned a correctly shaped
    object with one element in it, and nothing in the signature or the docstring said so.

    Regression test for trailofbits/polyfile#3584.
    """

    def test_caches_are_absent_before_analysis_starts(self):
        analyzer = Analyzer("not-opened-before-iteration")
        self.assertIsNone(analyzer.matches_so_far)
        self.assertIsNone(analyzer.magic_matches_so_far)

    def test_structured_magic_values_render_substitutions(self):
        with temporary_file(b"0 byte x value:%u\n!:mime application/x-value\n") as rules:
            custom = MagicMatcher.parse(rules)
            cases = ((custom, b"AxyzZ", "value:65"),
                     (None, b"UNIF\x07\x00\x00\x00", "NES ROM image (UNIF v7 format)"))
            for matcher, data, expected in cases:
                with temporary_file(data) as path:
                    analyzer = Analyzer(path, parse=False, magic_matcher=matcher)
                    self.assertIn(expected, [str(match) for match in analyzer.magic_matches()])
                    values = [node["value"] for node in analyzer.sbud()["struc"]]
                    self.assertIn(expected, values)

    def test_jpeg_extension_is_stable_across_hash_seeds(self):
        with temporary_file(b"") as path:
            Image.new("RGB", (1, 1)).save(Path(path), format="JPEG")
            script = (
                "import sys; from polyfile.polyfile import Analyzer; "
                "nodes = Analyzer(sys.argv[1], parse=False).sbud()['struc']; "
                "print(next(n['extension'] for n in nodes if n['type'] == 'image/jpeg'))"
            )
            extensions = {
                subprocess.check_output(
                    [sys.executable, "-c", script, str(path)],
                    env={**os.environ, "PYTHONHASHSEED": seed}, text=True,
                ).strip()
                for seed in ("0", "1", "2", "3")
            }
            self.assertEqual(len(extensions), 1, extensions)

    def test_sbud_agrees_however_the_matches_are_supplied(self):
        with temporary_file(build_zip(members=MEMBERS)) as path:
            from_analysis = Analyzer(str(path)).sbud(include_contents=False)

            materialized = Analyzer(str(path))
            from_list = materialized.sbud(
                matches=list(materialized.matches()), include_contents=False
            )

            lazily = Analyzer(str(path))
            from_generator = lazily.sbud(matches=lazily.matches(), include_contents=False)

        self.assertEqual(from_list, from_analysis)
        self.assertEqual(from_list, from_generator)

    def test_the_tree_is_not_trivially_small(self):
        """Whole-object equality passes if every caller gets the same truncated tree.

        The archive below has several members, so a described tree runs to dozens of elements. A
        handful would mean `sbud` agreed with itself about the wrong answer.
        """
        with temporary_file(build_zip(members=MEMBERS)) as path:
            sbud = Analyzer(str(path)).sbud(include_contents=False)
        self.assertGreater(tree_size(sbud), 10)

    def test_sbud_can_be_called_twice(self):
        """`Analyzer.matches` caches into `matches_so_far`, so a second call stays cheap."""
        with temporary_file(build_zip(members=MEMBERS)) as path:
            analyzer = Analyzer(str(path))
            first = analyzer.sbud(include_contents=False)
            matches = analyzer.matches_so_far
            assert matches is not None
            self.assertGreater(len(matches), 0)
            second = analyzer.sbud(include_contents=False)
        self.assertEqual(first, second)
