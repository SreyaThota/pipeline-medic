# data/sample_logs/

Failed GitHub Actions run logs (`gh run view --log-failed`, last 400 lines),
collected by `data/collect_ci_logs.py`.

- `dogfood/`: Pipeline Medic's own CI. Empty until its own CI fails.
- `oss/`: public open-source repos (ruff, black, fastapi, pydantic, pytest,
  poetry, prettier, httpx, home-assistant). Each row in `index.csv` links to
  the original run.
- `index.csv`: one row per log: source, repo, workflow, run URL, `label` and
  `label_status` (`draft` = not yet human-reviewed, `reviewed` = checked).

## Failure categories

| Label | Meaning |
|---|---|
| `test_failure` | A test, snapshot or regression check failed |
| `build_compile` | Compiling, bundling or packaging the project failed |
| `dependency_install` | Resolving or installing dependencies failed (missing package, stale lockfile) |
| `lint_format` | Linter or formatter rejected the code |
| `type_check` | mypy / pyright / tsc errors |
| `ci_config` | The workflow itself is broken: missing tool, script, action, artifact or runner label |
| `policy_check` | A repo rule blocked the change (changelog entry required, restricted dependency changes) |
| `docs_check` | Documentation build or link check failed |
| `infra_network` | Download failures, mirror timeouts, API rate limits |
| `timeout` | A step hit its time limit |
| `aggregate_gate` | Gate job that only reports that another job failed; no cause in the text. Excluded from retrieval eval. |
