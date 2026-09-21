"""Cache-aside reads against real Redis and PostgreSQL."""

import pytest

from app.clients import RedisClient
from app.services import FeatureFlagNotFoundError, FeatureFlagService

_NAME = "dark_mode"
_CACHE_KEY = "feature_flag:dark_mode"


async def test_get_raises_when_the_flag_is_in_neither_store(
    feature_flag_service: FeatureFlagService,
) -> None:
    """A name in neither Redis nor PostgreSQL is an error, not a disabled flag."""
    with pytest.raises(FeatureFlagNotFoundError) as caught:
        await feature_flag_service.get_flag("missing")

    assert caught.value.name == "missing"


async def test_get_returns_a_flag_after_set(
    feature_flag_service: FeatureFlagService,
) -> None:
    """A write is visible to the next read through the real stores."""
    written = await feature_flag_service.set_flag(_NAME, enabled=True)

    loaded = await feature_flag_service.get_flag(_NAME)

    assert loaded.name == _NAME
    assert loaded.enabled is True
    assert loaded.updated_at == written.updated_at


async def test_get_loads_postgres_when_the_cache_key_is_gone(
    feature_flag_service: FeatureFlagService,
    redis_client: RedisClient,
) -> None:
    """A cache miss still returns the row and writes Redis again."""
    written = await feature_flag_service.set_flag(_NAME, enabled=True)
    await redis_client.raw.delete(_CACHE_KEY)

    loaded = await feature_flag_service.get_flag(_NAME)

    assert loaded == written
    assert await redis_client.raw.get(_CACHE_KEY) == written.model_dump_json()
