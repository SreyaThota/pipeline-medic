# 002: Adopt the PipelineMedic X roadmap

**Status:** superseded by 003 (same day)
**Date:** 2026-10-21

## Context

The original plan (`CLAUDE.md`, October 2026) was a four-agent pipeline:
LangGraph orchestration, MCP tools, a LoRA-tuned risk classifier and a Neo4j
knowledge graph. By v0.2.5 the project had shipped a measured retrieval
baseline and found that the knowledge graph gave no proven gain over flat
search on held-out logs.

The PipelineMedic X build brief proposes a different focus: evidence-backed
diagnosis, safe patch proposals with human approval, sandboxed verification,
an audit trail and reproducible evaluation, on a minimal stack.

## Decision

The brief's phased roadmap (`ROADMAP.md`) replaces the agent roadmap.

- **Dropped:** LangGraph, MCP and LoRA. An explicit state machine in plain
  Python covers the workflow, and nothing measured so far calls for a
  fine-tuned classifier. Any of them can come back with a concrete
  requirement and an experiment note.
- **Kept:** the v0.2 retrieval experiment and its numbers, the v0.2.5 graph
  experiment (as an optional, non-default retriever), the dataset and its
  dev/test split, and every working rule in `CLAUDE.md`.
- **Added:** SQLite for persistence, as it needs no server.

## Consequences

- Less infrastructure to run and explain; the interview story moves from
  "many components" to "safe, evaluated, auditable".
- The empty placeholder folders for the dropped components (`agents/`,
  `mcp_server/`, `ml/`, `dashboard/`, `observability/`,
  `rag/knowledge_base/`) are removed.
- The README and `CLAUDE.md` now describe PipelineMedic X, with the old
  versions kept as history.
