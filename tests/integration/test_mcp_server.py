"""The MCP server over the real protocol, connected in-process."""

import asyncio

from mcp import Client

from app.config import Settings
from mcp_server.audit import AuditLog
from mcp_server.server import build_server


def call(settings, name, args):
    async def go():
        async with Client(build_server(settings)) as client:
            listed = await client.list_tools()
            result = await client.call_tool(name, args)
            return [t.name for t in listed.tools], result

    return asyncio.run(go())


def test_server_lists_exactly_the_three_tools(tmp_path):
    names, _ = call(Settings(runtime_dir=str(tmp_path)), "lookup_log",
                    {"log_id": "psf__black__34023398343", "start_line": 1, "end_line": 2})
    assert sorted(names) == ["create_ticket", "lookup_log", "notify"]


def test_create_ticket_over_mcp_defaults_to_dry_run(tmp_path):
    settings = Settings(runtime_dir=str(tmp_path), actions_enabled=True)
    _, result = call(settings, "create_ticket",
                     {"title": "CI failed", "body": "FAILED test_x", "severity": "medium"})
    payload = result.structured_content
    assert payload["status"] == "dry_run"
    assert not (tmp_path / "tickets.jsonl").exists()
    phases = [e["phase"] for e in AuditLog(tmp_path).entries(payload["action_id"])]
    assert phases == ["proposed", "dry_run"]


def test_bad_arguments_over_mcp_are_refused_and_audited(tmp_path):
    settings = Settings(runtime_dir=str(tmp_path), actions_enabled=True)
    _, result = call(settings, "notify",
                     {"channel": "general", "message": "hi", "severity": "low", "dry_run": False})
    assert result.structured_content["status"] == "rejected"
    assert AuditLog(tmp_path).entries()[-1]["phase"] == "rejected"
