"""Typed state shared by the agents (CLAUDE.md section 1).

v0.3 defines what the Action Agent consumes and produces: the diagnosis and
risk assessment it reads, and the `ProposedAction` it emits. v0.4 adds the
LangGraph state (`PipelineMedicState`) that carries these between agents.
"""

import operator
import uuid
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, Field

from app.schemas.logs import ParsedLog

RiskLevel = Literal["low", "medium", "high"]
ToolName = Literal["create_ticket", "notify", "lookup_log"]
ActionStatus = Literal["dry_run", "executed", "rejected", "failed"]


class Evidence(BaseModel):
    """One log line cited as evidence, with its original line number."""

    line: int
    text: str


class SimilarIncident(BaseModel):
    log_id: str
    repo: str
    label: str
    score: float


class Diagnosis(BaseModel):
    category: str | None = Field(description="Predicted failure category, or None if unsure")
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    evidence: list[Evidence] = Field(default_factory=list)
    similar: list[SimilarIncident] = Field(default_factory=list)
    method: str = Field(description="How the diagnosis was produced, e.g. retrieval_vote")


class RiskAssessment(BaseModel):
    level: RiskLevel
    rationale: str
    method: str = Field(description="prompted_llm, rules_fallback, or lora")


class ProposedAction(BaseModel):
    """A tool call the Action Agent wants to make. Nothing runs until approved."""

    action_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    tool: ToolName
    arguments: dict[str, Any]
    reason: str
    requires_approval: bool = True


class ToolResult(BaseModel):
    """What every MCP tool returns, whether it ran, dry-ran or was refused."""

    action_id: str
    tool: ToolName
    status: ActionStatus
    dry_run: bool
    proposal: dict[str, Any] = Field(description="Validated, redacted arguments")
    result: dict[str, Any] | None = None
    error: str | None = None


# --- v0.4: LangGraph state ------------------------------------------------------


StageStatus = Literal["ok", "fallback", "error", "skipped"]


class TraceEntry(BaseModel):
    """One graph stage: what ran, how long it took, and how it ended."""

    stage: str
    status: StageStatus
    started_at: str
    duration_ms: float
    detail: dict[str, Any] = Field(default_factory=dict)


class Approval(BaseModel):
    approved: bool
    approver: str = Field(min_length=1, max_length=100)
    note: str = Field("", max_length=500)


class PipelineMedicState(TypedDict, total=False):
    """Carried between the agents. `log_text` is already redacted when it
    enters the graph, so checkpoints never hold a secret (CLAUDE.md 2F)."""

    run_id: str
    log_text: str
    source_log_id: str | None
    workflow: str | None
    parsed: ParsedLog
    diagnosis: Diagnosis
    risk: RiskAssessment
    proposed_actions: list[ProposedAction]
    approval: Approval
    action_results: list[ToolResult]
    status: str
    trace: Annotated[list[TraceEntry], operator.add]
