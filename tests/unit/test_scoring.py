"""Tests for scoring primitives."""

from synapt_eval.scoring import kendall_tau, precision_at_k, recall_at_k


class TestKendallTau:
    def test_perfect_agreement(self):
        assert kendall_tau(["a", "b", "c"], ["a", "b", "c"]) == 1.0

    def test_perfect_disagreement(self):
        assert kendall_tau(["a", "b", "c"], ["c", "b", "a"]) == -1.0

    def test_partial_agreement(self):
        result = kendall_tau(["a", "b", "c", "d"], ["a", "c", "b", "d"])
        assert result is not None
        assert -1.0 <= result <= 1.0

    def test_single_item_returns_none(self):
        assert kendall_tau(["a"], ["a"]) is None

    def test_empty_returns_none(self):
        assert kendall_tau([], []) is None

    def test_no_overlap_returns_none(self):
        assert kendall_tau(["a", "b"], ["c", "d"]) is None

    def test_partial_overlap(self):
        result = kendall_tau(["a", "b", "c"], ["b", "c", "d"])
        assert result is not None


class TestPrecisionAtK:
    def test_all_relevant(self):
        assert precision_at_k(["a", "b", "c"], ["a", "b", "c"], k=3) == 1.0

    def test_none_relevant(self):
        assert precision_at_k(["x", "y", "z"], ["a", "b", "c"], k=3) == 0.0

    def test_partial_relevant(self):
        assert precision_at_k(["a", "x", "b"], ["a", "b", "c"], k=3) == 2 / 3

    def test_k_larger_than_retrieved(self):
        assert precision_at_k(["a"], ["a", "b"], k=5) == 1.0

    def test_k_zero(self):
        assert precision_at_k(["a", "b"], ["a"], k=0) == 0.0

    def test_empty_retrieved(self):
        assert precision_at_k([], ["a", "b"], k=5) == 0.0


class TestRecallAtK:
    def test_all_recalled(self):
        assert recall_at_k(["a", "b", "c"], ["a", "b"], k=3) == 1.0

    def test_none_recalled(self):
        assert recall_at_k(["x", "y", "z"], ["a", "b"], k=3) == 0.0

    def test_partial_recall(self):
        assert recall_at_k(["a", "x", "y"], ["a", "b"], k=3) == 0.5

    def test_empty_relevant(self):
        assert recall_at_k(["a", "b"], [], k=5) == 0.0

    def test_k_zero(self):
        assert recall_at_k(["a", "b"], ["a"], k=0) == 0.0
