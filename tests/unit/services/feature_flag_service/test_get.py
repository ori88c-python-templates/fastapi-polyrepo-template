"""Cache-aside reads: hit, miss that loads PostgreSQL, miss that is missing."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients.postgres import FeatureFlagRow
from app.models.feature_flags import FeatureFlag
from app.services import FeatureFlagNotFoundError, FeatureFlagService

_NAME = "dark_mode"
_CACHE_KEY = "feature_flag:dark_mode"
_FLAG = FeatureFlag(
    name=_NAME,
    enabled=True,
    updated_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
)
_CACHE_TTL_SECONDS = 300


async def test_get_returns_the_cached_flag_without_touching_postgres(
    feature_flag_service: FeatureFlagService,
    redis_client: MagicMock,
    postgres_client: MagicMock,
) -> None:
    """A Redis hit is the flag; the database session is never opened."""
    redis_client.raw.get.return_value = _FLAG.model_dump_json()

    flag = await feature_flag_service.get_flag(_NAME)

    assert flag == _FLAG
    postgres_client.create_session.assert_not_called()
    redis_client.raw.set.assert_not_called()


async def test_get_loads_postgres_on_a_cache_miss_and_populates_redis(
    feature_flag_service: FeatureFlagService,
    redis_client: MagicMock,
    postgres_session: AsyncMock,
) -> None:
    """A miss loads the row, returns it as a flag, and writes the cache with TTL."""
    redis_client.raw.get.return_value = None
    postgres_session.get.return_value = FeatureFlagRow(
        name=_NAME,
        value=True,
        updated_at=_FLAG.updated_at,
    )

    flag = await feature_flag_service.get_flag(_NAME)

    assert flag == _FLAG
    redis_client.raw.set.assert_awaited_once_with(
        _CACHE_KEY,
        _FLAG.model_dump_json(),
        ex=_CACHE_TTL_SECONDS,
    )


async def test_get_raises_when_the_flag_is_in_neither_store(
    feature_flag_service: FeatureFlagService,
    redis_client: MagicMock,
    postgres_session: AsyncMock,
) -> None:
    """A miss with no row is an error, not a disabled flag, and does not cache."""
    redis_client.raw.get.return_value = None
    postgres_session.get.return_value = None

    with pytest.raises(FeatureFlagNotFoundError) as caught:
        await feature_flag_service.get_flag("missing")

    assert caught.value.name == "missing"
    redis_client.raw.set.assert_not_called()
