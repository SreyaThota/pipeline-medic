# 001: Knowledge graph in Neo4j, built with rule-based extraction

**Status:** accepted (v0.2.5)
**Date:** 2026-10-21

## Context

v0.2 shipped flat vector retrieval over the last 15 lines of each failed CI
log: cross-repo MRR 0.496 on 46 queries. Flat retrieval compares surface
text, so two logs from different ecosystems that fail for the same reason
(say, a missing module) only match if their wording happens to be similar.

The roadmap planned a knowledge graph for this, and three choices had to be
made:

1. **How entities are extracted.** Regular-expression rules or a local LLM.
2. **Where the graph lives.** Neo4j or an in-memory structure.
3. **How graph and vector results combine.**

## Decision

1. **Rule-based extraction** (`rag/entities.py`). Rules are deterministic,
   fast, testable in CI, and every graph edge traces back to the line that
   produced it. A local LLM on this laptop's CPU would be slow, could give
   different output run to run, and could invent entities. LLM extraction
   remains an option to measure later against these rules.
2. **Neo4j 5.26 Community in Docker** (`docker-compose.yml`).
3. **Graph-first fusion** (`rag/hybrid.py`): rank by graph score, use vector
   similarity to break ties and to rank what the graph did not match.
   Reciprocal rank fusion was also measured, and scored lower on the dev logs.

To keep the measurement honest, the logs are split in two. The rules and
every setting were chosen on the 51 original "dev" logs. The comparison that
counts is on 72 logs collected afterwards ("test"), and the rules were
committed before any of those logs were read.

## Consequences

- **Neo4j is not needed at this size.** At 123 runs the same scoring could be
  an inverted index in a Python dictionary. Neo4j earns its place later: the
  Action and Diagnosis agents (v0.3, v0.4) need to ask relationship questions
  ("which fix resolved this error signature in other repos?"), and Cypher
  keeps those queries inspectable. Until then it is an extra running service.
- **The rules need maintenance.** A new tool or error format needs a new
  pattern, and anything the patterns miss is invisible to the graph.
  Graph-first fusion limits the damage: a log with no extracted entities still
  gets vector results.
- **One more moving part in CI.** The workflow runs Neo4j as a service
  container, and the graph tests fail in CI rather than skip when it is
  unreachable.
- **Multi-hop expansion is built but off.** It made retrieval worse on the dev
  logs. The ability to ask multi-hop questions is still the reason for using
  a graph database, but the evidence does not support using it for this
  retrieval task.
