"""
Central logging configuration for the FX Pulse API.

Overview:
    Configures process-wide logging with a consistent format and provides a
    shared logger factory for application modules.

Functions:
    configure_logging: Configure root logging level and message format.
    get_logger: Return a namespaced logger under the ``fx_pulse`` hierarchy.
"""

from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """
    Configure process-wide logging for the API service.

    Log lines use a consistent ``key=value`` style in message bodies so they
    remain readable in plain-text aggregators without a JSON formatter.

    Args:
        level: Logging level name (for example ``"INFO"`` or ``"DEBUG"``).

    Returns:
        None. Side effect: configures the root logger.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger namespaced under ``fx_pulse``.

    Args:
        name: Logical module name (for example ``"redis"`` or ``"fx.frankfurter"``).

    Returns:
        Configured ``logging.Logger`` instance.
    """
    return logging.getLogger(f"fx_pulse.{name}")
