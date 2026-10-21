from typing import Literal

from pydantic import BaseModel


class Health(BaseModel):
    status: Literal["ok"]
    version: str


class DependencyCheck(BaseModel):
    status: Literal["ok", "unavailable"]
    detail: str | None = None


class Readiness(BaseModel):
    """`degraded` means the API is up but a dependency (e.g. Ollama) is not."""

    status: Literal["ok", "degraded"]
    version: str
    checks: dict[str, DependencyCheck]
