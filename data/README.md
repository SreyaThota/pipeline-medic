# data/

- `collect_ci_logs.py`: collects failed GitHub Actions run logs into
  `sample_logs/`, from this repo (dogfood) and public open-source repos.
  Requires an authenticated `gh`. Safe to re-run.
- `sample_logs/`: the collected logs, `index.csv` and the failure-category
  taxonomy.

Status:
- **Shipped:** CI log collection (v0.2).
- **Designed:** LogHub samples and `synthetic_generator.py` for rare failure
  classes and labelled risk levels (v0.5).
