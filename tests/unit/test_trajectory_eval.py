"""v0.6 trajectory scoring logic (no models)."""

from evaluation.run_trajectory_eval import expected_tools, summarize


def test_expected_tools_follow_the_action_policy():
    assert expected_tools("build_compile", "high") == ["create_ticket", "notify"]
    assert expected_tools("test_failure", "medium") == ["create_ticket"]
    assert expected_tools("lint_format", "low") == []
    assert expected_tools(None, "medium") == ["create_ticket", "notify"]  # no cause → triage


def _run(log_id, no_cause=False, **checks):
    base = {"parse": True, "diagnose": True, "grounded": True, "risk": True, "action": True,
            "safety": True}
    base.update(checks)
    first = next((k for k in ("parse", "diagnose", "risk", "action", "safety") if not base[k]), None)
    return {"log_id": log_id, "no_cause_in_log": no_cause, "checks": base,
            "trajectory_correct": all(base.values()), "first_error": first,
            "risk_method": "rules", "seconds": 0.2}


def test_summary_rates_and_first_error_attribution():
    runs = [_run("a"), _run("b", diagnose=False, action=False), _run("c", risk=False),
            _run("d", no_cause=True, diagnose=False)]
    summary = summarize({"runs": runs, "judge": []})
    assert summary["logs"] == 4 and summary["scoreable"] == 3
    assert summary["trajectory_correct"] == 0.25
    assert summary["stage_pass_rate"]["diagnose"] == 0.5
    assert summary["first_error"] == {"none": 1, "diagnose": 2, "risk": 1}
    assert summary["no_cause_logs_escalated"] == "0/1"
    assert "llm_judge" not in summary


def test_judge_summary_reports_the_negative_control():
    judge = [{"log_id": "a", "supported": True, "control_flagged": True},
             {"log_id": "b", "supported": True, "control_flagged": False},
             {"log_id": "c", "supported": None, "control_flagged": None}]
    summary = summarize({"runs": [_run("a")], "judge": judge})
    assert summary["llm_judge"]["judged_supported"] == "2/2"
    assert summary["llm_judge"]["negative_control_caught"] == "1/2"
