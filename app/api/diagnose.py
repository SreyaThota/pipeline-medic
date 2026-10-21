from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.limits import check_log
from app.config import Settings, get_settings
from app.diagnosis import ollama
from app.redaction import redact_lines
from app.schemas.common import ErrorResponse
from app.schemas.diagnose import DiagnoseRequest, DiagnoseResponse

router = APIRouter(tags=["diagnose"])

_ERRORS: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorResponse, "description": description}
    for status, description in {
        413: "Log is longer than MAX_LOG_CHARS",
        422: "Invalid request",
        502: "The model returned an unusable response",
        503: "The model provider is unreachable",
        504: "The model provider timed out",
    }.items()
}


def _summarize(log_text: str, settings: Settings) -> str:
    check_log(log_text, settings)
    # Secrets never reach the model: redact first, line by line.
    redacted = "\n".join(redact_lines(log_text.splitlines()).lines)
    return ollama.generate(ollama.SUMMARY_PROMPT.format(log_text=redacted), settings)


@router.post("/v1/diagnose", response_model=DiagnoseResponse, responses=_ERRORS)
def diagnose_v1(
    body: DiagnoseRequest, settings: Annotated[Settings, Depends(get_settings)]
) -> DiagnoseResponse:
    """Summarise a CI log with the configured local model.

    A structured, evidence-backed diagnosis is the Diagnosis Agent's job (v0.4).
    """
    summary = _summarize(body.log_text, settings)
    return DiagnoseResponse(summary=summary, model=settings.ollama_model)


@router.post("/diagnose", deprecated=True, responses=_ERRORS)
def diagnose_legacy(
    log_text: Annotated[str, Query()], settings: Annotated[Settings, Depends(get_settings)]
) -> dict[str, str]:
    """v0.1 endpoint, kept for compatibility. Use POST /v1/diagnose instead:
    a query parameter puts the whole log into the URL."""
    return {"summary": _summarize(log_text, settings)}
