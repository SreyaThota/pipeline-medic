"""lookup_log: read lines of a stored CI log (read-only).

Path safety is layered: the log_id must match a strict pattern, must be listed
in data/sample_logs/index.csv, and the resolved path must stay inside the log
directory. A caller can never name a file, only an indexed log.
"""

import csv
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.config import Settings
from app.graph import ToolResult
from app.redaction import redact_lines
from mcp_server.audit import AuditLog
from mcp_server.tools import run_tool
from mcp_server.tools.create_ticket import LOG_ID_PATTERN

LOG_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_logs"
MAX_LINES = 200


@lru_cache(maxsize=4)
def _index(log_dir: Path) -> dict[str, Path]:
    with (log_dir / "index.csv").open(newline="", encoding="utf-8") as f:
        return {row["log_id"]: log_dir / row["source"] / f"{row['log_id']}.log"
                for row in csv.DictReader(f)}


class LookupInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    log_id: Annotated[str, StringConstraints(pattern=LOG_ID_PATTERN)]
    start_line: int = Field(1, ge=1)
    end_line: int | None = Field(None, ge=1)

    @model_validator(mode="after")
    def _bounded_range(self) -> LookupInput:
        end = self.end_line if self.end_line is not None else self.start_line + MAX_LINES - 1
        if end < self.start_line:
            raise ValueError("end_line must not be before start_line")
        if end - self.start_line + 1 > MAX_LINES:
            raise ValueError(f"at most {MAX_LINES} lines per lookup")
        return self


def lookup_log(
    args: dict[str, Any], *, settings: Settings, audit: AuditLog,
    log_dir: Path = LOG_DIR, action_id: str | None = None, trace_id: str | None = None,
) -> ToolResult:
    root = log_dir.resolve()

    def execute(model: BaseModel) -> dict[str, Any]:
        assert isinstance(model, LookupInput)
        path = _index(root).get(model.log_id)
        if path is None:
            raise LookupError(f"unknown log_id {model.log_id!r}")
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            raise PermissionError("resolved path escapes the log directory")
        lines = resolved.read_text(encoding="utf-8").splitlines()
        end = model.end_line or model.start_line + MAX_LINES - 1
        chunk = redact_lines(lines[model.start_line - 1 : end]).lines
        return {
            "log_id": model.log_id,
            "total_lines": len(lines),
            "lines": [{"number": model.start_line + i, "text": text}
                      for i, text in enumerate(chunk)],
        }

    return run_tool("lookup_log", LookupInput.model_validate, args, dry_run=False, settings=settings,
                    audit=audit, execute=execute, read_only=True, action_id=action_id,
                    trace_id=trace_id)
