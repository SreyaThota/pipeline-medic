# Pipeline Medic — Project Brief for Claude Code

Read this file in full at the start of every session before writing any code.
It is the single source of truth for architecture, scope, and working rules.
If a chat prompt conflicts with this file, say so instead of silently picking
one. This version supersedes earlier copies — it folds in the v0.2/v0.2.5
results and the security/evaluation rigor merged in from the "PipelineMedic X"
brief (2026-10, reviewed and merged, not adopted wholesale — see section 9).

Owner: Sreya Thota — M.Sc. AI student, BTU Cottbus-Senftenberg. Solo
portfolio project, cited on her resume and walked through in interviews.
Everything below exists to keep the repo honest and defensible under
technical questioning, not just to look impressive.

---

## 1. What Pipeline Medic is

An **agentic CI/CD reliability copilot**. It watches a build/CI pipeline (its
own GitHub Actions runs are the primary real data source — "dogfooding"),
diagnoses why a run failed, classifies how risky the failure is, and either
takes a safe automated action or escalates to a human, with every stage
traced and explainable.

Four-agent pipeline, orchestrated as an explicit LangGraph state graph:

```
Log Parser Agent → Diagnosis Agent (hybrid retrieval: flat RAG default,
                     GraphRAG evaluated and not adopted — see section 3)
                 → Risk Classifier (LoRA-tuned)
                 → Action Agent (MCP tools: ticket + notify only, dry-run by default)
                 → human escalation OR logged resolution
```

Differentiator: dogfooded against its own CI, not a toy dataset. Every
"upgrade" ships with a measured before/after comparison, not because it
sounds advanced — this already produced one honest negative result (see
section 3) and that result is part of the story, not a thing to hide.

---

## 2. Non-negotiable working rules

**A. Phase discipline.** Only build what the current prompt explicitly asks
for. Don't pre-build a later phase "while you're at it." If a shortcut
requires touching a future phase's territory, stop and ask first.

**B. Honesty discipline.** Every feature in the README, roadmap, and code
comments is tagged `Shipped` / `Building` / `Designed`. Never upgrade a tag
without the work actually being done. A negative or marginal result (like
v0.2.5's GraphRAG finding) is reported as-is, not hidden or reframed.

**C. "Every technology earns its place."** No library goes in because it's
trendy. Before a new piece of the stack is adopted, there's a one-page note
in `experiments/` comparing it against the simpler baseline it replaces, with
a number attached. Non-trivial architecture choices get a short ADR in
`docs/decisions/`.

**D. Git identity — no AI attribution.** Local git identity for this repo:
`user.name = "Sreya Thota"`, `user.email = "sreyathota@gmail.com"`
(repo-local `git config`, not global, unless she says otherwise; this is the
address linked to her GitHub account, so commits credit SreyaThota). Do
**not** add `Co-Authored-By: Claude`, a session link, "Generated with Claude
Code," or any AI-attribution trailer to commits or PRs. Conventional-commit
style messages (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `experiment:`).

**E. Evaluation rigor** (codified from how v0.2.5 was actually run — keep
doing this, it's already working):
- Freeze extraction/scoring rules and commit them *before* reading new
  held-out data, specifically to avoid unconsciously fitting rules to the
  test set.
- Split by repository/incident family to reduce leakage; document the split.
- Clearly label synthetic data as synthetic; never mix it into a reported
  "real" number without saying so.
- Report the honest number even when it's not flattering — a dev-set gain
  that shrinks or vanishes on held-out data is a real, reportable finding.
- Save raw predictions, config, and dependency versions alongside summary
  metrics so results are reproducible, not just a number in a doc.

**F. Security baseline** (merged in from the PipelineMedic X brief, applies
now — not gated behind a future feature):
- Treat all log text, retrieved text, and model output as untrusted data.
- Redact likely secrets (tokens, API keys, passwords) before persisting log
  text or sending it to a model — dogfooded CI logs can plausibly contain
  real leaked credentials in failed-run output, this isn't theoretical.
  (Implemented in v0.2.6: `app/redaction/`, tested in `tests/security/`.)
- Never place real secrets in prompts, fixtures, logs, or docs; `.env.example`
  gets placeholders only.
- Any MCP tool call is logged (audit trail: what was proposed, what ran,
  what the result was) regardless of how small the action.

**G. Stop and ask when scope is ambiguous**, rather than guessing and
producing a pile of code to review.

---

## 3. Status (as of 2026-10-21 — update as phases ship)

| Phase | Scope | Status |
|---|---|---|
| v0.1 | Local Ollama inference + FastAPI `/diagnose` endpoint | **Shipped** |
| v0.2 | Flat RAG baseline, last-15-lines chunking. **Recall@1 0.413 vs 0.217 for whole-log chunking** (cross-repo), over 46 real CI/CD failure logs from 9 open-source repos | **Shipped** |
| v0.2.5 | Neo4j GraphRAG, measured against v0.2. Dev-set gain +0.145 shrank to an unproven +0.028 on held-out cross-repo logs (123 logs from 21 repos). **Flat search stays the default** — GraphRAG did not clearly earn its place on this data; documented in `experiments/002_graphrag_vs_flat.md` with the honest verdict | **Building** — measured; the 72 held-out labels are still draft and need Sreya's review before the number is final |
| v0.2.6 | Foundation (built 2026-10-21 under the PipelineMedic X brief, kept): validated settings, typed `/v1/diagnose`, `/health` + `/health/ready`, one JSON error shape with request IDs, structured request logs, mypy in CI; `/v1/parse` for GitHub Actions/Jenkins/text logs with line-referenced failure regions; secret redaction before any model call | **Shipped** |
| v0.3 | Action Agent + MCP tools — **scope is ticket-creation + notification only**, dry-run by default, human approves any real action. Patch drafting/auto-remediation was explicitly considered and declined for now (see section 4). Built: `mcp_server/` (create_ticket, notify, read-only lookup_log; audit log), `agents/action_agent.py`; real backends are local files until NEEDS_DECISION.md #1 is answered | **Shipped** |
| v0.4 | Full LangGraph agent graph (Parser → Diagnosis → Classifier → Action), checkpointed. Built: `app/graph_orchestrator.py`, `agents/` (parser, diagnosis = flat-RAG vote, prompted risk classifier with rubric fallback), `interrupt()` before any tool call, per-stage trace entries | **Shipped** |
| v0.5 | LoRA-tuned risk/escalation classifier vs. prompted-LLM baseline. Measured on draft labels (`experiments/003`): LoRA acc 0.52–0.59 vs prompted 0.50, gain not proven (+0.047, CI -0.125 to +0.214); prompted LLM missed all 12 high-risk logs; a model-free rubric on the retrieved category scored best (0.609). **LoRA not adopted**; classifier choice is NEEDS_DECISION.md #3 | **Shipped** (as a measured experiment) |
| v0.6 | Trajectory evaluation of the full graph (`evaluation/run_trajectory_eval.py`, `experiments/004`): 27.8% of held-out trajectories fully right with the rubric, 11.1% with the prompted LLM; diagnosis is the first error in 48/72; safety and grounding 100%. LLM-as-judge built but unreliable (caught 8/20 planted fabrications) | **Shipped** (draft labels) |
| v0.7 | Observability: `app/observability/tracing.py` — one span per graph stage (keyed by run id) and per tool call (linked to the audit log by action_id, outcome = executed/dry_run/rejected/failed), JSONL export, p50/p95 latency and tool success-rate summary. Spans carry no log text | **Shipped** |
| v0.8–v0.9 | Guardrail/security hardening (prompt-injection fixtures), polish; stretch: Streamlit review console | Designed |
| v1.0+ | Polish, docs handbook, demo recording | Designed |

Each phase ships with: working code, a passing test, an updated README
status tag, and — where a new technology was adopted — an `experiments/`
note with the before/after numbers, honest verdict included.

---

## 4. Scope decisions already made — don't silently reopen these

- **Action Agent = ticket + notify only.** No `draft_patch`, no patch
  application, no sandboxed code execution. This was an explicit choice
  (2026-10-15) over a more ambitious "auto-draft and sandbox-verify patches"
  design, specifically to keep the safety story simple and defensible in an
  interview: the system recommends, a human approves, nothing it does is
  irreversible. If this gets revisited, it needs an explicit decision again,
  not a quiet scope-creep back in because a later prompt mentions patches —
  flag it and ask rather than building it.
- **GraphRAG is evaluated, not adopted.** Flat RAG (Chroma + sentence-
  transformers) is the production default. The Neo4j code and the
  experiment stay in the repo as a documented, honest negative result — a
  real engineering story, not something to quietly remove.

---

## 5. Tech stack (free / local-first)

| Layer | Choice | Why |
|---|---|---|
| LLM inference | Ollama, local (Llama 3.x / Qwen2.5) | Free, no API cost, works offline |
| Backend | FastAPI + Pydantic | Typed request/response, auto OpenAPI docs |
| Orchestration | LangGraph | Explicit, inspectable state graph, checkpointing |
| Vector store | Chroma + sentence-transformers | Flat RAG — the shipped default |
| Knowledge graph | Neo4j + Cypher | GraphRAG — evaluated, not adopted (section 3) |
| Lexical retrieval | BM25 (candidate addition, not yet scoped into a phase) | Exact error codes / stack-trace tokens; cheap to add, worth a small experiment before a full hybrid-fusion phase |
| Tool calling | MCP (Model Context Protocol) | Typed, schema-validated, dry-run-by-default; ticket + notify only |
| Fine-tuning | LoRA / PEFT (Hugging Face) | Risk/escalation classifier, benchmarked vs. prompted baseline |
| Evaluation | RAGAS, LLM-as-judge, golden/held-out set | Trajectory eval, not just final-answer correctness |
| Observability | OpenTelemetry / Langfuse (planned) | Latency, cost, tool-success-rate tracing |
| Dashboard | Streamlit (stretch) | Review console |
| Infra | Docker, GitHub Actions | Dogfooded CI source; Neo4j runs as a CI service for graph tests |

---

## 6. Target folder structure

Folders marked (exists) are in the repo today; the rest are created by the
phase that needs them, not as empty stubs.

```
pipeline-medic/
├── README.md, CLAUDE.md, ROADMAP.md, pyproject.toml, .env.example, .gitignore
├── app/                     (exists: main.py, config.py, errors.py, api/, schemas/,
│                             ingestion/, redaction/, diagnosis/, observability/;
│                             later: graph.py — LangGraph state schema)
├── agents/                  (parser_agent.py, diagnosis_agent.py, risk_classifier.py, action_agent.py)
├── rag/                     (exists: ingest.py, retrieve.py — flat RAG, shipped;
│                             entities.py, graph.py, hybrid.py — Neo4j/GraphRAG, evaluated-not-adopted)
├── mcp_server/              (server.py, tools/{create_ticket.py, notify.py, lookup_log.py})
├── ml/                      (anomaly_detector.py, lora_finetune/)
├── evaluation/              (exists: run_eval.py, run_graph_eval.py, results/)
├── dashboard/               (streamlit_app.py)
├── data/                    (exists: sample_logs/ real logs, fixtures/ synthetic logs)
├── docs/                    (exists: ontology.md, decisions/, notion_import/ — handbook, v1.0+)
├── experiments/             (exists: 001_chunking_strategy.md, 002_graphrag_vs_flat.md, ...)
└── tests/                   (exists: unit/, integration/, security/, failure_modes/)
```

---

## 7. Datasets

1. **Dogfooded CI (primary)** — this repo's own GitHub Actions run logs, plus
   the 123-log cross-repo set from 21 open-source repos used for v0.2/v0.2.5
   (`dev` split: 51 logs used for design; `test` split: 72 held-out logs).
2. **LogHub** — public log dataset, for broader coverage.
3. **Synthetic** — `data/fixtures/` and any future generator. Always labeled
   synthetic in any report; never silently mixed with real-log numbers.

---

## 8. How Sreya prompts each phase

One phase, one prompt, one review cycle: "Implement v0.3 per CLAUDE.md —
ticket + notify MCP tools only, nothing from v0.4 onward." Each phase ends
with: what was built, what's still a stub, the roadmap status update, and a
stop for review before the next phase.

---

## 9. Note on the "PipelineMedic X" brief (2026-10-21)

A separate, more elaborate build brief ("PipelineMedic X") was reviewed and
partially merged into this file — specifically its security/redaction
discipline (section 2F) and its evaluation rigor (section 2E, which mostly
just wrote down what v0.2.5 already did). Its first two phases were built
before this decision and are kept as v0.2.6 (API foundation, parsing,
redaction): they fit this architecture and implement section 2F. Its larger
proposals — patch application with sandboxed verification, Jira/PR
integrations, a full incident workspace UI, a 20-document Notion handbook,
dropping LangGraph/MCP/LoRA in favor of a plain workflow/state-machine
backend — were **not** adopted. The agentic core (LangGraph, MCP, LoRA, the
GraphRAG experiment) stays as the architecture. If patch-apply-with-sandboxing
comes back into scope later, treat it as a new explicit decision per section
4, not an automatic merge.
