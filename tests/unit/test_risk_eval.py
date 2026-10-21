"""v0.5 data handling and metrics (no model needed)."""

from collections import Counter

import pytest

from evaluation.run_risk_eval import _bootstrap, _metrics
from ml.lora_finetune.data import LEVELS, load_examples, risk_input_text


@pytest.fixture(scope="module")
def examples():
    return load_examples()


def test_splits_and_synthetic_examples_are_kept_apart(examples):
    splits = Counter(e.split for e in examples)
    assert splits == {"dev": 47, "test": 64, "synthetic": 30}
    assert all(e.synthetic == (e.split == "synthetic") for e in examples)
    assert {e.label for e in examples} == set(LEVELS)


def test_no_test_log_is_in_the_training_set(examples):
    train_ids = {e.example_id for e in examples if e.split in ("dev", "synthetic")}
    test_ids = {e.example_id for e in examples if e.split == "test"}
    assert train_ids.isdisjoint(test_ids)


def test_input_text_is_workflow_then_tail(examples):
    real = next(e for e in examples if e.split == "dev")
    first, *rest = real.text.splitlines()
    assert first.startswith("workflow: ")
    assert 0 < len(rest) <= 15
    assert risk_input_text(None, ["a", "b"]) == "workflow: unknown\na\nb"


def test_metrics():
    m = _metrics(["low", "medium", "high", "high"], ["low", "high", "high", "medium"])
    assert m["accuracy"] == 0.5
    assert m["per_class"]["high"] == {"precision": 0.5, "recall": 0.5, "f1": 0.5, "support": 2}
    assert m["confusion"]["high"] == {"high": 1, "medium": 1}


def test_bootstrap_interval_contains_the_mean():
    result = _bootstrap([1.0, 1.0, 0.0, 1.0], [0.0, 1.0, 0.0, 0.0])
    assert result["mean_difference"] == 0.5
    assert result["ci95_low"] <= 0.5 <= result["ci95_high"]
