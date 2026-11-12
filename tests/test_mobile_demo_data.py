"""Checks on the exported data behind the static mobile demo (demo/public)."""

import json
from pathlib import Path

import pytest

from app.redaction import redact_lines
from demo import build_demo_data as build

PUBLIC = Path(build.__file__).resolve().parent / "public"


@pytest.fixture(scope="module")
def runs() -> list[dict]:
    return json.loads((PUBLIC / "runs.json").read_text(encoding="utf-8"))["runs"]


def test_runs_are_the_chosen_held_out_logs(runs: list[dict]) -> None:
    assert [r["log_id"] for r in runs] == build.RUN_IDS
    assert all(r["split"] == "test" for r in runs)
    assert len({r["repo"] for r in runs}) == len({r["label"] for r in runs}) == 5


def test_four_correct_one_wrong(runs: list[dict]) -> None:
    correct = [r["diagnosis"]["correct"] for r in runs]
    assert correct.count(True) == 4 and correct.count(False) == 1
    assert all(r["diagnosis"]["correct"] == (r["diagnosis"]["category"] == r["label"]) for r in runs)


def test_approved_actions_were_dry_runs_only(runs: list[dict]) -> None:
    for run in runs:
        for result in run["approval"].get("results", []):
            assert result["dry_run"] is True and result["status"] == "dry_run"


def test_evidence_lines_are_in_the_excerpt(runs: list[dict]) -> None:
    for run in runs:
        shown = {line["line"] for line in run["excerpt"]}
        assert {e["line"] for e in run["evidence"]} <= shown


def test_exported_runs_hold_no_secrets_or_emails(runs: list[dict]) -> None:
    text = json.dumps(runs, ensure_ascii=False)
    assert redact_lines(text.splitlines()).by_kind == {}
    assert build.EMAIL.findall(text) == []


def test_metrics_match_the_result_files_and_readme() -> None:
    committed = json.loads((PUBLIC / "metrics.json").read_text(encoding="utf-8"))
    assert committed == build.build_metrics()
    build.check_against_readme(committed)  # raises SystemExit on any mismatch
