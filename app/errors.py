"""Application errors and the single JSON error shape the API returns.

Every error response looks like:

    {"error": {"code": "provider_unavailable", "message": "...", "request_id": "..."}}

`code` is stable and machine-readable; `message` is for people. Internal
details (stack traces, upstream response bodies) never reach the client.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.common import ErrorBody, ErrorResponse

logger = logging.getLogger("pipelinemedic")


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class EmptyLog(AppError):
    status_code = 422
    code = "validation_error"


class LogTooLarge(AppError):
    status_code = 413
    code = "log_too_large"


class ProviderUnavailable(AppError):
    status_code = 503
    code = "provider_unavailable"


class ProviderTimeout(AppError):
    status_code = 504
    code = "provider_timeout"


class ProviderBadResponse(AppError):
    status_code = 502
    code = "provider_bad_response"


def _respond(request: Request, status: int, code: str, message: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    body = ErrorResponse(error=ErrorBody(code=code, message=message, request_id=request_id))
    # Set the header here too: an unhandled exception skips the middleware
    # that normally adds it.
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse(status_code=status, content=body.model_dump(), headers=headers)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return _respond(request, exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        return _respond(request, 422, "validation_error", problems)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error", extra={"request_id": request.state.request_id})
        return _respond(request, 500, "internal_error", "Internal server error.")
