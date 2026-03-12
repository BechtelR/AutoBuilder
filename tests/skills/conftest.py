"""Shared fixtures for skills tests."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def _enable_log_propagation() -> Generator[None, None, None]:  # type: ignore[reportUnusedFunction]
    """Ensure the ``app`` logger propagates during tests so caplog works."""
    app_logger = logging.getLogger("app")
    original = app_logger.propagate
    app_logger.propagate = True
    yield
    app_logger.propagate = original
