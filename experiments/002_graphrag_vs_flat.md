# 002: Knowledge graph (GraphRAG) vs flat RAG (v0.2.5)

**Status:** final. Held-out labels reviewed on 2026-10-23 (accepted as drafted,
no changes); a re-run on the final labels gave identical numbers.
**Result file:** `evaluation/results/v0.2.5_graphrag_vs_flat.json`
**Reproduce:** `python -m evaluation.run_graph_eval` (needs Neo4j), or run the
"Retrieval eval" workflow in GitHub Actions. First measured in
[run 39660789178](https://github.com/SreyaThota/pipeline-medic/actions/runs/39660789178)
and re-run on the final labels in
[run 39942180961](https://github.com/SreyaThota/pipeline-medic/actions/runs/39942180961).

## Question

Does a knowledge graph of CI failures retrieve past failures of the same kind
better than v0.2's flat vector search, on logs it was not designed against?

## Setup

- **Task and metric:** same as experiment 001. Each log is a leave-one-out
  query, and a hit is a returned log with the same failure category. The
  primary number is cross-repo MRR, with the query's own repo excluded.
- **Graph:** rule-based entities (tools, error signatures, packages, exit
  codes) in Neo4j. A past run scores by the rarity-weighted entities it shares
  with the query. Schema: `docs/ontology.md`; design: `docs/decisions/001-neo4j-knowledge-graph.md`.
- **Methods:**
  - `flat`: the v0.2 baseline, vector search over each log's last 15 lines
  - `graph`: shared-entity score only
  - `graph_multihop`: plus a 4-hop expansion through co-occurring entities
  - `hybrid_rrf`: flat and graph combined by reciprocal rank fusion
  - `hybrid`: graph score first, with vector similarity breaking ties
  - `hybrid_multihop`: hybrid with the multi-hop expansion
- **Dev/test split:**
  - **dev:** the 51 original logs. The extraction rules, the fusion method and
    the multi-hop weight were all chosen here.
  - **test:** 72 logs from 20 repos, collected afterwards. The rules were
    committed (`f31d884`) and pushed before any test log was read. The method
    to compare was fixed on dev before the test run: `hybrid`.
- **Excluded:** logs whose text holds no cause, which no retriever can match.
  That is 4 + 3 `aggregate_gate` logs (gate jobs) and 5 `unknown` logs (cause
  cut off by the 400-line limit, or never printed). 64 test queries remain,
  searched against all 111 scoreable logs.

## Results

**Dev** (46 queries over 47 logs, chance@1 0.15). This is where the choices
were made, so it flatters the graph.

| Method | Cross R@1 | Cross MRR | Same-repo R@1 | Same-repo MRR |
|---|---|---|---|---|
| flat | 0.413 | 0.496 | 0.674 | 0.703 |
| graph | 0.500 | 0.559 | 0.739 | 0.772 |
| graph_multihop | 0.326 | 0.451 | 0.696 | 0.757 |
| hybrid_rrf | 0.435 | 0.527 | 0.652 | 0.707 |
| **hybrid** (selected) | **0.565** | **0.641** | 0.761 | 0.806 |
| hybrid_multihop | 0.370 | 0.505 | 0.717 | 0.786 |

**Held-out test** (64 queries over 111 logs, chance@1 0.164).

| Method | Cross R@1 | Cross MRR | Same-repo R@1 | Same-repo MRR | p50 latency* |
|---|---|---|---|---|---|
| flat | 0.375 | 0.477 | 0.500 | 0.589 | 52 ms |
| graph | 0.453 | 0.556 | 0.594 | 0.648 | 42 ms |
| graph_multihop | 0.328 | 0.419 | 0.422 | 0.490 | 20 ms |
| hybrid_rrf | 0.453 | 0.552 | 0.531 | 0.623 | 78 ms |
| **hybrid** (selected) | 0.375 | **0.504** | 0.656 | 0.709 | 84 ms |
| hybrid_multihop | 0.328 | 0.419 | 0.422 | 0.490 | 114 ms |

\*Measured on a GitHub Actions runner.

**Difference in cross-repo MRR against flat on the test logs** (paired
bootstrap, 10,000 resamples):

| Method | Mean difference | 95% interval | Queries better / worse / equal |
|---|---|---|---|
| **hybrid** (selected) | **+0.028** | **-0.088 to +0.146** | 17 / 18 / 29 |
| graph | +0.079 | -0.064 to +0.219 | 23 / 21 / 20 |
| hybrid_rrf | +0.076 | -0.023 to +0.172 | 21 / 11 / 32 |
| graph_multihop | -0.058 | -0.187 to +0.067 | 17 / 22 / 25 |

## Findings

1. **The pre-selected method shows no proven gain.** `hybrid` led on dev by
   +0.145 MRR. On held-out logs the lead fell to +0.028, and the interval
   includes zero. Most of the dev gain came from fitting the rules and the
   fusion choice to logs that had been read while designing them.
2. **Graph-only and RRF look better on test, but that is not evidence.**
   Picking them now would mean choosing the method on the test set. Their
   intervals include zero too. They are the candidates for the next held-out
   round, not the result of this one.
3. **The graph helps most on same-repo retrieval.** `hybrid` reaches
   same-repo MRR 0.709 against flat's 0.589. That is the "have we seen this
   failure in this repo before?" case. It is also where shared boilerplate
   inflates every method, so it is not the headline metric.
4. **Multi-hop expansion hurts, consistently.** It was worse on dev at every
   weight tried, and worse again on test (-0.058). Going through co-occurring
   entities pulls in generic matches such as exit code 1 or common tools.
5. **Flat RAG also dropped on new repos:** 0.496 on dev, 0.477 on test. The
   test set has 11 repos that never appeared in dev, so it is harder for every
   method, not only the graph.

## Caveats

- **One labeller.** The test labels were drafted after the rules were frozen,
  but with knowledge of them, and then accepted unchanged in review. There
  is no second, independent labeller.
- **Small sample.** With 64 queries, a difference smaller than about 0.1 MRR
  cannot be told apart from noise.
- **One labelling scheme.** "Same category" is coarse. A retriever could find
  the genuinely identical past failure and still be scored the same as one
  that found any test failure.

## Decision

**GraphRAG does not replace flat RAG.** Per `CLAUDE.md`, an upgrade ships only
once its gain is proven, and this one is not. Flat vector search stays the
default retriever. The graph, the extraction rules and the hybrid remain in
the repo, tested and measured, because later phases need graph queries for
other reasons (see the ADR).

**Next held-out round:** compare `graph` and `hybrid_rrf` against flat on
fresh logs collected after this commit, with labels reviewed before the run.
