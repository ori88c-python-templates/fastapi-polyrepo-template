"""Writes: insert a new row, update an existing one, refresh Redis."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from app.clients import create_redis_key
from app.clients.postgres import FeatureFlagRow
from app.models.user_details import UserDetails
from app.services import FeatureFlagService

_NAME = "dark_mode"
_CALLER = UserDetails(tenant_id="tenant-a", user_id="user-1")
_OTHER = UserDetails(tenant_id="tenant-b", user_id="user-2")
_CACHE_KEY = create_redis_key("feature_flag", _CALLER.tenant_id, _NAME)
_CACHE_TTL_SECONDS = 300


async def test_set_inserts_when_postgres_has_no_row(
    feature_flag_service: FeatureFlagService,
    redis_client: MagicMock,
    postgres_session: AsyncMock,
) -> None:
    """A new name is added, committed, and written to Redis with the cache TTL."""
    postgres_session.get.return_value = None

    flag = await feature_flag_service.set_flag(_NAME, enabled=True, user_details=_CALLER)

    assert flag.name == _NAME
    assert flag.enabled is True
    assert flag.updated_by_user_id == _CALLER.user_id
    assert flag.updated_at.tzinfo is UTC
    postgres_session.get.assert_awaited_once_with(
        FeatureFlagRow,
        (_CALLER.tenant_id, _NAME),
    )
    postgres_session.add.assert_called_once()
    added = postgres_session.add.call_args.args[0]
    assert added.tenant_id == _CALLER.tenant_id
    assert added.name == _NAME
    assert added.value is True
    assert added.updated_by_user_id == _CALLER.user_id
    postgres_session.commit.assert_awaited_once()
    redis_client.raw.set.assert_awaited_once_with(
        _CACHE_KEY,
        flag.model_dump_json(),
        ex=_CACHE_TTL_SECONDS,
    )


async def test_set_updates_an_existing_row_in_place(
    feature_flag_service: FeatureFlagService,
    redis_client: MagicMock,
    postgres_session: AsyncMock,
) -> None:
    """An existing row is mutated, not re-added, and Redis is refreshed."""
    row = FeatureFlagRow(
        tenant_id=_CALLER.tenant_id,
        name=_NAME,
        value=False,
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_by_user_id=_OTHER.user_id,
    )
    postgres_session.get.return_value = row

    flag = await feature_flag_service.set_flag(_NAME, enabled=True, user_details=_CALLER)

    assert flag.name == _NAME
    assert flag.enabled is True
    assert flag.updated_by_user_id == _CALLER.user_id
    assert flag.updated_at.tzinfo is UTC
    assert row.value is True
    assert row.updated_at == flag.updated_at
    assert row.updated_by_user_id == _CALLER.user_id
    postgres_session.add.assert_not_called()
    postgres_session.commit.assert_awaited_once()
    redis_client.raw.set.assert_awaited_once_with(
        _CACHE_KEY,
        flag.model_dump_json(),
        ex=_CACHE_TTL_SECONDS,
    )
