from rag.entities import Entity, extract_entities


def keys(text):
    return {e.key for e in extract_entities(text)}


def test_pytest_failure():
    log = (
        "Run python -m pytest tests\n"
        "FAILED tests/test_x.py::test_y - AssertionError: assert 1 == 2\n"
        "========= 1 failed, 20 passed in 3.10s =========\n"
        "##[error]Process completed with exit code 1."
    )
    found = keys(log)
    assert {"tool:pytest", "error:tests_failed", "error:AssertionError",
            "error:assertion_failed", "exit_code:1"} <= found


def test_tool_needs_invocation_not_a_path_mention():
    assert "tool:prettier" not in keys("cd /home/runner/work/prettier/prettier/src")
    assert "tool:prettier" in keys("npx prettier --check .")
    assert "tool:black" in keys("would reformat src/app.py")


def test_rust_compile_error_and_package():
    found = keys("error[E0277]: the trait bound is not satisfied\n"
                 "error: could not compile `ruff_python_ast` (lib) due to 1 previous error")
    assert {"tool:rustc", "tool:cargo", "error:compile_failed", "error:rustc_E0277",
            "package:ruff_python_ast"} <= found


def test_dependency_and_network_signatures():
    assert "error:no_matching_distribution" in keys(
        "ERROR: No matching distribution found for ruff"
    )
    assert "package:hypothesis" in keys("E   ModuleNotFoundError: No module named 'hypothesis'")
    assert "error:network_error" in keys("Curl error (28): Timeout was reached")
    assert "error:rate_limited" in keys("You have exceeded a secondary rate limit.")


def test_ci_config_and_timeout_signatures():
    assert "error:command_not_found" in keys("line 2: cibuildwheel: command not found")
    assert "error:step_timeout" in keys("##[error]The action 'Run pytest' has timed out after 60 minutes.")
    assert "error:gate_job" in keys("# ❌ Some of the required to succeed jobs failed")


def test_case_insensitive_rules_and_empty_log():
    assert "error:changelog_required" in keys("Please add '(#5390)' change line to CHANGES.md")
    assert extract_entities("") == set()


def test_entity_key():
    assert Entity("tool", "pytest").key == "tool:pytest"
