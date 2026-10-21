from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.limits import check_log
from app.config import Settings, get_settings
from app.ingestion import parse_log
from app.schemas.common import ErrorResponse
from app.schemas.logs import ParsedLog, ParseRequest

router = APIRouter(tags=["parse"])

_ERRORS: dict[int | str, dict[str, Any]] = {
    413: {"model": ErrorResponse, "description": "Log is longer than MAX_LOG_CHARS"},
    422: {"model": ErrorResponse, "description": "Invalid request"},
}


@router.post("/v1/parse", response_model=ParsedLog, responses=_ERRORS)
def parse(body: ParseRequest, settings: Annotated[Settings, Depends(get_settings)]) -> ParsedLog:
    """Redact secrets and extract line-referenced failure evidence. No model is used.

    The response contains only redacted text: failure regions with their
    original line numbers, the last 15 lines, exit codes, and a redaction
    report listing which kinds of secret were found on which lines.
    """
    check_log(body.log_text, settings)
    fmt = None if body.format == "auto" else body.format
    return parse_log(body.log_text, fmt=fmt)
