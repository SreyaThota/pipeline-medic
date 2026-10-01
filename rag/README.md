# rag/

Retrieval layer: find past CI failures similar to a new one.

- `ingest.py`: clean logs (strip gh prefixes, timestamps, ANSI codes and
  post-job cleanup), chunk, embed with `all-MiniLM-L6-v2`, store in Chroma.
  `python -m rag.ingest` builds the persistent index in `chroma_db/`.
- `retrieve.py`: `Retriever.search()` embeds the tail of a new log and
  returns the k most similar past logs, with their labels.
- `knowledge_base/`: runbooks and docs. Not used yet.

Status:
- **Shipped:** flat vector RAG (v0.2), measured in
  `experiments/001_chunking_strategy.md`.
- **Designed:** Neo4j GraphRAG (v0.2.5), adopted only if it beats that
  baseline.
