"""
Tests for shared logging configuration helpers.
"""

from __future__ import annotations

import logging

from app.core.logging_config import configure_logging, get_logger


def test_get_logger_uses_fx_pulse_namespace() -> None:
    """Return loggers namespaced under fx_pulse."""
    assert get_logger("tests").name == "fx_pulse.tests"


def test_configure_logging_sets_root_level() -> None:
    """Apply the requested log level to the root logger."""
    configure_logging("DEBUG")
    assert logging.getLogger().level == logging.DEBUG
