"""Training/test examples for the risk classifier, from the frozen label files."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from app.ingestion import parse_log

ROOT = Path(__file__).resolve().parents[2]
LABELS = ROOT / "data" / "risk_labels" / "risk_labels.csv"
SYNTHETIC = ROOT / "data" / "risk_labels" / "synthetic_train.jsonl"
LOG_DIR = ROOT / "data" / "sample_logs"
LEVELS = ("low", "medium", "high")


@dataclass
class Example:
    example_id: str
    text: str
    label: str
    split: str          # "dev", "test", or "synthetic"
    repo: str | None
    synthetic: bool


def risk_input_text(workflow: str | None, tail_lines: list[str]) -> str:
    """The classifier's input: workflow name, then the log's last lines."""
    return f"workflow: {workflow or 'unknown'}\n" + "\n".join(tail_lines)


def load_examples() -> list[Example]:
    examples = []
    with LABELS.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = (LOG_DIR / "oss" / f"{row['log_id']}.log").read_text(encoding="utf-8")
            tail = [line.text for line in parse_log(raw).tail]
            examples.append(Example(row["log_id"], risk_input_text(row["workflow"], tail),
                                    row["risk_level"], row["split"], row["repo"], False))
    for line in SYNTHETIC.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        examples.append(Example(item["id"], risk_input_text(item["workflow"], item["text"].splitlines()),
                                item["risk_level"], "synthetic", None, True))
    return examples
