# Overnight summary (2026-10-21 → 2026-10-22)

Read this first. Every phase v0.3–v0.9 was attempted; all are committed,
pushed, and green in CI. Several results rest on **draft labels**, and three
design questions are waiting for you in `NEEDS_DECISION.md` (copied below).

## Phase status

| Phase | Status | Headline |
|---|---|---|
| v0.3 MCP Action Agent | **Done** | `mcp_server/` with create_ticket, notify, read-only lookup_log; dry-run by default; every call audited (`proposed` before any outcome); `agents/action_agent.py` picks tools by a fixed policy, never from log text. Real backends are local files only (decision #1). |
| v0.4 LangGraph graph | **Done** | `app/graph_orchestrator.py`: parse → diagnose (flat RAG) → risk (prompted llama3.2, rubric fallback) → propose → `interrupt()` for human approval → execute. Checkpointed (resume works from a new graph instance); a trace entry per stage. Risk rubric is a draft (decision #2). |
| v0.5 LoRA risk classifier | **Done, as an experiment** | MiniLM + LoRA, 3 seeds, labels frozen before training. Accuracy 0.52–0.59 vs prompted LLM 0.50: gain **not proven** (+0.047, CI -0.125 to +0.214). The prompted LLM **missed all 12 high-risk logs**. A model-free rubric on the retrieved category scored best (0.609). LoRA **not adopted** (decision #3). |
| v0.6 Trajectory evaluation | **Done** | Whole-graph runs on 72 held-out logs: **27.8%** fully correct with the rubric risk stage, **11.1%** with the prompted LLM. Diagnosis is the first error in 48/72. Safety and evidence grounding 100%. The LLM-as-judge caught only 8/20 planted fabrications, so its verdicts are not trusted. |
| v0.7 Observability | **Done** | `app/observability/tracing.py`: a span per graph stage (keyed by run id) and per tool call (linked to the audit log by action_id); JSONL export; p50/p95 and tool success-rate summary CLI. No log text in spans. |
| v0.8 Security suite | **Done** | `pytest -m security` (80 tests, its own CI step): shared injection/traversal/secret fixtures; graph-level tests for secret leakage, injection via the log and via the model's answer, hostile run metadata, oversized logs, malformed approvals. Size limit added to `graph.start()`. Threat model in `docs/security.md`. |
| v0.9 Polish | **Done** | README rewritten to match exactly what shipped (it previously claimed a LoRA-tuned classifier in the architecture); the new usage examples were executed and work. |
| v1.0 | Not started, as instructed | Needs you looking at a running system. |

## Commits (in order)

| Commit | Message | CI |
|---|---|---|
| `92b1583` | feat: add the MCP Action Agent with ticket, notify and log lookup tools (v0.3) | ✅ |
| `bcc1813` | feat: wire the four agents into a checkpointed LangGraph graph with a human-approval interrupt (v0.4) | ✅ |
| `bcad6d1` | data: freeze draft risk labels and synthetic training examples for v0.5 | (pushed with next) |
| `ba00413` | experiment: LoRA risk classifier vs prompted LLM on held-out logs (v0.5) | ✅ |
| `5abcf8a` | experiment: trajectory evaluation of the full agent graph with an LLM judge and negative control (v0.6) | (pushed with v0.8) |
| `9056fed` | feat: trace per-stage latency and tool-call outcomes linked to the audit log (v0.7) | (pushed with v0.8) |
| `1ce6596` | test: security suite across the whole graph with a threat model (v0.8) | ✅ |
| `730b486` | docs: polish README and status docs to match exactly what shipped (v0.9) | ✅ |

"(pushed with …)" means GitHub ran CI only on the last commit of that push,
so those commits were not CI-tested on their own. I did test v0.7 alone
locally (below); v0.6 was not run as an isolated snapshot.

## Test results (as actually run)

| When | Result |
|---|---|
| v0.3 | full suite 262 passed, 4 skipped; mypy clean (33 files); CI ✅ |
| v0.4 | full suite 292 passed, 4 skipped; mypy clean (38 files); CI ✅. A real-model run on 3 held-out logs also completed end to end |
| v0.5 | new data/metric tests 5 passed (the full suite was not rerun just before this commit); CI ✅ on the commit |
| v0.6 | new scoring tests 3 passed |
| v0.7 snapshot | 305 passed, 4 skipped (v0.8 tests excluded); mypy clean (40 files) |
| v0.8 | **One full run showed 3 failed + 2 errors.** It was piped through `tail`, so the commit went ahead anyway: my mistake. I did not capture which tests failed. Four further full runs: 331 passed, 4 skipped each; CI on the commit ✅. The likeliest cause is the memory pressure that hit this machine all night (OpenBLAS allocation failures), but that is unproven. Since then I check pytest's real exit code before committing. |
| v0.9 / final | 331 passed, 4 skipped (pytest exit 0); security suite 80 passed; ruff and mypy clean; CI ✅ on `730b486` |

The 4 skipped tests are the Neo4j graph-store tests. Docker is not running
locally; they run in CI against a Neo4j service.

## NEEDS_DECISION.md (copied)

1. **Real ticket/notification backends.** Built with local files under
   `var/` (dry-run by default). Options: GitHub Issues (fits dogfooding),
   Jira, Slack/Teams/email for notify, or local-only for the demo. Needs your
   choice and permission to use a token.
2. **Draft risk rubric.** high = can't build/install/ship (compile,
   dependencies, OOM, release/publish/deploy workflows); medium = tests,
   types, timeouts, CI config; low = lint/format, docs, repo policy,
   network blips. It drives the classifier prompt, the fallback and the v0.5
   labels. Accept or edit.
3. **Which risk classifier the graph uses.** The prompted LLM (current
   default, high-risk recall 0.00), the rubric on the retrieved category
   (accuracy 0.609, inherits retrieval errors), or LoRA (macro-F1 0.50–0.57,
   gain not proven). Not changed tonight, because the labels are drafts.

## Deviations from the overnight brief (and why)

- **Tracing location.** It lives in `app/observability/tracing.py`, not a
  top-level `observability/`. The app already had that package (request IDs,
  logging), so one place for both.
- **v0.6 is a separate script.** `evaluation/run_trajectory_eval.py`, rather
  than extending `run_eval.py`, so the v0.2 baseline stays reproducible
  unchanged.
- **No RAGAS library.** Its metrics need an LLM judge, and the measured
  judge is unreliable (8/20 controls caught). Adding it would have produced
  numbers I could not stand behind.
- **`app/graph.py` was created.** The brief referred to it, but it did not
  exist; it now holds `ProposedAction`, `PipelineMedicState` and the other
  schemas.
- **No code execution of any kind.** The brief mentioned "sandboxed test runs
  already in the repo"; there are none, and nothing new executes code.

## Things I did to this machine

- **Ollama.** I stopped the Ollama app and server (which my own `ollama list`
  had started at 21:39) to free 4 GB for LoRA training. I later ran
  `ollama serve` for the prompted-LLM runs, and stopped it at the end.
  Start Ollama as you normally do.
- **Docker / Neo4j** are still stopped, as they were since earlier in the
  evening.
- **Runtime files** go to `var/` (gitignored); LoRA adapters to
  `ml/lora_finetune/artifacts/` (gitignored, rebuilt by the training script).
- **LoRA seed 0** was trained in a run I had to stop: I had given it a
  30-minute cap it could not meet. Its adapter was reused, so seed 0 has no
  recorded training time. Seeds 1 and 2 took about 12 minutes each.

## Single highest-value next step

**Review the 72 draft held-out labels**
(https://claude.ai/artifact/A2RJM7mk6psjgwWXi2adyz → Copy CSV → paste to
Claude Code). They underlie v0.2.5's final number and every v0.5 and v0.6
result. Once reviewed, decisions #2 and #3 can be made on solid numbers. The
engineering target after that is clear from v0.6: diagnosis is the first
error in 48 of 72 runs, so retrieval and category quality is where the next
gain is.
