# Changelog

All notable changes to Pipeline Medic. Numbers come from runs committed in
`evaluation/results/`; the reasoning behind each decision is in
`docs/decisions/` and `experiments/`.

## v1.0.0 — 2026-11-11

Demo, deployment and documentation.

- An interactive Streamlit demo (`streamlit run demo/app.py`) runs the real
  default graph on five real failed runs from five repositories, a synthetic
  log with fake credentials, or a pasted log. It shows every stage with its
  latency: redaction, evidence lines with their original line numbers, the
  diagnosis with the three most similar past failures, the rubric's risk
  reason and the proposed tool calls. Approve or Reject resumes the paused
  run and shows the dry-run result and the audit entries. Real actions are
  always off in the demo. One example deliberately shows a wrong diagnosis.
- A static, mobile-first demo on GitHub Pages that replays five real runs
  of the graph on held-out logs (four diagnosed correctly, one not), with
  the Results and "What didn't work" numbers read from `evaluation/results`.
  `demo/build_demo_data.py` exports the data and fails if it finds a
  secret or e-mail address, or a number that differs from the README.
- A Docker image for a free Hugging Face Space (CPU-only torch, embedding
  model baked in, non-root user) and a workflow that syncs `main` to the
  Space once `HF_TOKEN` and `HF_SPACE_ID` are set.
- `docs/DESIGN.md` (design and safety rules), this changelog, an MIT licence,
  a rewritten README and an updated roadmap.
- Tests: 353 (349 run locally; the 4 Neo4j tests run in CI).

## v0.9.0 — 2026-10-23

Polish, final numbers and three closed decisions.

- Reviewed and finalised the 72 held-out labels, then re-ran v0.2.5, v0.5
  and v0.6 on them. All results were unchanged.
- Made the rule-based risk classifier (rubric v1 on the retrieved category)
  the graph's default risk stage, because it won on every measure that
  mattered (ADR 004). The prompted-LLM classifier is still available as an
  option.
- Decided that tickets and notifications stay local files only, and kept
  the risk rubric as v1 (ADR 004).
- Rewrote the README to match exactly what shipped, with verified usage
  examples; corrected the dataset size to 24 repositories.
- Tests: 337, all passing in CI.

## v0.8.0 — 2026-10-21

Security hardening across the whole graph.

- Built a security suite of 80 tests with its own CI step
  (`pytest -m security`). It covers secret leakage into state, tickets,
  audit and traces; prompt injection through the log and through the
  model's answer; hostile run metadata; oversized logs; and malformed
  approvals.
- Shared adversarial fixtures: prompt injections, path traversals and
  token-shaped secrets built at runtime.
- `graph.start()` now enforces the same size limit as the API.
- Wrote the threat model (`docs/security.md`): each threat with its control
  and the test that proves it.
- Tests: 331 passing. One full run showed an intermittent failure that did
  not reproduce in four further runs or in CI.

## v0.7.0 — 2026-10-21

Observability.

- One tracing span per graph stage (keyed by run ID) and per tool call
  (linked to the audit log by action ID), exported as JSONL.
- A summary command for p50/p95 latency per stage and the tool-call success
  rate. Spans never contain log text.

## v0.6.0 — 2026-10-21

Whole-graph trajectory evaluation (experiment 004).

- Scored the full graph on 72 held-out logs, stage by stage, and recorded
  which stage went wrong first.
- With the rule-based risk stage, 27.8% of runs were fully correct; with
  the prompted LLM, 11.1%. Diagnosis is the first wrong stage in 48 of 72
  runs. Safety invariants and evidence grounding held in every run.
- Built an LLM-as-judge with a negative control. It caught a planted
  fabrication in only 8 of 20 tickets, so I do not trust its scores.

## v0.5.0 — 2026-10-21

LoRA risk classifier experiment (experiment 003).

- Froze risk labels in git before training, then fine-tuned MiniLM-L6 with
  LoRA (74,883 trainable parameters, 3 seeds).
- On 64 held-out logs, LoRA reached 0.52–0.59 accuracy against 0.50 for a
  prompted llama3.2. That gain is not proven (95% CI −0.125 to +0.214),
  and the prompted LLM missed all 12 high-risk failures. A rule-based
  classifier scored best (0.609). LoRA was not adopted.

## v0.4.0 — 2026-10-21

The agent graph.

- Wired the four agents into a LangGraph graph: parse → diagnose → risk →
  propose → human approval → execute.
- Checkpointing, so a paused run can be resumed by a new process; a
  LangGraph `interrupt()` before any tool runs; a trace entry per stage.
- Checkpoints only ever hold redacted text.

## v0.3.0 — 2026-10-21

The Action Agent and MCP tools.

- MCP server with `create_ticket`, `notify` and a read-only `lookup_log`.
  Dry-run by default; every call writes a `proposed` audit entry before
  anything happens.
- The Action Agent chooses tools by a fixed policy over category and risk,
  never from log text, so prompt injection in a log cannot change what it
  does.
- Guardrail tests for malformed input, oversized payloads, path traversal,
  channel allowlists and prompt injection.

## v0.2.6 — 2026-10-21

API foundation, log parsing and redaction.

- Validated settings, typed `/v1/diagnose`, liveness and readiness checks,
  one JSON error shape with request IDs, structured request logs, and mypy
  in CI.
- `POST /v1/parse` for GitHub Actions, Jenkins and plain-text logs. It
  returns failure regions (stack traces, errors, test summaries, exit codes)
  with their original line numbers.
- Secret redaction (11 credential types) before parsing, storage or any
  model call, with 0 false positives on 123 real public CI logs.

## v0.2.5 — 2026-10-21

Knowledge graph experiment (experiment 002, ADR 001).

- Built a Neo4j graph of tools, error signatures, packages and exit codes,
  plus graph and hybrid retrieval.
- Collected 72 more held-out logs, and froze the extraction rules in git
  before reading them.
- The chosen hybrid gained +0.145 MRR on the logs it was designed against,
  but only +0.028 on held-out logs (95% CI −0.088 to +0.146). Flat retrieval
  stays the default.

## v0.2.0 — 2026-10-01

Flat retrieval baseline (experiment 001).

- Collected real failed GitHub Actions logs and labelled their failure
  categories.
- Chroma + sentence-transformers retrieval, with a leave-one-out evaluation.
- Embedding the last 15 lines of a log nearly doubled cross-repo Recall@1
  over embedding the whole log (0.413 vs 0.217).
- CI workflow with lint and tests.

## v0.1.0 — 2026-10-01

- FastAPI `/diagnose` endpoint that sends a CI log to a local Ollama model
  and returns a short summary.
