# data/fixtures/

**Synthetic logs, written by hand for tests and demos.** They imitate real
CI output but are not real runs, and they are never mixed into the real-log
retrieval metrics in `data/sample_logs/`.

| File | Format | Failure |
|---|---|---|
| `github_actions_pytest.log` | GitHub Actions, `gh run view --log-failed` style | pytest assertion with a Python traceback, followed by post-job cleanup |
| `github_actions_raw.log` | GitHub Actions, raw log downloaded from the UI | npm dependency-resolution error |
| `jenkins_maven.log` | Jenkins pipeline console with Timestamper | Maven Surefire test failures in the `Test` stage |
| `text_vite_build.log` | Plain text | Vite/Rollup unresolved import |

None of these files contain secrets, not even fake ones: the redaction tests
build token-shaped strings at runtime so that nothing secret-looking is
committed to the repository.
