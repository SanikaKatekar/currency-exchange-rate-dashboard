"""
HTTP middleware for request tracing, logging, and rate limiting.

Overview:
    Starlette middleware components that enrich each request with a correlation ID,
    emit request logs with correlation IDs and latency metrics, and enforce per-IP rate limits on
    the summary endpoint via a shared Redis sliding window.

Classes:
    RequestContextMiddleware: Attach request IDs, log requests, record latency.
    RateLimitMiddleware: Apply a Redis-backed per-IP rate limit to ``/api/v1/summary``.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging_config import get_logger
from app.core.metrics import REQUEST_LATENCY
from app.core.rate_limiter import allow_request as redis_allow_request
from app.core.settings import get_settings

logger = get_logger("http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Attach request IDs, emit request logs, and record latency metrics.

    Methods:
        dispatch: Process an incoming request and enrich the outgoing response.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Process a request and attach tracing metadata to the response.

        Args:
            request: Incoming Starlette request.
            call_next: Next middleware or route handler in the chain.

        Returns:
            Response from downstream handlers with ``X-Request-ID`` header set.
        """
        request_id: str = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        start: float = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms: float = (time.perf_counter() - start) * 1000
        endpoint: str = request.url.path
        if endpoint.startswith("/api/"):
            REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration_ms / 1000)
        logger.info(
            "request_completed request_id=%s method=%s path=%s status=%s duration_ms=%s",
            request_id,
            request.method,
            endpoint,
            response.status_code,
            round(duration_ms, 2),
        )
        response.headers["X-Request-ID"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Apply a Redis-backed per-IP rate limit to ``/api/v1/summary``.

    Methods:
        dispatch: Enforce rate limits or pass the request downstream.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Enforce per-IP rate limits for the summary endpoint.

        Non-summary routes bypass rate limiting entirely.

        Args:
            request: Incoming Starlette request.
            call_next: Next middleware or route handler in the chain.

        Returns:
            Either a 429 JSON response when the limit is exceeded, or the downstream
            handler response when within limits.
        """
        if request.url.path != "/api/v1/summary":
            return await call_next(request)

        settings = get_settings()
        client_ip: str = request.client.host if request.client else "unknown"
        allowed = await redis_allow_request(client_ip, settings.rate_limit_per_minute)
        if not allowed:
            request_id: str = getattr(request.state, "request_id", "unknown")
            logger.warning(
                "rate_limit_exceeded request_id=%s client_ip=%s path=%s",
                request_id,
                client_ip,
                request.url.path,
            )
            return Response(
                content='{"error":"Rate limit exceeded","code":"rate_limit_exceeded","request_id":"'
                + request_id
                + '"}',
                status_code=429,
                media_type="application/json",
            )
        return await call_next(request)
