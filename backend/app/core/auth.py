"""
API key authentication dependency.

Overview:
    Validates the X-API-Key header against keys configured via the API_KEYS
    environment variable. Uses constant-time comparison to avoid timing attacks.

Functions:
    require_api_key: FastAPI dependency that authenticates a request.
"""

from __future__ import annotations

import hmac

from fastapi import HTTPException, Request, status

from app.core.logging_config import get_logger
from app.core.settings import get_settings

logger = get_logger("auth")


async def require_api_key(request: Request) -> str:
    """
    Validate the X-API-Key header against configured API keys.

    Uses constant-time comparison to prevent timing attacks that could leak
    information about which configured key was matched.

    Args:
        request: Incoming HTTP request.

    Returns:
        The client name associated with the validated API key.

    Raises:
        HTTPException: HTTP 401 when the header is missing, malformed, or invalid.
    """
    settings = get_settings()
    configured = settings.api_keys_map

    if not configured:
        # Fail closed in production-like setups. Local dev should configure
        # API_KEYS in .env (see .env.example).
        logger.error("auth_misconfigured no api_keys set")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key authentication is not configured on this server",
        )

    presented = request.headers.get("X-API-Key", "").strip()
    if not presented:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    # Constant-time comparison against every configured key. Short-circuiting
    # on the first match would leak timing information about key ordering.
    matched_name: str | None = None
    for key, name in configured.items():
        if hmac.compare_digest(presented, key):
            matched_name = name

    if matched_name is None:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning("auth_invalid_key request_id=%s", request_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return matched_name
