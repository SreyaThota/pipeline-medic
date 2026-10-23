# 004: Local backends, rubric v1, and a rule-based risk classifier by default

**Status:** accepted
**Date:** 2026-10-23
**Resolves:** NEEDS_DECISION.md #1, #2 and #3

## Context

The overnight build (v0.3–v0.9) left three questions open. On 2026-10-23 the
72 held-out labels were reviewed and accepted as drafted, and v0.2.5, v0.5
and v0.6 were re-run on the final labels with identical results. The final
numbers are in experiments 002–004.

## Decisions

**1. Tickets and notifications stay local-file only.** `create_ticket`
writes to `var/tickets.jsonl` and `notify` to `var/outbox.jsonl`, dry-run by
default. No external service, no credentials. This keeps the safety story
simple: nothing the system does leaves the machine or is irreversible. An
external adapter (GitHub Issues, Slack) would need a new decision.

**2. The risk rubric is kept as v1, unchanged.** The final labels matched
the drafts exactly, so they surfaced no evidence against the rubric. Its
known weakness stays documented: risk is a function of category and workflow
name only, so it cannot tell a flaky test from a real regression.

**3. The rule-based classifier (rubric v1 on the retrieved category) is the
graph's default risk stage.** On the final labels it is the clear winner:

| Classifier | Accuracy | Macro-F1 | High-risk recall | Whole trajectories correct | Latency |
|---|---|---|---|---|---|
| **Rubric on retrieved category** | **0.609** | 0.544 | **0.67** | **27.8%** | ~0.3 s per run |
| LoRA MiniLM (3 seeds) | 0.52–0.59 | 0.50–0.57 | 0.58 | not run | 70–130 ms |
| Prompted llama3.2 | 0.500 | 0.365 | 0.00 | 11.1% | ~6.8 s |

It is also the simplest option: no model, deterministic, explainable in one
sentence. The prompted classifier stays available as
`PipelineMedicGraph.default(settings, risk="prompted")`. LoRA stays an
experiment.

## Consequences

- **The risk stage inherits every retrieval error.** Diagnosis is the first
  wrong stage in 48 of 72 runs (experiment 004), so improving retrieval is
  now the only way to improve risk accuracy.
- **Part of the rubric's lead is structural.** The labels are the rubric
  applied to the true category, so the rubric classifier is only wrong when
  retrieval picks the wrong category. The comparison with the LLM still
  stands: the LLM was given the same rubric and the same category and did
  worse, including missing every high-risk failure.
- **The graph needs no LLM at all by default.** Ollama is now optional at
  runtime (used only by `/v1/diagnose` and the opt-in prompted classifier).
