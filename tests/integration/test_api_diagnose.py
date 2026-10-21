"""The diagnose endpoints, with the Ollama HTTP API faked."""

from tests.conftest import FakeResponse


def test_legacy_diagnose_returns_model_summary(client, fake_ollama):
    """v0.1 behaviour is unchanged: same URL, query parameter and response."""
    fake_ollama.post_result = FakeResponse(
        payload={"response": "Tests failed because of an assertion error."}
    )
    resp = client.post("/diagnose", params={"log_text": "FAILED test_x"})

    assert resp.status_code == 200
    assert resp.json() == {"summary": "Tests failed because of an assertion error."}
    assert "FAILED test_x" in fake_ollama.calls[0]["json"]["prompt"]


def test_v1_diagnose_uses_configured_model_and_timeout(client, fake_ollama, settings):
    resp = client.post("/v1/diagnose", json={"log_text": "error[E0277]: trait bound"})

    assert resp.status_code == 200
    assert resp.json() == {"summary": "A test failed.", "model": settings.ollama_model}
    call = fake_ollama.calls[0]
    assert call["url"] == f"{settings.ollama_url}/api/generate"
    assert call["json"]["model"] == settings.ollama_model
    assert call["timeout"] == settings.ollama_timeout_s


def test_v1_rejects_missing_and_empty_logs(client, fake_ollama):
    for body in ({}, {"log_text": ""}, {"log_text": "   \n "}):
        resp = client.post("/v1/diagnose", json=body)
        assert resp.status_code == 422, body
        assert resp.json()["error"]["code"] == "validation_error"
    assert fake_ollama.calls == []


def test_oversized_log_is_rejected_before_calling_the_model(client, fake_ollama, settings):
    resp = client.post("/v1/diagnose", json={"log_text": "x" * (settings.max_log_chars + 1)})

    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "log_too_large"
    assert fake_ollama.calls == []


def test_errors_carry_the_request_id(client, fake_ollama):
    resp = client.post("/v1/diagnose", json={}, headers={"X-Request-ID": "ci-run-42"})

    assert resp.headers["X-Request-ID"] == "ci-run-42"
    assert resp.json()["error"]["request_id"] == "ci-run-42"


def test_invalid_request_id_is_replaced(client, fake_ollama):
    resp = client.post(
        "/v1/diagnose", json={"log_text": "x"}, headers={"X-Request-ID": "bad id with spaces"}
    )
    assert resp.headers["X-Request-ID"] != "bad id with spaces"
    assert len(resp.headers["X-Request-ID"]) == 32
