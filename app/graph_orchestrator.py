"""The Pipeline Medic agent graph (v0.4), built with LangGraph.

    parse → diagnose → classify_risk → propose_actions
          ─(no actions)→ END ("resolved_no_action")
          ─(actions)──→ human_approval  ⏸ interrupt: waits for a person
                        → execute_actions → END

- Checkpointed: the state after every node is saved under the run's thread
  id, so a run paused at `human_approval` can be resumed later, even by a new
  process sharing the same checkpointer.
- Nothing executes without a human decision. `human_approval` calls
  LangGraph's `interrupt()`; `resume()` supplies the decision. A rejection is
  written to the audit log and no tool is called.
- Secrets are redacted before the log enters the state (CLAUDE.md 2F), so no
  checkpoint holds one.
- Every node appends a `TraceEntry` (stage, status, start, duration).

Usage:
    graph = PipelineMedicGraph.default(settings)
    paused = graph.start(log_text)             # status "awaiting_approval"
    done = graph.resume(paused["run_id"], Approval(approved=True, approver="sreya"))
"""

import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.errors import GraphBubbleUp
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from agents.action_agent import ActionAgent
from agents.diagnosis_agent import DiagnosisAgent
from agents.parser_agent import ParserAgent
from agents.risk_classifier import PromptedRiskClassifier
from app.config import Settings
from app.graph import Approval, PipelineMedicState, ToolResult, TraceEntry
from app.observability.tracing import Tracer, get_tracer
from app.redaction import redact_lines
from rag.retrieve import Retriever

# LangGraph's node type is a strict protocol; wrapped nodes cross that boundary as Any.
Node = Any
StageFn = Callable[[PipelineMedicState], tuple[dict[str, Any], str, dict[str, Any]]]


def _traced(stage: str, node: StageFn, tracer: Tracer) -> Node:
    """Wrap a node so it appends one TraceEntry to the state and exports one
    tracing span (v0.7). The node returns (state update, status, detail);
    exceptions are recorded, then re-raised. The span is keyed by run id and
    carries only the detail dict (counts, labels, line numbers, never log text)."""

    def wrapped(state: PipelineMedicState) -> dict[str, Any]:
        started = datetime.now(UTC).isoformat()
        t0 = time.perf_counter()
        with tracer.span(stage, "stage", trace_id=state["run_id"]) as span:
            try:
                update, status, detail = node(state)
            except GraphBubbleUp:
                span.status = "paused"  # interrupt(): waiting for a human, not an error
                raise  # LangGraph control flow
            except Exception as exc:
                entry = TraceEntry(stage=stage, status="error", started_at=started,
                                   duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                                   detail={"error": type(exc).__name__})
                raise _StageFailed(entry) from exc
            span.status = status
            span.attrs.update(detail)
        entry = TraceEntry(stage=stage, status=status, started_at=started,  # type: ignore[arg-type]
                           duration_ms=round((time.perf_counter() - t0) * 1000, 2), detail=detail)
        return {**update, "trace": [entry]}

    wrapped.__name__ = stage
    return wrapped


# The only types a checkpoint may deserialise (LangGraph blocks others by default
# in future versions). Keep in sync with PipelineMedicState.
CHECKPOINT_TYPES = [
    ("app.graph", name) for name in
    ("TraceEntry", "Diagnosis", "Evidence", "SimilarIncident", "RiskAssessment",
     "ProposedAction", "ToolResult", "Approval")
] + [("app.schemas.logs", name) for name in
     ("ParsedLog", "LogLine", "FailureRegion", "ExitCode", "RedactionReport")]


def make_checkpointer() -> InMemorySaver:
    """In-memory checkpointer that only deserialises Pipeline Medic state types."""
    return InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=CHECKPOINT_TYPES))


class _StageFailed(RuntimeError):
    def __init__(self, entry: TraceEntry):
        super().__init__(f"stage {entry.stage} failed: {entry.detail.get('error')}")
        self.entry = entry


class PipelineMedicGraph:
    def __init__(
        self,
        parser: ParserAgent,
        diagnoser: DiagnosisAgent,
        classifier: PromptedRiskClassifier,
        actor: ActionAgent,
        checkpointer: Any = None,
    ):
        self.parser = parser
        self.diagnoser = diagnoser
        self.classifier = classifier
        self.actor = actor
        self.checkpointer = checkpointer or make_checkpointer()
        self.tracer = get_tracer(actor.settings.runtime_dir)
        self.graph = self._build()

    @classmethod
    def default(cls, settings: Settings, retriever: Retriever | None = None) -> PipelineMedicGraph:
        """Production wiring. Without a retriever the diagnosis has no
        category and the Action Agent routes the failure to human triage."""
        return cls(ParserAgent(), DiagnosisAgent(retriever), PromptedRiskClassifier(settings),
                   ActionAgent(settings))

    # --- nodes ---------------------------------------------------------------

    def _parse(self, state: PipelineMedicState) -> tuple[dict[str, Any], str, dict[str, Any]]:
        parsed = self.parser.run(state["log_text"])
        return ({"parsed": parsed}, "ok",
                {"format": parsed.format, "lines": parsed.line_count,
                 "regions": len(parsed.regions), "flags": parsed.flags})

    def _diagnose(self, state: PipelineMedicState) -> tuple[dict[str, Any], str, dict[str, Any]]:
        diagnosis = self.diagnoser.run(state["parsed"], exclude_log_id=state.get("source_log_id"))
        status = "ok" if diagnosis.category else "fallback"
        return ({"diagnosis": diagnosis}, status,
                {"category": diagnosis.category, "confidence": diagnosis.confidence,
                 "method": diagnosis.method, "evidence_lines": [e.line for e in diagnosis.evidence]})

    def _classify(self, state: PipelineMedicState) -> tuple[dict[str, Any], str, dict[str, Any]]:
        risk = self.classifier.run(state["diagnosis"], workflow=state.get("workflow"))
        status = "ok" if risk.method == "prompted_llm" else "fallback"
        detail: dict[str, Any] = {"level": risk.level, "method": risk.method}
        if self.classifier.last_error:
            detail["error"] = self.classifier.last_error
        return {"risk": risk}, status, detail

    def _propose(self, state: PipelineMedicState) -> tuple[dict[str, Any], str, dict[str, Any]]:
        actions = self.actor.propose(state["diagnosis"], state["risk"],
                                     log_ref=state.get("source_log_id"))
        status_value = "awaiting_approval" if actions else "resolved_no_action"
        return ({"proposed_actions": actions, "status": status_value}, "ok",
                {"tools": [a.tool for a in actions]})

    def _approve(self, state: PipelineMedicState) -> tuple[dict[str, Any], str, dict[str, Any]]:
        decision = interrupt({
            "run_id": state["run_id"],
            "proposed_actions": [a.model_dump() for a in state["proposed_actions"]],
        })
        approval = Approval.model_validate(decision)
        return ({"approval": approval}, "ok",
                {"approved": approval.approved, "approver": approval.approver})

    def _execute(self, state: PipelineMedicState) -> tuple[dict[str, Any], str, dict[str, Any]]:
        approval = state["approval"]
        results: list[ToolResult] = []
        for action in state["proposed_actions"]:
            if approval.approved:
                results.append(self.actor.execute(action, approved=True, trace_id=state["run_id"]))
            else:
                self.actor.audit.record(action.action_id, action.tool, "rejected_by_human",
                                        approver=approval.approver, note=approval.note)
                results.append(ToolResult(action_id=action.action_id, tool=action.tool,
                                          status="rejected", dry_run=True,
                                          proposal=action.arguments,
                                          error=f"rejected by {approval.approver}"))
        final = "completed" if approval.approved else "rejected"
        return ({"action_results": results, "status": final}, "ok",
                {"statuses": [r.status for r in results]})

    def _build(self) -> Any:
        builder = StateGraph(PipelineMedicState)
        builder.add_node("parse", _traced("parse", self._parse, self.tracer))
        builder.add_node("diagnose", _traced("diagnose", self._diagnose, self.tracer))
        builder.add_node("classify_risk", _traced("classify_risk", self._classify, self.tracer))
        builder.add_node("propose_actions", _traced("propose_actions", self._propose, self.tracer))
        builder.add_node("human_approval", _traced("human_approval", self._approve, self.tracer))
        builder.add_node("execute_actions", _traced("execute_actions", self._execute, self.tracer))
        builder.add_edge(START, "parse")
        builder.add_edge("parse", "diagnose")
        builder.add_edge("diagnose", "classify_risk")
        builder.add_edge("classify_risk", "propose_actions")
        builder.add_conditional_edges(
            "propose_actions",
            lambda state: "human_approval" if state["proposed_actions"] else END,
            ["human_approval", END],
        )
        builder.add_edge("human_approval", "execute_actions")
        builder.add_edge("execute_actions", END)
        return builder.compile(checkpointer=self.checkpointer)

    # --- public API ------------------------------------------------------------

    @staticmethod
    def _config(run_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": run_id}}

    def start(
        self, log_text: str, source_log_id: str | None = None, workflow: str | None = None,
        run_id: str | None = None,
    ) -> PipelineMedicState:
        """Run until the human-approval pause (or the end, if nothing to do)."""
        run_id = run_id or uuid.uuid4().hex
        redacted = "\n".join(redact_lines(log_text.splitlines()).lines)
        initial: PipelineMedicState = {
            "run_id": run_id, "log_text": redacted, "source_log_id": source_log_id,
            "workflow": workflow, "status": "running", "trace": [],
        }
        self.graph.invoke(initial, self._config(run_id))
        return self.state(run_id)

    def resume(self, run_id: str, approval: Approval) -> PipelineMedicState:
        """Give the human decision to a paused run and finish it."""
        if not self.is_paused(run_id):
            raise RuntimeError(f"run {run_id} is not waiting for approval")
        self.graph.invoke(Command(resume=approval.model_dump()), self._config(run_id))
        return self.state(run_id)

    def state(self, run_id: str) -> PipelineMedicState:
        snapshot = self.graph.get_state(self._config(run_id))
        return snapshot.values  # type: ignore[no-any-return]

    def is_paused(self, run_id: str) -> bool:
        snapshot = self.graph.get_state(self._config(run_id))
        return "human_approval" in snapshot.next
