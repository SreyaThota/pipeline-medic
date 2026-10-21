import chromadb
import pytest

from agents.diagnosis_agent import DiagnosisAgent, select_evidence
from app.ingestion import parse_log
from rag.ingest import LogRecord, build_collection
from rag.retrieve import Retriever

CORPUS = [
    LogRecord("a__x__1", "org/a", "test_failure", "FAILED tests/test_login.py AssertionError expected 200"),
    LogRecord("b__x__2", "org/b", "test_failure", "FAILED tests/test_cart.py AssertionError expected 3"),
    LogRecord("c__x__3", "org/c", "lint_format", "would reformat src/app.py black"),
    LogRecord("d__x__4", "org/d", "aggregate_gate", "Some of the required jobs failed FAILED"),
]


@pytest.fixture
def retriever(fake_embed):
    collection = build_collection(chromadb.EphemeralClient(), CORPUS, fake_embed, "tail",
                                  name="diagnosis_agent_test")
    return Retriever(collection, fake_embed)


LOG = """Run pytest
Traceback (most recent call last):
  File "tests/test_login.py", line 9, in test_login
AssertionError: expected 200
FAILED tests/test_login.py::test_login - AssertionError
exit code 1"""


def test_vote_picks_the_majority_category(retriever):
    diagnosis = DiagnosisAgent(retriever, k=3).run(parse_log(LOG))
    assert diagnosis.category == "test_failure"
    assert 0.5 < diagnosis.confidence <= 1.0
    assert diagnosis.method == "retrieval_vote"
    assert {s.log_id for s in diagnosis.similar} <= {c.log_id for c in CORPUS}


def test_gate_and_unknown_labels_never_win_the_vote(retriever):
    diagnosis = DiagnosisAgent(retriever, k=4).run(parse_log(LOG))
    assert diagnosis.category != "aggregate_gate"


def test_exclude_log_id_is_passed_to_retrieval(retriever):
    diagnosis = DiagnosisAgent(retriever, k=4).run(parse_log(LOG), exclude_log_id="a__x__1")
    assert "a__x__1" not in {s.log_id for s in diagnosis.similar}


def test_evidence_lines_exist_in_the_log():
    parsed = parse_log(LOG)
    evidence = select_evidence(parsed)
    lines = LOG.splitlines()
    assert evidence
    for item in evidence:
        assert lines[item.line - 1].endswith(item.text) or item.text in lines[item.line - 1]


def test_without_retrieval_the_category_is_unknown():
    diagnosis = DiagnosisAgent(None).run(parse_log(LOG))
    assert diagnosis.category is None and diagnosis.confidence == 0.0
    assert diagnosis.method == "no_retrieval"
    assert "No similar past failure" in diagnosis.summary
