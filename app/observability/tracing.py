"""Tracing (v0.7): per-stage latency and tool-call outcomes.

Two kinds of span, written one JSON object per line to
`<RUNTIME_DIR>/traces.jsonl`:

    stage   one graph node (parse, diagnose, ...); trace_id = the run id
    tool    one MCP tool call; carries the action_id, so it links to the
            audit log entry for the same call (CLAUDE.md 2F)

Span attributes never contain log text or tool arguments, only identifiers,
counts and outcomes, so traces cannot leak what redaction removed.

Summarise a trace file:

    python -m app.observability.tracing var/traces.jsonl
"""

import argparse
import json
import threading
import time
import uuid
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

TRACE_FILE = "traces.jsonl"
SpanKind = Literal["stage", "tool"]
# Tool outcomes that mean the call did what it was asked to do.
TOOL_SUCCESS = {"executed", "dry_run"}


@dataclass
class Span:
    trace_id: str
    name: str
    kind: SpanKind
    started_at: str
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    duration_ms: float = 0.0
    status: str = "ok"
    attrs: dict[str, Any] = field(default_factory=dict)


class Tracer:
    """Collects spans in memory and appends them to a JSONL file."""

    def __init__(self, path: Path | None = None):
        self.path = path
        self.spans: list[Span] = []
        self._lock = threading.Lock()

    @contextmanager
    def span(self, name: str, kind: SpanKind, trace_id: str, **attrs: Any) -> Iterator[Span]:
        span = Span(trace_id=trace_id, name=name, kind=kind,
                    started_at=datetime.now(UTC).isoformat(), attrs=dict(attrs))
        start = time.perf_counter()
        try:
            yield span
        except BaseException as exc:
            if span.status == "ok":
                span.status = "error"
                span.attrs["error"] = type(exc).__name__
            raise
        finally:
            span.duration_ms = round((time.perf_counter() - start) * 1000, 2)
            self._export(span)

    def _export(self, span: Span) -> None:
        with self._lock:
            self.spans.append(span)
            if self.path is not None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(asdict(span), default=str) + "\n")


_TRACERS: dict[str, Tracer] = {}
_TRACERS_LOCK = threading.Lock()


def get_tracer(runtime_dir: str | Path) -> Tracer:
    """One tracer per runtime directory, writing to <runtime_dir>/traces.jsonl."""
    key = str(Path(runtime_dir).resolve())
    with _TRACERS_LOCK:
        if key not in _TRACERS:
            _TRACERS[key] = Tracer(Path(runtime_dir) / TRACE_FILE)
        return _TRACERS[key]


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))] if ordered else 0.0


def summarize(spans: list[dict[str, Any]]) -> dict[str, Any]:
    """Latency per stage and outcome counts per tool."""
    stage_ms: dict[str, list[float]] = defaultdict(list)
    stage_status: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    tool_status: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    tool_ms: dict[str, list[float]] = defaultdict(list)
    for span in spans:
        if span["kind"] == "stage":
            stage_ms[span["name"]].append(span["duration_ms"])
            stage_status[span["name"]][span["status"]] += 1
        else:
            tool_ms[span["name"]].append(span["duration_ms"])
            tool_status[span["name"]][span["status"]] += 1
    tools = {}
    for name, counts in tool_status.items():
        calls = sum(counts.values())
        ok = sum(n for status, n in counts.items() if status in TOOL_SUCCESS)
        tools[name] = {"calls": calls, **counts, "success_rate": round(ok / calls, 3),
                       "p50_ms": _percentile(tool_ms[name], 0.5)}
    return {
        "stages": {name: {"count": len(ms), "p50_ms": _percentile(ms, 0.5),
                          "p95_ms": _percentile(ms, 0.95), **stage_status[name]}
                   for name, ms in stage_ms.items()},
        "tools": tools,
        "traces": len({s["trace_id"] for s in spans}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarise a Pipeline Medic trace file.")
    parser.add_argument("path", type=Path)
    path = parser.parse_args().path
    spans = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    print(json.dumps(summarize(spans), indent=2))


if __name__ == "__main__":
    main()
