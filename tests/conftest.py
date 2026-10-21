import hashlib
import re

import pytest
import requests
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.diagnosis import ollama


def _hash_embed(texts):
    """Deterministic bag-of-words embedder so tests never download a model."""
    dim = 256
    vectors = []
    for text in texts:
        vec = [0.0] * dim
        for token in re.findall(r"[a-z]+", text.lower()):
            vec[int(hashlib.md5(token.encode()).hexdigest(), 16) % dim] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        vectors.append([v / norm for v in vec])
    return vectors


@pytest.fixture
def fake_embed():
    return _hash_embed


# --- API --------------------------------------------------------------------


@pytest.fixture
def settings():
    """Small, fast limits so tests can hit them; never reads the real .env."""
    return Settings(ollama_url="http://ollama.test:11434", ollama_timeout_s=5, max_log_chars=1_000)


@pytest.fixture
def client(settings):
    from app.main import app

    app.dependency_overrides[get_settings] = lambda: settings
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


class FakeResponse:
    def __init__(self, status_code=200, payload=None, json_error=False):
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise ValueError("not JSON")
        return self._payload


class FakeOllama:
    """Stands in for the Ollama HTTP API. Set `post_result` to a FakeResponse
    or an exception instance; every call is recorded in `calls`."""

    def __init__(self):
        self.calls = []
        self.post_result = FakeResponse(payload={"response": "A test failed."})
        self.get_result = FakeResponse(payload={"models": []})

    def post(self, url, json, timeout):
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        if isinstance(self.post_result, Exception):
            raise self.post_result
        return self.post_result

    def get(self, url, timeout):
        if isinstance(self.get_result, Exception):
            raise self.get_result
        return self.get_result


@pytest.fixture
def fake_ollama(monkeypatch):
    fake = FakeOllama()
    monkeypatch.setattr(ollama.requests, "post", fake.post)
    monkeypatch.setattr(ollama.requests, "get", fake.get)
    return fake


@pytest.fixture
def network_errors():
    return requests
