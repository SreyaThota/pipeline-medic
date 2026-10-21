from pathlib import Path

import pytest

from app.ingestion import parse_log
from app.ingestion.formats import detect_format

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("github_actions_pytest.log", "github_actions"),
        ("github_actions_raw.log", "github_actions"),
        ("jenkins_maven.log", "jenkins"),
        ("text_vite_build.log", "text"),
    ],
)
def test_format_detection(name, expected):
    assert detect_format(fixture(name).splitlines()) == expected


def test_github_columns_timestamps_and_markers():
    parsed = parse_log(fixture("github_actions_pytest.log"))
    assert parsed.jobs == ["test (3.12)"]
    last_error = parsed.exit_codes[-1]
    assert (last_error.line, last_error.code) == (15, 1)
    tail_line = next(line for line in parsed.tail if line.number == 15)
    assert tail_line.text == "Process completed with exit code 1."  # ##[error] marker stripped
    assert tail_line.severity == "error"
    assert tail_line.step == "Run tests"
    assert tail_line.timestamp is not None and tail_line.timestamp.isoformat().startswith(
        "2026-10-20T09:15:10"
    )


def test_raw_github_log_without_columns():
    parsed = parse_log(fixture("github_actions_raw.log"))
    assert parsed.format == "github_actions"
    assert parsed.jobs == []
    severities = {line.number: line.severity for line in parsed.tail}
    assert severities[4] == "error"    # npm ERR!
    assert severities[7] == "warning"  # ##[warning]


def test_jenkins_stage_becomes_the_step():
    parsed = parse_log(fixture("jenkins_maven.log"))
    assert parsed.format == "jenkins"
    assert "Test" in parsed.failed_steps
    surefire = next(line for line in parsed.tail if "Failures: 2" in line.text)
    assert surefire.step == "Test"
    assert surefire.text.startswith("[ERROR] Tests run: 120")  # Timestamper prefix removed
    assert parsed.exit_codes[-1].code == 1


def test_plain_text_and_forced_format():
    parsed = parse_log(fixture("text_vite_build.log"))
    assert parsed.format == "text" and parsed.format_detected
    forced = parse_log(fixture("text_vite_build.log"), fmt="jenkins")
    assert forced.format == "jenkins"
    assert "format_forced" in forced.flags


def test_crlf_and_trailing_newline_keep_line_numbers():
    parsed = parse_log("ok\r\nstill ok\r\nERROR: boom\r\n")
    assert parsed.line_count == 3
    assert parsed.regions[0].anchor_line == 3
