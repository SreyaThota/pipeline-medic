# rag/

Retrieval layer: find past CI failures similar to a new one.

- `ingest.py`: clean logs (strip gh prefixes, timestamps, ANSI codes and
  post-job cleanup), chunk, embed with `all-MiniLM-L6-v2`, store in Chroma.
  `python -m rag.ingest` builds the persistent index in `chroma_db/`.
- `retrieve.py`: `Retriever.search()` embeds the tail of a new log and
  returns the k most similar past logs, with their labels.
- `entities.py`: rule-based extraction of tools, error signatures,
  packages and exit codes from a cleaned log.
- `graph.py`: Neo4j knowledge graph of runs and their entities (schema in
  `docs/ontology.md`). `python -m rag.graph` loads the labelled logs.
- `hybrid.py`: combines graph and vector results (graph-first or RRF).
- `knowledge_base/`: runbooks and docs. Not used yet.

Status:
- **Shipped:** flat vector RAG (v0.2), measured in
  `experiments/001_chunking_strategy.md`. This is the default retriever.
- **Building:** knowledge graph and hybrid retrieval (v0.2.5). Built, tested
  and measured in `experiments/002_graphrag_vs_flat.md`, with no proven gain
  over flat on held-out logs, so not the default.
