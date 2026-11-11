# Pipeline Medic roadmap

The design and the rules each version follows are in
[`docs/DESIGN.md`](docs/DESIGN.md); release notes are in
[`CHANGELOG.md`](CHANGELOG.md). Each version ships with working code, tests,
an updated README and, where a technology was considered for adoption, an
`experiments/` note with the honest verdict.

| Version | Scope | Status |
|---|---|---|
| v0.1 | Local Ollama inference + FastAPI `/diagnose` | Shipped |
| v0.2 | Flat RAG baseline: last 15 lines beats whole log (cross-repo Recall@1 0.413 vs 0.217, 46 logs, 9 repos) | Shipped |
| v0.2.5 | Neo4j GraphRAG vs flat RAG: +0.028 MRR on held-out logs (95% CI -0.088 to +0.146), not proven; flat stays default | Shipped |
| v0.2.6 | Foundation: typed API, health checks, structured errors, request IDs, log parsing with line-referenced evidence, secret redaction | Shipped |
| v0.3 | Action Agent + MCP tools: ticket + notify only, dry-run by default, audit trail; local-file backends by decision | Shipped |
| v0.4 | LangGraph agent graph (Parser → Diagnosis → Classifier → Action), checkpointed; rule-based risk stage by default (ADR 004) | Shipped |
| v0.5 | LoRA risk classifier vs prompted LLM: LoRA 0.52–0.59 acc vs 0.50, not proven; rubric 0.609 wins | Shipped (LoRA not adopted) |
| v0.6 | Trajectory evaluation of the full graph: 27.8% fully correct (rubric) vs 11.1% (LLM); LLM judge unreliable (8/20 controls) | Shipped |
| v0.7 | Tracing: per-stage latency, tool-call outcomes linked to the audit log | Shipped |
| v0.8 | Security suite across the whole graph, threat model | Shipped |
| v0.9 | Final numbers on reviewed labels; decisions closed (ADR 004) | Shipped |
| v1.0 | Interactive Streamlit demo, Hugging Face Space packaging and sync, design doc, changelog, release | Shipped (Space goes live once created) |
| v1.1 | Improve diagnosis (the first error in 48 of 72 runs) on a fresh held-out set; run on real pipelines as a GitHub Action | Planned |

Out of scope by decision (`docs/DESIGN.md` §5): patch drafting or
application, sandboxed code execution, external ticket or chat services.
