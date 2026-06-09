"""
Tests for FastAPI application factory and lifecycle hooks.
"""

from __future__ import annotations

import pytest

from app.main import app, create_app, lifespan


@pytest.mark.asyncio
async def test_lifecycle_runs_startup_and_shutdown() -> None:
    """Lifespan configures logging, Redis, and shared clients."""
    test_app = create_app()
    async with lifespan(test_app):
        pass


def test_module_level_app_is_created() -> None:
    """Module import exposes a configured application instance."""
    assert app.title == "FX Pulse API"
