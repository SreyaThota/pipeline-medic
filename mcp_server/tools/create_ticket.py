"""create_ticket: open an incident ticket for a failed CI run.

The real backend is a local JSONL ticket store (`<RUNTIME_DIR>/tickets.jsonl`).
Which external tracker to use (GitHub Issues, Jira, ...) is an open decision
recorded in NEEDS_DECISION.md; this tool never contacts one.
"""

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.config import Settings
from app.graph import ToolResult
from app.redaction import redact_lines
from mcp_server.audit import AuditLog
from mcp_server.tools import run_tool

LOG_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}__[A-Za-z0-9_.-]{1,80}__\d{1,20}$"
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

Label = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,49}$")]


class TicketInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    body: str = Field(max_length=10_000)
    severity: Literal["low", "medium", "high"]
    labels: list[Label] = Field(default_factory=list, max_length=10)
    source_log_id: Annotated[str, StringConstraints(pattern=LOG_ID_PATTERN)] | None = None

    @field_validator("title")
    @classmethod
    def _single_line(cls, value: str) -> str:
        if "\n" in value or "\r" in value or _CONTROL.search(value):
            raise ValueError("must be a single line without control characters")
        return value

    @field_validator("body")
    @classmethod
    def _no_control_chars(cls, value: str) -> str:
        if _CONTROL.search(value):
            raise ValueError("must not contain control characters")
        return value


def _redact(model: BaseModel) -> BaseModel:
    assert isinstance(model, TicketInput)
    return model.model_copy(update={
        "title": redact_lines([model.title]).lines[0],
        "body": "\n".join(redact_lines(model.body.split("\n")).lines),
    })


def create_ticket(
    args: dict[str, Any], *, dry_run: bool = True, settings: Settings, audit: AuditLog,
    action_id: str | None = None,
) -> ToolResult:
    store = Path(settings.runtime_dir) / "tickets.jsonl"

    def execute(model: BaseModel) -> dict[str, Any]:
        ticket_id = f"PM-{uuid.uuid4().hex[:8]}"
        record = {"ticket_id": ticket_id, "created_at": datetime.now(UTC).isoformat(),
                  **model.model_dump()}
        store.parent.mkdir(parents=True, exist_ok=True)
        with store.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return {"ticket_id": ticket_id, "backend": "local_file"}

    return run_tool("create_ticket", TicketInput.model_validate, args, dry_run=dry_run, settings=settings,
                    audit=audit, execute=execute, redact=_redact, action_id=action_id)
