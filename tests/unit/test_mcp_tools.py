import json

import pytest

from app.config import Settings
from mcp_server.audit import AuditLog
from mcp_server.tools.create_ticket import create_ticket
from mcp_server.tools.lookup_log import lookup_log
from mcp_server.tools.notify import notify

TICKET = {"title": "CI failure: test_failure", "body": "FAILED tests/test_x.py", "severity": "high"}


@pytest.fixture
def env(tmp_path):
    settings = Settings(runtime_dir=str(tmp_path))
    return settings, AuditLog(tmp_path)


@pytest.fixture
def live_env(tmp_path):
    settings = Settings(runtime_dir=str(tmp_path), actions_enabled=True)
    return settings, AuditLog(tmp_path)


def test_create_ticket_is_a_dry_run_by_default(env, tmp_path):
    settings, audit = env
    result = create_ticket(TICKET, settings=settings, audit=audit)

    assert result.status == "dry_run" and result.dry_run
    assert not (tmp_path / "tickets.jsonl").exists()
    phases = [e["phase"] for e in audit.entries(result.action_id)]
    assert phases == ["proposed", "dry_run"]  # proposal logged before the outcome


def test_real_action_needs_both_the_setting_and_dry_run_false(env, live_env, tmp_path):
    settings, audit = env
    refused = create_ticket(TICKET, dry_run=False, settings=settings, audit=audit)
    assert refused.status == "dry_run"
    assert "ACTIONS_ENABLED" in refused.result["note"]

    live_settings, live_audit = live_env
    done = create_ticket(TICKET, dry_run=False, settings=live_settings, audit=live_audit)
    assert done.status == "executed"
    stored = json.loads((tmp_path / "tickets.jsonl").read_text(encoding="utf-8"))
    assert stored["ticket_id"] == done.result["ticket_id"]
    assert [e["phase"] for e in live_audit.entries(done.action_id)] == ["proposed", "executed"]


def test_notify_only_reaches_allowlisted_channels(live_env, tmp_path):
    settings, audit = live_env
    ok = notify({"channel": "oncall", "message": "CI is red", "severity": "high"},
                dry_run=False, settings=settings, audit=audit)
    assert ok.status == "executed"
    assert ok.result == {"delivered_to": "oncall", "backend": "local_outbox"}

    bad = notify({"channel": "general", "message": "hi", "severity": "low"},
                 dry_run=False, settings=settings, audit=audit)
    assert bad.status == "rejected"
    assert "allowlist" in bad.error
    assert [e["phase"] for e in audit.entries(bad.action_id)] == ["rejected"]


def test_secrets_are_redacted_in_the_proposal_the_store_and_the_audit(live_env, tmp_path):
    settings, audit = live_env
    secret = "ghp_" + "Ab3dEf6hIj9kLm2nOp5qRs8tUv1wXy4zAb7d"
    result = create_ticket({**TICKET, "body": f"push failed with token {secret}"},
                           dry_run=False, settings=settings, audit=audit)
    assert result.status == "executed"
    for text in (json.dumps(result.proposal),
                 (tmp_path / "tickets.jsonl").read_text(encoding="utf-8"),
                 (tmp_path / "audit.jsonl").read_text(encoding="utf-8")):
        assert secret not in text
    assert "[REDACTED:github_token]" in result.proposal["body"]


def test_lookup_log_reads_a_bounded_redacted_range(env):
    settings, audit = env
    result = lookup_log({"log_id": "psf__black__34023398343", "start_line": 160, "end_line": 168},
                        settings=settings, audit=audit)
    assert result.status == "executed"
    numbers = [line["number"] for line in result.result["lines"]]
    assert numbers == list(range(160, 169))
    assert result.result["total_lines"] > 160


def test_lookup_of_an_unindexed_log_fails_cleanly(env):
    settings, audit = env
    result = lookup_log({"log_id": "nobody__nothing__123"}, settings=settings, audit=audit)
    assert result.status == "failed"
    assert "unknown log_id" in result.error
    assert [e["phase"] for e in audit.entries(result.action_id)] == ["proposed", "failed"]
