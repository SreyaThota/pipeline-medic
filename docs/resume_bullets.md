# Resume bullets: Pipeline Medic

Every bullet below is backed by code in this repository and a measurement
you can reproduce (as of version 0.9.0, 2026-10-23). Each
number is followed by the file it comes from, so it can be defended in an
interview. Pick 2–3 bullets for the role; do not mix in the "Do not claim"
list at the bottom.

**Project line:** Pipeline Medic — agentic CI/CD failure-diagnosis copilot
(Python, LangGraph, MCP, FastAPI, Chroma, sentence-transformers, Neo4j,
PEFT/LoRA, pytest, GitHub Actions) · github.com/SreyaThota/pipeline-medic

---

## AI engineering (LLM / agents)

- Built a 4-agent LangGraph pipeline (parse → diagnose → risk → act) with
  checkpointing and a human-approval interrupt before any tool call; an MCP
  server exposes ticket, notify and log-lookup tools that are dry-run by
  default and audited on every call. *(app/graph_orchestrator.py,
  mcp_server/, tests/integration/test_graph_orchestrator.py)*
- Evaluated the agent end to end with trajectory scoring on 72 held-out CI
  failures: a rule-based risk stage gave 2.5× more fully correct runs than a
  prompted llama3.2 stage (27.8% vs 11.1%), which never flagged any of the 12
  high-risk failures; switched the default to the rule-based stage on that
  evidence. *(experiments/004, experiments/003, docs/decisions/004)*
- Hardened the agent against prompt injection and secret leakage with an
  80-test security suite: tool choice never comes from log text, model output
  is parsed to a fixed enum, and 11 credential types are redacted before any
  model call, with 0 false positives on 123 real public CI logs.
  *(tests/security/, docs/security.md, app/redaction/)*

## Machine learning

- Fine-tuned MiniLM-L6 with LoRA (74,883 trainable parameters, 0.33% of the
  model, 3 seeds) as a CI-failure risk classifier and benchmarked it on
  repositories unseen in training against a prompted LLM and a rule baseline;
  reported the honest result: 0.52–0.59 accuracy vs 0.50, a gain that was not
  statistically significant (95% CI −0.125 to +0.214). *(experiments/003,
  evaluation/run_risk_eval.py)*
- Designed a leakage-controlled evaluation: froze extraction rules and labels
  in git before reading 72 held-out logs (52 from unseen repos), and used
  paired-bootstrap confidence intervals. It showed a knowledge-graph (Neo4j
  GraphRAG) gain of +0.145 MRR on dev logs shrinking to an unproven +0.028 on
  held-out logs, so flat retrieval stayed the default. *(experiments/002)*
- Improved retrieval of similar past CI failures by measuring chunking
  strategies on real GitHub Actions logs: embedding the last 15 lines nearly doubled
  cross-repo Recall@1 over whole-log embedding (0.413 vs 0.217; MRR 0.496 vs
  0.312). *(experiments/001)*

## Automation / AIOps

- Built an AIOps copilot that turns a failed GitHub Actions or Jenkins run
  into line-referenced failure evidence, a likely failure category and a
  proposed ticket/notification, with nothing executed until a human approves.
  *(app/ingestion/, agents/, app/graph_orchestrator.py)*
- Collected and labelled a dataset of 123 real failed CI runs from 24
  open-source repositories (pytest, Django, React, Next.js, Cargo, ...) via
  the GitHub CLI, with provenance for every log. *(data/collect_ci_logs.py,
  data/sample_logs/index.csv)*

## Backend

- Built a typed FastAPI service (Pydantic schemas, validated settings,
  liveness/readiness checks, one JSON error contract with 6 error codes and
  request IDs, structured request logs that never include bodies), covered by
  337 pytest tests and strict mypy in CI. *(app/, tests/)*
- Wrote a log parser for GitHub Actions, Jenkins and plain-text logs that
  extracts stack traces, failing tests and exit codes with original line
  numbers; validated it on all 123 real logs at ~45 ms per log.
  *(app/ingestion/, tests/integration/test_real_logs.py)*
- Added per-stage tracing (latency p50/p95) and tool-call outcome tracking
  linked to an append-only audit log by action ID.
  *(app/observability/tracing.py, mcp_server/audit.py)*

## Full-stack

There is no frontend in this project, so it does not support a full-stack
claim on its own. These bullets cover the parts beyond the backend that a
full-stack role values:

- Shipped the service with Docker Compose (Neo4j) and GitHub Actions CI
  running lint, type-checks, an 80-test security stage and the full suite
  against a Neo4j service container; an on-demand workflow reproduces the
  retrieval experiments. *(docker-compose.yml, .github/workflows/)*
- Designed the API contract with OpenAPI docs generated from Pydantic
  models, including a versioned `/v1` API alongside a deprecated legacy
  endpoint kept for compatibility. *(app/api/, app/schemas/)*

---

## Do not claim (not built, or measured as not better)

- A UI or incident dashboard (none exists).
- Real ticket or Slack/Jira integrations (by decision, actions only write
  local files).
- That GraphRAG, the LoRA model or the LLM risk classifier improved results
  (all three were measured and not adopted).
- Production deployment, users or traffic.
- Automatic remediation, patch generation or code execution.
- LLM-as-judge or RAGAS faithfulness scores (the judge caught only 8 of 20
  planted fabrications, so its scores are not trustworthy).
