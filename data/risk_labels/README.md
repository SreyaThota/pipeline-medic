# data/risk_labels/

Labels for the v0.5 risk-classifier experiment. **Frozen before any model
was trained or scored** (commit history shows this file set landing first).

- `risk_labels.csv`: 111 real CI logs. `risk_level` is the **draft rubric**
  (`agents/risk_rubric.py`, NEEDS_DECISION.md #2) applied to the log's
  failure-category label and workflow name. `category_status` says whether
  that category label was human-reviewed (`dev`, 47 logs) or is still a
  draft (`test`, 64 logs). Gate jobs and logs with no cause are excluded.
- `synthetic_train.jsonl`: 30 **synthetic**, hand-written failure tails (10
  per level). Used for training only, never in any reported test number.

Split: train on `dev` + synthetic, test on `test`. 52 of the 64 test logs
come from repositories that never appear in `dev`.
