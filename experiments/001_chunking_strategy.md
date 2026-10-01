# 001: Chunking strategy for the flat-RAG baseline (v0.2)

**Status:** final for v0.2. Labels reviewed (accepted as drafted, no changes).
**Result file:** `evaluation/results/v0.2_flat_rag_baseline.json`
**Reproduce:** `python -m evaluation.run_eval --reviewed-only`

## Question

A CI failure log is hundreds of lines, but `all-MiniLM-L6-v2` only reads the
first ~256 tokens of each input and silently drops the rest. How should a log
be cut into embedded chunks so that a new failure retrieves past failures of
the same kind?

## Setup

- **Corpus:** 51 real failed GitHub Actions runs from 9 public repos (ruff,
  black, fastapi, pydantic, pytest, poetry, prettier, httpx, home-assistant),
  collected with `data/collect_ci_logs.py`. Pipeline Medic's own CI has no
  failures yet, so there are no dogfooded logs in this run.
- **Labels:** one failure category per log (taxonomy in
  `data/sample_logs/README.md`). All 51 labels were drafted from the error
  lines and then reviewed; none were changed.
- **Excluded:** 4 `aggregate_gate` logs ("alls-green" jobs that only report
  that another job failed). Their text contains no cause, so they can't be
  matched. The single `timeout` log stays in the corpus as a distractor but
  is not used as a query. Result: 47 logs in the corpus, 46 queries.
- **Protocol:** leave-one-out. Each log queries all the others. A hit means
  a returned log has the same label. The query is always the last 15
  cleaned lines of the log.
- **Cleaning** (applies to all strategies): strip the gh prefix, timestamps
  and ANSI codes, and drop each job's "Post job cleanup." section.
- **Strategies:**
  - `whole`: whole log, one chunk (the model keeps only the start)
  - `tail`: last 15 lines, one chunk
  - `window`: 15-line windows, 5 lines of overlap; a log scores as its best chunk
- **Embeddings:** `all-MiniLM-L6-v2`, CPU, cosine distance in Chroma.

## Results

Chance@1 (picking a random other log) = **0.15**.

**Same-repo neighbours allowed:**

| Strategy | Chunks | Recall@1 | Recall@3 | Recall@5 | MRR | p50 latency |
|---|---|---|---|---|---|---|
| whole | 47 | 0.239 | 0.413 | 0.500 | 0.340 | 35 ms |
| **tail** | 47 | **0.674** | **0.717** | **0.761** | **0.703** | 45 ms |
| window | 1376 | 0.522 | 0.587 | 0.674 | 0.575 | 66 ms |

**Cross-repo (the query's own repo excluded):**

| Strategy | Recall@1 | Recall@3 | Recall@5 | MRR |
|---|---|---|---|---|
| whole | 0.217 | 0.413 | 0.435 | 0.312 |
| **tail** | **0.413** | **0.609** | **0.652** | **0.496** |
| window | 0.174 | 0.348 | 0.478 | 0.282 |

## Findings

1. **`tail` wins on every metric.** The error almost always sits at the end
   of a failed job. `whole` mostly embeds runner setup, so it is barely above
   chance.
2. **`window` is worse than the simpler `tail`, and drops to about chance
   cross-repo.** With max-aggregation, any log can win through a chunk of
   generic boilerplate (`actions/checkout`, `setup-python`, env dumps) that
   closely matches the query. More chunks give more chances for a false
   match. A more complex strategy didn't earn its place.
3. **Same-repo matches inflate the scores.** `tail` falls from MRR 0.703 to
   0.496 once same-repo logs are excluded. Part of the same-repo score comes
   from shared repo boilerplate, not the failure itself. The cross-repo
   number is the honest one for "have we seen this kind of failure before".
4. **Cleaning mattered before any chunking choice.** Before "Post job cleanup."
   sections were stripped, most log tails were identical git/docker teardown
   lines.

## Caveats

- **Small sample.** With n = 46, recall@1 has a 95% interval of roughly
  ±0.14. Treat `tail` > `whole` as solid and `tail` vs `window` as directional.
- **Single labeller.** One person reviewed the labels, and a few are
  judgment calls (e.g. a native build failure during dependency install was
  labelled `build_compile`). There is no inter-annotator agreement figure.
- **Only one model and one window size** (15 lines) were tested.

## Decision

`tail` (15 lines) is the v0.2 default in `rag/ingest.py`. The number any
v0.2.5 GraphRAG upgrade must beat is the **cross-repo `tail` MRR, 0.496**
(recall@1 0.413).
