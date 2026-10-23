# evaluation/

- `run_eval.py`: v0.2 retrieval baseline. It runs a leave-one-out test over
  the labelled logs in `data/sample_logs/index.csv` and reports recall@k, MRR,
  chance@1 and latency per chunking strategy, with and without same-repo
  neighbours. Run with `python -m evaluation.run_eval`, adding
  `--reviewed-only` to use only human-reviewed labels, or `--split dev` for
  the 51 logs v0.2 was measured on.
- `run_graph_eval.py`: v0.2.5 comparison of flat, graph and hybrid
  retrieval. Settings are chosen on the dev logs, then the selected method is
  compared with flat on the held-out logs with a paired bootstrap interval.
  Needs Neo4j; also runs as the "Retrieval eval" workflow in GitHub Actions.
- `results/`: JSON output of each run.

Status:
- **Shipped:** retrieval baseline eval (v0.2).
- **Shipped:** graph vs flat comparison (v0.2.5), risk classifier comparison
  (v0.5, `run_risk_eval.py`), whole-graph trajectory evaluation with an
  LLM-as-judge and negative control (v0.6, `run_trajectory_eval.py`).
