from rag.hybrid import graph_first, reciprocal_rank_fusion
from rag.retrieve import Hit


def hit(log_id, score):
    return Hit(log_id, "org/x", "test_failure", score, "")


def test_rrf_rewards_items_ranked_by_both():
    order = reciprocal_rank_fusion([["a", "b", "c"], ["b", "c", "a"]])
    assert order[0] == "b"
    assert set(order) == {"a", "b", "c"}


def test_graph_first_graph_score_decides_similarity_breaks_ties():
    vector = [hit("a", 0.95), hit("b", 0.30), hit("c", 0.60), hit("d", 0.99)]
    graph = [hit("b", 4.71), hit("c", 4.71), hit("a", 4.50)]
    # b and c tie on graph score: c is more similar. a has a lower graph score
    # and must stay below them even though it is far more similar.
    # d has no graph match, so it comes after every graph hit.
    assert graph_first(vector, graph) == ["c", "b", "a", "d"]


def test_graph_first_falls_back_to_vector_order():
    vector = [hit("a", 0.2), hit("b", 0.9)]
    assert graph_first(vector, []) == ["b", "a"]
