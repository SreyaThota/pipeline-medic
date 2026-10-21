"""The full v0.4 agent graph on a synthetic failure log.

The model and the embedder are faked so the test is deterministic; every
other part (parser, retrieval over Chroma, vote, rubric, policy, MCP tools,
audit, LangGraph checkpointing and interrupt) is real.
"""

from pathlib import Path

import chromadb
import pytest

from agents.action_agent import ActionAgent
from agents.diagnosis_agent import DiagnosisAgent
from agents.parser_agent import ParserAgent
from agents.risk_classifier import PromptedRiskClassifier
from app.config import Settings
from app.graph import Approval
from app.graph_orchestrator import PipelineMedicGraph, make_checkpointer
from mcp_server.audit import AuditLog
from rag.ingest import LogRecord, build_collection
from rag.retrieve import Retriever

FIXTURE = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "github_actions_pytest.log"
SECRET = "ghp_" + "Ab3dEf6hIj9kLm2nOp5qRs8tUv1wXy4zAb7d"
STAGES = ["parse", "diagnose", "classify_risk", "propose_actions"]

CORPUS = [
    LogRecord("a__x__1", "org/a", "test_failure",
              "FAILED tests/test_api.py::test_login - AssertionError: expected 200\n1 failed"),
    LogRecord("b__x__2", "org/b", "test_failure", "FAILED tests/test_cart.py AssertionError 1 failed"),
    LogRecord("c__x__3", "org/c", "lint_format", "would reformat src/app.py"),
]


def make_graph(tmp_path, fake_embed, risk="high", actions_enabled=False, checkpointer=None):
    settings = Settings(runtime_dir=str(tmp_path), actions_enabled=actions_enabled)
    collection = build_collection(chromadb.EphemeralClient(), CORPUS, fake_embed, "tail",
                                  name=f"graph_test_{risk}")
    classifier = PromptedRiskClassifier(
        settings, generate=lambda p, s: f'{{"risk": "{risk}", "rationale": "fixture"}}'
    )
    return PipelineMedicGraph(ParserAgent(), DiagnosisAgent(Retriever(collection, fake_embed), k=3),
                              classifier, ActionAgent(settings), checkpointer=checkpointer)


@pytest.fixture
def log_text():
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    lines.insert(2, f"test (3.12)\tRun tests\t2026-10-20T09:15:01.2500000Z export GITHUB_TOKEN={SECRET}")
    return "\n".join(lines)


def test_full_run_pauses_for_approval_with_a_traced_proposal(tmp_path, fake_embed, log_text):
    graph = make_graph(tmp_path, fake_embed)
    state = graph.start(log_text, source_log_id="org__demo__1")

    assert state["status"] == "awaiting_approval"
    assert graph.is_paused(state["run_id"])
    assert [t.stage for t in state["trace"]] == STAGES
    assert all(t.duration_ms >= 0 for t in state["trace"])
    assert state["diagnosis"].category == "test_failure"
    assert state["risk"].level == "high" and state["risk"].method == "prompted_llm"
    assert [a.tool for a in state["proposed_actions"]] == ["create_ticket", "notify"]
    ticket = state["proposed_actions"][0]
    assert "> L" in ticket.arguments["body"]  # evidence with line numbers
    assert AuditLog(tmp_path).entries() == []  # nothing has run yet


def test_approval_resumes_from_the_checkpoint_in_a_new_graph(tmp_path, fake_embed, log_text):
    saver = make_checkpointer()
    first = make_graph(tmp_path, fake_embed, actions_enabled=True, checkpointer=saver)
    run_id = first.start(log_text)["run_id"]

    # A fresh graph instance (e.g. after a restart) sharing the checkpointer.
    second = make_graph(tmp_path, fake_embed, actions_enabled=True, checkpointer=saver)
    done = second.resume(run_id, Approval(approved=True, approver="sreya"))

    assert done["status"] == "completed"
    assert [t.stage for t in done["trace"]] == [*STAGES, "human_approval", "execute_actions"]
    assert [r.status for r in done["action_results"]] == ["executed", "executed"]
    assert (tmp_path / "tickets.jsonl").exists() and (tmp_path / "outbox.jsonl").exists()
    with pytest.raises(RuntimeError, match="not waiting"):
        second.resume(run_id, Approval(approved=True, approver="sreya"))


def test_approval_with_real_actions_disabled_still_only_dry_runs(tmp_path, fake_embed, log_text):
    graph = make_graph(tmp_path, fake_embed, actions_enabled=False)
    run_id = graph.start(log_text)["run_id"]
    done = graph.resume(run_id, Approval(approved=True, approver="sreya"))
    assert [r.status for r in done["action_results"]] == ["dry_run", "dry_run"]
    assert not (tmp_path / "tickets.jsonl").exists()


def test_rejection_runs_nothing_and_is_audited(tmp_path, fake_embed, log_text):
    graph = make_graph(tmp_path, fake_embed, actions_enabled=True)
    run_id = graph.start(log_text)["run_id"]
    done = graph.resume(run_id, Approval(approved=False, approver="sreya", note="known flake"))

    assert done["status"] == "rejected"
    assert [r.status for r in done["action_results"]] == ["rejected", "rejected"]
    assert not (tmp_path / "tickets.jsonl").exists()
    phases = [e["phase"] for e in AuditLog(tmp_path).entries()]
    assert phases == ["rejected_by_human", "rejected_by_human"]


def test_low_risk_finishes_without_an_interrupt(tmp_path, fake_embed, log_text):
    graph = make_graph(tmp_path, fake_embed, risk="low")
    state = graph.start(log_text)
    assert state["status"] == "resolved_no_action"
    assert not graph.is_paused(state["run_id"])
    assert [t.stage for t in state["trace"]] == STAGES


def test_no_secret_reaches_the_checkpointed_state(tmp_path, fake_embed, log_text):
    graph = make_graph(tmp_path, fake_embed)
    state = graph.start(log_text)
    checkpointed = repr(graph.graph.get_state({"configurable": {"thread_id": state["run_id"]}}))
    assert SECRET not in checkpointed
    assert SECRET not in state["log_text"]
    assert "[REDACTED:" in state["log_text"]
