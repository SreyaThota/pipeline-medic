import pytest

from evaluation.run_eval import chance_at_1_for, hit_at_k, reciprocal_rank


def test_hit_at_k():
    ranked = ["lint", "test", "dep"]
    assert not hit_at_k(ranked, "test", 1)
    assert hit_at_k(ranked, "test", 2)


def test_reciprocal_rank():
    assert reciprocal_rank(["lint", "test"], "test") == 0.5
    assert reciprocal_rank(["lint"], "test") == 0.0


def test_chance_at_1_for():
    corpus = ["a", "a", "b", "b", "c"]
    # each "a"/"b" query has 1 same-label log among the 4 others
    assert chance_at_1_for(["a", "a", "b", "b"], corpus) == pytest.approx(1 / 4)
