# Pipeline Medic

**Status: ✅ v0.1–v0.9 shipped and measured on human-reviewed labels; v1.0 (handbook, demo) not started**

An agentic CI/CD reliability copilot. It takes a failed pipeline run,
diagnoses *why* it failed, judges how risky the failure is, and proposes a
safe action (open a ticket, notify someone) that a human approves before
anything happens, with every step traced and audited.

It is built and measured on real GitHub Actions failure logs from public
open-source projects, not a toy dataset. Every claim here is tagged ✅ Shipped,
🚧 Building or 📋 Designed, and every number comes from a run that is in the
repo and reproducible, including the negative results.

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
| Neo4j knowledge graph and hybrid retrieval | ✅ Built and measured; not adopted (v0.2.5) |
| MCP server: `create_ticket`, `notify`, read-only `lookup_log`; dry-run by default, every call audited | ✅ Shipped (v0.3), local file backends only |
| Action Agent: fixed ticket/notify policy from risk level; tool choice never taken from log text | ✅ Shipped (v0.3) |
| LangGraph agent graph: parse → diagnose → risk → propose → ⏸ human approval → execute; checkpointed | ✅ Shipped (v0.4) |
| Rule-based risk classifier (rubric v1 on the retrieved category) as the graph default | ✅ Shipped, chosen on measured results ([ADR 004](docs/decisions/004-resolve-open-decisions.md)) |
| LoRA risk classifier (MiniLM + LoRA) vs prompted LLM, measured on held-out logs | ✅ Built and measured; not adopted (v0.5) |
| Trajectory evaluation of the whole graph, stage by stage, with first-error attribution | ✅ Shipped (v0.6) |
| Tracing: span per graph stage and per tool call (`var/traces.jsonl`), latency and tool success-rate summary | ✅ Shipped (v0.7) |
| Security suite (80 tests, `pytest -m security`) and threat model ([`docs/security.md`](docs/security.md)) | ✅ Shipped (v0.8) |
| External ticket / notification backends (GitHub Issues, Slack, ...) | ❌ Out of scope by decision: local files only ([ADR 004](docs/decisions/004-resolve-open-decisions.md)) |

## Architecture

What runs today (`app/graph_orchestrator.py`):

```
Log Parser Agent     redact secrets, parse, extract line-referenced evidence (deterministic)
  → Diagnosis Agent  flat-RAG retrieval over reviewed past failures, category by weighted vote
  → Risk Classifier  rubric v1 on the retrieved category (no model); llama3.2 is opt-in
  → Action Agent     fixed policy → proposed create_ticket / notify (MCP tools)
  → ⏸ human approval (LangGraph interrupt, checkpointed)
  → execute          dry-run unless approved AND ACTIONS_ENABLED; audited and traced
```

GraphRAG (v0.2.5), the LoRA classifier (v0.5) and the prompted-LLM risk
classifier are built and measured but not in the default path: none beat the
simpler option on held-out logs. By default the graph needs no LLM at all. Safety
rules: logs, retrieved text and model output are untrusted; the model never
chooses a tool, channel or file; secrets are redacted before any model call;
nothing runs without a human's approval.

## Tech stack

Ollama (llama3.2) · FastAPI · Pydantic · LangGraph · MCP (Python SDK) ·
Chroma + sentence-transformers · Neo4j/Cypher (evaluated) · PEFT/LoRA
(evaluated) · Docker · pytest · mypy · GitHub Actions

## Results

All held-out numbers below use human-reviewed failure-category labels (123
real logs from 21 repos); risk levels come from rubric v1 applied to those
categories.

### Retrieval

The task: given a failed CI log, return past failures of the same category.
Scored leave-one-out, excluding results from the query's own repo
("cross-repo").

**v0.2: flat vector search.** 46 logs from 9 open-source repos:

| Chunking | Recall@1 (cross-repo) | MRR (cross-repo) |
|---|---|---|
| Whole log | 0.217 | 0.312 |
| **Last 15 lines** | **0.413** | **0.496** |
| 15-line windows | 0.174 | 0.282 |

Chance@1 is 0.15. Details: [`experiments/001`](experiments/001_chunking_strategy.md).

**v0.2.5: knowledge graph (Neo4j).** Every choice was made on the original
logs; the comparison that counts is on 64 later logs from 20 repos:

| Method | MRR on dev logs | MRR on held-out logs | Gain over flat, held-out (95% interval) |
|---|---|---|---|
| Flat (v0.2) | 0.496 | 0.477 | — |
| **Hybrid, chosen on dev** | **0.641** | **0.504** | **+0.028 (-0.088 to +0.146)** |
| Graph only | 0.559 | 0.556 | +0.079 (-0.064 to +0.219) |
| Multi-hop graph | 0.451 | 0.419 | -0.058 (-0.187 to +0.067) |

The dev gain mostly came from fitting the rules to the logs they were written
against. Flat search stays the default. Details: [`experiments/002`](experiments/002_graphrag_vs_flat.md).

### Risk classification (v0.5)

64 held-out logs; 52 of them from repos never seen in training.

| Classifier | Accuracy | Macro-F1 | High-risk recall |
|---|---|---|---|
| LoRA MiniLM (3 seeds) | 0.52–0.59 | 0.50–0.57 | 0.58 |
| Prompted llama3.2 (graph default) | 0.500 | 0.365 | **0.00** |
| Rubric on retrieved category (no model) | 0.609 | 0.544 | 0.67 |

LoRA minus prompted LLM: +0.047 accuracy (95% interval -0.125 to +0.214),
not proven, so LoRA is not adopted. The prompted LLM missed every high-risk
failure. The rule-based classifier is now the default (ADR 004). Details: [`experiments/003`](experiments/003_lora_risk_classifier.md).

### Whole-graph trajectories (v0.6)

72 held-out logs through the full graph, stage by stage:

| | Rubric risk stage | Prompted LLM risk stage |
|---|---|---|
| Fully correct trajectory | **27.8%** | 11.1% |
| Diagnosis correct | 33.3% | 33.3% |
| Evidence cites real log lines | 100% | 100% |
| Safety invariants held | 100% | 100% |

Diagnosis is the first wrong stage in 48 of 72 runs. An LLM-as-judge was
built, but it caught a planted fabrication in only 8 of 20 controls, so its
faithfulness verdicts are not trusted. Details: [`experiments/004`](experiments/004_trajectory_eval.md).

Design decisions are in [`docs/decisions/`](docs/decisions/) and the roadmap in
[`ROADMAP.md`](ROADMAP.md).

## Running it locally

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows cmd
# .venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements-dev.txt
ollama pull llama3.2
copy .env.example .env           # optional: every setting has a safe default
uvicorn app.main:app --reload    # API docs at http://localhost:8000/docs
```

Tests and checks:

```bash
python -m pytest                  # everything (Neo4j tests skip without Docker)
python -m pytest -m security      # the security suite only
ruff check . && mypy
```

The agents:

```bash
python -m mcp_server.server       # MCP server over stdio (dry-run by default)
python -m app.observability.tracing var/traces.jsonl   # latency / tool summary
```

```python
from app.config import get_settings
from app.graph import Approval
from app.graph_orchestrator import PipelineMedicGraph
from agents.diagnosis_agent import build_retriever

graph = PipelineMedicGraph.default(get_settings(), retriever=build_retriever())
paused = graph.start(open("failed_run.log").read(), workflow="CI")
print(paused["diagnosis"], paused["risk"], paused["proposed_actions"])
done = graph.resume(paused["run_id"], Approval(approved=True, approver="you"))
```

Experiments:

```bash
python -m evaluation.run_eval --split dev                  # v0.2 baseline
docker compose up -d && python -m evaluation.run_graph_eval   # v0.2.5 (Neo4j)
python -m evaluation.run_risk_eval --stage lora            # v0.5, then --stage prompted, --stage report
python -m evaluation.run_trajectory_eval --risk rules      # v0.6 (add --risk prompted --judge 20)
python data/collect_ci_logs.py                             # collect more failed CI logs (gh auth)
```

## API examples

```bash
curl http://localhost:8000/health/ready
```
```bash
curl -X POST http://localhost:8000/v1/parse -H "Content-Type: application/json" -d "{\"log_text\": \"export API_KEY=abcd1234efgh\nFAILED tests/test_x.py::test_y\"}"
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
