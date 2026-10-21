"""Build the v0.5 risk-label set (run once; the output is committed and frozen).

Real logs: the draft rubric (agents/risk_rubric.py) applied to each log's
failure-category label and workflow name. Logs with no cause in the text
(aggregate_gate, unknown) are left out. Status follows the category label:
dev labels are human-reviewed, test labels are still draft.

Synthetic logs: short hand-written failure tails, 10 per risk level, used for
training only and marked `synthetic` in every file and report.

    python -m ml.build_risk_labels
"""

import csv
import json
from pathlib import Path

from agents.risk_rubric import rubric_risk

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "sample_logs" / "index.csv"
OUT_DIR = ROOT / "data" / "risk_labels"
EXCLUDED = {"aggregate_gate", "unknown"}

SYNTHETIC = {
    "high": [
        ("CI", "src/parser.c:118:5: error: implicit declaration of function 'strlcpy'\nmake: *** [Makefile:42: parser.o] Error 1"),
        ("CI", "error[E0308]: mismatched types\n  --> src/lib.rs:88:16\nerror: could not compile `engine` (lib) due to 1 previous error"),
        ("CI", "src/app.ts(14,7): error TS2322: Type 'string' is not assignable to type 'number'.\nerror Command failed with exit code 2. (tsc -b)"),
        ("CI", "ERROR: Cannot install shop-api==2.1.0 because these package versions have conflicting dependencies.\nERROR: ResolutionImpossible"),
        ("CI", "npm ERR! code ERESOLVE\nnpm ERR! ERESOLVE could not resolve\nnpm ERR! peer react@\"^18\" from react-dom@18.3.1"),
        ("CI", "error: failed to select a version for `tokio`.\nversions that meet the requirements `^2.0` are: (none)"),
        ("CI", "<--- Last few GCs --->\nFATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory"),
        ("Release", "Uploading shop_api-2.1.0-py3-none-any.whl\nHTTPError: 403 Forbidden from https://upload.pypi.org/legacy/"),
        ("Deploy production", "Error: deployment \"web\" exceeded its progress deadline\nerror: timed out waiting for the condition"),
        ("Build and publish", "ERROR: Docker build failed: failed to solve: process \"/bin/sh -c pip install .\" did not complete successfully: exit code: 1"),
    ],
    "medium": [
        ("CI", "FAILED tests/test_orders.py::test_refund - AssertionError: assert 90 == 100\n= 1 failed, 212 passed in 31.2s ="),
        ("CI", "FAIL src/cart.test.ts\n  ● cart › applies discount\n    Expected: 90\n    Received: 100\nTests: 1 failed, 88 passed"),
        ("CI", "--- FAIL: TestCheckout (0.03s)\n    checkout_test.go:41: got 3 items, want 2\nFAIL\tgithub.com/shop/api\t0.512s"),
        ("CI", "test result: FAILED. 120 passed; 2 failed; 0 ignored; 0 measured\nerror: test failed, to rerun pass `--lib`"),
        ("CI", "src/shop/models.py:57: error: Incompatible return value type (got \"str\", expected \"int\")  [return-value]\nFound 1 error in 1 file (checked 64 source files)"),
        ("CI", "/work/src/api.py:12:9 - error: \"user\" is possibly unbound (reportPossiblyUnbound)\n1 error, 0 warnings, 0 informations"),
        ("CI", "##[error]The job running on runner GitHub Actions 12 has exceeded the maximum execution time of 60 minutes."),
        ("CI", "pytest-timeout: Timeout >300.0s\nFAILED tests/test_sync.py::test_full_sync - Failed: Timeout >300.0s"),
        ("CI", "Error: Unable to resolve action `actions/setup-pyhton@v5`, repository not found"),
        ("CI", "Invalid workflow file: .github/workflows/ci.yml#L19\nThe workflow is not valid. Unexpected value 'run-on'"),
    ],
    "low": [
        ("Lint", "src/shop/views.py:88:101: E501 Line too long (112 > 100)\nFound 3 errors.\n[*] 2 fixable with the `--fix` option."),
        ("Lint", "would reformat src/shop/forms.py\nOh no! 💥 💔 💥\n1 file would be reformatted, 40 files would be left unchanged."),
        ("Lint", "  12:5  error  'unused' is defined but never used  no-unused-vars\n✖ 1 problem (1 error, 0 warnings)"),
        ("Lint", "[warn] src/components/Cart.tsx\n[warn] Code style issues found in the above file. Run Prettier with --write to fix."),
        ("Docs", "docs/install.rst:44: WARNING: broken link: https://example.test/old-guide (404 Client Error)\nbuild finished with problems, 1 warning."),
        ("Docs", "Warning, treated as error:\ndocs/api.rst:10: WARNING: undefined label: 'quickstart'"),
        ("Changelog", "No changelog entry found. Add a news fragment in changes/ or ask a maintainer for the 'skip-news' label."),
        ("PR checks", "##[error]Commit 4f2a1c9 message must start with a component prefix, e.g. 'api: fix refund rounding'."),
        ("CI", "Error: API rate limit exceeded for installation ID 1234. Retry after 2026-10-21T22:10:00Z\n##[error]HTTP 429"),
        ("CI", "curl: (28) Failed to connect to mirror.example.test port 443 after 30001 ms: Timeout was reached\nRetrying in 10 seconds..."),
    ],
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    with INDEX.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row["label"] or row["label"] in EXCLUDED:
                continue
            rows.append({
                "log_id": row["log_id"],
                "repo": row["repo"],
                "workflow": row["workflow"],
                "split": row["split"],
                "category_label": row["label"],
                "category_status": row["label_status"],
                "risk_level": rubric_risk(row["label"], row["workflow"]),
                "risk_source": "draft_rubric_v1",
            })
    with (OUT_DIR / "risk_labels.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    with (OUT_DIR / "synthetic_train.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for level, examples in SYNTHETIC.items():
            for i, (workflow, text) in enumerate(examples, start=1):
                f.write(json.dumps({"id": f"synthetic-{level}-{i:02d}", "synthetic": True,
                                    "workflow": workflow, "risk_level": level, "text": text},
                                   ensure_ascii=False) + "\n")
    print(f"{len(rows)} real logs, {sum(len(v) for v in SYNTHETIC.values())} synthetic examples")


if __name__ == "__main__":
    main()
