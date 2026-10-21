# data/

- `collect_ci_logs.py`: collects failed GitHub Actions run logs into
  `sample_logs/`, from this repo (dogfood) and public open-source repos.
  Requires an authenticated `gh`. Safe to re-run.
- `sample_logs/`: the collected real logs, `index.csv` and the failure-category
  taxonomy.
- `fixtures/`: small hand-written **synthetic** logs (GitHub Actions, Jenkins,
  plain text) for parser and API tests. Never mixed into real-log metrics.

Status:
- **Shipped:** CI log collection (v0.2); synthetic parser fixtures (v0.2.6).
