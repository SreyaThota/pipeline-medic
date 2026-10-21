# Security model (v0.8)

Pipeline Medic reads untrusted text (CI logs written by any code that ran in
a pipeline), sends some of it to a model, and can open tickets and send
notifications. This page lists what could go wrong, what stops it, and the
test that proves the control works.

Run the whole suite with `python -m pytest -m security` (80 tests). CI runs
it as its own step.

## Trust boundaries

```
untrusted                       │ deterministic code (trusted)        │ side effects
────────────────────────────────┼─────────────────────────────────────┼──────────────
CI log text                     │ redaction → parser → retrieval      │
model answers (llama3.2)        │ strict JSON parsing, enum only      │
run metadata (source_log_id)    │ pattern + index allowlist           │
approval payloads               │ Approval schema                     │
                                │ Action policy (fixed table)         │ ticket / notify
                                │   ⏸ human approval (interrupt)     │ (dry-run unless
                                │   ACTIONS_ENABLED gate              │  approved + enabled)
```

The model never chooses a tool, a channel or a file. It contributes one
value, the risk level, from a fixed set.

## Threats, controls, tests

| Threat | Control | Tests |
|---|---|---|
| Secret in a log is stored or sent to a model | Redaction before parsing, before the prompt, before tickets, audit and traces; checkpoints only ever hold redacted text | `test_redaction.py`, `test_graph_security.py::test_secrets_never_reach_state_proposals_tickets_audit_or_traces` |
| Prompt injection in a log changes what the agent does | Tool choice and channel come from a fixed policy over category and risk, never from log text; evidence is quoted and labelled untrusted | `test_tool_guardrails.py::test_prompt_injection_...`, `test_graph_security.py::test_injection_in_the_log_...` (5 injection fixtures each) |
| Injected instructions in the model's answer | Only the `risk` value is read, and only if it is low/medium/high; everything else is ignored or counts as invalid | `test_risk_classifier.py::test_answers_are_parsed_strictly`, `test_graph_security.py::test_injected_instructions_in_the_model_answer_...` |
| Path traversal to read or reference a file | log_id must match a strict pattern and appear in `index.csv`; the resolved path must stay inside the log directory | `test_tool_guardrails.py::test_path_traversal_in_log_id_is_rejected`, `test_graph_security.py::test_hostile_source_log_id_...` (8 fixtures each) |
| Notification to an arbitrary destination | Channel must exactly match the `NOTIFY_CHANNELS` allowlist | `test_tool_guardrails.py::test_notify_channel_must_match_the_allowlist_exactly` |
| Malformed or oversized tool input | Pydantic schemas with length limits, no extra fields, no control characters; a 20,000-character cap on the whole call; refusals are audited, never raised | `test_tool_guardrails.py::test_malformed_ticket_input_is_rejected`, `::test_oversized_payload_...` |
| Oversized log exhausting memory | `MAX_LOG_CHARS` checked by the API and by `graph.start()` before anything runs; long lines clipped | `test_graph_security.py::test_oversized_log_...`, API tests |
| Action without human consent | `interrupt()` before execution; no tool runs until `resume()` with a valid `Approval`; real actions additionally need `ACTIONS_ENABLED` | `test_graph_security.py::test_nothing_executes_until_approval`, `::test_malformed_approval_...`, `test_graph_orchestrator.py` |
| Untraceable action | Every tool call writes `proposed` then an outcome to the audit log; tracing spans carry the same action_id and never log text | `test_mcp_tools.py`, `test_observability.py` |

## Known limits

- **Redaction is pattern-based.** A secret with no recognisable shape is
  missed (see `docs/notion_import/04-log-parsing-and-redaction.md`).
- **No authentication on the HTTP API.** It is meant for localhost. Exposing
  it beyond that needs authentication first.
- **Local backends only.** Tickets and notifications go to files under
  `var/`. Choosing and securing a real backend is NEEDS_DECISION.md #1.
- **In-memory checkpoints.** A paused run is lost if the process restarts.
  Durable checkpoints would need a storage decision.
- **Corrupted resume.** A `None` resume payload is refused by LangGraph
  itself rather than by our schema; the run stays paused either way (tested).
