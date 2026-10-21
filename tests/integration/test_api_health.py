from app import __version__
from tests.conftest import FakeResponse


def test_health_makes_no_outside_calls(client, fake_ollama):
    fake_ollama.get_result = AssertionError("liveness must not call Ollama")
    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "version": __version__}


def test_ready_reports_ok_when_ollama_answers(client, fake_ollama):
    resp = client.get("/health/ready")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["checks"]["ollama"] == {"status": "ok", "detail": None}


def test_ready_reports_degraded_when_ollama_is_down(client, fake_ollama, network_errors):
    fake_ollama.get_result = network_errors.ConnectionError()
    resp = client.get("/health/ready")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["checks"]["ollama"] == {"status": "unavailable", "detail": "ConnectionError"}


def test_ready_reports_degraded_on_http_error(client, fake_ollama):
    fake_ollama.get_result = FakeResponse(status_code=500)
    assert client.get("/health/ready").json()["checks"]["ollama"]["detail"] == "HTTP 500"
