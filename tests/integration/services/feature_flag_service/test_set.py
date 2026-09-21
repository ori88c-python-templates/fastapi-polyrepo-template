"""Writes persist in PostgreSQL and refresh Redis."""

from app.services import FeatureFlagService

_NAME = "dark_mode"


async def test_set_inserts_a_row_that_get_returns(
    feature_flag_service: FeatureFlagService,
) -> None:
    """A new name is stored so a later get does not raise."""
    written = await feature_flag_service.set_flag(_NAME, enabled=True)

    loaded = await feature_flag_service.get_flag(_NAME)

    assert loaded.name == _NAME
    assert loaded.enabled is True
    assert loaded.updated_at == written.updated_at


async def test_set_updates_an_existing_flag(
    feature_flag_service: FeatureFlagService,
) -> None:
    """A second write is what get returns, not the first value."""
    await feature_flag_service.set_flag(_NAME, enabled=True)

    updated = await feature_flag_service.set_flag(_NAME, enabled=False)

    loaded = await feature_flag_service.get_flag(_NAME)
    assert loaded.enabled is False
    assert loaded.updated_at == updated.updated_at
