"""Tool implementations. Each is a plain function, testable without MCP:

    create_ticket(args, dry_run=True, settings=..., audit=...) -> ToolResult

Common flow (`run_tool`): validate input → redact → audit `proposed` →
dry-run or execute → audit outcome. Invalid input is refused with a
`rejected` result, never an exception, so a malformed call from a model
cannot crash the agent.
"""

import uuid
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from app.config import Settings
from app.graph import ToolName, ToolResult
from app.observability.tracing import get_tracer
from mcp_server.audit import AuditLog

MAX_ARGUMENT_CHARS = 20_000  # whole serialised call; field limits are tighter


def _validation_message(exc: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(p) for p in err['loc']) or 'input'}: {err['msg']}" for err in exc.errors()
    )


def run_tool(
    tool: ToolName,
    validate: Callable[[dict[str, Any]], BaseModel],
    raw_args: dict[str, Any],
    *,
    dry_run: bool,
    settings: Settings,
    audit: AuditLog,
    execute: Callable[[BaseModel], dict[str, Any]],
    redact: Callable[[BaseModel], BaseModel] = lambda model: model,
    read_only: bool = False,
    action_id: str | None = None,
    trace_id: str | None = None,
) -> ToolResult:
    """Run one tool call inside a tracing span (v0.7). The span records only
    the tool, the action_id (which links to the audit log) and the outcome."""
    action_id = action_id or uuid.uuid4().hex
    tracer = get_tracer(settings.runtime_dir)
    with tracer.span(tool, "tool", trace_id=trace_id or action_id, action_id=action_id,
                     requested_dry_run=dry_run) as span:
        result = _run_tool(tool, validate, raw_args, dry_run=dry_run, settings=settings,
                           audit=audit, execute=execute, redact=redact, read_only=read_only,
                           action_id=action_id)
        span.status = result.status
    return result


def _run_tool(
    tool: ToolName,
    validate: Callable[[dict[str, Any]], BaseModel],
    raw_args: dict[str, Any],
    *,
    dry_run: bool,
    settings: Settings,
    audit: AuditLog,
    execute: Callable[[BaseModel], dict[str, Any]],
    redact: Callable[[BaseModel], BaseModel],
    read_only: bool,
    action_id: str,
) -> ToolResult:
    size = len(repr(raw_args))
    if size > MAX_ARGUMENT_CHARS:
        error = f"arguments are {size:,} characters; the limit is {MAX_ARGUMENT_CHARS:,}"
        audit.record(action_id, tool, "rejected", error=error)
        return ToolResult(action_id=action_id, tool=tool, status="rejected",
                          dry_run=dry_run, proposal={}, error=error)
    try:
        args = redact(validate(raw_args))
    except ValidationError as exc:
        error = _validation_message(exc)
        audit.record(action_id, tool, "rejected", error=error)
        return ToolResult(action_id=action_id, tool=tool, status="rejected",
                          dry_run=dry_run, proposal={}, error=error)

    proposal = args.model_dump()
    audit.record(action_id, tool, "proposed", dry_run=dry_run, arguments=proposal)

    # Read-only tools have no side effect to protect, so they always run.
    if not read_only and (dry_run or not settings.actions_enabled):
        note = "dry_run requested" if dry_run else "real actions are disabled (ACTIONS_ENABLED)"
        audit.record(action_id, tool, "dry_run", note=note)
        return ToolResult(action_id=action_id, tool=tool, status="dry_run", dry_run=True,
                          proposal=proposal, result={"note": note})
    try:
        result = execute(args)
    except Exception as exc:  # noqa: BLE001 - audit boundary: every failure is recorded
        audit.record(action_id, tool, "failed", error=type(exc).__name__)
        return ToolResult(action_id=action_id, tool=tool, status="failed", dry_run=False,
                          proposal=proposal, error=f"{type(exc).__name__}: {exc}")
    audit.record(action_id, tool, "executed", result=result)
    return ToolResult(action_id=action_id, tool=tool, status="executed", dry_run=False,
                      proposal=proposal, result=result)
