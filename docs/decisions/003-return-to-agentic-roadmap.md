# 003: Return to the agentic roadmap, keep the brief's safety rules

**Status:** accepted, supersedes 002
**Date:** 2026-10-21

## Context

ADR 002 adopted the PipelineMedic X build brief as the roadmap, and its first
two phases were built the same day (API foundation, log parsing, secret
redaction). On review, I decided the agentic architecture (LangGraph
orchestration, MCP tools, a LoRA classifier) is the story the project is
built to tell, and that the brief's larger proposals (patch application with
sandboxed verification, Jira/PR integrations, an incident UI, a 20-chapter
handbook) are more scope than the project needs.

## Decision

- The design brief (now `docs/DESIGN.md`) returns to the agentic roadmap:
  v0.3 is an MCP Action Agent
  limited to ticket creation and notification.
- The brief's security baseline (redact before any model call or storage,
  treat logs and model output as untrusted, audit every tool call) and its
  evaluation rigor are kept as standing rules (`docs/DESIGN.md` §3 and §4).
- The work already built under the brief is kept as **v0.2.6**: it fits this
  architecture, and the redaction implements the safety rules.
- Patch drafting, patch application and sandboxed execution stay out of
  scope (`docs/DESIGN.md` §5) unless explicitly re-decided.

## Consequences

- The app is named Pipeline Medic again (API title, README); the code and
  endpoints do not change.
- `ROADMAP.md` tracks the versions. The handbook in
  `docs/notion_import/` keeps its two accurate chapters; the rest is a
  v1.0+ stretch.
- ADR 002 is superseded but kept as history.
