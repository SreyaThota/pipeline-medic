"""Compare flat RAG with the knowledge graph and their hybrid (v0.2.5).

Same task and protocol as run_eval.py: leave-one-out, a hit is a returned log
with the same failure category. Methods:

  flat            v0.2 baseline: vector search over each log's last 15 lines
  graph           shared-entity score from Neo4j (direct, 2 hops)
  graph_multihop  graph plus the multi-hop expansion score
  hybrid_rrf      flat + graph, fused by reciprocal rank
  hybrid          graph score first, vector similarity breaks ties and ranks
                  whatever the graph did not match
  hybrid_multihop hybrid, with the multi-hop expansion in the graph score

To keep the comparison honest the logs are split in two (index.csv `split`):

  dev   the 51 logs the extraction rules were written against. Every method
        and setting is scored here, and the best graph-based one is selected.
  test  logs collected after the rules were frozen. Only here is the selected
        method compared with flat, with a paired bootstrap interval.

Requires Neo4j (docker compose up -d).

Usage:
    python -m evaluation.run_graph_eval
"""

import json
import random
import statistics
import time
from collections import Counter
from pathlib import Path

import chromadb

from evaluation.run_eval import EXCLUDED_LABELS, KS, chance_at_1_for, hit_at_k, reciprocal_rank
from rag.entities import extract_entities
from rag.graph import GraphStore
from rag.hybrid import HybridRetriever
from rag.ingest import build_collection, load_records, sentence_transformer_embedder
from rag.retrieve import Retriever

RESULTS_PATH = Path(__file__).parent / "results" / "v0.2.5_graphrag_vs_flat.json"
EXPAND_WEIGHTS = (0.25, 0.5, 1.0)  # multi-hop weights tried on dev
BOOTSTRAP_SAMPLES = 10_000


def make_rankers(retriever: Retriever, graph: GraphStore, expand_weight: float) -> dict:
    """name -> function(record, exclude_repo) returning ranked hits."""
    entities = {}

    def ents(rec):
        if rec.log_id not in entities:
            entities[rec.log_id] = extract_entities(rec.text)
        return entities[rec.log_id]

    def common(rec, exclude_repo):
        return {"k": max(KS), "exclude_log_id": rec.log_id, "exclude_repo": exclude_repo}

    hybrid_rrf = HybridRetriever(retriever, graph, fusion="rrf")
    hybrid = HybridRetriever(retriever, graph)
    hybrid_multihop = HybridRetriever(retriever, graph, expand_weight=expand_weight)
    return {
        "flat": lambda rec, repo: retriever.search(rec.text, clean=False, **common(rec, repo)),
        "graph": lambda rec, repo: graph.search(ents(rec), **common(rec, repo)),
        "graph_multihop": lambda rec, repo: graph.search(
            ents(rec), expand_weight=expand_weight, **common(rec, repo)
        ),
        "hybrid_rrf": lambda rec, repo: hybrid_rrf.search(
            rec.text, clean=False, **common(rec, repo)
        ),
        "hybrid": lambda rec, repo: hybrid.search(rec.text, clean=False, **common(rec, repo)),
        "hybrid_multihop": lambda rec, repo: hybrid_multihop.search(
            rec.text, clean=False, **common(rec, repo)
        ),
    }


def score(ranker, queries, cross_repo: bool) -> dict:
    """Metrics plus the per-query reciprocal ranks (kept for the bootstrap)."""
    rrs, hits, latencies = [], {k: 0 for k in KS}, []
    for rec in queries:
        start = time.perf_counter()
        results = ranker(rec, rec.repo if cross_repo else None)
        latencies.append((time.perf_counter() - start) * 1000)
        ranked = [h.label for h in results]
        for k in KS:
            hits[k] += hit_at_k(ranked, rec.label, k)
        rrs.append(reciprocal_rank(ranked, rec.label))
    n = len(queries)
    return {
        **{f"recall@{k}": round(hits[k] / n, 3) for k in KS},
        "mrr": round(sum(rrs) / n, 3),
        "latency_ms_p50": round(statistics.median(latencies), 1),
        "rr": rrs,
    }


def paired_bootstrap(a: list[float], b: list[float], seed: int = 0) -> dict:
    """Mean of (a - b) over queries with a 95% bootstrap interval."""
    diffs = [x - y for x, y in zip(a, b)]
    rng = random.Random(seed)
    means = sorted(
        sum(rng.choices(diffs, k=len(diffs))) / len(diffs) for _ in range(BOOTSTRAP_SAMPLES)
    )
    return {
        "mean_difference": round(sum(diffs) / len(diffs), 3),
        "ci95_low": round(means[int(0.025 * BOOTSTRAP_SAMPLES)], 3),
        "ci95_high": round(means[int(0.975 * BOOTSTRAP_SAMPLES)], 3),
        "queries_better": sum(d > 0 for d in diffs),
        "queries_worse": sum(d < 0 for d in diffs),
        "queries_equal": sum(d == 0 for d in diffs),
    }


def evaluate_setting(name, corpus, queries, embed, client, expand_weight) -> dict:
    """Build both indexes over `corpus` and score every method on `queries`."""
    collection = build_collection(client, corpus, embed, "tail", name=f"graph_eval_{name}")
    graph = GraphStore.from_settings(namespace=f"eval_{name}")
    try:
        graph_counts = graph.load(corpus)
        rankers = make_rankers(Retriever(collection, embed), graph, expand_weight)
        methods = {
            method: {
                "cross_repo": score(ranker, queries, cross_repo=True),
                "same_repo_allowed": score(ranker, queries, cross_repo=False),
            }
            for method, ranker in rankers.items()
        }
    finally:
        graph.reset()
        graph.close()
    labels = [r.label for r in corpus]
    return {
        "corpus_logs": len(corpus),
        "queries": len(queries),
        "label_counts": dict(Counter(labels).most_common()),
        "chance@1": round(chance_at_1_for([r.label for r in queries], labels), 3),
        "graph": graph_counts,
        "expand_weight": expand_weight,
        "methods": methods,
    }


def answerable(records, corpus):
    """Queries whose category has at least one other member in the corpus."""
    counts = Counter(r.label for r in corpus)
    return [r for r in records if counts[r.label] >= 2]


def strip_rr(setting: dict) -> dict:
    for method in setting["methods"].values():
        for view in method.values():
            view.pop("rr", None)
    return setting


def print_table(title: str, setting: dict) -> None:
    print(f"\n{title}: {setting['queries']} queries over {setting['corpus_logs']} logs, "
          f"chance@1 {setting['chance@1']}")
    print(f"  {'method':16} {'cross R@1':>9} {'cross MRR':>9} {'same R@1':>9} {'same MRR':>9} {'p50 ms':>7}")
    for name, m in setting["methods"].items():
        c, s = m["cross_repo"], m["same_repo_allowed"]
        print(f"  {name:16} {c['recall@1']:9.3f} {c['mrr']:9.3f} {s['recall@1']:9.3f} "
              f"{s['mrr']:9.3f} {c['latency_ms_p50']:7.1f}")


def main() -> None:
    records = [r for r in load_records(labelled_only=True) if r.label not in EXCLUDED_LABELS]
    dev = [r for r in records if r.split != "test"]
    test = [r for r in records if r.split == "test"]
    embed = sentence_transformer_embedder()
    client = chromadb.EphemeralClient()

    # 1. Dev: try each multi-hop weight, keep the best, then pick the best
    #    graph-based method. Nothing from the test logs is used here.
    dev_runs = {
        w: evaluate_setting(f"dev_{i}", dev, answerable(dev, dev), embed, client, w)
        for i, w in enumerate(EXPAND_WEIGHTS)
    }

    def dev_mrr(run, method):
        return run["methods"][method]["cross_repo"]["mrr"]

    best_weight = max(EXPAND_WEIGHTS, key=lambda w: dev_mrr(dev_runs[w], "hybrid_multihop"))
    dev_result = dev_runs[best_weight]
    candidates = [m for m in dev_result["methods"] if m != "flat"]
    selected = max(candidates, key=lambda m: dev_mrr(dev_result, m))
    print_table("DEV (rules and settings were chosen here)", dev_result)
    print(f"  multi-hop weight chosen on dev: {best_weight}; selected method: {selected}")

    report = {
        "selected_on_dev": {"method": selected, "expand_weight": best_weight},
        "dev_expand_weight_sweep": {
            str(w): {m: dev_mrr(run, m) for m in ("graph_multihop", "hybrid_multihop")}
            for w, run in dev_runs.items()
        },
        "dev": dev_result,
    }

    # 2. Test: held-out logs as queries over the full corpus.
    if test:
        test_result = evaluate_setting(
            "test", records, answerable(test, records), embed, client, best_weight
        )
        print_table("TEST (held out)", test_result)
        flat_rr = test_result["methods"]["flat"]["cross_repo"]["rr"]
        comparisons = {
            method: paired_bootstrap(test_result["methods"][method]["cross_repo"]["rr"], flat_rr)
            for method in candidates
        }
        report["test"] = test_result
        report["test_mrr_difference_vs_flat_cross_repo"] = comparisons
        primary = comparisons[selected]
        print(f"\n  {selected} vs flat, cross-repo MRR difference on test: "
              f"{primary['mean_difference']:+.3f} "
              f"(95% CI {primary['ci95_low']:+.3f} to {primary['ci95_high']:+.3f}); "
              f"better on {primary['queries_better']}, worse on {primary['queries_worse']}, "
              f"equal on {primary['queries_equal']} queries")
    else:
        print("\nNo labelled test logs yet: dev numbers only.")

    for key in ("dev", "test"):
        if key in report:
            strip_rr(report[key])
    RESULTS_PATH.parent.mkdir(exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\n-> {RESULTS_PATH}")


if __name__ == "__main__":
    main()
