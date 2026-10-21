"""Hybrid retrieval: fuse flat vector search with the knowledge graph (v0.2.5).

The two retrievers score on different scales (cosine similarity vs summed
IDF), so their scores are never added together. Two fusion modes, neither
with a weight to tune:

  graph_first  order by graph score; vector similarity only breaks ties (runs
               with identical entity sets tie often) and ranks whatever the
               graph did not match, so a log with no extractable entities
               still gets vector results
  rrf          reciprocal rank fusion of the two rankings
"""

from collections.abc import Sequence

from rag.entities import extract_entities
from rag.graph import GraphStore
from rag.ingest import clean_log
from rag.retrieve import Hit, Retriever

RRF_K = 60  # standard constant from the original RRF paper (Cormack et al., 2009)
POOL = 200  # how deep each retriever's ranking is read before fusing


def reciprocal_rank_fusion(rankings: Sequence[Sequence[str]], k: int = RRF_K) -> list[str]:
    """Order ids by the sum of 1 / (k + rank) over the rankings they appear in."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda item: (-scores[item], item))


def graph_first(vector_hits: Sequence[Hit], graph_hits: Sequence[Hit]) -> list[str]:
    """Order ids by graph score, then by vector similarity.

    Graph scores are rounded so float noise cannot separate runs that share
    exactly the same entities; those ties go to the more similar log.
    """
    similarity = {h.log_id: h.score for h in vector_hits}
    graph_score = {h.log_id: round(h.score, 6) for h in graph_hits}
    return sorted(
        set(similarity) | set(graph_score),
        key=lambda i: (-graph_score.get(i, 0.0), -similarity.get(i, -1.0), i),
    )


class HybridRetriever:
    def __init__(
        self,
        vector: Retriever,
        graph: GraphStore,
        expand_weight: float = 0.0,
        fusion: str = "graph_first",
    ):
        if fusion not in ("rrf", "graph_first"):
            raise ValueError(f"unknown fusion mode: {fusion!r}")
        self.vector = vector
        self.graph = graph
        self.expand_weight = expand_weight
        self.fusion = fusion

    def search(
        self,
        log_text: str,
        k: int = 5,
        exclude_log_id: str | None = None,
        exclude_repo: str | None = None,
        clean: bool = True,
    ) -> list[Hit]:
        """Return the k best past runs. Hit.score is the rank-based position
        score (1.0 for the top hit), since the fused order has no single scale.
        """
        text = clean_log(log_text) if clean else log_text
        vector_hits = self.vector.search(
            text, k=POOL, exclude_log_id=exclude_log_id, exclude_repo=exclude_repo, clean=False
        )
        graph_hits = self.graph.search(
            extract_entities(text), k=POOL, exclude_log_id=exclude_log_id,
            exclude_repo=exclude_repo, expand_weight=self.expand_weight,
        )
        if self.fusion == "rrf":
            order = reciprocal_rank_fusion(
                [[h.log_id for h in vector_hits], [h.log_id for h in graph_hits]]
            )
        else:
            order = graph_first(vector_hits, graph_hits)

        vector_by_id = {h.log_id: h for h in vector_hits}
        graph_by_id = {h.log_id: h for h in graph_hits}
        results = []
        for rank, log_id in enumerate(order[:k], start=1):
            base = vector_by_id.get(log_id) or graph_by_id[log_id]
            snippet = base.snippet
            if log_id in vector_by_id and log_id in graph_by_id:
                snippet += f"\n[{graph_by_id[log_id].snippet}]"
            results.append(Hit(log_id, base.repo, base.label, 1.0 / rank, snippet))
        return results
