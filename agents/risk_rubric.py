"""Risk rubric: how urgent a CI failure is for the team.

**DRAFT — needs Sreya's sign-off (NEEDS_DECISION.md #2).** It is used in
three places, so changing it changes all three consistently:

- the prompted classifier's instructions (`agents/risk_classifier.py`),
- the rules fallback when the model is unavailable or answers badly,
- the labels for the v0.5 LoRA experiment (`data/risk_labels/`).

Levels:
    high    the project cannot build, install or ship: compile/bundle errors,
            dependency resolution, out-of-memory/disk, or any failure in a
            release/publish/deploy workflow
    medium  correctness signal is red: failing tests, type errors, timeouts,
            broken CI configuration
    low     hygiene or transient: lint/format, docs, repository policy
            (changelog, PR checklist), network/rate-limit blips worth a retry
"""

from app.graph import RiskLevel

RUBRIC_TEXT = """\
high: the project cannot build, install or ship (compile or bundle errors, dependency
      resolution failures, out of memory or disk, any failure in a release, publish or
      deploy workflow)
medium: correctness is red (failing tests, type-check errors, timeouts, broken CI
      configuration)
low: hygiene or transient problems (lint or format, docs, repository policy such as a
      missing changelog entry, network or rate-limit blips that a retry fixes)"""

CATEGORY_RISK: dict[str, RiskLevel] = {
    "build_compile": "high",
    "dependency_install": "high",
    "test_failure": "medium",
    "type_check": "medium",
    "timeout": "medium",
    "ci_config": "medium",
    "lint_format": "low",
    "docs_check": "low",
    "policy_check": "low",
    "infra_network": "low",
}

SHIPPING_WORKFLOW_WORDS = ("release", "publish", "deploy", "wheel", "build and publish")


def rubric_risk(category: str | None, workflow: str | None = None) -> RiskLevel:
    """Apply the rubric to a category (and workflow name, if known)."""
    if workflow and any(word in workflow.lower() for word in SHIPPING_WORKFLOW_WORDS):
        return "high"
    if category is None:
        return "medium"  # unknown: neither ignore it nor page anyone by default
    return CATEGORY_RISK.get(category, "medium")
