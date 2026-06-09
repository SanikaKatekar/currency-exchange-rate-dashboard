"""
Assignment compliance checks for README markers and sample data.

Overview:
    Verifies required assignment artifacts exist in the repository, including
    the ``android-cursor`` README marker and the offline fallback sample file.

Functions:
    test_readme_has_android_cursor_marker: README contains android-cursor marker.
    test_sample_fx_file_exists: Offline fallback JSON file exists in data/.
"""

from __future__ import annotations

from pathlib import Path


def test_readme_has_android_cursor_marker() -> None:
    """Ensure README includes the required android-cursor compliance marker."""
    readme = Path(__file__).resolve().parents[2].joinpath("README.md").read_text(encoding="utf-8")
    assert "android-cursor" in readme


def test_sample_fx_file_exists() -> None:
    """Ensure the offline fallback sample file exists at the repository path."""
    sample = Path(__file__).resolve().parents[2].joinpath("data", "sample_fx.json")
    assert sample.is_file()
