"""
Custom application exceptions and FastAPI exception handlers.

Overview:
    Provides a structured application error type and handlers that serialize
    errors into consistent JSON responses with request correlation IDs.

Classes:
    AppError: Application exception carrying HTTP status and error code metadata.

Functions:
    app_error_handler: Convert ``AppError`` instances into JSON error responses.
    unhandled_error_handler: Catch unexpected exceptions and return safe 500 JSON.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """
    Application-level error mapped to an HTTP response.

    Args:
        message: Human-readable error description returned to clients.
        code: Stable machine-readable error code (for example ``validation_error``).
        status_code: HTTP status code to return. Defaults to 400.
    """

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        self.message: str = message
        self.code: str = code
        self.status_code: int = status_code
        super().__init__(message)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """
    Serialize known application errors into a consistent JSON payload.

    Args:
        request: Incoming HTTP request; used to read ``request_id`` from state.
        exc: Raised ``AppError`` instance.

    Returns:
        JSONResponse containing ``error``, ``code``, and ``request_id`` fields.
    """
    request_id: str = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "code": exc.code,
            "request_id": request_id,
        },
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch unexpected exceptions and avoid leaking stack traces to clients.

    Args:
        request: Incoming HTTP request; used to read ``request_id`` from state.
        exc: Unhandled exception (not exposed in the response body).

    Returns:
        JSONResponse with HTTP 500 and a generic internal error payload.
    """
    request_id: str = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "code": "internal_error",
            "request_id": request_id,
        },
    )
