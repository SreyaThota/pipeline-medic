"""Non-UI helpers of the Streamlit demo (demo/helpers.py)."""

import csv

from app.graph import Diagnosis, RiskAssessment, TraceEntry
from app.redaction import redact_lines
from demo.helpers import (
    EXAMPLE_IDS,
    INDEX_CSV,
    demo_settings,
    evidence_window,
    load_examples,
    redaction_example,
    redaction_summary,
    rubric_reason,
    stage_latency,
)


def test_examples_are_five_real_reviewed_logs_from_five_repos():
    examples = load_examples()
    assert [e.log_id for e in examples] == EXAMPLE_IDS
    assert len({e.repo for e in examples}) == 5
    with INDEX_CSV.open(newline="", encoding="utf-8") as f:
        rows = {r["log_id"]: r for r in csv.DictReader(f)}
    for e in examples:
        assert rows[e.log_id]["label_status"] == "reviewed"
        assert e.run_url.startswith("https://github.com/")
        assert e.path.is_file() and e.text().strip()


def test_examples_fit_the_log_size_limit():
    limit = demo_settings().max_log_chars
    assert all(len(e.text()) <= limit for e in load_examples())


def test_demo_settings_never_enable_real_actions(monkeypatch):
    monkeypatch.setenv("ACTIONS_ENABLED", "true")
    assert demo_settings().actions_enabled is False


def test_redaction_example_is_fully_redacted():
    text = redaction_example()
    assert redaction_summary(text) == {"github_token": 1, "aws_access_key_id": 1}
    redacted = "\n".join(redact_lines(text.splitlines()).lines)
    assert "[REDACTED:github_token]" in redacted
    assert "[REDACTED:aws_access_key_id]" in redacted
    assert "Demo0nly" not in redacted


def test_evidence_window_marks_evidence_with_original_line_numbers():
    text = "\n".join(f"line {n}" for n in range(1, 21))
    window = evidence_window(text, [5, 15], context=1).splitlines()
    assert window == [
        "   4 | line 4", ">  5 | line 5", "   6 | line 6", "...",
        "  14 | line 14", "> 15 | line 15", "  16 | line 16",
    ]


def test_evidence_window_clips_at_log_edges_and_long_lines():
    text = "first\n" + "x" * 500
    window = evidence_window(text, [1, 2], context=3, max_width=10).splitlines()
    assert window[0] == "> 1 | first"
    assert window[1] == "> 2 | xxxxxxxxxx …"


def test_evidence_window_without_evidence_is_empty():
    assert evidence_window("a\nb", []) == ""


def test_stage_latency_maps_stage_to_ms():
    trace = [TraceEntry(stage="parse", status="ok", started_at="t", duration_ms=1.5),
             TraceEntry(stage="diagnose", status="ok", started_at="t", duration_ms=20.0)]
    assert stage_latency(trace) == {"parse": 1.5, "diagnose": 20.0}


def test_rubric_reason_is_one_line_from_structured_fields():
    diagnosis = Diagnosis(category="build_compile", confidence=0.6, summary="s", method="m")
    risk = RiskAssessment(level="high", rationale="rubric v1: ...", method="rubric")
    reason = rubric_reason({"risk": risk, "diagnosis": diagnosis, "workflow": "Loom"})
    assert reason == "Rubric v1 maps category `build_compile` in workflow “Loom” to **high** risk."
    assert "\n" not in reason
    unknown = Diagnosis(category=None, confidence=0.0, summary="s", method="m")
    risk = RiskAssessment(level="medium", rationale="r", method="rubric")
    assert "`unknown`" in rubric_reason({"risk": risk, "diagnosis": unknown})


def test_evidence_window_strips_github_actions_columns():
    text = "\n".join(f"build\tRun tests\t2026-10-11T12:00:0{n}.000Z message {n}" for n in range(1, 4))
    window = evidence_window(text, [2], log_format="github_actions", context=1)
    assert window.splitlines() == ["  1 | message 1", "> 2 | message 2", "  3 | message 3"]
