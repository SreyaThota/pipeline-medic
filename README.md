# PipelineMedic X

**Status: 🚧 Building — PipelineMedic X: Phase 1 (foundation) shipped, Phase 2 next**

AI-assisted CI/CD failure diagnosis and safe remediation. It takes a failed
pipeline log, finds the evidence in it, retrieves similar past failures,
proposes a root cause and a patch, and records every step for audit. Anything
privileged or destructive needs explicit human approval.

It is built and measured on real GitHub Actions failure logs from public
open-source projects, not a toy dataset. Every claim in this README is tagged
✅ Shipped, 🚧 Building or 📋 Planned, and every number comes from a run that
is in the repo and reproducible.

## What works today

| Capability | Status |
|---|---|
| `POST /v1/diagnose`: Ollama summary of a log, typed request and response | ✅ Shipped (Phase 1) |
| `GET /health` (liveness) and `GET /health/ready` (checks Ollama) | ✅ Shipped (Phase 1) |
| One JSON error shape with a request ID; size limit; validated settings | ✅ Shipped (Phase 1) |
| `POST /diagnose`: the original v0.1 endpoint, kept for compatibility | ✅ Shipped, deprecated |
| Retrieval of similar past failures (flat vector search) | ✅ Shipped, measured (v0.2) |
| Neo4j knowledge graph and hybrid retrieval | 🚧 Built and measured, not the default (v0.2.5) |
| Parsing, redaction, structured diagnosis, patch proposals, approval and audit, UI | 📋 Planned, see [`ROADMAP.md`](ROADMAP.md) |

## Target architecture

This is the planned design, not a claim that every box exists yet.

```
log → parse + redact → retrieve similar incidents → structured diagnosis
    → patch proposal (diff only) → human approval
    → opt-in sandboxed verification → incident report + audit trail
```

Design rules: every diagnosis cites log lines or retrieved incident IDs; the
LLM only proposes, and application code validates and controls side effects;
a deterministic mode works with no LLM at all; logs and model output are
treated as untrusted; nothing is merged, deployed or executed on the host
automatically.

## Tech stack

FastAPI · Pydantic · Ollama · sentence-transformers · Chroma · Neo4j
(optional) · SQLite (planned) · Docker · pytest · GitHub Actions

### Retrieval results

The task: given a failed CI log, return past failures of the same category.
Scored leave-one-out on real GitHub Actions failure logs, excluding results
from the query's own repo ("cross-repo").

**v0.2: flat vector search.** 46 logs from 9 open-source repos:

| Chunking | Recall@1 (cross-repo) | MRR (cross-repo) |
|---|---|---|
| Whole log | 0.217 | 0.312 |
| **Last 15 lines** | **0.413** | **0.496** |
| 15-line windows | 0.174 | 0.282 |

Chance@1 is 0.15. Method, caveats and the same-repo numbers are in
[`experiments/001_chunking_strategy.md`](experiments/001_chunking_strategy.md).

**v0.2.5: knowledge graph (Neo4j).** Rule-based entities (tools, error
signatures, packages, exit codes) in a graph, alone and combined with flat
search. Every choice was made on the 46 original logs; the comparison that
counts is on 64 logs from 20 repos collected afterwards and held out
(draft labels):

| Method | MRR on dev logs | MRR on held-out logs | Gain over flat, held-out (95% interval) |
|---|---|---|---|
| Flat (v0.2) | 0.496 | 0.477 | — |
| **Hybrid, chosen on dev** | **0.641** | **0.504** | **+0.028 (-0.088 to +0.146)** |
| Graph only | 0.559 | 0.556 | +0.079 (-0.064 to +0.219) |
| Multi-hop graph | 0.451 | 0.419 | -0.058 (-0.187 to +0.067) |

The dev gain mostly came from fitting the rules to the logs they were written
against, and it does not hold up on new logs. Flat search stays the default.
Details: [`experiments/002_graphrag_vs_flat.md`](experiments/002_graphrag_vs_flat.md).

Design decisions are in [`docs/decisions/`](docs/decisions/) and the build plan in
[`ROADMAP.md`](ROADMAP.md).

## Running it locally

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows cmd
# .venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements-dev.txt
ollama pull llama3.2
uvicorn app.main:app --reload    # API docs at http://localhost:8000/docs

copy .env.example .env           # local settings (Neo4j password)
docker compose up -d              # Neo4j for the knowledge graph

python -m pytest                  # tests (graph tests skip without Neo4j)
python -m evaluation.run_eval     # flat retrieval baseline
python -m evaluation.run_graph_eval   # graph vs flat (needs Neo4j)
python data/collect_ci_logs.py    # collect more failed CI logs (needs gh auth)
```

## API examples

```bash
curl http://localhost:8000/health/ready
```
```bash
curl -X POST http://localhost:8000/v1/diagnose -H "Content-Type: application/json" -d "{\"log_text\": \"FAILED tests/test_api.py::test_login - AssertionError\"}"
```

Errors always look like
`{"error": {"code": "provider_unavailable", "message": "...", "request_id": "..."}}`.
Codes: `validation_error` (422), `log_too_large` (413), `provider_bad_response`
(502), `provider_unavailable` (503), `provider_timeout` (504), `internal_error` (500).

## Author

Sreya Thota — [github.com/SreyaThota](https://github.com/SreyaThota) ·
[linkedin.com/in/sreyathota5](https://linkedin.com/in/sreyathota5)
