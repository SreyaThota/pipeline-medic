"""Measure the v0.2 flat-RAG retrieval baseline.

Leave-one-out over the labelled logs in data/sample_logs/index.csv: every log
is used as a query against all the others, and a retrieval counts as correct
when a returned log has the same failure category label.

Reported per chunking strategy:
  recall@k    - share of queries with >=1 same-label log in the top k
  MRR         - mean reciprocal rank of the first same-label log
  chance@1    - recall@1 a random pick would get, given the label mix
  latency     - per-query search time (embedding the query + Chroma lookup)

"cross-repo" repeats the run with the query's own repo excluded, because
failures from the same repo often share boilerplate and inflate the score.

Usage:
    python -m evaluation.run_eval                 # all labelled logs
    python -m evaluation.run_eval --reviewed-only # only human-reviewed labels
"""

import argparse
import csv
import json
import statistics
import time
from collections import Counter
from pathlib import Path

import chromadb

from rag.ingest import INDEX_CSV, build_collection, load_records, sentence_transformer_embedder
from rag.retrieve import Retriever

RESULTS_DIR = Path(__file__).parent / "results"
# Gate jobs (e.g. "alls-green") only say that another job failed; the cause is
# not in their text, so no retriever can match them. Kept out of the eval.
EXCLUDED_LABELS = {"aggregate_gate"}
STRATEGIES = ["whole", "tail", "window"]
KS = (1, 3, 5)


def hit_at_k(ranked_labels: list[str], true_label: str, k: int) -> bool:
    return true_label in ranked_labels[:k]


def reciprocal_rank(ranked_labels: list[str], true_label: str) -> float:
    for i, label in enumerate(ranked_labels, start=1):
        if label == true_label:
            return 1.0 / i
    return 0.0


def chance_at_1_for(query_labels: list[str], corpus_labels: list[str]) -> float:
    """Expected recall@1 of picking one other corpus log uniformly at random."""
    counts = Counter(corpus_labels)
    n = len(corpus_labels)
    return sum((counts[lbl] - 1) / (n - 1) for lbl in query_labels) / len(query_labels)


def evaluate(retriever: Retriever, queries, cross_repo: bool) -> dict:
    hits = {k: 0 for k in KS}
    rr, latencies, n = 0.0, [], 0
    for rec in queries:
        start = time.perf_counter()
        results = retriever.search(
            rec.text, k=max(KS), exclude_log_id=rec.log_id,
            exclude_repo=rec.repo if cross_repo else None, clean=False,
        )
        latencies.append((time.perf_counter() - start) * 1000)
        if not results:
            continue
        ranked = [h.label for h in results]
        for k in KS:
            hits[k] += hit_at_k(ranked, rec.label, k)
        rr += reciprocal_rank(ranked, rec.label)
        n += 1
    return {
        **{f"recall@{k}": round(hits[k] / n, 3) for k in KS},
        "mrr": round(rr / n, 3),
        "latency_ms_p50": round(statistics.median(latencies), 1),
        "latency_ms_p95": round(statistics.quantiles(latencies, n=20)[-1], 1),
        "queries": n,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the v0.2 retrieval baseline eval.")
    parser.add_argument("--reviewed-only", action="store_true")
    parser.add_argument("--window", type=int, default=15)
    parser.add_argument("--overlap", type=int, default=5)
    args = parser.parse_args()

    with INDEX_CSV.open(newline="", encoding="utf-8") as f:
        status = {r["log_id"]: r["label_status"] for r in csv.DictReader(f)}
    records = [r for r in load_records(labelled_only=True)
               if r.label not in EXCLUDED_LABELS
               and (not args.reviewed_only or status[r.log_id] == "reviewed")]
    labels = [r.label for r in records]
    counts = Counter(labels)
    # A log whose category has no other member can never be matched, so it
    # stays in the corpus as a distractor but is not used as a query.
    queries = [r for r in records if counts[r.label] >= 2]
    query_labels = [r.label for r in queries]
    print(f"{len(records)} logs in corpus, {len(queries)} queries, {len(counts)} categories")
    if len(queries) < 2:
        hint = (" Set label_status to 'reviewed' in data/sample_logs/index.csv"
                " for the labels you've checked." if args.reviewed_only else "")
        raise SystemExit(f"Not enough labelled logs to evaluate.{hint}")

    embed = sentence_transformer_embedder()
    client = chromadb.EphemeralClient()
    report = {
        "corpus_logs": len(records),
        "queries": len(queries),
        "excluded_labels": sorted(EXCLUDED_LABELS),
        "label_counts": dict(counts.most_common()),
        "reviewed_only": args.reviewed_only,
        "chance@1": round(chance_at_1_for(query_labels, labels), 3),
        "window": args.window, "overlap": args.overlap,
        "strategies": {},
    }
    for strategy in STRATEGIES:
        start = time.perf_counter()
        collection = build_collection(
            client, records, embed, strategy, args.window, args.overlap, name=f"eval_{strategy}"
        )
        build_s = time.perf_counter() - start
        retriever = Retriever(collection, embed, query_window=args.window)
        report["strategies"][strategy] = {
            "chunks": collection.count(),
            "index_build_s": round(build_s, 1),
            "same_repo_allowed": evaluate(retriever, queries, cross_repo=False),
            "cross_repo": evaluate(retriever, queries, cross_repo=True),
        }
        print(strategy, json.dumps(report["strategies"][strategy]))

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / "v0.2_flat_rag_baseline.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"chance@1 = {report['chance@1']}  ->  {out}")


if __name__ == "__main__":
    main()
