"""Shared fixtures for in-process unit tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients import PostgresClient, RedisClient
from app.logger import LogManager
from app.services import FeatureFlagService
from app.state import AppState
from tests.unit.app_state_factory import AppStateFactory, build_app_state


@pytest.fixture
def redis_client() -> MagicMock:
    """Provide a Redis wrapper whose ``raw`` commands are async mocks.

    Returns:
        A ``MagicMock`` specced on ``RedisClient``, with ``raw.get`` / ``raw.set``
        awaitable so a service test can canned-response the cache.
    """
    client = MagicMock(spec=RedisClient)
    client.raw = AsyncMock()
    return client


@pytest.fixture
def postgres_session() -> AsyncMock:
    """Provide an async session usable as ``async with postgres.create_session()``.

    ``add`` is a sync ``MagicMock`` because SQLAlchemy's ``session.add`` is not a
    coroutine; leaving it on the ``AsyncMock`` would leak an un-awaited coroutine.

    Returns:
        An ``AsyncMock`` whose ``__aenter__`` returns itself, so ``session.get``
        and ``session.commit`` can be canned per test.
    """
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = False
    session.add = MagicMock()
    return session


@pytest.fixture
def postgres_client(postgres_session: AsyncMock) -> MagicMock:
    """Provide a PostgreSQL wrapper whose ``create_session`` is synchronous.

    ``PostgresClient.create_session`` is not a coroutine. An ``AsyncMock`` of
    the whole client would make ``create_session()`` awaitable and break
    ``async with``.

    Args:
        postgres_session: Session the sync factory returns.

    Returns:
        A ``MagicMock`` specced on ``PostgresClient``.
    """
    client = MagicMock(spec=PostgresClient)
    client.create_session = MagicMock(return_value=postgres_session)
    return client


@pytest.fixture
def make_app_state(log_manager: LogManager) -> AppStateFactory:
    """Provide a factory that builds AppState with AsyncMock defaults.

    Args:
        log_manager: Buffer-backed manager shared by every state this factory builds.

    Returns:
        A callable that accepts optional ``redis``, ``postgres``, and ``feature_flag``
        dependencies and fills in specced AsyncMocks for the rest.
    """

    def factory(
        *,
        redis: RedisClient | None = None,
        postgres: PostgresClient | None = None,
        feature_flag: FeatureFlagService | None = None,
    ) -> AppState:
        """Build AppState, forwarding only the dependencies the caller supplied.

        Args:
            redis: Injected Redis client, or ``None`` for a specced AsyncMock.
            postgres: Injected PostgreSQL client, or ``None`` for a specced AsyncMock.
            feature_flag: Injected service, or ``None`` for a specced AsyncMock.

        Returns:
            Frozen application state for a test FastAPI app.
        """
        return build_app_state(
            log_manager,
            redis=redis,
            postgres=postgres,
            feature_flag=feature_flag,
        )

    return factory
