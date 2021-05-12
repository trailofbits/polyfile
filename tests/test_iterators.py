import random
from typing import Iterator
from unittest import TestCase

from polyfile.iterators import LazyIterableSequence, LazyIterableSet, unique


class TestIterators(TestCase):
    @staticmethod
    def random_sequence(min_len: int = 0, max_len: int = 1000) -> Iterator[str]:
        seq_length = random.randint(min_len, max_len)
        for _ in range(seq_length):
            yield chr(random.randint(ord('a'), ord('z')))

    def test_lazy_sequence(self):
        for _ in range(100):
            ground_truth = list(TestIterators.random_sequence())
            seq = LazyIterableSequence(ground_truth)
            seq_iter = iter(seq)
            if len(ground_truth) > 0:
                self.assertEqual(next(seq_iter), ground_truth[0])
            for i, s in enumerate(seq):
                self.assertEqual(ground_truth[i], s)
            self.assertEqual("".join(ground_truth), "".join(seq))
            if len(ground_truth) > 1:
                self.assertEqual(next(seq_iter), ground_truth[1])

    def test_lazy_set(self):
        for _ in range(100):
            ground_truth = list(TestIterators.random_sequence())
            seq = LazyIterableSet(ground_truth)
            self.assertEqual("".join(unique(ground_truth)), "".join(seq))
