"""
FastAPI application factory and process lifecycle management.

Overview:
    Builds the FX Pulse API application, registers middleware, mounts routes and
    Prometheus metrics, and manages startup/shutdown hooks for shared resources.

Functions:
    configure_logging: Configure root logging level and format for the process.
    lifespan: Async context manager for startup and shutdown lifecycle events.
    create_app: Construct and return a fully configured FastAPI application.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.api.v1.dependencies import close_http_client, set_start_time
from app.api.v1.routes import legacy_router, router
from app.core.exceptions import AppError, app_error_handler, unhandled_error_handler
from app.core.middleware import RateLimitMiddleware, RequestContextMiddleware
from app.core.settings import get_settings


def configure_logging(level: str) -> None:
    """
    Configure process-wide logging for the API service.

    Args:
        level: Logging level name (for example ``"INFO"`` or ``"DEBUG"``).

    Returns:
        None. Side effect: configures the root logger.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Manage application startup and shutdown lifecycle hooks.

    On startup, logging is configured and the process start time is recorded.
    On shutdown, the shared HTTP client and singleton services are closed.

    Args:
        app: FastAPI application instance (unused, required by Starlette).

    Yields:
        None while the application is running.

    Returns:
        None. Control is yielded back to FastAPI after startup setup.
    """
    settings = get_settings()
    configure_logging(settings.log_level)
    set_start_time(time.time())
    yield
    await close_http_client()


def create_app() -> FastAPI:
    """
    Build and configure the FastAPI application instance.

    Registers CORS, request context middleware, rate limiting, exception
    handlers, versioned API routes, legacy routes, and the Prometheus metrics
    mount at ``/metrics``.

    Returns:
        A configured FastAPI application ready to be served by Uvicorn.
    """
    settings = get_settings()
    app = FastAPI(
        title="FX Pulse API",
        description="Production EUR to USD exchange rate analytics API.",
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    app.include_router(router)
    app.include_router(legacy_router)
    app.mount("/metrics", make_asgi_app())
    return app


app = create_app()
