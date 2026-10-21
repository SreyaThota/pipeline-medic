"""notify: tell a person or channel about a failed CI run.

Channels come from an allowlist (NOTIFY_CHANNELS); anything else is refused.
The real backend is a local outbox file (`<RUNTIME_DIR>/outbox.jsonl`); which
messaging system to deliver to is an open decision (NEEDS_DECISION.md).
"""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.config import Settings
from app.graph import ToolResult
from app.redaction import redact_lines
from mcp_server.audit import AuditLog
from mcp_server.tools import run_tool

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class NotifyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: str = Field(min_length=1, max_length=50)
    message: str = Field(min_length=1, max_length=2_000)
    severity: Literal["low", "medium", "high"]
    ticket_id: str | None = Field(None, pattern=r"^PM-[0-9a-f]{8}$")

    @field_validator("channel")
    @classmethod
    def _allowed_channel(cls, value: str, info: ValidationInfo) -> str:
        allowed = (info.context or {}).get("channels", ())
        if value not in allowed:
            raise ValueError(f"channel is not in the allowlist {sorted(allowed)}")
        return value

    @field_validator("message")
    @classmethod
    def _no_control_chars(cls, value: str) -> str:
        if _CONTROL.search(value):
            raise ValueError("must not contain control characters")
        return value


def _redact(model: BaseModel) -> BaseModel:
    assert isinstance(model, NotifyInput)
    return model.model_copy(
        update={"message": "\n".join(redact_lines(model.message.split("\n")).lines)}
    )


def notify(
    args: dict[str, Any], *, dry_run: bool = True, settings: Settings, audit: AuditLog,
    action_id: str | None = None, trace_id: str | None = None,
) -> ToolResult:
    outbox = Path(settings.runtime_dir) / "outbox.jsonl"

    def validate(raw: dict[str, Any]) -> NotifyInput:
        return NotifyInput.model_validate(raw, context={"channels": settings.notify_channels})

    def execute(model: BaseModel) -> dict[str, Any]:
        record = {"sent_at": datetime.now(UTC).isoformat(), **model.model_dump()}
        outbox.parent.mkdir(parents=True, exist_ok=True)
        with outbox.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return {"delivered_to": model.model_dump()["channel"], "backend": "local_outbox"}

    return run_tool("notify", validate, args, dry_run=dry_run, settings=settings, audit=audit,
                    execute=execute, redact=_redact, action_id=action_id,
                    trace_id=trace_id)
