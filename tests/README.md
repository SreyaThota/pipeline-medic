# tests/

Each phase ships with a passing test for its new piece. Run with
`python -m pytest`.

- `test_diagnose.py`: v0.1 `/diagnose` endpoint, with Ollama mocked.
- `test_ingest.py`: log cleaning and chunking.
- `test_retrieve.py`: retrieval ranking and leave-one-out filters.
- `test_eval_metrics.py`: recall@k, MRR, chance baseline.
- `test_entities.py`: the entity extraction rules.
- `test_hybrid.py`: graph-first and reciprocal-rank fusion.
- `test_graph.py`: the Neo4j graph store. Needs Neo4j; skipped locally
  without it, required in CI (`REQUIRE_NEO4J=1`).

The retrieval tests use a deterministic bag-of-words embedder from
`conftest.py`, so they never download a model.
