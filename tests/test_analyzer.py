from typing import Any, Dict
from unittest import TestCase

from polyfile.polyfile import Analyzer

from .test_zipmatcher import MEMBERS, build_zip, temporary_file


def node_count(element: Dict[str, Any]) -> int:
    """Counts an SBuD element and everything nested under it."""
    return 1 + sum(node_count(child) for child in (element.get("subEls") or ()))


def tree_size(sbud: Dict[str, Any]) -> int:
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
            self.assertGreater(len(analyzer.matches_so_far), 0)
            second = analyzer.sbud(include_contents=False)
        self.assertEqual(first, second)
