"""PipelineMedic X API.

Run locally:  uvicorn app.main:app --reload   (docs at http://localhost:8000/docs)
"""

import logging

from fastapi import FastAPI

from app import __version__
from app.api import diagnose, health
from app.config import get_settings
from app.errors import install_error_handlers
from app.observability.requests import install_request_middleware


def create_app() -> FastAPI:
    get_settings()  # fail fast on invalid configuration
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    application = FastAPI(
        title="PipelineMedic X",
        version=__version__,
        description="AI-assisted CI/CD failure diagnosis and safe remediation.",
    )
    install_request_middleware(application)
    install_error_handlers(application)
    application.include_router(health.router)
    application.include_router(diagnose.router)
    return application


app = create_app()
