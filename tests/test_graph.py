"""Integration tests against a real Neo4j (docker compose up -d).

Skipped when Neo4j is not reachable, unless REQUIRE_NEO4J=1 (set in CI),
in which case an unreachable database is a failure.
"""

import os

import pytest

from rag.entities import Entity
from rag.ingest import LogRecord

neo4j = pytest.importorskip("neo4j")

RECORDS = [
    LogRecord("a1", "org/a", "test_failure",
              "Run python -m pytest\nFAILED tests/t.py::test_x\n= 1 failed, 3 passed in 1.0s ="),
    LogRecord("b1", "org/b", "test_failure",
              "Run python -m pytest\nFAILED tests/u.py::test_y\n= 2 failed, 9 passed in 2.0s ="),
    LogRecord("c1", "org/c", "dependency_install",
              "ERROR: No matching distribution found for foo\nexit code 1"),
    LogRecord("d1", "org/a", "lint_format", "would reformat src/x.py\nexit code 1"),
]


@pytest.fixture(scope="module")
def store():
    from rag.graph import GraphStore

    graph = GraphStore.from_settings(namespace="pytest")
    try:
        graph.driver.verify_connectivity()
    except Exception as exc:  # any connection problem means "no Neo4j"
        graph.close()
        if os.environ.get("REQUIRE_NEO4J") == "1":
            raise
        pytest.skip(f"Neo4j not reachable: {exc}")
    graph.load(RECORDS)
    yield graph
    graph.reset()
    graph.close()


def test_load_creates_typed_nodes(store):
    counts = store.counts()
    assert counts["Run"] == 4
    assert counts["Repo"] == 3
    assert counts["Tool"] >= 2  # pytest, black
    assert counts["ErrorSignature"] >= 3


def test_search_ranks_shared_entities_first(store):
    query = {Entity("tool", "pytest"), Entity("error", "tests_failed")}
    hits = store.search(query, k=3)
    assert [h.log_id for h in hits[:2]] == ["a1", "b1"]
    assert "error:tests_failed" in hits[0].snippet


def test_search_exclusions_for_leave_one_out(store):
    query = {Entity("tool", "pytest"), Entity("error", "tests_failed")}
    hits = store.search(query, k=5, exclude_log_id="b1", exclude_repo="org/a")
    assert hits == []


def test_namespaces_are_isolated(store):
    from rag.graph import GraphStore

    other = GraphStore.from_settings(namespace="pytest_other")
    try:
        assert other.search({Entity("tool", "pytest")}, k=5) == []
    finally:
        other.close()
