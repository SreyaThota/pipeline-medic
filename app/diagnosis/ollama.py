"""Minimal Ollama client with a timeout and typed errors.

The Diagnosis Agent (v0.4) builds on this client.
"""

import requests

from app.config import Settings
from app.errors import ProviderBadResponse, ProviderTimeout, ProviderUnavailable

SUMMARY_PROMPT = "Summarize this build log in 2 sentences:\n{log_text}"


def generate(prompt: str, settings: Settings) -> str:
    """Return the model's completion, or raise a Provider* error."""
    try:
        response = requests.post(
            f"{settings.ollama_url}/api/generate",
            json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
            timeout=settings.ollama_timeout_s,
        )
    except requests.Timeout:
        raise ProviderTimeout(
            f"Ollama did not answer within {settings.ollama_timeout_s:g} seconds."
        ) from None
    except requests.ConnectionError:
        raise ProviderUnavailable(
            f"Could not reach Ollama at {settings.ollama_url}. Is it running?"
        ) from None

    if response.status_code != 200:
        raise ProviderBadResponse(f"Ollama returned HTTP {response.status_code}.")
    try:
        text = response.json()["response"]
    except (ValueError, KeyError, TypeError):
        raise ProviderBadResponse("Ollama returned a response without generated text.") from None
    if not isinstance(text, str):
        raise ProviderBadResponse("Ollama returned a response without generated text.")
    return text


def is_reachable(settings: Settings, timeout_s: float = 2.0) -> tuple[bool, str | None]:
    """Cheap readiness probe: can we list Ollama's models?"""
    try:
        response = requests.get(f"{settings.ollama_url}/api/tags", timeout=timeout_s)
    except requests.RequestException as exc:
        return False, type(exc).__name__
    if response.status_code != 200:
        return False, f"HTTP {response.status_code}"
    return True, None
