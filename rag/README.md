# rag/

Retrieval layer: `ingest.py`, `retrieve.py`, and `knowledge_base/`.
Flat vector RAG (Chroma + sentence-transformers) comes first; the Neo4j
knowledge-graph upgrade follows only if it beats the measured baseline.

Status: **Designed** — flat RAG built in Phase v0.2, GraphRAG in v0.2.5. Not yet started.
