# PipelineMedic X roadmap

Adopted 2026-10-21 from the PipelineMedic X build brief. Each phase ends only
when its acceptance gate is met with tests that were actually run.

| Phase | Scope | Acceptance gate | Status |
|---|---|---|---|
| 0 | Repository reconnaissance and plan | Inventory and phased plan approved | Shipped |
| 1 | Foundation: validated settings, typed schemas, `/health`, structured errors, versioned API, type-checking, regression tests | Core API runs; existing behaviour preserved; deterministic tests pass | Planned |
| 2 | Ingestion and evidence: GitHub Actions / Jenkins / text parsers, line references, secret redaction, size limits, synthetic fixtures | Parsing and redaction have unit and security tests | Planned |
| 3 | Retrieval experiments: lexical baseline, semantic, hybrid fusion, optional graph; one evaluation harness with saved raw results | Baselines reproducible; every method measured on the same held-out set | Planned (needs reviewed held-out labels) |
| 4 | Structured diagnosis: provider adapter, validated output, evidence grounding, bounded retries, deterministic fallback | Outputs validate against schemas and cite real evidence | Planned |
| 5 | Patch proposals: diffs only, path validation, preview, approval gate | Unsafe patches rejected; nothing applied without approval | Planned |
| 6 | Verification and audit: SQLite persistence, state machine, idempotency, opt-in network-less sandbox | Security and failure-mode tests pass or limits documented | Planned |
| 7 | UI and integrations: incident workspace, read-only GitHub, mock Jira | Works on real API data; no fake metrics | Planned |
| 8 | Portfolio polish: diagrams, handbook, demo script, threat model, clean-setup check | Docs match the implementation | Planned |

## History before PipelineMedic X

| Version | Scope | Result |
|---|---|---|
| v0.1 | Ollama + FastAPI `/diagnose` | Shipped |
| v0.2 | Flat vector retrieval, chunking experiment | Last 15 lines: cross-repo MRR 0.496 on 46 queries (`experiments/001`) |
| v0.2.5 | Neo4j knowledge graph and hybrid | No proven gain on held-out logs (`experiments/002`); labels in review |
