"""Typed state shared by the agents (CLAUDE.md section 1).

v0.3 defines what the Action Agent consumes and produces: the diagnosis and
risk assessment it reads, and the `ProposedAction` it emits. v0.4 adds the
LangGraph state (`PipelineMedicState`) that carries these between agents.
"""

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

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
