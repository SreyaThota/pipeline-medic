"""Export real graph runs and real experiment numbers for the static demo.

    python demo/build_demo_data.py

Writes `demo/public/runs.json` and `demo/public/metrics.json`. Nothing in
them is typed in by hand:

- runs.json: the default graph (flat-RAG diagnosis, rubric risk, no LLM) is
  run on five held-out logs, with the same knowledge base as the trajectory
  evaluation (`build_retriever(split="dev")`, so these logs were never in it).
  Each paused run is then approved as user "demo" and finished as a dry run;
  real actions are switched off in the settings.
- metrics.json: values read from `evaluation/results/*.json`. The script
  checks that each value, formatted as the README shows it, appears in
  README.md, so the demo and the README cannot drift apart.

Before writing, the exported runs are scanned for anything the redaction
rules would still catch, plus e-mail addresses; the script fails if any
are found.
"""

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.diagnosis_agent import build_retriever
from app.graph import Approval
from app.graph_orchestrator import PipelineMedicGraph
from app.ingestion.formats import PARSERS
from app.redaction import redact_lines
from demo.helpers import INDEX_CSV, demo_settings, stage_latency

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "demo" / "public"
RESULTS = ROOT / "evaluation" / "results"

# Held-out (split=test) runs from five repos and five failure categories.
# In the v0.6 trajectory evaluation the first four were diagnosed correctly
# and the last one was not; the export re-checks this against the live run.
RUN_IDS = [
    "tokio-rs__tokio__38134725610",          # build_compile, high risk
    "home-assistant__core__38223769150",     # ci_config, medium risk
    "python-poetry__poetry__38201401884",    # test_failure, medium risk
    "pytest-dev__pytest__38099531711",       # docs_check, low risk, no action
    "numpy__numpy__38197650837",             # dependency_install, misdiagnosed
]
EXCERPT_LINES = 25
MAX_WIDTH = 220
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def clip(text: str) -> str:
    return text if len(text) <= MAX_WIDTH else text[:MAX_WIDTH] + " …"


def excerpt_lines(total: int, evidence: list[int]) -> list[int]:
    """Line numbers around the evidence, at most EXCERPT_LINES of them.

    The last lines of a GitHub Actions log are usually runner clean-up, so
    the excerpt follows the evidence instead; with no evidence it is the tail."""
    if not evidence:
        return list(range(max(1, total - EXCERPT_LINES + 1), total + 1))
    for context in (2, 1, 0):
        wanted = sorted({n for e in evidence
                         for n in range(max(1, e - context), min(total, e + context) + 1)})
        if len(wanted) <= EXCERPT_LINES:
            return wanted
    return sorted(evidence)[:EXCERPT_LINES]


def export_run(graph: PipelineMedicGraph, row: dict[str, str]) -> dict[str, Any]:
    path = INDEX_CSV.parent / row["source"] / f"{row['log_id']}.log"
    original = path.read_text(encoding="utf-8", errors="replace")
    redactions = redact_lines(original.splitlines()).by_kind

    state = graph.start(original, source_log_id=row["log_id"], workflow=row["workflow"])
    parsed, diagnosis, risk = state["parsed"], state["diagnosis"], state["risk"]
    lines = [raw.text for raw in PARSERS[parsed.format](state["log_text"].splitlines())]
    evidence = [{"line": e.line, "text": clip(e.text)} for e in diagnosis.evidence]
    excerpt = excerpt_lines(len(lines), [e.line for e in diagnosis.evidence])

    final = state
    approval: dict[str, Any] = {"required": bool(state["proposed_actions"])}
    if graph.is_paused(state["run_id"]):
        final = graph.resume(state["run_id"], Approval(approved=True, approver="demo",
                                                         note="dry-run approval for the static demo"))
        approval.update(approver="demo", approved=True, run_status=final["status"])
        approval["results"] = [
            {"tool": r.tool, "status": r.status, "dry_run": r.dry_run, "proposal": r.proposal,
             "result": r.result, "error": r.error,
             "audit": [{"ts": e["ts"], "tool": e["tool"], "phase": e["phase"],
                        "action_id": e["action_id"][:8]}
                       for e in graph.actor.audit.entries(r.action_id)]}
            for r in final["action_results"]]
    else:
        approval["run_status"] = final["status"]

    latency = stage_latency(final["trace"])
    return {
        "log_id": row["log_id"], "repo": row["repo"], "workflow": row["workflow"],
        "run_url": row["run_url"], "label": row["label"], "split": row["split"],
        "format": parsed.format, "line_count": parsed.line_count,
        "redactions": redactions,
        "excerpt": [{"line": n, "text": clip(lines[n - 1])} for n in excerpt],
        "evidence": evidence,
        "similar": [s.model_dump() for s in diagnosis.similar[:3]],
        "diagnosis": {"category": diagnosis.category, "confidence": diagnosis.confidence,
                      "summary": diagnosis.summary, "method": diagnosis.method,
                      "correct": diagnosis.category == row["label"]},
        "risk": {"level": risk.level, "method": risk.method, "rationale": risk.rationale},
        "actions": [{"tool": a.tool, "reason": a.reason, "arguments": a.arguments}
                    for a in state["proposed_actions"]],
        "approval": approval,
        "latency_ms": {k: round(v, 1) for k, v in latency.items()},
    }


def check_no_secrets(runs: list[dict[str, Any]]) -> None:
    text = json.dumps(runs, ensure_ascii=False)
    leaks = redact_lines(text.splitlines()).by_kind
    emails = EMAIL.findall(text)
    if leaks or emails:
        raise SystemExit(f"refusing to write runs.json: secrets {leaks}, e-mails {emails}")


def load(name: str) -> Any:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def build_metrics() -> dict[str, Any]:
    flat = load("v0.2_flat_rag_baseline.json")
    graph_rag = load("v0.2.5_graphrag_vs_flat.json")
    risk = load("v0.5_risk_classifier.json")["subsets"]["all_test"]
    rules = load("v0.6_trajectory_rules.json")["summary"]
    prompted = load("v0.6_trajectory_prompted.json")["summary"]

    lora = [risk[f"lora_seed{i}"] for i in range(3)]
    stages = {"whole": "Whole log", "tail": "Last 15 lines", "window": "15-line windows"}
    methods = {"flat": "Flat (v0.2)", "hybrid": "Hybrid, chosen on dev",
               "graph": "Graph only", "graph_multihop": "Multi-hop graph"}
    diff = graph_rag["test_mrr_difference_vs_flat_cross_repo"]
    return {
        "sources": sorted(p.name for p in RESULTS.glob("*.json")),
        "retrieval": {
            "queries": flat["queries"], "chance_at_1": flat["chance@1"],
            "rows": [{"name": label, "recall_at_1": flat["strategies"][k]["cross_repo"]["recall@1"],
                      "mrr": flat["strategies"][k]["cross_repo"]["mrr"], "chosen": k == "tail"}
                     for k, label in stages.items()],
        },
        "graphrag": {
            "held_out_queries": graph_rag["test"]["queries"],
            "rows": [{"name": label,
                      "dev_mrr": graph_rag["dev"]["methods"][k]["cross_repo"]["mrr"],
                      "test_mrr": graph_rag["test"]["methods"][k]["cross_repo"]["mrr"],
                      "gain": None if k == "flat" else diff[k]}
                     for k, label in methods.items()],
        },
        "risk": {
            "n": risk["rubric_on_retrieved"]["n"],
            "rows": [
                {"name": "LoRA MiniLM (3 seeds)",
                 "accuracy": [min(r["accuracy"] for r in lora), max(r["accuracy"] for r in lora)],
                 "macro_f1": [min(r["macro_f1"] for r in lora), max(r["macro_f1"] for r in lora)],
                 "high_recall": [min(r["per_class"]["high"]["recall"] for r in lora),
                                 max(r["per_class"]["high"]["recall"] for r in lora)]},
                {"name": "Prompted llama3.2", "accuracy": risk["prompted_llm"]["accuracy"],
                 "macro_f1": risk["prompted_llm"]["macro_f1"],
                 "high_recall": risk["prompted_llm"]["per_class"]["high"]["recall"]},
                {"name": "Rubric on retrieved category (default)",
                 "accuracy": risk["rubric_on_retrieved"]["accuracy"],
                 "macro_f1": risk["rubric_on_retrieved"]["macro_f1"],
                 "high_recall": risk["rubric_on_retrieved"]["per_class"]["high"]["recall"],
                 "chosen": True},
            ],
            "lora_vs_prompted": risk["lora_mean_vs_prompted_accuracy"],
        },
        "trajectory": {
            "logs": rules["logs"],
            "rows": [
                {"name": "Fully correct trajectory", "rubric": rules["trajectory_correct"],
                 "prompted": prompted["trajectory_correct"]},
                {"name": "Diagnosis correct", "rubric": rules["stage_pass_rate"]["diagnose"],
                 "prompted": prompted["stage_pass_rate"]["diagnose"]},
                {"name": "Evidence cites real log lines", "rubric": rules["stage_pass_rate"]["grounded"],
                 "prompted": prompted["stage_pass_rate"]["grounded"]},
                {"name": "Safety invariants held", "rubric": rules["stage_pass_rate"]["safety"],
                 "prompted": prompted["stage_pass_rate"]["safety"]},
            ],
            "diagnosis_first_error": rules["first_error"]["diagnose"],
            "judge_controls_caught": prompted["llm_judge"]["negative_control_caught"],
        },
    }


def check_against_readme(m: dict[str, Any]) -> None:
    """Every number the demo shows must appear, formatted the same way, in the README."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    def f3(x: float) -> str:
        return f"{x:.3f}"

    def pct(x: float) -> str:
        return f"{x * 100:.1f}%"

    def signed(x: float) -> str:
        return f"{x:+.3f}".replace("+-", "-")

    expected = [f3(r[k]) for r in m["retrieval"]["rows"] for k in ("recall_at_1", "mrr")]
    for r in m["graphrag"]["rows"]:
        expected += [f3(r["dev_mrr"]), f3(r["test_mrr"])]
        if r["gain"]:
            g = r["gain"]
            expected.append(f"{signed(g['mean_difference'])} ({f3(g['ci95_low'])} to "
                            f"{signed(g['ci95_high'])})")
    lora, prompted, rubric = m["risk"]["rows"]
    expected += [f"{lora['accuracy'][0]:.2f}–{lora['accuracy'][1]:.2f}",
                 f"{lora['macro_f1'][0]:.2f}–{lora['macro_f1'][1]:.2f}",
                 f"{lora['high_recall'][0]:.2f}"]
    expected += [f3(prompted[k]) for k in ("accuracy", "macro_f1")]
    expected += [f3(rubric[k]) for k in ("accuracy", "macro_f1")] + [f"{rubric['high_recall']:.2f}"]
    for r in m["trajectory"]["rows"]:
        expected += [pct(r["rubric"]).replace("100.0%", "100%"),
                     pct(r["prompted"]).replace("100.0%", "100%")]
    expected += [f"{m['trajectory']['diagnosis_first_error']} of 72",
                 m["trajectory"]["judge_controls_caught"].replace("/", " of ")]
    missing = [e for e in expected if e not in readme]
    if missing:
        raise SystemExit(f"metrics do not match the README: {missing}")
    print(f"metrics: {len(expected)} values checked against README.md")


def main() -> None:
    with INDEX_CSV.open(newline="", encoding="utf-8") as f:
        rows = {row["log_id"]: row for row in csv.DictReader(f)}
    graph = PipelineMedicGraph.default(demo_settings(), retriever=build_retriever(split="dev"),
                                       risk="rubric")
    runs = []
    for log_id in RUN_IDS:
        row = rows[log_id]
        assert row["split"] == "test", f"{log_id} is not a held-out log"
        run = export_run(graph, row)
        runs.append(run)
        d, a = run["diagnosis"], run["approval"]
        print(f"{run['repo']:<22} {run['label']:<19} -> {d['category']!s:<19} "
              f"{'OK ' if d['correct'] else 'BAD'} risk={run['risk']['level']:<6} "
              f"actions={[x['tool'] for x in run['actions']]} "
              f"results={[(r['tool'], r['status']) for r in a.get('results', [])]} "
              f"redacted={run['redactions']} ms={sum(run['latency_ms'].values()):.0f}")
    check_no_secrets(runs)
    metrics = build_metrics()
    check_against_readme(metrics)

    OUT.mkdir(parents=True, exist_ok=True)
    meta = {"knowledge_base": "dev split only (the same as the v0.6 trajectory evaluation)",
            "risk": "rubric v1", "actions": "dry run; real actions disabled"}
    (OUT / "runs.json").write_text(json.dumps({"meta": meta, "runs": runs}, indent=1,
                                              ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT / 'runs.json'} and {OUT / 'metrics.json'}")


if __name__ == "__main__":
    main()
