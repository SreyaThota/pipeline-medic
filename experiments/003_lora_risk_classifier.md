# 003: LoRA risk classifier vs prompted LLM (v0.5)

**Status:** final. Category labels reviewed on 2026-10-23 (accepted as drafted,
no changes); risk labels use rubric v1. Re-scored on the final labels with
identical results. LoRA not adopted: see Decision.
**Result files:** `evaluation/results/v0.5_risk_classifier.json` (metrics,
versions), `evaluation/results/v0.5_risk_predictions.json` (every prediction).
**Reproduce:** `python -m evaluation.run_risk_eval --stage lora`, then
`--stage prompted` (needs Ollama), then `--stage report`.

## Question

Does a small LoRA-fine-tuned model classify CI-failure risk (low / medium /
high) better than the graph's current prompted-LLM classifier, on logs from
repositories it never saw?

## Setup

- **Labels.** Frozen in commit `bcad6d1` before any training or scoring:
  rubric v1 (`agents/risk_rubric.py`) applied to each log's reviewed failure
  category and workflow name.
- **Train:** 47 dev logs (reviewed categories) + 30 synthetic examples
  (training only, labelled synthetic).
- **Test:** 64 held-out logs. 52 of them come from repos that never appear in
  training, reported separately as "unseen repos".
- **LoRA:**
  - Model: `all-MiniLM-L6-v2` (22.8M parameters) with rank-8 LoRA on the
    attention query/value matrices plus a new 3-way head. That is 74,883
    trainable parameters (0.33%).
  - Input: "workflow: <name>" plus the log's last 15 parsed lines,
    truncated from the left at 256 tokens.
  - Training: 20 epochs, batch 8, learning rate 1e-3, class-weighted loss.
    All fixed in advance, nothing tuned on test.
  - 3 seeds; about 12 minutes of training per seed on a laptop CPU.
- **Prompted LLM:** exactly what the v0.4 graph runs. The flat-RAG diagnosis
  (knowledge base = dev logs only) feeds a llama3.2 prompt containing the
  rubric, the predicted category and the evidence lines, with strict JSON
  parsing.
- **Rubric on retrieved category:** the rubric applied to the
  retrieval-predicted category, with no model. A reference point.
- **Majority class:** always "medium".

## Results

**All 64 held-out logs**

| System | Accuracy | Macro-F1 | Recall high / medium / low |
|---|---|---|---|
| LoRA seed 0 | 0.531 | 0.498 | 0.58 / 0.68 / 0.29 |
| LoRA seed 1 | 0.594 | 0.571 | 0.58 / 0.68 / 0.48 |
| LoRA seed 2 | 0.516 | 0.500 | 0.58 / 0.58 / 0.38 |
| Prompted llama3.2 | 0.500 | 0.365 | **0.00** / 0.61 / 0.62 |
| Rubric on retrieved category | **0.609** | 0.544 | 0.67 / 0.87 / 0.19 |
| Majority class ("medium") | 0.484 | 0.218 | 0.00 / 1.00 / 0.00 |

**The 52 logs from unseen repos**

| System | Accuracy | Macro-F1 |
|---|---|---|
| LoRA, 3 seeds | 0.481–0.577 | 0.457–0.547 |
| Prompted llama3.2 | 0.481 | 0.351 |
| Rubric on retrieved category | 0.558 | 0.490 |
| Majority class | 0.462 | 0.211 |

**LoRA (mean over seeds) minus prompted LLM, accuracy, paired bootstrap:**

| Set | Difference | 95% interval |
|---|---|---|
| All 64 logs | +0.047 | -0.125 to +0.214 |
| Unseen repos | +0.038 | -0.147 to +0.224 |

**Latency:** LoRA 70–130 ms per log; prompted LLM about 6.8 s (p50).

## Findings

1. **LoRA's accuracy advantage over the prompted LLM is not proven.** The
   interval includes zero on both test sets.
2. **The prompted LLM never predicts "high".** All 12 high-risk failures came
   out medium (6) or low (6), although the rubric in its prompt names them.
   For a risk classifier whose job is to escalate, this is the most important
   number here. LoRA catches 58% of them; macro-F1 is 0.50–0.57 for LoRA vs
   0.365 for the LLM.
3. **The simplest system has the best accuracy.** The rubric applied to the
   retrieved category beats both models. This is partly structural: the
   labels *are* the rubric applied to the true category, so this system is
   only wrong when retrieval picks the wrong category. It measures retrieval
   quality as much as risk classification.
4. **Seed variance is large.** LoRA accuracy ranges over 0.08 across three
   seeds. With 64 test logs, a single seed would be a misleading number.

## Caveats

- **Rubric-derived labels.** Risk labels come from rubric v1 applied to the
  category labels, not from independent human risk judgements. A different
  rubric would change every number.
- **Small training set:** 77 examples, 30 of them synthetic.
- **One small base model and one hyper-parameter setting.** Nothing was tuned,
  on purpose. This is not a ceiling.

## Decision

**LoRA is not adopted.** Its gain over the prompted LLM is not proven, and a
model-free rule does better on these labels.

The rule-based classifier (rubric v1 on the retrieved category) became the
graph's default risk stage in ADR 004: it has the best accuracy (0.609) and
high-risk recall (0.67), needs no model, and gave 2.5 times as many fully
correct trajectories as the prompted LLM in experiment 004. The prompted LLM
remains available as an option.
