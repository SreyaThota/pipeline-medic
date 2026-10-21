import json

import pytest

from app.observability.tracing import Tracer, get_tracer, summarize


def test_span_records_duration_status_and_writes_jsonl(tmp_path):
    tracer = Tracer(tmp_path / "traces.jsonl")
    with tracer.span("parse", "stage", trace_id="run1", lines=10) as span:
        span.attrs["regions"] = 2

    written = [json.loads(line) for line in (tmp_path / "traces.jsonl").read_text().splitlines()]
    assert len(written) == 1
    assert written[0]["name"] == "parse" and written[0]["status"] == "ok"
    assert written[0]["attrs"] == {"lines": 10, "regions": 2}
    assert written[0]["duration_ms"] >= 0


def test_exception_marks_the_span_as_error_and_still_exports(tmp_path):
    tracer = Tracer(tmp_path / "traces.jsonl")
    with pytest.raises(ValueError), tracer.span("diagnose", "stage", trace_id="run1"):
        raise ValueError("boom")
    assert tracer.spans[0].status == "error"
    assert tracer.spans[0].attrs["error"] == "ValueError"


def test_one_tracer_per_runtime_dir(tmp_path):
    assert get_tracer(tmp_path) is get_tracer(tmp_path)
    assert get_tracer(tmp_path) is not get_tracer(tmp_path / "other")


def test_summary_latency_and_tool_success_rate():
    spans = [
        {"trace_id": "r1", "name": "parse", "kind": "stage", "duration_ms": 10.0, "status": "ok"},
        {"trace_id": "r2", "name": "parse", "kind": "stage", "duration_ms": 30.0, "status": "ok"},
        {"trace_id": "r1", "name": "create_ticket", "kind": "tool", "duration_ms": 2.0,
         "status": "dry_run"},
        {"trace_id": "r1", "name": "create_ticket", "kind": "tool", "duration_ms": 3.0,
         "status": "executed"},
        {"trace_id": "r2", "name": "create_ticket", "kind": "tool", "duration_ms": 1.0,
         "status": "failed"},
        {"trace_id": "r2", "name": "notify", "kind": "tool", "duration_ms": 1.0,
         "status": "rejected"},
    ]
    summary = summarize(spans)
    assert summary["stages"]["parse"]["count"] == 2
    assert summary["stages"]["parse"]["p95_ms"] == 30.0
    ticket = summary["tools"]["create_ticket"]
    assert ticket["calls"] == 3 and ticket["success_rate"] == round(2 / 3, 3)
    assert summary["tools"]["notify"]["success_rate"] == 0.0
    assert summary["traces"] == 2
