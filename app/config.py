"""Validated settings, read from the environment with a local .env as fallback.

Every setting has a safe local default, so the app and the tests run with no
configuration at all. Invalid values fail at startup with a message that
names the variable, instead of failing later inside a request.
"""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class SettingsError(RuntimeError):
    """Raised when an environment variable holds an invalid value."""


def _load_env_file(path: Path = ENV_FILE) -> None:
    """Minimal KEY=VALUE loader; real environment variables take priority."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = Field("llama3.2", min_length=1)
    ollama_timeout_s: float = Field(60.0, gt=0, le=600)
    max_log_chars: int = Field(200_000, gt=0, le=5_000_000)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("")
    # Action Agent (v0.3). Real actions need ACTIONS_ENABLED=true *and* a
    # caller that asks for dry_run=False; everything else is a dry run.
    actions_enabled: bool = False
    runtime_dir: str = "var"  # audit log, local ticket store, notification outbox
    notify_channels: tuple[str, ...] = ("ci-alerts", "oncall")

    @field_validator("notify_channels", mode="before")
    @classmethod
    def _split_channels(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(part.strip() for part in value.split(",") if part.strip())
        return value

    @field_validator("ollama_url")
    @classmethod
    def _http_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("must start with http:// or https://")
        return value.rstrip("/")


# Environment variable for each setting: the field name in upper case.
_ENV_NAMES = {name: name.upper() for name in Settings.model_fields}


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process. Tests call get_settings.cache_clear()."""
    _load_env_file()
    values = {
        field: os.environ[env] for field, env in _ENV_NAMES.items() if env in os.environ
    }
    try:
        return Settings.model_validate(values)
    except ValidationError as exc:
        problems = "; ".join(
            f"{_ENV_NAMES[str(err['loc'][0])]}: {err['msg']}" for err in exc.errors()
        )
        raise SettingsError(f"Invalid configuration: {problems}") from None
