# Pipeline Medic

**Status: 🚧 Building — v0.2.5 (knowledge graph) measured; held-out labels in review**

An agentic CI/CD reliability copilot. It watches a build pipeline, diagnoses
*why* a run failed, judges how risky the failure is, and either takes a safe
automated action or escalates to a human — with every step traced and
explainable.

This is my flagship AI/ML + automation portfolio project, built to combine
agentic AI (LangGraph, RAG, knowledge graphs, MCP tool-calling) with the
production/CI-CD engineering background I already have. It runs on real
GitHub Actions failure logs, not a toy dataset: public open-source projects
for volume, plus this repo's own CI runs (dogfooding) as they accumulate.

I'm building and documenting this in public, phase by phase — see the
roadmap below for what's shipped vs. in progress vs. designed.

## Architecture

```
Log Parser Agent → Diagnosis Agent (hybrid RAG: vector + knowledge graph)
                 → Risk Classifier (LoRA-tuned)
                 → Action Agent (MCP tools, dry-run by default)
                 → human escalation OR logged resolution
```

Orchestrated as an explicit, inspectable LangGraph state graph.

## Why this architecture

- **Dogfooding** — the system's primary data source is its own CI, so every
  failure mode is real, not synthetic.
- **Measured upgrades, not buzzwords** — flat RAG ships first with a
  baseline measurement; GraphRAG only replaces it once the delta is proven.
  Every non-trivial choice has a before/after note in `experiments/`.
- **MCP tool-calling with guardrails** — the Action Agent's tools are
  schema-validated and dry-run by default, with adversarial-input tests.
- **Trajectory evaluation, not just final-answer correctness** — the system
  is graded on whether it took the right *path* through the pipeline, using
  a golden labelled log set.

## Tech stack

Ollama (local LLM inference) · FastAPI · LangGraph · Chroma · Neo4j/Cypher ·
MCP · LoRA/PEFT (Hugging Face) · RAGAS · Streamlit · Docker · GitHub Actions

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| v0.1 | Local Ollama inference + FastAPI `/diagnose` endpoint | ✅ Shipped |
| v0.2 | Flat RAG baseline over real CI failure logs (measured) | ✅ Shipped |
| v0.2.5 | Knowledge-graph upgrade (GraphRAG), measured vs. v0.2 | 🚧 Building — measured, no proven gain; labels in review |
| v0.3 | Action Agent + MCP tools, dry-run + guardrail tests | 📋 Designed |
| v0.4 | Full agent graph, checkpointed | 📋 Designed |
| v0.5 | LoRA-tuned risk classifier vs. prompted-LLM baseline | 📋 Designed |
| v0.6–v0.9 | Evaluation, observability, guardrail hardening (+ stretch: review console) | 📋 Designed |
| v1.0+ | Polish, docs, demo | 📋 Designed |

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

See `CLAUDE.md` for the full architecture brief and `docs/decisions/` for
design rationale as it's written.

## Running it locally

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows cmd
# .venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements-dev.txt
ollama pull llama3.2
uvicorn app.main:app --reload

copy .env.example .env           # local settings (Neo4j password)
docker compose up -d              # Neo4j for the knowledge graph

python -m pytest                  # tests (graph tests skip without Neo4j)
python -m evaluation.run_eval     # flat retrieval baseline
python -m evaluation.run_graph_eval   # graph vs flat (needs Neo4j)
python data/collect_ci_logs.py    # collect more failed CI logs (needs gh auth)
```

## Author

Sreya Thota — [github.com/SreyaThota](https://github.com/SreyaThota) ·
[linkedin.com/in/sreyathota5](https://linkedin.com/in/sreyathota5)
