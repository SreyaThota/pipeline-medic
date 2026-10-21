# tests/

Run everything with `python -m pytest`. No test needs a model download, an
LLM, network access or real credentials: Ollama is faked and embeddings use a
deterministic bag-of-words embedder from `conftest.py`.

| Folder | What it covers |
|---|---|
| `unit/` | Settings validation, log parsing and failure regions, log cleaning and chunking, retrieval ranking, entity rules, fusion, eval metrics |
| `integration/` | The HTTP API (`/health`, `/health/ready`, `/v1/parse`, `/diagnose`, `/v1/diagnose`), the Neo4j graph store, and a parse of every real log in the dataset |
| `security/` | Secret redaction: token formats, partial replacement, false positives, nothing reaching the model or the API response |
| `failure_modes/` | Model provider unreachable, timing out, or returning unusable output |

`integration/test_graph.py` needs Neo4j (`docker compose up -d`): it is
skipped locally without it and required in CI (`REQUIRE_NEO4J=1`).

Shared fixtures in `conftest.py`: `client` (API with test settings),
`fake_ollama` (records calls, returns or raises what you set), `fake_embed`.
