from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"


def test_parse_returns_evidence_with_line_numbers(client, fake_ollama):
    log = (FIXTURES / "jenkins_maven.log").read_text(encoding="utf-8")
    resp = client.post("/v1/parse", json={"log_text": log})

    assert resp.status_code == 200
    body = resp.json()
    assert body["format"] == "jenkins" and body["format_detected"] is True
    assert body["line_count"] == 19
    assert body["exit_codes"][-1] == {"line": 18, "code": 1}
    assert all(r["start_line"] <= r["anchor_line"] <= r["end_line"] for r in body["regions"])
    assert fake_ollama.calls == []  # parsing never calls a model


def test_parse_with_forced_format(client):
    resp = client.post("/v1/parse", json={"log_text": "ERROR: x", "format": "text"})
    assert resp.json()["format"] == "text"
    assert "format_forced" in resp.json()["flags"]


def test_parse_rejects_bad_input(client, settings):
    assert client.post("/v1/parse", json={"log_text": "x", "format": "gitlab"}).status_code == 422
    assert client.post("/v1/parse", json={"log_text": "  "}).status_code == 422
    too_big = client.post("/v1/parse", json={"log_text": "x" * (settings.max_log_chars + 1)})
    assert too_big.status_code == 413
    assert too_big.json()["error"]["code"] == "log_too_large"
