# tests/

Each phase ships with a passing test for its new piece. Run with
`python -m pytest`.

- `test_diagnose.py`: v0.1 `/diagnose` endpoint, with Ollama mocked.
- `test_ingest.py`: log cleaning and chunking.
- `test_retrieve.py`: retrieval ranking and leave-one-out filters.
- `test_eval_metrics.py`: recall@k, MRR, chance baseline.

The retrieval tests use a deterministic bag-of-words embedder from
`conftest.py`, so they never download a model.
