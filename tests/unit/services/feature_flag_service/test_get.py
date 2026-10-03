"""Cache-aside reads: hit, miss that loads PostgreSQL, miss that is missing."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients import create_redis_key
from app.clients.postgres import FeatureFlagRow
from app.models.feature_flags import FeatureFlag
from app.models.user_details import UserDetails
from app.services import FeatureFlagNotFoundError, FeatureFlagService

_NAME = "dark_mode"
_CALLER = UserDetails(tenant_id="tenant-a", user_id="user-1")
_OTHER = UserDetails(tenant_id="tenant-b", user_id="user-2")
_CACHE_KEY = create_redis_key("feature_flag", _CALLER.tenant_id, _NAME)
_FLAG = FeatureFlag(
    name=_NAME,
    enabled=True,
    updated_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
    updated_by_user_id=_CALLER.user_id,
)
_CACHE_TTL_SECONDS = 300


async def test_get_returns_the_cached_flag_without_touching_postgres(
    feature_flag_service: FeatureFlagService,
    redis_client: MagicMock,
    postgres_client: MagicMock,
) -> None:
    """A Redis hit is the flag; the database session is never opened."""
    redis_client.raw.get.return_value = _FLAG.model_dump_json()

    flag = await feature_flag_service.get_flag(_NAME, _CALLER)

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
        tenant_id=_CALLER.tenant_id,
        name=_NAME,
        value=True,
        updated_at=_FLAG.updated_at,
        updated_by_user_id=_CALLER.user_id,
    )

    flag = await feature_flag_service.get_flag(_NAME, _CALLER)

    assert flag == _FLAG
    postgres_session.get.assert_awaited_once_with(
        FeatureFlagRow,
        (_CALLER.tenant_id, _NAME),
    )
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
        await feature_flag_service.get_flag("missing", _CALLER)

    assert caught.value.name == "missing"
    redis_client.raw.set.assert_not_called()


async def test_get_looks_up_only_the_callers_tenant(
    feature_flag_service: FeatureFlagService,
    redis_client: MagicMock,
    postgres_session: AsyncMock,
) -> None:
    """Another tenant's name is a different cache key and a different row identity."""
    redis_client.raw.get.return_value = None
    postgres_session.get.return_value = None

    with pytest.raises(FeatureFlagNotFoundError):
        await feature_flag_service.get_flag(_NAME, _OTHER)

    redis_client.raw.get.assert_awaited_once_with(
        create_redis_key("feature_flag", _OTHER.tenant_id, _NAME),
    )
    postgres_session.get.assert_awaited_once_with(
        FeatureFlagRow,
        (_OTHER.tenant_id, _NAME),
    )
