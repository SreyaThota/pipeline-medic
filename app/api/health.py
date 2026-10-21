from typing import Annotated

from fastapi import APIRouter, Depends

from app import __version__
from app.config import Settings, get_settings
from app.diagnosis import ollama
from app.schemas.health import DependencyCheck, Health, Readiness

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Health)
def health() -> Health:
    """Liveness: the process is up. Makes no outside calls."""
    return Health(status="ok", version=__version__)


@router.get("/health/ready", response_model=Readiness)
def ready(settings: Annotated[Settings, Depends(get_settings)]) -> Readiness:
    """Readiness: which dependencies are reachable right now."""
    ok, detail = ollama.is_reachable(settings)
    checks = {"ollama": DependencyCheck(status="ok" if ok else "unavailable", detail=detail)}
    all_ok = all(c.status == "ok" for c in checks.values())
    return Readiness(status="ok" if all_ok else "degraded", version=__version__, checks=checks)
