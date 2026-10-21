# tests/

Run everything with `python -m pytest`. No test needs a model download, an
LLM, network access or real credentials: Ollama is faked, embeddings use a
deterministic bag-of-words embedder from `conftest.py`, and every tool writes
to a temporary directory.

| Folder | What it covers |
|---|---|
| `unit/` | Settings, log parsing and failure regions, chunking, retrieval, entity rules, fusion, MCP tools, Action Agent policy, Diagnosis Agent vote, risk classifier parsing and fallback, tracing, v0.5/v0.6 evaluation logic |
| `integration/` | The HTTP API, the MCP server over the real protocol, the full LangGraph graph (pause, resume from checkpoint, reject, no-action path), tracing end to end, the Neo4j graph store, a parse of every real log |
| `security/` | `pytest -m security`: redaction, tool guardrails (malformed, oversized, path traversal, channel allowlist), prompt injection via the log and via the model's answer, hostile run metadata, malformed approvals; shared fixtures in `fixtures.py`; threat model in `docs/security.md` |
| `failure_modes/` | Model provider unreachable, timing out, or returning unusable output |

`integration/test_graph.py` needs Neo4j (`docker compose up -d`): it is
skipped locally without it and required in CI (`REQUIRE_NEO4J=1`).

Shared fixtures in `conftest.py`: `client` (API with test settings),
`fake_ollama` (records calls, returns or raises what you set), `fake_embed`.
