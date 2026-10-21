# Pipeline Medic roadmap

Mirrors section 3 of `CLAUDE.md`, which is the source of truth. Each phase
ships with working code, a passing test, an updated README tag and, where a
technology was adopted, an `experiments/` note with the honest verdict.

| Phase | Scope | Status |
|---|---|---|
| v0.1 | Local Ollama inference + FastAPI `/diagnose` | Shipped |
| v0.2 | Flat RAG baseline: last 15 lines beats whole log (cross-repo Recall@1 0.413 vs 0.217, 46 logs, 9 repos) | Shipped |
| v0.2.5 | Neo4j GraphRAG vs flat RAG: +0.028 MRR on held-out logs, not proven; flat stays default | Building — held-out labels in review |
| v0.2.6 | Foundation: typed API, health checks, structured errors, request IDs, log parsing with line-referenced evidence, secret redaction | Shipped |
| v0.3 | Action Agent + MCP tools: ticket + notify only, dry-run by default, audit trail | Shipped (local backends; external backend undecided) |
| v0.4 | LangGraph agent graph (Parser → Diagnosis → Classifier → Action), checkpointed | Shipped (risk rubric is a draft) |
| v0.5 | LoRA-tuned risk/escalation classifier vs. prompted-LLM baseline | Shipped as an experiment: LoRA not adopted (gain not proven); draft labels |
| v0.6–v0.9 | Evaluation (RAGAS / LLM-as-judge), tracing, guardrail hardening; stretch: Streamlit console | Designed |
| v1.0+ | Polish, docs handbook, demo recording | Designed |

Not in scope (decided, see `CLAUDE.md` section 4): patch drafting or
application, sandboxed code execution, Jira/PR integrations, an incident UI.
