# Pipeline Medic: engineering handbook

This handbook explains how Pipeline Medic works, why it was built this way,
and how to defend each decision in an interview. It is plain Markdown so it
can be imported into Notion (Import → Markdown) or read on GitHub.

**Rule for every page:** a feature is described as implemented only if it
exists in the repository and has tests. Anything else is marked *planned*.

## What the project is

A service that takes a failed CI/CD log, finds the evidence in it, retrieves
similar past failures, and (as it grows) proposes a root cause and a patch for
a human to approve. It is built and measured on real GitHub Actions failure
logs from open-source projects.

## Status

The handbook is a v1.0+ stretch goal. It has chapters for the parts that are
built; the full roadmap is in `ROADMAP.md`.

| Version | Topic | Status | Chapter |
|---|---|---|---|
| v0.1 | Ollama + FastAPI `/diagnose` | Shipped | — |
| v0.2 | Flat retrieval baseline | Shipped | `experiments/001_chunking_strategy.md` |
| v0.2.5 | Neo4j GraphRAG, evaluated not adopted | Shipped | `experiments/002_graphrag_vs_flat.md` |
| v0.2.6 | API foundation | Shipped | [10 – API, FastAPI and Pydantic](10-api-fastapi-pydantic.md) |
| v0.2.6 | Log parsing and redaction | Shipped | [04 – Log parsing and redaction](04-log-parsing-and-redaction.md) |
| v0.3 | MCP Action Agent: ticket + notify | Shipped | `docs/security.md` |
| v0.4 | LangGraph agent graph | Shipped | — |
| v0.5 | LoRA risk classifier, not adopted | Shipped (experiment) | `experiments/003_lora_risk_classifier.md` |
| v0.6 | Trajectory evaluation | Shipped | `experiments/004_trajectory_eval.md` |
| v0.7 | Tracing | Shipped | — |
| v0.8 | Security suite | Shipped | `docs/security.md` |

Handbook chapters for v0.3–v0.8 are part of v1.0, which needs a running-system review first.

## Earlier results

- **v0.1:** `POST /diagnose`, a FastAPI endpoint that sends a log to a local
  Ollama model and returns a two-sentence summary. Still available.
- **v0.2:** flat vector retrieval over 46 real failure logs. Embedding only
  the last 15 lines of a log beat embedding the whole log (cross-repo
  Recall@1 0.413 vs 0.217). See `experiments/001_chunking_strategy.md`.
- **v0.2.5:** a Neo4j knowledge graph of tools and error signatures. On
  held-out logs it gave no proven gain over flat search, so it is not the
  default. See `experiments/002_graphrag_vs_flat.md`.

## How to run it

```bash
pip install -r requirements-dev.txt
uvicorn app.main:app --reload        # http://localhost:8000/docs
python -m pytest                     # all tests, no model needed
```
