"""Top-level matching must retain the result iterator's order and laziness."""
from unittest import TestCase

from polyfile.magic import AbsoluteOffset, MagicMatcher, MagicTest, MatchContext, MatchedTest, TestType as MagicTestType


class ScriptedTest(MagicTest):
    AUTO_REGISTER_TEST = False

    def __init__(self, results):
        super().__init__(AbsoluteOffset(0), mime="application/example")
        self.results = results

    def subtest_type(self):
        return MagicTestType.BINARY

    def test(self, data, absolute_offset, parent_match):
        raise AssertionError("match supplies its own results")

    def match(self, to_match):
        return self.results(self)


class TestResultIteration(TestCase):
    @staticmethod
    def run_tests(*tests):
        return MagicMatcher()._run_tests(tests, MatchContext(b"example"), None, "test")

    def test_continuations_are_not_consumed_before_yield(self):
        events = []

        def results(test):
            events.append("first")
            yield MatchedTest(test, offset=0, length=1, value=b"e")
            events.append("continuation")
            yield MatchedTest(test, offset=2, length=1, value=b"a")

        test = ScriptedTest(results)
        matches = self.run_tests(test)
        returned_test, match = next(matches)
        self.assertIs(returned_test, test)
        self.assertEqual(events, ["first"])
        self.assertEqual([r.offset for r in match], [0, 2])
        self.assertEqual(events, ["first", "continuation"])
        self.assertEqual(list(matches), [])

    def test_empty_and_index_error_generators_do_not_match(self):
        def empty(test):
            yield from ()

        def index_error(test):
            raise IndexError("the result iterator ended")
            yield  # pragma: no cover

        self.assertEqual(list(self.run_tests(ScriptedTest(empty), ScriptedTest(index_error))), [])

    def test_other_generator_exceptions_propagate(self):
        def broken(test):
            raise ValueError("bad test input")
            yield  # pragma: no cover

        with self.assertRaisesRegex(ValueError, "^bad test input$"):
            list(self.run_tests(ScriptedTest(broken)))

    def test_non_generator_iterables_keep_the_normal_path(self):
        def results(test):
            return [MatchedTest(test, offset=1, length=1, value=b"x")]

        test, match = next(self.run_tests(ScriptedTest(results)))
        self.assertEqual(list(match.mimetypes), ["application/example"])
        self.assertEqual([r.offset for r in match], [1])

    def test_index_error_in_custom_iterator_can_resume(self):
        class ResumingIterator:
            def __init__(self, test):
                self.test = test
                self.index = 0

            def __iter__(self):
                return self

            def __next__(self):
                self.index += 1
                if self.index == 1:
                    raise IndexError("not exhausted")
                if self.index == 2:
                    return MatchedTest(self.test, offset=3, length=1, value=b"x")
                raise StopIteration

        test = ScriptedTest(ResumingIterator)
        test.extensions.add("example")
        _, match = next(self.run_tests(test))
        self.assertEqual([r.offset for r in match], [3])

    def test_exception_after_first_result_remains_lazy(self):
        def results(test):
            yield MatchedTest(test, offset=0, length=1, value=b"e")
            raise ValueError("continuation failed")

        _, match = next(self.run_tests(ScriptedTest(results)))
        with self.assertRaisesRegex(ValueError, "^continuation failed$"):
            list(match)
