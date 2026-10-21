"""v0.7: a graph run leaves a complete, linkable, text-free trace."""

import json

import chromadb

from agents.action_agent import ActionAgent
from agents.diagnosis_agent import DiagnosisAgent
from agents.parser_agent import ParserAgent
from agents.risk_classifier import PromptedRiskClassifier
from app.config import Settings
from app.graph import Approval
from app.graph_orchestrator import PipelineMedicGraph
from app.observability.tracing import summarize
from mcp_server.audit import AuditLog
from rag.ingest import LogRecord, build_collection
from rag.retrieve import Retriever

LOG = """Run tests
FAILED tests/test_api.py::test_login - AssertionError: expected 200, got 401
= 1 failed, 7 passed in 8.1s =
exit code 1"""
CORPUS = [LogRecord("a__x__1", "org/a", "test_failure", "FAILED tests/test_api.py AssertionError")]


def test_run_produces_stage_and_tool_spans_linked_to_the_audit_log(tmp_path, fake_embed):
    settings = Settings(runtime_dir=str(tmp_path), actions_enabled=True)
    collection = build_collection(chromadb.EphemeralClient(), CORPUS, fake_embed, "tail",
                                  name="observability_test")
    graph = PipelineMedicGraph(
        ParserAgent(), DiagnosisAgent(Retriever(collection, fake_embed), k=1),
        PromptedRiskClassifier(settings, generate=lambda p, s: '{"risk": "high"}'),
        ActionAgent(settings),
    )
    run_id = graph.start(LOG)["run_id"]
    graph.resume(run_id, Approval(approved=True, approver="sreya"))

    spans = [json.loads(line) for line in (tmp_path / "traces.jsonl").read_text().splitlines()]
    stages = [s for s in spans if s["kind"] == "stage"]
    tools = [s for s in spans if s["kind"] == "tool"]

    # The approval node runs twice: once to pause (status "paused"), once on resume.
    assert [(s["name"], s["status"]) for s in stages] == [
        ("parse", "ok"), ("diagnose", "ok"), ("classify_risk", "ok"), ("propose_actions", "ok"),
        ("human_approval", "paused"), ("human_approval", "ok"), ("execute_actions", "ok"),
    ]
    assert {s["trace_id"] for s in spans} == {run_id}

    audited = {e["action_id"] for e in AuditLog(tmp_path).entries() if e["phase"] == "executed"}
    assert {s["attrs"]["action_id"] for s in tools} == audited
    assert [s["status"] for s in tools] == ["executed", "executed"]

    assert "AssertionError" not in (tmp_path / "traces.jsonl").read_text()  # no log text

    summary = summarize(spans)
    assert summary["tools"]["create_ticket"]["success_rate"] == 1.0
    assert summary["stages"]["parse"]["count"] == 1
