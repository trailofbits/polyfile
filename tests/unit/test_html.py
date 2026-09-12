import base64
import json
import re
from unittest import TestCase

from polyfile.fileutils import Tempfile
from polyfile.html import generate, undescribed_regions


def match(offset, size, sub_els=()):
    return {
        'offset': offset,
        'relative_offset': offset,
        'size': size,
        'type': 'application/octet-stream',
        'name': f'match@{offset}',
        'value': '',
        'subEls': list(sub_els)
    }


def sbud(contents, struc, include_contents=True):
    obj = {
        'MD5': '',
        'SHA1': '',
        'SHA256': '',
        'fileName': 'test.bin',
        'length': len(contents),
        'versions': [],
        'struc': struc
    }
    if include_contents:
        obj['b64contents'] = base64.b64encode(contents).decode('utf-8')
    return obj


class UndescribedRegionTests(TestCase):
    """Test that undescribed_regions finds every byte that no childless match covers.

    These tests prevent a regression to the behavior reported in
    https://github.com/trailofbits/polyfile/issues/8, where the hex viewer had no way to tell
    a reader which bytes the analysis failed to describe.
    """

    def test_no_matches_leaves_the_whole_file_undescribed(self):
        self.assertEqual([(0, 16)], undescribed_regions([], 16))

    def test_full_coverage_reports_nothing(self):
        self.assertEqual([], undescribed_regions([match(0, 16)], 16))

    def test_a_gap_between_two_matches(self):
        regions = undescribed_regions([match(0, 4), match(10, 6)], 16)
        self.assertEqual([(4, 6)], regions)

    def test_a_gap_before_the_first_match(self):
        self.assertEqual([(0, 3)], undescribed_regions([match(3, 13)], 16))

    def test_a_gap_after_the_last_match(self):
        self.assertEqual([(12, 4)], undescribed_regions([match(0, 12)], 16))

    def test_only_childless_matches_describe_bytes(self):
        parent = match(0, 16, [match(0, 4), match(12, 4)])
        self.assertEqual([(4, 8)], undescribed_regions([parent], 16))

    def test_overlapping_matches_do_not_create_gaps(self):
        regions = undescribed_regions([match(0, 10), match(4, 6), match(2, 3)], 16)
        self.assertEqual([(10, 6)], regions)

    def test_a_match_nested_out_of_order_is_still_counted(self):
        parent = match(0, 16, [match(8, 8), match(0, 2)])
        self.assertEqual([(2, 6)], undescribed_regions([parent], 16))

    def test_zero_length_matches_describe_nothing(self):
        self.assertEqual([(0, 16)], undescribed_regions([match(4, 0)], 16))

    def test_a_match_running_past_the_end_is_clamped(self):
        self.assertEqual([], undescribed_regions([match(0, 1024)], 16))


class GeneratedHtmlTests(TestCase):
    """Test that the generated hex viewer carries the data it needs to mark undescribed bytes."""

    def render(self, contents, struc, include_contents=True):
        with Tempfile(contents) as file_path:
            return generate(file_path, sbud(contents, struc, include_contents))

    def emitted_regions(self, html):
        emitted = re.search(r'const UNDESCRIBED_REGIONS = (\[.*?]);', html)
        self.assertIsNotNone(emitted, 'the viewer script declares no undescribed regions')
        return [tuple(region) for region in json.loads(emitted.group(1))]

    def legend(self, html):
        found = re.search(r'<div class="coverage">(.*?)</div>', html, re.DOTALL)
        self.assertIsNotNone(found, 'the viewer has no coverage legend')
        return ' '.join(found.group(1).split())

    def test_a_file_with_gaps_emits_them(self):
        html = self.render(bytes(16), [match(0, 16, [match(0, 4), match(12, 4)])])
        self.assertEqual([(4, 8)], self.emitted_regions(html))
        self.assertIn('8 of 16 bytes (50.0%) are undescribed.', self.legend(html))
        self.assertIn('class="swatch undescribed"', html)

    def test_a_fully_described_file_emits_no_gaps(self):
        html = self.render(bytes(16), [match(0, 16)])
        self.assertEqual([], self.emitted_regions(html))
        self.assertIn('Every one of the 16 bytes is described by a match.', self.legend(html))
        self.assertNotIn('class="swatch undescribed"', html)

    def test_an_empty_file_renders(self):
        """The address gutter used to take the logarithm of the file's length.

        This is a regression test for trailofbits/polyfile#3566. `math.log(0)` raises
        `ValueError: expected a positive input`, so `--format html` aborted with a traceback on a
        zero-length file rather than writing a viewer.
        """
        html = self.render(b'', [{**match(0, 0), 'type': 'inode/x-empty', 'name': 'inode/x-empty'}])
        self.assertEqual([], self.emitted_regions(html))
        self.assertIn('inode/x-empty', html)

    def test_the_style_the_viewer_applies_is_defined(self):
        html = self.render(bytes(16), [match(0, 16)])
        self.assertIn(".toggleClass('undescribed'", html)
        self.assertIn('.undescribed {', html)
        self.assertIn('repeating-linear-gradient', html)

    def test_the_contents_reach_the_viewer(self):
        contents = bytes(range(16))
        html = self.render(contents, [match(0, 16)])
        self.assertIn(base64.b64encode(contents).decode('utf-8'), html)

    def test_an_sbud_without_contents_is_refused(self):
        """`--no-contents` omits `b64contents`, which the hex viewer is built from.

        This is a regression test for trailofbits/polyfile#3399. Without the check, rendering an
        SBuD object that carries no contents raised a bare `KeyError: 'b64contents'` from deep
        inside `generate`.
        """
        with self.assertRaises(ValueError) as refused:
            self.render(bytes(16), [match(0, 16)], include_contents=False)
        self.assertIn("no 'b64contents' key", str(refused.exception))
