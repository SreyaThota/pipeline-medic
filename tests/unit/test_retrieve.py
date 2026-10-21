import chromadb

from rag.ingest import LogRecord, build_collection
from rag.retrieve import Retriever

SETUP = "\n".join(f"runner setup step {i}" for i in range(30))
RECORDS = [
    LogRecord("a1", "org/a", "test_failure", SETUP + "\nAssertionError expected 3 got 4\nFAILED tests"),
    LogRecord("b1", "org/b", "test_failure", SETUP + "\nAssertionError expected true\nFAILED tests"),
    LogRecord("c1", "org/c", "dependency_install",
              SETUP + "\nERROR Could not find a version that satisfies the requirement foo"),
    LogRecord("d1", "org/a", "lint_format", SETUP + "\nruff check found 3 errors E501 line too long"),
]


def _retriever(fake_embed, strategy="window"):
    client = chromadb.EphemeralClient()
    collection = build_collection(client, RECORDS, fake_embed, strategy, name=f"t_{strategy}")
    return Retriever(collection, fake_embed)


def test_similar_failure_ranks_first(fake_embed):
    hits = _retriever(fake_embed).search("AssertionError expected 1 got 2\nFAILED tests", k=2, clean=False)
    assert hits[0].label == "test_failure"
    assert hits[0].score >= hits[1].score


def test_results_are_unique_logs_not_chunks(fake_embed):
    hits = _retriever(fake_embed).search("runner setup step 3", k=4, clean=False)
    ids = [h.log_id for h in hits]
    assert len(ids) == len(set(ids)) == 4


def test_exclude_filters_for_leave_one_out(fake_embed):
    retriever = _retriever(fake_embed)
    query = RECORDS[0].text
    hits = retriever.search(query, k=4, exclude_log_id="a1", clean=False)
    assert "a1" not in [h.log_id for h in hits]
    hits = retriever.search(query, k=4, exclude_log_id="a1", exclude_repo="org/a", clean=False)
    assert {h.repo for h in hits}.isdisjoint({"org/a"})
