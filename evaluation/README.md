# evaluation/

- `run_eval.py`: v0.2 retrieval baseline. It runs a leave-one-out test over
  the labelled logs in `data/sample_logs/index.csv` and reports recall@k, MRR,
  chance@1 and latency per chunking strategy, with and without same-repo
  neighbours. Run with `python -m evaluation.run_eval`, adding
  `--reviewed-only` to use only human-reviewed labels.
- `results/`: JSON output of each run.

Status:
- **Shipped:** retrieval baseline eval (v0.2).
- **Designed:** golden trajectory set (`benchmark.json`), RAGAS and
  LLM-as-judge (v0.6–v0.9).
