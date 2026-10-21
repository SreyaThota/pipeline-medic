"""v0.5: LoRA risk classifier vs the prompted-LLM classifier, on held-out logs.

Run in stages so only one model is in memory at a time:

    python -m evaluation.run_risk_eval --stage lora       # train 3 seeds, predict test
    python -m evaluation.run_risk_eval --stage prompted   # llama3.2 via Ollama, as in the graph
    python -m evaluation.run_risk_eval --stage report     # metrics + paired bootstrap

Labels are frozen in data/risk_labels/ (draft rubric applied to the category
labels). Train = dev split + synthetic examples; test = the held-out split.
Raw predictions, configuration and versions are saved next to the summary.

Systems compared:
  lora              MiniLM-L6 + LoRA on "workflow + last 15 lines" (3 seeds)
  prompted_llm      the graph's classifier: flat-RAG diagnosis (dev-only
                    knowledge base) + llama3.2 prompt with the rubric
  rubric_on_retrieved  the rubric applied to the retrieval-predicted category,
                    no model; shows how much the LLM adds over the rubric itself
"""

import argparse
import json
import platform
import random
import time
from collections import Counter
from importlib.metadata import version
from pathlib import Path

from ml.lora_finetune.data import LEVELS, Example, load_examples

RESULTS = Path(__file__).parent / "results"
PRED_FILE = RESULTS / "v0.5_risk_predictions.json"
SUMMARY_FILE = RESULTS / "v0.5_risk_classifier.json"
SEEDS = (0, 1, 2)
BOOTSTRAP = 10_000


def _load_predictions() -> dict:
    return json.loads(PRED_FILE.read_text(encoding="utf-8")) if PRED_FILE.exists() else {}


def _save_predictions(data: dict) -> None:
    RESULTS.mkdir(exist_ok=True)
    PRED_FILE.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


def _test_set(examples: list[Example]) -> list[Example]:
    return [e for e in examples if e.split == "test"]


def stage_lora() -> None:
    """Train and predict seed by seed, saving after each one, so an interrupted
    run resumes where it stopped (an already-trained adapter is reused)."""
    from agents.risk_classifier_lora import LoraRiskClassifier
    from ml.lora_finetune.train import ARTIFACTS, TrainConfig, train

    examples = load_examples()
    test = _test_set(examples)
    data = _load_predictions()
    lora = data.setdefault("lora", {"config": TrainConfig().__dict__, "runs": {}})
    for seed in SEEDS:
        if str(seed) in lora["runs"]:
            print(f"seed {seed}: already done")
            continue
        adapter = ARTIFACTS / f"seed{seed}"
        if (adapter / "adapter_config.json").exists():
            stats: dict = {"train_examples": sum(e.split != "test" for e in examples),
                           "reused_adapter": True}
        else:
            adapter, stats = train(seed, examples=examples)
        clf = LoraRiskClassifier(adapter)
        start = time.perf_counter()
        preds = {}
        for e in test:
            lines = e.text.splitlines()
            level, probs = clf.predict(lines[0].removeprefix("workflow: "), lines[1:])
            preds[e.example_id] = {"pred": level, "probs": probs}
        stats["predict_ms_per_log"] = round((time.perf_counter() - start) * 1000 / len(test), 1)
        lora["runs"][str(seed)] = {"stats": stats, "predictions": preds}
        _save_predictions(data)
        print(f"seed {seed}: {stats}", flush=True)


def stage_prompted() -> None:
    from agents.diagnosis_agent import DiagnosisAgent, build_retriever
    from agents.risk_classifier import PromptedRiskClassifier
    from agents.risk_rubric import rubric_risk
    from app.config import get_settings
    from app.ingestion import parse_log

    labels = {row["log_id"]: row for row in _label_rows()}
    test = _test_set(load_examples())
    diagnoser = DiagnosisAgent(build_retriever(only_reviewed=True))  # dev-only knowledge base
    classifier = PromptedRiskClassifier(get_settings())
    data = _load_predictions()
    prompted = data.get("prompted_llm", {"predictions": {}})
    rubric = data.get("rubric_on_retrieved", {"predictions": {}})
    for i, e in enumerate(test, 1):
        if e.example_id in prompted["predictions"]:
            continue  # resume after an interruption
        row = labels[e.example_id]
        raw = (Path("data/sample_logs/oss") / f"{e.example_id}.log").read_text(encoding="utf-8")
        diagnosis = diagnoser.run(parse_log(raw))
        start = time.perf_counter()
        risk = classifier.run(diagnosis, workflow=row["workflow"])
        prompted["predictions"][e.example_id] = {
            "pred": risk.level, "method": risk.method, "error": classifier.last_error,
            "ms": round((time.perf_counter() - start) * 1000), "category": diagnosis.category}
        rubric["predictions"][e.example_id] = {"pred": rubric_risk(diagnosis.category, row["workflow"]),
                                               "category": diagnosis.category}
        data["prompted_llm"], data["rubric_on_retrieved"] = prompted, rubric
        _save_predictions(data)  # after every log, so a crash loses nothing
        print(f"{i}/{len(test)} {e.example_id}: {risk.level} ({risk.method})", flush=True)


def _label_rows() -> list[dict]:
    import csv

    from ml.lora_finetune.data import LABELS

    with LABELS.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _metrics(golds: list[str], preds: list[str]) -> dict:
    n = len(golds)
    per_class = {}
    for lvl in LEVELS:
        tp = sum(g == p == lvl for g, p in zip(golds, preds))
        support = sum(g == lvl for g in golds)
        predicted = sum(p == lvl for p in preds)
        precision = tp / predicted if predicted else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[lvl] = {"precision": round(precision, 3), "recall": round(recall, 3),
                          "f1": round(f1, 3), "support": support}
    return {
        "n": n,
        "accuracy": round(sum(g == p for g, p in zip(golds, preds)) / n, 3),
        "macro_f1": round(sum(c["f1"] for c in per_class.values()) / len(LEVELS), 3),
        "per_class": per_class,
        "confusion": {g: dict(Counter(p for gg, p in zip(golds, preds) if gg == g)) for g in LEVELS},
    }


def _bootstrap(a: list[float], b: list[float], seed: int = 0) -> dict:
    diffs = [x - y for x, y in zip(a, b)]
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(diffs, k=len(diffs))) / len(diffs) for _ in range(BOOTSTRAP))
    return {"mean_difference": round(sum(diffs) / len(diffs), 3),
            "ci95_low": round(means[int(0.025 * BOOTSTRAP)], 3),
            "ci95_high": round(means[int(0.975 * BOOTSTRAP)], 3)}


def stage_report() -> None:
    data = _load_predictions()
    labels = {row["log_id"]: row for row in _label_rows()}
    test_ids = [e.example_id for e in _test_set(load_examples())]
    dev_repos = {r["repo"] for r in labels.values() if r["split"] == "dev"}
    subsets = {"all_test": test_ids,
               "unseen_repos": [i for i in test_ids if labels[i]["repo"] not in dev_repos]}
    gold = {i: labels[i]["risk_level"] for i in test_ids}

    systems: dict[str, dict[str, str]] = {}
    for seed, run in data.get("lora", {}).get("runs", {}).items():
        systems[f"lora_seed{seed}"] = {i: p["pred"] for i, p in run["predictions"].items()}
    for name in ("prompted_llm", "rubric_on_retrieved"):
        if name in data:
            systems[name] = {i: p["pred"] for i, p in data[name]["predictions"].items()}
    majority = Counter(r["risk_level"] for r in labels.values() if r["split"] == "dev").most_common(1)[0][0]
    systems["majority_class"] = {i: majority for i in test_ids}

    report: dict = {"labels": "draft rubric v1 on category labels (test category labels are draft)",
                    "train": "dev split + 30 synthetic", "subsets": {}, "versions": {
                        p: version(p) for p in ("torch", "transformers", "peft")},
                    "python": platform.python_version()}
    for subset, ids in subsets.items():
        rows = {}
        for name, preds in systems.items():
            covered = [i for i in ids if i in preds]
            if len(covered) < len(ids):
                rows[name] = {"incomplete": f"{len(covered)}/{len(ids)} predictions"}
                continue
            rows[name] = _metrics([gold[i] for i in ids], [preds[i] for i in ids])
        lora_names = [n for n in systems if n.startswith("lora_seed")]
        if lora_names and "prompted_llm" in systems and all(
                "accuracy" in rows.get(n, {}) for n in [*lora_names, "prompted_llm"]):
            lora_correct = [sum(systems[n][i] == gold[i] for n in lora_names) / len(lora_names)
                            for i in ids]
            llm_correct = [float(systems["prompted_llm"][i] == gold[i]) for i in ids]
            rows["lora_mean_vs_prompted_accuracy"] = _bootstrap(lora_correct, llm_correct)
        report["subsets"][subset] = rows
    if "prompted_llm" in data:
        methods = Counter(p["method"] for p in data["prompted_llm"]["predictions"].values())
        ms = sorted(p["ms"] for p in data["prompted_llm"]["predictions"].values())
        report["prompted_llm_methods"] = dict(methods)
        report["prompted_llm_ms_p50"] = ms[len(ms) // 2]
    if "lora" in data:
        report["lora_runs"] = {s: r["stats"] for s, r in data["lora"]["runs"].items()}
    SUMMARY_FILE.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for subset, rows in report["subsets"].items():
        print(f"\n{subset}:")
        for name, m in rows.items():
            if "accuracy" in m:
                print(f"  {name:22} acc {m['accuracy']:.3f}  macro-F1 {m['macro_f1']:.3f}  "
                      f"recall(h/m/l) {m['per_class']['high']['recall']:.2f}/"
                      f"{m['per_class']['medium']['recall']:.2f}/{m['per_class']['low']['recall']:.2f}")
            else:
                print(f"  {name:22} {m}")
    print(f"\n-> {SUMMARY_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stage", choices=["lora", "prompted", "report"], required=True)
    stage = parser.parse_args().stage
    {"lora": stage_lora, "prompted": stage_prompted, "report": stage_report}[stage]()


if __name__ == "__main__":
    main()
