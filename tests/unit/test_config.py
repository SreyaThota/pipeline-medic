import pytest

from app.config import Settings, SettingsError, get_settings


@pytest.fixture
def clean_env(monkeypatch):
    """Isolate from the developer's .env and environment."""
    monkeypatch.setattr("app.config._load_env_file", lambda: None)
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def test_defaults_work_with_no_configuration(clean_env):
    settings = get_settings()
    assert settings.ollama_url == "http://localhost:11434"
    assert settings.max_log_chars == 200_000


def test_environment_overrides_and_normalises(clean_env):
    clean_env.setenv("OLLAMA_URL", "http://gpu-box:11434/")
    clean_env.setenv("MAX_LOG_CHARS", "5000")
    settings = get_settings()
    assert settings.ollama_url == "http://gpu-box:11434"
    assert settings.max_log_chars == 5000


@pytest.mark.parametrize(
    ("name", "value"),
    [("OLLAMA_URL", "ftp://example"), ("OLLAMA_TIMEOUT_S", "-1"), ("MAX_LOG_CHARS", "lots")],
)
def test_invalid_values_fail_fast_and_name_the_variable(clean_env, name, value):
    clean_env.setenv(name, value)
    with pytest.raises(SettingsError, match=name):
        get_settings()


def test_password_is_hidden_in_repr(clean_env):
    clean_env.setenv("NEO4J_PASSWORD", "hunter2-example")
    settings = get_settings()
    assert "hunter2-example" not in repr(settings)
    assert settings.neo4j_password.get_secret_value() == "hunter2-example"
