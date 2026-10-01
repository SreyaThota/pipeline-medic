"""Retrieve past CI failures similar to a new failure log (v0.2 flat RAG).

Chroma returns chunks; a log's score is its best-matching chunk's cosine
similarity (max-aggregation), so one strongly matching error window is
enough to surface a log.
"""

from dataclasses import dataclass

import chromadb

from rag.ingest import Embedder, chunk_log, clean_log


@dataclass
class Hit:
    log_id: str
    repo: str
    label: str
    score: float  # cosine similarity of the best chunk, higher is closer
    snippet: str


class Retriever:
    def __init__(self, collection: chromadb.Collection, embed: Embedder, query_window: int = 15):
        self.collection = collection
        self.embed = embed
        self.query_window = query_window

    def search(
        self,
        log_text: str,
        k: int = 5,
        exclude_log_id: str | None = None,
        exclude_repo: str | None = None,
        clean: bool = True,
    ) -> list[Hit]:
        """Return the k most similar logs.

        The query is the tail of the incoming log, since that is where a
        failure's error output almost always is. The exclude_* filters exist
        for leave-one-out evaluation.
        """
        text = clean_log(log_text) if clean else log_text
        query = chunk_log(text, "tail", window=self.query_window)
        if not query:
            return []

        filters = []
        if exclude_log_id:
            filters.append({"log_id": {"$ne": exclude_log_id}})
        if exclude_repo:
            filters.append({"repo": {"$ne": exclude_repo}})
        where = None if not filters else filters[0] if len(filters) == 1 else {"$and": filters}

        result = self.collection.query(
            query_embeddings=self.embed(query),
            n_results=min(k * 20, self.collection.count()),
            where=where,
            include=["metadatas", "distances", "documents"],
        )
        best: dict[str, Hit] = {}
        for meta, dist, doc in zip(
            result["metadatas"][0], result["distances"][0], result["documents"][0]
        ):
            score = 1.0 - dist
            hit = best.get(meta["log_id"])
            if hit is None or score > hit.score:
                best[meta["log_id"]] = Hit(meta["log_id"], meta["repo"], meta["label"], score, doc)
        return sorted(best.values(), key=lambda h: h.score, reverse=True)[:k]
