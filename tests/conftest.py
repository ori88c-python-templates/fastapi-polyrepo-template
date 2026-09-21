"""Fixtures shared by unit, integration, and e2e tests.

``sink`` and ``log_manager`` are always available. ``throwaway_stores`` starts
Docker only when a test requests it, so ``pytest tests/unit`` stays container-free.
"""

from __future__ import annotations

from collections.abc import Iterator
from io import BytesIO
from typing import TYPE_CHECKING

import pytest

from app.config import Environment, LoggerConfig
from app.logger import LogManager

if TYPE_CHECKING:
    from tests.throwaway_stores import ThrowawayStores


@pytest.fixture
def sink() -> BytesIO:
    """Provide an in-memory binary stream standing in for stdout.

    Returns:
        An empty buffer that a :class:`LogManager` can write records to.
    """
    return BytesIO()


@pytest.fixture
def log_manager(sink: BytesIO) -> LogManager:
    """Provide a LogManager that writes to ``sink``.

    Args:
        sink: Buffer every record is written to. Tests that inspect logs request
            this fixture; tests that do not can ignore it.

    Returns:
        A manager whose records tests can ignore or inspect without touching stdout.
    """
    return LogManager(
        LoggerConfig(),
        env=Environment.DEV,
        app_version="0.1.0",
        stream=sink,
    )


@pytest.fixture(scope="session")
def throwaway_stores() -> Iterator[ThrowawayStores]:
    """Start throwaway Redis and PostgreSQL, migrate, then tear both down.

    Yields:
        Config objects pointed at the running containers, not Compose.
    """
    from tests.alembic_upgrade import upgrade_to_head  # noqa: PLC0415
    from tests.throwaway_stores import start_throwaway_stores  # noqa: PLC0415

    with start_throwaway_stores() as stores:
        upgrade_to_head(stores)
        yield stores
