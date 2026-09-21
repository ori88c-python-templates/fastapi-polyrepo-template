"""Build a typed AppState for in-process router tests."""

from typing import Protocol, cast
from unittest.mock import AsyncMock

from app.clients import PostgresClient, RedisClient
from app.logger import LogManager
from app.services import FeatureFlagService
from app.state import AppClients, AppServices, AppState


class AppStateFactory(Protocol):
    """Callable that fills AppState, defaulting omitted dependencies to AsyncMocks."""

    def __call__(
        self,
        *,
        redis: RedisClient | None = None,
        postgres: PostgresClient | None = None,
        feature_flag: FeatureFlagService | None = None,
    ) -> AppState:
        """Assemble state from the given dependencies.

        Args:
            redis: Injected Redis client. ``None`` means a specced AsyncMock.
            postgres: Injected PostgreSQL client. ``None`` means a specced AsyncMock.
            feature_flag: Injected service. ``None`` means a specced AsyncMock.

        Returns:
            Frozen application state suitable for attaching to a test FastAPI app.
        """
        ...


def build_app_state(
    log_manager: LogManager,
    *,
    redis: RedisClient | None = None,
    postgres: PostgresClient | None = None,
    feature_flag: FeatureFlagService | None = None,
) -> AppState:
    """Assemble AppState, substituting AsyncMocks for any omitted dependency.

    Args:
        log_manager: Already-built manager (usually writing to a buffer).
        redis: Injected Redis client. Defaults to a specced AsyncMock.
        postgres: Injected PostgreSQL client. Defaults to a specced AsyncMock.
        feature_flag: Injected service. Defaults to a specced AsyncMock.

    Returns:
        Frozen application state suitable for attaching to a test FastAPI app.
    """
    return AppState(
        clients=AppClients(
            redis=redis if redis is not None else cast(RedisClient, AsyncMock(spec=RedisClient)),
            postgres=(
                postgres
                if postgres is not None
                else cast(PostgresClient, AsyncMock(spec=PostgresClient))
            ),
        ),
        services=AppServices(
            feature_flag=(
                feature_flag
                if feature_flag is not None
                else cast(FeatureFlagService, AsyncMock(spec=FeatureFlagService))
            ),
        ),
        log_manager=log_manager,
    )
