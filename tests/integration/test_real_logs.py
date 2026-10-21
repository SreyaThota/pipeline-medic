"""Regression check: the parser handles every real CI log in the dataset."""

import csv
from pathlib import Path

import pytest

from app.ingestion import parse_log

LOGS = Path(__file__).resolve().parents[2] / "data" / "sample_logs"
ROWS = list(csv.DictReader((LOGS / "index.csv").open(encoding="utf-8")))


@pytest.mark.parametrize("row", ROWS, ids=[row["log_id"] for row in ROWS])
def test_real_log_parses_with_valid_evidence(row):
    text = (LOGS / row["source"] / f"{row['log_id']}.log").read_text(encoding="utf-8")
    parsed = parse_log(text)

    assert parsed.format == "github_actions"
    assert parsed.line_count == len(text.splitlines())
    assert 0 < len(parsed.tail) <= 15
    for region in parsed.regions:
        assert 1 <= region.start_line <= region.anchor_line <= region.end_line <= parsed.line_count
        assert [line.number for line in region.lines] == list(
            range(region.start_line, region.end_line + 1)
        )
        assert not any(line.noise for line in region.lines)
