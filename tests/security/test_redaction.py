"""Secret redaction.

Token-shaped strings are built at runtime (`"ghp_" + ...`) so that nothing
in the repository looks like a real credential to secret scanners.
"""

import pytest

from app.ingestion import parse_log
from app.redaction import redact_line, redact_lines
from tests.security.fixtures import ALNUM, SECRETS


@pytest.mark.parametrize("name", sorted(SECRETS))
def test_known_token_formats_are_redacted(name):
    secret = SECRETS[name]
    line, kinds = redact_line(f"deploying with {secret} now")
    assert secret not in line
    assert "[REDACTED:" in line
    assert len(kinds) == 1


@pytest.mark.parametrize(
    ("line", "kept"),
    [
        ("export DB_PASSWORD=" + "s3cr3t-value", "export DB_PASSWORD="),
        ('"api_key": "' + "k-12345678" + '"', '"api_key": "'),
        ("Authorization: Bearer " + ALNUM[:24], "Authorization: Bearer "),
        ("git clone https://deploy:" + "hunter2pass" + "@git.example.test/repo.git",
         "https://[REDACTED:url_credentials]@git.example.test"),
        ("db_password: " + "s3cr3t-value", "db_password: "),  # YAML style, has a non-letter
    ],
)
def test_only_the_secret_part_is_replaced(line, kept):
    redacted, _ = redact_line(line)
    assert kept in redacted
    for value in ("s3cr3t-value", "k-12345678", ALNUM[:24], "hunter2pass"):
        assert value not in redacted


@pytest.mark.parametrize(
    "line",
    [
        "HEAD is now at 3f2a9c1b7e6d5f4a3b2c1d0e9f8a7b6c5d4e3f2a",  # 40-hex commit SHA
        "run id 6f1c2e3a-8b7d-4c5e-9f0a-1b2c3d4e5f6a",               # UUID
        "token: ***",                                                # GitHub's own masking
        "test_password_reset_flow PASSED",
        "digest: sha256:" + "a" * 64,
        # false positives seen in the real public logs:
        "  - Token: ghs_" + "*" * 40,                                       # GitHub partial mask
        "New password: Retype new password: passwd: password updated",      # passwd prose
        '.whl?token=x&sha256=<64hex>").has_hash',                           # URL query text
        "PASSWORD_FILE=/run/secrets/db",                                    # a path, not a secret
    ],
)
def test_ordinary_ids_and_masked_values_are_left_alone(line):
    assert redact_line(line) == (line, [])


def test_private_key_block_is_fully_redacted_and_line_count_kept():
    lines = [
        "writing key",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAAB",
        "AAAAMwAAAAtzc2gtZWQyNTUxOQAAACDexample",
        "-----END OPENSSH PRIVATE KEY-----",
        "key written",
    ]
    result = redact_lines(lines)
    assert len(result.lines) == len(lines)
    assert result.lines[0] == "writing key" and result.lines[-1] == "key written"
    assert all(line == "[REDACTED:private_key]" for line in result.lines[1:5])
    assert result.findings == [(2, "private_key")]


def test_parsed_output_and_report_never_contain_the_secret():
    secret = SECRETS["github_token"]
    log = f"step 1\nexport GITHUB_TOKEN={secret}\nERROR: push rejected for {secret}\n"
    parsed = parse_log(log)
    dumped = parsed.model_dump_json()
    assert secret not in dumped
    assert parsed.redaction.total == 2
    assert parsed.redaction.lines == [2, 3]
    assert set(parsed.redaction.by_kind) <= {"github_token", "assigned_secret"}


def test_secrets_are_redacted_before_the_model_call(client, fake_ollama):
    secret = SECRETS["aws_access_key_id"]
    resp = client.post("/v1/diagnose", json={"log_text": f"aws configure set key {secret}\nERROR: denied"})
    assert resp.status_code == 200
    prompt = fake_ollama.calls[0]["json"]["prompt"]
    assert secret not in prompt
    assert "[REDACTED:aws_access_key_id]" in prompt


def test_api_parse_response_contains_no_secret(client):
    secret = SECRETS["slack_token"]
    resp = client.post("/v1/parse", json={"log_text": f"notify {secret}\nERROR: webhook failed"})
    assert resp.status_code == 200
    assert secret not in resp.text
    assert resp.json()["redaction"]["by_kind"] == {"slack_token": 1}
