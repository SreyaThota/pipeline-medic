from pathlib import Path

from app.ingestion import MAX_LINE_CHARS, parse_log
from app.ingestion.regions import MAX_REGIONS

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"


def test_python_traceback_becomes_one_stack_trace_region():
    parsed = parse_log((FIXTURES / "github_actions_pytest.log").read_text(encoding="utf-8"))
    trace = next(r for r in parsed.regions if r.kind == "stack_trace")
    assert (trace.start_line, trace.end_line) == (8, 11)
    assert trace.anchor_line == 11
    assert trace.lines[-1].text == "AssertionError: expected 200, got 401"


def test_test_summary_and_exit_code_regions():
    parsed = parse_log((FIXTURES / "github_actions_pytest.log").read_text(encoding="utf-8"))
    kinds = {r.kind for r in parsed.regions}
    assert {"test_summary", "exit_code", "error"} <= kinds
    summary = next(r for r in parsed.regions if r.kind == "test_summary")
    assert "1 failed, 7 passed" in summary.lines[0].text


def test_post_job_cleanup_is_noise_and_excluded():
    parsed = parse_log((FIXTURES / "github_actions_pytest.log").read_text(encoding="utf-8"))
    assert all(line.number < 16 for line in parsed.tail)
    assert all(line.number < 16 for region in parsed.regions for line in region.lines)


def test_error_context_window_and_merging():
    log = "\n".join(["setup"] * 5 + ["ERROR: first", "between", "ERROR: second"] + ["after"] * 5)
    parsed = parse_log(log, context=1)
    errors = [r for r in parsed.regions if r.kind == "error"]
    assert len(errors) == 1  # windows 5-7 and 7-9 merge
    assert (errors[0].start_line, errors[0].end_line) == (5, 9)


def test_tail_window_matches_v02_baseline_size():
    parsed = parse_log("\n".join(f"line {i}" for i in range(1, 41)))
    assert [line.number for line in parsed.tail] == list(range(26, 41))
    assert parse_log("a\nb", tail_lines=0).tail == []


def test_logs_without_error_evidence_are_flagged():
    parsed = parse_log("Installing dependencies\nDone in 3s")
    assert parsed.regions == []
    assert "no_error_markers_found" in parsed.flags


def test_region_cap_keeps_the_last_regions():
    log = "\n".join(f"ERROR: failure {i}\n" + "filler\n" * 8 for i in range(MAX_REGIONS + 5))
    parsed = parse_log(log, context=0)
    assert len(parsed.regions) == MAX_REGIONS
    assert "regions_truncated" in parsed.flags
    assert parsed.regions[-1].lines[0].text == f"ERROR: failure {MAX_REGIONS + 4}"


def test_very_long_lines_are_clipped_and_flagged():
    parsed = parse_log("x" * (MAX_LINE_CHARS + 500) + "\nERROR: done")
    assert "long_lines_truncated" in parsed.flags
    assert all(len(line.text) <= MAX_LINE_CHARS for line in parsed.tail)
