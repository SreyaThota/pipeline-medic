import pytest

from agents.action_agent import ActionAgent
from app.config import Settings
from app.graph import Diagnosis, Evidence, RiskAssessment


def diagnosis(category="test_failure", confidence=0.8, evidence=None):
    return Diagnosis(
        category=category, confidence=confidence, method="retrieval_vote",
        summary="1 test failed in tests/test_api.py",
        evidence=evidence or [Evidence(line=12, text="FAILED tests/test_api.py::test_login")],
    )


def risk(level):
    return RiskAssessment(level=level, rationale="test fixture", method="rules_fallback")


@pytest.fixture
def agent(tmp_path):
    return ActionAgent(Settings(runtime_dir=str(tmp_path)))


@pytest.mark.parametrize(
    ("level", "category", "confidence", "tools"),
    [
        ("high", "build_compile", 0.9, ["create_ticket", "notify"]),
        ("medium", "test_failure", 0.9, ["create_ticket"]),
        ("low", "lint_format", 0.9, []),
        ("low", None, 0.0, ["create_ticket", "notify"]),          # unknown → human triage
        ("medium", "test_failure", 0.3, ["create_ticket", "notify"]),  # low confidence
    ],
)
def test_policy_table(agent, level, category, confidence, tools):
    actions = agent.propose(diagnosis(category, confidence), risk(level))
    assert [a.tool for a in actions] == tools
    assert all(a.requires_approval for a in actions)


def test_uncertain_diagnosis_is_labelled_for_triage(agent):
    ticket = agent.propose(diagnosis(None, 0.0), risk("low"))[0]
    assert "needs-triage" in ticket.arguments["labels"]
    assert ticket.arguments["title"].startswith("[low] CI failure: unknown")


def test_ticket_body_quotes_evidence_with_line_numbers(agent):
    ticket = agent.propose(diagnosis(), risk("medium"), log_ref="org__repo__42")[0]
    body = ticket.arguments["body"]
    assert "> L12: FAILED tests/test_api.py::test_login" in body
    assert "Source log: org__repo__42" in body
    assert ticket.arguments["source_log_id"] == "org__repo__42"


def test_execute_without_approval_is_always_a_dry_run(tmp_path):
    agent = ActionAgent(Settings(runtime_dir=str(tmp_path), actions_enabled=True))
    actions = agent.propose(diagnosis(), risk("high"))
    results = [agent.execute(a) for a in actions]
    assert [r.status for r in results] == ["dry_run", "dry_run"]
    assert not (tmp_path / "tickets.jsonl").exists()

    approved = agent.execute(actions[0], approved=True)
    assert approved.status == "executed"
    assert approved.action_id == actions[0].action_id  # audit links proposal and outcome


def test_proposed_arguments_pass_tool_validation(agent):
    for action in agent.propose(diagnosis(None, 0.0), risk("high"), log_ref="org__repo__42"):
        assert agent.execute(action).status == "dry_run"
