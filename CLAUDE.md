# Pipeline Medic — Project Brief for Claude Code

This file is the persistent context for this repository. Read it in full at the
start of every session before writing any code. It is the single source of
truth for architecture, scope, and working rules. If anything in a chat prompt
conflicts with this file, point that out instead of silently picking one.

Owner: Sreya Thota — M.Sc. AI student, BTU Cottbus-Senftenberg. This is a
solo portfolio project built to be cited on her resume and walked through in
interviews, so everything below exists to keep the repo honest and
defensible under technical questioning, not just to look impressive.

---

## 1. What Pipeline Medic is

Pipeline Medic is an **agentic CI/CD reliability copilot**. It watches a
build/CI pipeline (its own GitHub Actions runs are the primary real data
source — "dogfooding"), diagnoses why a run failed, classifies how risky the
failure is, and either takes a safe automated action or escalates to a
human, with every stage traced and explainable.

Four-agent pipeline, orchestrated as an explicit LangGraph state graph:

```
Log Parser Agent → Diagnosis Agent (hybrid RAG: vector + knowledge graph)
                 → Risk Classifier (LoRA-tuned)
                 → Action Agent (MCP tools, dry-run by default)
                 → human escalation OR logged resolution
```

Differentiator: it is dogfooded against its own CI, not a toy dataset, and
every "upgrade" (flat RAG → GraphRAG, prompted classifier → LoRA classifier)
is shipped with a measured before/after comparison, not added because it
sounds advanced.

---

## 2. Non-negotiable working rules

**A. Phase discipline — the most important rule.**
Only build what the current prompt explicitly asks for. Do not pre-build a
later phase "while you're at it," do not scaffold agents/ internals during
Phase 0, do not add a feature from the roadmap below unless this session's
prompt names that phase. If a shortcut would require touching a future
phase's territory, stop and ask first. Sreya is learning the concepts
between phases on purpose — getting ahead of her defeats the point.

**B. Honesty discipline (this drives the README and resume language).**
Every feature in the README, roadmap, and code comments is tagged one of:
- `Shipped` — working, tested, in the repo right now.
- `Building` — in progress this phase.
- `Designed` — planned, described in docs/decisions/, not yet started.
Never upgrade a tag without the work actually being done. Never write a
docstring or README line implying something works when it's stubbed.

**C. "Every technology earns its place."**
No library or technique goes in because it's trendy. Before a new piece of
the stack (GraphRAG, LoRA, a new eval framework) is adopted, there must be a
one-page note in `experiments/` comparing it against the simpler baseline it
replaces, with a number attached (latency, precision/recall, retrieval
accuracy — whatever's relevant). Architecture choices that aren't trivial go
in `docs/decisions/NNN-title.md` as a short ADR (context, decision,
consequences).

**D. Git identity and commit style — do not add AI attribution.**
- Local git identity for this repo: `user.name = "Sreya Thota"`,
  `user.email = "sreyathota@gmail.com"`. Set these with `git config`
  (repo-local, i.e. without `--global`, unless Sreya says she already uses
  this identity globally) before the first commit.
- Do **not** append `Co-Authored-By: Claude`, a `Claude-Session` link, a
  "Generated with Claude Code" line, or any other AI-attribution trailer to
  commit messages or PR descriptions in this repository. Sreya directs,
  reviews, and owns every change; the commit history should read as her
  own engineering log.
- Commit messages: short conventional-commit style — `feat: …`, `fix: …`,
  `docs: …`, `chore: …`, `experiment: …`. One logical change per commit.
  No emoji, no filler.

**E. Stop and ask when scope is ambiguous**, rather than guessing and
producing a pile of code to review. A wrong assumption here costs Sreya more
time than a short clarifying question.

---

## 3. Tech stack (free / local-first)

| Layer | Choice | Why |
|---|---|---|
| LLM inference | Ollama, local (Llama 3.x / Qwen2.5) | Free, no API cost, works offline |
| Backend | FastAPI | Already shipped in v0.1 |
| Orchestration | LangGraph | Explicit, inspectable state graph, checkpointing |
| Vector store | Chroma + sentence-transformers | Flat RAG baseline before GraphRAG |
| Knowledge graph | Neo4j + Cypher | Multi-hop queries flat RAG can't answer |
| Tool calling | MCP (Model Context Protocol) | Typed, schema-validated, dry-run-by-default |
| Fine-tuning | LoRA / PEFT (Hugging Face) | Risk/escalation classifier, benchmarked vs. prompted baseline |
| Evaluation | RAGAS, LLM-as-judge, golden set | Trajectory eval, not just final-answer correctness |
| Observability | OpenTelemetry / Langfuse (planned) | Latency, cost, tool-success-rate tracing |
| Dashboard | Streamlit | Review console (stretch) |
| Infra | Docker, GitHub Actions | Dogfooded CI source + deployment |

---

## 4. Target folder structure

Build this incrementally, phase by phase — do not generate empty stub files
for every folder in one shot except in Phase 0, where placeholder READMEs
mark what's coming and when.

```
pipeline-medic/
├── README.md
├── CLAUDE.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── app/                    (main.py, graph.py, config.py)
├── agents/                 (parser_agent.py, diagnosis_agent.py, risk_classifier.py, action_agent.py)
├── rag/                    (ingest.py, retrieve.py, knowledge_base/)
├── mcp_server/             (server.py, tools/{create_ticket.py, lookup_log.py, search_docs.py})
├── ml/                     (anomaly_detector.py, lora_finetune/)
├── evaluation/             (benchmark.json, run_eval.py)
├── observability/          (tracing.py)
├── dashboard/              (streamlit_app.py)
├── data/                   (sample_logs/, synthetic_generator.py)
├── docs/                   (ontology.md, decisions/)
├── experiments/            (001_chunking_strategy.md, ...)
└── tests/
```

---

## 5. Datasets

1. **Dogfooded CI (primary)** — this repo's own GitHub Actions run logs.
2. **LogHub** — public log dataset, for broader coverage / stress-testing.
3. **Synthetic generator** — fills gaps the first two don't cover (rare
   failure classes, labelled risk levels for classifier training).

---

## 6. Roadmap (status as of Phase 0 kickoff — update tags as phases ship)

| Phase | Scope | Status |
|---|---|---|
| v0.1 | Local Ollama inference + FastAPI `/diagnose` endpoint | **Shipped** |
| v0.2 | Flat RAG baseline (Chroma) over real CI failure logs (public OSS + dogfooded), measured | Building — code, tests and baseline done; label review pending |
| v0.2.5 | Knowledge-graph upgrade (Neo4j/Cypher GraphRAG), measured vs. v0.2 baseline | Designed |
| v0.3 | Action Agent + MCP tools, dry-run by default, adversarial guardrail tests | Designed |
| v0.4 | Full LangGraph agent graph (Parser → Diagnosis → Classifier → Action), checkpointed | Designed |
| v0.5 | LoRA-tuned risk/escalation classifier vs. prompted-LLM baseline | Designed |
| v0.6–v0.9 | Evaluation (RAGAS/LLM-as-judge), observability (tracing), guardrails hardening; stretch: Streamlit review console | Designed |
| v1.0+ | Polish, docs, demo recording | Designed |

Each phase ships with: working code, a passing test for the new piece, an
updated README status tag, and — where a new technology was adopted — an
`experiments/` note with the before/after numbers.

---

## 7. How Sreya will prompt each phase

She will paste one phase at a time, referencing this file, roughly as:
"Implement v0.2 per CLAUDE.md — flat RAG baseline only, nothing from v0.2.5
onward." Treat each such prompt as scoped strictly to the named phase. End
each phase by: listing what was built, what's still a stub, updating the
roadmap table status, and stopping for review before touching the next phase.
