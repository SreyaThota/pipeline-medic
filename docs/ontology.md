# Knowledge-graph ontology (v0.2.5)

The graph describes failed CI runs and the things they have in common. It is
built by `rag/graph.py` from entities extracted by the rules in
`rag/entities.py`. Every node also has an `ns` (namespace) property so test
and evaluation graphs can share the one database Neo4j Community provides.

```
(:Run)-[:IN_REPO]---------->(:Repo)
(:Run)-[:USED_TOOL]-------->(:Tool:Entity)
(:Run)-[:RAISED]----------->(:ErrorSignature:Entity)
(:Run)-[:MENTIONS_PACKAGE]->(:Package:Entity)
(:Run)-[:EXITED_WITH]------>(:ExitCode:Entity)
```

## Nodes

| Label | Key | Meaning | Example |
|---|---|---|---|
| `Run` | `log_id` | One failed GitHub Actions run. Carries `repo` and `label` (the failure category), which is returned with results but never used for matching. | `astral-sh__ruff__33831722570` |
| `Repo` | `name` | The repository the run belongs to. | `astral-sh/ruff` |
| `Tool` | `tool:<name>` | A program that was running when the job failed. It counts only if invoked or recognised by its output, not when its name appears in a path. | `tool:pytest`, `tool:cargo` |
| `ErrorSignature` | `error:<name>` | What kind of thing went wrong: a named rule (see below), a language exception name, or a rustc error code. | `error:tests_failed`, `error:ModuleNotFoundError`, `error:rustc_E0277` |
| `Package` | `package:<name>` | A dependency named in an error message. | `package:hypothesis` |
| `ExitCode` | `exit_code:<n>` | The process exit status. | `exit_code:127` |

`Tool`, `ErrorSignature`, `Package` and `ExitCode` nodes also carry the
`:Entity` label and a `key` property, so a query can match any of them.

## Error-signature rules

Grouped by what they detect. Each is a set of regular expressions in
`rag/entities.py`.

| Group | Signatures |
|---|---|
| Tests | `tests_failed`, `test_collection_error`, `snapshot_mismatch`, `assertion_failed`, `regression_detected` |
| Build | `compile_failed`, `bundle_failed`, `package_build_failed` |
| Code quality | `type_errors`, `format_diff`, `lint_errors`, `hook_failed` |
| Dependencies | `no_matching_distribution`, `module_not_found`, `lockfile_out_of_date`, `missing_export` |
| Infrastructure | `network_error`, `rate_limited`, `step_timeout`, `out_of_memory`, `disk_full` |
| CI configuration | `command_not_found`, `action_not_found`, `workflow_invalid`, `artifact_missing`, `file_not_found`, `permission_denied` |
| Repository policy | `changelog_required`, `restricted_change` |
| Docs | `docs_problem` |
| Gate jobs | `gate_job` |

## Queries

**Direct (2 hops):** query entities ← candidate run. A candidate scores the
sum of `log(1 + N / df)` over the entities it shares with the query, where
`df` is how many runs have that entity. A rare signature counts far more than
`exit_code:1`, which almost every run has.

**Multi-hop expansion (4 hops):** query entity ← bridge run → other entity ←
candidate. This lets a candidate that shares nothing directly score through
entities that co-occur with the query's entities. Measured on the dev logs it
made retrieval worse at every weight tried, so it is off by default
(`expand_weight=0`). See `experiments/002_graphrag_vs_flat.md`.

## Example Cypher

Runs that failed with the same rustc error as a given run, in other repos:

```cypher
MATCH (q:Run {ns: "main", log_id: $id})-[:RAISED]->(e:ErrorSignature)
      <-[:RAISED]-(other:Run)
WHERE e.key STARTS WITH "error:rustc_" AND other.repo <> q.repo
RETURN e.name, other.log_id, other.repo
```

Most common error signatures per tool:

```cypher
MATCH (t:Tool {ns: "main"})<-[:USED_TOOL]-(r:Run)-[:RAISED]->(e:ErrorSignature)
RETURN t.name AS tool, e.name AS error, count(r) AS runs
ORDER BY runs DESC LIMIT 20
```
