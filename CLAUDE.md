# PipelineMedic X — Project Brief for Claude Code

This file is the persistent context for this repository. Read it in full at the
start of every session before writing any code. It is the single source of
truth for architecture, scope, and working rules. If anything in a chat prompt
conflicts with this file, point that out instead of silently picking one.

Owner: Sreya Thota — M.Sc. AI student, BTU Cottbus-Senftenberg. This is a
solo portfolio project built to be cited on her resume and walked through in
interviews, so everything below exists to keep the repo honest and
defensible under technical questioning, not just to look impressive.

The full build brief ("PipelineMedic X — Build Brief", October 2026) was
adopted on 2026-10-21 and replaces the earlier agent roadmap (LangGraph, MCP,
LoRA). `ROADMAP.md` tracks the phases and their acceptance gates.

---

## 1. What PipelineMedic X is

An **AI-assisted CI/CD incident investigation and safe remediation
platform**. It ingests pipeline logs, extracts evidence, retrieves similar
historical incidents, proposes a root cause, suggests a patch, runs
controlled verification, and produces an auditable incident report.
Privileged or destructive actions require explicit human approval.

```
logs → parse + redact → retrieve similar incidents → structured diagnosis
     → patch proposal (diff only) → human approval → opt-in sandboxed
       verification → incident report + audit trail
```

Design principles:
- Evidence before explanation: every diagnosis links to log lines or
  retrieved incident IDs.
- Deterministic code controls permissions, validation, retries, timeouts and
  approval. LLMs propose; application code validates and controls side effects.
- Reproducible evaluation with held-out cases and honest metrics.
- Local-first, with a deterministic mode that works without any LLM.
- Security by default: redact secrets, limit log size, isolate patch
  execution, audit actions. Logs, repository files, retrieved text and model
  output are all untrusted data.

---

## 2. Non-negotiable working rules

**A. Phase discipline.**
Build only the phase that is current in `ROADMAP.md`. At the start of each
phase state its goal, files to change, acceptance criteria and risks. Run the
relevant tests, fix regressions, and summarise before moving on. Do not
pre-build a later phase. Sreya chose continuous pacing (2026-10-21): move to
the next phase without waiting, but stop for any real decision, for any
review only she can do, and before Phase 3 if the held-out labels are still
draft.

**B. Honesty discipline (this drives the README and resume language).**
Every feature in the README, roadmap, and docs is tagged one of:
- `Shipped` — working, tested, in the repo right now.
- `Building` — in progress this phase.
- `Planned` — on the roadmap, not started.
Never upgrade a tag without the work actually being done. Never claim a test
passed without running it. Never invent benchmark results, screenshots,
integrations or usage. Keep the original v0.2 experiment and its numbers
intact and reproducible.

**C. "Every technology earns its place."**
Prefer a minimal, reliable stack. No new infrastructure (Redis, Celery,
PostgreSQL, Next.js, Grafana, ...) without a concrete requirement; explain
the trade-off first. New retrieval or modelling techniques get an
`experiments/` note comparing them with the simpler baseline, with numbers.
Non-trivial architecture choices get an ADR in `docs/decisions/`.

**D. Git identity and commit style — do not add AI attribution.**
- Local git identity for this repo: `user.name = "Sreya Thota"`,
  `user.email = "sreyathota@gmail.com"` (repo-local).
- Do **not** append `Co-Authored-By: Claude`, a `Claude-Session` link, a
  "Generated with Claude Code" line, or any other AI-attribution trailer to
  commit messages or PR descriptions in this repository. Sreya directs,
  reviews, and owns every change; the commit history should read as her
  own engineering log.
- Commit messages: short conventional-commit style — `feat: …`, `fix: …`,
  `docs: …`, `chore: …`, `test: …`, `experiment: …`. One logical change per
  commit. No emoji, no filler.

**E. Stop and ask when scope is ambiguous**, rather than guessing and
producing a pile of code to review.

**F. Safety rules.**
- Secrets never go in source control, prompts, logs, fixtures or docs.
  `.env.example` holds placeholders only.
- No auto-merge, deployment, or production mutation. Never execute
  model-generated commands on the host.
- Patch execution is opt-in, containerised, time- and resource-limited, and
  network-disabled by default. If isolation is unavailable, report
  "verification unavailable" instead of running anything.
- Integrations (GitHub, Jira) are disabled unless configured, least-privilege,
  with a mock mode. Tests never need real credentials.

---

## 3. Tech stack

| Layer | Choice | Why |
|---|---|---|
| API | FastAPI + Pydantic | Typed contracts, validation, OpenAPI docs |
| LLM | Ollama (local), behind an adapter; deterministic no-LLM mode | Free and offline; provider swappable |
| Retrieval | Embeddings (sentence-transformers) in Chroma; lexical baseline; hybrid fusion | Flat vector search is the measured default |
| Knowledge graph | Neo4j (optional) | Built and measured in v0.2.5; no proven gain, so not the default |
| Persistence | SQLite (stdlib) for incidents and audit | No server needed until a requirement says otherwise |
| Isolation | Docker, network-disabled, resource-limited | Opt-in patch verification only |
| Tests and CI | pytest, ruff, mypy, GitHub Actions | Unit, integration, security and failure-mode tests |

---

## 4. Repository layout (target, built incrementally)

```
app/            FastAPI app: api/, schemas/, ingestion/, redaction/,
                retrieval/, diagnosis/, patching/, verification/,
                workflows/, integrations/, persistence/, observability/
rag/            v0.2 / v0.2.5 retrieval code (moves into app/retrieval/ in Phase 3)
evaluation/     retrieval evaluation scripts and results
experiments/    one note per measured experiment
data/           sample_logs/ (real CI logs, provenance in index.csv), fixtures/
tests/          unit/, integration/, security/, failure_modes/
docs/           decisions/, architecture/, notion_import/ (handbook)
```

---

## 5. Datasets

1. **Real CI logs** — failed GitHub Actions runs from public open-source
   repos plus this repo's own CI, in `data/sample_logs/` with provenance.
   Split: `dev` (51 logs, used for design) and `test` (72 logs, held out).
2. **Synthetic fixtures** — clearly labelled as synthetic, for parser,
   redaction, security and failure-mode tests. Never mixed into real-log
   metrics.

---

## 6. Roadmap

See `ROADMAP.md` for phases, status and acceptance gates. Completed history:

| Version | Scope | Status |
|---|---|---|
| v0.1 | Local Ollama inference + FastAPI `/diagnose` endpoint | **Shipped** |
| v0.2 | Flat RAG baseline over real CI failure logs, measured | **Shipped** |
| v0.2.5 | Neo4j knowledge graph, measured vs. v0.2 on held-out logs | Building — measured (no proven gain); held-out label review pending |

---

## 7. How each phase ends

List what was built, what is still planned, commands run and their real
results, known limitations, and the next highest-value task. Update the
README, `ROADMAP.md` and the handbook in `docs/notion_import/` to match what
actually exists.
