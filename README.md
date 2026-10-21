# Pipeline Medic

**Status: 🚧 Building — v0.2.6 foundation shipped; v0.2.5 held-out labels in review; v0.3 (MCP Action Agent) next**

An agentic CI/CD reliability copilot. It takes a failed pipeline run,
diagnoses *why* it failed, judges how risky the failure is, and either takes a
safe action (open a ticket, notify someone) or escalates to a human, with
every step traced and explainable.

It is built and measured on real GitHub Actions failure logs from public
open-source projects plus its own CI, not a toy dataset. Every claim here is
tagged ✅ Shipped, 🚧 Building or 📋 Designed, and every number comes from a
run that is in the repo and reproducible, including a negative result.

## What works today

| Capability | Status |
|---|---|
| `POST /v1/parse`: GitHub Actions / Jenkins / text logs into line-referenced failure evidence | ✅ Shipped (v0.2.6) |
| Secret redaction before parsing, storage or any model call | ✅ Shipped (v0.2.6) |
| `POST /v1/diagnose`: Ollama summary of a log, typed request and response | ✅ Shipped (v0.2.6) |
| `GET /health` (liveness) and `GET /health/ready` (checks Ollama) | ✅ Shipped (v0.2.6) |
| One JSON error shape with a request ID; size limit; validated settings | ✅ Shipped (v0.2.6) |
| `POST /diagnose`: the original v0.1 endpoint, kept for compatibility | ✅ Shipped, deprecated |
| Retrieval of similar past failures (flat vector search) | ✅ Shipped, measured (v0.2) |
| Neo4j knowledge graph and hybrid retrieval | 🚧 Built and measured, not adopted (v0.2.5) |
| MCP server: `create_ticket`, `notify`, read-only `lookup_log`; dry-run by default, every call audited | ✅ Shipped (v0.3), local backends only |
| Action Agent: fixed ticket/notify policy from risk level; tool choice never taken from log text | ✅ Shipped (v0.3) |
| LangGraph agent graph: parse → diagnose (flat RAG) → risk (prompted LLM, rubric fallback) → propose → human approval → execute; checkpointed | ✅ Shipped (v0.4), draft risk rubric |
| LoRA risk classifier (MiniLM + LoRA) vs prompted LLM, measured on held-out logs | 🚧 Built and measured, not adopted (v0.5, draft labels) |
| Trajectory evaluation of the whole graph, stage by stage, with first-error attribution | ✅ Shipped (v0.6), draft labels |
| Tracing: span per graph stage and per tool call (`var/traces.jsonl`), latency and tool success-rate summary | ✅ Shipped (v0.7) |
| Security suite (80 tests, `pytest -m security`) and threat model ([`docs/security.md`](docs/security.md)) | ✅ Shipped (v0.8) |

## Architecture

The target design; the roadmap shows which parts exist.

```
Log Parser Agent → Diagnosis Agent (retrieval: flat RAG default,
                     GraphRAG evaluated and not adopted)
                 → Risk Classifier (LoRA-tuned)
                 → Action Agent (MCP tools: ticket + notify only, dry-run by default)
                 → human escalation OR logged resolution
```

Orchestrated as an explicit LangGraph state graph. Safety rules: logs,
retrieved text and model output are untrusted; secrets are redacted before
any model call; the system recommends and a human approves; nothing it does
is irreversible; every tool call is audited.

## Tech stack

Ollama · FastAPI · Pydantic · Chroma + sentence-transformers · Neo4j/Cypher
(evaluated) · LangGraph, MCP, LoRA/PEFT (designed) · Docker · pytest ·
GitHub Actions

## Results

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

Design decisions are in [`docs/decisions/`](docs/decisions/) and the roadmap in
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
curl -X POST http://localhost:8000/v1/parse -H "Content-Type: application/json" -d "{\"log_text\": \"export API_KEY=abcd1234efgh
FAILED tests/test_x.py::test_y\"}"
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
