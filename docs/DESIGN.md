# Pipeline Medic: design

This is my engineering design document: what the system is, the rules I
built it under, and the decisions that shaped it. The per-version history is
in [`CHANGELOG.md`](../CHANGELOG.md), the decisions in detail are in
[`decisions/`](decisions/), and every measured claim links to a note in
[`experiments/`](../experiments/).

## 1. What it is

Pipeline Medic is an agentic CI/CD reliability copilot. It takes a failed
pipeline run, finds the lines that show why it failed, retrieves similar past
failures, judges how risky the failure is, and proposes a ticket or a
notification. Nothing runs until a person approves.

It is orchestrated as an explicit LangGraph state graph with four agents:

```
Log Parser Agent     redact secrets, parse, extract line-referenced evidence (deterministic)
  → Diagnosis Agent  flat-RAG retrieval over reviewed past failures, category by weighted vote
  → Risk Classifier  rubric v1 on the retrieved category (no model); an LLM classifier is opt-in
  → Action Agent     fixed policy → proposed create_ticket / notify (MCP tools)
  → human approval   LangGraph interrupt, checkpointed
  → execute          dry-run unless approved and ACTIONS_ENABLED; audited and traced
```

I built and measured three more ambitious components that are not in this
default path, because none of them beat a simpler option on held-out data:
a Neo4j knowledge graph (GraphRAG), a LoRA-fine-tuned risk classifier and a
prompted-LLM risk classifier. They stay in the repository with their
experiments, as honest negative results.

## 2. Engineering principles

**Measure before adopting.** Nothing joins the default path because it
sounds advanced. Each candidate gets an experiment note comparing it with the
simpler baseline it would replace, with a number and a confidence interval.
Non-trivial architecture choices get a short decision record.

**Report what is true.** Every feature in the README and roadmap is tagged as
shipped, in progress or planned, and never upgraded before the work exists.
A negative or marginal result is reported as it came out.

**One phase at a time.** I built the project in small versions, each with
working code, tests, updated status and, where relevant, an experiment.

## 3. Safety design

The system reads untrusted text (CI logs are written by whatever code ran in
a pipeline) and can take actions, so safety is designed in rather than added
later. The threat model, with the test for each control, is in
[`security.md`](security.md).

- **All log text, retrieved text and model output is untrusted.** The model
  never chooses a tool, a channel or a file; it can contribute one value from
  a fixed set, and by default the graph uses no model at all.
- **Secrets are redacted before anything else.** Before a log is parsed,
  stored, put in a checkpoint or sent to a model, 11 kinds of credential are
  replaced in place, keeping line numbers valid as evidence.
- **No real secrets anywhere in the repository.** Fixtures contain none, and
  tests build token-shaped strings at runtime. `.env.example` holds
  placeholders only.
- **Every tool call is audited.** A `proposed` entry is written before
  anything happens, then the outcome, whatever the size of the action.
- **Nothing runs without a person.** The graph pauses before execution; even
  after approval, actions are dry runs unless real actions are enabled.

## 4. Evaluation method

I learned these rules from the v0.2.5 experiment, where a gain that looked
clear on the logs I had designed against disappeared on new ones:

- **Freeze before looking.** Extraction rules, settings and labels are
  committed before any held-out data is read, so the git history proves the
  test set did not shape the method.
- **Split by repository.** 52 of the 64 scoreable held-out logs come from
  repositories never seen during design.
- **Label synthetic data as synthetic** and never mix it into a real-log
  number.
- **Report intervals, not just means.** Comparisons use paired bootstrap 95%
  intervals; a gain whose interval includes zero is reported as unproven.
- **Keep the evidence.** Raw predictions, configuration and dependency
  versions are saved next to every summary, in `evaluation/results/`.

## 5. Scope decisions

- **The Action Agent can only open a ticket or send a notification.** I
  considered drafting patches and verifying them in a sandbox, and decided
  against it: the system recommends, a person approves, and nothing it does
  is irreversible. That keeps the safety argument simple enough to defend
  completely.
- **Actions only write local files** (ADR 004). No external tracker or chat
  service is contacted, and no credentials are needed.
- **Flat retrieval is the default; GraphRAG is evaluated, not adopted**
  (ADR 001, experiment 002).
- **The rule-based risk classifier is the default** (ADR 004, experiments
  003 and 004).

## 6. Components

| Folder | What it does |
|---|---|
| `app/` | FastAPI service, settings, errors, log ingestion and redaction, graph state (`graph.py`), the LangGraph orchestrator, tracing |
| `agents/` | The four agents and the risk rubric |
| `mcp_server/` | MCP server with `create_ticket`, `notify` and read-only `lookup_log`, plus the audit log |
| `rag/` | Flat retrieval (Chroma + sentence-transformers); the Neo4j graph experiment |
| `ml/` | LoRA fine-tuning for the v0.5 experiment; risk-label builder |
| `evaluation/` | Experiment runners and their saved results |
| `data/` | 123 real failed CI logs with labels and provenance; synthetic fixtures |
| `tests/` | Unit, integration, security and failure-mode tests |

## 7. Data

- **Real CI failures:** 123 failed GitHub Actions runs from 24 open-source
  repositories, collected with `data/collect_ci_logs.py`, each linked to its
  original run. Split into `dev` (51 logs, used for design) and `test` (72
  logs, held out). All failure-category labels are human-reviewed.
- **Synthetic:** hand-written fixtures for parser and API tests, and 30
  training examples for the v0.5 experiment. Always marked as synthetic.

## 8. Tech stack

| Layer | Choice | Status |
|---|---|---|
| Orchestration | LangGraph | Default path |
| Tool calling | MCP (Python SDK) | Default path |
| API | FastAPI + Pydantic | Default path |
| Retrieval | Chroma + sentence-transformers | Default path |
| Knowledge graph | Neo4j + Cypher | Evaluated, not adopted |
| Fine-tuning | PEFT / LoRA | Evaluated, not adopted |
| Local LLM | Ollama (llama3.2) | Optional: `/v1/diagnose` and the opt-in classifier |
| Testing and CI | pytest, ruff, mypy, GitHub Actions | Default path |
| Infrastructure | Docker | Neo4j locally and in CI |
