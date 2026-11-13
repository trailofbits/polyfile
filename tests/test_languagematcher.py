import tracemalloc
from collections.abc import Iterable
from typing import cast
from unittest import TestCase

from polyfile.languagematcher import BFCommandType, BFMatcher, BFParseError, BFProgram
from polyfile.magic import FailedTest, MatchedTest


class TestBFProgram(TestCase):
    def test_comments_preserve_command_offsets(self):
        data = b"\x00abc+de[f>g,hi-]j.k<\xff"
        program = BFProgram.parse(data)
        self.assertEqual(bytes(program), b"+[>,-].<")
        self.assertEqual([c.offset for c in program.commands], [4, 7, 9, 11, 14, 15, 17, 19])
        self.assertEqual(program.commands[1].command_type, BFCommandType.LOOP_START)
        self.assertEqual(program.num_loops, 1)

    def test_unclosed_loop_reports_eof_including_comments(self):
        for data in (b"[", b"[comment", b"[][\x00\xff", b"prefix[comment"):
            with self.subTest(data=data), self.assertRaises(BFParseError) as error:
                BFProgram.parse(data)
            self.assertEqual(str(error.exception), "unbalanced square brackets")
            self.assertEqual(error.exception.offset, len(data) - 1)

    def test_unexpected_close_reports_first_close(self):
        data = b"abc]long trailing comment]"
        with self.assertRaises(BFParseError) as error:
            BFProgram.parse(data)
        self.assertEqual(error.exception.offset, 3)

    def test_empty_or_comment_only_input(self):
        for data in (b"", b"comment\x00\xff", bytearray(b"comment")):
            self.assertEqual(BFProgram.parse(data).commands, ())

    def test_other_iterable_inputs(self):
        for data in (bytearray(b"a+[]b"), memoryview(b"a+[]b"), [97, 43, 91, 93, 98]):
            program = BFProgram.parse(data)
            self.assertEqual(bytes(program), b"+[]")
            self.assertEqual([c.offset for c in program.commands], [1, 2, 3])

    def test_bytes_subclass_iteration_is_preserved(self):
        class DifferentBytes(bytes):
            def __iter__(self):
                return iter(b"a+[comment]b")

        program = BFProgram.parse(DifferentBytes(b"ignored"))
        self.assertEqual(bytes(program), b"+[]")
        self.assertEqual([c.offset for c in program.commands], [1, 2, 10])

    def test_invalid_iterable_element_still_raises(self):
        with self.assertRaises(TypeError):
            # An invalid element deliberately crosses the parser's typed input boundary.
            BFProgram.parse(cast(Iterable[int], [1.5]))

    def test_dense_commands_with_trailing_comments(self):
        commands = b"[->+<]" * 100
        program = BFProgram.parse(commands + b"a comment with no commands" * 1000)
        self.assertEqual(bytes(program), commands)
        self.assertEqual([c.offset for c in program.commands], list(range(len(commands))))


class TestBFMatcher(TestCase):
    def test_bracket_errors_precede_missing_commands(self):
        for data, offset in ((b"abc]trailing[", 3), (b"abc[trailing", 11), (b"][", 0)):
            with self.subTest(data=data):
                result = BFMatcher().test(data, 0, None)
                self.assertFalse(result)
                assert isinstance(result, FailedTest)
                self.assertEqual(result.message, "unbalanced square brackets")
                self.assertEqual(result.offset, offset)

    def test_missing_command_uses_first_command_including_input(self):
        result = BFMatcher().test(b"comment,[]><+-comment", 0, None)
        self.assertFalse(result)
        assert isinstance(result, FailedTest)
        self.assertEqual(result.message, "missing commands .")
        self.assertEqual(result.offset, 7)
        self.assertIsNone(result.parent)

    def test_large_comment_region_preserves_offsets(self):
        prefix = b"a comment with no operators\n" * 10000
        result = BFMatcher().test(prefix + b"[]><+-", 0, None)
        assert isinstance(result, FailedTest)
        self.assertEqual(result.message, "missing commands .")
        self.assertEqual(result.offset, len(prefix))

    def test_offsets_include_the_slice_base(self):
        for offset in (7, -6):
            result = BFMatcher().test(b"ignored[]><+-", offset, None)
            assert isinstance(result, FailedTest)
            self.assertEqual(result.message, "missing commands .")
            self.assertEqual(result.offset, offset)

    def test_all_required_commands_still_use_thresholds(self):
        matcher = BFMatcher()
        result = matcher.test(b"[]><+-.", 0, None)
        assert isinstance(result, FailedTest)
        self.assertEqual(result.message, "expected at least 2 BrainFu loops but only found 1")
        matcher.min_bf_loops = 0
        result = matcher.test(b"[]><+-.", 0, None)
        assert isinstance(result, FailedTest)
        self.assertEqual(result.message, "expected at least 24 BrainFu commands but only found 7")
        data = b"[]><+-." * 4
        result = matcher.test(data, 0, None)
        self.assertTrue(result)
        assert isinstance(result, MatchedTest)
        self.assertEqual(result.value, data)
        self.assertEqual(result.length, len(data))

    def test_noop_validation_returns_successful_matches(self) -> None:
        matcher = BFMatcher()
        matcher.reject_arithmetical_noops = True
        for data, commands in (
            (b"[->+<]." * 4, b"[->+<]." * 4),
            (b"[]><+comment-." * 4, b"[]><+-." * 4),
        ):
            with self.subTest(data=data):
                result = matcher.test(data, 0, None)
                self.assertIsInstance(result, MatchedTest)
                assert isinstance(result, MatchedTest)
                self.assertEqual(result.value, commands)
                self.assertEqual(result.offset, 0)
                self.assertEqual(result.length, len(data))

    def test_noop_validation_rejects_both_adjacent_cancelling_pairs(self) -> None:
        matcher = BFMatcher()
        matcher.reject_arithmetical_noops = True
        for pair in (b"+-", b"-+"):
            with self.subTest(pair=pair):
                result = matcher.test((b"[]><" + pair + b".") * 4, 0, None)
                self.assertIsInstance(result, FailedTest)
                assert isinstance(result, FailedTest)
                self.assertEqual(result.offset, 4)
                self.assertEqual(
                    result.message, "BrainFu program contains arithmetic that cancels itself out"
                )

    def test_noop_validation_preserves_earlier_validation(self) -> None:
        matcher = BFMatcher()
        matcher.reject_arithmetical_noops = True
        for data, message in (
            (b"]", "unbalanced square brackets"),
            (b"[]", "missing commands"),
            (b"[]><+-.", "expected at least 2 BrainFu loops but only found 1"),
            (b"[]><+-." * 2, "expected at least 24 BrainFu commands but only found 14"),
        ):
            with self.subTest(data=data):
                result = matcher.test(data, 0, None)
                self.assertIsInstance(result, FailedTest)
                assert isinstance(result, FailedTest)
                self.assertIn(message, result.message)

    def test_subclass_slice_iteration_is_preserved(self):

        class DifferentBytes(bytes):
            def __getitem__(self, key):
                return self

            def __iter__(self):
                return iter(b"abc]comment")

        result = BFMatcher().test(DifferentBytes(b"[]><+-"), 0, None)
        assert isinstance(result, FailedTest)
        self.assertEqual(result.message, "unbalanced square brackets")
        self.assertEqual(result.offset, 3)


class TestBFCommandRuns(TestCase):
    def test_comment_header_followed_by_dense_commands(self):
        header = b"a comment with no operators\n" * 20
        commands = b"[->+<]" * 10000
        program = BFProgram.parse(header + commands)
        self.assertEqual(bytes(program), commands)
        self.assertEqual([c.offset for c in program.commands],
                         list(range(len(header), len(header) + len(commands))))

    def test_command_runs_with_comments_and_first_bracket_error(self):
        data = b"prefix++[->+<]middle]ignored++["
        with self.assertRaises(BFParseError) as error:
            BFProgram.parse(data)
        self.assertEqual(error.exception.offset, data.index(b"]ignored"))


class TestBFEarlyRejection(TestCase):
    # A long command run that the parser rejects at its first byte.
    DATA = b"]><+-.[" + b"+" * 4_000_000 + b"x"

    def assert_small_peak(self, call):
        # Measure growth during the call, so that tracing already enabled by the
        # caller (PYTHONTRACEMALLOC, -X tracemalloc) neither counts earlier
        # allocations nor gets switched off here.
        started = not tracemalloc.is_tracing()
        if started:
            tracemalloc.start()
        try:
            tracemalloc.reset_peak()
            before, _ = tracemalloc.get_traced_memory()
            call()
            _, peak = tracemalloc.get_traced_memory()
        finally:
            if started:
                tracemalloc.stop()
        self.assertLess(peak - before, 256 * 1024)

    def test_parse_does_not_copy_the_whole_run(self):
        def parse():
            with self.assertRaises(BFParseError) as raised:
                BFProgram.parse(self.DATA)
            self.assertEqual(raised.exception.offset, 0)
        self.assert_small_peak(parse)

    def test_matcher_does_not_copy_the_whole_run(self):
        def match():
            result = BFMatcher().test(self.DATA, 0, None)
            self.assertFalse(result)
            self.assertEqual(result.offset, 0)
        self.assert_small_peak(match)

    def test_runs_longer_than_one_chunk_keep_offsets(self):
        data = b"xx[" + b"+" * 10_000 + b"]x" + b"><-." * 6
        program = BFProgram.parse(data)
        self.assertEqual([c.offset for c in program.commands],
                         [i for i, b in enumerate(data) if b != ord("x")])
