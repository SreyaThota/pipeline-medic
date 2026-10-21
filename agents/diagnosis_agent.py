"""Diagnosis Agent: parsed log → category, evidence and similar past failures.

Retrieval is flat RAG, the measured default (CLAUDE.md section 4): the query
is the log's last 15 lines, exactly the v0.2 baseline. The category is a
score-weighted vote over the top-k retrieved past failures; the confidence is
the winning share of that vote. Evidence comes from the parser's failure
regions, so every cited line exists in the submitted log.

No model writes the summary: it is built from the evidence, so it cannot
claim anything the log does not show.
"""

from collections import defaultdict

from app.graph import Diagnosis, Evidence, SimilarIncident
from app.schemas.logs import ParsedLog
from rag.retrieve import Retriever

# Labels that mean "this log holds no cause": never voted for.
NON_CATEGORIES = {"aggregate_gate", "unknown"}
MAX_EVIDENCE = 8


def select_evidence(parsed: ParsedLog) -> list[Evidence]:
    """Anchor lines of the most informative regions, in log order."""
    priority = {"stack_trace": 0, "error": 1, "test_summary": 2, "exit_code": 3}
    regions = sorted(parsed.regions, key=lambda r: (priority[r.kind], -r.anchor_line))
    chosen: dict[int, str] = {}
    for region in regions:
        anchor = next(line for line in region.lines if line.number == region.anchor_line)
        chosen.setdefault(anchor.number, anchor.text)
        if len(chosen) >= MAX_EVIDENCE:
            break
    if not chosen:  # no regions: fall back to the end of the log
        chosen = {line.number: line.text for line in parsed.tail[-3:]}
    return [Evidence(line=n, text=t) for n, t in sorted(chosen.items())]


def build_retriever(only_reviewed: bool = True, embed: object = None) -> Retriever:
    """Flat-RAG retriever over the labelled real logs.

    By default only human-reviewed labels go into the knowledge base, so a
    draft label can never drive a diagnosis.
    """
    import csv

    import chromadb

    from rag.ingest import INDEX_CSV, build_collection, load_records, sentence_transformer_embedder

    with INDEX_CSV.open(newline="", encoding="utf-8") as f:
        reviewed = {row["log_id"] for row in csv.DictReader(f) if row["label_status"] == "reviewed"}
    records = [r for r in load_records(labelled_only=True)
               if r.label not in NON_CATEGORIES and (not only_reviewed or r.log_id in reviewed)]
    embedder = embed or sentence_transformer_embedder()
    collection = build_collection(chromadb.EphemeralClient(), records, embedder, "tail",  # type: ignore[arg-type]
                                  name="knowledge_base")
    return Retriever(collection, embedder)  # type: ignore[arg-type]


class DiagnosisAgent:
    def __init__(self, retriever: Retriever | None, k: int = 5):
        self.retriever = retriever
        self.k = k

    def run(self, parsed: ParsedLog, exclude_log_id: str | None = None) -> Diagnosis:
        evidence = select_evidence(parsed)
        query = "\n".join(line.text for line in parsed.tail)
        hits = []
        if self.retriever is not None and query.strip():
            hits = self.retriever.search(query, k=self.k, exclude_log_id=exclude_log_id,
                                         clean=False)
        votes: dict[str, float] = defaultdict(float)
        for hit in hits:
            if hit.label and hit.label not in NON_CATEGORIES:
                votes[hit.label] += max(hit.score, 0.0)
        total = sum(votes.values())
        category = max(votes, key=lambda label: votes[label]) if total > 0 else None
        confidence = round(votes[category] / total, 3) if category else 0.0

        key = evidence[0] if evidence else None
        summary = (
            f"{len(parsed.regions)} failure region(s) in {parsed.line_count} lines"
            + (f"; key evidence at line {key.line}: {key.text[:200]}" if key else "")
            + (f". Most similar past failures suggest {category} "
               f"({confidence:.0%} of the retrieval vote)." if category else
               ". No similar past failure was found.")
        )
        return Diagnosis(
            category=category,
            confidence=confidence,
            summary=summary,
            evidence=evidence,
            similar=[SimilarIncident(log_id=h.log_id, repo=h.repo, label=h.label,
                                     score=round(h.score, 4)) for h in hits],
            method="retrieval_vote" if self.retriever is not None else "no_retrieval",
        )
