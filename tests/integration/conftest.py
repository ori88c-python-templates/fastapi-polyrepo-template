"""Pytest fixtures for Redis, PostgreSQL, and the integration event loop.

Throwaway stores and Alembic live in ``tests/``. Future services should take
``postgres_client`` / ``redis_client`` from here. Feature-flag wiring stays in
``services/feature_flag_service/conftest.py``.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from app.clients import PostgresClient, RedisClient
from app.config import PostgresConfig, RedisConfig
from app.logger import LogManager

if TYPE_CHECKING:
    from tests.throwaway_stores import ThrowawayStores

_INTEGRATION_ROOT: Final = Path(__file__).resolve().parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test under this directory as ``integration``.

    Args:
        items: The collected session. Tests outside this tree are left unmarked.
    """
    marker = pytest.mark.integration
    for item in items:
        try:
            item.path.relative_to(_INTEGRATION_ROOT)
        except ValueError:
            continue
        item.add_marker(marker)


def pytest_asyncio_loop_factories(
    config: pytest.Config,
    item: pytest.Item,
) -> Mapping[str, Callable[[], asyncio.AbstractEventLoop]]:
    """Use a selector loop so psycopg async can connect on Windows.

    Linux and macOS already default to a selector loop. One factory keeps a
    single code path. Unit tests do not see this hook.

    Args:
        config: The pytest config. Required by the hook spec.
        item: The test item. Required by the hook spec.

    Returns:
        A single factory. pytest-asyncio hides the id when there is only one.
    """
    del config, item
    return {"selector": asyncio.SelectorEventLoop}


@pytest.fixture(scope="session")
def postgres_config(throwaway_stores: ThrowawayStores) -> PostgresConfig:
    """Expose the session Postgres settings for any service under test.

    Args:
        throwaway_stores: Session containers after Alembic has run.

    Returns:
        Settings that reach the throwaway PostgreSQL, not Compose.
    """
    return throwaway_stores.postgres


@pytest.fixture(scope="session")
def redis_config(throwaway_stores: ThrowawayStores) -> RedisConfig:
    """Expose the session Redis settings for any service under test.

    Args:
        throwaway_stores: Session containers after Alembic has run.

    Returns:
        Settings that reach the throwaway Redis, not Compose.
    """
    return throwaway_stores.redis


@pytest.fixture
async def postgres_client(
    postgres_config: PostgresConfig,
    log_manager: LogManager,
) -> AsyncGenerator[PostgresClient]:
    """Open a real SQLAlchemy engine against the session Postgres.

    Args:
        postgres_config: Session container settings.
        log_manager: Supplies the client child logger.

    Yields:
        A started client. ``stop`` runs even if the test fails.
    """
    client = PostgresClient(
        postgres_config,
        log_manager.get_child_logger("PostgresClient"),
    )
    await client.start()
    try:
        yield client
    finally:
        await client.stop()


@pytest.fixture
async def redis_client(
    redis_config: RedisConfig,
    log_manager: LogManager,
) -> AsyncGenerator[RedisClient]:
    """Open a real redis-py pool against the session Redis.

    Args:
        redis_config: Session container settings.
        log_manager: Supplies the client child logger.

    Yields:
        A started client. ``stop`` runs even if the test fails.
    """
    client = RedisClient(
        redis_config,
        log_manager.get_child_logger("RedisClient"),
    )
    await client.start()
    try:
        yield client
    finally:
        await client.stop()


@pytest.fixture(autouse=True)
async def _flush_redis(  # pyright: ignore[reportUnusedFunction]
    redis_client: RedisClient,
) -> None:
    """Empty Redis before every test so a later service does not inherit keys.

    Args:
        redis_client: Started pool for ``FLUSHDB``.
    """
    await redis_client.raw.flushdb()  # pyright: ignore[reportUnknownMemberType]
