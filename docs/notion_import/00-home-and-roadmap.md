# PipelineMedic X: engineering handbook

This handbook explains how PipelineMedic X works, why it was built this way,
and how to defend each decision in an interview. It is plain Markdown so it
can be imported into Notion (Import → Markdown) or read on GitHub.

**Rule for every page:** a feature is described as implemented only if it
exists in the repository and has tests. Anything else is marked *planned*.

## What the project is

A service that takes a failed CI/CD log, finds the evidence in it, retrieves
similar past failures, and (as it grows) proposes a root cause and a patch for
a human to approve. It is built and measured on real GitHub Actions failure
logs from open-source projects.

## Status by phase

| Phase | Topic | Status | Handbook chapter |
|---|---|---|---|
| 0 | Reconnaissance and plan | Shipped | this page |
| 1 | Foundation: API, schemas, errors, health, config | Shipped | [10 – API, FastAPI and Pydantic](10-api-fastapi-pydantic.md) |
| 2 | Log parsing and redaction | Planned | 04 (planned) |
| 3 | Retrieval: lexical, semantic, hybrid | Planned (v0.2 baseline exists) | 05, 06 (planned) |
| 4 | Structured diagnosis | Planned | 07 (planned) |
| 5 | Patch proposals | Planned | 09 (planned) |
| 6 | Verification and audit | Planned | 08, 11 (planned) |
| 7 | UI and integrations | Planned | (planned) |
| 8 | Polish, threat model, demo | Planned | 13, 16, 19 (planned) |

## What already existed before PipelineMedic X

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
