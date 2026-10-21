"""What the API returns when the model provider misbehaves.

Each failure maps to one stable error code, never a 500 stack trace, and
never a fabricated summary.
"""

import pytest

from tests.conftest import FakeResponse


@pytest.mark.parametrize(
    ("make_failure", "status", "code"),
    [
        (lambda r: r.ConnectionError(), 503, "provider_unavailable"),
        (lambda r: r.Timeout(), 504, "provider_timeout"),
        (lambda r: FakeResponse(status_code=500), 502, "provider_bad_response"),
        (lambda r: FakeResponse(json_error=True), 502, "provider_bad_response"),
        (lambda r: FakeResponse(payload={"error": "model not found"}), 502, "provider_bad_response"),
        (lambda r: FakeResponse(payload={"response": None}), 502, "provider_bad_response"),
        (lambda r: FakeResponse(payload=["unexpected"]), 502, "provider_bad_response"),
    ],
    ids=["unreachable", "timeout", "http-500", "not-json", "no-response-field",
         "null-response", "wrong-shape"],
)
def test_provider_failures_map_to_structured_errors(
    client, fake_ollama, network_errors, make_failure, status, code
):
    fake_ollama.post_result = make_failure(network_errors)
    resp = client.post("/v1/diagnose", json={"log_text": "FAILED test_x"})

    assert resp.status_code == status
    error = resp.json()["error"]
    assert error["code"] == code
    assert error["request_id"]
    assert "Traceback" not in error["message"]


def test_legacy_endpoint_fails_the_same_way(client, fake_ollama, network_errors):
    fake_ollama.post_result = network_errors.ConnectionError()
    resp = client.post("/diagnose", params={"log_text": "FAILED test_x"})

    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "provider_unavailable"


def test_unexpected_exception_returns_generic_500(client, fake_ollama):
    fake_ollama.post_result = RuntimeError("secret internal detail")
    from fastapi.testclient import TestClient

    from app.main import app

    resp = TestClient(app, raise_server_exceptions=False).post(
        "/v1/diagnose", json={"log_text": "FAILED test_x"}
    )
    assert resp.status_code == 500
    assert resp.json()["error"] == {
        "code": "internal_error",
        "message": "Internal server error.",
        "request_id": resp.headers["X-Request-ID"],
    }
    assert "secret internal detail" not in resp.text
