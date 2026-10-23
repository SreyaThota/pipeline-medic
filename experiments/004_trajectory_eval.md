# 004: Trajectory evaluation of the full agent graph (v0.6)

**Status:** final. Category labels reviewed on 2026-10-23 (accepted as drafted,
no changes); risk from rubric v1. The rule-based run was repeated on the final
labels with identical results; the LLM run was not repeated, because its
inputs and labels did not change.
**Result files:** `evaluation/results/v0.6_trajectory_rules.json`,
`evaluation/results/v0.6_trajectory_prompted.json` (one entry per run, with
every stage check, plus the judge verdicts).
**Reproduce:** `python -m evaluation.run_trajectory_eval --risk rules`;
`python -m evaluation.run_trajectory_eval --risk prompted --judge 20` (needs Ollama).

## Question

When the whole v0.4 graph runs on held-out failures, how often does it take
the right path end to end, and which stage goes wrong first?

## Setup

- **Logs:** all 72 held-out logs, including 8 whose text holds no cause
  (gate jobs, cut-off logs). For those, the right path is "uncertain → route
  to human triage".
- **Knowledge base:** flat-RAG retrieval over the 47 reviewed dev logs only.
- **Two risk stages:** the rubric on the predicted category (no LLM), and
  the graph's default prompted llama3.2.
- **Stage checks per run:**
  - parse: evidence was found
  - diagnose: category matches the label (or the run is uncertain, for
    no-cause logs)
  - grounded: every cited line exists in the log with exactly that text
  - risk: matches the risk label
  - action: the proposed tools equal the policy applied to the *true*
    category and risk
  - safety: no tool ran before approval; the run paused if and only if it
    proposed actions; no secret-bearing line appears in the stored state
- **LLM-as-judge:** llama3.2 was asked whether 20 tickets are supported by
  their quoted evidence. Each ticket also had a **negative control**: the
  same ticket with one fabricated root-cause sentence added.

## Results

| | Rubric (no LLM) | Prompted llama3.2 |
|---|---|---|
| parse | 1.00 | 1.00 |
| diagnose | 0.333 | 0.333 |
| grounded (evidence cites real lines) | 1.00 | 1.00 |
| risk | 0.653 | 0.514 |
| action | 0.403 | 0.306 |
| safety | 1.00 | 1.00 |
| **Whole trajectory correct** | **0.278** | 0.111 |
| No-cause logs routed to triage | 1/8 | 1/8 |
| Seconds per run (p50) | 0.22 | 6.56 |

**First stage that went wrong (72 runs):**

| | Rubric | Prompted |
|---|---|---|
| diagnose | 48 | 48 |
| risk | 0 | 13 |
| action | 4 | 3 |
| none (fully correct) | 20 | 8 |

**LLM-as-judge on 20 tickets:**
- Judged "supported": 15/20.
- Fabricated claim caught in the negative control: **8/20**.

## Findings

1. **Diagnosis is the bottleneck.** The predicted category is wrong in two
   thirds of runs, and that is the first error in 48 of 72. Better retrieval
   or a better category model is the highest-value next step; nothing
   downstream can recover from a wrong category.
2. **The LLM risk stage makes the pipeline worse.** With the rubric, 28% of
   trajectories are fully right; with llama3.2, 11%. It is also 30 times
   slower. This agrees with experiment 003.
3. **Safety and grounding hold in every run.** No tool ran before approval,
   no secret line reached the state, and every cited evidence line is real.
   These are properties of the deterministic code, not of a model.
4. **Uncertain logs are rarely routed to a human.** Only 1 of the 8 no-cause
   logs was marked uncertain: the retrieval vote is confidently wrong on gate
   jobs. A confidence threshold that understands "no cause in the log" is
   missing.
5. **The LLM judge cannot be trusted with this model.** It caught a
   fabricated root cause in only 8 of 20 controls. Its "15/20 supported" says
   little, because it would pass most fabrications too. RAGAS-style
   faithfulness needs a stronger judge, or human review; that is a stretch
   goal, not tonight's result.

## Notes

- `evaluation/run_eval.py` (the v0.2 retrieval baseline) is unchanged so its
  numbers stay reproducible. Trajectory evaluation is a separate script.
- The RAGAS library itself was not added: its metrics need an LLM judge, and
  finding 5 shows the local judge is not good enough to make them meaningful.
