import pytest

from rag.ingest import chunk_log, clean_log


def test_clean_log_strips_gh_prefix_timestamp_ansi_and_groups():
    raw = (
        "build\tRun tests\t﻿2026-08-05T11:06:45.7866481Z ##[group]Run pytest\n"
        "build\tRun tests\t2026-08-05T11:06:46.1Z \x1b[31mFAILED\x1b[0m test_a.py::test_x\n"
        "build\tRun tests\t2026-08-05T11:06:46.2Z \n"
        "build\tRun tests\t2026-08-05T11:06:47Z ##[error]Process completed with exit code 1."
    )
    assert clean_log(raw).splitlines() == [
        "Run pytest",
        "FAILED test_a.py::test_x",
        "##[error]Process completed with exit code 1.",
    ]


def test_clean_log_strips_caret_notation_ansi():
    raw = "job	step	2026-09-02T17:32:10.2171299Z ^[[1m^[[91merror^[[0m: could not compile"
    assert clean_log(raw) == "error: could not compile"


def test_clean_log_drops_post_job_cleanup_per_job():
    raw = (
        "lint\tUNKNOWN STEP\t2026-09-07T02:48:37Z ruff found 2 errors\n"
        "lint\tUNKNOWN STEP\t2026-09-07T02:48:38Z Post job cleanup.\n"
        "lint\tUNKNOWN STEP\t2026-09-07T02:48:39Z [command]/usr/bin/git config --local --unset-all\n"
        "lint\tUNKNOWN STEP\t2026-09-07T02:48:40Z Cleaning up orphan processes\n"
        "test\tUNKNOWN STEP\t2026-09-07T02:49:00Z FAILED tests/test_x.py::test_y\n"
    )
    assert clean_log(raw).splitlines() == ["ruff found 2 errors", "FAILED tests/test_x.py::test_y"]


def test_chunk_whole_and_tail():
    text = "\n".join(f"line {i}" for i in range(40))
    assert chunk_log(text, "whole") == [text]
    assert chunk_log(text, "tail", window=3) == ["line 37\nline 38\nline 39"]


def test_chunk_window_overlaps_and_covers_every_line():
    text = "\n".join(f"line {i}" for i in range(40))
    chunks = chunk_log(text, "window", window=15, overlap=5)
    assert chunks[0].splitlines()[0] == "line 0"
    assert chunks[1].splitlines()[0] == "line 10"
    assert chunks[-1].splitlines()[-1] == "line 39"
    covered = {line for c in chunks for line in c.splitlines()}
    assert len(covered) == 40


def test_chunk_empty_and_unknown_strategy():
    assert chunk_log("", "window") == []
    with pytest.raises(ValueError):
        chunk_log("x", "semantic")
