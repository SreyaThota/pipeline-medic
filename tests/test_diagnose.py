from fastapi.testclient import TestClient

import app.main
from app.main import app as fastapi_app


class _FakeResponse:
    def json(self):
        return {"response": "Tests failed because of an assertion error."}


def test_diagnose_returns_model_summary(monkeypatch):
    calls = []

    def fake_post(url, json):
        calls.append((url, json))
        return _FakeResponse()

    monkeypatch.setattr(app.main.requests, "post", fake_post)
    resp = TestClient(fastapi_app).post("/diagnose", params={"log_text": "FAILED test_x"})

    assert resp.status_code == 200
    assert resp.json() == {"summary": "Tests failed because of an assertion error."}
    assert "FAILED test_x" in calls[0][1]["prompt"]
