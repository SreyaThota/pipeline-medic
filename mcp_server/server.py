"""MCP server for the Action Agent's tools.

Run over stdio (for an MCP client such as Claude Desktop or the agent):

    python -m mcp_server.server

Tools default to dry-run. A real action needs ACTIONS_ENABLED=true *and* a
call with dry_run=false; even then tickets and notifications only go to
local files (ADR 004).
"""

from typing import Any

from mcp.server.mcpserver import MCPServer

from app.config import Settings, get_settings
from mcp_server.audit import AuditLog
from mcp_server.tools.create_ticket import create_ticket
from mcp_server.tools.lookup_log import lookup_log
from mcp_server.tools.notify import notify


def build_server(settings: Settings | None = None) -> MCPServer:
    settings = settings or get_settings()
    audit = AuditLog(settings.runtime_dir)
    server = MCPServer(
        name="pipeline-medic",
        instructions=(
            "Tools for acting on a diagnosed CI failure. create_ticket and notify are "
            "dry-run unless dry_run=false and the server has real actions enabled. "
            "lookup_log is read-only. Every call is audited."
        ),
    )

    @server.tool(name="create_ticket",
                 description="Open an incident ticket for a failed CI run. Dry-run by default.")
    def create_ticket_tool(
        title: str,
        body: str,
        severity: str,
        labels: list[str] | None = None,
        source_log_id: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        args = {"title": title, "body": body, "severity": severity,
                "labels": labels or [], "source_log_id": source_log_id}
        return create_ticket(args, dry_run=dry_run, settings=settings, audit=audit).model_dump()

    @server.tool(name="notify",
                 description="Notify an allowlisted channel about a failed CI run. Dry-run by default.")
    def notify_tool(
        channel: str, message: str, severity: str, ticket_id: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        args = {"channel": channel, "message": message, "severity": severity,
                "ticket_id": ticket_id}
        return notify(args, dry_run=dry_run, settings=settings, audit=audit).model_dump()

    @server.tool(name="lookup_log",
                 description="Read up to 200 lines of an indexed CI log (read-only, redacted).")
    def lookup_log_tool(
        log_id: str, start_line: int = 1, end_line: int | None = None
    ) -> dict[str, Any]:
        args = {"log_id": log_id, "start_line": start_line, "end_line": end_line}
        return lookup_log(args, settings=settings, audit=audit).model_dump()

    return server


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
