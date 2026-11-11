"""Non-UI helpers for the Streamlit demo (demo/app.py), kept here so they are
unit-tested without Streamlit.

The demo runs the default graph: parse → diagnose (flat-RAG vote) → risk
(rubric v1, no LLM) → propose → human approval → execute. Execution is always
a dry run in the demo.
"""

import csv
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings, get_settings
from app.graph import PipelineMedicState, TraceEntry
from app.ingestion.formats import PARSERS
from app.redaction import redact_lines

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "data" / "sample_logs"
INDEX_CSV = LOG_DIR / "index.csv"
REPO_URL = "https://github.com/SreyaThota/pipeline-medic"
EXPERIMENTS_URL = f"{REPO_URL}/tree/main/experiments"

# Five real failed runs from five repositories, chosen for variety: three
# risk levels, one run that needs no action, and one where the diagnosis is
# wrong (diagnosis is the weakest stage; see experiment 004).
EXAMPLE_IDS = [
    "tokio-rs__tokio__38134725610",
    "home-assistant__core__38223769150",
    "astral-sh__ruff__33829682997",
    "scikit-learn__scikit-learn__38220142959",
    "numpy__numpy__38197650837",
]

STAGES = ["parse", "diagnose", "classify_risk", "propose_actions",
          "human_approval", "execute_actions"]

FLOW_DIAGRAM = """flowchart TD
    A[CI log] --> R[Redact secrets]
    R --> P[Parse]
    P --> D[Diagnose]
    D --> K[Risk rubric]
    K --> X{Action?}
    X -- no --> E1[Done]
    X -- yes --> H[Human approval]
    H -- approve --> T[Tools: dry run]
    H -- reject --> J[Rejected]
"""


@dataclass(frozen=True)
class Example:
    log_id: str
    repo: str
    workflow: str
    run_url: str
    label: str
    path: Path

    @property
    def title(self) -> str:
        return f"{self.repo}: {self.workflow}"

    def text(self) -> str:
        return self.path.read_text(encoding="utf-8", errors="replace")


def load_examples(ids: list[str] = EXAMPLE_IDS, index_csv: Path = INDEX_CSV) -> list[Example]:
    """Metadata for the bundled example logs, in the order of `ids`."""
    with index_csv.open(newline="", encoding="utf-8") as f:
        rows = {row["log_id"]: row for row in csv.DictReader(f)}
    examples = []
    for log_id in ids:
        row = rows[log_id]
        examples.append(Example(
            log_id=log_id, repo=row["repo"], workflow=row["workflow"], run_url=row["run_url"],
            label=row["label"], path=index_csv.parent / row["source"] / f"{log_id}.log",
        ))
    return examples


def redaction_example() -> str:
    """A short synthetic log with fake credentials, to show redaction.

    The fake values are assembled at runtime so no token-shaped string sits
    in the repository (secret scanners would flag it)."""
    fake_github = "gh" + "p_" + "Demo0nlyNotARealToken" + "x" * 16
    fake_aws = "AK" + "IA" + "DEMO" + "0" * 12
    return "\n".join([
        "Run ./scripts/publish.sh",
        f"Using GITHUB_TOKEN={fake_github}",
        f"aws configure set aws_access_key_id {fake_aws}",
        "Uploading dist/pkg-1.0.0.tar.gz",
        "ERROR: HTTP 403 Forbidden: the token does not have write access",
        "Error: Process completed with exit code 1.",
    ])


def demo_settings() -> Settings:
    """Demo settings: a private temp runtime dir, and real actions always off."""
    runtime_dir = tempfile.mkdtemp(prefix="pipeline-medic-demo-")
    return get_settings().model_copy(update={"runtime_dir": runtime_dir,
                                             "actions_enabled": False})


def redaction_summary(log_text: str) -> dict[str, int]:
    """Count of redacted secrets by kind (values are never returned)."""
    return redact_lines(log_text.splitlines()).by_kind


def evidence_window(redacted_text: str, evidence_lines: list[int], log_format: str = "text",
                    context: int = 2, max_width: int = 160) -> str:
    """Evidence lines with surrounding context, numbered as in the original
    log. Evidence lines are marked with '>'; gaps are shown as '...'.

    Lines are shown as the parser normalised them (for GitHub Actions logs,
    without the job, step and timestamp columns)."""
    lines = [raw.text for raw in PARSERS[log_format](redacted_text.splitlines())]
    wanted: set[int] = set()
    for n in evidence_lines:
        wanted.update(range(max(1, n - context), min(len(lines), n + context) + 1))
    out: list[str] = []
    previous = 0
    width = len(str(max(wanted))) if wanted else 1
    for n in sorted(wanted):
        if previous and n > previous + 1:
            out.append("...")
        marker = ">" if n in evidence_lines else " "
        text = lines[n - 1]
        if len(text) > max_width:
            text = text[:max_width] + " …"
        out.append(f"{marker} {n:>{width}} | {text}")
        previous = n
    return "\n".join(out)


def stage_latency(trace: list[TraceEntry]) -> dict[str, float]:
    """Milliseconds per stage (the last entry wins if a stage ran twice)."""
    return {entry.stage: entry.duration_ms for entry in trace}


def rubric_reason(state: PipelineMedicState) -> str:
    """One line on why the rubric chose this risk level."""
    risk, category, workflow = state["risk"], state["diagnosis"].category, state.get("workflow")
    if risk.method != "rubric":
        return risk.rationale
    reason = f"Rubric v1 maps category `{category or 'unknown'}`"
    if workflow:
        reason += f" in workflow “{workflow}”"
    return f"{reason} to **{risk.level}** risk."
