"""Parsed-log contract: what /v1/parse returns and what later phases consume."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

LogFormat = Literal["github_actions", "jenkins", "text"]
Severity = Literal["error", "warning", "info"]
RegionKind = Literal["stack_trace", "error", "test_summary", "exit_code"]


class LogLine(BaseModel):
    number: int = Field(description="1-based line number in the submitted log")
    job: str | None = None
    step: str | None = None
    timestamp: datetime | None = None
    severity: Severity
    text: str = Field(description="Normalised and redacted line text")
    noise: bool = Field(False, description="Runner boilerplate such as post-job cleanup")


class FailureRegion(BaseModel):
    kind: RegionKind
    start_line: int
    end_line: int
    anchor_line: int = Field(description="The line that triggered this region")
    lines: list[LogLine]


class ExitCode(BaseModel):
    line: int
    code: int


class RedactionReport(BaseModel):
    total: int
    by_kind: dict[str, int]
    lines: list[int] = Field(description="Line numbers that had something redacted")


class ParsedLog(BaseModel):
    format: LogFormat
    format_detected: bool = Field(description="False if the caller forced the format")
    line_count: int
    jobs: list[str]
    failed_steps: list[str]
    exit_codes: list[ExitCode]
    regions: list[FailureRegion]
    tail: list[LogLine] = Field(description="Last non-noise lines: the v0.2 retrieval window")
    redaction: RedactionReport
    flags: list[str] = Field(description="Diagnostic notes, e.g. no_error_markers_found")


class ParseRequest(BaseModel):
    log_text: str = Field(min_length=1)
    format: LogFormat | Literal["auto"] = "auto"
