"""Collect failed GitHub Actions run logs into data/sample_logs/.

Two sources share one index (data/sample_logs/index.csv):
  - dogfood: this repo's own CI (SreyaThota/pipeline-medic)
  - oss:     public open-source repos, to give the v0.2 baseline enough volume

Requires an authenticated `gh` CLI. Re-running is safe: runs already in the
index are skipped and existing labels are never overwritten.

Usage:
    python data/collect_ci_logs.py                 # default repo list
    python data/collect_ci_logs.py --repos owner/name --per-repo 5
"""

import argparse
import csv
import json
import re
import subprocess
from pathlib import Path

DATA_DIR = Path(__file__).parent / "sample_logs"
INDEX_PATH = DATA_DIR / "index.csv"
INDEX_FIELDS = [
    "log_id", "source", "repo", "workflow", "run_id", "run_url",
    "created_at", "label", "label_status",
]

DOGFOOD_REPO = "SreyaThota/pipeline-medic"
DEFAULT_OSS_REPOS = [
    "pytest-dev/pytest", "psf/black", "fastapi/fastapi", "pydantic/pydantic",
    "pandas-dev/pandas", "scikit-learn/scikit-learn", "astral-sh/ruff",
    "encode/httpx", "python-poetry/poetry", "home-assistant/core",
    "vitejs/vite", "prettier/prettier",
]

# Repo-housekeeping workflows (PR label checks, bots) fail for reasons that
# aren't build/test failures, so they're excluded from the corpus.
SKIP_WORKFLOW = re.compile(
    r"label|smokeshow|stale|triage|welcome|cla\b|assign|greet|lock|"
    r"dependabot|issue|milestone|title",
    re.IGNORECASE,
)
MAX_LINES = 400  # keep the tail of each log, where the failure usually is
PER_WORKFLOW = 2  # spread samples across workflows for failure-type variety


def gh(*args: str) -> str:
    return subprocess.run(
        ["gh", *args], capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=True,
    ).stdout


def load_index() -> dict[str, dict]:
    if not INDEX_PATH.exists():
        return {}
    with INDEX_PATH.open(newline="", encoding="utf-8") as f:
        return {row["log_id"]: row for row in csv.DictReader(f)}


def save_index(rows: dict[str, dict]) -> None:
    with INDEX_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=INDEX_FIELDS)
        writer.writeheader()
        writer.writerows(sorted(rows.values(), key=lambda r: r["log_id"]))


def collect_repo(repo: str, source: str, per_repo: int, index: dict) -> int:
    runs = json.loads(gh(
        "run", "list", "-R", repo, "--status", "failure", "--limit", "100",
        "--json", "databaseId,workflowName,createdAt,url",
    ))
    per_workflow: dict[str, int] = {}
    added = 0
    for run in runs:
        if added >= per_repo:
            break
        workflow = run["workflowName"]
        if SKIP_WORKFLOW.search(workflow) or per_workflow.get(workflow, 0) >= PER_WORKFLOW:
            continue
        log_id = f"{repo.replace('/', '__')}__{run['databaseId']}"
        if log_id in index:
            continue
        try:
            text = gh("run", "view", str(run["databaseId"]), "-R", repo, "--log-failed")
        except subprocess.CalledProcessError:
            continue  # logs expired or not accessible
        lines = text.splitlines()
        if not lines:
            continue
        out_dir = DATA_DIR / source
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{log_id}.log").write_text(
            "\n".join(lines[-MAX_LINES:]) + "\n", encoding="utf-8"
        )
        index[log_id] = {
            "log_id": log_id, "source": source, "repo": repo,
            "workflow": workflow, "run_id": run["databaseId"],
            "run_url": run["url"], "created_at": run["createdAt"],
            "label": "", "label_status": "",
        }
        per_workflow[workflow] = per_workflow.get(workflow, 0) + 1
        added += 1
    return added


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repos", nargs="*", default=DEFAULT_OSS_REPOS)
    parser.add_argument("--per-repo", type=int, default=8)
    args = parser.parse_args()

    index = load_index()
    total = collect_repo(DOGFOOD_REPO, "dogfood", args.per_repo, index)
    print(f"{DOGFOOD_REPO}: {total} new")
    for repo in args.repos:
        n = collect_repo(repo, "oss", args.per_repo, index)
        print(f"{repo}: {n} new")
        total += n
    save_index(index)
    print(f"{total} logs added, {len(index)} in index")


if __name__ == "__main__":
    main()
