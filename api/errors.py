"""Typed error responses: every non-2xx answer has the same shape and carries the trace id."""

import logging
from collections.abc import Mapping
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException

from api.tracing import TRACE_ID_HEADER, current_trace_id

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    """One problem found in the request, such as an invalid field."""

    location: list[str | int]
    message: str
    type: str


class Error(BaseModel):
    """Machine-readable code and human-readable message of an error."""

    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Body of every error response."""

    error: Error
    trace_id: str


class ApiError(Exception):
    """An error deliberately returned to the client with its own status and code."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def install_error_handlers(app: FastAPI) -> None:
    """Register the handlers that turn every exception into an `ErrorResponse`."""
    app.add_exception_handler(ApiError, _handle_api_error)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, _handle_http_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unexpected_error)


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Build an error response for the current request."""
    trace_id = current_trace_id()
    body = ErrorResponse(
        error=Error(code=code, message=message, details=details or []), trace_id=trace_id
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(),
        headers={**(headers or {}), TRACE_ID_HEADER: trace_id},
    )


def _describe_status(status_code: int) -> tuple[str, str]:
    """Return a snake_case error code and a reason phrase, also for non-standard status codes."""
    try:
        phrase = HTTPStatus(status_code).phrase
    except ValueError:
        return "http_error", "HTTP error"
    return phrase.lower().replace(" ", "_").replace("-", "_"), phrase


async def _handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message)


async def _handle_http_error(_request: Request, exc: HTTPException) -> JSONResponse:
    code, phrase = _describe_status(exc.status_code)
    message = exc.detail if isinstance(exc.detail, str) else phrase
    return error_response(exc.status_code, code, message, headers=exc.headers)


async def _handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    # The offending input values are deliberately not echoed back: they may contain user content.
    details = [
        ErrorDetail(location=list(error["loc"]), message=error["msg"], type=error["type"])
        for error in exc.errors()
    ]
    return error_response(
        HTTPStatus.UNPROCESSABLE_ENTITY,
        "validation_error",
        "The request is invalid.",
        details=details,
    )


async def _handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled exception",
        exc_info=exc,
        extra={"trace_id": current_trace_id(), "exception_type": type(exc).__name__},
    )
    return error_response(
        HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", "An unexpected error occurred."
    )
