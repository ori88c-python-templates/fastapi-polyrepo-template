"""Writes persist in PostgreSQL and refresh Redis."""

from app.models.user_details import UserDetails
from app.services import FeatureFlagService

_NAME = "dark_mode"
_CALLER = UserDetails(tenant_id="tenant-a", user_id="user-1")
_EDITOR = UserDetails(tenant_id="tenant-a", user_id="user-2")


async def test_set_inserts_a_row_that_get_returns(
    feature_flag_service: FeatureFlagService,
) -> None:
    """A new name is stored so a later get does not raise."""
    written = await feature_flag_service.set_flag(_NAME, enabled=True, user_details=_CALLER)

    loaded = await feature_flag_service.get_flag(_NAME, _CALLER)

    assert loaded.name == _NAME
    assert loaded.enabled is True
    assert loaded.updated_by_user_id == _CALLER.user_id
    assert loaded.updated_at == written.updated_at


async def test_set_updates_an_existing_flag(
    feature_flag_service: FeatureFlagService,
) -> None:
    """A second write is what get returns, including the new editor."""
    await feature_flag_service.set_flag(_NAME, enabled=True, user_details=_CALLER)

    updated = await feature_flag_service.set_flag(_NAME, enabled=False, user_details=_EDITOR)

    loaded = await feature_flag_service.get_flag(_NAME, _CALLER)
    assert loaded.enabled is False
    assert loaded.updated_by_user_id == _EDITOR.user_id
    assert loaded.updated_at == updated.updated_at
